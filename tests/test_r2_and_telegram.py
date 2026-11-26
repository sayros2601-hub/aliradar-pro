"""Unit tests for Cloudflare R2 media sync/packing, Telegram digest/alerts, and link streak tracking."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site/tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import link_health_guard  # noqa: E402
import r2_media_sync  # noqa: E402
from fluxixo_ai import telegram_digest  # noqa: E402


class R2MediaAndTelegramTests(unittest.TestCase):
    def test_pack_pages_bundle_strips_offloaded_media_and_rewrites_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = root / 'release'
            pages = root / 'release_pages'
            (rel / 'assets/images').mkdir(parents=True)
            (rel / 'assets/thumbs').mkdir(parents=True)
            (rel / 'assets/fonts').mkdir(parents=True)
            (rel / 'en').mkdir(parents=True)

            (rel / 'assets/images/p1.webp').write_bytes(b'RIFFxxxxWEBP')
            (rel / 'assets/thumbs/p1-480.webp').write_bytes(b'RIFFyyyyWEBP')
            (rel / 'assets/fonts/font.woff2').write_bytes(b'wOF2')
            (rel / 'favicon.ico').write_bytes(b'ico')
            (rel / 'en/index.html').write_text(
                '<meta property="og:image" content="https://www.fluxixo.shop/assets/images/p1.webp">'
                '<img src="/assets/thumbs/p1-480.webp?v=abc" '
                'srcset="/assets/thumbs/p1-480.webp?v=abc 480w">',
                encoding='utf-8',
            )
            (rel / 'rss.xml').write_text(
                '<enclosure url="https://www.fluxixo.shop/assets/images/p1.webp" type="image/webp"/>',
                encoding='utf-8',
            )

            stats = r2_media_sync.pack_pages_bundle(rel, pages)
            self.assertEqual(4, stats['pages_files'])
            self.assertEqual(2, stats['rewritten_files'])
            self.assertFalse((pages / 'assets/images/p1.webp').exists())
            self.assertFalse((pages / 'assets/thumbs/p1-480.webp').exists())
            self.assertTrue((pages / 'assets/fonts/font.woff2').is_file())
            self.assertTrue((pages / 'favicon.ico').is_file())

            html = (pages / 'en/index.html').read_text(encoding='utf-8')
            self.assertIn('https://media.fluxixo.shop/assets/images/p1.webp', html)
            self.assertIn('src="https://media.fluxixo.shop/assets/thumbs/p1-480.webp?v=abc"', html)
            self.assertIn('srcset="https://media.fluxixo.shop/assets/thumbs/p1-480.webp?v=abc 480w"', html)
            self.assertNotIn('https://www.fluxixo.shop/assets/images/', html)
            self.assertIn('https://media.fluxixo.shop/assets/images/p1.webp', (pages / 'rss.xml').read_text(encoding='utf-8'))

    def test_sync_media_to_r2_caches_unchanged_hashes_and_skips_watch_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = root / 'release'
            manifest = root / 'r2_manifest.json'
            (rel / 'assets/images/watch-layers').mkdir(parents=True)
            (rel / 'assets/images/hero.webp').write_bytes(b'RIFFheroWEBP')
            (rel / 'assets/images/watch-layers/raw.png').write_bytes(b'pnglayer')

            uploaded_keys = []

            def fake_upload(url, sync_token, key, raw, ctype):
                uploaded_keys.append((key, ctype))

            with patch.dict(os.environ, {'AUTOPILOT_SYNC_TOKEN': 'tok'}, clear=False), \
                 patch.object(r2_media_sync, '_upload_via_worker', side_effect=fake_upload):
                s1 = r2_media_sync.sync_media_to_r2(rel, manifest, verify_live=False)
                s2 = r2_media_sync.sync_media_to_r2(rel, manifest, verify_live=False)

            self.assertEqual([('assets/images/hero.webp', 'image/webp')], uploaded_keys)
            self.assertEqual({'total_media': 1, 'uploaded': 1, 'cached': 0}, s1)
            self.assertEqual({'total_media': 1, 'uploaded': 0, 'cached': 1}, s2)

    def test_telegram_digest_and_ops_alerts(self):
        products = [
            {'id': 'p1', 'name': 'Умный датчик', 'category': 'Дом', 'description': 'Краткое описание.', 'image': 'assets/images/p1.webp'}
        ]
        i18n = {'products': {'p1': {'en': {'name': 'Smart Sensor'}}}}
        clicks = {'days': 7, 'total_clicks': 42, 'top_products': [{'product_id': 'p1', 'clicks': 19}]}
        digest = telegram_digest.build_digest_payload(products, i18n, clicks_summary=clicks, limit=5)
        self.assertEqual('https://media.fluxixo.shop/assets/images/p1.webp', digest['items'][0]['image_url'])
        self.assertIn('Клики за 7 дн.', digest['message_html'])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps = root / 'ps.json'
            lr = root / 'lr.json'
            ps.write_text(json.dumps({'days': {'2026-11-20': {'status': 'published', 'published_day': '2026-11-20'}}}), encoding='utf-8')
            lr.write_text(json.dumps({'results': [{'id': 'p9', 'status': 'UNAVAILABLE', 'reason': 'HTTP_404', 'broken_streak': 3}]}), encoding='utf-8')
            alerts = telegram_digest.collect_ops_alerts(
                ps, lr, now=datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc), explicit_reason='test_err'
            )
            self.assertTrue(any('Workflow alert: test_err' in a for a in alerts))
            self.assertTrue(any('Catalog publish stall' in a for a in alerts))
            self.assertTrue(any('Persistent broken affiliate links' in a for a in alerts))

    def test_link_health_guard_tracks_broken_streak(self):
        with tempfile.TemporaryDirectory() as tmp:
            rep = Path(tmp) / 'rep.json'
            prods = [{'id': 'p1', 'slug': 'p1', 'affiliate_url': 'https://s.click.aliexpress.com/e/_a'}]
            with patch.object(
                link_health_guard,
                'check_single_link',
                side_effect=lambda p: {'id': p['id'], 'status': 'UNAVAILABLE', 'reason': 'HTTP_404'},
            ):
                r1 = link_health_guard.audit_catalog(prods, report_path=rep, write=True, workers=1)
                r2 = link_health_guard.audit_catalog(prods, report_path=rep, write=True, workers=1)
            self.assertEqual(1, r1['results'][0]['broken_streak'])
            self.assertEqual(2, r2['results'][0]['broken_streak'])
            with patch.object(link_health_guard, 'check_single_link', return_value={'id': 'p1', 'status': 'RESOLVED', 'reason': 'PRODUCT_DESTINATION_ONLY'}):
                r3 = link_health_guard.audit_catalog(prods, report_path=rep, write=True, workers=1)
            self.assertEqual(0, r3['results'][0]['broken_streak'])


if __name__ == '__main__':
    unittest.main()
