"""Offline UTC daily cap and idempotency tests for the existing daily writer."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fluxixo_ai.daily_ledger import LedgerError, utc_day, read_ledger, remaining, record, atomic_write, verify_catalog, remaining_validation, record_validation

DAY = '2026-11-10'
VALIDATION_ID = 'fluxixo-validation-20261110-01'
VALIDATION_NOW = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)
SEED = Path(__file__).resolve().parents[1] / 'data/fluxixo_daily_ledger.json'


def api_item(number):
    return {'catalog_id': 'ai-' + str(number), 'product_id': str(number), 'source': 'api'}


class DailyLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ledger.json'

    def test_seed_uses_only_the_three_existing_ids_and_no_invented_marketplace_id(self):
        data = read_ledger(SEED)
        records = data['days'][DAY]
        self.assertEqual(['find-064-book-light', 'find-065-spice-grinder', 'find-067-pill-organizer'],
                         [row['catalog_id'] for row in records])
        self.assertTrue(all(row['product_id'] is None and row['source'] == 'github_actions'
                            and row['run_id'] == '42853498987' for row in records))
        self.assertEqual(0, remaining(data, DAY, 3))

    def test_utc_not_machine_local_time_and_reject_naive_datetime(self):
        israel = timezone(timedelta(hours=2))
        self.assertEqual('2026-11-09', utc_day(datetime(2026, 11, 10, 0, 30, tzinfo=israel)))
        with self.assertRaises(LedgerError): utc_day(datetime(2026, 11, 10))

    def test_missing_corrupt_and_duplicate_keys_never_reset_quota(self):
        with self.assertRaises(LedgerError): read_ledger(self.path)
        for raw in ('{bad json', '{"version":1,"version":1,"days":{}}', '{"version":1,"days":NaN}'):
            self.path.write_text(raw, encoding='utf-8')
            with self.subTest(raw=raw), self.assertRaises(LedgerError): read_ledger(self.path)

    def test_valid_json_with_seed_removed_cannot_reset_today(self):
        self.path.write_text('{"version":1,"days":{}}', encoding='utf-8')
        with self.assertRaises(LedgerError): read_ledger(self.path)
        data = read_ledger(SEED)
        atomic_write(self.path, data)
        before = self.path.read_bytes()
        with self.assertRaises(LedgerError): atomic_write(self.path, {'version': 1, 'days': {}})
        self.assertEqual(before, self.path.read_bytes())

    def test_record_is_atomic_pure_and_per_day_maximum_three(self):
        initial = {'version': 1, 'days': {}, 'validation_runs': {}}
        copy = deepcopy(initial)
        entries = [api_item(1), api_item(2), api_item(3)]
        updated = record(initial, DAY, entries)
        self.assertEqual(copy, initial)
        self.assertEqual(0, remaining(updated, DAY, 3))
        self.assertEqual(3, remaining(updated, '2026-11-11', 3))
        with self.assertRaises(LedgerError): record(updated, DAY, [api_item(4)])
        self.assertEqual(3, len(updated['days'][DAY]))

    def test_retry_same_record_is_idempotent_but_conflicts_fail(self):
        first = record({'version': 1, 'days': {}, 'validation_runs': {}}, DAY, [api_item(123)])
        self.assertEqual(first, record(first, DAY, [api_item(123)]))
        conflict = {'catalog_id': 'ai-123', 'product_id': '456', 'source': 'api'}
        with self.assertRaises(LedgerError): record(first, DAY, [conflict])
        with self.assertRaises(LedgerError): record(first, '2026-11-11', [api_item(123)])
        other_id_same_product = {'catalog_id': 'ai-alias', 'product_id': '123', 'source': 'api'}
        with self.assertRaises(LedgerError): record(first, '2026-11-11', [other_id_same_product])

    def test_no_add_does_not_consume_slot_and_requested_count_is_bounded(self):
        data = read_ledger(SEED)
        snapshot = deepcopy(data)
        self.assertEqual(0, remaining(data, '2026-11-11', 0))
        self.assertEqual(snapshot, data)
        for invalid in (-1, 4, True, '3'):
            with self.subTest(value=invalid), self.assertRaises(LedgerError): remaining(data, DAY, invalid)

    def test_corrupt_or_overfull_ledger_rejected_not_truncated(self):
        for invalid in ({'version': 2, 'days': {}, 'validation_runs': {}}, {'version': 1, 'days': {'2026-02-30': []}, 'validation_runs': {}},
                        {'version': 1, 'days': {DAY: [api_item(n) for n in range(4)]}, 'validation_runs': {}},
                        {'version': 1, 'days': {DAY: [api_item(1), api_item(1)]}, 'validation_runs': {}}):
            with self.subTest(data=invalid), self.assertRaises(LedgerError): remaining(invalid, DAY)

    def test_seed_catalog_must_really_contain_each_claimed_item(self):
        data = read_ledger(SEED)
        good = {'products': [{'id': row['catalog_id']} for row in data['days'][DAY]]}
        verify_catalog(data, good)
        good['products'].pop()
        with self.assertRaises(LedgerError) as error: verify_catalog(data, good)
        self.assertEqual('ledger_catalog_mismatch', error.exception.code)

    def test_failed_atomic_write_preserves_last_valid_ledger(self):
        baseline = read_ledger(SEED)
        atomic_write(self.path, baseline)
        before = self.path.read_bytes()
        next_ledger = record(baseline, '2026-11-11', [api_item(123)])
        with patch('fluxixo_ai.daily_ledger.os.replace', side_effect=OSError('fail')):
            with self.assertRaises(LedgerError): atomic_write(self.path, next_ledger)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(baseline, read_ledger(self.path))
        self.assertEqual([self.path], list(self.path.parent.iterdir()))

    def test_rejects_untrusted_fields_and_inconsistent_api_identity(self):
        initial = {'version': 1, 'days': {}, 'validation_runs': {}}
        for row in ({'catalog_id': '../bad', 'product_id': '123', 'source': 'api'},
                    {'catalog_id': 'ai-123', 'product_id': None, 'source': 'api'},
                    {'catalog_id': 'ai-123', 'product_id': '123', 'source': 'api', 'secret': 'not allowed'},
                    {'catalog_id': 'ai-123', 'product_id': '0123', 'source': 'api'}):
            with self.subTest(row=row), self.assertRaises(LedgerError): record(initial, DAY, [row])

    def test_one_explicit_validation_is_separate_audited_and_idempotent(self):
        original = read_ledger(SEED)
        self.assertEqual(0, remaining(original, DAY))
        self.assertEqual(1, remaining_validation(original, DAY, VALIDATION_ID, now=VALIDATION_NOW))
        new = record_validation(original, DAY, VALIDATION_ID, api_item(123), now=VALIDATION_NOW)
        self.assertEqual({}, original['validation_runs'])
        self.assertEqual(0, remaining_validation(new, DAY, VALIDATION_ID, now=VALIDATION_NOW))
        self.assertEqual(0, remaining(new, DAY))
        self.assertEqual(3, remaining(new, '2026-11-11'))
        self.assertEqual({'day': DAY, **api_item(123)}, new['validation_runs'][VALIDATION_ID])
        self.assertEqual(new, record_validation(new, DAY, VALIDATION_ID, api_item(123), now=VALIDATION_NOW))
        with self.assertRaises(LedgerError): record_validation(new, DAY, VALIDATION_ID, api_item(456), now=VALIDATION_NOW)

    def test_validation_cannot_run_on_another_day_or_under_another_id(self):
        ledger = read_ledger(SEED)
        for day, run_id in (('2026-11-11', VALIDATION_ID), (DAY, 'another-validation'), ('2026-11-09', VALIDATION_ID)):
            with self.subTest(day=day, run_id=run_id):
                with self.assertRaises(LedgerError): remaining_validation(ledger, day, run_id, now=VALIDATION_NOW)
                with self.assertRaises(LedgerError): record_validation(ledger, day, run_id, api_item(123), now=VALIDATION_NOW)

    def test_validation_day_cannot_be_backdated_after_utc_midnight(self):
        ledger = read_ledger(SEED)
        tomorrow = datetime(2026, 11, 11, 0, 0, 1, tzinfo=timezone.utc)
        with self.assertRaises(LedgerError): remaining_validation(ledger, DAY, VALIDATION_ID, now=tomorrow)
        with self.assertRaises(LedgerError): record_validation(ledger, DAY, VALIDATION_ID, api_item(123), now=tomorrow)

    def test_completed_validation_is_idempotently_readable_after_midnight(self):
        original = read_ledger(SEED)
        done = record_validation(original, DAY, VALIDATION_ID, api_item(123), now=VALIDATION_NOW)
        tomorrow = datetime(2026, 11, 11, 0, 0, 1, tzinfo=timezone.utc)
        self.assertEqual(0, remaining_validation(done, DAY, VALIDATION_ID, now=tomorrow))
        self.assertEqual(done, record_validation(done, DAY, VALIDATION_ID, api_item(123), now=tomorrow))
        with self.assertRaises(LedgerError): record_validation(done, DAY, VALIDATION_ID, api_item(456), now=tomorrow)

    def test_validation_item_and_normal_items_cannot_duplicate_each_other(self):
        ledger = read_ledger(SEED)
        normal = record(ledger, '2026-11-11', [api_item(123)])
        with self.assertRaises(LedgerError): record_validation(normal, DAY, VALIDATION_ID, api_item(123), now=VALIDATION_NOW)
        trial = record_validation(ledger, DAY, VALIDATION_ID, api_item(456), now=VALIDATION_NOW)
        with self.assertRaises(LedgerError): record(trial, '2026-11-11', [api_item(456)])

    def test_validation_record_must_exist_in_catalog_with_exact_product_id(self):
        ledger = record_validation(read_ledger(SEED), DAY, VALIDATION_ID, api_item(123), now=VALIDATION_NOW)
        catalog = {'products': [{'id': item['catalog_id']} for item in ledger['days'][DAY]]}
        with self.assertRaises(LedgerError): verify_catalog(ledger, catalog)
        catalog['products'].append({'id': 'ai-123', 'sourceProductId': '123'})
        verify_catalog(ledger, catalog)
        catalog['products'][-1]['sourceProductId'] = '999'
        with self.assertRaises(LedgerError): verify_catalog(ledger, catalog)


if __name__ == '__main__': unittest.main()
