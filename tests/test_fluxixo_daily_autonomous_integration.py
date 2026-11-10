"""Daily catalog/ledger integration against temporary files and synthetic API."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fluxixo_daily_rotate as daily
from fluxixo_ai.autonomous import SEEDS

NOW = datetime(2026, 11, 11, 8, tzinfo=timezone.utc)


def selected(index):
    task = SEEDS[index]
    product_id = str(12345678901 + index)
    return {'product_id': product_id, 'title': task['query'],
            'detail_url': f'https://www.aliexpress.com/item/{product_id}.html',
            'image_url': f'https://ae01.alicdn.com/kf/{product_id}.jpg',
            'affiliate_url': f'https://s.click.aliexpress.com/e/{product_id}',
            'model_key': None, 'task': task}


class DailyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.site = self.root / 'fluxixo_site'
        self.dist = self.site / 'dist'
        self.reserve = self.site / 'reserve'
        for path in (self.dist / 'js', self.site / 'tools', self.reserve, self.root / 'data'):
            path.mkdir(parents=True)
        ids = ('find-064-book-light', 'find-065-spice-grinder', 'find-067-pill-organizer')
        self.old = [{'id': item, 'name': item, 'affiliateUrl': f'https://s.click.aliexpress.com/e/{item}'} for item in ids]
        (self.dist / 'js/catalog.js').write_text('window.MIRA_CATALOG = ' + json.dumps({'products': self.old}) + ';', encoding='utf-8')
        (self.site / 'tools/i18n_data.json').write_text(json.dumps({'products': {}}), encoding='utf-8')
        (self.reserve / 'reserve_pool.json').write_text('[]', encoding='utf-8')
        # The seed ledger (three seed-day rows, no validation yet), not the live file, which keeps growing.
        source = Path(daily.__file__).resolve().parent / 'data/fluxixo_daily_ledger.json'
        live = json.loads(source.read_text(encoding='utf-8'))
        seed = {'version': live['version'], 'days': {'2026-11-10': live['days']['2026-11-10']}, 'validation_runs': {}}
        (self.root / 'data/fluxixo_daily_ledger.json').write_text(json.dumps(seed, indent=2), encoding='utf-8')
        for name, value in [('SITE_ROOT',self.site), ('DIST',self.dist), ('RESERVE_DIR',self.reserve),
                            ('RESERVE_IMAGES',self.reserve/'images'), ('RESERVE_ORIGINALS',self.reserve/'originals'),
                            ('LEDGER_PATH',self.root/'data/fluxixo_daily_ledger.json')]:
            replacement = patch.object(daily, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def media(self, item, internal_id, stage):
        import hashlib
        image = stage / (internal_id + '-prepared.webp')
        original = stage / (internal_id + '-original.webp')
        image.write_bytes(b'prepared fixture ' + internal_id.encode())
        original.write_bytes(b'original fixture ' + internal_id.encode())
        return {'image': image, 'original': original,
                'source_sha256': hashlib.sha256(('source'+internal_id).encode()).hexdigest(),
                'pixel_sha256': hashlib.sha256(('pixel'+internal_id).encode()).hexdigest()}

    def catalog(self):
        return json.loads((self.dist / 'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))

    def test_today_already_has_three_so_never_calls_api(self):
        def no_discovery(*_): self.fail('daily cap must be checked before API')
        result = daily.accumulate_catalog(3, now=datetime(2026,11,10,20,tzinfo=timezone.utc),
                                          discover_fn=no_discovery, media_fn=self.media)
        self.assertEqual(0, result['added'])
        self.assertEqual(self.old, self.catalog()['products'])

    def test_new_day_adds_only_three_source_bound_and_retry_is_idempotent(self):
        calls = []
        def discover(existing, needed, now):
            calls.append(needed)
            return [selected(i) for i in range(3)]
        result = daily.accumulate_catalog(3, now=NOW, discover_fn=discover, media_fn=self.media)
        self.assertEqual(3, result['added'])
        products = self.catalog()['products']
        self.assertEqual(self.old, products[3:])
        self.assertEqual(['12345678901','12345678902','12345678903'], [p['sourceProductId'] for p in products[:3]])
        translations = json.loads((self.site/'tools/i18n_data.json').read_text(encoding='utf-8'))['products']
        self.assertTrue(all(set(translations[p['id']]) == {'en','pt','es','fr','he'} for p in products[:3]))
        self.assertTrue(all((self.dist / p['image']).is_file() and (self.dist / p['original']).is_file() for p in products[:3]))
        result = daily.accumulate_catalog(3, now=NOW, discover_fn=lambda *_: self.fail('retry must not query'), media_fn=self.media)
        self.assertEqual(0, result['added'])
        self.assertEqual([3], calls)

    def test_underfilled_batch_is_error_and_leaves_existing_catalog_ledger_assets_untouched(self):
        original = (self.root/'data/fluxixo_daily_ledger.json').read_bytes()
        with self.assertRaises(daily.DailyError):
            daily.accumulate_catalog(3, now=NOW, discover_fn=lambda *_: [selected(0)], media_fn=self.media)
        self.assertEqual(self.old, self.catalog()['products'])
        self.assertEqual(original, (self.root/'data/fluxixo_daily_ledger.json').read_bytes())
        self.assertFalse((self.dist/'assets').exists())

    def test_zero_count_never_queries_or_changes_ledger(self):
        before = (self.root/'data/fluxixo_daily_ledger.json').read_bytes()
        result = daily.accumulate_catalog(0, now=NOW, discover_fn=lambda *_: self.fail('no API'), media_fn=self.media)
        self.assertEqual(0, result['added'])
        self.assertEqual(before, (self.root/'data/fluxixo_daily_ledger.json').read_bytes())

    def test_one_time_validation_is_separate_from_normal_three_and_idempotent(self):
        from fluxixo_ai.daily_ledger import remaining, read_ledger
        today = datetime(2026,11,10,20,tzinfo=timezone.utc)
        run_id = 'fluxixo-validation-20261110-01'
        result = daily.accumulate_catalog(1, now=today, validation_run_id=run_id,
                                          discover_fn=lambda *_: [selected(0)], media_fn=self.media)
        self.assertEqual(1, result['added'])
        ledger = read_ledger(self.root/'data/fluxixo_daily_ledger.json')
        self.assertEqual(0, remaining(ledger, '2026-11-10', 3))
        self.assertEqual('auto-12345678901', ledger['validation_runs'][run_id]['catalog_id'])
        result = daily.accumulate_catalog(1, now=today, validation_run_id=run_id,
                                          discover_fn=lambda *_: self.fail('replay must not query'), media_fn=self.media)
        self.assertEqual(0, result['added'])
        self.assertTrue(result['validation_existing'])
        result = daily.accumulate_catalog(1, now=NOW, validation_run_id=run_id,
                                          discover_fn=lambda *_: self.fail('next-day replay must not query'), media_fn=self.media)
        self.assertEqual(0, result['added'])
        self.assertTrue(result['validation_existing'])

    def test_queued_ai_product_precedes_autonomous_fallback_with_same_daily_limit(self):
        from fluxixo_ai.store import Store
        from tests.test_fluxixo_ai_publisher import selected as queued_selection
        store = Store(self.root/'data/fluxixo_ai.sqlite3')
        store.enqueue('ai-request', queued_selection('12345678901'), now=NOW)
        needed = []
        def fallback(existing, count, now):
            needed.append(count)
            return [selected(1), selected(2)]
        result = daily.accumulate_catalog(3, now=NOW, queue_store=store, refresh_fn=lambda _entry, _now: selected(0),
                                          discover_fn=fallback, media_fn=self.media)
        self.assertEqual(3, result['added'])
        self.assertEqual([2], needed)
        self.assertEqual('ai-request', self.catalog()['products'][0]['sourceQueueRequestId'])
        self.assertEqual('reserved', store.status('ai-request')['state'])
        from fluxixo_ai.autonomous import mark_queued_committed, DailyError
        with self.assertRaises(DailyError):
            mark_queued_committed(self.catalog(), store, result['ids'], 'a'*40,
                                  verify_commit=lambda _: False, now=NOW)
        self.assertEqual('reserved', store.status('ai-request')['state'])
        marked = mark_queued_committed(self.catalog(), store, result['ids'], 'a'*40,
                                       verify_commit=lambda _: True, now=NOW)
        self.assertEqual(['ai-request'], marked)
        self.assertEqual('committed', store.status('ai-request')['state'])
        self.assertIsNone(store.status('ai-request')['deployment_id'])

    def test_transient_queue_refresh_failure_defers_request_and_keeps_daily_fallback(self):
        from fluxixo_ai.store import Store
        from tests.test_fluxixo_ai_publisher import selected as queued_selection
        store = Store(self.root/'data/fluxixo_ai.sqlite3')
        store.enqueue('ai-request', queued_selection('12345678909'), now=NOW)
        def unavailable(*_):
            raise OSError('temporary API failure')
        result = daily.accumulate_catalog(3, now=NOW, queue_store=store, refresh_fn=unavailable,
                                          discover_fn=lambda *_: [selected(0), selected(1), selected(2)], media_fn=self.media)
        self.assertEqual(3, result['added'])
        self.assertEqual('queued', store.status('ai-request')['state'])
        self.assertIsNone(store.status('ai-request')['reason'])

    def test_corrupt_ledger_and_out_of_range_count_fail_without_api(self):
        path = self.root/'data/fluxixo_daily_ledger.json'
        path.write_text('{}', encoding='utf-8')
        with self.assertRaises(Exception):
            daily.accumulate_catalog(3, now=NOW, discover_fn=lambda *_: self.fail('no API'), media_fn=self.media)
        with self.assertRaises(Exception):
            daily.accumulate_catalog(4, now=NOW, discover_fn=lambda *_: self.fail('no API'), media_fn=self.media)

    def test_validation_deploy_can_skip_all_indexnow_without_rebuilding(self):
        argv = ['fluxixo_daily_rotate.py', '--add', '0', '--deploy', '--deploy-existing', '--skip-indexnow']
        with patch('sys.argv', argv), patch.object(daily.subprocess, 'run') as subprocess_run, \
             patch.object(daily, 'deploy_release') as deploy, patch.object(daily, 'submit_indexnow') as indexnow:
            daily.main()
        deploy.assert_called_once()
        indexnow.assert_not_called()
        self.assertEqual(1, subprocess_run.call_count)  # existing release verification only


if __name__ == '__main__': unittest.main()
