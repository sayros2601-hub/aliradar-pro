"""Offline release checks for the pinned, unchanged legacy-gallery exception."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'fluxixo_site/tools'))
import verify_release


class LegacyMediaBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'js').mkdir()
        (self.root / 'assets/images').mkdir(parents=True)
        self.product = {'id': 'old-item', 'sourceProductId': '123', 'sourceTitle': 'Original product',
                        'sourceImageUrl': 'https://ae01.alicdn.com/original.png',
                        'sourceDetailUrl': 'https://www.aliexpress.com/item/123.html',
                        'image': 'assets/images/old.png', 'views': []}
        image = Image.new('RGBA', (12, 12))
        image.putpixel((6, 6), (240, 80, 20, 255))
        image.save(self.root / self.product['image'])
        identity = [self.product.get(key) for key in
                    ('id', 'sourceProductId', 'sourceTitle', 'sourceImageUrl', 'sourceDetailUrl')]
        baseline = {'version': 1, 'source_commit': '8a4caaf152ae7b382e8577a535091876ee15ff34',
                    'products': {'old-item': {
                        'identity_sha256': hashlib.sha256(json.dumps(identity, ensure_ascii=False,
                            separators=(',', ':')).encode()).hexdigest(),
                        'gallery': [[self.product['image'], hashlib.sha256(
                            (self.root / self.product['image']).read_bytes()).hexdigest()]]}}}
        raw = json.dumps(baseline, ensure_ascii=False).encode()
        self.baseline = self.root / 'baseline.json'
        self.baseline.write_bytes(raw)
        for name, value in (('LEGACY_MEDIA_BASELINE_PATH', self.baseline),
                            ('LEGACY_MEDIA_BASELINE_SHA256', hashlib.sha256(raw).hexdigest())):
            patcher = patch.object(verify_release, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

    def validate(self, product=None):
        (self.root / 'js/catalog.js').write_text('window.CATALOG = ' + json.dumps(
            {'products': [self.product if product is None else product]}) + ';', encoding='utf-8')
        return verify_release.validate_transparent_product_images(self.root)

    def test_unknown_untagged_gallery_cannot_skip_review(self):
        product = {**self.product, 'id': 'new-item', 'sourceProductId': '456'}
        self.assertTrue(any('review' in error for error in self.validate(product)))

    def test_original_single_image_gallery_is_grandfathered_only_unchanged(self):
        self.assertEqual([], self.validate())
        Image.new('RGBA', (12, 12), (0, 0, 0, 0)).save(self.root / self.product['image'])
        self.assertTrue(any('review' in error for error in self.validate()))

    def test_removed_review_tags_do_not_grandfather_modified_legacy_images(self):
        product = copy.deepcopy(self.product)
        product.update(mediaReviewRequired=True, mediaReview={'accepted': True})
        Image.new('RGBA', (14, 14)).save(self.root / product['image'])
        self.assertTrue(self.validate(product))
        del product['mediaReviewRequired']
        del product['mediaReview']
        self.assertTrue(any('review' in error for error in self.validate(product)))

    def test_changed_identity_or_gallery_order_requires_review(self):
        for change in ({'sourceTitle': 'Another product'}, {'sourceProductId': '456'},
                       {'views': [self.product['image']]}, {'mediaReviewRequired': False}):
            with self.subTest(change=change):
                self.assertTrue(any('review' in error for error in self.validate({**self.product, **change})))

    def test_missing_legacy_file_is_rejected(self):
        (self.root / self.product['image']).unlink()
        self.assertTrue(self.validate())

    def test_modified_baseline_cannot_grandfather_new_assets(self):
        self.baseline.write_bytes(self.baseline.read_bytes() + b' ')
        self.assertTrue(any('baseline' in error for error in self.validate()))


if __name__ == '__main__':
    unittest.main()
