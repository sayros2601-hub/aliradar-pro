"""One existing card follows ordinary copy validation without changing the catalog."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

from test_gemini_text import mirror_bundle, reply, ai_seo


class TextSmokeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('fluxixo_ai.text_smoke'))
        self.smoke = importlib.import_module('fluxixo_ai.text_smoke')
        from fluxixo_ai import gemini_client
        self.client = gemini_client
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.site = self.root / 'fluxixo_site'
        (self.site / 'dist/js').mkdir(parents=True)
        (self.site / 'tools').mkdir()
        self.bundle = mirror_bundle()
        self.record = {'id': 'test-existing-mirror', **self.bundle['ru'], 'category': 'Инструменты',
                       'sourceProductId': '123456',
                       'sourceTitle': 'New Telescoping Magnetic Inspection Mirror Tool 360 Swivel Mechanic',
                       'original': 'assets/originals/mirror.webp', 'image': 'assets/images/mirror.webp',
                       'views': ['assets/images/mirror-use.webp', 'assets/images/mirror-result.webp']}
        for index, relative in enumerate([self.record['original'], self.record['image'], *self.record['views']]):
            asset = self.site / 'dist' / relative
            asset.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', (640, 640), (index * 50, 100, 100)).save(asset, 'WEBP', lossless=True)
        (self.site / 'dist/js/catalog.js').write_text('window.MIRA_CATALOG = '+json.dumps({'products': [self.record]})+';', encoding='utf-8')
        (self.site / 'tools/i18n_data.json').write_text(json.dumps({'products': {self.record['id']: {
            k: v for k, v in self.bundle.items() if k != 'ru'}}}), encoding='utf-8')
        self.env = patch.dict(os.environ, {'FLUXIXO_TEXT_PROVIDER': 'gemini', 'FLUXIXO_TEXT_GEMINI_API_KEY': 'test-key',
            'FLUXIXO_GEMINI_BUDGET_PATH': str(Path(self.tmp.name) / 'usage.sqlite3'), 'FLUXIXO_OFFLINE': '1'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def snapshot(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file() and 'reserve' not in p.parts}

    @staticmethod
    def accepted():
        from fluxixo_ai.reviewed_media import CHECKS
        return {'accepted': True, **dict.fromkeys(CHECKS, True), 'reasons': []}

    def test_ordinary_enrichment_accepts_one_card_excluding_itself(self):
        before = self.snapshot()
        calls = []
        def fake(url, body, headers):
            calls.append(url)
            if 'gemini-3.8-flash' in url:
                return reply(self.accepted())
            request = json.loads(body['contents'][0]['parts'][0]['text'])
            if request.get('task') == 'verify_source_claims':
                checks = {locale: dict.fromkeys(request['required_fields'], True)
                          for locale in request['proposed_copy']}
                return reply({'accepted': True, 'checks': checks, 'unsupported_claims': []})
            if 'старший редактор' in body['systemInstruction']['parts'][0]['text']:
                return reply({'who': 'Зеркало пригодится для осмотра крепежа за шкафом и под капотом, когда к детали трудно подойти напрямую. Подвижная головка помогает подобрать направление отражения без разборки соседних деталей.',
                              'check': ['Сверьте длину ручки и размер зеркала с доступным пространством.',
                                        'Уточните диапазон поворота головки и способ фиксации шарнира.',
                                        'Проверьте комплектацию выбранного варианта на странице продавца.']})
            return reply(self.bundle)
        clock = [2_000_000_000.0]
        with patch.object(self.client, '_post_json', side_effect=fake), \
             patch.object(self.client.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(self.client.time, 'sleep', side_effect=lambda delay: clock.__setitem__(0, clock[0]+delay)):
            report = self.smoke.run_smoke(self.record['id'], repo_root=self.root)
        self.assertTrue(report['success'])
        self.assertEqual(6, report['validated_locales'])
        self.assertFalse(report['published'])
        self.assertEqual('HIGH', report['thinking_level'])
        self.assertEqual(3, sum('gemini-3.8-flash:generateContent' in url for url in calls))
        self.assertTrue(report['all_frames_accepted'])
        self.assertEqual(['hero', 'application', 'result'], [frame['role'] for frame in report['frames']])
        self.assertEqual([[], [report['frames'][0]['image_sha256']],
                         [frame['image_sha256'] for frame in report['frames'][:2]]],
                         [frame['prior_image_sha256'] for frame in report['frames']])
        self.assertEqual(before, self.snapshot())
        self.assertNotIn('test-key', json.dumps(report))

    def run_with_reviewer(self, reviewer):
        # Text path is covered above; these cases isolate exact-byte review/cache behavior.
        with patch('fluxixo_ai.autonomous._maybe_ai_enrich', return_value=(self.record, {k: v for k, v in self.bundle.items() if k != 'ru'})), \
             patch('fluxixo_ai.reviewed_media._default_reviewer', side_effect=reviewer):
            return self.smoke.run_smoke(self.record['id'], repo_root=self.root)

    def test_identical_resume_reuses_acceptance_and_changed_final_requires_new_review(self):
        calls = []
        def accept(source, output, **kwargs):
            calls.append(kwargs['role'])
            return self.accepted()
        self.run_with_reviewer(accept)
        self.assertEqual(['hero', 'application', 'result'], calls)
        calls.clear()
        report = self.run_with_reviewer(accept)
        self.assertEqual([], calls)
        self.assertTrue(all(frame['reused'] for frame in report['frames']))
        Image.new('RGB', (640, 640), (250, 100, 100)).save(self.site / 'dist' / self.record['views'][1], 'WEBP', lossless=True)
        report = self.run_with_reviewer(accept)
        self.assertEqual(['result'], calls)
        self.assertFalse(report['frames'][2]['reused'])

    def test_rejection_is_distinct_from_transport_failure_and_never_published(self):
        calls = []
        def reject(source, output, **kwargs):
            calls.append(kwargs['role'])
            return {**self.accepted(), 'accepted': False, 'role': False, 'reasons': ['Does not demonstrate use.']}
        result = self.run_with_reviewer(reject)
        self.assertEqual('rejected', result['status'])
        self.assertFalse(result['success'])
        self.assertFalse(result['published'])
        self.assertEqual(['hero'], calls)
        self.assertEqual('not_reviewed', result['frames'][1]['status'])
        # Changed source invalidates the rejection too; a transport error remains visibly deferred.
        Image.new('RGB', (640, 640), (225, 100, 100)).save(self.site / 'dist' / self.record['original'], 'WEBP', lossless=True)
        def unavailable(*args, **kwargs):
            raise self.client.GeminiDeferred('gemini_http_429', 2_000_000_300)
        result = self.run_with_reviewer(unavailable)
        self.assertEqual('deferred', result['status'])
        self.assertEqual('gemini_http_429', result['frames'][0]['reason'])
        self.assertEqual(2_000_000_300, result['frames'][0]['retry_at'])
        self.assertFalse(result['published'])

    def test_new_copy_policy_revalidates_only_text_on_an_identical_gallery(self):
        first = self.run_with_reviewer(lambda *args, **kwargs: self.accepted())
        self.assertTrue(first['success'])
        with patch.object(self.smoke, 'COPY_POLICY', 'new-claims-policy'):
            second = self.run_with_reviewer(lambda *args, **kwargs: self.fail('image review should be reused'))
        self.assertFalse(second['text_reused'])
        self.assertTrue(second['success'])
        self.assertEqual(0, second['reviews_requested'])
        self.assertTrue(all(frame['reused'] for frame in second['frames']))

    def test_same_image_timeout_waits_then_stops_without_another_call(self):
        calls = []
        def unavailable(source, frame, **kw):
            calls.append(hashlib.sha256(frame).hexdigest())
            raise self.client.GeminiDeferred('gemini_transport_timeout', self.smoke.time.time() + 60)
        clock = [2_000_000_000.]
        with patch.object(self.smoke.time, 'time', side_effect=lambda: clock[0]):
            first = self.run_with_reviewer(unavailable)
            self.assertEqual('deferred', first['status'])
            self.assertEqual(0, self.run_with_reviewer(unavailable)['reviews_requested'])
            clock[0] += 86400
            stopped = self.run_with_reviewer(unavailable)
            self.assertEqual('stopped', stopped['status'])
            self.assertEqual('gemini_transport_timeout', stopped['frames'][0]['reason'])
            clock[0] += 86400
            self.assertEqual(0, self.run_with_reviewer(unavailable)['reviews_requested'])
        self.assertEqual(2, len(calls))
        self.assertEqual(calls[0], calls[1])

    def test_unknown_card_and_missing_key_fail_without_requests(self):
        with patch.object(self.client, '_post_json', side_effect=AssertionError('must not request')):
            with self.assertRaises(ValueError):
                self.smoke.run_smoke('not-in-catalog', repo_root=self.root)
            with patch.dict(os.environ, {'FLUXIXO_TEXT_GEMINI_API_KEY': ''}):
                with self.assertRaises(self.client.GeminiDeferred):
                    self.smoke.run_smoke(self.record['id'], repo_root=self.root)

    def test_scoped_missing_key_never_reads_legacy_local_credentials(self):
        import types
        credential_module = types.ModuleType('dpapi_store')
        credential_module.load_credential = lambda *a: self.fail('must not read local credentials')
        with patch.dict('sys.modules', {'dpapi_store': credential_module}), \
             patch.dict(os.environ, {'FLUXIXO_TEXT_GEMINI_API_KEY': ''}):
            keys = ai_seo.load_ai_keys(local=True)
        self.assertEqual({'FLUXIXO_TEXT_PROVIDER': 'gemini', 'FLUXIXO_TEXT_GEMINI_API_KEY': ''}, keys)


if __name__ == '__main__':
    unittest.main()
