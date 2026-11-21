"""Tests for rare-gadget discovery, anti-commodity stoplists, 6-market verification, studio image QA, and per-country ordering."""
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import re
import sys
import unittest
import unittest.mock

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
        # Every active curated query rotates in; types already on the site (RETIRED_TYPES) never do.
        active = [q for q in discovery_curator.CURATED_RARE_QUERIES if q['key'] not in discovery_curator.RETIRED_TYPES]
        self.assertEqual(len(active), len(q1))
        self.assertFalse({q['key'] for q in q1} & discovery_curator.RETIRED_TYPES)
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

    def test_latest_drop_rope_keeps_top_three_products_across_all_languages(self):
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
            'headline': ['h1', 'h2'],
            'description': 'Item description',
        }
        products = [
            {**common, 'id': 'auto-1', 'name': 'New 1', 'availableMarkets': ['US', 'BR', 'FR', 'IL']},
            {**common, 'id': 'auto-2', 'name': 'New 2', 'availableMarkets': ['RU', 'US', 'BR', 'MX', 'IL']},
            {**common, 'id': 'auto-3', 'name': 'New 3', 'availableMarkets': ['US', 'BR', 'IL', 'FR']},
            {**common, 'id': 'auto-4', 'name': 'Older 4', 'availableMarkets': ['RU', 'US', 'BR', 'MX', 'IL', 'FR']},
        ]
        i18n_entry = {'name': 'Localized', 'headline': ['h1', 'h2'], 'description': 'Desc'}
        data = {'products': {p['id']: {lang: i18n_entry for lang in ('en', 'pt', 'es', 'fr', 'he')} for p in products}}

        ru_site = build_redesign.Site(products, data, 'ru')
        self.assertEqual(['auto-1', 'auto-2', 'auto-3'], [item['id'] for item in ru_site.drop_items])
        self.assertEqual(['auto-2', 'auto-4', 'auto-1', 'auto-3'], [item['id'] for item in ru_site.items])


class PeakHourSchedulingTests(unittest.TestCase):
    def test_peak_slots_stagger_one_product_per_wave_across_all_six_markets(self):
        # Slot 1: 01:00 UTC -> US/MX prime, adds 1 when done=0
        s1 = discovery_curator.resolve_peak_slot(datetime(2026, 11, 13, 1, 5, tzinfo=timezone.utc), cron_expr='0 1 * * *', done_today=0)
        self.assertEqual(('americas_prime', ('US', 'MX'), 1, False), (s1['id'], s1['preferred_markets'], s1['add_count'], s1['skip']))
        # Repeat/retry inside slot 1 when done=1 must skip instead of dumping a batch
        s1_done = discovery_curator.resolve_peak_slot(cron_expr='0 1 * * *', done_today=1)
        self.assertEqual((0, True), (s1_done['add_count'], s1_done['skip']))

        # Slot 2: 17:00 UTC -> RU/IL/FR prime, adds 1 when done=1
        s2 = discovery_curator.resolve_peak_slot(datetime(2026, 11, 13, 17, 10, tzinfo=timezone.utc), cron_expr='0 17 * * *', done_today=1)
        self.assertEqual(('eurasia_prime', ('RU', 'IL', 'FR'), 1, False), (s2['id'], s2['preferred_markets'], s2['add_count'], s2['skip']))

        # Slot 3: 21:00 UTC -> BR prime, adds 1 when done=2
        s3 = discovery_curator.resolve_peak_slot(datetime(2026, 11, 13, 21, 5, tzinfo=timezone.utc), cron_expr='0 21 * * *', done_today=2)
        self.assertEqual(('brazil_latam_prime', ('BR', 'US', 'MX'), 1, False), (s3['id'], s3['preferred_markets'], s3['add_count'], s3['skip']))

        # Catch-up slot 22:30 UTC skips when 3/3 completed, or adds 1 if an earlier wave missed
        s4_skip = discovery_curator.resolve_peak_slot(cron_expr='30 22 * * *', done_today=3)
        self.assertEqual((0, True), (s4_skip['add_count'], s4_skip['skip']))
        s4_retry = discovery_curator.resolve_peak_slot(cron_expr='30 22 * * *', done_today=2)
        self.assertEqual((1, False), (s4_retry['add_count'], s4_retry['skip']))

    def test_select_rotating_queries_prioritizes_preferred_markets_first(self):
        ordered = discovery_curator.select_rotating_queries(
            NOW.date().toordinal(),
            preferred_markets=('RU', 'IL', 'FR'),
        )
        # First 6 queries come strictly from the preferred peak cluster before falling back
        self.assertTrue(all(q['market'] in ('RU', 'IL', 'FR') for q in ordered[:6]))
        self.assertEqual(set(MARKETS), {q['market'] for q in ordered})


