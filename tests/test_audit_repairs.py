import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from dealvault_core import DATA_DIR, read_json, write_json, validate_catalog
from build_google_merchant_feeds import build_google_feed
from build_modern_hub import SiteBuilder
from traffic_audit import measure, save_snapshot
import daily_rotator as rotation


class CatalogIntegrityTests(unittest.TestCase):
    def test_different_shortlinks_cannot_duplicate_marketplace_item(self):
        db = read_json(DATA_DIR/'products.json')
        db['products'][1]['item_id'] = db['products'][0]['item_id']
        with self.assertRaisesRegex(ValueError, 'duplicate marketplace item'):
            validate_catalog(db)

    def test_invented_identity_cannot_pass_format_checks(self):
        db = read_json(DATA_DIR/'products.json')
        db['products'][0].update(source='curated_ai_studio', item_id='ai_invented')
        with self.assertRaisesRegex(ValueError, 'actual product'):
            validate_catalog(db)

    def test_review_flag_cannot_bypass_failed_selection(self):
        db = read_json(DATA_DIR/'products.json')
        candidate = copy.deepcopy(db['products'][0])
        candidate.update(id='candidate', slug='candidate', item_id='1005001234567',
                         affiliate_url='https://s.click.aliexpress.com/e/_candidate',
                         source='portals', reviewed=True, source_evidence='Captured Portals record')
        with tempfile.TemporaryDirectory() as tmp:
            paths = {k: Path(tmp)/k for k in ('PRODUCTS_FILE','RESERVE_FILE','LOG_FILE','JOURNAL')}
            write_json(paths['PRODUCTS_FILE'], db)
            write_json(paths['RESERVE_FILE'], [candidate])
            checker = unittest.mock.Mock(return_value={'status':'RESOLVED'})
            with patch.multiple(rotation, **paths), patch.object(rotation, 'rank_candidates', return_value=[({'eligible':False}, candidate)]):
                self.assertEqual(rotation.rotate_deals(1, checker=checker), [])
            checker.assert_not_called()
            self.assertEqual(read_json(paths['PRODUCTS_FILE']), db)


class FeedRepairTests(unittest.TestCase):
    def test_merchant_feed_withdraws_invented_offers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'google_feed.xml'
            path.write_text('<rss><channel><item>stale offer</item></channel></rss>')
            build_google_feed(output=tmp)
            self.assertEqual(ET.parse(path).findall('./channel/item'), [])

    def test_rss_declares_real_image_format_and_size(self):
        db = read_json(DATA_DIR/'products.json')
        db['products'] = db['products'][:1]
        with tempfile.TemporaryDirectory() as tmp:
            builder = SiteBuilder(db, tmp)
            builder.prepare_assets()
            builder.feeds()
            for lang in ('en','ru','he','es'):
                file = 'rss.xml' if lang == 'en' else f'rss_{lang}.xml'
                enclosure = ET.parse(Path(tmp)/file).find('./channel/item/enclosure')
                self.assertEqual(enclosure.get('type'), 'image/webp')
                self.assertEqual(int(enclosure.get('length')), (Path(tmp)/builder.images[db['products'][0]['image']]).stat().st_size)
            self.assertIn('is_new', builder.public_products[0])


class TrafficTruthTests(unittest.TestCase):
    def test_http_failure_does_not_become_success_or_measured_traffic(self):
        snapshot = measure(getter=lambda path:(403, b'blocked', {}))
        self.assertEqual(snapshot['site_health']['endpoints_ok'], 0)
        self.assertIsNone(snapshot['traffic_metrics']['total_clicks'])
        self.assertTrue(all(c['status']=='not_checked' for c in snapshot['channels'].values()))

    def test_history_is_appended_and_corrupt_history_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'history.json'
            save_snapshot(path, {'schema_version':2,'timestamp':'first'})
            save_snapshot(path, {'schema_version':2,'timestamp':'second'})
            self.assertEqual([x['timestamp'] for x in read_json(path)], ['first','second'])
            path.write_text('{corrupt')
            with self.assertRaises(ValueError):
                save_snapshot(path, {'schema_version':2})
            self.assertEqual(path.read_text(), '{corrupt')


if __name__ == '__main__':
    unittest.main()
