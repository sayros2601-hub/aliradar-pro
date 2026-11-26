"""Unit tests for FLUXIXO multi-country SEO, AI firewall, sitemaps, and Stage-2 rollback safety."""
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site/tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ai_seo  # noqa: E402
import journal_pages  # noqa: E402
import locales  # noqa: E402
import market_seo  # noqa: E402
import stage2_seo  # noqa: E402
import write_sitemaps  # noqa: E402


class AiFirewallTests(unittest.TestCase):
    def test_english_root_and_russian_unprefixed_routes_have_separate_languages(self):
        for path, expected in [('/', 'en'), ('/en/', 'en'), ('/catalog/', 'ru'),
                               ('/products/a/', 'ru'), ('/journal/', 'ru'), ('/he/', 'he')]:
            with self.subTest(path=path):
                self.assertEqual(expected, stage2_seo.lang_from_path(path))

    def test_firewall_rejects_forbidden_tokens_lint_issues_and_ungrounded_specs(self):
        errs = ai_seo.validate_route_override(
            {'title': 'Best Price Offer $19 InStock', 'description': 'Free shipping guaranteed best seller review stars.'},
            'en',
        )
        self.assertTrue(any('unverified price' in e or 'forbidden policy' in e for e in errs))

        fr_errs = ai_seo.validate_route_override(
            {'title': 'Chargeur USB-C compact pour voyage | FLUXIXO',
             'description': 'Chargeur rapide pour appareil photo et téléphone sans fil: vérifiez la prise sur AliExpress.'},
            'fr',
        )
        self.assertTrue(any('French needs' in e for e in fr_errs))

        es_errs = ai_seo.validate_route_override(
            {'title': 'Cargador compacto USB-C en México | FLUXIXO',
             'description': 'Cómo revisar clavija y potencia del cargador compacto antes de confirmar en AliExpress?'},
            'es',
        )
        self.assertTrue(any('Spanish needs opening' in e for e in es_errs))

        faq_errs = ai_seo.validate_route_override(
            {'title': 'Cargador compacto USB-C en México | FLUXIXO',
             'description': 'Revisa clavija y potencia del cargador compacto antes de confirmar en AliExpress.',
             'faq': [{'q': '¿Cómo elegir la versión?', 'a': 'Abre la ficha del vendedor y selecciona el modelo compatible.'}]},
            'es',
        )
        self.assertTrue(any('Quick buyer questions / FAQ blocks are forbidden' in e for e in faq_errs))

        ru_errs = ai_seo.validate_route_override(
            {'title': 'Зарядное устройство wireless quick | FLUXIXO',
             'description': 'Быстрое сетевое зарядное устройство мощностью 240W для телефона и планшета в дороге.'},
            'ru',
            grounding_text='USB-C charger 65W compact',
        )
        self.assertTrue(any('Latin words' in e for e in ru_errs))
        self.assertTrue(any('ungrounded specs' in e for e in ru_errs))

    def test_provider_fallback_cloudflare_to_github_models_and_auto_retry(self):
        calls = []

        def fake_transport(url, payload, headers):
            calls.append(url)
            self.assertNotIn('generativelanguage.googleapis.com', url)
            if 'api.cloudflare.com' in url:
                raise RuntimeError('HTTP 429: neuron quota exhausted')
            # First GitHub Models call fails check_texts (missing space before ':' in fr)
            body = json.dumps(payload, ensure_ascii=False)
            if 'validation_errors' not in body:
                bad = {
                    'title': 'Chargeur USB-C compact pour voyage | FLUXIXO',
                    'description': 'Modèle vérifié: contrôlez la prise européenne et les délais de livraison chez le vendeur AliExpress.',
                }
                return {'choices': [{'message': {'content': json.dumps(bad, ensure_ascii=False)}}]}
            good = {
                'title': 'Chargeur USB-C compact pour voyage | FLUXIXO',
                'description': 'Modèle vérifié : contrôlez la prise européenne et les délais de livraison chez le vendeur AliExpress.',
            }
            return {'choices': [{'message': {'content': json.dumps(good, ensure_ascii=False)}}]}

        opp = {'path': '/fr/products/import-0010/', 'lang': 'fr', 'product_name': 'Chargeur USB-C', 'category': 'Техника'}
        cur = {'title': 'Old title', 'description': 'Old description long enough to provide context.', 'h1': 'Chargeur USB-C'}
        res, provider = ai_seo.propose_route_optimization(
            opp,
            cur,
            keys={'CLOUDFLARE_API_TOKEN': 'cf-tok', 'GITHUB_TOKEN': 'gh-tok'},
            transport=fake_transport,
        )
        self.assertIsNotNone(res)
        self.assertTrue(provider.startswith('github_models:'), provider)
        self.assertNotIn('faq', res)
        self.assertIn(' :', res['description'])
        self.assertTrue(any('api.cloudflare.com' in u for u in calls))
        self.assertTrue(any('models.github.ai' in u for u in calls))

    def test_complete_json_supports_cloudflare_worker_copy_transport_without_gemini(self):
        seen_urls = []

        def fake_transport(url, payload, headers):
            seen_urls.append((url, payload, headers))
            self.assertNotIn('generativelanguage.googleapis.com', url)
            return {
                'ok': True,
                'provider': 'cloudflare-workers-ai',
                'model': '@cf/meta/llama-3.3-70b-instruct-fp8-fast',
                'choices': [{'message': {'content': '{"status":"ok"}'}}],
            }

        # Direct Cloudflare token routes directly to Cloudflare REST API when Worker URL is disabled
        res_cf, prov_cf = ai_seo.complete_json(
            'sys',
            'user',
            keys={'CLOUDFLARE_API_TOKEN': 'cf-api', 'CLOUDFLARE_ACCOUNT_ID': 'acc-123'},
            transport=fake_transport,
        )
        self.assertEqual({'status': 'ok'}, res_cf)
        self.assertEqual('cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast', prov_cf)
        self.assertIn('api.cloudflare.com/client/v4/accounts/acc-123/ai/run/', seen_urls[0][0])

        # Worker transport routes to /api/generate-copy using Cloudflare Workers AI models
        seen_urls.clear()
        res_wk, prov_wk = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            transport=fake_transport,
        )
        self.assertEqual({'status': 'ok'}, res_wk)
        self.assertEqual('cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast', prov_wk)
        self.assertEqual(1, len(seen_urls))
        self.assertEqual('https://fluxixo-autopilot.sayros2601.workers.dev/api/generate-copy', seen_urls[0][0])
        self.assertEqual('cloudflare-workers-ai', seen_urls[0][1]['provider'])
        self.assertEqual('@cf/meta/llama-3.3-70b-instruct-fp8-fast', seen_urls[0][1]['model'])


