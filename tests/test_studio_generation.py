"""Tests for pure-Pillow studio alpha extraction, Cloudflare Workers AI cutout generation, and autonomous media prep."""
from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from PIL import Image, ImageDraw

from fluxixo_ai import autonomous, image_studio as ims


def _studio_white_scene(
    size: int = 640,
    *,
    variant: int = 0,
) -> Image.Image:
    """Render a sharp patterned studio object on pure solid #FFFFFF background."""
    img = Image.new('RGB', (size, size), (255, 255, 255))
    d = ImageDraw.Draw(img)
    rng = random.Random(100 + variant)
    if variant == 0:
        d.rounded_rectangle((110, 140, 530, 500), radius=34, fill=(38, 56, 92), outline=(22, 30, 48), width=6)
        # Enclosed pure white highlight panel inside closed perimeter
        d.rounded_rectangle((170, 200, 320, 350), radius=18, fill=(255, 255, 255), outline=(48, 66, 102), width=4)
        for y in range(210, 470, 28):
            for x in range(345, 500, 28):
                c = rng.randint(135, 235)
                d.rectangle((x, y, x + 16, y + 16), fill=(c, c - 30, 72))
        d.ellipse((215, 385, 295, 465), fill=(224, 108, 42), outline=(24, 28, 36), width=4)
    elif variant == 1:
        # Distinct 45-degree diagonal silhouette
        d.polygon([(140, 470), (220, 540), (530, 210), (450, 140)], fill=(48, 62, 74))
        d.ellipse((125, 420, 275, 555), fill=(212, 118, 48), outline=(28, 34, 42), width=5)
        for step in range(8):
            cx = 230 + step * 34
            cy = 440 - step * 34
            c = rng.randint(150, 240)
            d.rectangle((cx - 12, cy - 12, cx + 12, cy + 12), fill=(c, c, c - 20))
    else:
        # Distinct close-up circular dial / mechanism detail
        d.ellipse((90, 90, 550, 550), fill=(52, 46, 58), outline=(20, 20, 26), width=8)
        d.ellipse((150, 150, 490, 490), fill=(226, 228, 234), outline=(36, 44, 58), width=6)
        for idx in range(12):
            ang = idx * 30
            d.pieslice((190, 190, 450, 450), ang, ang + 14, fill=(38, 128, 178) if idx % 2 == 0 else (218, 92, 54))
        d.ellipse((265, 265, 375, 375), fill=(28, 32, 40))
    return img


def _jpeg_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=94)
    return buf.getvalue()


class _FakeHttpResponse:
    def __init__(self, body: bytes, content_type: str = 'application/json') -> None:
        self._body = body
        self.headers = {'Content-Type': content_type}
        self.status = 200

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> '_FakeHttpResponse':
        return self

    def __exit__(self, *_args) -> None:
        return None


