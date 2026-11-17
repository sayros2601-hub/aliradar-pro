"""Verification tests for exclusive Google AI Studio routing and Cloudflare HTTP transport contracts."""
from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch
import urllib.error

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site' / 'tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ai_seo  # noqa: E402
from fluxixo_ai import image_studio as ims  # noqa: E402


def _studio_scene(size: int = 640, bg: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """Create a sharp, textured studio product scene on a uniform backdrop."""
    img = Image.new('RGB', (size, size), bg)
    draw = ImageDraw.Draw(img)
    s = size / 640.0
    draw.rounded_rectangle(
        (int(130 * s), int(150 * s), int(510 * s), int(490 * s)),
        radius=int(34 * s),
        fill=(36, 54, 88),
        outline=(20, 28, 44),
        width=max(2, int(6 * s)),
    )
    for row in range(180, 460, 32):
        for col in range(160, 480, 32):
            c = 150 + ((row + col) % 80)
            draw.rectangle(
                (int(col * s), int(row * s), int((col + 16) * s), int((row + 16) * s)),
                fill=(c, c - 30, 82),
            )
    draw.ellipse(
        (int(230 * s), int(240 * s), int(410 * s), int(400 * s)),
        fill=(224, 112, 48),
        outline=(24, 28, 36),
        width=max(2, int(4 * s)),
    )
    return img


def _png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format='PNG')
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


class CloudflareWorkerContractTests(unittest.TestCase):
    def test_worker_2100_schedule_and_5xx_retry_contract(self):
        wrangler_text = (ROOT / 'cloudflare_autopilot' / 'wrangler.toml').read_text(encoding='utf-8')
        self.assertIn('0 19 * * *', wrangler_text)
        cron_block = wrangler_text.split('crons = [', 1)[1].split(']', 1)[0]
        crons = [line.strip() for line in cron_block.splitlines() if '"' in line]
        self.assertLessEqual(len(crons), 4)

        index_text = (ROOT / 'cloudflare_autopilot' / 'src' / 'index.js').read_text(encoding='utf-8')
        self.assertIn('RETRYABLE_GEMINI_STATUSES = new Set([400, 403, 404, 429, 500, 502, 503, 504])', index_text)
        self.assertIn('hour = 21', index_text)
        self.assertIn('drop_2100_check', index_text)
        self.assertIn('/Ultra-clean commercial industrial design studio product photograph/i.test(base)', index_text)

        rotate_wf = (ROOT / '.github' / 'workflows' / 'fluxixo_daily_rotate.yml').read_text(encoding='utf-8')
        self.assertIn("FLUXIXO_AI_TRANSPORT: ${{ vars.FLUXIXO_AI_TRANSPORT || 'worker' }}", rotate_wf)
        self.assertIn("FLUXIXO_USE_VISION_SPEC: '1'", rotate_wf)
        self.assertIn('15 19 * * *', rotate_wf)

    def test_slot3_effect_prompt_and_white_enclosed_hole_cutout(self):
        from PIL import Image, ImageDraw
        from fluxixo_ai import image_studio

        slot3_prompt = image_studio.build_studio_prompt(
            'LED Therapy Facial Mask',
            angle='close-up detail studio view',
            background_hex='#F8D9E6',
        )
        self.assertIn('active powered-on functional demonstration', slot3_prompt)
        self.assertIn('illuminated LED', slot3_prompt)
        self.assertNotIn('even shadowless studio lighting', slot3_prompt)

        img = Image.new('RGB', (160, 160), (223, 229, 251))
        draw = ImageDraw.Draw(img)
        draw.rectangle((30, 30, 130, 130), fill=(30, 30, 30))
        draw.rectangle((60, 60, 100, 100), fill=(223, 229, 251))
        with unittest.mock.patch.dict(os.environ, {'FLUXIXO_DISABLE_REMBG_REFINE': '1'}):
            cut = image_studio.extract_isolated_studio_alpha(img, background_hex='#DFE5FB')
        self.assertEqual(0, cut.getpixel((80, 80))[3])
        self.assertEqual(255, cut.getpixel((45, 45))[3])

    def test_wrangler_toml_uses_google_ai_studio_without_workers_ai_binding(self):
        wrangler_path = ROOT / 'cloudflare_autopilot' / 'wrangler.toml'
        text = wrangler_path.read_text(encoding='utf-8')

        self.assertIsNone(re.search(r'(?m)^\s*\[ai\]', text), 'wrangler.toml must not define an [ai] binding')
        self.assertNotIn('@cf/', text, 'wrangler.toml must not reference Cloudflare @cf/ models')
        self.assertIn('AI_PROVIDER = "google-ai-studio"', text)
        self.assertIn('DEFAULT_GEMINI_IMAGE_MODEL = "gemini-3-pro-image"', text)
        self.assertIn('DEFAULT_GEMINI_TEXT_MODEL = "gemini-4-argon"', text)
        self.assertIn('GEMINI_THINKING_LEVEL = "HIGH"', text)
        self.assertIn('GITHUB_REPO = "sayros2601-hub/aliradar-pro"', text)

    def test_worker_index_js_has_no_workers_ai_and_exposes_dispatch_and_gemini_transport(self):
        index_path = ROOT / 'cloudflare_autopilot' / 'src' / 'index.js'
        text = index_path.read_text(encoding='utf-8')

        self.assertNotRegex(text, r'\benv\.AI\b', 'Worker must not invoke env.AI')
        self.assertNotIn('env.AI.run', text, 'Worker must not invoke env.AI.run')
        self.assertNotIn('@cf/', text, 'Worker must not reference Cloudflare @cf/ models')
        self.assertIn('async function dispatchGitHubWorkflow(', text)
        self.assertIn('path === "/api/dispatch"', text)
        self.assertIn('path === "/api/generate-cutout"', text)
        self.assertIn('path === "/api/generate-copy"', text)
        self.assertIn('path === "/api/describe-product"', text)
        self.assertIn('generativelanguage.googleapis.com/v1beta/models/', text)

    def test_daily_rotate_workflow_configures_google_ai_studio_exclusively(self):
        wf_path = ROOT / '.github' / 'workflows' / 'fluxixo_daily_rotate.yml'
        text = wf_path.read_text(encoding='utf-8')

        self.assertNotRegex(text, r"FLUXIXO_USE_CLOUDFLARE_AI\s*:\s*['\"]?1['\"]?")
        self.assertNotIn('FLUXIXO_USE_CLOUDFLARE_AI', text)
        self.assertIn('FLUXIXO_IMAGE_MODE: generate', text)
        self.assertIn('FLUXIXO_IMAGE_PROVIDER: nano_banana', text)
        self.assertIn('FLUXIXO_GEMINI_THINKING_LEVEL: HIGH', text)
        self.assertIn('GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}', text)
        self.assertIn('GEMINI_IMAGE_API_KEY: ${{ secrets.GEMINI_IMAGE_API_KEY }}', text)
        self.assertIn('GEMINI_TEXT_API_KEY: ${{ secrets.GEMINI_TEXT_API_KEY }}', text)