class MarketSeoAndSitemapsTests(unittest.TestCase):
    def test_rotating_related_covers_entire_category(self):
        items = [{'id': f'p-{i}'} for i in range(10)]
        inbound = {p['id']: 0 for p in items}
        for p in items:
            for rel in market_seo.rotating_related(items, p, items, limit=4):
                inbound[rel['id']] += 1
        self.assertTrue(all(count >= 4 for count in inbound.values()), inbound)

    def test_full_alternates_covers_six_markets_plus_x_default(self):
        paths = {'ru': '/products/x/', 'en': '/en/products/x/', 'pt': '/pt/products/x/',
                 'es': '/es/products/x/', 'fr': '/fr/products/x/', 'he': '/he/products/x/'}
        html = market_seo.full_alternates('https://www.fluxixo.shop', paths)
        for tag in ('ru', 'ru-RU', 'en', 'en-US', 'pt-BR', 'pt', 'es-MX', 'es', 'fr', 'fr-FR', 'he-IL', 'he', 'x-default'):
            self.assertIn(f'hreflang="{tag}"', html)

    def test_wifi_guide_retains_russian_article_and_renders_english_counterpart(self):
        origin = 'https://www.fluxixo.shop'
        slug = 'wifi-repeater-buying-guide'
        product_id = 'katord-wifi-repeater'
        guide_paths = {
            'ru': f'/journal/{slug}/',
            'en': f'/en/journal/{slug}/',
            'pt': f'/pt/journal/{slug}/',
            'es': f'/es/journal/{slug}/',
            'fr': f'/fr/journal/{slug}/',
            'he': f'/he/journal/{slug}/',
        }
        product_paths = {
            'ru': f'/products/{product_id}/',
            'en': f'/en/products/{product_id}/',
            'pt': f'/pt/products/{product_id}/',
            'es': f'/es/products/{product_id}/',
            'fr': f'/fr/products/{product_id}/',
            'he': f'/he/products/{product_id}/',
        }
        journal_indexes = {
            'ru': '/journal/',
            'en': '/en/journal/',
            'pt': '/pt/journal/',
            'es': '/es/journal/',
            'fr': '/fr/journal/',
            'he': '/he/journal/',
        }
        products = [
            {'id': 'fallback-example', 'name': 'Fallback example', 'image': 'assets/images/fallback.webp'},
            {'id': product_id, 'name': 'KATORD RU', 'image': 'assets/images/katord.webp'},
        ]
        translations = {'products': {product_id: {lg: {'name': f'KATORD {lg.upper()}'} for lg in ('en', 'pt', 'es', 'fr', 'he')}}}
        pages = {}

        def page(title, description, path, body, *, schema, language, alternate_paths, image=None):
            pages[path] = (body, schema, language, alternate_paths)
            return body

        routes = journal_pages.generate_journal_pages(
            origin, products, translations, page, lambda *_: None, market_seo.full_alternates,
        )
        guide_routes = [path for path in routes if path.endswith(f'/{slug}/')]
        self.assertCountEqual(guide_paths.values(), guide_routes)
        dates = {}
        for language, path in guide_paths.items():
            with self.subTest(language=language):
                body, schema, html_language, alternatives = pages[path]
                self.assertEqual(language, html_language)
                self.assertEqual(guide_paths, alternatives)
                self.assertIn(f'href="{product_paths[language]}"', body)
                self.assertIn(f'href="{path}"', pages[journal_indexes[language]][0])
                article_schema = next(node for node in schema['@graph'] if node['@type'] == 'Article')
                self.assertEqual(origin + path, article_schema['mainEntityOfPage'])
                dates[language] = date.fromisoformat(article_schema['datePublished'])

        russian_body = pages[guide_paths['ru']][0]
        self.assertIn('<h1>Как выбрать усилитель Wi-Fi сигнала для квартиры и дачи</h1>', russian_body)
        for heading in ('Сколько антенн и диапазонов нужно на практике',
                        'Где ставить повторитель, чтобы он усиливал, а не тормозил',
                        'Порт RJ45 и режим точки доступа', 'Вилка, нагрев и способ настройки'):
            self.assertIn(f'<h2>{heading}</h2>', russian_body)
        self.assertEqual(date(2026, 11, 13), dates['ru'])
        self.assertGreater(dates['en'], dates['ru'])

    def test_write_sitemaps_creates_country_maps_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            routes = ['/', '/catalog/', '/products/a/', '/en/', '/en/products/a/', '/pt/', '/es/', '/fr/', '/he/']
            for r in routes:
                target = dist / (r.strip('/') + '/index.html' if r != '/' else 'index.html')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f'<html><body>{r}</body></html>', encoding='utf-8')
            old_state = write_sitemaps.STATE
            try:
                write_sitemaps.STATE = dist / 'state.json'
                write_sitemaps.write_sitemaps(dist, routes)
            finally:
                write_sitemaps.STATE = old_state
            for name in ('sitemap.xml', 'sitemap-index.xml', 'sitemap-ru.xml', 'sitemap-en.xml', 'sitemap-pt.xml', 'sitemap-es.xml', 'sitemap-fr.xml', 'sitemap-he.xml'):
                self.assertTrue((dist / name).exists(), name)
            en_urls = [n.text for n in ET.parse(dist / 'sitemap-en.xml').getroot().findall('.//{*}loc')]
            self.assertEqual(['https://www.fluxixo.shop/', 'https://www.fluxixo.shop/en/',
                              'https://www.fluxixo.shop/en/products/a/'], en_urls)
            idx_locs = [n.text for n in ET.parse(dist / 'sitemap-index.xml').getroot().findall('.//{*}loc')]
            self.assertIn('https://www.fluxixo.shop/sitemap-en.xml', idx_locs)
            self.assertIn('https://www.fluxixo.shop/sitemap-he.xml', idx_locs)


