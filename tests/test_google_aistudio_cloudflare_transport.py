"""Verification tests for Google-free Cloudflare Workers AI + GitHub (rembg & Models) transport contracts."""
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
    def test_worker_1330_schedule_and_5xx_retry_contract(self):
        wrangler_text = (ROOT / 'cloudflare_autopilot' / 'wrangler.toml').read_text(encoding='utf-8')
        self.assertIn('30 11 * * *', wrangler_text)
        cron_block = wrangler_text.split('crons = [', 1)[1].split(']', 1)[0]
        crons = [line.strip() for line in cron_block.splitlines() if '"' in line]
        self.assertLessEqual(len(crons), 4)

        index_text = (ROOT / 'cloudflare_autopilot' / 'src' / 'index.js').read_text(encoding='utf-8')
        self.assertIn('@cf/black-forest-labs/flux-2-klein-9b', index_text)
        self.assertIn('env.AI.run', index_text)
        self.assertNotIn('generativelanguage.googleapis.com', index_text)
        self.assertIn('hour = 13', index_text)
        self.assertIn('minute = 30', index_text)
        self.assertIn('drop_1330_check', index_text)
        self.assertIn('/Ultra-clean commercial industrial design studio product photograph/i.test(base)', index_text)

        rotate_wf = (ROOT / '.github' / 'workflows' / 'fluxixo_daily_rotate.yml').read_text(encoding='utf-8')
        self.assertIn("FLUXIXO_AI_TRANSPORT: ${{ vars.FLUXIXO_AI_TRANSPORT || 'worker' }}", rotate_wf)
        self.assertIn("FLUXIXO_USE_VISION_SPEC: '1'", rotate_wf)
        self.assertIn('32 11 * * *', rotate_wf)
        self.assertIn('models: read', rotate_wf)

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

    def test_wrangler_toml_uses_cloudflare_workers_ai_without_gemini(self):
        wrangler_path = ROOT / 'cloudflare_autopilot' / 'wrangler.toml'
        text = wrangler_path.read_text(encoding='utf-8')

        self.assertIsNotNone(re.search(r'(?m)^\s*\[ai\]', text), 'wrangler.toml must bind [ai] for Workers AI')
        self.assertIn('binding = "AI"', text)
        self.assertIn('AI_PROVIDER = "cloudflare-workers-ai"', text)
        self.assertIn('DEFAULT_IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-9b"', text)
        self.assertIn('FALLBACK_IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"', text)
        self.assertIn('DEFAULT_TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"', text)
        self.assertIn('DEFAULT_VISION_MODEL = "@cf/meta/llama-4-scout-17b-16e-instruct"', text)
        self.assertIn('GITHUB_REPO = "sayros2601-hub/aliradar-pro"', text)
        self.assertNotIn('GEMINI_', text)
        self.assertNotIn('google-ai-studio', text)

    def test_worker_index_js_uses_workers_ai_without_google_or_gemini(self):
        index_path = ROOT / 'cloudflare_autopilot' / 'src' / 'index.js'
        text = index_path.read_text(encoding='utf-8')

        self.assertIn('env.AI.run', text)
        self.assertIn('@cf/black-forest-labs/flux-2-klein-9b', text)
        self.assertIn('async function dispatchGitHubWorkflow(', text)
        self.assertIn('path === "/api/dispatch"', text)
        self.assertIn('path === "/api/generate-cutout"', text)
        self.assertIn('path === "/api/generate-copy"', text)
        self.assertIn('path === "/api/describe-product"', text)
        self.assertNotIn('generativelanguage.googleapis.com', text)
        self.assertNotIn('GEMINI_', text)

    def test_daily_rotate_workflow_configures_cloudflare_and_github_hybrid_without_gemini(self):
        wf_path = ROOT / '.github' / 'workflows' / 'fluxixo_daily_rotate.yml'
        text = wf_path.read_text(encoding='utf-8')

        self.assertIn('FLUXIXO_IMAGE_MODE: hybrid', text)
        self.assertIn('FLUXIXO_IMAGE_PROVIDER: cloudflare', text)
        self.assertIn('GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}', text)
        self.assertIn('models: read', text)
        self.assertIn("env.FLUXIXO_IMAGE_MODE != 'generate'", text)
        self.assertNotIn('GEMINI_API_KEY', text)
        self.assertNotIn('GEMINI_IMAGE_API_KEY', text)
        self.assertNotIn('GEMINI_TEXT_API_KEY', text)
        self.assertNotIn('nano_banana', text)


