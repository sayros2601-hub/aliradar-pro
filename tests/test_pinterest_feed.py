"""The future-only Pinterest feed must not republish the baseline catalog."""
import importlib.util
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'pinterest_feed_test', ROOT / 'fluxixo_site/tools/pinterest_feed.py')
feed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feed)


class PinterestFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dist = Path(self.temp.name) / 'dist'
        image = self.dist / 'assets/images/new-product.webp'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'RIFF\x08\x00\x00\x00WEBPtest')
        self.state = Path(self.temp.name) / 'pinterest-feed-state.json'
        self.state.write_text(json.dumps({
            'version': 1, 'baseline_ids': ['old-product'], 'first_seen': {}
        }), encoding='utf-8')
        self.product = {'id': 'new-product', 'demo': False,
                        'image': 'assets/images/new-product.webp'}
        self.translations = {'products': {'new-product': {'en': {
            'name': 'Coffee scale & timer',
            'description': 'Check the platform size and power supply.'
        }}}}
        self.first = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)

    def render(self, products, now=None):
        return feed.build_pinterest_feed(
            self.dist, products, self.translations, self.state,
            now=now or self.first)

    def test_baseline_stays_excluded_and_empty_rss_is_valid(self):
        before = self.state.read_bytes()
        xml = self.render([{'id': 'old-product', 'demo': False}])
        channel = ET.fromstring(xml).find('channel')
        self.assertEqual('en', channel.findtext('language'))
        self.assertEqual([], channel.findall('item'))
        self.assertEqual(before, self.state.read_bytes())

    def test_new_product_has_canonical_guid_real_image_length_and_disclosures(self):
        item = ET.fromstring(self.render([self.product])).find('channel/item')
        self.assertEqual('Coffee scale & timer', item.findtext('title'))
        self.assertEqual('https://www.fluxixo.shop/en/products/new-product/',
                         item.findtext('guid'))
        self.assertEqual(item.findtext('guid'), item.findtext('link'))
        self.assertEqual('true', item.find('guid').get('isPermaLink'))
        self.assertEqual(self.first, parsedate_to_datetime(item.findtext('pubDate')))
        self.assertEqual({
            'url': 'https://www.fluxixo.shop/assets/images/new-product.webp',
            'type': 'image/webp', 'length': '16'
        }, item.find('enclosure').attrib)
        self.assertIn('AI-assisted', item.findtext('description'))
        self.assertIn('Affiliate disclosure:', item.findtext('description'))
        self.assertIn('may earn a commission', item.findtext('description'))

    def test_retry_keeps_feed_and_dates_stable_instead_of_republishing(self):
        first_xml = self.render([self.product])
        before = self.state.read_bytes()
        self.assertEqual(first_xml, self.render(
            [self.product], datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc)))
        self.assertEqual(before, self.state.read_bytes())
        # A copy correction must not make this an additional new item.
        self.translations['products']['new-product']['en']['name'] = 'Updated scale'
        item = ET.fromstring(self.render([self.product])).find('channel/item')
        self.assertEqual(self.first, parsedate_to_datetime(item.findtext('pubDate')))
        self.assertEqual('https://www.fluxixo.shop/en/products/new-product/',
                         item.findtext('guid'))

    def test_image_disclosure_matches_documented_provenance(self):
        notes = [
            ('Студийная ИИ-визуализация по фотографии продавца. Исходное фото доступно для сравнения; состав заказа уточняйте на AliExpress.',
             "AI-generated studio illustration based on the seller's photo.", True),
            ('Студийная визуализация по исходному фото, созданная ИИ. Оригинал доступен ниже для сравнения деталей.',
             'AI-generated studio illustration based on the source photo.', True),
            ('Изображение подготовлено из фотографии продавца. Исходная фотография доступна для сравнения.',
             "Image prepared from the seller's photo.", False),
            ('Подготовленное изображение на основе фото продавца; исходное изображение доступно для сравнения.',
             "Image prepared from the seller's photo.", False),
            ('Студийная визуализация по фото продавца, очищенная от фона. Оригинальная фотография доступна для сравнения ниже.',
             "Background-removed studio image based on the seller's photo.", False),
        ]
        for note, expected, generated in notes:
            with self.subTest(note=note):
                xml = self.render([{**self.product, 'imageNote': note}])
                description = ET.fromstring(xml).findtext('channel/item/description')
                self.assertIn(expected, description)
                self.assertEqual(generated, 'AI-generated' in description)

    def test_absent_or_unknown_image_note_does_not_invent_provenance(self):
        for note in [None, '', 'Unrecognized note']:
            with self.subTest(note=note):
                product = {**self.product, 'imageNote': note,
                           'imageQualityVerified': True,
                           'sourceImageUrl': 'https://example.com/source.jpg'}
                description = ET.fromstring(self.render([product])).findtext('channel/item/description')
                self.assertIn('Image preparation details are not confirmed.', description)
                self.assertNotIn('AI-generated', description)
                self.assertNotIn("seller's photo", description)

    def test_long_copy_keeps_image_ai_and_affiliate_disclosures_within_500_characters(self):
        self.translations['products']['new-product']['en']['description'] = 'Check compatibility. ' * 40
        product = {**self.product, 'imageNote':
                   'Студийная ИИ-визуализация по фотографии продавца. Исходное фото доступно для сравнения; состав заказа уточняйте на AliExpress.'}
        description = ET.fromstring(self.render([product])).findtext('channel/item/description')
        self.assertLessEqual(len(description), 500)
        self.assertIn("AI-generated studio illustration based on the seller's photo.", description)
        self.assertIn('AI-assisted product summary.', description)
        self.assertIn('Affiliate disclosure:', description)
        self.assertTrue(description.endswith('may earn a commission from purchases.'))

    def test_second_addition_retains_first_date_and_catalog_order_does_not_matter(self):
        self.render([self.product])
        second = {**self.product, 'id': 'another-product'}
        self.translations['products']['another-product'] = {
            'en': {'name': 'Second item', 'description': 'Check compatibility.'}}
        later = datetime(2026, 11, 16, 17, 0, tzinfo=timezone.utc)
        xml = self.render([second, self.product], later)
        self.assertEqual(xml, self.render([self.product, second], later))
        items = ET.fromstring(xml).findall('channel/item')
        self.assertEqual([self.first, later],
                         [parsedate_to_datetime(p.findtext('pubDate')) for p in items])

    def test_missing_or_invalid_state_cannot_backfill_the_catalog(self):
        self.state.unlink()
        with self.assertRaisesRegex(ValueError, 'Pinterest feed state'):
            self.render([self.product])
        self.state.write_text('{"version":1,"baseline_ids":[],"first_seen":{}}')
        with self.assertRaisesRegex(ValueError, 'Pinterest feed state'):
            self.render([self.product])

    def test_invalid_new_item_cannot_create_external_links_or_missing_images(self):
        for field, value in [('id', '../elsewhere'),
                             ('image', '../private.webp'),
                             ('image', 'assets/images/missing.webp')]:
            with self.subTest(field=field, value=value):
                before = self.state.read_bytes()
                with self.assertRaises(ValueError):
                    self.render([{**self.product, field: value}])
                self.assertEqual(before, self.state.read_bytes())


if __name__ == '__main__':
    unittest.main()
