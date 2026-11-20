"""No network: provider envelopes, atomic quota reservations, backoff and safe errors."""
from concurrent.futures import ThreadPoolExecutor
from email.utils import formatdate
import importlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
import urllib.error
from unittest.mock import patch


class GeminiClientTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('fluxixo_ai.gemini_client')
        self.assertIsNotNone(spec, 'Gemini client must implement isolated quota-safe transport')
        self.client = importlib.import_module('fluxixo_ai.gemini_client')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'budget.sqlite3'
        self.clock = 2_000_000_000.0
        self.timer = patch.object(self.client.time, 'time', side_effect=lambda: self.clock)
        self.timer.start()
        self.addCleanup(self.timer.stop)
        self.sleep = patch.object(self.client.time, 'sleep', side_effect=self.advance)
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def advance(self, seconds):
        self.clock += seconds

    def call(self, transport=None, model='gemini-3.8-flash', **kwargs):
        return self.client.call_json('system', 'user', api_key='fake-test-key', model=model,
                                     transport=transport or (lambda *args: self.good()),
                                     budget_path=self.path, **kwargs)

    @staticmethod
    def good():
        return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
            {'thought': True, 'text': '{"unsafe":"reasoning"}'}, {'text': '{"approved":true}'},
        ]}}]}

    def test_no_model_switch_and_images_are_inline(self):
        captured = []
        def fake(url, body, headers):
            captured.append((url, body, headers))
            return self.good()
        self.assertEqual({'approved': True}, self.call(fake, images=[b'\x89PNG\r\n\x1a\nabc']))
        url, body, headers = captured[0]
        self.assertTrue(url.endswith('/gemini-3.8-flash:generateContent'))
        self.assertEqual('HIGH', body['generationConfig']['thinkingConfig']['thinkingLevel'])
        self.assertEqual('image/png', body['contents'][0]['parts'][1]['inlineData']['mimeType'])
        self.assertNotIn('fake-test-key', url)

    def test_cadence_and_rolling_limit_are_persistent(self):
        for _ in range(18):
            self.call()
            self.advance(20)
        with self.assertRaises(self.client.GeminiDeferred) as error:
            self.call(transport=lambda *a: self.fail('must not exceed review allowance'))
        self.assertEqual('gemini_daily_budget', error.exception.code)
        self.assertGreater(error.exception.retry_at, self.clock)
        self.advance(86401)
        self.assertEqual({'approved': True}, self.call())

    def test_text_and_review_allowances_are_separate_and_throttle_short_wait(self):
        self.call()
        before = self.clock
        self.call()
        self.assertGreaterEqual(self.clock-before, 12.1)
        self.call(model='gemini-3.5-flash-lite')
        before = self.clock
        self.call(model='gemini-3.5-flash-lite')
        self.assertGreaterEqual(self.clock-before, 4.1)

    def test_http_429_retry_after_persists_and_does_not_retry_network(self):
        calls = []
        def fail(*args):
            calls.append(1)
            raise urllib.error.HTTPError('https://no-secret.invalid', 429, 'fake-test-key', {'Retry-After': '300'}, None)
        with self.assertRaises(self.client.GeminiDeferred) as error:
            self.call(fail)
        self.assertEqual(1, len(calls))
        self.assertEqual(self.clock + 300, error.exception.retry_at)
        self.assertNotIn('fake-test-key', str(error.exception))
        with self.assertRaises(self.client.GeminiDeferred):
            self.call(transport=lambda *a: self.fail('backoff must survive subsequent call'))
        with sqlite3.connect(self.path) as db:
            self.assertEqual(1, db.execute('SELECT count(*) FROM requests').fetchone()[0])
        db.close()

    def test_retry_after_http_date(self):
        def fail(*args):
            raise urllib.error.HTTPError('https://invalid', 429, 'ignored',
                                         {'Retry-After': formatdate(self.clock+120, usegmt=True)}, None)
        with self.assertRaises(self.client.GeminiDeferred) as error:
            self.call(fail)
        self.assertEqual(self.clock+120, error.exception.retry_at)

    def test_bad_finish_or_json_or_blocked_envelope_is_never_approved(self):
        bad = [
            {'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': '{"approved":true}'}]}}]},
            {'candidates': [{'content': {'parts': [{'text': '{"approved":true}'}]}}]},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'not-json'}]}}]},
            {'promptFeedback': {'blockReason': 'SAFETY'}},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{"approved":true}'}, {'functionCall': {'name': 'unexpected'}}]}}]},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'thought': True, 'text': '{"approved":true}'}]}}]},
        ]
        for response in bad:
            with self.subTest(response=response):
                with self.assertRaises(self.client.GeminiDeferred):
                    self.call(lambda *args: response)
                self.advance(3601)

    def test_timeout_has_no_raw_message_or_paid_fallback(self):
        def fail(*args):
            raise TimeoutError('private prompt fake-test-key')
        with self.assertRaises(self.client.GeminiDeferred) as error:
            self.call(fail)
        self.assertEqual('gemini_transport_unavailable', error.exception.code)
        self.assertNotIn('fake-test-key', str(error.exception))
        self.assertIsNone(error.exception.__cause__)

    def test_unsupported_model_is_rejected_before_transport(self):
        with self.assertRaises(self.client.GeminiDeferred) as error:
            self.call(lambda *a: self.fail('no arbitrary model'), model='gemini-paid-other')
        self.assertEqual('gemini_model_not_allowed', error.exception.code)

    def test_concurrent_callers_reserve_one_rate_slot_atomically(self):
        # Each process sees the same durable ledger; no caller can overspend a shared time slot.
        def reserve(_):
            try:
                self.client._reserve(self.path, 'gemini-3.8-flash', self.clock)
                return 'reserved'
            except self.client.GeminiDeferred as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(reserve, range(8)))
        self.assertEqual(1, outcomes.count('reserved'))
        self.assertEqual(7, outcomes.count('gemini_rate_wait'))

    def test_failed_durable_checkpoint_prevents_provider_request(self):
        hook = types.ModuleType('fluxixo_ai.state_checkpoint')
        def fail():
            raise OSError('sensitive internal detail')
        hook.checkpoint = fail
        with patch.dict('sys.modules', {'fluxixo_ai.state_checkpoint': hook}), \
             patch.dict(os.environ, {'FLUXIXO_DURABLE_CHECKPOINT': 'git'}):
            with self.assertRaises(self.client.GeminiDeferred) as error:
                self.call(lambda *args: self.fail('must checkpoint before provider request'))
        self.assertEqual('checkpoint_unavailable', error.exception.code)
        self.assertNotIn('sensitive', str(error.exception))

    def test_durable_checkpoint_happens_after_reservation_before_provider(self):
        hook = types.ModuleType('fluxixo_ai.state_checkpoint')
        sequence = []
        def checkpoint():
            with sqlite3.connect(self.path) as db:
                self.assertEqual(1, db.execute('SELECT count(*) FROM requests').fetchone()[0])
            db.close()
            sequence.append('checkpoint')
        hook.checkpoint = checkpoint
        def transport(*args):
            sequence.append('request')
            return self.good()
        with patch.dict('sys.modules', {'fluxixo_ai.state_checkpoint': hook}), \
             patch.dict(os.environ, {'FLUXIXO_DURABLE_CHECKPOINT': 'git'}):
            self.call(transport)
        self.assertEqual(['checkpoint', 'request'], sequence)


if __name__ == '__main__':
    unittest.main()
