"""Synthetic-only tests for the legacy offline Portals importer."""
import copy
from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import import_portals as importer
from dealvault_core import read_json, write_json


class OfflinePortalsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        self.queue = self.data / 'portals_inbox.json'
        self.catalog = self.data / 'products.json'
        write_json(self.catalog, {'products': [
            {'affiliate_url': 'https://s.click.aliexpress.com/e/_existing?track=original'}
        ]})
        self.original_catalog = self.catalog.read_bytes()
        self.patch_data = patch.object(importer, 'DATA_DIR', self.data)
        self.patch_data.start()
        self.addCleanup(self.patch_data.stop)
        # Every test, including CLI entry-point tests, forbids real networking.
        for name in ('socket.socket', 'socket.create_connection', 'urllib.request.urlopen'):
            guard = patch(name, side_effect=AssertionError('Network is forbidden in offline imports'))
            guard.start()
            self.addCleanup(guard.stop)

    def record(self, key='new', **fields):
        return {
            'raw_title': 'Synthetic desk cable organizer',
            'affiliate_url': f'https://s.click.aliexpress.com/e/_{key}?tag=keep%2Fthis&x=1#details',
            **fields,
        }

    def test_default_is_offline_and_catalog_untouched(self):
        added = importer.stage_records([self.record(item_id='1005001234567')])
        self.assertEqual(added[0]['destination_check'], {
            'status': 'UNCHECKED_OFFLINE', 'item_id': '1005001234567'})
        self.assertEqual(self.catalog.read_bytes(), self.original_catalog)
        self.assertEqual(read_json(self.queue), added)

    def test_check_links_requires_explicit_checker_before_any_file_access(self):
        with patch.object(importer, 'queue_lock') as lock, patch.object(importer, 'read_json') as read:
            for checker in (None, True, 'network', {}):
                with self.subTest(checker=checker), self.assertRaises(ValueError):
                    importer.stage_records([self.record()], check_links=True, link_checker=checker)
            lock.assert_not_called()
            read.assert_not_called()
        self.assertFalse(self.queue.exists())

    def test_offline_default_never_uses_an_accidentally_supplied_checker(self):
        checker = Mock(side_effect=AssertionError('Unexpected checker call'))
        importer.stage_records([self.record()], link_checker=checker)
        checker.assert_not_called()

    def test_explicit_offline_evidence_checker_is_supported(self):
        checker = Mock(return_value={'status': 'SAVED_EVIDENCE_ONLY', 'item_id': '1005002222222'})
        added = importer.stage_records([self.record()], check_links=True, link_checker=checker)
        checker.assert_called_once()
        self.assertEqual(added[0]['item_id'], '1005002222222')
        self.assertFalse(added[0]['reviewed'])
        self.assertEqual(added[0]['status'], 'pending')

    def test_cli_default_and_legacy_offline_option_both_use_no_network(self):
        for index, options in enumerate(([], ['--offline'])):
            source = self.data / f'capture-{index}.json'
            write_json(source, [self.record(key=f'cli{index}')])
            self.assertEqual(importer.main([str(source), *options]), 0)
        self.assertEqual(len(read_json(self.queue)), 2)

    def test_cli_rejects_link_check_before_reading_a_capture(self):
        with patch.object(importer, 'read_json') as read, patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                importer.main([str(self.data / 'absent.json'), '--check-links'])
            self.assertEqual(result.exception.code, 2)
            read.assert_not_called()

    def test_mixed_queue_preserved_and_deduplicated_by_affiliate_key(self):
        previous = [
            {'original_affiliate_url': 'https://s.click.aliexpress.com/e/_envelope?a=old',
             'observation_id': 'saved-observation', 'fields': {'price': None}},
            {'affiliate_url': 'https://s.click.aliexpress.com/e/_legacy?b=old',
             'raw_title': 'Saved legacy record', 'custom_user_note': 'Keep exactly'},
        ]
        write_json(self.queue, previous)
        records = [self.record(key=key) for key in ('existing', 'envelope', 'legacy', 'new')]
        added = importer.stage_records(records)
        self.assertEqual(len(added), 1)
        self.assertEqual(read_json(self.queue)[:2], previous)
        original_queue = self.queue.read_bytes()
        self.assertEqual(importer.stage_records(records), [])
        self.assertEqual(self.queue.read_bytes(), original_queue)

    def test_corrupt_existing_queue_is_never_reset_or_overwritten(self):
        malformed = [
            b'{not-json', b'{}', b'null', b'[null]', b'[42]', b'[{}]',
            b'[{"affiliate_url":"https://example.invalid/not-portals"}]',
            b'[{"original_affiliate_url":[]}]',
            b'[{"original_affiliate_url":["bad"]}]',
            b'[{"affiliate_url":{"value":"bad"}}]',
            b'[{"affiliate_url":"https://s.click.aliexpress.com/e/_a", "affiliate_url":"https://s.click.aliexpress.com/e/_b"}]',
            b'[{"affiliate_url":"https://s.click.aliexpress.com/e/_a", "original_affiliate_url":"https://s.click.aliexpress.com/e/_b"}]',
            b'[{"affiliate_url":"https://s.click.aliexpress.com/e/_a", "price":NaN}]',
            b'\xff\xfeinvalid',
        ]
        for content in malformed:
            with self.subTest(content=content):
                self.queue.write_bytes(content)
                with self.assertRaises((ValueError, UnicodeError, OSError)):
                    importer.stage_records([self.record()])
                self.assertEqual(self.queue.read_bytes(), content)

    def test_malformed_catalog_does_not_change_existing_queue(self):
        write_json(self.queue, [self.record(key='saved')])
        original_queue = self.queue.read_bytes()
        for db in ([], {}, {'products': {}}, {'products': [None]}, {'products': [{}]}):
            with self.subTest(db=db):
                write_json(self.catalog, db)
                with self.assertRaises(ValueError):
                    importer.stage_records([self.record()])
                self.assertEqual(self.queue.read_bytes(), original_queue)

    def test_wrong_record_and_nested_types_are_skipped_or_left_unknown(self):
        candidate = self.record(
            modal=['invalid'], text={'invalid': 'text'}, images=5,
            observed_at=[], category=[], query={}, target_country=False,
            selection=[], offer='invalid', ad_review=None, editorial=8,
            evidence={}, fields=[], missing_fields=7, item_id=True)
        added = importer.stage_records([None, 5, [], 'invalid', {}, candidate])
        self.assertEqual(len(added), 1)
        item = added[0]
        for field in ('observed_at', 'captured_at', 'category', 'query', 'target_country', 'currency', 'item_id'):
            self.assertIsNone(item[field])
        for field in ('selection', 'offer', 'ad_review', 'editorial', 'fields'):
            self.assertEqual(item[field], {})
        self.assertEqual(item['images'], [])
        self.assertEqual(item['evidence'], [])

    def test_captured_time_is_never_fabricated_from_import_time(self):
        observed = '2025-01-15T08:00:00Z'
        with patch.object(importer, 'utc_now', return_value='2026-10-22T08:00:00+00:00'):
            added = importer.stage_records([
                self.record(key='old', observed_at=observed),
                self.record(key='undated', captured_at='2026-10-22T08:00:00Z'),
            ])
        self.assertEqual(added[0]['observed_at'], observed)
        self.assertEqual(added[0]['captured_at'], observed)
        self.assertNotEqual(added[0]['imported_at'], observed)
        self.assertIsNone(added[1]['observed_at'])
        self.assertIsNone(added[1]['captured_at'])

    def test_input_cannot_promote_itself_to_reviewed_or_verified(self):
        record = self.record(source='verified', reviewed=True, status='approved', review_status='approved')
        before = copy.deepcopy(record)
        item = importer.stage_records([record])[0]
        self.assertEqual(record, before)
        self.assertEqual(item['source'], 'portals')
        self.assertFalse(item['reviewed'])
        self.assertEqual(item['status'], 'pending')
        self.assertEqual(item['review_status'], 'pending')

    def test_text_extraction_keeps_all_tracking_parameters(self):
        url = 'https://s.click.aliexpress.com/e/_fromText?aff_fsk=keep%2Bme&aff_trace_key=A%2FB#offer'
        item = importer.stage_records([{'modal': {'text': 'Captured item\nOrganizer\n' + url}}])[0]
        self.assertEqual(item['affiliate_url'], url)
        self.assertEqual(item['original_affiliate_url'], url)

    def test_original_url_has_precedence_and_is_preserved_exactly(self):
        url = 'https://s.click.aliexpress.com/e/_original?track=A%2Fb&extra=%25#anchor'
        item = importer.stage_records([self.record(original_affiliate_url=url)])[0]
        self.assertEqual(item['affiliate_url'], url)
        self.assertEqual(item['original_affiliate_url'], url)

    def test_invalid_explicit_urls_do_not_fall_back_to_text(self):
        invalid = [
            'https://s.click.aliexpress.com.attacker.invalid/e/_bad',
            'https://s.click.aliexpress.com/e/_bad/extra',
            'https://user@s.click.aliexpress.com/e/_bad',
            'http://s.click.aliexpress.com/e/_bad',
            'https://s.click.aliexpress.com:444/e/_bad',
            [], {}, 2,
        ]
        records = [self.record(original_affiliate_url=url, text='https://s.click.aliexpress.com/e/_fallback')
                   for url in invalid]
        self.assertEqual(importer.stage_records(records), [])
        self.assertFalse(self.queue.exists())

    def test_missing_actual_title_never_uses_a_search_query(self):
        self.assertEqual(importer.stage_records([
            self.record(raw_title=None, query='best popular organizer'),
            self.record(raw_title={}, text=['not', 'a', 'title']),
        ]), [])
        self.assertFalse(self.queue.exists())

    def test_checker_failure_preserves_entire_queue_without_partial_batch(self):
        write_json(self.queue, [self.record(key='saved')])
        before = self.queue.read_bytes()
        checker = Mock(side_effect=[{'status': 'SAVED_EVIDENCE_ONLY'}, RuntimeError('invalid evidence')])
        with self.assertRaises(RuntimeError):
            importer.stage_records([self.record(key='one'), self.record(key='two')],
                                   check_links=True, link_checker=checker)
        self.assertEqual(self.queue.read_bytes(), before)
        with self.assertRaises(ValueError):
            importer.stage_records([self.record()], check_links=True, link_checker=lambda item: None)
        self.assertEqual(self.queue.read_bytes(), before)

    def test_shared_lock_covers_queue_read_and_atomic_write(self):
        state = {'locked': False}

        @contextmanager
        def lock(path):
            self.assertEqual(path, self.data)
            state['locked'] = True
            try:
                yield
            finally:
                state['locked'] = False

        original_read = importer.read_queue

        def read(path):
            self.assertTrue(state['locked'])
            return original_read(path)

        def write(path, value):
            self.assertTrue(state['locked'])
            return write_json(path, value)

        with patch.object(importer, 'queue_lock', lock), patch.object(importer, 'read_queue', read), \
                patch.object(importer, 'write_json', write):
            importer.stage_records([self.record()])
        self.assertFalse(state['locked'])

    def test_atomic_replace_failure_preserves_old_queue_and_cleans_temp_file(self):
        write_json(self.queue, [self.record(key='saved')])
        original = self.queue.read_bytes()
        with patch('dealvault_core.os.replace', side_effect=OSError('synthetic disk error')):
            with self.assertRaises(OSError):
                importer.stage_records([self.record()])
        self.assertEqual(self.queue.read_bytes(), original)
        self.assertEqual(list(self.data.glob('portals_inbox.json.*.tmp')), [])

    def test_invalid_top_level_input_does_not_create_queue(self):
        for value in (None, {}, 'text', 42):
            with self.subTest(value=value), self.assertRaises(ValueError):
                importer.stage_records(value)
        self.assertFalse(self.queue.exists())


if __name__ == '__main__':
    unittest.main()
