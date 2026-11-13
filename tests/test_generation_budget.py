"""Offline media-product quota checks against real catalog and ledger writes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fluxixo_ai import autonomous, discovery_curator
from fluxixo_ai.daily_ledger import SEED_DAY, SEED_IDS, SEED_RUN
from tests.test_fluxixo_daily_autonomous_integration import selected


NOW = datetime(2026, 11, 14, 17, tzinfo=timezone.utc)


class GenerationBudgetTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.site = self.root / 'site'
        self.dist = self.site / 'dist'
        self.reserve = self.site / 'reserve'
        self.ledger = self.root / 'ledger.json'
        (self.dist / 'js').mkdir(parents=True)
        (self.site / 'tools').mkdir(parents=True)
        self.old = [{'id': pid, 'name': pid} for pid in sorted(SEED_IDS)]
        (self.dist / 'js/catalog.js').write_text(
            'window.MIRA_CATALOG = ' + json.dumps({'products': self.old}) + ';', encoding='utf-8')
        (self.site / 'tools/i18n_data.json').write_text('{"products": {}}', encoding='utf-8')
        self.ledger.write_text(json.dumps({
            'version': 1,
            'days': {SEED_DAY: [
                {'catalog_id': pid, 'product_id': None, 'source': 'github_actions', 'run_id': SEED_RUN}
                for pid in sorted(SEED_IDS)
            ]},
            'validation_runs': {},
        }), encoding='utf-8')
        self.calls = []
        # AI enrichment is an external service boundary. Keep real title lint,
        # discovery candidate validation, media admission, catalog and ledger writes.
        offline_copy = patch.object(autonomous, '_maybe_ai_enrich', side_effect=lambda record, translated, *_args, **_kwargs: (record, translated))
        offline_copy.start()
        self.addCleanup(offline_copy.stop)
        env = patch.dict(os.environ, {'FLUXIXO_STRICT_COPY': ''})
        env.start()
        self.addCleanup(env.stop)

    def media(self, candidate, internal_id, stage):
        self.calls.append(internal_id)
        image = stage / (internal_id + '.webp')
        original = stage / (internal_id + '-original.webp')
        image.write_bytes(('prepared ' + internal_id).encode())
        original.write_bytes(('original ' + internal_id).encode())
        return {'image': image, 'original': original,
                'source_sha256': hashlib.sha256(('source ' + internal_id).encode()).hexdigest(),
                'pixel_sha256': hashlib.sha256(('pixel ' + internal_id).encode()).hexdigest()}

    def run_batch(self, *, media=None, candidates=None, count=3):
        pool = candidates if candidates is not None else [selected(i) for i in range(6)]
        def discover(existing, needed, instant):
            old_ids = {p.get('sourceProductId') for p in existing}
            return [p for p in pool if p['product_id'] not in old_ids]
        return autonomous.accumulate(count=count, site_root=self.site, dist=self.dist,
                                     reserve_dir=self.reserve, ledger_path=self.ledger,
                                     now=NOW, discover_fn=discover, media_fn=media or self.media)

    def test_rejected_images_consume_product_budget_and_cannot_launch_a_fourth(self):
        before = self.ledger.read_bytes()
        def rejected(candidate, internal_id, stage):
            self.calls.append(internal_id)
            return {}
        with patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': '3'}):
            with self.assertRaises(autonomous.DailyError):
                self.run_batch(media=rejected)
        self.assertEqual(['auto-12345678901', 'auto-12345678902', 'auto-12345678903'], self.calls)
        self.assertEqual(before, self.ledger.read_bytes())
        self.assertFalse((self.dist / 'assets').exists())

    def test_failed_image_processing_also_consumes_budget(self):
        def rejected(candidate, internal_id, stage):
            self.calls.append(internal_id)
            raise autonomous.DailyError('synthetic_image_rejected')
        with patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': '1'}):
            with self.assertRaises(autonomous.DailyError):
                self.run_batch(media=rejected)
        self.assertEqual(['auto-12345678901'], self.calls)

    def test_zero_budget_never_processes_images(self):
        with patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': '0'}):
            with self.assertRaisesRegex(autonomous.DailyError, 'media_budget_exhausted'):
                self.run_batch()
        self.assertEqual([], self.calls)

    def test_invalid_budget_fails_before_images_or_catalog_changes(self):
        before = self.ledger.read_bytes()
        for value in ('-1', '4', '3.0', 'true', ''):
            with self.subTest(value=value), patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': value}):
                with self.assertRaisesRegex(autonomous.DailyError, 'media_budget_invalid'):
                    self.run_batch()
        self.assertEqual([], self.calls)
        self.assertEqual(before, self.ledger.read_bytes())

    def test_three_valid_products_publish_once_with_exactly_three_media_calls(self):
        with patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': '3'}):
            result = self.run_batch()
            replay = self.run_batch()
        self.assertEqual(3, result['added'])
        self.assertEqual(0, replay['added'])
        self.assertEqual(['auto-12345678901', 'auto-12345678902', 'auto-12345678903'], self.calls)
        ledger = json.loads(self.ledger.read_text(encoding='utf-8'))
        self.assertEqual(3, len(ledger['days']['2026-11-14']))

    def test_untranslated_candidate_is_rejected_before_spending_image_budget(self):
        candidate = selected(0)
        candidate['task'] = None
        candidate['category'] = 'Техника'
        candidate['title'] = 'Untranslated inspection mirror gadget'
        with patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': '3', 'FLUXIXO_STRICT_COPY': '1'}):
            with self.assertRaises(autonomous.DailyError):
                self.run_batch(candidates=[candidate], count=1)
        self.assertEqual([], self.calls)

    def test_strict_localized_copy_keeps_product_media_and_catalog_writes(self):
        candidates = []
        for index, task in enumerate(discovery_curator.CURATED_RARE_QUERIES[:3]):
            candidate = selected(index)
            candidate['task'] = task
            candidate['title'] = task['query'] + ' ' + ' '.join(group[0] for group in task['groups'])
            candidates.append(candidate)
        with patch.dict(os.environ, {'FLUXIXO_MAX_MEDIA_PRODUCTS': '3', 'FLUXIXO_STRICT_COPY': '1'}):
            result = self.run_batch(candidates=candidates)
        self.assertEqual(3, result['added'])
        catalog = json.loads((self.dist / 'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
        products = catalog['products'][:3]
        self.assertEqual(['auto-12345678901', 'auto-12345678902', 'auto-12345678903'], [p['id'] for p in products])
        self.assertTrue(all((self.dist / p['image']).is_file() for p in products))
        self.assertTrue(all(len(p['sourcePixelSha256']) == 64 for p in products))


if __name__ == '__main__':
    unittest.main()
