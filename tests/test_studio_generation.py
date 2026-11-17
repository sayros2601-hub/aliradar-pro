"""Tests for pure-Pillow studio alpha extraction, Google AI Studio cutout generation, and autonomous media prep."""
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

    def test_resolve_gemini_keys_and_exclusive_nano_banana_provider(self):
        with patch.dict(
            os.environ,
            {
                'GEMINI_IMAGE_API_KEY': 'img-key-1',
                'GEMINI_TEXT_API_KEY': 'txt-key-1',
                'GEMINI_API_KEY': 'shared-key-2',
                'FLUXIXO_IMAGE_PROVIDER': 'cloudflare',
                'FLUXIXO_USE_CLOUDFLARE_AI': '1',
            },
            clear=False,
        ), patch.object(ims, '_load_dpapi_secret', return_value=''):
            self.assertEqual('img-key-1', ims.resolve_gemini_api_key(local=False))
            self.assertEqual('txt-key-1', ims.resolve_gemini_text_api_key(local=False))
            self.assertEqual('explicit-img', ims.resolve_gemini_api_key('explicit-img', local=False))
            self.assertEqual(
                'nano_banana',
                ims.resolve_image_provider('cloudflare', cf_token='cf-tok', autopilot_url='https://example.workers.dev'),
            )

    def test_generate_studio_cutout_google_ai_studio_and_worker_http_transport(self):
        ref = _studio_white_scene(640, variant=0)
        generated_bytes = _jpeg_bytes(_studio_white_scene(800, variant=1))
        b64_img = base64.b64encode(generated_bytes).decode('ascii')

        seen_requests = []

        def fake_urlopen_primary(req, timeout=60):
            seen_requests.append((req.full_url, dict(req.header_items()), json.loads(req.data.decode('utf-8'))))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            self.assertNotIn('@cf/', req.full_url)
            return _FakeHttpResponse(json.dumps({
                'candidates': [{
                    'content': {
                        'parts': [{'inlineData': {'mimeType': 'image/jpeg', 'data': b64_img}}],
                    },
                }],
            }).encode('utf-8'))

        with patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen_primary):
            cutout = ims.generate_studio_cutout(
                'Telescopic inspection tool',
                reference_image=ref,
                gemini_api_key='test-gemini-key',
                token='ignored-cf-token',
            )

        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((1254, 1254), cutout.size)
        self.assertEqual((0, 255), cutout.getchannel('A').getextrema())
        ok, metrics = ims.verify_studio_image(cutout, composed=cutout)
        self.assertTrue(ok, f'Generated cutout failed QA: {metrics}')

        url, headers, payload = seen_requests[0]
        self.assertIn('generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent', url)
        hdrs = {k.lower(): v for k, v in headers.items()}
        self.assertEqual('test-gemini-key', hdrs['x-goog-api-key'])
        inline = payload['contents'][0]['parts'][1]['inlineData']
        self.assertEqual('image/png', inline['mimeType'])

        # Without direct Gemini key, optional Worker HTTP transport routes to /api/generate-cutout (never api.cloudflare.com)
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ('GEMINI_API_KEY', 'GEMINI_IMAGE_API_KEY', 'GEMINI_TEXT_API_KEY', 'GOOGLE_API_KEY')
        }
        worker_calls = []

        def fake_urlopen_worker(req, timeout=60):
            worker_calls.append((req.full_url, dict(req.header_items()), req.data))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            return _FakeHttpResponse(generated_bytes, content_type='image/jpeg')

        with patch.dict(
            os.environ,
            {
                **clean_env,
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            clear=True,
        ), patch.object(ims, '_load_dpapi_secret', return_value=''), \
           patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen_worker):
            cutout_worker = ims.generate_studio_cutout(
                'Telescopic inspection tool',
                reference_image=ref,
                token='ignored-pages-only-token',
            )

        self.assertEqual(1, len(worker_calls))
        self.assertEqual(
            'https://fluxixo-autopilot.sayros2601.workers.dev/api/generate-cutout?provider=nano_banana',
            worker_calls[0][0],
        )
        self.assertIn(b'name="input_image_0"', worker_calls[0][2])
        self.assertEqual((1254, 1254), cutout_worker.size)
        ok_wk, metrics_wk = ims.verify_studio_image(cutout_worker, composed=cutout_worker)
        self.assertTrue(ok_wk, f'Worker transport cutout failed QA: {metrics_wk}')

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

        def fake_generate(prompt, reference_image=None, *, angle='', **kwargs):
            gen_calls.append((prompt, angle, reference_image, kwargs.get('provider')))
            return studio_views[len(gen_calls) - 1]

        candidate = {
            'product_id': '777001',
            'title': 'Telescopic inspection mirror tool',
            'image_url': 'https://ae01.alicdn.com/kf/777001-main.jpg',
            'image_urls': ['https://ae01.alicdn.com/kf/777001-main.jpg'],
        }

        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {'FLUXIXO_IMAGE_MODE': 'generate'}, clear=False), \
             patch.object(ims, 'resolve_gemini_api_key', return_value='gem-test-key'), \
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
            self.assertTrue(all(c[3] == 'nano_banana' for c in gen_calls))
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

    def test_default_media_preparer_cut_mode_and_missing_keys_preserve_rembg_fallback(self):
        with patch.dict(os.environ, {'FLUXIXO_IMAGE_MODE': 'cut'}, clear=False), \
             patch.object(ims, 'resolve_gemini_api_key', return_value='gem-test-key'), \
             patch.dict(sys.modules, {'rembg': None}):
            with self.assertRaisesRegex(autonomous.DailyError, 'image_processor_unavailable'):
                autonomous._default_media_preparer()

        with patch.dict(
            os.environ,
            {'FLUXIXO_IMAGE_MODE': 'generate', 'CLOUDFLARE_AUTOPILOT_URL': '', 'FLUXIXO_AI_TRANSPORT': ''},
            clear=False,
        ), patch.object(ims, 'resolve_gemini_api_key', return_value=''), \
           patch.object(ims, '_load_dpapi_secret', return_value=''), \
           patch.dict(sys.modules, {'rembg': None}):
            with self.assertRaisesRegex(autonomous.DailyError, 'image_processor_unavailable'):
                autonomous._default_media_preparer()

    def test_colored_world_studio_alpha_punches_enclosed_holes_while_keeping_white_highlights(self):
        bg_rgb = (253, 216, 196)  # #FDD8C4 (Инструменты)
        scene = Image.new('RGB', (640, 640), bg_rgb)
        d = ImageDraw.Draw(scene)
        # Closed tool body + enclosed peach handle hole + interior pure white specular panel
        d.rounded_rectangle((110, 140, 530, 500), radius=40, fill=(36, 44, 58), outline=(18, 22, 30), width=6)
        d.rounded_rectangle((165, 220, 265, 420), radius=24, fill=bg_rgb)  # enclosed peach handle cutout
        d.rounded_rectangle((330, 220, 460, 360), radius=16, fill=(255, 255, 255))  # genuine white indicator/dial

        cutout = ims.extract_isolated_studio_alpha(scene, background_hex='#FDD8C4')
        self.assertEqual(0, cutout.getpixel((10, 10))[3], 'outer peach border should be transparent')
        self.assertEqual(0, cutout.getpixel((215, 320))[3], 'enclosed world-colored handle hole should be transparent')
        self.assertEqual(255, cutout.getpixel((135, 180))[3], 'solid foreground body must stay opaque')
        self.assertEqual(255, cutout.getpixel((395, 290))[3], 'pure white detail inside body must stay opaque')

    def test_world_background_prompt_and_default_reference_attachment(self):
        self.assertEqual('#DFEAC4', ims.resolve_world_background('На природе'))
        self.assertEqual('#12ABEF', ims.resolve_world_background('На природе', '#12abef'))
        self.assertIsNone(ims.resolve_world_background('Несуществующая'))

        ref = _studio_white_scene(640, variant=0)
        bg_scene = Image.new('RGB', (800, 800), (223, 234, 196))
        d = ImageDraw.Draw(bg_scene)
        d.rounded_rectangle((180, 180, 620, 620), radius=36, fill=(42, 58, 86))
        out_png = BytesIO()
        bg_scene.save(out_png, format='PNG')
        b64_out = base64.b64encode(out_png.getvalue()).decode('ascii')
        seen = []

        def fake_urlopen(req, timeout=60):
            seen.append((req.full_url, json.loads(req.data.decode('utf-8'))))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            return _FakeHttpResponse(json.dumps({
                'candidates': [{
                    'content': {
                        'parts': [{'inlineData': {'mimeType': 'image/png', 'data': b64_out}}],
                    },
                }],
            }).encode('utf-8'))

        with patch.dict(os.environ, {'GEMINI_IMAGE_API_KEY': 'world-key'}, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen):
            cutout = ims.generate_studio_cutout(
                'Outdoor plasma lighter',
                reference_image=ref,
                category='На природе',
                visual_spec='clear cylindrical case with hinged latch',
            )

        self.assertEqual((1254, 1254), cutout.size)
        self.assertEqual(1, len(seen))
        parts = seen[0][1]['contents'][0]['parts']
        self.assertIn('clear cylindrical case with hinged latch', parts[0]['text'])
        self.assertIn('#DFEAC4', parts[0]['text'])
        self.assertEqual('image/png', parts[1]['inlineData']['mimeType'])

    def test_describe_product_from_reference_uses_google_vision_and_gracefully_handles_missing_keys(self):
        ref = _studio_white_scene(480, variant=0)
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (
                'GEMINI_API_KEY',
                'GEMINI_TEXT_API_KEY',
                'GEMINI_IMAGE_API_KEY',
                'GOOGLE_API_KEY',
                'CLOUDFLARE_AUTOPILOT_URL',
                'FLUXIXO_AI_TRANSPORT',
            )
        }
        with patch.dict(os.environ, clean_env, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=AssertionError('missing keys must not hit network')):
            self.assertEqual('', ims.describe_product_from_reference(ref, product_title='Dial tool', token='cf-tok'))

        calls = []

        def fake_urlopen(req, timeout=25):
            calls.append((req.full_url, json.loads(req.data.decode('utf-8'))))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            self.assertNotIn('@cf/', req.full_url)
            if 'gemini-4-hydrogen:' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 429, 'Too Many Requests', {}, BytesIO(b'{}'))
            return _FakeHttpResponse(json.dumps({
                'candidates': [{
                    'content': {
                        'parts': [{'text': 'Compact matte metal body with circular dial and orange toggle.'}],
                    },
                }],
            }).encode('utf-8'))

        with patch.dict(os.environ, {**clean_env, 'GEMINI_TEXT_API_KEY': 'vision-gem-key'}, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen):
            desc = ims.describe_product_from_reference(ref, product_title='Dial tool', token='ignored-cf-token')

        self.assertEqual('Compact matte metal body with circular dial and orange toggle.', desc)
        self.assertEqual(2, len(calls))
        self.assertIn('gemini-4-hydrogen:generateContent', calls[0][0])
        self.assertIn('gemini-3.8-flash:generateContent', calls[1][0])

    def test_nano_banana_provider_resolution_1k_generation_and_strict_isolation(self):
        with patch.dict(
            os.environ,
            {
                'GEMINI_IMAGE_API_KEY': 'img-key-1',
                'GEMINI_API_KEY': 'shared-key-2',
            },
            clear=False,
        ):
            self.assertEqual('img-key-1', ims.resolve_gemini_api_key(local=False))
            self.assertEqual(
                'nano_banana',
                ims.resolve_image_provider('cloudflare', gemini_key='img-key-1', cf_token='cf-tok'),
            )

        ref = _studio_white_scene(640, variant=0)
        bg_scene = Image.new('RGB', (800, 800), (223, 234, 196))  # #DFEAC4 (На природе)
        d = ImageDraw.Draw(bg_scene)
        d.rounded_rectangle((170, 170, 630, 630), radius=36, fill=(40, 68, 92))
        out_png = BytesIO()
        bg_scene.save(out_png, format='PNG')
        b64_out = base64.b64encode(out_png.getvalue()).decode('ascii')

        calls = []

        def fake_urlopen(req, timeout=60):
            calls.append((req.full_url, dict(req.header_items()), json.loads(req.data.decode('utf-8'))))
            self.assertNotIn('cloudflare.com', req.full_url)
            if 'gemini-3-pro-image:' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 404, 'Not Found', {}, BytesIO(b'{}'))
            if 'gemini-nano-banana-2.1:' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 429, 'Quota Exceeded', {}, BytesIO(b'{}'))
            return _FakeHttpResponse(json.dumps({
                'candidates': [{
                    'content': {
                        'parts': [{'inlineData': {'mimeType': 'image/png', 'data': b64_out}}],
                    },
                }],
            }).encode('utf-8'))

        with patch.dict(os.environ, {'FLUXIXO_IMAGE_PROVIDER': 'nano_banana'}, clear=False), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims, 'describe_product_from_reference', side_effect=AssertionError('vision optional unless requested')), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_urlopen):
            cutout = ims.generate_studio_cutout(
                'solar lantern clip',
                reference_image=ref,
                category='На природе',
                gemini_api_key='tier1-nano-key',
                image_size='1K',
            )

        self.assertEqual(3, len(calls))
        self.assertIn('gemini-3-pro-image:generateContent', calls[0][0])
        self.assertIn('gemini-nano-banana-2.1:generateContent', calls[1][0])
        self.assertIn('gemini-3.1-flash-image:generateContent', calls[2][0])
        hdrs = {k.lower(): v for k, v in calls[0][1].items()}
        self.assertEqual('tier1-nano-key', hdrs['x-goog-api-key'])
        gen_cfg = calls[0][2]['generationConfig']
        self.assertEqual(['IMAGE'], gen_cfg['responseModalities'])
        self.assertEqual({'aspectRatio': '1:1', 'imageSize': '1K'}, gen_cfg['imageConfig'])
        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((1254, 1254), cutout.size)
        self.assertEqual((0, 255), cutout.getchannel('A').getextrema())

        def fake_429(req, timeout=60):
            self.assertNotIn('cloudflare.com', req.full_url)
            raise urllib.error.HTTPError(req.full_url, 429, 'Too Many Requests', {}, BytesIO(b'quota 0'))

        with patch.dict(os.environ, {'FLUXIXO_IMAGE_PROVIDER': 'nano_banana'}, clear=False), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_429):
            with self.assertRaisesRegex(RuntimeError, 'gemini_image_http_429'):
                ims.generate_studio_cutout(
                    'solar lantern clip',
                    gemini_api_key='free-tier-key',
                    token='should-not-fallback-to-cf',
                )

    def test_ai_seo_argon_high_and_discovery_complete_json(self):
        from fluxixo_site.tools import ai_seo
        from fluxixo_ai import discovery_curator

        seen = []

        def fake_transport(url, payload, headers):
            seen.append((url, payload))
            self.assertNotIn('@cf/', url)
            self.assertNotIn('api.cloudflare.com', url)
            if 'gemini-4-argon:' in url or 'gemini-4-carbon:' in url:
                raise RuntimeError('HTTP 429: limit 0 on free tier')
            return {
                'candidates': [{
                    'content': {
                        'parts': [
                            {'thought': True, 'text': 'internal reasoning'},
                            {'text': '{"queries":[{"query":"optical glass prism physics cube","keyword_required":"prism","category":"Техника"}]}'},
                        ],
                    },
                }],
            }

        with patch.dict(os.environ, {'FLUXIXO_GEMINI_THINKING_LEVEL': 'HIGH'}, clear=False):
            parsed, provider_tag = ai_seo.complete_json(
                'sys',
                'user',
                keys={'GEMINI_API_KEY': 'test-key'},
                transport=fake_transport,
            )

        self.assertEqual('gemini:gemini-4-hydrogen', provider_tag)
        self.assertEqual('prism', parsed['queries'][0]['keyword_required'])
        self.assertEqual('HIGH', seen[0][1]['generationConfig']['thinkingConfig']['thinkingLevel'])
        self.assertEqual(8192, seen[0][1]['generationConfig']['maxOutputTokens'])

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}, clear=False), \
             patch.object(
                 ai_seo,
                 'complete_json',
                 return_value=({'queries': [{'query': 'optical glass prism physics cube', 'keyword_required': 'prism', 'category': 'Техника'}]}, 'gemini:gemini-4-argon'),
             ):
            ideas = discovery_curator.generate_ai_discovery_queries(
                [],
                limit=2,
            )
        self.assertEqual(1, len(ideas))
        self.assertEqual('optical glass prism physics cube', ideas[0]['query'])


if __name__ == '__main__':
    unittest.main()