class CloudflareAndGitHubExclusiveRoutingTests(unittest.TestCase):
    def test_resolve_image_provider_always_returns_cloudflare(self):
        for explicit_provider in (None, '', 'cloudflare', 'cf', 'workers_ai', 'nano_banana'):
            with self.subTest(explicit_provider=explicit_provider), patch.dict(
                os.environ,
                {
                    'FLUXIXO_IMAGE_PROVIDER': 'nano_banana',
                },
                clear=False,
            ):
                self.assertEqual(
                    'cloudflare',
                    ims.resolve_image_provider(
                        explicit_provider,
                        cf_token='cf-secret',
                        autopilot_url='https://fluxixo-autopilot.sayros2601.workers.dev',
                    ),
                )

    def test_describe_product_from_reference_uses_cloudflare_and_github_vision_without_gemini(self):
        ref = _studio_scene(640)
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (
                'CLOUDFLARE_API_TOKEN',
                'CLOUDFLARE_AI_TOKEN',
                'GITHUB_TOKEN',
                'GH_TOKEN',
                'GITHUB_MODELS_TOKEN',
                'CLOUDFLARE_AUTOPILOT_URL',
                'FLUXIXO_AI_TRANSPORT',
            )
        }
        with patch.dict(os.environ, clean_env, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=AssertionError('no network call expected when unconfigured')):
            self.assertEqual('', ims.describe_product_from_reference(ref, product_title='Pocket lantern'))
            self.assertEqual('', ims.describe_product_from_reference(None, token='cf-tok'))

        vision_calls = []

        def fake_vision_urlopen(req, timeout=25):
            body = json.loads(req.data.decode('utf-8'))
            vision_calls.append((req.full_url, dict(req.header_items()), body))
            self.assertNotIn('generativelanguage.googleapis.com', req.full_url)
            if '@cf/meta/llama-4-scout-17b-16e-instruct' in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 404, 'Not Found', {}, BytesIO(b'{}'))
            return _FakeHttpResponse(json.dumps({
                'result': {
                    'response': 'Compact dark-blue housing with matte orange circular dial and rounded corners.',
                },
            }).encode('utf-8'))

        with patch.dict(os.environ, {**clean_env, 'CLOUDFLARE_API_TOKEN': 'cf-tok-123'}, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_vision_urlopen):
            desc = ims.describe_product_from_reference(ref, product_title='Pocket dial lamp')

        self.assertEqual('Compact dark-blue housing with matte orange circular dial and rounded corners.', desc)
        self.assertEqual(2, len(vision_calls))
        self.assertIn('api.cloudflare.com/client/v4/accounts/', vision_calls[0][0])
        self.assertIn('@cf/meta/llama-4-scout-17b-16e-instruct', vision_calls[0][0])
        self.assertIn('@cf/mistralai/mistral-small-3.1-24b-instruct', vision_calls[1][0])

        worker_calls = []

        def fake_worker_vision(req, timeout=25):
            worker_calls.append((req.full_url, json.loads(req.data.decode('utf-8'))))
            self.assertNotIn('generativelanguage.googleapis.com', req.full_url)
            return _FakeHttpResponse(json.dumps({
                'ok': True,
                'provider': 'cloudflare-workers-ai',
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
        self.assertIn('/api/describe-product?provider=cloudflare', worker_calls[0][0])
        self.assertEqual('cloudflare-workers-ai', worker_calls[0][1]['provider'])

        # GitHub Models vision fallback when Cloudflare Workers AI fails
        gh_calls = []

        def fake_gh_vision(req, timeout=25):
            gh_calls.append((req.full_url, json.loads(req.data.decode('utf-8'))))
            self.assertIn('models.github.ai', req.full_url)
            return _FakeHttpResponse(json.dumps({
                'choices': [{'message': {'content': 'Matte black cylinder with glowing ring indicator.'}}],
            }).encode('utf-8'))

        with patch.dict(os.environ, {**clean_env, 'GITHUB_TOKEN': 'ghp-test-tok'}, clear=True), \
             patch.object(ims, '_load_dpapi_secret', return_value=''), \
             patch.object(ims.urllib.request, 'urlopen', side_effect=fake_gh_vision):
            gh_desc = ims.describe_product_from_reference(ref, product_title='Desk purifier')

        self.assertEqual('Matte black cylinder with glowing ring indicator.', gh_desc)
        self.assertEqual(1, len(gh_calls))

    def test_generate_studio_cutout_retries_9b_to_4b_resizes_ref_below_512_and_supports_worker(self):
        ref = _studio_scene(720)
        ref_bytes = ims._encode_reference_image(ref, max_side=448)
        with Image.open(BytesIO(ref_bytes)) as resized_ref:
            self.assertLess(max(resized_ref.size), 512, 'FLUX.2 requires input_image_0 strictly smaller than 512x512')

        generated_png = _png_bytes(_studio_scene(800, bg=(223, 234, 196)))  # #DFEAC4 (На природе)
        b64_png = base64.b64encode(generated_png).decode('ascii')

        attempted_models = []

        def fake_cascade_urlopen(req, timeout=60):
            self.assertNotIn('generativelanguage.googleapis.com', req.full_url)
            self.assertIn('/ai/run/', req.full_url)
            model_name = req.full_url.split('/ai/run/', 1)[1]
            attempted_models.append(model_name)
            if model_name.endswith('flux-2-klein-9b'):
                raise urllib.error.HTTPError(req.full_url, 429, 'HTTP 429', {}, BytesIO(b'{}'))
            return _FakeHttpResponse(json.dumps({
                'success': True,
                'result': {'image': b64_png},
            }).encode('utf-8'))

        with patch.dict(
            os.environ,
            {
                'CLOUDFLARE_API_TOKEN': 'cf-direct-key',
                'CLOUDFLARE_AUTOPILOT_URL': '',
                'FLUXIXO_AI_TRANSPORT': 'direct',
            },
            clear=False,
        ), patch.object(ims, '_load_dpapi_secret', return_value=''), \
           patch.object(ims.urllib.request, 'urlopen', side_effect=fake_cascade_urlopen):
            cutout = ims.generate_studio_cutout(
                'Portable camp beacon',
                reference_image=ref,
                category='На природе',
            )

        self.assertEqual(
            ['@cf/black-forest-labs/flux-2-klein-9b', '@cf/black-forest-labs/flux-2-klein-4b'],
            attempted_models,
        )
        self.assertEqual('RGBA', cutout.mode)
        self.assertEqual((1254, 1254), cutout.size)
        ok, metrics = ims.verify_studio_image(cutout, composed=cutout)
        self.assertTrue(ok, f'Studio cutout failed QA: {metrics}')

        # Worker transport sends multipart form to /api/generate-cutout?provider=cloudflare
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ('CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_AI_TOKEN', 'FLUXIXO_CF_IMAGE_MODEL')
        }
        worker_calls = []

        def fake_worker_cutout(req, timeout=60):
            worker_calls.append((req.full_url, dict(req.header_items()), req.data))
            self.assertNotIn('generativelanguage.googleapis.com', req.full_url)
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
            'https://fluxixo-autopilot.sayros2601.workers.dev/api/generate-cutout?provider=cloudflare',
            worker_calls[0][0],
        )
        self.assertIn(b'name="provider"\r\n\r\ncloudflare-workers-ai', worker_calls[0][2])
        self.assertIn(b'name="input_image_0"', worker_calls[0][2])
        self.assertEqual('RGBA', worker_cutout.mode)
        self.assertEqual((1254, 1254), worker_cutout.size)
        ok_w, metrics_w = ims.verify_studio_image(worker_cutout, composed=worker_cutout)
        self.assertTrue(ok_w, f'Worker transport cutout failed QA: {metrics_w}')

    def test_ai_seo_complete_json_cloudflare_cascade_github_fallback_and_worker_transport(self):
        self.assertEqual('@cf/meta/llama-3.3-70b-instruct-fp8-fast', ai_seo.CF_TEXT_MODELS[0])

        direct_calls = []

        def fake_direct_transport(url, payload, headers):
            direct_calls.append((url, payload, headers))
            self.assertNotIn('generativelanguage.googleapis.com', url)
            if 'llama-3.3-70b' in url:
                raise RuntimeError('HTTP 429: neuron quota exhausted')
            if 'qwen3.8-27b' in url:
                raise RuntimeError('HTTP 404: unavailable')
            return {'choices': [{'message': {'content': '{"ok_flag":true,"title":"Precision Desk Lamp"}'}}]}

        parsed, provider = ai_seo.complete_json(
            'sys',
            'user',
            keys={'CLOUDFLARE_API_TOKEN': 'cf-direct-key', 'GITHUB_TOKEN': 'gh-fallback'},
            transport=fake_direct_transport,
        )

        self.assertEqual({'ok_flag': True, 'title': 'Precision Desk Lamp'}, parsed)
        self.assertTrue(provider.startswith('cloudflare:') or provider.startswith('github_models:'), provider)
        self.assertGreaterEqual(len(direct_calls), 3)

        worker_calls = []

        def fake_worker_transport(url, payload, headers):
            worker_calls.append((url, payload, headers))
            return {
                'ok': True,
                'provider': 'cloudflare-workers-ai',
                'model': '@cf/meta/llama-3.3-70b-instruct-fp8-fast',
                'choices': [{'message': {'content': '{"ok_flag":true,"via":"worker"}'}}],
            }

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (
                'CLOUDFLARE_API_TOKEN',
                'CLOUDFLARE_AI_TOKEN',
                'GITHUB_TOKEN',
                'FLUXIXO_CF_TEXT_MODEL',
                'CLOUDFLARE_AUTOPILOT_URL',
            )
        }
        with patch.dict(
            os.environ,
            {
                **clean_env,
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            clear=True,
        ):
            w_parsed, w_provider = ai_seo.complete_json('sys', 'user', keys=None, transport=fake_worker_transport)

        self.assertEqual({'ok_flag': True, 'via': 'worker'}, w_parsed)
        self.assertEqual('cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast', w_provider)
        self.assertEqual(1, len(worker_calls))
        self.assertEqual('https://fluxixo-autopilot.sayros2601.workers.dev/api/generate-copy', worker_calls[0][0])
        self.assertEqual('cloudflare-workers-ai', worker_calls[0][1]['provider'])
        self.assertEqual('@cf/meta/llama-3.3-70b-instruct-fp8-fast', worker_calls[0][1]['model'])

        def fake_gemini_rejected_transport(url, payload, headers):
            return {
                'ok': True,
                'provider': 'google-ai-studio',
                'model': 'gemini-4-argon',
                'choices': [{'message': {'content': '{"ok_flag":true}'}}],
            }

        bad_res, bad_provider = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
            },
            transport=fake_gemini_rejected_transport,
        )
        self.assertIsNone(bad_res)
        self.assertIn('disallowed', bad_provider)

    def test_worker_transport_preferred_even_when_direct_token_present(self):
        calls = []

        def worker_ok_then_fail_transport(url, payload, headers):
            calls.append((url, dict(headers or {})))
            self.assertNotIn('generativelanguage.googleapis.com', url)
            if 'workers.dev/api/generate-copy' in url and len(calls) == 1:
                return {
                    'ok': True,
                    'provider': 'cloudflare-workers-ai',
                    'model': '@cf/meta/llama-3.3-70b-instruct-fp8-fast',
                    'choices': [{'message': {'content': '{"headline":"ok"}'}}],
                }
            if 'workers.dev/api/generate-copy' in url:
                raise RuntimeError('worker 503')
            return {'choices': [{'message': {'content': '{"headline":"direct"}'}}]}

        res1, prov1 = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
                'AUTOPILOT_SYNC_TOKEN': 'sync-test-secret',
                'CLOUDFLARE_API_TOKEN': 'cf-direct-secret',
            },
            transport=worker_ok_then_fail_transport,
        )
        self.assertEqual({'headline': 'ok'}, res1)
        self.assertEqual('cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast', prov1)
        self.assertEqual(1, len(calls))
        self.assertEqual('Bearer sync-test-secret', calls[0][1].get('Authorization'))

        res2, prov2 = ai_seo.complete_json(
            'sys',
            'user',
            keys={
                'CLOUDFLARE_AUTOPILOT_URL': 'https://fluxixo-autopilot.sayros2601.workers.dev',
                'FLUXIXO_AI_TRANSPORT': 'worker',
                'CLOUDFLARE_API_TOKEN': 'cf-direct-secret',
            },
            transport=worker_ok_then_fail_transport,
        )
        self.assertEqual({'headline': 'direct'}, res2)
        self.assertTrue(prov2.startswith('cloudflare:'), prov2)
        self.assertIn('api.cloudflare.com', calls[-1][0])

    def test_cutout_prefers_worker_and_falls_back_to_direct_cloudflare(self):
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
            'CLOUDFLARE_API_TOKEN': 'cf-direct-secret',
        }
        with unittest.mock.patch.dict(os.environ, env, clear=False), \
             unittest.mock.patch.object(image_studio, '_post_autopilot_cutout', side_effect=fake_worker_cutout), \
             unittest.mock.patch.object(image_studio, '_post_cloudflare_direct_cutout', side_effect=fake_direct_cutout):
            out1 = image_studio.generate_studio_cutout('Magnetic Desk Lamp', background_hex='#F5F5F5')
            self.assertEqual((1254, 1254), out1.size)
            self.assertEqual(['worker'], events)

            out2 = image_studio.generate_studio_cutout('Magnetic Desk Lamp', background_hex='#F5F5F5')
            self.assertEqual((1254, 1254), out2.size)
            self.assertEqual(['worker', 'worker', 'direct'], events)


if __name__ == '__main__':
    unittest.main()