class StudioGenerationTests(unittest.TestCase):
    def test_extract_isolated_studio_alpha_crisp_cutout_and_enclosed_highlights(self):
        scene = _studio_white_scene(640, variant=0)
        cutout = ims.extract_isolated_studio_alpha(scene)
        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((640, 640), cutout.size)
        self.assertEqual((0, 255), cutout.getchannel('A').getextrema())

        for corner in ((0, 0), (639, 0), (0, 639), (639, 639), (40, 320)):
            self.assertEqual(0, cutout.getpixel(corner)[3], f'expected transparent background at {corner}')

        # Solid colored body and enclosed pure white highlight inside closed perimeter both stay opaque
        self.assertEqual(255, cutout.getpixel((140, 180))[3])
        self.assertEqual(255, cutout.getpixel((245, 275))[3], 'enclosed white highlight inside object was punched out')
        self.assertEqual((255, 255, 255, 255), cutout.getpixel((245, 275)))

    def test_resolve_cloudflare_ai_token_precedence_and_wrangler_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            appdata = Path(tmp) / 'appdata'
            cfg = appdata / 'xdg.config' / '.wrangler' / 'config' / 'default.toml'
            cfg.parent.mkdir(parents=True)
            cfg.write_text('oauth_token = "wrangler-oauth-123"\n', encoding='utf-8')

            with patch.dict(
                os.environ,
                {'CLOUDFLARE_AI_TOKEN': 'ai-tok', 'CLOUDFLARE_API_TOKEN': 'api-tok', 'APPDATA': str(appdata)},
                clear=False,
            ):
                self.assertEqual(('explicit-tok', 'fluxixo-image-studio/1.0'), ims.resolve_cloudflare_ai_token('explicit-tok'))
                self.assertEqual(('ai-tok', 'fluxixo-image-studio/1.0'), ims.resolve_cloudflare_ai_token())

            with patch.dict(
                os.environ,
                {'CLOUDFLARE_AI_TOKEN': '', 'CLOUDFLARE_API_TOKEN': 'api-tok', 'APPDATA': str(appdata)},
                clear=False,
            ):
                self.assertEqual(('api-tok', 'fluxixo-image-studio/1.0'), ims.resolve_cloudflare_ai_token())

            with patch.dict(
                os.environ,
                {'CLOUDFLARE_AI_TOKEN': '', 'CLOUDFLARE_API_TOKEN': '', 'APPDATA': str(appdata), 'XDG_CONFIG_HOME': ''},
                clear=False,
            ):
                self.assertEqual(('wrangler-oauth-123', 'wrangler/4.151.3'), ims.resolve_cloudflare_ai_token())

            with patch.dict(
                os.environ,
                {'CLOUDFLARE_AI_TOKEN': '', 'CLOUDFLARE_API_TOKEN': '', 'APPDATA': str(Path(tmp) / 'missing'), 'XDG_CONFIG_HOME': ''},
                clear=False,
            ):
                self.assertEqual(('', ''), ims.resolve_cloudflare_ai_token())

    def test_generate_studio_cutout_mocked_json_base64_and_jpeg_fallback(self):
        ref = _studio_white_scene(640, variant=0)
        generated_bytes = _jpeg_bytes(_studio_white_scene(800, variant=1))
        b64_payload = json.dumps({'success': True, 'result': {'image': base64.b64encode(generated_bytes).decode('ascii')}}).encode('utf-8')

        seen_requests = []

        def fake_urlopen_primary(req, timeout=45):
            seen_requests.append((req.full_url, dict(req.header_items()), req.data))
            return _FakeHttpResponse(b64_payload, content_type='application/json')

        with patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen_primary):
            cutout = ims.generate_studio_cutout(
                'Telescopic inspection tool',
                reference_image=ref,
                token='test-cf-token',
            )

        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((1254, 1254), cutout.size)
        self.assertEqual((0, 255), cutout.getchannel('A').getextrema())
        ok, metrics = ims.verify_studio_image(cutout, composed=cutout)
        self.assertTrue(ok, f'Generated cutout failed QA: {metrics}')

        url, headers, body = seen_requests[0]
        self.assertIn('/ai/run/@cf/black-forest-labs/flux-2-klein-4b', url)
        self.assertEqual('Bearer test-cf-token', headers['Authorization'])
        self.assertIn('multipart/form-data; boundary=', headers['Content-type'])
        self.assertIn(b'name="input_image_0"', body)

        # Fallback to flux-1-schnell JSON returning raw JPEG binary bytes when flux-2 multipart fails
        fallback_calls = []

        def fake_urlopen_fallback(req, timeout=45):
            fallback_calls.append((req.full_url, dict(req.header_items()), req.data))
            if 'flux-2-klein-4b' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 502, 'Bad Gateway', {}, None)
            return _FakeHttpResponse(generated_bytes, content_type='image/jpeg')

        with patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen_fallback):
            cutout_fb = ims.generate_studio_cutout(
                'Telescopic inspection tool',
                reference_image=None,
                token='test-cf-token',
            )

        self.assertEqual(2, len(fallback_calls))
        self.assertIn('@cf/black-forest-labs/flux-1-schnell', fallback_calls[1][0])
        self.assertEqual('application/json', fallback_calls[1][1]['Content-type'])
        self.assertEqual((1254, 1254), cutout_fb.size)
        ok_fb, metrics_fb = ims.verify_studio_image(cutout_fb, composed=cutout_fb)
        self.assertTrue(ok_fb, f'Fallback cutout failed QA: {metrics_fb}')

        # Fallback to Cloudflare Autopilot Worker when direct REST returns 401/403 (Pages-scoped token)
        worker_calls = []

        def fake_urlopen_worker(req, timeout=45):
            worker_calls.append((req.full_url, dict(req.header_items()), req.data))
            if 'api.cloudflare.com' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 401, 'Unauthorized', {}, None)
            return _FakeHttpResponse(generated_bytes, content_type='image/jpeg')

        with patch.dict(os.environ, {'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev'}, clear=False), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen_worker):
            cutout_worker = ims.generate_studio_cutout(
                'Telescopic inspection tool',
                reference_image=ref,
                token='pages-only-token',
            )

        self.assertEqual(3, len(worker_calls))
        self.assertTrue(worker_calls[2][0].endswith('/api/generate-cutout'))
        self.assertEqual((1254, 1254), cutout_worker.size)
        ok_wk, metrics_wk = ims.verify_studio_image(cutout_worker, composed=cutout_worker)
        self.assertTrue(ok_wk, f'Worker fallback cutout failed QA: {metrics_wk}')

    def test_default_media_preparer_generates_three_studio_views_without_rembg_or_ocr(self):
        ref_bytes = _jpeg_bytes(_studio_white_scene(800, variant=0))
        studio_views = [
            ims.compose_studio_frame(
                ims.extract_isolated_studio_alpha(_studio_white_scene(800, variant=v)),
                canvas_size=1254,
                max_box=890,
                normalize_tonality=True,
                add_contact_shadow=True,
                apply_clarity=True,
            )
            for v in (0, 1, 2)
        ]

        gen_calls = []

        def fake_generate(prompt, reference_image=None, *, angle='', **_kwargs):
            gen_calls.append((prompt, angle, reference_image))
            return studio_views[len(gen_calls) - 1]

        candidate = {
            'product_id': '777001',
            'title': 'Telescopic inspection mirror tool',
            'image_url': 'https://ae01.alicdn.com/kf/777001-main.jpg',
            'image_urls': ['https://ae01.alicdn.com/kf/777001-main.jpg'],
        }

        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'FLUXIXO_IMAGE_MODE': 'generate'}, clear=False), \
             patch.object(ims, 'resolve_cloudflare_ai_token', return_value=('cf-tok', 'wrangler/4.151.3')), \
             patch.object(autonomous, '_image_bytes', return_value=ref_bytes) as dl_mock, \
             patch.object(autonomous, '_check_ocr', side_effect=AssertionError('OCR must not run in generate mode')), \
             patch.object(ims, 'generate_studio_cutout', side_effect=fake_generate), \
             patch.dict(sys.modules, {'rembg': None}):
            preparer = autonomous._default_media_preparer()
            media = preparer(candidate, 'auto-777001', Path(tmp))

            dl_mock.assert_called_once_with('https://ae01.alicdn.com/kf/777001-main.jpg')
            self.assertEqual(
                ['hero studio view', '45-degree isometric studio angle', 'close-up detail studio view'],
                [c[1] for c in gen_calls],
            )
            self.assertTrue(all(c[0] == 'Telescopic inspection mirror tool' for c in gen_calls))
            self.assertTrue(media['image_quality_verified'])
            self.assertEqual(2, len(media['views']))
            self.assertEqual('auto-777001-prepared.webp', Path(media['image']).name)
            self.assertEqual('auto-777001-original.webp', Path(media['original']).name)
            self.assertEqual(
                ['auto-777001-view-2.webp', 'auto-777001-view-3.webp'],
                [Path(v).name for v in media['views']],
            )

            for p in [media['image'], *media['views']]:
                self.assertTrue(Path(p).is_file())
                with Image.open(p) as out_img:
                    out_img.load()
                    self.assertEqual('RGBA', out_img.mode)
                    self.assertEqual((1254, 1254), out_img.size)
                    self.assertEqual((0, 255), out_img.getchannel('A').getextrema())
            self.assertTrue(Path(media['original']).is_file())

    def test_default_media_preparer_cut_mode_and_missing_token_preserve_rembg_fallback(self):
        with patch.dict(os.environ, {'FLUXIXO_IMAGE_MODE': 'cut'}, clear=False), \
             patch.object(ims, 'resolve_cloudflare_ai_token', return_value=('cf-tok', 'wrangler/4.151.3')), \
             patch.dict(sys.modules, {'rembg': None}):
            with self.assertRaisesRegex(autonomous.DailyError, 'image_processor_unavailable'):
                autonomous._default_media_preparer()

        with patch.dict(os.environ, {'FLUXIXO_IMAGE_MODE': 'generate'}, clear=False), \
             patch.object(ims, 'resolve_cloudflare_ai_token', return_value=('', '')), \
             patch.dict(sys.modules, {'rembg': None}):
            with self.assertRaisesRegex(autonomous.DailyError, 'image_processor_unavailable'):
                autonomous._default_media_preparer()

    @unittest.skipUnless(
        os.environ.get('FLUXIXO_RUN_LIVE_CF_TEST') == '1' and bool(ims.resolve_cloudflare_ai_token()[0]),
        'live Cloudflare Workers AI smoke test requires FLUXIXO_RUN_LIVE_CF_TEST=1 and available CF token',
    )
    def test_live_cloudflare_flux2_studio_cutout_smoke(self):
        cutout = ims.generate_studio_cutout(
            'precision brass pocket vernier caliper tool',
            angle='hero front three-quarter studio view',
            model='@cf/black-forest-labs/flux-2-klein-4b',
        )
        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((1254, 1254), cutout.size)
        self.assertEqual((0, 255), cutout.getchannel('A').getextrema())
        ok, metrics = ims.verify_studio_image(cutout, composed=cutout)
        self.assertTrue(ok, f'Live Flux-2 studio cutout failed QA: {metrics}')


if __name__ == '__main__':
    unittest.main()
