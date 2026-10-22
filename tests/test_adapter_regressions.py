"""Offline regressions found when accepting the returned adapter."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from dealvault_adapter import DealVaultAdapter, parse_observation_record
from inbox_store import queue_lock


class AdapterRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inbox, self.data = self.root/'inbox', self.root/'data'
        self.inbox.mkdir(); self.data.mkdir()
        self.adapter = DealVaultAdapter(self.inbox, self.data)
        self.row = {'raw_title':'Synthetic record', 'item_id':'1005000000001',
                    'original_affiliate_url':'https://s.click.aliexpress.com/e/_Synthetic?aff_trace=A%2BB',
                    'country':'US', 'currency':'USD', 'observed_at':'2026-01-01T00:00:00Z'}

    def put(self, value, name='input.json'):
        (self.inbox/name).write_text(json.dumps(value), encoding='utf-8')
        return name

    def test_scalar_roots_and_wrong_nested_types_are_errors(self):
        for value in [None, 7, True, 'text', {'records':None}, [{'text':12}], [{**self.row,'modal':[]}], [{**self.row,'fields':'bad'}]]:
            with self.subTest(value=value):
                result=self.adapter.validate_import(self.put(value))
                self.assertNotEqual(result['status'],'OK')

    def test_null_optional_objects_do_not_crash_and_observation_time_not_fabricated(self):
        value={**self.row,'modal':None,'offer':None,'observed_at':None}
        result=self.adapter.validate_import(self.put([value]))
        self.assertEqual(result['status'],'OK')
        self.assertIsNone(result['valid_observations'][0]['observed_at'])

    def test_schema_types_and_bad_times_cannot_claim_validity(self):
        for changes in [{'observed_at':'bad'},{'observed_at':'2039-01-01T00:00:00Z'},
                        {'observed_at':'2026-01-01'},{'source_kind':'invented'}, {'evidence':{}},
                        {'fields':{'rating':float('nan')}}, {'fields':{'in_stock':'yes'}}, {'item_id':True}]:
            _, errors=parse_observation_record({**self.row,**changes},'2026-01-02T00:00:00Z')
            self.assertTrue(errors,changes)

    def test_corrupt_queue_is_not_overwritten(self):
        name=self.put([self.row]); queue=self.data/'portals_inbox.json'
        for raw in [b'{broken',b'{}',b'[null]',b'[{"affiliate_url":"invalid"}]']:
            queue.write_bytes(raw)
            result=self.adapter.stage_import(name)
            self.assertEqual(result['status'],'FAILED')
            self.assertEqual(queue.read_bytes(),raw)

    def test_fresh_observation_kept_while_exact_repeat_is_idempotent(self):
        name=self.put([self.row]); self.assertEqual(self.adapter.stage_import(name)['staged_count'],1)
        self.assertEqual(self.adapter.stage_import(name)['staged_count'],0)
        name=self.put([{**self.row,'observed_at':'2026-01-02T00:00:00Z','fields':{'item_price':12}}])
        self.assertEqual(self.adapter.stage_import(name)['staged_count'],1)
        rows=json.loads((self.data/'portals_inbox.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['fields']['item_price'],12)
        self.assertEqual(rows[1]['affiliate_url'],self.row['original_affiliate_url'])
        self.assertFalse(rows[1]['reviewed'])

    def test_both_importers_share_queue_format_without_network(self):
        import import_portals
        self.adapter.stage_import(self.put([self.row]))
        with patch.object(import_portals,'DATA_DIR',self.data):
            (self.data/'products.json').write_text('{"products":[]}',encoding='utf-8')
            import_portals.stage_records([])
        self.assertEqual(len(json.loads((self.data/'portals_inbox.json').read_text(encoding='utf-8'))),1)

    def test_text_link_preserves_query_and_conflicting_links_are_rejected(self):
        value={**self.row,'text':'Observed: '+self.row['original_affiliate_url']}
        del value['original_affiliate_url']
        row,errors=parse_observation_record(value,'2026-01-02T00:00:00Z')
        self.assertFalse(errors);self.assertEqual(row['original_affiliate_url'],self.row['original_affiliate_url'])
        _,errors=parse_observation_record({**self.row,'affiliate_url':'https://s.click.aliexpress.com/e/_Different'},'2026-01-02T00:00:00Z')
        self.assertTrue(errors)

    def test_status_is_read_only_and_only_implemented_capabilities_are_enabled(self):
        empty=self.root/'absent'
        bridge=DealVaultAdapter(empty/'inbox',empty/'data')
        status=bridge.get_status()
        self.assertFalse(empty.exists())
        for key in ('check_session','local_harvest','financial_summary','live_api_search'):
            self.assertFalse(status['capabilities'][key])
        self.assertEqual(bridge.check_session()['status'],'POLICY_BLOCKED')

    def test_duplicate_json_keys_nan_directory_and_empty_wrapper(self):
        for raw in ['{"records":[],"records":[]}','[{"rating":NaN}]']:
            (self.inbox/'bad.json').write_text(raw,encoding='utf-8')
            self.assertEqual(self.adapter.validate_import('bad.json')['status'],'INVALID_INPUT')
        self.assertEqual(self.adapter.validate_import('.')['status'],'INVALID_INPUT')
        self.assertEqual(self.adapter.validate_import(self.put({'records':[]}))['summary']['total_records'],0)

    def test_partial_import_keeps_failure_visible_and_does_not_echo_raw_record(self):
        result=self.adapter.stage_import(self.put([self.row,{'text':123,'private':'do not echo'}]))
        self.assertEqual(result['status'],'PARTIAL')
        self.assertNotIn('do not echo',json.dumps(result))

    def test_overlapping_import_stops_without_replacing_queue(self):
        name=self.put([self.row])
        with queue_lock(self.data):
            result=self.adapter.stage_import(name)
        self.assertEqual(result['status'],'FAILED')
        self.assertFalse((self.data/'portals_inbox.json').exists())

    def test_atomic_write_failure_preserves_previous_queue(self):
        name=self.put([self.row]); queue=self.data/'portals_inbox.json';queue.write_text('[]',encoding='utf-8')
        with patch('dealvault_adapter.write_json',side_effect=OSError('simulated disk failure')):
            result=self.adapter.stage_import(name)
        self.assertEqual(result['status'],'FAILED');self.assertEqual(queue.read_text(),'[]')

    def test_legacy_capture_context_is_retained_without_verification(self):
        value={**self.row,'offer':{'item_price':12,'in_stock':True},'images':['https://example.invalid/photo.jpg']}
        row,errors=parse_observation_record(value,'2026-01-02T00:00:00Z')
        self.assertFalse(errors)
        self.assertEqual(row['fields']['source_offer'],value['offer'])
        self.assertEqual(row['fields']['source_images'],value['images'])
        self.assertEqual(row['review_status'],'pending')

    def test_corrupt_url_or_observation_id_is_structured_error(self):
        name=self.put([self.row]); queue=self.data/'portals_inbox.json'
        for value in [[{'affiliate_url':{'bad':1}}],[{'affiliate_url':self.row['original_affiliate_url'],'observation_id':{}}]]:
            queue.write_text(json.dumps(value),encoding='utf-8');before=queue.read_bytes()
            self.assertEqual(self.adapter.stage_import(name)['status'],'FAILED')
            self.assertEqual(queue.read_bytes(),before)

    def test_queue_size_limit_uses_actual_pretty_serialization(self):
        import inbox_store
        # A compact representation is below the cap, while pretty JSON exceeds it.
        rows=[{'affiliate_url':self.row['original_affiliate_url'],'fields':[0]*10}]
        compact=len(json.dumps(rows).encode('utf-8'))
        pretty=len((json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
        self.assertGreater(pretty,compact)
        with patch.object(inbox_store,'MAX_QUEUE_BYTES',compact+1):
            with self.assertRaises(ValueError):inbox_store.ensure_queue_size(rows)


if __name__=='__main__':unittest.main()
