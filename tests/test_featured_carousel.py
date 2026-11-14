"""The fixed carousel renders existing, localized product cards without generation."""
import copy
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class CarouselParser(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.slides = []
        self.current = None
        self.text_field = None
        self.controls = {}
        self.controls_group = None
        self.slides_container = None
        self.region = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'data-carousel' in attrs:
            self.region = attrs
        if 'data-carousel-controls' in attrs:
            self.controls_group = attrs
        if 'data-carousel-slides' in attrs:
            self.slides_container = attrs
        if 'data-carousel-slide' in attrs:
            self.current = {'attrs': attrs, 'name': '', 'description': '', 'caption': '', 'links': [], 'images': []}
            self.slides.append(self.current)
        if tag == 'button':
            for name in ('prev', 'next', 'toggle'):
                if 'data-carousel-' + name in attrs:
                    self.controls[name] = attrs
        if self.current is not None:
            if tag == 'h2':
                self.text_field = 'name'
            elif tag == 'p' and attrs.get('class') in ('t', 'day-caption'):
                self.text_field = 'description' if attrs['class'] == 't' else 'caption'
            elif tag == 'a':
                self.current['links'].append(attrs)
            elif tag == 'img':
                self.current['images'].append(attrs)

    def handle_endtag(self, tag):
        if tag in ('h2', 'p'):
            self.text_field = None
        if tag == 'article':
            self.current = None

    def handle_data(self, text):
        if self.current is not None and self.text_field:
            self.current[self.text_field] += text


class FeaturedCarouselTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('featured_carousel_builder_test', ROOT / 'fluxixo_site/redesign/build_redesign.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.products, cls.translations = cls.module.load()

    def render(self, lang='en', products=None, translations=None, day='2026-11-14'):
        module = self.module
        pages = {}
        site = module.Site(products if products is not None else self.products,
                           translations if translations is not None else self.translations, lang)
        # Capture only the filesystem boundary; product selection and all HTML rendering stay real.
        with patch.object(module, 'write', side_effect=lambda path, html: pages.update({path: html})), \
                patch.object(module, 'countdown_metadata', return_value={'published_day': day, 'due_day': day}):
            site.build_home()
        return CarouselParser(pages['/catalog/' if lang == 'ru' else f'/{lang}/'])

    def test_seven_existing_cards_keep_image_text_and_both_urls_together(self):
        catalog = {product['id']: product for product in self.products}
        order = None
        for lang in ('ru', 'en', 'es', 'pt', 'fr', 'he'):
            with self.subTest(lang=lang):
                page = self.render(lang)
                self.assertEqual(len(page.slides), 7)
                ids = [slide['attrs']['data-product-id'] for slide in page.slides]
                self.assertEqual(len(set(ids)), 7)
                if order is None:
                    order = ids
                self.assertEqual(ids, order)
                self.assertNotIn('hidden', page.slides[0]['attrs'])
                self.assertTrue(all('hidden' in slide['attrs'] for slide in page.slides[1:]))
                for slide, pid in zip(page.slides, ids):
                    product = catalog[pid]
                    text = product if lang == 'ru' else self.translations['products'][pid][lang]
                    self.assertEqual(slide['name'], text['name'])
                    self.assertEqual(slide['caption'], ' '.join(text['headline']))
                    self.assertEqual(slide['description'], text['description'])
                    self.assertEqual(len(slide['images']), 1)
                    self.assertEqual(slide['images'][0]['alt'], text['name'])
                    self.assertIn(Path(product['image']).stem, Path(slide['images'][0]['src']).stem)
                    detail = ('' if lang == 'ru' else '/' + lang) + '/products/' + pid + '/'
                    self.assertEqual([link['href'] for link in slide['links']], [detail, detail, product['affiliateUrl']])
                    self.assertEqual(set(slide['links'][-1]['rel'].split()), {'sponsored', 'nofollow', 'noopener'})

    def test_date_order_and_catalog_growth_do_not_change_the_fixed_selection(self):
        baseline = self.render('ru')
        expected = [s['attrs']['data-product-id'] for s in baseline.slides]
        self.assertEqual(len(expected), 7)
        products = copy.deepcopy(list(reversed(self.products)))
        extra = copy.deepcopy(products[0])
        extra['id'] = 'new-unpinned-product'
        products.insert(0, extra)
        changed = self.render('ru', products=products, day='2030-02-01')
        self.assertEqual([s['attrs']['data-product-id'] for s in changed.slides], expected)

    def test_two_pinned_png_cutouts_bypass_old_thumbnails_without_heavy_shadow(self):
        cutouts = {
            'find-063-cable-tester': '/assets/featured/find-063-cable-tester-clean-v1.png',
            'find-023-cat-laser': '/assets/featured/find-023-cat-laser-clean-v1.png',
        }
        for lang in ('ru', 'en', 'es', 'pt', 'fr', 'he'):
            with self.subTest(lang=lang):
                page = self.render(lang)
                self.assertEqual(len(page.slides), 7)
                replacements = []
                for slide in page.slides:
                    pid = slide['attrs']['data-product-id']
                    image = slide['images'][0]
                    self.assertNotIn('cut', image.get('class', '').split())
                    if pid in cutouts:
                        self.assertEqual(image['src'], cutouts[pid])
                        self.assertIn('day-cutout', image.get('class', '').split())
                        replacements.append(pid)
                    else:
                        self.assertNotIn('/assets/featured/', image['src'])
                        self.assertNotIn('/assets/originals/', image['src'])
                self.assertEqual(set(replacements), set(cutouts))

    def test_fixed_cutout_sources_have_transparency_and_copy_byte_for_byte(self):
        source = ROOT / 'fluxixo_site/redesign/static/featured'
        names = ('find-063-cable-tester-clean-v1.png', 'find-023-cat-laser-clean-v1.png')
        for name in names:
            asset = source / name
            self.assertTrue(asset.is_file(), f'Missing curated cutout source: {asset}')
            self.assertGreater(asset.stat().st_size, 0)
            with Image.open(asset) as image:
                self.assertEqual(image.format, 'PNG')
                self.assertIn('A', image.getbands())
                low, high = image.getchannel('A').getextrema()
                self.assertLess(low, 255, 'Cutout background must actually be transparent')
                self.assertGreater(high, 0, 'Product must not be fully transparent')
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'site'
            self.module.copy_featured_images(output)
            for name in names:
                copied = output / 'assets/featured' / name
                self.assertEqual(copied.read_bytes(), (source / name).read_bytes())

    def test_missing_cutout_source_stops_before_copying_any_output(self):
        with tempfile.TemporaryDirectory() as scratch:
            source, output = Path(scratch) / 'source', Path(scratch) / 'site'
            source.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, 'find-063-cable-tester-clean-v1.png'):
                self.module.copy_featured_images(output, source)
            self.assertFalse(output.exists())

    def test_missing_pinned_product_fails_instead_of_silently_substituting(self):
        selected = self.render('ru').slides
        self.assertEqual(len(selected), 7)
        missing = selected[0]['attrs']['data-product-id']
        with self.assertRaisesRegex(ValueError, missing):
            self.render('ru', products=[p for p in self.products if p['id'] != missing])

    def test_missing_pinned_translation_cannot_create_a_broken_localized_slide(self):
        selected = self.render('en').slides
        self.assertEqual(len(selected), 7)
        missing = selected[0]['attrs']['data-product-id']
        translations = copy.deepcopy(self.translations)
        del translations['products'][missing]['en']
        with self.assertRaisesRegex(ValueError, missing):
            self.render('en', translations=translations)

    def test_controls_are_localized_and_no_script_initial_state_is_accessible(self):
        for lang in ('ru', 'en', 'es', 'pt', 'fr', 'he'):
            with self.subTest(lang=lang):
                page = self.render(lang)
                self.assertIsNotNone(page.region)
                self.assertEqual(page.region['role'], 'region')
                self.assertTrue(page.region['aria-label'])
                self.assertTrue(page.region['aria-roledescription'])
                self.assertEqual(set(page.controls), {'prev', 'next'})
                self.assertNotIn('toggle', page.controls)
                self.assertIn('hidden', page.controls_group)
                self.assertEqual(page.slides_container['aria-live'], 'off')
                for attrs in page.controls.values():
                    self.assertEqual(attrs['type'], 'button')
                    self.assertTrue(attrs['aria-label'])


if __name__ == '__main__':
    unittest.main()
