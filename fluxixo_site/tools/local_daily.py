"""Run the daily product step on this PC instead of GitHub (owner, 2026-11-14), with a person reviewing the result.

  python fluxixo_site/tools/local_daily.py prepare [--count 3] [--markets IL,FR,RU]
      finds new products through the AliExpress API, writes their texts and cuts their photos out (rembg),
      exactly like the GitHub job's prepare step; nothing is built or published.
  python fluxixo_site/tools/local_daily.py build --day YYYY-MM-DD
      rebuilds and verifies the site with the countdown advanced to that drop day (no deploy).

Keys come from the encrypted store on this PC (tools/set_ali_keys_gui.py); they are never printed.
Tesseract OCR must be installed (it rejects seller posters with text, as on the GitHub runner).
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


def env_with_keys():
    env = dict(os.environ)
    key, secret = load_credential('ali-app-key.dpapi'), load_credential('ali-app-secret.dpapi')
    if not key or not secret:
        sys.exit('AliExpress keys are missing: run "FLUXIXO ключи AliExpress.cmd" on the Desktop first.')
    env.update({'ALI_APP_KEY': key.strip(), 'ALI_APP_SECRET': secret.strip(), 'FLUXIXO_IMAGE_MODE': 'cut',
                'FLUXIXO_STRICT_COPY': '1', 'PYTHONUTF8': '1'})
    env.pop('FLUXIXO_MAX_MEDIA_PRODUCTS', None)
    # Tesseract finds poster text on seller photos, exactly as on the GitHub runner (winget UB-Mannheim.TesseractOCR).
    tesseract_dir = Path(r'C:\Program Files\Tesseract-OCR')
    if not (tesseract_dir / 'tesseract.exe').exists():
        sys.exit('Tesseract is missing: winget install --id UB-Mannheim.TesseractOCR -e')
    env['PATH'] = str(tesseract_dir) + os.pathsep + env.get('PATH', '')
    # Every Python step (and the build scripts it starts) retries a write the antivirus briefly blocks: tools/winfs.
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(SITE / 'tools' / 'winfs'), env.get('PYTHONPATH', '')]))
    return env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('step', choices=('prepare', 'build'))
    parser.add_argument('--count', type=int, default=3)
    parser.add_argument('--markets', default='IL,FR,RU')
    parser.add_argument('--day', default='')
    args = parser.parse_args()
    env = env_with_keys()
    if args.step == 'prepare':
        cmd = [sys.executable, '-B', 'fluxixo_daily_rotate.py', '--add', str(args.count), '--markets', args.markets, '--prepare-only']
    else:
        if args.day:
            env['FLUXIXO_PREPARED_PUBLISH_DAY'] = args.day
        cmd = [sys.executable, '-B', 'fluxixo_daily_rotate.py', '--add', '0']
    sys.exit(subprocess.run(cmd, cwd=REPO, env=env).returncode)


if __name__ == '__main__':
    main()
