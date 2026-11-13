"""Google Search Central structured data and SEO regression tests."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site/tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import locales  # noqa: E402
import market_seo  # noqa: E402
import verify_release  # noqa: E402


class GoogleSeoComplianceTests(unittest.TestCase):
    def test_build_image_object_omits_licensable_triggers(self):
        obj = locales.build_image_object(
            'https://www.fluxixo.shop',
            'assets/images/sample.webp',
            name='Sample Gadget',
            caption='Sample Gadget — studio visual',
            size=(800, 800),
            thumb_rel='assets/thumbs/sample-480.webp',
        )
        for trigger in verify_release.IMAGE_LICENSE_TRIGGERS:
            self.assertNotIn(trigger, obj)
        self.assertEqual([], verify_release.validate_google_structured_data(obj))

    def test_item_page_schema_passes_google_rules_for_primary_and_extra_views(self):
        schema = locales.item_page_schema(
            'https://www.fluxixo.shop',
            '/en/products/sample/',
            'Sample Gadget | FLUXIXO',
            'Clean studio preview of Sample Gadget.',
            'assets/images/sample.webp',
            'en',
            'Sample Gadget — studio visual',
            [('FLUXIXO', '/'), ('Catalog', '/en/'), ('Sample Gadget', '/en/products/sample/')],
            extra_images=['assets/images/sample.webp', 'assets/images/sample-v2.webp'],
            image_name='Sample Gadget',
        )
        self.assertEqual([], verify_release.validate_google_structured_data(schema))

    def test_validator_catches_partial_image_license_metadata(self):
        partial = {
            '@context': 'https://schema.org',
            '@type': 'ImageObject',
            'contentUrl': 'https://www.fluxixo.shop/assets/images/sample.webp',
            'creditText': 'FLUXIXO Studio',
        }
        errs = verify_release.validate_google_structured_data(partial)
        self.assertIn('incomplete image license metadata in JSON-LD', errs)

        complete = {
            **partial,
            'creator': {'@type': 'Organization', 'name': 'FLUXIXO'},
            'copyrightNotice': '© 2026 FLUXIXO',
            'license': 'https://www.fluxixo.shop/about/#license',
            'acquireLicensePage': 'https://www.fluxixo.shop/about/#license',
        }
        self.assertEqual([], verify_release.validate_google_structured_data(complete))

    def test_validator_checks_video_breadcrumb_article_and_faq(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            video_dir = dist / 'assets/video'
            video_dir.mkdir(parents=True)
            (video_dir / 'sample.mp4').write_bytes(b'ftypmp42')
            (video_dir / 'sample.poster.jpg').write_bytes(b'jpg')
            _, vid_schema = market_seo.video_block_and_schema(
                'https://www.fluxixo.shop', dist, {'id': 'sample'}, 'Sample', 'Quick showcase clip.', 'en', 'assets/images/sample.webp'
            )
            self.assertEqual([], verify_release.validate_google_structured_data(vid_schema))

        bad_video = {
            '@type': 'VideoObject',
            'name': 'Demo',
            'description': 'Clip',
            'thumbnailUrl': ['https://www.fluxixo.shop/assets/thumbs/sample-480.webp'],
            'contentUrl': 'https://www.fluxixo.shop/assets/video/sample.mp4',
            'uploadDate': '2026-11-01T10:00:00',  # Missing timezone!
        }
        self.assertIn('invalid VideoObject structured data', verify_release.validate_google_structured_data(bad_video))

        bad_crumbs = {
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 2, 'name': 'Home', 'item': 'https://www.fluxixo.shop/'},
            ],
        }
        self.assertIn('invalid BreadcrumbList structured data', verify_release.validate_google_structured_data(bad_crumbs))

        bad_article = {
            '@type': 'Article',
            'headline': 'Guide',
            'datePublished': 'not-a-date',
        }
        self.assertIn('invalid Article structured data', verify_release.validate_google_structured_data(bad_article))

        bad_faq = {
            '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question', 'name': 'How?', 'acceptedAnswer': {'@type': 'Answer', 'text': ''}}],
        }
        self.assertIn('invalid FAQPage structured data', verify_release.validate_google_structured_data(bad_faq))


if __name__ == '__main__':
    unittest.main()