_FIRST_TASK = discovery_curator.select_rotating_queries(NOW.date().toordinal())[0]


class SoldEverywhereTests(unittest.TestCase):
    """A new product must be sold in all six countries, or one country's front-page rope keeps an older product."""

    TASK = _FIRST_TASK
    # Countries other than the one the search runs in (that one is confirmed by the search's own detail call).
    OTHERS = [m for m in MARKETS if m != _FIRST_TASK['market']]

    def _discover(self, title_by_pid, sold_in, required, *, fail_once=()):
        task = self.TASK
        terms = ' '.join(group[0] for group in task['groups'])
        titles = {pid: title.format(terms=terms) for pid, title in title_by_pid.items()}
        failed = set()

        def fake_call(method, params):
            def wrap(rows):
                key = method.replace('.', '_') + '_response'
                return {key: {'resp_result': {'resp_code': '200', 'result': {
                    'current_record_count': len(rows), 'products': {'product': rows}}}}}
            if method == HOT:
                return wrap([])
            if method == QUERY:
                return wrap([_api_row(pid, t) for pid, t in titles.items()] if params.get('keywords') == task['query'] else [])
            if method == DETAIL:
                country = params.get('country')
                pids = str(params.get('product_ids') or '').split(',')
                if len(pids) == 1 and (pids[0], country) in fail_once and (pids[0], country) not in failed:
                    failed.add((pids[0], country))
                    raise RuntimeError('API did not answer')
                # The search's own detail call (its country) returns every row; per-country checks follow sold_in.
                return wrap([_api_row(pid, titles[pid]) for pid in pids
                             if pid in titles and (country == task['market'] or country in sold_in[pid])])
            if method == LINK:
                url = str(params.get('source_values'))
                pid = re.search(r'item/(\d+)\.html', url).group(1)
                return {'aliexpress_affiliate_link_generate_response': {'resp_result': {'resp_code': '200', 'result': {
                    'promotion_links': {'promotion_link': [{'source_value': url,
                                                            'promotion_link': f'https://s.click.aliexpress.com/e/{pid}'}]}}}}}
            raise AssertionError(f'Unexpected method {method}')

        with unittest.mock.patch.object(discovery_curator.time, 'sleep'):
            return autonomous.discover(
                fake_call, existing=[], count=1, now=NOW, use_curated_pool=True, check_all_markets=True,
                check_hot_background=True, presearch_fn=lambda _: {'checked': True, 'status': 'ok', 'saturated': False},
                required_markets=required)

    def test_product_missing_a_country_is_skipped_for_one_sold_everywhere(self):
        partly = set(MARKETS) - set(self.OTHERS[:2])
        picks = self._discover(
            {'777000001': 'Pocket {terms} Studio Edition', '777000002': 'Folding {terms} Travel Edition'},
            {'777000001': partly, '777000002': set(MARKETS)},
            tuple(MARKETS))
        self.assertEqual(['777000002'], [p['product_id'] for p in picks])
        self.assertEqual(list(MARKETS), picks[0]['availableMarkets'])

    def test_nothing_is_picked_when_no_product_is_sold_everywhere(self):
        partly = set(MARKETS) - set(self.OTHERS[:1])
        self.assertEqual([], self._discover({'777000001': 'Pocket {terms} Studio Edition'},
                                            {'777000001': partly}, tuple(MARKETS)))

    def test_without_the_rule_a_partly_sold_product_can_still_be_found(self):
        partly = set(MARKETS) - set(self.OTHERS[:2])
        picks = self._discover({'777000001': 'Pocket {terms} Studio Edition'}, {'777000001': partly}, ())
        self.assertEqual([m for m in MARKETS if m in partly], picks[0]['availableMarkets'])

    def test_a_country_that_errors_once_is_asked_again(self):
        picks = self._discover({'777000003': 'Compact {terms} Home Edition'}, {'777000003': set(MARKETS)},
                               tuple(MARKETS), fail_once={('777000003', self.OTHERS[-1])})
        self.assertEqual(list(MARKETS), picks[0]['availableMarkets'])

    def test_required_markets_setting(self):
        with unittest.mock.patch.dict(os.environ, {'FLUXIXO_REQUIRED_MARKETS': ''}):
            self.assertEqual(tuple(MARKETS), autonomous.required_markets())
        with unittest.mock.patch.dict(os.environ, {'FLUXIXO_REQUIRED_MARKETS': 'none'}):
            self.assertEqual((), autonomous.required_markets())
        with unittest.mock.patch.dict(os.environ, {'FLUXIXO_REQUIRED_MARKETS': 'ru, us'}):
            self.assertEqual(('RU', 'US'), autonomous.required_markets())
        with unittest.mock.patch.dict(os.environ, {'FLUXIXO_REQUIRED_MARKETS': 'RU,DE'}):
            with self.assertRaises(autonomous.DailyError):
                autonomous.required_markets()

    def test_presearch_exclusivity_catches_english_duplicate_via_name_en(self):
        existing = [
            {
                'id': 'levitating-moon-001',
                'name': 'Левитирующий светильник Луна на магнитной подставке',
                'name_en': 'Magnetic Levitating Floating Lunar Moon Lamp Desk Sculpture',
            }
        ]
        candidate = {
            'product_id': '999888777',
            'title': 'Magnetic Levitating Floating Lunar Moon Lamp Desk Sculpture Edition',
            'orders_count': 40,
            'evaluate_rate': '97%',
            'price': 38.0,
        }
        ok, reason, meta = discovery_curator.presearch_exclusivity_check(candidate, existing)
        self.assertFalse(ok)
        self.assertIn('catalog_concept_duplicate:levitating-moon-001', reason)
        self.assertEqual('catalog_overlap', meta.get('stage'))

    def test_price_window_strict_metrics_shop_dedup_and_rich_media_bonuses(self):
        existing = [{'id': 'auto-1', 'name': 'Item', 'sourceShopId': 'shop-999'}]
        base = {
            'product_id': '3001',
            'title': 'Magnetic Ferrofluid Sound Display Bottle Studio',
            'evaluate_rate': '96.0%',
            'lastest_volume': 120,
            'target_sale_price': '34.50',
            'commission_rate': '8.0%',
            'product_video_url': 'https://video.aliexpress-media.com/demo.mp4',
            'image_urls': ['https://a/1.jpg', 'https://a/2.jpg', 'https://a/3.jpg', 'https://a/4.jpg'],
            'shop_id': 'shop-123',
        }
        ok, reason, meta = discovery_curator.presearch_exclusivity_check(
            base, existing, require_observed_metrics=True, known_shop_ids={'shop-999'}
        )
        self.assertTrue(ok, reason)
        self.assertGreater(meta['score'], 30.0)

        # Too cheap (<$12) and too expensive (>$120) rejected
        for price, err_code in (('4.99', 'price_below_floor'), ('189.00', 'price_above_ceiling')):
            ok_p, rsn_p, _ = discovery_curator.presearch_exclusivity_check(
                {**base, 'target_sale_price': price}, existing, require_observed_metrics=True
            )
            self.assertFalse(ok_p)
            self.assertIn(err_code, rsn_p)

        # Missing/low volume or missing rating rejected in strict mode
        for bad_metrics, err_code in (
            ({'lastest_volume': 0}, 'low_volume_unproven'),
            ({'lastest_volume': 3}, 'low_volume_unproven'),
            ({'evaluate_rate': None}, 'missing_seller_rating'),
        ):
            ok_m, rsn_m, _ = discovery_curator.presearch_exclusivity_check(
                {**base, **bad_metrics}, existing, require_observed_metrics=True
            )
            self.assertFalse(ok_m)
            self.assertIn(err_code, rsn_m)

        # Duplicate shop blocked
        ok_s, rsn_s, _ = discovery_curator.presearch_exclusivity_check(
            {**base, 'shop_id': 'shop-999'}, existing, require_observed_metrics=True, known_shop_ids={'shop-999'}
        )
        self.assertFalse(ok_s)
        self.assertIn('duplicate_shop_id', rsn_s)

    def test_industrial_metrology_and_medical_rehab_titles_banned(self):
        banned_titles = [
            'High Precision Calibration Ring Gauge Inside Micrometer Bore Tool',
            'CT Series External Air Pump Plasma Cutter Arc Gouging Welder',
            'Incontinence Elderly Arthritis Button Hook Zipper Aid Tool',
        ]
        for title in banned_titles:
            banned, reason = discovery_curator.is_ordinary_or_banned_listing(title)
            self.assertTrue(banned, f'Expected industrial/medical ban for {title!r}')
            self.assertIsNotNone(reason)

    def test_judge_candidates_uniqueness_filters_low_wow_and_boosts_winners(self):
        from fluxixo_site.tools import ai_seo
        candidates = [
            {'product_id': '111', 'title': 'Ordinary Plastic Organizer Tray'},
            {'product_id': '222', 'title': 'Anti Gravity Tensegrity Floating Desk Sculpture', 'target_sale_price': '29.00'},
            {'product_id': '333', 'title': 'Solar Rotating Crystal Sphere Desk Ornament', 'target_sale_price': '25.00'},
        ]
        verdicts = {
            'verdicts': [
                {'product_id': '111', 'wow_score': 4.0, 'not_commodity': False, 'photogenic': True, 'reason': 'ordinary'},
                {'product_id': '222', 'wow_score': 9.5, 'not_commodity': True, 'photogenic': True, 'reason': 'wow physics'},
                {'product_id': '333', 'wow_score': 7.5, 'not_commodity': True, 'photogenic': True, 'reason': 'decent'},
            ]
        }
        with unittest.mock.patch.object(ai_seo, 'has_ai_provider', return_value=True), \
             unittest.mock.patch.object(ai_seo, 'complete_json', return_value=(verdicts, 'mock')):
            approved = discovery_curator.judge_candidates_uniqueness(candidates, [])
        self.assertEqual(['222', '333'], [c['product_id'] for c in approved])
        self.assertGreater(approved[0]['_curator_judge_bonus'], approved[1]['_curator_judge_bonus'])

    def test_multipage_price_params_and_min_markets_relaxed_threshold(self):
        task = self.TASK
        terms = ' '.join(group[0] for group in task['groups'])
        seen_pages = []
        seen_price_bounds = []
        page1_rows = [{**_api_row(str(71000 + i), f'Filler {terms} Tool {i}'), 'target_sale_price': '40.00', 'lastest_volume': 5} for i in range(20)]
        rare_p2_row = {**_api_row('72999', f'Magnetic Kinetic {terms} Collector Studio'), 'target_sale_price': '39.00', 'lastest_volume': 120, 'product_video_url': 'https://video.aliexpress-media.com/x.mp4', 'shop_id': 'shop-rare'}
        low_mkt_p2_row = {**_api_row('72888', f'Magnetic Kinetic {terms} Collector Ultra Tool'), 'target_sale_price': '39.00', 'lastest_volume': 120, 'shop_id': 'shop-3mkt'}
        four_mkts = set(MARKETS[:4]) | {task['market']}
        three_mkts = set(MARKETS[:2]) | {task['market']}

        def fake_call(method, params):
            def wrap(rows):
                key = method.replace('.', '_') + '_response'
                return {key: {'resp_result': {'resp_code': '200', 'result': {
                    'current_record_count': len(rows), 'products': {'product': rows}}}}}
            if method == HOT:
                return wrap([])
            if method == QUERY:
                if params.get('keywords') != task['query']:
                    return wrap([])
                seen_pages.append(params.get('page_no'))
                seen_price_bounds.append((params.get('min_sale_price'), params.get('max_sale_price')))
                if params.get('page_no') == '1':
                    return wrap(page1_rows)
                if params.get('page_no') == '2':
                    return wrap([low_mkt_p2_row, rare_p2_row])
                return wrap([])
            if method == DETAIL:
                country = params.get('country')
                pids = str(params.get('product_ids') or '').split(',')
                out = []
                for r in (*page1_rows, low_mkt_p2_row, rare_p2_row):
                    if r['product_id'] not in pids:
                        continue
                    if r['product_id'] == '72999' and country not in four_mkts and country != task['market']:
                        continue
                    if r['product_id'] == '72888' and country not in three_mkts and country != task['market']:
                        continue
                    out.append(r)
                return wrap(out)
            if method == LINK:
                url = str(params.get('source_values'))
                pid = re.search(r'item/(\d+)\.html', url).group(1)
                return {'aliexpress_affiliate_link_generate_response': {'resp_result': {'resp_code': '200', 'result': {
                    'promotion_links': {'promotion_link': [{'source_value': url,
                                                            'promotion_link': f'https://s.click.aliexpress.com/e/{pid}'}]}}}}}
            raise AssertionError(f'Unexpected method {method}')

        with unittest.mock.patch.dict(os.environ, {'FLUXIXO_MIN_PRICE_CENTS': '1200', 'FLUXIXO_MAX_PRICE_CENTS': '12000'}), \
             unittest.mock.patch.object(discovery_curator.time, 'sleep'):
            picks = autonomous.discover(
                fake_call, existing=[], count=1, now=NOW, use_curated_pool=True, check_all_markets=True,
                check_hot_background=False, presearch_fn=None, required_markets=(), min_markets=4, use_ai_judge=False,
            )
        self.assertEqual(['1', '2'], seen_pages[:2])
        self.assertEqual(('1200', '12000'), seen_price_bounds[0])
        self.assertEqual(['72999'], [p['product_id'] for p in picks])
        self.assertTrue(len(picks[0]['availableMarkets']) >= 4)
        rec, _ = autonomous.build_record(picks[0])
        self.assertEqual('shop-rare', rec.get('sourceShopId'))
        self.assertTrue(rec.get('hasVideo'))


if __name__ == '__main__':
    unittest.main()