class GoogleAiStudioExclusiveRoutingTests(unittest.TestCase):
    def test_resolve_image_provider_always_returns_nano_banana(self):
        for explicit_provider in (None, '', 'cloudflare', 'cf', 'workers_ai', 'nano_banana'):
            with self.subTest(explicit_provider=explicit_provider), patch.dict(
                os.environ,
                {
                    'FLUXIXO_IMAGE_PROVIDER': 'cloudflare',
                    'FLUXIXO_USE_CLOUDFLARE_AI': '1',
                },
                clear=False,
            ):
                self.assertEqual(
                    'nano_banana',
                    ims.resolve_image_provider(
                        explicit_provider,
                        gemini_key='',
                        cf_token='cf-secret',
                        autopilot_url='https://fluxixo-autopilot.sayros2601.workers.dev',
                    ),
                )

    def test_describe_product_from_reference_uses_google_vision_and_handles_missing_keys(self):
        ref = _studio_scene(480)
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
             patch.object(ims.urllib.request, 'urlopen', side_effect=AssertionError('no network call expected when unconfigured')):
            self.assertEqual('', ims.describe_product_from_reference(ref, product_title='Pocket lantern'))
            self.assertEqual('', ims.describe_product_from_reference(None, api_key='gem-vision-key'))

        vision_calls = []

        def fake_vision_urlopen(req, timeout=25):
            body = json.loads(req.data.decode('utf-8'))
            vision_calls.append((req.full_url, dict(req.header_items()), body))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            self.assertNotIn('@cf/', req.full_url)
            if 'gemini-4-hydrogen:' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 404, 'Not Found', {}, BytesIO(b'{}'))
            return _FakeHttpResponse(json.dumps({
                'candidates': [{
                    'content': {
                        'parts': [{'text': 'Compact dark-blue housing with matte orange circular dial and rounded corners.'}],
                    },
                }],
            }).encode('utf-8'))

        with patch.dict(os.environ, {**clean_env, 'GEMINI_TEXT_API_KEY': 'gem-text-123'}, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_vision_urlopen):
            desc = ims.describe_product_from_reference(ref, product_title='Pocket dial lamp')

        self.assertEqual('Compact dark-blue housing with matte orange circular dial and rounded corners.', desc)
        self.assertEqual(2, len(vision_calls))
        self.assertIn('generativelanguage.googleapis.com/v1beta/models/gemini-4-hydrogen:generateContent', vision_calls[0][0])
        self.assertIn('generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent', vision_calls[1][0])
        parts = vision_calls[0][2]['contents'][0]['parts']
        self.assertEqual('image/jpeg', parts[1]['inlineData']['mimeType'])

        worker_calls = []

        def fake_worker_vision(req, timeout=25):
            worker_calls.append((req.full_url, json.loads(req.data.decode('utf-8'))))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            return _FakeHttpResponse(json.dumps({
                'ok': True,
                'provider': 'google-ai-studio',
                'visual_spec': 'Anodized slate housing with recessed amber button.',
            }).encode('utf-8'))

        with patch.dict(
            os.environ,
            {
                **clean_env,
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            clear=True,
        ), patch.object(ims, '_load_dpapi_secret', return_value=''), \
           patch.object(ims.urllib.request, 'urlopen', side_effect=fake_worker_vision):
            worker_desc = ims.describe_product_from_reference(ref, product_title='Compact flashlight')

        self.assertEqual('Anodized slate housing with recessed amber button.', worker_desc)
        self.assertEqual(1, len(worker_calls))
        self.assertIn('/api/describe-product?provider=nano_banana', worker_calls[0][0])
        self.assertEqual('nano_banana', worker_calls[0][1]['provider'])

    def test_generate_studio_cutout_retries_400_403_404_429_across_model_cascade_and_worker_transport(self):
        ref = _studio_scene(640)
        generated_png = _png_bytes(_studio_scene(800, bg=(223, 234, 196)))  # #DFEAC4 (На природе)
        b64_png = base64.b64encode(generated_png).decode('ascii')

        status_by_model = {
            'gemini-3-pro-image': 400,
            'gemini-nano-banana-2.1': 403,
            'gemini-3.1-flash-image': 404,
            'gemini-3.1-flash-lite-image': 429,
            'gemini-3.1-flash-image-preview': 429,
        }
        attempted_models = []

        def fake_cascade_urlopen(req, timeout=60):
            self.assertNotIn('api.cloudflare.com', req.full_url)
            self.assertNotIn('@cf/', req.full_url)
            model_name = req.full_url.split('/models/', 1)[1].split(':', 1)[0]
            attempted_models.append(model_name)
            err_code = status_by_model.get(model_name)
            if err_code is not None:
                raise urllib.error.HTTPError(req.full_url, err_code, f'HTTP {err_code}', {}, BytesIO(b'{}'))
            return _FakeHttpResponse(json.dumps({
                'candidates': [{
                    'content': {
                        'parts': [{'inlineData': {'mimeType': 'image/png', 'data': b64_png}}],
                    },
                }],
            }).encode('utf-8'))

        with patch.dict(
            os.environ,
            {
                'GEMINI_IMAGE_API_KEY': 'gem-img-key',
                'FLUXIXO_GEMINI_IMAGE_MODEL': '@cf/black-forest-labs/flux-2-klein-4b',
            },
            clear=False,
        ), patch.object(ims, '_load_dpapi_secret', return_value=''), \
           patch.object(ims.urllib.request, 'urlopen', side_effect=fake_cascade_urlopen):
            cutout = ims.generate_studio_cutout(
                'Portable camp beacon',
                reference_image=ref,
                category='На природе',
                token='ignored-cf-token',
                provider='cloudflare',
            )

        self.assertEqual(
            [
                'gemini-3-pro-image',
                'gemini-nano-banana-2.1',
                'gemini-3.1-flash-image',
                'gemini-3.1-flash-lite-image',
                'gemini-3.1-flash-image-preview',
                'gemini-2.5-flash-image',
            ],
            attempted_models,
        )
        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((1254, 1254), cutout.size)
        ok, metrics = ims.verify_studio_image(cutout, composed=cutout)
        self.assertTrue(ok, f'Studio cutout failed QA: {metrics}')

        # When direct Gemini API keys are absent and Worker HTTP transport is configured,
        # route strictly through Worker /api/generate-cutout (never api.cloudflare.com/client/v4/accounts/.../ai/run).
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (
                'GEMINI_API_KEY',
                'GEMINI_IMAGE_API_KEY',
                'GEMINI_TEXT_API_KEY',
                'GOOGLE_API_KEY',
                'FLUXIXO_GEMINI_IMAGE_MODEL',
            )
        }
        worker_calls = []

        def fake_worker_cutout(req, timeout=60):
            worker_calls.append((req.full_url, dict(req.header_items()), req.data))
            self.assertNotIn('api.cloudflare.com', req.full_url)
            return _FakeHttpResponse(generated_png, content_type='image/png')

        with patch.dict(
            os.environ,
            {
                **clean_env,
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            clear=True,
        ), patch.object(ims, '_load_dpapi_secret', return_value=''), \
           patch.object(ims.urllib.request, 'urlopen', side_effect=fake_worker_cutout):
            worker_cutout = ims.generate_studio_cutout(
                'Portable camp beacon',
                reference_image=ref,
                category='На природе',
            )

        self.assertEqual(1, len(worker_calls))
        self.assertEqual(
            'https://fluxixo-autopilot.sayros2601.workers.dev/api/generate-cutout?provider=nano_banana',
            worker_calls[0][0],
        )
        self.assertIn(b'name="provider"\r\n\r\nnano_banana', worker_calls[0][2])
        self.assertIn(b'name="input_image_0"', worker_calls[0][2])
        self.assertEqual('RGBA', worker_cutout.mode)
        self.assertEqual((1254, 1254), worker_cutout.size)
        ok_w, metrics_w = ims.verify_studio_image(worker_cutout, composed=worker_cutout)
        self.assertTrue(ok_w, f'Worker transport cutout failed QA: {metrics_w}')

    def test_ai_seo_complete_json_google_cascade_and_worker_copy_transport(self):
        self.assertEqual('gemini-4-argon', ai_seo.GEMINI_MODELS[0])
        self.assertEqual('gemini-4-hydrogen', ai_seo.GEMINI_MODELS[2])

        direct_calls = []

        def fake_direct_transport(url, payload, headers):
            direct_calls.append((url, payload, headers))
            self.assertNotIn('@cf/', url)
            self.assertNotIn('api.cloudflare.com', url)
            if 'gemini-4-argon:' in url:
                raise RuntimeError('HTTP 429: quota exhausted')
            if 'gemini-4-carbon:' in url:
                raise RuntimeError('HTTP 404: unavailable')
            return {
                'candidates': [{
                    'content': {
                        'parts': [{'text': '{"ok_flag":true,"title":"Precision Desk Lamp"}'}],
                    },
                }],
            }

        with patch.dict(
            os.environ,
            {
                'FLUXIXO_GEMINI_THINKING_LEVEL': 'HIGH',
                'FLUXIXO_GEMINI_TEXT_MODEL': '@cf/meta/llama-3.3-70b-instruct-fp8-fast',
            },
            clear=False,
        ):
            parsed, provider = ai_seo.complete_json(
                'sys',
                'user',
                keys={'GEMINI_API_KEY': 'direct-gem-key'},
                transport=fake_direct_transport,
            )

        self.assertEqual({'ok_flag': True, 'title': 'Precision Desk Lamp'}, parsed)
        self.assertEqual('gemini:gemini-4-hydrogen', provider)
        self.assertEqual(3, len(direct_calls))
        self.assertIn('gemini-4-argon:generateContent', direct_calls[0][0])
        self.assertEqual('HIGH', direct_calls[0][1]['generationConfig']['thinkingConfig']['thinkingLevel'])
        self.assertIn('gemini-4-carbon:generateContent', direct_calls[1][0])
        self.assertIn('gemini-4-hydrogen:generateContent', direct_calls[2][0])

        worker_calls = []

        def fake_worker_transport(url, payload, headers):
            worker_calls.append((url, payload, headers))
            return {
                'ok': True,
                'provider': 'google-ai-studio',
                'model': 'gemini:gemini-4-argon',
                'choices': [{'message': {'content': '{"ok_flag":true,"via":"worker"}'}}],
            }

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (
                'GEMINI_API_KEY',
                'GEMINI_TEXT_API_KEY',
                'GEMINI_IMAGE_API_KEY',
                'FLUXIXO_GEMINI_TEXT_MODEL',
                'CLOUDFLARE_AUTOPILOT_URL',
            )
        }
        with patch.dict(
            os.environ,
            {
                **clean_env,
                'FLUXIXO_GEMINI_THINKING_LEVEL': 'HIGH',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            clear=True,
        ):
            w_parsed, w_provider = ai_seo.complete_json('sys', 'user', keys=None, transport=fake_worker_transport)

        self.assertEqual({'ok_flag': True, 'via': 'worker'}, w_parsed)
        self.assertEqual('gemini:gemini-4-argon', w_provider)
        self.assertEqual(1, len(worker_calls))
        self.assertEqual('https://fluxixo-autopilot.sayros2601.workers.dev/api/generate-copy', worker_calls[0][0])
        self.assertEqual('gemini', worker_calls[0][1]['provider'])
        self.assertEqual('gemini-4-argon', worker_calls[0][1]['model'])
        self.assertEqual('HIGH', worker_calls[0][1]['thinking_level'])

        def fake_cf_rejected_transport(url, payload, headers):
            return {
                'ok': True,
                'model': '@cf/meta/llama-3.3-70b-instruct-fp8-fast',
                'choices': [{'message': {'content': '{"ok_flag":true}'}}],
            }

        bad_res, bad_provider = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            transport=fake_cf_rejected_transport,
        )
        self.assertIsNone(bad_res)
        self.assertIn('disallowed Workers AI model', bad_provider)

    def test_worker_transport_preferred_even_when_gemini_key_present_with_direct_fallback(self):
        calls = []

        def worker_ok_then_fail_transport(url, payload, headers):
            calls.append((url, dict(headers or {})))
            if 'workers.dev/api/generate-copy' in url and len(calls) == 1:
                return {
                    'ok': True,
                    'provider': 'gemini',
                    'model': 'gemini-3.5-flash-lite',
                    'choices': [{'message': {'content': '{"headline":"ok"}'}}],
                }
            if 'workers.dev/api/generate-copy' in url:
                raise RuntimeError('worker 503')
            return {'candidates': [{'content': {'parts': [{'text': '{"headline":"direct"}'}]}}]}

        res1, prov1 = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
                'AUTOPILOT_SYNC_TOKEN': 'sync-test-secret',
                'GEMINI_API_KEY': 'AIzaFakeDirectKey',
            },
            transport=worker_ok_then_fail_transport,
        )
        self.assertEqual({'headline': 'ok'}, res1)
        self.assertEqual('gemini:gemini-3.5-flash-lite', prov1)
        self.assertEqual(1, len(calls))
        self.assertEqual('Bearer sync-test-secret', calls[0][1].get('Authorization'))

        res2, prov2 = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
                'GEMINI_API_KEY': 'AIzaFakeDirectKey',
            },
            transport=worker_ok_then_fail_transport,
        )
        self.assertEqual({'headline': 'direct'}, res2)
        self.assertIn('gemini:', prov2)
        self.assertIn('generativelanguage.googleapis.com', calls[-1][0])

    def test_cutout_prefers_worker_with_gemini_key_and_falls_back_to_direct(self):
        from PIL import Image, ImageDraw
        from fluxixo_ai import image_studio

        sample = Image.new('RGB', (160, 160), (245, 245, 245))
        ImageDraw.Draw(sample).rectangle((30, 30, 130, 130), fill=(30, 90, 190))
        events = []

        def fake_worker_cutout(*args, **kwargs):
            events.append('worker')
            if len(events) == 1:
                return sample
            raise RuntimeError('worker temporary error')

        def fake_direct_cutout(*args, **kwargs):
            events.append('direct')
            return sample

        env = {
            'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
            'FLUXIXO_AI_TRANSPORT': 'worker',
            'GEMINI_API_KEY': 'AIzaFakeDirectKey',
        }
        with unittest.mock.patch.dict(os.environ, env, clear=False), \
             unittest.mock.patch.object(image_studio, '_post_autopilot_cutout', side_effect=fake_worker_cutout), \
             unittest.mock.patch.object(image_studio, '_post_gemini_generate_image', side_effect=fake_direct_cutout):
            out1 = image_studio.generate_studio_cutout('Magnetic Desk Lamp', background_hex='#F5F5F5')
            self.assertEqual((1254, 1254), out1.size)
            self.assertEqual(['worker'], events)

            out2 = image_studio.generate_studio_cutout('Magnetic Desk Lamp', background_hex='#F5F5F5')
            self.assertEqual((1254, 1254), out2.size)
            self.assertEqual(['worker', 'worker', 'direct'], events)


if __name__ == '__main__':
    unittest.main()
