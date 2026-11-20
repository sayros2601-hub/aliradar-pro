import tempfile
import unittest
from pathlib import Path
import sqlite3
from contextlib import closing
from unittest.mock import patch

from fluxixo_ai.pending_products import PendingProducts


class PendingProductsTests(unittest.TestCase):
    def test_terminal_products_survive_restart_and_never_autoclaim(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pending.sqlite3'
            q = PendingProducts(path)
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            q.put({'product_id': '2', 'title': 'two'}, now=10)
            q.park('1', 'media_attempts_exhausted', source_version='a' * 64, kind='media', now=11)
            q = PendingProducts(path)
            self.assertEqual(q.parked_candidate('1')['title'], 'one')
            self.assertIsNone(q.parked_candidate('2'))
            q.defer('1', 'temporary', retry_at=20, now=12)
            q.hold('1', now=13)
            q.put({'product_id': '1', 'title': 'new title', 'image_url': 'https://ae01.alicdn.com/new.jpg'}, now=14)
            self.assertFalse(q.is_due('1', now=1000000))
            self.assertEqual(q.claim(now=1000000)['product_id'], '2')
            self.assertIsNone(q.claim(now=1000001))
            self.assertEqual(q.terminal_info('1'), {
                'kind': 'media', 'reason': 'media_attempts_exhausted', 'source_version': 'a' * 64})
            self.assertIn('1', [p['sourceProductId'] for p in q.exclusions()])

    def test_only_unseen_verified_source_reopens_without_erasing_history_or_attempts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pending.sqlite3'
            q = PendingProducts(path)
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            q.claim(now=11)
            q.save_copy_state('1', {'versions': {'old': {'attempts': 3}}}, now=12)
            q.park('1', 'copy_attempts_exhausted', source_version='a' * 64, kind='copy', now=13)
            self.assertFalse(q.reconsider('1', source_version='a' * 64, now=14))
            self.assertTrue(q.reconsider('1', source_version='b' * 64, now=15))
            self.assertIsNone(q.terminal_info('1'))
            self.assertEqual(q.claim(now=16)['product_id'], '1')
            q.park('1', 'copy_attempts_exhausted', source_version='b' * 64, kind='copy', now=17)
            q = PendingProducts(path)
            self.assertFalse(q.reconsider('1', source_version='a' * 64, now=18))
            self.assertFalse(q.reconsider('1', source_version='b' * 64, now=18))
            self.assertEqual(q.copy_state('1'), {'versions': {'old': {'attempts': 3}}})
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT attempts FROM pending WHERE product_id=?', ('1',)).fetchone()[0], 2)

    def test_source_histories_are_scoped_by_failure_kind(self):
        with tempfile.TemporaryDirectory() as folder:
            q = PendingProducts(Path(folder) / 'pending.sqlite3')
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            q.park('1', 'copy_exhausted', source_version='a' * 64, kind='copy', now=11)
            self.assertTrue(q.reconsider('1', source_version='b' * 64, now=12))
            q.park('1', 'media_exhausted', source_version='c' * 64, kind='media', now=13)
            self.assertTrue(q.reconsider('1', source_version='a' * 64, now=14))
            q.park('1', 'copy_exhausted', source_version='b' * 64, kind='copy', now=15)
            self.assertFalse(q.reconsider('1', source_version='a' * 64, now=16))

    def test_copy_journal_survives_source_changes_and_completed_row_reconciliation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pending.sqlite3'
            q = PendingProducts(path)
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            self.assertEqual(q.copy_state('1'), {})
            state = {'versions': {'first': {'attempts': 2, 'draft': 'saved text'}}}
            with patch('fluxixo_ai.state_checkpoint.checkpoint') as checkpoint:
                q.save_copy_state('1', state, now=11)
                checkpoint.assert_called_once_with()
            q.put({'product_id': '1', 'title': 'changed'}, now=12)
            q.reconcile([{'sourceProductId': '1'}])
            q = PendingProducts(path)
            self.assertEqual(q.copy_state('1'), state)
            q.put({'product_id': '1', 'title': 'one'}, now=13)
            q.complete('1')
            self.assertEqual(q.copy_state('1'), state)

    def test_terminal_history_remains_excluded_after_row_reconciliation(self):
        with tempfile.TemporaryDirectory() as folder:
            q = PendingProducts(Path(folder) / 'pending.sqlite3')
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            q.park('1', 'media_exhausted', source_version='a' * 64, kind='media', now=11)
            q.reconcile([{'sourceProductId': '1'}])
            self.assertFalse(q.is_due('1', now=10000))
            self.assertIn('1', [p['sourceProductId'] for p in q.exclusions()])
            q.put({'product_id': '1', 'title': 'one'}, now=12)
            self.assertFalse(q.reconsider('1', source_version='a' * 64, now=13))

    def test_source_reconsideration_rejects_urls_or_missing_verified_version(self):
        with tempfile.TemporaryDirectory() as folder:
            q = PendingProducts(Path(folder) / 'pending.sqlite3')
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            for version in ('', 'https://ae01.alicdn.com/new.jpg', None):
                with self.subTest(version=version), self.assertRaises(ValueError):
                    q.park('1', 'media_exhausted', source_version=version, kind='media', now=11)
            q.park('1', 'media_exhausted', source_version='a' * 64, kind='media', now=12)
            with self.assertRaises(ValueError):
                q.reconsider('1', source_version='https://ae01.alicdn.com/new.jpg', now=13)
            self.assertFalse(q.is_due('1', now=10000))

    def test_expired_lease_recovers_and_deferred_item_does_not_starve_others(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'pending.sqlite3'
            q = PendingProducts(db)
            q.put({'product_id': '1', 'title': 'one'}, now=100)
            q.put({'product_id': '2', 'title': 'two'}, now=101)
            first = q.claim(now=102, lease=10)
            self.assertEqual(first['product_id'], '1')
            q.defer('1', 'quota', retry_at=200, now=103)
            self.assertEqual(q.claim(now=104, lease=10)['product_id'], '2')
            self.assertIsNone(q.claim(now=105))
            q = PendingProducts(db)
            self.assertEqual(q.claim(now=115)['product_id'], '2')
            q.complete('2')
            self.assertEqual(q.claim(now=201)['product_id'], '1')

    def test_idempotent_upsert_preserves_cache_and_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            q = PendingProducts(Path(folder) / 'pending.sqlite3')
            candidate = {'product_id': '1', 'title': 'one', 'image_url': 'https://ae01.alicdn.com/a.jpg'}
            q.put(candidate, now=10)
            q.save_text('1', {'ru': {'name': 'name'}}, now=11)
            q.defer('1', 'review_unavailable', retry_at=100, now=12)
            self.assertEqual(q.exclusions()[0]['sourceProductId'], '1')
            self.assertFalse(q.is_due('1', now=20))
            self.assertTrue(q.is_due('1', now=100))
            q.put(candidate, now=20)
            self.assertIsNone(q.claim(now=30))
            self.assertEqual(q.text('1'), {'ru': {'name': 'name'}})
            candidate['title'] = 'different'
            q.put(candidate, now=40)
            self.assertIsNone(q.text('1'))

    def test_catalog_reconciliation_removes_crash_after_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            q = PendingProducts(Path(folder) / 'pending.sqlite3')
            q.put({'product_id': '1', 'title': 'one'}, now=10)
            q.reconcile([{'sourceProductId': '1'}])
            self.assertIsNone(q.claim(now=20))
