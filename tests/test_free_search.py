"""Offline proof of keyless search bounds, exact-draft caching and fail-closed parsing."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from fluxixo_ai.free_search import check_external_text, require_search_capacity, SearchDeferred


class FreeSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'search.sqlite3'
        self.calls = []
        self.now = 1000.0
        self.hit = {'url': 'https://EXAMPLE.org/item#part', 'title': 'External title',
                    'content': 'Unique provider snippet which must never enter the durable database.'}

    def transport(self, url, body, headers, timeout):
        self.calls.append((url, body, headers, timeout))
        return {'query': body['query'], 'results': [self.hit], 'request_id': 'sample'}

    def check(self, text='Full original product description.', lang='en', **kwargs):
        options = {'compare': lambda results: (True, []), 'policy_version': 'test-v1',
                   'db_path': self.path, 'transport': self.transport, 'now': self.now}
        options.update(kwargs)
        return check_external_text(text, lang, **options)

    def test_keyless_only_and_cached_verdict_never_persists_provider_text(self):
        compared = []
        def compare(results):
            compared.append(results)
            return False, ['external overlap with a full quoted snippet must not be persisted']
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'must-not-be-used', 'SERPER_API_KEY': 'must-not-be-used'}):
            first = self.check(compare=compare)
            second = self.check(compare=lambda _: self.fail('cached verdict must not compare again'))
        self.assertFalse(first['passed'])
        self.assertEqual(first['issues'], ['external_overlap'])
        self.assertTrue(second['cache_hit'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(compared), 1)
        url, body, headers, timeout = self.calls[0]
        self.assertEqual(url, 'https://api.tavily.com/search')
        self.assertEqual(headers, {'Content-Type': 'application/json', 'X-Tavily-Access-Mode': 'keyless'})
        self.assertEqual(body['search_depth'], 'basic')
        self.assertFalse(body['auto_parameters'])
        self.assertEqual(body['exclude_domains'], ['fluxixo.shop'])
        self.assertLessEqual(body['max_results'], 5)
        self.assertLessEqual(timeout, 30)
        self.assertEqual(first['evidence_urls'], ['https://example.org/item'])
        raw = self.path.read_bytes()
        self.assertNotIn(self.hit['content'].encode(), raw)
        self.assertNotIn(b'Full original product description.', raw)
        self.assertNotIn(b'full quoted snippet', raw)

    def test_cache_binds_whole_description_locale_query_and_policy(self):
        self.check('same excerpt different ending A', query='same excerpt')
        self.check('same excerpt different ending B', query='same excerpt')
        self.check('same excerpt different ending B', 'fr', query='same excerpt')
        self.check('same excerpt different ending B', 'fr', query='same excerpt', policy_version='test-v2')
        self.assertEqual(len(self.calls), 4)

    def test_attempt_limit_is_rolling_durable_and_counts_failed_calls(self):
        for i in range(36):
            self.check(f'Original product description number {i}')
        with self.assertRaises(SearchDeferred) as cm:
            self.check('A further different description')
        self.assertEqual(cm.exception.code, 'search_daily_budget')
        self.assertEqual(len(self.calls), 36)
        self.now += 86401
        self.check('A further different description')
        self.assertEqual(len(self.calls), 37)

    def test_rate_limit_pauses_all_queries_and_resumes_without_paid_fallback(self):
        def limited(*args):
            self.calls.append(args)
            raise HTTPError(args[0], 429, 'secret provider body', {'Retry-After': '120'}, None)
        with self.assertRaises(SearchDeferred) as cm:
            self.check(transport=limited)
        self.assertEqual(cm.exception.code, 'search_http_429')
        self.assertNotIn('secret', str(cm.exception))
        self.now += 1
        with self.assertRaises(SearchDeferred):
            self.check('Another description')
        self.assertEqual(len(self.calls), 1)
        self.now += 120
        self.check()
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0], 2)

    def test_partial_error_and_unsupported_responses_never_approve(self):
        invalid = [None, 'sign up now', {'results': []}, {'query': 'wrong', 'results': []},
                   {'results': [], 'partial': True}, {'error': 'quota'}, {'results': [{}]},
                   {'results': [{'url': 'file:///secret', 'title': 'x', 'content': 'x'}]},
                   {'results': [{'url': 'http://127.0.0.1/x', 'title': 'x', 'content': 'x'}]}]
        for i, payload in enumerate(invalid):
            with self.subTest(payload=payload), self.assertRaises(SearchDeferred):
                self.check(db_path=Path(self.tmp.name) / f'bad{i}.sqlite3',
                           transport=lambda *args, value=payload: value,
                           compare=lambda _: (True, []))

    def test_natural_language_limit_instructions_cannot_look_like_zero_results(self):
        for field in ('answer', 'instructions', 'failed_results', 'incomplete', 'truncated', 'quota_notice'):
            with self.subTest(field=field), self.assertRaises(SearchDeferred):
                self.check(db_path=Path(self.tmp.name) / f'{field}.sqlite3',
                    transport=lambda url, body, *args, key=field: {
                        'query': body['query'], 'results': [], key: 'Rate limit reached, add an API key.'},
                    compare=lambda _: (True, []))

    def test_unsafe_result_links_never_become_external_evidence(self):
        for i, url in enumerate(('file:///secret', 'http://127.0.0.1/x', 'http://127.1/x',
                                  'https://user:pass@example.org/x', 'http://localhost/x')):
            with self.subTest(url=url), self.assertRaises(SearchDeferred):
                self.check(db_path=Path(self.tmp.name) / f'url{i}.sqlite3',
                    transport=lambda endpoint, body, *args, value=url: {
                        'query': body['query'], 'results': [{**self.hit, 'url': value}]})

    def test_432_and_433_hard_stop_all_other_queries_for_a_day(self):
        for status in (432, 433):
            path = Path(self.tmp.name) / f'limit{status}.sqlite3'
            attempts = []
            def limited(url, *args):
                attempts.append(url)
                raise HTTPError(url, status, 'limit', {}, None)
            with self.subTest(status=status):
                with self.assertRaises(SearchDeferred) as cm:
                    self.check(db_path=path, transport=limited)
                self.assertGreaterEqual(cm.exception.retry_at, self.now + 86400)
                with self.assertRaises(SearchDeferred):
                    self.check('Other text', db_path=path, transport=limited, now=self.now + 1)
                self.assertEqual(len(attempts), 1)

    def test_parallel_calls_share_the_same_36_attempt_reservation_limit(self):
        def attempt(index):
            try:
                return self.check(f'Independent product description {index}')['passed']
            except SearchDeferred as error:
                return error.code
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(40)))
        self.assertEqual(results.count(True), 36)
        self.assertEqual(results.count('search_daily_budget'), 4)
        self.assertEqual(len(self.calls), 36)

    def test_real_http_adapter_sets_timeout_and_never_sends_authentication(self):
        import json
        from fluxixo_ai.free_search import _post_json
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return json.dumps({'query': 'example', 'results': []}).encode()
        with patch('urllib.request.OpenerDirector.open', return_value=Response()) as opened:
            result = _post_json('https://api.tavily.com/search', {'query': 'example'},
                {'Content-Type': 'application/json', 'X-Tavily-Access-Mode': 'keyless'}, 30)
        request = opened.call_args.args[0]
        self.assertEqual(opened.call_args.kwargs['timeout'], 30)
        self.assertEqual(request.get_method(), 'POST')
        self.assertNotIn('authorization', {name.lower() for name, value in request.header_items()})
        self.assertEqual(result, {'query': 'example', 'results': []})

    def test_empty_valid_results_are_distinct_from_provider_failure(self):
        checked = []
        result = self.check(transport=lambda url, body, *args: {'query': body['query'], 'results': []},
                            compare=lambda hits: (checked.append(hits) is None, []))
        self.assertTrue(result['passed'])
        self.assertEqual(checked, [[]])
        self.assertEqual(result['evidence_urls'], [])

    def test_reservation_is_checkpointed_before_transport_and_failure_stops_network(self):
        observations = []
        def checkpoint():
            with closing(sqlite3.connect(self.path)) as db:
                observations.append(db.execute('SELECT count(*) FROM requests').fetchone()[0])
            if not self.calls:
                raise RuntimeError('git unavailable')
        with patch('fluxixo_ai.state_checkpoint.checkpoint', side_effect=checkpoint):
            with self.assertRaises(SearchDeferred) as cm:
                self.check()
        self.assertEqual(cm.exception.code, 'search_checkpoint_unavailable')
        self.assertEqual(observations[0], 1)
        self.assertEqual(self.calls, [])

    def test_comparison_failure_is_deferred_not_cached_as_passed(self):
        with self.assertRaises(SearchDeferred):
            self.check(compare=lambda _: (_ for _ in ()).throw(RuntimeError('private quote')))
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM checks WHERE verdict IS NOT NULL').fetchone()[0], 0)

    def test_exact_verdict_expires_after_thirty_days(self):
        self.check()
        self.now += 29 * 86400
        self.assertTrue(self.check()['cache_hit'])
        self.now += 2 * 86400
        self.assertFalse(self.check()['cache_hit'])
        self.assertEqual(len(self.calls), 2)

    def test_capacity_preflight_does_not_create_missing_database_or_contact_provider(self):
        path = Path(self.tmp.name) / 'not-created' / 'search.sqlite3'
        with (patch('fluxixo_ai.free_search._post_json', side_effect=AssertionError('no HTTP')),
              patch('fluxixo_ai.state_checkpoint.checkpoint', side_effect=AssertionError('no checkpoint'))):
            self.assertIsNone(require_search_capacity(db_path=path, now=self.now))
        self.assertFalse(path.parent.exists())

    def test_capacity_preflight_reads_without_reserving_or_modifying_database(self):
        self.check()
        before = self.path.read_bytes()
        for _ in range(3):
            self.assertIsNone(require_search_capacity(db_path=self.path, now=self.now + 1))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.calls), 1)

    def test_capacity_preflight_honors_rolling_limit_and_does_not_prune_old_rows(self):
        for index in range(36):
            self.check(f'Product description for capacity test {index}')
        before = self.path.read_bytes()
        with self.assertRaises(SearchDeferred) as cm:
            require_search_capacity(db_path=self.path, now=self.now + 1)
        self.assertEqual(cm.exception.code, 'search_daily_budget')
        self.assertAlmostEqual(cm.exception.retry_at, self.now + 86400.01)
        self.assertIsNone(require_search_capacity(db_path=self.path, now=self.now + 86401))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.calls), 36)

    def test_capacity_preflight_honors_shared_provider_backoff(self):
        def limited(url, *args):
            raise HTTPError(url, 429, 'limit', {'Retry-After': '120'}, None)
        with self.assertRaises(SearchDeferred):
            self.check(transport=limited)
        before = self.path.read_bytes()
        with self.assertRaises(SearchDeferred) as cm:
            require_search_capacity(db_path=self.path, now=self.now + 1)
        self.assertEqual(cm.exception.code, 'search_http_429')
        self.assertEqual(cm.exception.retry_at, self.now + 120)
        self.assertIsNone(require_search_capacity(db_path=self.path, now=self.now + 121))
        self.assertEqual(self.path.read_bytes(), before)

    def test_capacity_preflight_cannot_reset_corrupt_existing_budget(self):
        self.path.write_bytes(b'broken existing budget')
        with self.assertRaises(SearchDeferred) as cm:
            require_search_capacity(db_path=self.path, now=self.now)
        self.assertEqual(cm.exception.code, 'search_budget_unavailable')
        self.assertEqual(self.path.read_bytes(), b'broken existing budget')

    def test_tavily_stripped_outer_quotes_query_is_accepted(self):
        result = self.check(
            text='Full original product description for quote normalization check.',
            query='"exact quoted phrase query"',
            transport=lambda url, body, *args: {'query': 'exact quoted phrase query', 'results': [self.hit], 'request_id': 'live-shape'},
        )
        self.assertTrue(result['passed'])
        self.assertEqual(result['evidence_urls'], ['https://example.org/item'])


if __name__ == '__main__':
    unittest.main()
