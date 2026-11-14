"""A release may not hide new Russian products from the Yandex sitemap."""
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    'verify_release_yandex', Path(__file__).parents[1] / 'fluxixo_site/tools/verify_release.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
ORIGIN = 'https://www.fluxixo.shop'


class RussianSitemapGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.release = Path(self.temp.name)
        self.urls = [ORIGIN + p for p in ('/', '/catalog/', '/products/new-tool/', '/en/', '/en/products/new-tool/')]

    def write_map(self, urls):
        root = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        for url in urls:
            row = ET.SubElement(root, 'url')
            ET.SubElement(row, 'loc').text = url
            ET.SubElement(row, 'lastmod').text = '2026-11-10T17:49:00+00:00'
        ET.ElementTree(root).write(self.release / 'sitemap-ru.xml', encoding='utf-8')

    def validate(self):
        validator = getattr(verifier, 'validate_ru_sitemap', None)
        self.assertIsNotNone(validator, 'Release gate must validate RU sitemap contents, not only its existence')
        return validator(self.release, self.urls)

    def test_complete_ru_map_passes_without_foreign_locale_pages(self):
        self.write_map(self.urls[1:3])
        self.assertEqual([], self.validate())

    def test_missing_new_product_is_rejected(self):
        self.write_map(self.urls[1:2])
        errors = self.validate()
        self.assertTrue(any('missing' in err and '/products/new-tool/' in err for err in errors), errors)

    def test_foreign_locale_url_is_rejected(self):
        self.write_map(self.urls[1:3] + [self.urls[3]])
        self.assertTrue(any('unexpected' in err and '/en/' in err for err in self.validate()))

    def test_english_root_is_rejected_from_russian_map(self):
        self.write_map(self.urls[:3])
        self.assertTrue(any('unexpected' in err and ORIGIN + '/' in err for err in self.validate()))

    def test_duplicate_or_noncanonical_ru_url_is_rejected(self):
        self.write_map(self.urls[1:3] + [self.urls[2], 'http://fluxixo.shop/catalog/'])
        errors = self.validate()
        self.assertTrue(any('duplicate' in err for err in errors), errors)
        self.assertTrue(any('unexpected' in err for err in errors), errors)

    def test_malformed_map_becomes_release_error(self):
        (self.release / 'sitemap-ru.xml').write_text('<urlset>', encoding='utf-8')
        self.assertTrue(any('unreadable' in err for err in self.validate()))


if __name__ == '__main__':
    unittest.main()
