"""The English landing and standalone full catalog must not compete in hreflang."""
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    'english_root_verifier', Path(__file__).parents[1] / 'fluxixo_site/tools/verify_release.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
ORIGIN = 'https://www.fluxixo.shop'
ALTERNATES = {
    'en': '/', 'en-US': '/', 'ru': '/catalog/', 'ru-RU': '/catalog/',
    'pt': '/pt/', 'pt-BR': '/pt/', 'es': '/es/', 'es-MX': '/es/',
    'fr': '/fr/', 'fr-FR': '/fr/', 'he': '/he/', 'he-IL': '/he/', 'x-default': '/',
}


def markup(path, lang, alternates):
    links = ''.join(f'<link rel="alternate" hreflang="{code}" href="{ORIGIN}{target}">'
                    for code, target in alternates.items())
    page = verifier.Page()
    page.feed(f'<html lang="{lang}"><head><link rel="canonical" href="{ORIGIN}{path}">'
              f'{links}</head><body><h1>Buying guides</h1></body></html>')
    return page


class EnglishRootMarkupTests(unittest.TestCase):
    def setUp(self):
        self.pages = {ORIGIN + path: markup(path, lang, ALTERNATES)
                      for path, lang in [('/', 'en'), ('/catalog/', 'ru'), ('/pt/', 'pt-BR'),
                                         ('/es/', 'es-MX'), ('/fr/', 'fr'), ('/he/', 'he')]}
        self.pages[ORIGIN + '/en/'] = markup('/en/', 'en', {})

    def validate(self):
        self.assertTrue(callable(getattr(verifier, 'validate_home_languages', None)),
                        'The release gate must check the migrated landing cluster')
        return verifier.validate_home_languages(self.pages)

    def test_migrated_cluster_and_standalone_english_catalog_pass(self):
        self.assertEqual([], self.validate())

    def test_old_russian_root_language_is_rejected(self):
        self.pages[ORIGIN + '/'] = markup('/', 'ru', ALTERNATES)
        self.assertTrue(any('HTML language' in error for error in self.validate()))

    def test_old_english_alternate_and_default_targets_are_rejected(self):
        old = {**ALTERNATES, 'en': '/en/', 'en-US': '/en/', 'x-default': '/en/'}
        self.pages[ORIGIN + '/catalog/'] = markup('/catalog/', 'ru', old)
        self.assertTrue(any('home hreflang' in error for error in self.validate()))

    def test_standalone_catalog_cannot_rejoin_the_landing_cluster(self):
        self.pages[ORIGIN + '/en/'] = markup('/en/', 'en', ALTERNATES)
        self.assertTrue(any('standalone /en/' in error for error in self.validate()))

    def test_standalone_catalog_requires_its_own_canonical(self):
        self.pages[ORIGIN + '/en/'].canonical = ORIGIN + '/'
        self.assertTrue(any('canonical' in error for error in self.validate()))

    def test_root_cannot_drop_its_alternates(self):
        self.pages[ORIGIN + '/'] = markup('/', 'en', {})
        self.assertTrue(any('home hreflang' in error for error in self.validate()))


if __name__ == '__main__':
    unittest.main()
