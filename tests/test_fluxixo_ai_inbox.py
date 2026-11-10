"""Offline shared inbox: no AliExpress, GitHub or deployment requests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from fluxixo_ai.inbox import process_inbox
from tests.test_fluxixo_ai_store import candidate

NOW = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)


def request(request_id, operation, payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return {'request_id': request_id, 'operation': operation,
            'payload_sha256': hashlib.sha256(raw).hexdigest(), 'payload': payload}


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.requests = self.root / '.fluxixo-ai/requests'
        self.results = self.root / '.fluxixo-ai/results'
        self.requests.mkdir(parents=True)

    def put(self, data):
        (self.requests / (data['request_id'] + '.json')).write_text(json.dumps(data), encoding='utf-8')

    def result(self, request_id):
        return json.loads((self.results / (request_id + '.json')).read_text(encoding='utf-8'))

    def test_search_uses_exact_payload_binding_and_never_initializes_store(self):
        req = request('a' * 32, 'search', {'query': 'lamp', 'markets': ['BR'], 'limit': 3})
        self.put(req)
        calls = []
        def handler(op, payload, identifier, call, store, load_search, **kwargs):
            calls.append((op, payload, identifier, store))
            return {'considered_count': 0, 'candidates': []}
        summary = process_inbox(self.root, handler=handler, now=NOW)
        self.assertEqual(1, summary['processed'])
        self.assertEqual('complete', self.result(req['request_id'])['status'])
        self.assertEqual(req['payload_sha256'], self.result(req['request_id'])['payload_sha256'])
        self.assertEqual([('search', req['payload'], req['request_id'], None)], calls)
        self.assertFalse((self.root / 'data/fluxixo_ai.sqlite3').exists())

    def test_all_pending_requests_and_dependencies_are_processed_not_only_head(self):
        search = request('f' * 32, 'search', {'query': 'lamp', 'markets': ['BR']})
        queue = request('1' * 32, 'queue', {'search_id': search['request_id'], 'selections': []})
        second = request('2' * 32, 'search', {'query': 'mirror', 'markets': ['US']})
        for item in (queue, search, second): self.put(item)
        events = []
        def handler(op, payload, identifier, call, store, load_search, **kwargs):
            events.append(op)
            if op == 'queue':
                self.assertEqual(search['request_id'], load_search(payload['search_id'])['request_id'])
            return {'seen': identifier}
        summary = process_inbox(self.root, handler=handler, now=NOW)
        self.assertEqual(3, summary['processed'])
        self.assertEqual(['search', 'search', 'queue'], events)
        self.assertEqual('complete', self.result(queue['request_id'])['status'])

    def test_existing_success_never_overwritten_on_same_id_changed_payload(self):
        identifier = 'a' * 32
        old = request(identifier, 'search', {'query': 'lamp', 'markets': ['BR']})
        self.put(old)
        process_inbox(self.root, handler=lambda *a, **k: {'value': 'old'}, now=NOW)
        before = (self.results / (identifier + '.json')).read_bytes()
        self.put(request(identifier, 'search', {'query': 'mirror', 'markets': ['BR']}))
        summary = process_inbox(self.root, handler=lambda *a, **k: self.fail('must not run'), now=NOW)
        self.assertEqual(1, summary['conflicts'])
        self.assertEqual(before, (self.results / (identifier + '.json')).read_bytes())

    def test_bad_digest_and_duplicate_json_keys_do_not_call_provider(self):
        identifier = 'a' * 32
        data = request(identifier, 'search', {'query': 'lamp'})
        data['payload_sha256'] = '0' * 64
        self.put(data)
        process_inbox(self.root, handler=lambda *a, **k: self.fail('must not run'), now=NOW)
        self.assertEqual('failed', self.result(identifier)['status'])
        self.assertEqual('request_binding_invalid', self.result(identifier)['error'])
        other = 'b' * 32
        (self.requests / (other + '.json')).write_text('{"request_id":"' + other + '","request_id":"' + other + '"}', encoding='utf-8')
        process_inbox(self.root, handler=lambda *a, **k: self.fail('must not run'), now=NOW)
        self.assertEqual('failed', self.result(other)['status'])

    def test_failure_after_queue_mutation_exposes_partial_state_without_details(self):
        identifier = 'b' * 32
        self.put(request(identifier, 'queue', {'search_id': 'a' * 32, 'selections': []}))
        def handler(op, payload, rid, call, store, load_search, **kwargs):
            store.enqueue(rid + ':one', candidate(), now=NOW)
            raise RuntimeError('provider secret or request detail')
        process_inbox(self.root, handler=handler, now=NOW)
        result = self.result(identifier)
        self.assertEqual('partial', result['status'])
        self.assertEqual('queued', result['partial_queue'][0]['state'])
        self.assertNotIn('provider secret', json.dumps(result))

    def test_oversized_request_and_unknown_operation_fail_without_api(self):
        data = request('c' * 32, 'search', {'query': 'a' * 30000})
        self.put(data)
        other = request('d' * 32, 'deploy', {})
        self.put(other)
        process_inbox(self.root, handler=lambda *a, **k: self.fail('must not run'), now=NOW)
        self.assertEqual('failed', self.result(data['request_id'])['status'])
        self.assertEqual('failed', self.result(other['request_id'])['status'])

    def test_second_run_is_idempotent_and_unrelated_files_are_ignored(self):
        data = request('a' * 32, 'search', {'query': 'lamp'})
        self.put(data)
        (self.requests / 'NOT-A-REQUEST.json').write_text('{}', encoding='utf-8')
        process_inbox(self.root, handler=lambda *a, **k: {'value': 'done'}, now=NOW)
        summary = process_inbox(self.root, handler=lambda *a, **k: self.fail('must not rerun'), now=NOW)
        self.assertEqual(0, summary['processed'])
        self.assertEqual(0, summary['conflicts'])


if __name__ == '__main__': unittest.main()
