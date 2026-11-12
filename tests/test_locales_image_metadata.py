"""Tests for 6-language per-image alt/caption metadata, schema ImageObject resolution, and FOUC CSS/early.js invariants."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / 'fluxixo_site' / 'tools'
REDESIGN_DIR = REPO_ROOT / 'fluxixo_site' / 'redesign'
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import check_texts  # noqa: E402
import locales as L  # noqa: E402


class LocalesImageMetadataTests(unittest.TestCase):
    def test_editorial_image_alt_distinct_across_roles_and_clean_all_6_langs(self):
        names = {
            'ru': ('Складная подставка', 'Стол'),
            'en': ('Folding Stand', 'Desk'),
            'pt': ('Suporte Dobrável', 'Mesa'),
            'es': ('Soporte Plegable', 'Escritorio'),
            'fr': ('Support Pliant', 'Bureau'),
            'he': ('מעמד מתקפל', 'שולחן'),
        }
        roles = ('hero', 'view', 'card', 'spotlight', 'rope', 'mini', 'original')
        problems: list[str] = []

        for lang, (name, cat) in names.items():
            seen_alts: set[str] = set()
            for role in roles:
                alt = L.editorial_image_alt(name, cat, lang, role=role, view_index=1, total_views=3)
                cap = L.editorial_image_caption(name, cat, lang, role=role, view_index=1)
                self.assertTrue(alt.strip(), f'{lang}.{role} empty alt')
                self.assertTrue(cap.strip(), f'{lang}.{role} empty caption')
                seen_alts.add(alt)
                check_texts.check_string(alt, lang, f'alt.{lang}.{role}', problems)
                check_texts.check_string(cap, lang, f'cap.{lang}.{role}', problems)
            self.assertEqual(len(roles), len(seen_alts), f'{lang} roles produced duplicate alts: {seen_alts}')
            view2 = L.editorial_image_alt(name, cat, lang, role='view', view_index=2, total_views=3)
            view3 = L.editorial_image_alt(name, cat, lang, role='view', view_index=3, total_views=3)
            self.assertNotEqual(view2, view3)

        self.assertEqual([], problems, f'Text hygiene problems in image metadata: {problems}')

    def test_item_page_schema_resolves_real_image_dimensions_and_associated_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            img_dir = dist / 'assets' / 'images'
            img_dir.mkdir(parents=True)
            hero_rel = 'assets/images/test-stand.webp'
            view2_rel = 'assets/images/test-stand-2.webp'
            Image.new('RGBA', (800, 600), (20, 30, 40, 255)).save(dist / hero_rel, format='WEBP')
            Image.new('RGBA', (1200, 900), (30, 40, 50, 255)).save(dist / view2_rel, format='WEBP')

            self.assertEqual((800, 600), L.resolve_image_size(dist, hero_rel))
            self.assertEqual((1200, 900), L.resolve_image_size(dist, view2_rel))

            schema = L.item_page_schema(
                'https://www.fluxixo.shop',
                '/en/products/test-stand/',
                'Folding Stand',
                'Compact folding desk stand.',
                hero_rel,
                'en',
                'Folding Stand — Desk (Main)',
                [('Home', '/en/'), ('Stand', '/en/products/test-stand/')],
                extra_images=[view2_rel],
                image_name='Folding Stand — studio cutout',
                dist_root=dist,
            )
            graph = schema['@graph']
            item_page = next(node for node in graph if node.get('@type') == 'ItemPage')
            primary = item_page['primaryImageOfPage']
            self.assertEqual('ImageObject', primary['@type'])
            self.assertEqual(800, primary['width'])
            self.assertEqual(600, primary['height'])
            self.assertTrue(primary['representativeOfPage'])
            self.assertIn('Folding Stand', primary['name'])
            assoc = item_page.get('associatedMedia') or []
            self.assertEqual(1, len(assoc))
            self.assertEqual(1200, assoc[0]['width'])
            self.assertEqual(900, assoc[0]['height'])
            self.assertFalse(assoc[0]['representativeOfPage'])
            self.assertNotEqual(primary['caption'], assoc[0]['caption'])

    def test_fouc_css_and_early_js_invariants(self):
        early = (REDESIGN_DIR / 'static' / 'early.js').read_text(encoding='utf-8')
        self.assertIn("document.documentElement.classList.add('js')", early)
        self.assertIn('DOMContentLoaded', early)
        self.assertIn("classList.add('anim')", early)

        css = (REDESIGN_DIR / 'static' / 'style.css').read_text(encoding='utf-8')
        self.assertRegex(css, r'\.js\s+\.day\s*\{[^}]*--p\s*:\s*0')
        self.assertNotIn('.js .rv{opacity:0', css.replace('\n', ' '))
        langs_rest = re.search(r'\.js\s+\.langs\s*\{([^}]*)\}', css)
        self.assertIsNotNone(langs_rest)
        self.assertNotIn('100vmax', langs_rest.group(1))
        self.assertRegex(css, r'\.js\s+\.langs\.open\s*\{[^}]*100vmax')


if __name__ == '__main__':
    unittest.main()
