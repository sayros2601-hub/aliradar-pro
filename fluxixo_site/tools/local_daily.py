"""Run the daily product step locally, routing all text and image generation to Google AI Studio.

  python fluxixo_site/tools/local_daily.py prepare [--count 3] [--markets IL,FR,RU] [--mode auto] [--provider nano_banana]
      finds new products through the AliExpress API, writes their 6-language cards via Google AI Studio
      (high-tier Gemini text with HIGH thinking), and generates clean 1254x1254 studio photos via Nano Banana 1K;
      Cloudflare is used solely for optional Autopilot transport (CLOUDFLARE_AUTOPILOT_URL) and Pages hosting.
  python fluxixo_site/tools/local_daily.py build --day YYYY-MM-DD
      rebuilds and verifies the site with the countdown advanced to that drop day (no deploy).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parent
sys.path.insert(0, str(SITE / 'tools'))
from dpapi_store import load_credential  # noqa: E402


def env_with_keys(*, image_mode: str = '', image_provider: str = ''):
    """Build subprocess environment with AliExpress, Google AI Studio, and Autopilot transport credentials."""
    env = dict(os.environ)
    key, secret = load_credential('ali-app-key.dpapi'), load_credential('ali-app-secret.dpapi')
    if not key or not secret:
        sys.exit('AliExpress keys are missing: run "FLUXIXO ключи AliExpress.cmd" on the Desktop first.')

    optional_dpapi = {
        'GEMINI_API_KEY': 'gemini-api-key.dpapi',
        'GEMINI_TEXT_API_KEY': 'gemini-text-api-key.dpapi',
        'GEMINI_IMAGE_API_KEY': 'gemini-image-api-key.dpapi',
        'AUTOPILOT_SYNC_TOKEN': 'autopilot-sync-token.dpapi',
    }
    for env_name, dpapi_name in optional_dpapi.items():
        if not env.get(env_name, '').strip():
            val = (load_credential(dpapi_name) or '').strip()
            if val:
                env[env_name] = val

    resolved_mode = (image_mode or env.get('FLUXIXO_IMAGE_MODE', '')).strip().lower()
    if resolved_mode in ('', 'auto'):
        has_gemini = any(
            k.startswith('GEMINI_') and k.endswith('_KEY') and v.strip()
            for k, v in env.items()
        )
        has_autopilot = bool(env.get('CLOUDFLARE_AUTOPILOT_URL', '').strip())
        resolved_mode = 'generate' if (has_gemini or has_autopilot) else 'cut'

    requested_provider = (image_provider or '').strip().lower()
    if requested_provider not in ('', 'auto', 'nano_banana'):
        raise ValueError(f'Unsupported image provider: {image_provider!r}')

    env.update({
        'ALI_APP_KEY': key.strip(),
        'ALI_APP_SECRET': secret.strip(),
        'FLUXIXO_IMAGE_MODE': resolved_mode,
        'FLUXIXO_IMAGE_PROVIDER': 'nano_banana',
        'FLUXIXO_USE_VISION_SPEC': env.get('FLUXIXO_USE_VISION_SPEC', '').strip() or '1',
        'FLUXIXO_GEMINI_THINKING_LEVEL': env.get('FLUXIXO_GEMINI_THINKING_LEVEL', '').strip().upper() or 'HIGH',
        'FLUXIXO_GEMINI_IMAGE_SIZE': env.get('FLUXIXO_GEMINI_IMAGE_SIZE', '').strip() or '1K',
        'FLUXIXO_STRICT_COPY': '1',
        'PYTHONUTF8': '1',
    })
    env.pop('FLUXIXO_USE_CLOUDFLARE_AI', None)
    env.pop('FLUXIXO_MAX_MEDIA_PRODUCTS', None)

    tesseract_dir = Path(r'C:\Program Files\Tesseract-OCR')
    if (tesseract_dir / 'tesseract.exe').exists():
        env['PATH'] = str(tesseract_dir) + os.pathsep + env.get('PATH', '')
    elif resolved_mode == 'cut':
        sys.exit('Tesseract is missing: winget install --id UB-Mannheim.TesseractOCR -e')
    # Every Python step (and the build scripts it starts) retries a write the antivirus briefly blocks: tools/winfs.
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(SITE / 'tools' / 'winfs'), env.get('PYTHONPATH', '')]))
    return env


def main():
    """Parse CLI arguments and dispatch local prepare or build steps."""
    parser = argparse.ArgumentParser()
    parser.add_argument('step', choices=('prepare', 'build'))
    parser.add_argument('--count', type=int, default=3)
    parser.add_argument('--markets', default='IL,FR,RU')
    parser.add_argument('--day', default='')
    parser.add_argument('--mode', default='auto', choices=('', 'auto', 'generate', 'cut'))
    parser.add_argument('--provider', default='nano_banana', choices=('auto', 'nano_banana'))
    args = parser.parse_args()
    env = env_with_keys(image_mode=args.mode, image_provider=args.provider)
    if args.step == 'prepare':
        cmd = [sys.executable, '-B', 'fluxixo_daily_rotate.py', '--add', str(args.count), '--markets', args.markets, '--prepare-only']
    else:
        if args.day:
            env['FLUXIXO_PREPARED_PUBLISH_DAY'] = args.day
        cmd = [sys.executable, '-B', 'fluxixo_daily_rotate.py', '--add', '0']
    sys.exit(subprocess.run(cmd, cwd=REPO, env=env).returncode)


if __name__ == '__main__':
    main()
