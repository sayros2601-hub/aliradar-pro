"""Offline tests for the shared catalog queue. Never calls AliExpress or GitHub."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from fluxixo_ai.store import Store, StoreError

NOW = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)
DAY = '2026-11-10'
SHA = 'a' * 40


def candidate(product_id='12345678901'):
    return {
        'product_id': product_id,
        'detail_url': f'https://www.aliexpress.com/item/{product_id}.html',
        'title': 'Seller title from the API',
        'evidence': {'method': 'aliexpress.affiliate.product.query', 'product_id': product_id},
        'content': {language: {'name': 'Product title', 'headline': ['Product'],
                               'description': 'See the seller listing.'}
                    for language in ('ru', 'en', 'pt', 'es', 'fr', 'he')},
    }


class SharedStoreTests(unittest.TestCase):
    def test_same_explicit_model_across_distinct_items_is_not_added_twice(self):
        one={**candidate('12345678901'),'model_key':'brand\x1fmodel-x'}
        two={**candidate('12345678902'),'model_key':'brand\x1fmodel-x'}
        self.store.enqueue('model-one',one,now=NOW)
        with self.assertRaises(StoreError) as error:self.store.enqueue('model-two',two,now=NOW)
        self.assertEqual(error.exception.code,'duplicate_model')
        self.store.enqueue('model-other-brand',{**two,'model_key':'other-brand\x1fmodel-x'},now=NOW)
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.sqlite3'
        self.store = Store(self.path)

    def add(self, n):
        return self.store.enqueue(f'request-{n}', candidate(str(12345678901 + n)), now=NOW)

    def test_idempotent_replay_and_request_collision(self):
        first = self.add(0)
        self.assertEqual('queued', first['state'])
        self.assertEqual(first, self.add(0))
        with self.assertRaises(StoreError) as error:
            self.store.enqueue('request-0', candidate('12345678902'), now=NOW)
        self.assertEqual('idempotency_conflict', error.exception.code)

    def test_duplicate_marketplace_id_cannot_be_queued_under_another_request(self):
        self.add(0)
        with self.assertRaises(StoreError) as error:
            self.store.enqueue('other-request', candidate(), now=NOW)
        self.assertEqual('duplicate_product', error.exception.code)

    def test_supported_product_id_is_not_a_size_or_rarity_score(self):
        for index, pid in enumerate(('1', '12345678901234567890123456789012')):
            with self.subTest(pid=pid):
                result = self.store.enqueue(f'length-{index}', candidate(pid), now=NOW)
                self.assertEqual(pid, result['product_id'])

    def test_reject_missing_identity_mismatched_url_and_missing_translation(self):
        invalid = candidate()
        invalid['detail_url'] = 'https://www.aliexpress.com/item/98765432100.html'
        with self.assertRaises(StoreError):
            self.store.enqueue('bad-url', invalid, now=NOW)
        invalid = candidate()
        del invalid['content']['he']
        with self.assertRaises(StoreError):
            self.store.enqueue('bad-translation', invalid, now=NOW)
        invalid = candidate()
        invalid['evidence']['product_id'] = '98765432100'
        with self.assertRaises(StoreError):
            self.store.enqueue('bad-evidence', invalid, now=NOW)

    def test_parallel_submissions_cannot_duplicate_item(self):
        def worker(n):
            try:
                Store(self.path).enqueue(f'parallel-{n}', candidate(), now=NOW)
                return 'ok'
            except StoreError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(worker, range(20)))
        self.assertEqual(1, results.count('ok'))
        self.assertEqual(19, results.count('duplicate_product'))
        self.assertEqual(1, len(self.store.list_status()))

    def test_parallel_claimers_share_a_hard_daily_limit(self):
        for n in range(8):
            self.add(n)
        def worker(n):
            return Store(self.path).claim(DAY, f'worker-{n}', 3, now=NOW)
        with ThreadPoolExecutor(max_workers=6) as pool:
            claims = sum(pool.map(worker, range(6)), [])
        self.assertEqual(3, len(claims))
        self.assertEqual(3, len({entry['product_id'] for entry in claims}))
        self.assertEqual(3, len({entry['claim_id'] for entry in claims}))
        self.assertEqual([], self.store.claim(DAY, 'another', 3, now=NOW))

    def test_limit_counts_reserved_committed_published_and_failure(self):
        for n in range(4):
            self.add(n)
        claims = self.store.claim(DAY, 'runner', 3, now=NOW)
        self.store.mark_committed(claims[0]['claim_id'], 'runner', SHA, verified=True, now=NOW)
        self.store.mark_published(claims[0]['claim_id'], SHA, 'deployment-1', verified=True, now=NOW)
        self.store.fail(claims[1]['claim_id'], 'runner', 'safe-error-code', now=NOW)
        self.assertEqual([], self.store.claim(DAY, 'other', 1, now=NOW))
        self.assertEqual(1, len(self.store.claim('2026-11-11', 'tomorrow', 3, now=NOW + timedelta(days=1))))

    def test_publish_requires_verified_commit_and_verified_matching_deployment(self):
        self.add(0)
        claim = self.store.claim(DAY, 'runner', 1, now=NOW)[0]
        with self.assertRaises(StoreError):
            self.store.mark_committed(claim['claim_id'], 'runner', SHA, verified=False, now=NOW)
        with self.assertRaises(StoreError):
            self.store.mark_published(claim['claim_id'], SHA, 'deployment-1', verified=True, now=NOW)
        self.assertEqual('reserved', self.store.status('request-0')['state'])
        self.store.mark_committed(claim['claim_id'], 'runner', SHA, verified=True, now=NOW)
        with self.assertRaises(StoreError):
            self.store.mark_published(claim['claim_id'], 'b' * 40, 'deployment-1', verified=True, now=NOW)
        with self.assertRaises(StoreError):
            self.store.mark_published(claim['claim_id'], SHA, 'deployment-1', verified=False, now=NOW)
        published = self.store.mark_published(claim['claim_id'], SHA, 'deployment-1', verified=True, now=NOW)
        self.assertEqual('published', published['state'])
        self.assertEqual(published, self.store.mark_published(claim['claim_id'], SHA, 'deployment-1', verified=True, now=NOW))
        with self.assertRaises(StoreError):
            self.store.mark_published(claim['claim_id'], SHA, 'different-deployment', verified=True, now=NOW)

    def test_wrong_owner_cannot_mark_or_fail_claim(self):
        self.add(0)
        claim = self.store.claim(DAY, 'real-runner', 1, now=NOW)[0]
        with self.assertRaises(StoreError):
            self.store.mark_committed(claim['claim_id'], 'other-runner', SHA, verified=True, now=NOW)
        with self.assertRaises(StoreError):
            self.store.fail(claim['claim_id'], 'other-runner', 'safe-error-code', now=NOW)
        self.assertEqual('reserved', self.store.status('request-0')['state'])

    def test_stale_lease_is_not_blindly_requeued(self):
        self.add(0)
        claim = self.store.claim(DAY, 'runner', 1, lease_seconds=10, now=NOW)[0]
        later = NOW + timedelta(seconds=11)
        self.assertEqual([], self.store.claim(DAY, 'other', 1, now=later))
        with self.assertRaises(StoreError):
            self.store.mark_committed(claim['claim_id'], 'runner', SHA, verified=True, now=later)
        with self.assertRaises(StoreError):
            self.store.recover_claim(claim['claim_id'], 'other', '', False, now=later)
        recovered = self.store.recover_claim(claim['claim_id'], 'other', SHA, False, now=later)
        self.assertEqual(claim['claim_id'], recovered['claim_id'])
        self.assertEqual('reserved', recovered['state'])
        self.assertEqual('committed', self.store.mark_committed(claim['claim_id'], 'other', SHA, verified=True, now=later)['state'])

    def test_recover_already_committed_item_without_adding_again(self):
        self.add(0)
        claim = self.store.claim(DAY, 'crashed', 1, lease_seconds=10, now=NOW)[0]
        result = self.store.recover_claim(claim['claim_id'], 'replacement', SHA, True, now=NOW + timedelta(seconds=11))
        self.assertEqual('committed', result['state'])
        self.assertEqual(SHA, result['commit_sha'])
        self.assertEqual([], self.store.claim(DAY, 'replacement', 1, now=NOW + timedelta(seconds=11)))

    def test_day_cannot_be_forged_to_evade_limit(self):
        self.add(0)
        with self.assertRaises(StoreError):
            self.store.claim('2026-11-11', 'runner', 1, now=NOW)
        with self.assertRaises(StoreError):
            self.store.claim(DAY, 'runner', 4, now=NOW)

    def test_claim_cannot_outlive_the_utc_day(self):
        self.add(0)
        late = datetime(2026, 11, 10, 23, 59, tzinfo=timezone.utc)
        with self.assertRaises(StoreError) as error:
            self.store.claim(DAY, 'runner', 1, lease_seconds=300, now=late)
        self.assertEqual('day_end_window', error.exception.code)
        self.assertEqual('queued', self.store.status('request-0')['state'])

    def test_next_day_recovery_rebooks_the_quota_before_retry(self):
        for n in range(4):
            self.add(n)
        original = self.store.claim(DAY, 'old-runner', 1, lease_seconds=10, now=NOW)[0]
        tomorrow = NOW + timedelta(days=1)
        recovered = self.store.recover_claim(original['claim_id'], 'new-runner', SHA, False, now=tomorrow)
        self.assertEqual('2026-11-11', recovered['budget_day'])
        self.assertEqual(2, len(self.store.claim('2026-11-11', 'another', 3, now=tomorrow)))
        self.assertEqual([], self.store.claim('2026-11-11', 'third', 3, now=tomorrow))

    def test_next_day_recovery_cannot_consume_fourth_slot(self):
        for n in range(4):
            self.add(n)
        original = self.store.claim(DAY, 'old-runner', 1, lease_seconds=10, now=NOW)[0]
        tomorrow = NOW + timedelta(days=1)
        self.assertEqual(3, len(self.store.claim('2026-11-11', 'another', 3, now=tomorrow)))
        with self.assertRaises(StoreError) as error:
            self.store.recover_claim(original['claim_id'], 'new-runner', SHA, False, now=tomorrow)
        self.assertEqual('daily_limit', error.exception.code)
        self.assertEqual('reserved', self.store.status(original['request_id'])['state'])

    def test_presence_after_midnight_does_not_invent_commit_day(self):
        self.add(0)
        original = self.store.claim(DAY, 'old-runner', 1, lease_seconds=10, now=NOW)[0]
        with self.assertRaises(StoreError) as error:
            self.store.recover_claim(original['claim_id'], 'new-runner', SHA, True, now=NOW + timedelta(days=1))
        self.assertEqual('day_changed_reconcile_required', error.exception.code)
        self.assertEqual('reserved', self.store.status('request-0')['state'])

    def test_public_status_does_not_return_raw_evidence_or_content(self):
        self.add(0)
        status = self.store.status('request-0')
        self.assertNotIn('candidate', status)
        self.assertNotIn('candidate_json', status)
        self.assertIsNone(self.store.status('missing'))
        claim = self.store.claim(DAY, 'runner', 1, now=NOW)[0]
        self.assertEqual(candidate(), claim['candidate'])


if __name__ == '__main__':
    unittest.main()