class Stage2AutonomousTests(unittest.TestCase):
    def test_underperforming_experiment_rolls_back_with_cooldown(self):
        today = date(2026, 11, 20)
        old_day = (today - timedelta(days=16)).isoformat()
        state = {
            'experiments': {
                '/en/products/x/': {
                    'date': old_day, 'status': 'active', 'lang': 'en',
                    'baseline': {'clicks': 10, 'impressions': 100, 'position': 8.0},
                }
            },
            'cooldowns': {},
            'keywords': {},
        }
        overrides = {'version': 1, 'routes': {'/en/products/x/': {'title': 'Experiment', 'description': 'Desc'}}}
        results = {'google': {'rows': [{'page': 'https://www.fluxixo.shop/en/products/x/', 'query': 'q', 'clicks': 1, 'impressions': 120, 'position': 14.2}]}}
        metrics = stage2_seo._page_metrics(results)
        rolled, _ = stage2_seo.evaluate_experiments(today, state, overrides, metrics)
        self.assertEqual([{'path': '/en/products/x/', 'reason': 'ctr_drop'}], rolled)
        self.assertNotIn('/en/products/x/', overrides['routes'])
        self.assertEqual('rolled_back', state['experiments']['/en/products/x/']['status'])
        self.assertGreater(state['cooldowns']['/en/products/x/'], today.isoformat())

    def test_verify_failure_auto_reverts_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            dist = tmp_dir / 'dist'
            (dist / 'js').mkdir(parents=True)
            (dist / 'js/catalog.js').write_text('window.MIRA_CATALOG = {"products": [{"id": "item-1", "name": "Мини фонарик", "category": "Техника", "demo": false}]};', encoding='utf-8')
            page_dir = dist / 'en/products/item-1'
            page_dir.mkdir(parents=True)
            (page_dir / 'index.html').write_text('<html><head><title>Mini Flashlight | FLUXIXO</title><meta name="description" content="Compact mini flashlight for daily carry and travel checks on AliExpress."></head><body><h1>Mini Flashlight</h1></body></html>', encoding='utf-8')
            ov_file = tmp_dir / 'seo_overrides.json'
            orig = '{"version": 1, "routes": {}}\n'
            ov_file.write_text(orig, encoding='utf-8')
            state = {'experiments': {}, 'cooldowns': {}, 'keywords': {}}
            results = {'google': {'rows': [], 'country_rows': [{'country': 'USA', 'page': 'https://www.fluxixo.shop/en/products/item-1/', 'query': 'mini flashlight', 'clicks': 0, 'impressions': 60, 'position': 11.0}]}}

            def broken_verify():
                raise RuntimeError('simulated release verification failure')

            res = stage2_seo.run_stage2(
                date(2026, 11, 20), dist, results, state, {},
                apply_changes=True, overrides_path=ov_file, verify_fn=broken_verify,
            )
            self.assertIsNotNone(res['verify_error'])
            self.assertEqual(orig, ov_file.read_text(encoding='utf-8'))
            self.assertEqual([], res['applied'])
            self.assertEqual({}, state['experiments'])

    def test_fit_description_snaps_to_sentences_without_ellipsis_cutoff(self):
        long_en = (
            'This magnetic seam guide attaches securely to your sewing machine to help maintain precise '
            'stitch lines and prevent fabric from curling while you work. It includes a built-in ruler '
            'and thread cutter for daily sewing projects.'
        )
        fitted = locales.fit_description(long_en, 'en', limit=158)
        self.assertLessEqual(len(fitted), 158)
        self.assertFalse(fitted.endswith(('…', '...')), fitted)
        self.assertTrue(fitted.endswith('.'), fitted)

        single_long_clause = (
            'Компактный двухдиапазонный повторитель с шестью внешними антеннами расширяет покрытие '
            'домашней сети, устраняет мёртвые зоны в спальне и легко настраивается со смартфона или компьютера.'
        )
        fitted_ru = locales.fit_description(single_long_clause, 'ru', limit=158)
        self.assertLessEqual(len(fitted_ru), 158)
        self.assertFalse(fitted_ru.endswith(('…', '...')), fitted_ru)
        self.assertTrue(fitted_ru.endswith('.'), fitted_ru)

    def test_technical_audit_tracks_static_dynamic_limits_and_llms_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            for name in ('sitemap.xml', 'sitemap-index.xml', 'sitemap-ru.xml', 'sitemap-en.xml',
                         'sitemap-pt.xml', 'sitemap-es.xml', 'sitemap-fr.xml', 'sitemap-he.xml', 'llms.txt'):
                (dist / name).write_text('ok', encoding='utf-8')
            (dist / 'products/katord-wifi-repeater').mkdir(parents=True)
            (dist / 'products/katord-wifi-repeater/index.html').write_text('<html></html>', encoding='utf-8')
            static_lines = [f'/old-{i} /en/ 301' for i in range(150)]
            dynamic_lines = ['/ru/products/:id /products/:id/ 301']
            (dist / '_redirects').write_text('\n'.join(static_lines + dynamic_lines), encoding='utf-8')

            with mock.patch.object(stage2_seo.check_texts, 'run', return_value=[]):
                audit_ok = stage2_seo.technical_audit(dist)
                self.assertTrue(audit_ok['ok'], audit_ok)
                self.assertEqual(150, audit_ok['static_redirects'])
                self.assertEqual(1, audit_ok['dynamic_redirects'])
                self.assertTrue(audit_ok['llms_txt'])

                (dist / 'llms.txt').unlink()
                audit_no_llms = stage2_seo.technical_audit(dist)
                self.assertFalse(audit_no_llms['ok'])
                self.assertTrue(any('llms.txt' in i for i in audit_no_llms['issues']))

                (dist / '_redirects').write_text('\n'.join(f'/dyn-{i}/* /en/ 301' for i in range(95)), encoding='utf-8')
                audit_dyn = stage2_seo.technical_audit(dist)
                self.assertFalse(audit_dyn['ok'])
                self.assertTrue(any('динамических' in i for i in audit_dyn['issues']))


if __name__ == '__main__':
    unittest.main()
