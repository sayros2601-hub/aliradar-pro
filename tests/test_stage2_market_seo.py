"""Unit tests for FLUXIXO multi-country SEO, AI firewall, sitemaps, and Stage-2 rollback safety."""
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site/tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ai_seo  # noqa: E402
import journal_pages  # noqa: E402
import market_seo  # noqa: E402
import stage2_seo  # noqa: E402
import write_sitemaps  # noqa: E402


class AiFirewallTests(unittest.TestCase):
    def test_firewall_rejects_forbidden_tokens_lint_issues_and_ungrounded_specs(self):
        errs = ai_seo.validate_route_override(
            {'title': 'Best Price Offer $19 InStock', 'description': 'Free shipping guaranteed best seller review stars.'},
            'en',
        )
        self.assertTrue(any('unverified price' in e or 'forbidden policy' in e for e in errs))

        fr_errs = ai_seo.validate_route_override(
            {'title': 'Chargeur USB-C compact pour voyage | FLUXIXO',
             'description': 'Chargeur rapide pour appareil photo et téléphone sans fil sur AliExpress.',
             'faq': [{'q': 'Comment choisir la puissance?', 'a': 'Vérifiez la puissance maximale annoncée chez le vendeur AliExpress avant la commande.'}]},
            'fr',
        )
        self.assertTrue(any('French needs' in e for e in fr_errs))

        es_errs = ai_seo.validate_route_override(
            {'title': 'Cargador compacto USB-C en México | FLUXIXO',
             'description': 'Revisa clavija y potencia del cargador compacto antes de confirmar en AliExpress.',
             'faq': [{'q': 'Cómo elegir la versión?', 'a': 'Abre la ficha del vendedor y selecciona el modelo compatible con tu equipo.'}]},
            'es',
        )
        self.assertTrue(any('Spanish needs opening' in e for e in es_errs))

        ru_errs = ai_seo.validate_route_override(
            {'title': 'Зарядное устройство wireless quick | FLUXIXO',
             'description': 'Быстрое сетевое зарядное устройство мощностью 240W для телефона и планшета в дороге.'},
            'ru',
            grounding_text='USB-C charger 65W compact',
        )
        self.assertTrue(any('Latin words' in e for e in ru_errs))
        self.assertTrue(any('ungrounded specs' in e for e in ru_errs))

    def test_provider_fallback_gemini_to_groq_and_auto_retry(self):
        calls = []

        def fake_transport(url, payload, headers):
            calls.append(url)
            if 'generativelanguage.googleapis.com' in url:
                raise RuntimeError('HTTP 429: quota exceeded')
            # First Groq call fails check_texts (missing space before '?' in fr)
            body = json.dumps(payload, ensure_ascii=False)
            if 'validation_errors' not in body:
                bad = {
                    'title': 'Chargeur USB-C compact pour voyage | FLUXIXO',
                    'description': 'Vérifiez le modèle exact, la prise européenne et les délais de livraison chez le vendeur AliExpress.',
                    'faq': [{'q': 'Comment choisir la prise?', 'a': 'Sélectionnez la prise européenne 230V avant de finaliser votre panier sur AliExpress.'}],
                }
                return {'choices': [{'message': {'content': json.dumps(bad, ensure_ascii=False)}}]}
            good = {
                'title': 'Chargeur USB-C compact pour voyage | FLUXIXO',
                'description': 'Vérifiez le modèle exact, la prise européenne et les délais de livraison chez le vendeur AliExpress.',
                'faq': [{'q': 'Comment choisir la prise ?', 'a': 'Sélectionnez la prise européenne 230V avant de finaliser votre panier sur AliExpress.'}],
            }
            return {'choices': [{'message': {'content': json.dumps(good, ensure_ascii=False)}}]}

        opp = {'path': '/fr/products/import-0010/', 'lang': 'fr', 'product_name': 'Chargeur USB-C', 'category': 'Техника'}
        cur = {'title': 'Old title', 'description': 'Old description long enough to provide context.', 'h1': 'Chargeur USB-C'}
        res, provider = ai_seo.propose_route_optimization(
            opp, cur, keys={'GEMINI_API_KEY': 'k1', 'GROQ_API_KEY': 'k2', 'OPENROUTER_API_KEY': ''}, transport=fake_transport
        )
        self.assertIsNotNone(res)
        self.assertTrue(provider.startswith('groq:'))
        self.assertIn(' ?', res['faq'][0]['q'])
        self.assertTrue(any('generativelanguage.googleapis.com' in u for u in calls))
        self.assertTrue(any('api.groq.com' in u for u in calls))


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
            self.assertEqual(['https://www.fluxixo.shop/en/', 'https://www.fluxixo.shop/en/products/a/'], en_urls)
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


if __name__ == '__main__':
    unittest.main()
