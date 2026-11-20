"""Offline proof that release copy matches six checked descriptions."""
import copy
from html import escape
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unicodedata
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'fluxixo_site/tools'))
import verify_release

LANGS = ('ru', 'en', 'pt', 'es', 'fr', 'he')


def expected_hash(text):
    return hashlib.sha256(' '.join(unicodedata.normalize('NFC', text).split()).encode('utf-8')).hexdigest()


class OriginalityReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'js').mkdir()
        self.descriptions = {lang: f'{lang}: Café brush & handle for cleaning.' for lang in LANGS}
        self.product = {'id': 'new-reviewed-product', 'description': self.descriptions['ru'],
                        'externalOriginality': {'policy': 'tavily-keyless-description-v1', 'locales': {
                            lang: {'sha256': expected_hash(text), 'checked_at': 1700000000.0}
                            for lang, text in self.descriptions.items()}}}
        self.write_pages()

    def path(self, lang):
        return self.root / ('' if lang == 'ru' else lang) / 'products' / self.product['id'] / 'index.html'

    def write_pages(self):
        for lang, text in self.descriptions.items():
            path = self.path(lang)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<html><body><section class="p-hero"><div class="p-text">'
                            '<p class="s">Headline</p><p class="t">' + escape(text) + '</p>'
                            '</div></section><p class="t">Unrelated recommendation.</p></body></html>', encoding='utf-8')

    def validate(self):
        (self.root / 'js/catalog.js').write_text('window.MIRA_CATALOG = ' + json.dumps(
            {'products': [self.product]}, ensure_ascii=False) + ';', encoding='utf-8')
        gate = getattr(verify_release, 'validate_external_originality', None)
        self.assertTrue(callable(gate), 'release needs the external-originality binding gate')
        return gate(self.root)

    def test_all_six_rendered_descriptions_and_catalog_pass(self):
        self.assertEqual([], self.validate())

    def test_missing_locale_or_evidence_blocks_publication(self):
        original = copy.deepcopy(self.product['externalOriginality'])
        for change in ('locale', 'receipt', 'sha256', 'checked_at', 'policy'):
            with self.subTest(change=change):
                self.product['externalOriginality'] = copy.deepcopy(original)
                receipt = self.product['externalOriginality']
                if change == 'locale':
                    del receipt['locales']['fr']
                elif change == 'receipt':
                    del self.product['externalOriginality']
                elif change == 'policy':
                    receipt['policy'] = 'unknown'
                else:
                    receipt['locales']['en'].pop(change)
                self.assertTrue(self.validate())

    def test_changed_rendered_paragraph_or_russian_catalog_is_rejected(self):
        self.path('pt').write_text('<div class="p-text"><p class="t">A different use claim.</p></div>', encoding='utf-8')
        self.assertTrue(any('pt' in error for error in self.validate()))
        self.write_pages()
        self.product['description'] = 'An unreviewed Russian description.'
        self.assertTrue(any('catalog' in error for error in self.validate()))

    def test_receipt_order_is_irrelevant_but_locale_hash_swapping_is_rejected(self):
        receipt = self.product['externalOriginality']
        receipt['locales'] = dict(reversed(list(receipt['locales'].items())))
        self.assertEqual([], self.validate())
        receipt['locales']['en'], receipt['locales']['fr'] = receipt['locales']['fr'], receipt['locales']['en']
        self.assertTrue(self.validate())

    def test_missing_or_ambiguous_canonical_paragraph_cannot_use_unrelated_text(self):
        for html in ('<p class="t">' + escape(self.descriptions['en']) + '</p>',
                     '<div class="p-text"><div><p class="t">' + escape(self.descriptions['en']) + '</p></div></div>',
                     '<div class="p-text"><p class="t">' + escape(self.descriptions['en']) + '</p><p class="t">Duplicate.</p></div>'):
            with self.subTest(html=html):
                self.path('en').write_text(html, encoding='utf-8')
                self.assertTrue(self.validate())
        self.path('en').unlink()
        self.assertTrue(any('en' in error for error in self.validate()))

    def test_hash_only_normalizes_nfc_and_whitespace(self):
        spec = importlib.util.find_spec('fluxixo_ai.originality_receipt')
        self.assertIsNotNone(spec, 'shared hash module is required')
        receipt = importlib.import_module('fluxixo_ai.originality_receipt')
        self.assertEqual(receipt.description_hash('  Café\tbrush\n'), expected_hash('Cafe\u0301 brush'))
        self.assertNotEqual(receipt.description_hash('Café brush.'), receipt.description_hash('café brush.'))
        self.assertNotEqual(receipt.description_hash('Brush １'), receipt.description_hash('Brush 1'))
        self.path('fr').write_text('<div class="extra p-text"><p class="t extra">\nfr: Cafe\u0301   '
                                  '<span>brush &amp; handle</span> for cleaning.\n</p></div>', encoding='utf-8')
        self.assertEqual([], self.validate())

    def test_invalid_timestamps_fail_closed(self):
        for value in (None, True, '1700000000', 0, -1, float('nan'), float('inf')):
            with self.subTest(value=value):
                self.product['externalOriginality']['locales']['he']['checked_at'] = value
                self.assertTrue(self.validate())

    def test_legacy_image_changes_remain_exempt_but_explicit_receipt_requires_review(self):
        self.product['id'] = next(iter(verify_release._load_legacy_media_baseline()))
        self.product.pop('externalOriginality')
        self.product.update(image='assets/images/new-image.webp', views=['assets/images/new-v2.webp'],
                            mediaReviewRequired=True)
        self.assertEqual([], self.validate())
        self.product['externalOriginality'] = None
        self.assertTrue(self.validate())

    def test_invalid_pinned_baseline_is_not_an_exemption(self):
        self.product['id'] = next(iter(verify_release._load_legacy_media_baseline()))
        self.product.pop('externalOriginality')
        with patch.object(verify_release, 'LEGACY_MEDIA_BASELINE_SHA256', '0' * 64):
            self.assertTrue(any('baseline' in error for error in self.validate()))


if __name__ == '__main__':
    unittest.main()
