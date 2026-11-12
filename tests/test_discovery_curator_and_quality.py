"""Tests for rare-gadget discovery, anti-commodity stoplists, 6-market verification, studio image QA, and per-country ordering."""
from datetime import datetime, timezone
from pathlib import Path
import random
import sys
import unittest

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fluxixo_ai import autonomous, discovery_curator, image_studio
from fluxixo_ai.policy import DETAIL, MARKETS, QUERY
from fluxixo_ai.search import HOT, LINK
from fluxixo_site.redesign import build_redesign

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)


def _sharp_textured_cutout(size: int = 720, fg_margin: int = 90) -> Image.Image:
    """Create a realistic high-contrast patterned RGBA cutout for studio & QA verification tests."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = fg_margin, fg_margin, size - fg_margin, size - fg_margin
    draw.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=(42, 68, 118, 255), outline=(220, 230, 248, 255), width=6)
    rng = random.Random(42)
    for row in range(y0 + 36, y1 - 36, 26):
        for col in range(x0 + 36, x1 - 36, 26):
            tint = rng.randint(155, 248)
            accent = rng.randint(30, 95)
            draw.rectangle((col, row, col + 14, row + 14), fill=(tint, tint - 25, accent, 255))
    draw.ellipse((size // 2 - 75, size // 2 - 75, size // 2 + 75, size // 2 + 75), fill=(235, 112, 48, 255), outline=(255, 255, 255, 255), width=5)
    return img


def _api_row(pid: str, title: str, *, rate: str = '96.4%', volume: int = 420) -> dict:
    return {
        'product_id': pid,
        'product_title': title,
        'product_detail_url': f'https://www.aliexpress.com/item/{pid}.html',
        'product_main_image_url': f'https://ae01.alicdn.com/kf/{pid}.jpg',
        'product_small_image_urls': {'string': [f'https://ae01.alicdn.com/kf/{pid}-2.jpg']},
        'evaluate_rate': rate,
        'lastest_volume': volume,
    }


class DiscoveryCuratorTests(unittest.TestCase):
    def test_six_target_markets_include_ru_and_keep_spain_absent(self):
        self.assertEqual(('RU', 'US', 'BR', 'MX', 'IL', 'FR'), MARKETS)
        self.assertEqual(('RU', 'US', 'BR', 'MX', 'IL', 'FR'), discovery_curator.ALL_MARKETS)
        self.assertNotIn('ES', MARKETS)
        self.assertEqual({'ru': 'RU', 'en': 'US', 'pt': 'BR', 'es': 'MX', 'fr': 'FR', 'he': 'IL'},
                         discovery_curator.LANG_TO_MARKET)

    def test_commodity_and_replacement_stoplist(self):
        rejected_samples = [
            'Baseus USB Cable Fast Charging Data Cord 2m',
            'Silicone Phone Case Protective Cover for Smartphone',
            'Tempered Glass Screen Protector 3 Pack',
            'Replacement Mop Head Refill Spare Part Pad',
            'Universal Power Plug Adapter Outlet',
        ]
        for title in rejected_samples:
            banned, reason = discovery_curator.is_ordinary_or_banned_listing(title)
            self.assertTrue(banned, f'Expected commodity ban for {title!r}')
            self.assertIsNotNone(reason)

        allowed_samples = [
            'Heat Powered Wood Stove Fan 6 Blade Quiet Thermal Circulator',
            'Articulated USB Borescope Inspection Camera Dual Lens IP67',
            'Ultrasonic Jewelry Retainer Denture Cleaner Pod Digital Timer',
        ]
        for title in allowed_samples:
            banned, reason = discovery_curator.is_ordinary_or_banned_listing(title)
            self.assertFalse(banned, f'Unexpected ban ({reason}) for {title!r}')

    def test_voltage_compatibility_filters_markets(self):
        self.assertEqual(['US', 'MX'], discovery_curator.compatible_markets_for_title('110V US Plug Compact Espresso Maker'))
        self.assertEqual(['RU', 'IL', 'FR'], discovery_curator.compatible_markets_for_title('220V EU Plug Thermal Precision Station'))
        self.assertEqual(list(MARKETS), discovery_curator.compatible_markets_for_title('USB Type-C Rechargeable Gyroscopic Wrist Ball'))

    def test_presearch_exclusivity_screens_rating_volume_hot_and_clones(self):
        existing = [{'id': 'auto-111', 'name': 'Ультразвуковая ванночка', 'sourceTitle': 'Ultrasonic Jewelry Cleaner Pod 45kHz Digital'}]

        # 1. Low rating blocked
        ok, reason, _ = discovery_curator.presearch_exclusivity_check(
            {'product_id': '2001', 'title': 'Articulated Thermal Stove Fan Circulator', 'evaluate_rate': '81.0%', 'lastest_volume': 200},
            existing,
        )
        self.assertFalse(ok)
        self.assertIn('low_seller_rating', reason)

        # 2. Hyper-volume mass commodity blocked
        ok, reason, _ = discovery_curator.presearch_exclusivity_check(
            {'product_id': '2002', 'title': 'Articulated Thermal Stove Fan Circulator', 'evaluate_rate': '96.5%', 'lastest_volume': 55000},
            existing,
        )
        self.assertFalse(ok)
        self.assertIn('mass_commodity_volume', reason)

        # 3. Catalog clone blocked via Jaccard similarity
        ok, reason, _ = discovery_curator.presearch_exclusivity_check(
            {'product_id': '2003', 'title': 'Digital Ultrasonic Jewelry Cleaner Pod 45kHz', 'evaluate_rate': '97%', 'lastest_volume': 300},
            existing,
        )
        self.assertFalse(ok)
        self.assertIn('catalog_concept_duplicate', reason)

        # 4. Hot-product flood blocked (>=3 clones)
        hot_titles = [
            'Gravity Induction Electric Pepper Grinder Mill LED',
            'Gravity Induction Electric Pepper Mill Grinder Auto',
            'Auto Gravity Induction Electric Pepper Grinder Kitchen',
        ]
        ok, reason, _ = discovery_curator.presearch_exclusivity_check(
            {'product_id': '2004', 'title': 'Gravity Induction Electric Pepper Grinder Steel', 'evaluate_rate': '97%', 'lastest_volume': 450},
            existing,
            hot_titles=hot_titles,
        )
        self.assertFalse(ok)
        self.assertIn('hotproduct_commodity_saturation', reason)

        # 5. Web presearch saturation signal blocked
        ok, reason, _ = discovery_curator.presearch_exclusivity_check(
            {'product_id': '2005', 'title': 'Locking Contour Profile Duplicator Gauge Tool', 'evaluate_rate': '98%', 'lastest_volume': 180},
            existing,
            presearch_fn=lambda _: {'checked': True, 'status': 'ok', 'saturated': True},
        )
        self.assertFalse(ok)
        self.assertIn('web_presearch_ordinary', reason)

        # 6. Fresh rare gadget passes cleanly
        ok, reason, meta = discovery_curator.presearch_exclusivity_check(
            {'product_id': '2006', 'title': 'Locking Contour Profile Duplicator Gauge Tool', 'evaluate_rate': '98.2%', 'lastest_volume': 240},
            existing,
            presearch_fn=lambda _: {'checked': True, 'status': 'ok', 'saturated': False},
        )
        self.assertTrue(ok)
        self.assertEqual('passed', reason)
        self.assertGreater(meta['score'], 10.0)

    def test_rotating_queries_rotate_and_cover_all_six_markets(self):
        q1 = discovery_curator.select_rotating_queries(NOW.date().toordinal())
        q2 = discovery_curator.select_rotating_queries(NOW.date().toordinal() + 1)
        self.assertEqual(len(discovery_curator.CURATED_RARE_QUERIES), len(q1))
        self.assertEqual(set(MARKETS), {q['market'] for q in q1})
        self.assertNotEqual([q['key'] for q in q1[:6]], [q['key'] for q in q2[:6]])

    def test_discover_curated_pool_checks_six_markets_and_passes_pre_deploy_gate(self):
        # First query matches our chosen rotating task with both a banned cable item and a good rare item.
        first_task = discovery_curator.select_rotating_queries(NOW.date().toordinal())[0]
        good_pid = '888001234'
        bad_pid = '888001235'
        good_terms = ' '.join(group[0] for group in first_task['groups'])
        good_title = f'Articulated 220V EU Plug {good_terms} Studio Edition'
        bad_title = f'Replacement Spare Part {good_terms} Cable'

        checked_detail_countries = []

        def fake_call(method, params):
            def _wrap_products(rows):
                key = method.replace('.', '_') + '_response'
                return {key: {'resp_result': {'resp_code': '200', 'result': {
                    'current_record_count': len(rows),
                    'products': {'product': rows},
                }}}}

            if method == HOT:
                return _wrap_products([])
            if method == QUERY:
                if params.get('keywords') == first_task['query']:
                    return _wrap_products([_api_row(bad_pid, bad_title), _api_row(good_pid, good_title)])
                return _wrap_products([])
            if method == DETAIL:
                country = params.get('country')
                checked_detail_countries.append(country)
                pids = str(params.get('product_ids') or '').split(',')
                rows = []
                if good_pid in pids:
                    rows.append(_api_row(good_pid, good_title))
                if bad_pid in pids:
                    rows.append(_api_row(bad_pid, bad_title))
                return _wrap_products(rows)
            if method == LINK:
                detail = f'https://www.aliexpress.com/item/{good_pid}.html'
                return {'aliexpress_affiliate_link_generate_response': {'resp_result': {
                    'resp_code': '200',
                    'result': {'promotion_links': {'promotion_link': [{
                        'source_value': detail,
                        'promotion_link': f'https://s.click.aliexpress.com/e/{good_pid}',
                    }]}},
                }}}
            raise AssertionError(f'Unexpected method {method}')

        picks = autonomous.discover(
            fake_call,
            existing=[],
            count=1,
            now=NOW,
            use_curated_pool=True,
            check_all_markets=True,
            check_hot_background=True,
            presearch_fn=lambda _: {'checked': True, 'status': 'ok', 'saturated': False},
        )
        self.assertEqual(1, len(picks))
        pick = picks[0]
        self.assertEqual(good_pid, pick['product_id'])
        # Since title specifies 220V EU Plug, only 220V regions among ALL_MARKETS are approved even though API matched 6.
        self.assertEqual(['RU', 'IL', 'FR'], pick['availableMarkets'])
        for m in ('RU', 'US', 'BR', 'MX', 'IL', 'FR'):
            self.assertIn(m, checked_detail_countries)

        record, trans = autonomous.build_record(pick)
        self.assertEqual(['RU', 'IL', 'FR'], record['availableMarkets'])
        self.assertEqual({'ru', 'en', 'pt', 'es', 'fr', 'he'}, {'ru', *trans.keys()})

        record['imageQualityVerified'] = True
        ok, errors = discovery_curator.pre_deploy_catalog_gate([record], [], require_markets=True)
        self.assertTrue(ok, f'Gate failed unexpectedly: {errors}')

    def test_pre_deploy_catalog_gate_rejects_bad_candidates(self):
        base = {
            'id': 'auto-9001',
            'name': 'Compact Gyroscopic Ball',
            'sourceProductId': '9001',
            'sourceTitle': 'Auto Start Gyroscopic Wrist Ball Exerciser',
            'availableMarkets': ['RU', 'US'],
            'imageQualityVerified': True,
        }
        # Missing availableMarkets
        missing_mkt = {**base, 'id': 'auto-9002', 'sourceProductId': '9002'}
        missing_mkt.pop('availableMarkets')
        ok, errs = discovery_curator.pre_deploy_catalog_gate([missing_mkt], [], require_markets=True)
        self.assertFalse(ok)
        self.assertTrue(any('missing_verified_availableMarkets' in e for e in errs))

        # Voltage incompatible availableMarket
        volt_bad = {**base, 'id': 'auto-9003', 'sourceProductId': '9003', 'sourceTitle': '110V US Plug Compact Kettle', 'availableMarkets': ['RU']}
        ok, errs = discovery_curator.pre_deploy_catalog_gate([volt_bad], [], require_markets=True)
        self.assertFalse(ok)
        self.assertTrue(any('voltage_incompatible_market' in e for e in errs))

        # Unverified image quality
        img_bad = {**base, 'id': 'auto-9004', 'sourceProductId': '9004', 'imageQualityVerified': False}
        ok, errs = discovery_curator.pre_deploy_catalog_gate([img_bad], [], require_markets=True)
        self.assertFalse(ok)
        self.assertTrue(any('image_quality_not_verified' in e for e in errs))


class StudioImageQualityTests(unittest.TestCase):
    def test_sharp_cutout_passes_clarity_and_verification(self):
        cutout = _sharp_textured_cutout()
        composed = image_studio.compose_studio_frame(cutout, apply_clarity=True)
        self.assertEqual((1254, 1254), composed.size)
        ok, metrics = image_studio.verify_studio_image(cutout, raw_fg_size=(540, 540), composed=composed)
        self.assertTrue(ok, f'Expected sharp cutout to pass QA: {metrics}')
        self.assertGreaterEqual(metrics['sharpness'], 4.2)
        self.assertLessEqual(metrics['upscale_ratio'], 2.6)

    def test_tiny_upscale_cutout_fails_verification(self):
        cutout = _sharp_textured_cutout(size=240, fg_margin=20)
        ok, metrics = image_studio.verify_studio_image(cutout, raw_fg_size=(190, 190))
        self.assertFalse(ok)
        self.assertTrue(any(r in metrics['reasons'] for r in ('low_foreground_resolution', 'excessive_upscale')))

    def test_blurred_cutout_fails_sharpness_gate(self):
        cutout = _sharp_textured_cutout().filter(ImageFilter.GaussianBlur(radius=14))
        ok, metrics = image_studio.verify_studio_image(cutout, raw_fg_size=(540, 540))
        self.assertFalse(ok)
        self.assertIn('blurry_foreground', metrics['reasons'])

    def test_edge_clipped_cutout_fails_border_gate(self):
        img = Image.new('RGBA', (600, 600), (80, 110, 150, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((40, 40, 560, 560), fill=(210, 180, 130, 255), outline=(30, 40, 50, 255), width=6)
        ok, metrics = image_studio.verify_studio_image(img, raw_fg_size=(600, 600))
        self.assertFalse(ok)
        self.assertIn('cropped_subject', metrics['reasons'])


class PerCountryStorefrontOrderingTests(unittest.TestCase):
    def test_site_prioritizes_confirmed_market_products_per_language(self):
        common = {
            'world': 'tech',
            'category': 'Техника',
            'image': 'assets/images/test.webp',
            'original': 'assets/originals/test.webp',
            'affiliateUrl': 'https://s.click.aliexpress.com/e/test',
            'details': 'Spec',
            'facts': [],
            'theme': 'blue',
            'scale': 0.85,
            'rotation': 0,
        }
        p_us_only = {**common, 'id': 'auto-us', 'name': 'US Gadget', 'headline': ['h1', 'h2'], 'description': 'US item', 'availableMarkets': ['US', 'MX']}
        p_legacy = {**common, 'id': 'find-legacy', 'name': 'Legacy Gadget', 'headline': ['h1', 'h2'], 'description': 'Legacy item', 'sourceMarket': 'US'}
        p_ru_fr = {**common, 'id': 'auto-ru', 'name': 'RU Gadget', 'headline': ['h1', 'h2'], 'description': 'RU item', 'availableMarkets': ['RU', 'FR', 'IL']}

        i18n_entry = {'name': 'Localized', 'headline': ['h1', 'h2'], 'description': 'Desc'}
        data = {'products': {pid: {lang: i18n_entry for lang in ('en', 'pt', 'es', 'fr', 'he')} for pid in ('auto-us', 'find-legacy', 'auto-ru')}}

        # Russian storefront (RU): auto-ru first, p_us_only demoted to end
        ru_site = build_redesign.Site([p_us_only, p_legacy, p_ru_fr], data, 'ru')
        self.assertEqual(['auto-ru', 'find-legacy', 'auto-us'], [item['id'] for item in ru_site.items])

        # English storefront (US): both auto-us and sourceMarket=US match priority 0 before auto-ru
        en_site = build_redesign.Site([p_ru_fr, p_us_only, p_legacy], data, 'en', root=True)
        self.assertEqual(['auto-us', 'find-legacy', 'auto-ru'], [item['id'] for item in en_site.items])

        # French storefront (FR): auto-ru (includes FR) jumps to front
        fr_site = build_redesign.Site([p_us_only, p_legacy, p_ru_fr], data, 'fr')
        self.assertEqual(['auto-ru', 'find-legacy', 'auto-us'], [item['id'] for item in fr_site.items])

        # Brazilian storefront (pt -> BR): none confirmed for BR specifically, so legacy (rank 1) precedes explicitly unavailable items (rank 2)
        pt_site = build_redesign.Site([p_us_only, p_ru_fr, p_legacy], data, 'pt')
        self.assertEqual(['find-legacy', 'auto-us', 'auto-ru'], [item['id'] for item in pt_site.items])


if __name__ == '__main__':
    unittest.main()
