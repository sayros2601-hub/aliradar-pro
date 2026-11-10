"""Offline autonomous daily product selection with synthetic API responses."""
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fluxixo_ai.autonomous import discover, build_record, SEEDS, AutonomousError, mask_usable, ocr_poster

NOW = datetime(2026, 11, 11, 8, tzinfo=timezone.utc)


def row(pid, title):
    return {'product_id': pid, 'product_title': title,
            'product_detail_url': f'https://www.aliexpress.com/item/{pid}.html',
            'product_main_image_url': f'https://ae01.alicdn.com/kf/{pid}.jpg'}


def response(method, products):
    return {method.replace('.', '_') + '_response': {'resp_result': {'resp_code': 200,
            'result': {'current_record_count': len(products), 'products': {'product': products}}}}}


def seed():
    return next(s for s in SEEDS if s['key'] == 'inspection_mirror')


class AutonomousSelectionTests(unittest.TestCase):
    def api(self, method, params):
        self.calls.append((method, params))
        if method == 'aliexpress.affiliate.product.query':
            return response(method, [row('1', 'Unrelated kitchen tray'), row('2', 'Inspection mirror tool'),
                                     row('3', 'Telescopic inspection mirror tool')])
        if method == 'aliexpress.affiliate.productdetail.get':
            return response(method, [row('1', 'Unrelated kitchen tray'), row('2', 'Inspection mirror tool'),
                                     row('3', 'Telescopic inspection mirror tool')])
        if method == 'aliexpress.affiliate.link.generate':
            detail = params['source_values']
            return {'aliexpress_affiliate_link_generate_response': {'resp_result': {'resp_code': 200,
                    'result': {'promotion_links': {'promotion_link': [{'source_value': detail,
                    'promotion_link': 'https://s.click.aliexpress.com/e/_synthetic'}]}}}}}
        raise AssertionError('unexpected method')

    def setUp(self): self.calls = []

    def test_compares_pool_and_never_selects_unrelated_first_result_or_hot(self):
        result = discover(self.api, [], 1, NOW, seeds=[seed()])
        self.assertEqual(1, len(result))
        self.assertNotEqual('1', result[0]['product_id'])
        self.assertIn(result[0]['product_id'], {'2', '3'})
        methods = [call[0] for call in self.calls]
        self.assertNotIn('aliexpress.affiliate.hotproduct.query', methods)
        self.assertIn('aliexpress.affiliate.productdetail.get', methods)
        self.assertEqual(result[0]['detail_url'], self.calls[-1][1]['source_values'])

    def test_exact_known_product_and_title_are_skipped(self):
        existing = [{'id': 'old', 'sourceProductId': '3', 'sourceTitle': 'Inspection mirror tool'}]
        self.assertEqual([], discover(self.api, existing, 1, NOW, seeds=[seed()]))

    def test_query_without_matching_successful_market_detail_does_not_qualify(self):
        def api(method, params):
            if method.endswith('product.query'): return response(method, [row('2', 'Inspection mirror tool')])
            if method.endswith('productdetail.get'): return response(method, [])
            self.fail('must not generate affiliate for unconfirmed detail')
        self.assertEqual([], discover(api, [], 1, NOW, seeds=[seed()]))

    def test_same_product_alternate_photos_are_host_checked_and_preserved(self):
        def api(method, params):
            if method.endswith('product.query') or method.endswith('productdetail.get'):
                item = row('2', 'Inspection mirror tool')
                item['product_small_image_urls'] = {'string': ['https://ae01.alicdn.com/kf/alternate.jpg',
                                                                'https://ae01.alicdn.com.evil.invalid/image.jpg']}
                return response(method, [item])
            detail = params['source_values']
            return {'aliexpress_affiliate_link_generate_response': {'resp_result': {'resp_code': 200,
                    'result': {'promotion_links': {'promotion_link': [{'source_value': detail,
                    'promotion_link': 'https://s.click.aliexpress.com/e/_synthetic'}]}}}}}
        found = discover(api, [], 1, NOW, seeds=[seed()])[0]
        self.assertIn('https://ae01.alicdn.com/kf/alternate.jpg', found['image_urls'])
        self.assertFalse(any('.evil.invalid' in url for url in found['image_urls']))

    def test_failed_or_mismatched_affiliate_never_becomes_product(self):
        def api(method, params):
            if method.endswith('product.query') or method.endswith('productdetail.get'):
                return response(method, [row('2', 'Inspection mirror tool')])
            return {'aliexpress_affiliate_link_generate_response': {'resp_result': {'resp_code': 200,
                    'result': {'promotion_links': {'promotion_link': [{'source_value': 'https://attacker.invalid/item/3',
                    'promotion_link': 'https://s.click.aliexpress.com/e/bad'}]}}}}}
        self.assertEqual([], discover(api, [], 1, NOW, seeds=[seed()]))

    def test_card_and_all_locales_are_grounded_in_actual_matching_title(self):
        candidate = discover(self.api, [], 1, NOW, seeds=[seed()])[0]
        item, translations = build_record(candidate)
        self.assertEqual(candidate['product_id'], item['sourceProductId'])
        self.assertEqual(candidate['title'], item['sourceTitle'])
        self.assertEqual(candidate['detail_url'], item['sourceDetailUrl'])
        self.assertEqual('Зеркало для осмотра', item['name'])
        self.assertEqual({'en', 'pt', 'es', 'fr', 'he'}, set(translations))
        self.assertTrue(all(value['name'] and value['description'] for value in translations.values()))
        self.assertIn('труднодоступных мест', item['description'])
        self.assertIn('размер зеркала', item['description'])
        self.assertIn('mirror size', translations['en']['description'])
        self.assertNotIn('Telescopic', item['description'])
        self.assertFalse(item['demo'])
        # The slogan says something of its own instead of repeating the product name.
        for value in [item, *translations.values()]:
            self.assertEqual(2, len(value['headline']))
            self.assertNotEqual(value['name'].casefold(), ' '.join(value['headline']).rstrip('.').casefold())
        self.assertEqual(['Видно', 'даже за углом.'], item['headline'])

    def test_every_task_has_a_slogan_in_every_language(self):
        from fluxixo_ai.task_copy import TASK_HEADLINE, CATEGORY_HEADLINE, LANGS
        from fluxixo_ai.publisher import CATEGORIES
        self.assertEqual({s['key'] for s in SEEDS}, set(TASK_HEADLINE))
        self.assertEqual(set(CATEGORIES), set(CATEGORY_HEADLINE))
        for table in (TASK_HEADLINE, CATEGORY_HEADLINE):
            for lines in table.values():
                self.assertEqual(set(LANGS), set(lines))
                self.assertTrue(all(len(pair) == 2 and all(part.strip() for part in pair) for pair in lines.values()))

    def test_mismatched_task_cannot_manufacture_name_or_description(self):
        candidate = discover(self.api, [], 1, NOW, seeds=[seed()])[0]
        candidate['title'] = 'Unrelated kitchen tray'
        with self.assertRaises(AutonomousError): build_record(candidate)

    def test_replacement_part_is_not_relabelled_as_complete_tool(self):
        def api(method, params):
            if method.endswith('product.query') or method.endswith('productdetail.get'):
                return response(method, [row('2', 'Replacement screw for telescopic inspection mirror tool')])
            self.fail('accessory must not get an affiliate link for a complete tool')
        self.assertEqual([], discover(api, [], 1, NOW, seeds=[seed()]))

    def test_requested_count_is_bounded_at_three(self):
        with self.assertRaises(AutonomousError): discover(self.api, [], 4, NOW, seeds=[seed()])
        self.assertEqual([], self.calls)

    def test_bad_fragmentary_mask_is_rejected_and_substantial_single_object_passes(self):
        from PIL import Image, ImageDraw
        bad = Image.new('RGBA', (200,200), (0,0,0,0))
        ImageDraw.Draw(bad).rectangle((95,40,99,110), fill=(255,0,0,255))
        good = Image.new('RGBA', (200,200), (0,0,0,0))
        ImageDraw.Draw(good).rounded_rectangle((50,30,150,170), radius=20, fill=(0,0,0,255))
        self.assertFalse(mask_usable(bad))
        self.assertTrue(mask_usable(good))

    def test_seller_step_panel_beside_the_product_is_rejected_but_a_small_accessory_is_not(self):
        from PIL import Image, ImageDraw
        with_panel = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
        draw = ImageDraw.Draw(with_panel)
        draw.ellipse((20, 40, 180, 260), fill=(90, 90, 90, 255))
        draw.rectangle((220, 20, 260, 280), fill=(240, 200, 40, 255))  # a tall step-by-step strip
        with_part = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
        draw = ImageDraw.Draw(with_part)
        draw.ellipse((20, 40, 180, 260), fill=(90, 90, 90, 255))
        draw.rectangle((210, 200, 260, 250), fill=(90, 90, 90, 255))  # a compact accessory in the same set
        self.assertFalse(mask_usable(with_panel))
        self.assertTrue(mask_usable(with_part))

    def test_ocr_poster_detects_multiple_confident_words(self):
        header = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        def word(s): return '5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t90\t' + s + '\n'
        self.assertTrue(ocr_poster(header + word('SUPER') + word('STRONG') + word('MIRROR')))
        self.assertFalse(ocr_poster(header + word('USB')))


if __name__ == '__main__': unittest.main()
