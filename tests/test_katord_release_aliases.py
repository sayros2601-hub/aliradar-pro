"""Keep the historical KATORD URLs attached to the same active supplier item."""
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    'verify_release_katord', Path(__file__).parents[1] / 'fluxixo_site/tools/verify_release.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)

ORIGIN = 'https://www.fluxixo.shop'
OLD_SLUG = 'katord-1200mbps-wireless-wifi-repeater-2-4g-5'
RU_ALIAS = f'/ru/deals/{OLD_SLUG}'
RU_CARD = '/products/katord-wifi-repeater/'


class KatordMigrationGateTests(unittest.TestCase):
    def setUp(self):
        self.product = {'id': 'katord-wifi-repeater', 'sourceProductId': '1005011800659333', 'demo': False}
        self.rules = []
        self.pages = {}
        for old_prefix, new_prefix in (
                ('', '/en'), ('/ru', ''), ('/en', '/en'), ('/es', '/es'),
                ('/fr', '/fr'), ('/he', '/he'), ('/pt', '/pt')):
            target = f'{new_prefix}{RU_CARD}'
            canonical = ORIGIN + target
            page = verifier.Page()
            page.feed(f'<link rel="canonical" href="{canonical}">')
            self.pages[canonical] = page
            for suffix in ('', '/', '.html'):
                self.rules.append(f'{old_prefix}/deals/{OLD_SLUG}{suffix} {target} 301')

    def validate(self):
        return verifier.validate_katord_aliases(self.rules, {'products': [self.product]}, self.pages)

    def test_direct_permanent_aliases_pass_with_unrelated_fallbacks(self):
        self.rules += ['/ru/* /catalog/ 301', '/sitemap /sitemap.xml 301']
        self.assertEqual([], self.validate())

    def test_missing_html_variant_cannot_fall_back_to_catalog(self):
        self.rules.remove(f'{RU_ALIAS}.html {RU_CARD} 301')
        self.rules.append('/ru/* /catalog/ 301')
        self.assertTrue(any(f'{RU_ALIAS}.html' in error and '/catalog/' in error for error in self.validate()))

    def test_other_product_or_temporary_redirect_is_rejected(self):
        index = self.rules.index(f'{RU_ALIAS} {RU_CARD} 301')
        for target, status in (('/products/another-item/', 301), (RU_CARD, 302)):
            with self.subTest(target=target, status=status):
                self.rules[index] = f'{RU_ALIAS} {target} {status}'
                self.assertTrue(any(f'{target} {status}' in error for error in self.validate()))

    def test_earlier_exact_wildcard_or_placeholder_shadows_correct_rule(self):
        for source in (RU_ALIAS, '/ru/*', '/:locale/deals/:slug', 'ru/deals/*'):
            with self.subTest(source=source):
                self.rules.insert(0, f'{source} /catalog/ 301')
                self.assertTrue(any(RU_ALIAS in error and '/catalog/' in error for error in self.validate()))
                self.rules.pop(0)

    def test_alias_after_pages_dynamic_rule_limit_is_rejected(self):
        self.rules[:0] = ['/unrelated/* /catalog/ 301',
                          *(f'/unrelated/{i} /catalog/ 301' for i in range(99))]
        self.assertTrue(any(RU_ALIAS in error and 'no matching rule' in error for error in self.validate()))

    def test_destination_must_be_present_and_self_canonical(self):
        canonical = ORIGIN + RU_CARD
        self.pages[canonical].canonical = ORIGIN + '/catalog/'
        self.assertTrue(any('self-canonical' in error and RU_CARD in error for error in self.validate()))
        del self.pages[canonical]
        self.assertTrue(any('self-canonical' in error and RU_CARD in error for error in self.validate()))

    def test_destination_cannot_add_a_second_redirect(self):
        self.rules.append(f'{RU_CARD} /catalog/ 301')
        self.assertTrue(any('one hop' in error and RU_CARD in error for error in self.validate()))

    def test_catalog_retirement_turns_off_the_gate(self):
        self.rules.clear()
        for retired in ({'demo': True}, {'sourceProductId': '9999999999999'}):
            with self.subTest(retired=retired):
                self.product.update(retired)
                self.assertEqual([], self.validate())
                self.product.update(sourceProductId='1005011800659333', demo=False)


if __name__ == '__main__':
    unittest.main()
