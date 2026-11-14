"""Batch product video generator for FLUXIXO.
Creates square (720x720) 8.7s smooth showcase loops for all catalog products
and compiles H.264 (.mp4) and HEVC (.hevc.mp4) formats.
"""
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
VIDEO_DIR = DIST / 'assets/video'
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# Colors matching FLUXIXO worlds
WORLDS = {
    'Техника': '0xdfe5fb', 'Дом': '0xf1e3cf', 'Кухня': '0xd9eede', 'В дороге': '0xfbe7a6',
    'Инструменты': '0xfdd8c4', 'Уход': '0xf8d9e6', 'Спорт': '0xd3edf5', 'На природе': '0xdfeac4',
    'Питомцы': '0xe9dcf8'
}
DEFAULT_BG = '0xf3f0e9'


def get_products():
    catalog_path = DIST / 'js/catalog.js'
    text = catalog_path.read_text(encoding='utf-8')
    raw_json = text.split('=', 1)[1].strip().rstrip(';')
    data = json.loads(raw_json)
    return data['products']


def generate_video_for_product(p):
    pid = p['id']
    h264_path = VIDEO_DIR / f'{pid}.mp4'
    hevc_path = VIDEO_DIR / f'{pid}.hevc.mp4'

    # If both already exist, skip
    if h264_path.exists() and hevc_path.exists():
        return f'[EXISTS] {pid}'

    # Resolve image source
    img_rel = p.get('image', '').lstrip('/')
    img_path = DIST / img_rel
    if not img_path.exists():
        img_rel = p.get('original', '').lstrip('/')
        img_path = DIST / img_rel
    if not img_path.exists():
        return f'[ERROR: No image] {pid}'

    bg_color = WORLDS.get(p.get('category'), DEFAULT_BG)

    try:
        # 1. Generate H.264 loop (8.68s = 217 frames at 25 fps, smooth sinus zoom)
        if not h264_path.exists():
            cmd_h264 = [
                'ffmpeg', '-y', '-loop', '1', '-i', str(img_path),
                '-vf', (
                    f'scale=640:640:force_original_aspect_ratio=decrease,'
                    f'pad=720:720:(ow-iw)/2:(oh-ih)/2:color={bg_color},'
                    f'zoompan=z=\'1.0+0.05*sin(2*PI*in/217)\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':d=217:s=720x720:fps=25,'
                    f'format=yuv420p'
                ),
                '-t', '8.68',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-profile:v', 'high',
                '-level', '4.0',
                '-movflags', '+faststart',
                str(h264_path)
            ]
            res = subprocess.run(cmd_h264, capture_output=True, text=True)
            if res.returncode != 0:
                return f'[FAIL H264] {pid}: {res.stderr[-200:]}'

        # 2. Generate HEVC loop from H.264 output
        if not hevc_path.exists() and h264_path.exists():
            cmd_hevc = [
                'ffmpeg', '-y', '-i', str(h264_path),
                '-c:v', 'libx265',
                '-preset', 'fast',
                '-crf', '26',
                '-tag:v', 'hvc1',
                str(hevc_path)
            ]
            res = subprocess.run(cmd_hevc, capture_output=True, text=True)
            if res.returncode != 0:
                return f'[FAIL HEVC] {pid}: {res.stderr[-200:]}'

        return f'[OK] {pid}'
    except Exception as exc:
        return f'[EXC] {pid}: {exc}'


def main():
    products = get_products()
    print(f'Starting video generation for {len(products)} products...')
    t0 = time.time()

    # Run in parallel with 4 workers for optimal CPU utilization
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(generate_video_for_product, p): p['id'] for p in products}
        done_count = 0
        for future in concurrent.futures.as_completed(futures):
            pid = futures[future]
            try:
                res = future.result()
                done_count += 1
                if done_count % 10 == 0 or done_count == len(products):
                    print(f'Progress: {done_count}/{len(products)} ({res})')
            except Exception as e:
                print(f'Error processing {pid}: {e}')

    elapsed = time.time() - t0
    print(f'Video generation complete in {elapsed:.1f}s.')

    # Rebuild redesign in production mode to inject all video tags into product pages
    print('Rebuilding storefront pages with video markup...')
    rebuild_cmd = [sys.executable, str(ROOT / 'redesign/build_redesign.py'), '--production']
    reb = subprocess.run(rebuild_cmd, cwd=str(ROOT), capture_output=True, text=True)
    if reb.returncode == 0:
        print('Storefront pages rebuilt successfully with all video clips.')
    else:
        print('Storefront rebuild error:', reb.stderr[:300])


if __name__ == '__main__':
    main()
