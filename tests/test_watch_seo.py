"""Single existing watch page SEO regression; no network or deployment."""
import html
import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WATCH_ID = 'import-0024'
AFFILIATE = 'https://s.click.aliexpress.com/e/_c2vkUuwb'
CANONICAL = 'https://www.fluxixo.shop/products/import-0024/'


class WatchSeoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'fluxixo_site/redesign/build_redesign.py'
        spec = importlib.util.spec_from_file_location('watch_redesign_test', path)
        cls.site_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.site_module)
        products, cls.translations = cls.site_module.load()
        cls.products = [p for p in products if p['id'] in (WATCH_ID, 'import-0042')]
        assert len(cls.products) == 2

    def render(self, lang):
        module = self.site_module
        site = module.Site(self.products, self.translations, lang)
        captured = {}
        original = module.write
        module.write = lambda path, page: captured.update({path: page})
        try:
            site.build_products({locale: {p['id'] for p in self.products} for locale in module.LANGS})
        finally:
            module.write = original
        return captured

    def test_russian_watch_has_specific_useful_search_copy_and_same_affiliate(self):
        page = self.render('ru')['/products/import-0024/']
        title = html.unescape(re.search(r'<title>(.*?)</title>',page).group(1))
        description = html.unescape(re.search(r'<meta name="description" content="([^"]+)">',page).group(1))
        h1 = html.unescape(re.search(r'<h1 class="d">(.*?)</h1>',page).group(1))
        self.assertIn('Купить наручные часы',title)
        self.assertIn('AliExpress',title)
        self.assertEqual(h1,'Умные наручные часы')
        self.assertIn('наручные часы',description.lower())
        visible = html.unescape(re.sub('<[^>]+>', ' ', page))
        self.assertIn('купить часы',visible.lower())
        for concept in ('совместимость','размер','доставк','возврат'):
            self.assertIn(concept,visible.lower())
        self.assertIn('модель и характеристики',visible.lower())
        self.assertIn('не подтверждены',visible.lower())
        self.assertIn(f'<link rel="canonical" href="{CANONICAL}">',page)
        self.assertIn(f'href="{AFFILIATE}"',page)
        self.assertIn('rel="sponsored nofollow noopener"',page)
        self.assertNotRegex(page,r'"(?:price|priceCurrency|ratingValue|reviewCount)"\s*:')

    def test_other_product_and_english_watch_keep_existing_title(self):
        ru = self.render('ru')['/products/import-0042/']
        en = self.render('en')['/en/products/import-0024/']
        self.assertNotIn('Купить наручные часы',ru)
        self.assertNotIn('Купить наручные часы',en)
        expected = self.translations['products'][WATCH_ID]['en']['name']
        self.assertIn(f'<h1 class="d">{html.escape(expected,quote=True)}</h1>',en)
        self.assertIn(f'href="{AFFILIATE}"',en)


if __name__ == '__main__':
    unittest.main()
