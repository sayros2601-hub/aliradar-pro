"""Sitemap dates follow the published pages: unchanged pages keep their date, edited ones get a new one."""
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fluxixo_site/tools'))
import write_sitemaps  # noqa: E402


class SitemapDateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dist = Path(self.tmp.name) / 'dist'
        for path in ('', 'es/', 'products/a/'):
            (self.dist / path).mkdir(parents=True, exist_ok=True)
            (self.dist / path / 'index.html').write_text(f'<p>{path}</p>', encoding='utf-8')
        self.state = Path(self.tmp.name) / 'state.json'
        replacement = patch.object(write_sitemaps, 'STATE', self.state)
        replacement.start()
        self.addCleanup(replacement.stop)
        self.routes = ['/', '/es/', '/products/a/']

    def dates(self, name='sitemap.xml'):
        tree = ET.parse(self.dist / name)
        return {u.findtext('{*}loc'): u.findtext('{*}lastmod') for u in tree.getroot()}

    def test_rebuild_without_changes_keeps_dates_and_an_edit_moves_only_that_page(self):
        self.assertEqual(3, write_sitemaps.write_sitemaps(self.dist, self.routes))
        first = self.dates()
        self.assertEqual(0, write_sitemaps.write_sitemaps(self.dist, self.routes))
        self.assertEqual(first, self.dates())
        (self.dist / 'products/a/index.html').write_text('<p>new copy</p>', encoding='utf-8')
        state = json.loads(self.state.read_text(encoding='utf-8'))
        state['/products/a/']['lastmod'] = state['/']['lastmod'] = '2026-01-01T00:00:00+00:00'
        self.state.write_text(json.dumps(state), encoding='utf-8')
        self.assertEqual(1, write_sitemaps.write_sitemaps(self.dist, self.routes))
        dates = self.dates()
        self.assertEqual('2026-01-01T00:00:00+00:00', dates['https://www.fluxixo.shop/'])
        self.assertNotEqual('2026-01-01T00:00:00+00:00', dates['https://www.fluxixo.shop/products/a/'])

    def test_interim_map_reuses_stored_dates_and_leaves_state_alone(self):
        write_sitemaps.write_sitemaps(self.dist, self.routes)
        before = self.state.read_bytes()
        (self.dist / 'index.html').write_text('<p>plain page before the design</p>', encoding='utf-8')
        write_sitemaps.write_sitemaps(self.dist, self.routes, update_state=False)
        self.assertEqual(before, self.state.read_bytes())

    def test_russian_map_has_only_russian_pages(self):
        write_sitemaps.write_sitemaps(self.dist, self.routes)
        self.assertEqual({'https://www.fluxixo.shop/', 'https://www.fluxixo.shop/products/a/'}, set(self.dates('sitemap-ru.xml')))


if __name__ == '__main__':
    unittest.main()
