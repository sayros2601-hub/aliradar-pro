import tempfile
import unittest
from pathlib import Path

from fluxixo_ai.pending_products import PendingProducts


class PendingProductsTests(unittest.TestCase):
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
