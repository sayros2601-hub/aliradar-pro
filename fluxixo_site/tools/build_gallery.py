"""Extra studio views for each product: other photos of the same listing, cut out like the main image.

The site never shows a seller photo as it is. For every product this finds its AliExpress listing (the stored item ID,
or a keyword search whose result images match the stored seller photo), takes the listing's other photos, and keeps
only those that cut out cleanly: no text posters (OCR), one dominant object, not a copy of the main view.

  python tools/build_gallery.py [--limit N] [--only ID,ID]

Needs ALI_APP_KEY / ALI_APP_SECRET, rembg and tesseract (the daily GitHub job has all three). Products already listed
in tools/gallery.json are skipped, so the daily run only handles new products. Writes assets/images/<id>-v<n>.webp
with 480/800 thumbnails and records them in tools/gallery.json, which redesign/build_redesign.py reads.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parent
DIST = SITE / 'dist'
STATE = SITE / 'tools/gallery.json'
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SITE / 'tools'))
from fluxixo_ai.autonomous import _source_images, mask_usable  # noqa: E402
from fluxixo_ai.policy import DETAIL, QUERY  # noqa: E402
import locales as L  # noqa: E402

API_URL = 'https://api-sg.aliexpress.com/sync'
MAX_EXTRA = 3
MATCH = 10        # dHash distance at which two photos count as the same picture
DIFFERENT = 26    # cut-outs (cropped to the product) closer than this to an already kept view are dropped as repeats


def api(method, params):
    key, secret = os.environ['ALI_APP_KEY'], os.environ['ALI_APP_SECRET']
    for attempt in range(4):
        time.sleep(1.2 + attempt)
        body = {'app_key': key, 'method': method, 'sign_method': 'sha256', 'timestamp': str(int(time.time() * 1000)), **params}
        body['sign'] = hmac.new(secret.encode(), ''.join(f'{k}{v}' for k, v in sorted(body.items())).encode(),
                                hashlib.sha256).hexdigest().upper()
        try:
            with urllib.request.urlopen(urllib.request.Request(API_URL, data=urllib.parse.urlencode(body).encode()), timeout=25) as r:
                result = json.loads(r.read().decode('utf-8'))
        except Exception:
            continue
        if result.get('error_response', {}).get('code') == 'ApiCallLimit':
            time.sleep(3)
            continue
        envelope = result.get(method.replace('.', '_') + '_response', {}).get('resp_result', {})
        rows = ((envelope.get('result') or {}).get('products') or {}).get('product') or []
        return [rows] if isinstance(rows, dict) else rows
    return []


def fetch(url, small=False):
    if small and re.search(r'\.(jpe?g|png|webp)$', url, re.I):
        url += '_220x220.jpg'
    request = urllib.request.Request(url, headers={'Referer': 'https://www.aliexpress.com/', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(request, timeout=20) as r:
            if not r.headers.get('Content-Type', '').startswith('image/'):
                return None
            data = r.read(12_000_000)
        image = Image.open(BytesIO(data))
        image.load()
        return image
    except Exception:
        return None


def dhash(image):
    grey = image.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    px = list(grey.tobytes())
    return sum(1 << i for i in range(64) if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])


def on_white(cutout):
    canvas = Image.new('RGB', cutout.size, 'white')
    canvas.paste(cutout, mask=cutout.getchannel('A'))
    return canvas


def distance(a, b):
    return bin(a ^ b).count('1')


def listing_images(row):
    return _source_images(row, row.get('product_main_image_url'))


def find_listing(product, name_en, original_hash):
    """The listing whose photos include the stored seller photo."""
    pid = product.get('sourceProductId') or (re.search(r'/item/(\d+)', product.get('sourceUrl', '')) or [None, None])[1]
    if pid:
        for market in (product.get('sourceMarket') or 'US', 'US'):
            rows = api(DETAIL, {'product_ids': pid, 'country': market, 'target_currency': 'USD', 'target_language': 'EN',
                                'tracking_id': 'default'})
            if rows:
                return pid, listing_images(rows[0])
    words = name_en.split()
    queries = [(name_en, 'US'), (name_en, 'BR'), (' '.join(words[:3]), 'US')] if len(words) > 3 else [(name_en, 'US'), (name_en, 'BR')]
    seen = set()
    for keywords, market in queries:
        rows = api(QUERY, {'keywords': keywords, 'target_currency': 'USD', 'target_language': 'EN', 'ship_to_country': market,
                           'page_size': '40', 'page_no': '1', 'tracking_id': 'default'})
        rows = [r for r in rows if str(r.get('product_id')) not in seen]
        seen.update(str(r.get('product_id')) for r in rows)
        jobs = [(r, url) for r in rows for url in listing_images(r)[:6]]
        with ThreadPoolExecutor(12) as pool:
            hashes = list(pool.map(lambda job: (job[0], (lambda im: dhash(im) if im else None)(fetch(job[1], small=True))), jobs))
        best = min(((distance(h, original_hash), str(r.get('product_id')), r) for r, h in hashes if h is not None),
                   default=None, key=lambda t: (t[0], t[1]))
        if best and best[0] <= MATCH:
            return best[1], listing_images(best[2])
    return None, []


def poster(path):
    """True when the photo carries words (an infographic, a size chart): those never become studio views."""
    try:
        out = subprocess.run(['tesseract', str(path), 'stdout', '--psm', '11', 'tsv'], capture_output=True, timeout=30).stdout.decode('utf-8', 'replace')
    except (OSError, subprocess.SubprocessError):
        return True
    words = [c[11] for c in (line.split('\t') for line in out.splitlines()[1:])
             if len(c) >= 12 and c[10].replace('.', '', 1).lstrip('-').isdigit() and float(c[10]) >= 40
             and len(re.sub(r'\W', '', c[11])) >= 3]
    return len(words) >= 1


def solid_box(cutout):
    """Bounding box of the clearly opaque pixels (a faint halo does not count)."""
    return cutout.getchannel('A').point(lambda v: 255 if v > 128 else 0).getbbox()


def scene(cutout):
    """True when the cut-out failed and kept a whole picture: a filled rectangle with opaque corners."""
    box = solid_box(cutout)
    if not box:
        return True
    alpha = cutout.getchannel('A').crop(box)
    w, h = alpha.size
    corners = sum(alpha.getpixel((x, y)) > 200 for x, y in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)))
    filled = sum(alpha.resize((64, 64), Image.Resampling.BOX).histogram()[200:]) / 4096
    return corners >= 3 or filled > 0.9


def shape_hash(cutout):
    """dHash of the product alone, so the same view at another size or position still counts as a repeat."""
    return dhash(on_white(cutout.crop(solid_box(cutout) or (0, 0) + cutout.size)))


def keep_main(cutout):
    """Clear everything not attached to the product: stray captions, icons and arrows the cut-out kept."""
    side = 160
    alpha = cutout.getchannel('A')
    small = alpha.resize((side, side), Image.Resampling.BOX).tobytes()
    seen, parts = set(), []
    for start in range(side * side):
        if small[start] < 60 or start in seen:
            continue
        stack, part = [start], []
        seen.add(start)
        while stack:
            point = stack.pop()
            part.append(point)
            x, y = point % side, point // side
            for nb in (point - 1 if x else -1, point + 1 if x < side - 1 else -1, point - side if y else -1, point + side if y < side - 1 else -1):
                if nb >= 0 and nb not in seen and small[nb] >= 60:
                    seen.add(nb)
                    stack.append(nb)
        parts.append(part)
    if not parts:
        return cutout
    main = max(parts, key=len)
    biggest = len(main)
    xs, ys = [p % side for p in main], [p // side for p in main]
    pad = side // 10
    near = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    keep = bytearray(side * side)
    for part in parts:
        inside = sum(near[0] <= p % side <= near[2] and near[1] <= p // side <= near[3] for p in part) / len(part)
        if len(part) >= biggest * 0.5 or (len(part) >= biggest * 0.05 and inside > 0.8):
            for point in part:
                keep[point] = 255
    mask = Image.frombytes('L', (side, side), bytes(keep)).resize(cutout.size, Image.Resampling.BILINEAR).point(lambda v: 255 if v > 40 else 0)
    cleaned = cutout.copy()
    cleaned.putalpha(Image.composite(alpha, Image.new('L', cutout.size, 0), mask))
    return cleaned


def studio(cutout):
    """The same framing as the main image: product centred on a transparent 1254 px square."""
    cutout = cutout.crop(cutout.getbbox())
    scale = min(903 / cutout.width, 903 / cutout.height)
    size = (max(1, round(cutout.width * scale)), max(1, round(cutout.height * scale)))
    cutout = cutout.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (1254, 1254), (0, 0, 0, 0))
    canvas.alpha_composite(cutout, ((1254 - size[0]) // 2, (1254 - size[1]) // 2))
    return canvas


def save(canvas, relative):
    target = DIST / relative
    canvas.save(target, 'WEBP', quality=90, method=5)
    for width in (480, 800):
        small = canvas.copy()
        small.thumbnail((width, width), Image.Resampling.LANCZOS)
        small.save(DIST / L.thumb(relative, width), 'WEBP', quality=82, method=4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    if not (os.environ.get('ALI_APP_KEY') and os.environ.get('ALI_APP_SECRET')):
        print('Gallery: no AliExpress credentials, skipped.')
        return
    if not shutil.which('tesseract'):
        print('Gallery: tesseract missing, skipped (text posters could not be filtered).')
        return
    from rembg import new_session, remove
    session = new_session('u2net')
    catalog = json.loads((DIST / 'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
    names = json.loads((SITE / 'tools/i18n_data.json').read_text(encoding='utf-8'))['products']
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    only = {x for x in args.only.split(',') if x}
    todo = [p for p in catalog['products'] if not p.get('demo') and (p['id'] in only if only else p['id'] not in state)]
    if args.limit:
        todo = todo[:args.limit]
    work = SITE / '.gallery-work'
    work.mkdir(exist_ok=True)
    for n, product in enumerate(todo, 1):
        pid_label = product['id']
        record = {'checked': datetime.now(timezone.utc).date().isoformat(), 'source': None, 'images': []}
        try:
            original = Image.open(DIST / product['original'])
            main_view = Image.open(DIST / product['image']).convert('RGBA')
            original_hash = dhash(original)
            name_en = names.get(product['id'], {}).get('en', {}).get('name') or product['name']
            source, urls = find_listing(product, name_en, original_hash)
            record['source'] = source
            kept = [shape_hash(main_view)]
            why = record['rejected'] = {'urls': len(urls)}
            reject = lambda reason: why.__setitem__(reason, why.get(reason, 0) + 1)
            for index, url in enumerate(urls[:9]):
                if len(record['images']) >= MAX_EXTRA:
                    break
                picture = fetch(url)
                if picture is None or picture.width * picture.height > 25_000_000 or min(picture.size) < 350:
                    reject('fetch')
                    continue
                if distance(dhash(picture), original_hash) <= MATCH:
                    reject('same')
                    continue  # the photo the main view was made from
                # Seller photos nearly always carry captions; they sit on the background, which the cut-out drops.
                # Loose caption fragments are cleared, and only a finished view with no words left is kept.
                cutout = keep_main(remove(picture.convert('RGBA'), session=session).convert('RGBA'))
                if not mask_usable(cutout) or scene(cutout):
                    reject('mask')
                    continue
                canvas = studio(cutout)
                check_png = work / f'{pid_label}-{index}.png'
                white = on_white(canvas)
                white.resize((2508, 2508), Image.Resampling.LANCZOS).save(check_png)  # small captions read better enlarged
                if poster(check_png):
                    reject('text')
                    continue
                h = shape_hash(canvas)
                if any(distance(h, k) <= DIFFERENT for k in kept):
                    reject('repeat')
                    continue
                kept.append(h)
                relative = f'assets/images/{pid_label}-v{len(record["images"]) + 2}.webp'
                save(canvas, relative)
                record['images'].append(relative)
        except Exception as error:  # one odd listing never stops the rest
            record['error'] = type(error).__name__
        state[pid_label] = record
        STATE.write_text(json.dumps(dict(sorted(state.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
        print(f'[{n}/{len(todo)}] {pid_label}: listing {record["source"] or "not found"}, {len(record["images"])} extra views {record.get("rejected", {})}', flush=True)
    shutil.rmtree(work, ignore_errors=True)
    total = sum(1 for r in state.values() if r['images'])
    print(f'Gallery: {total} of {len(state)} products have extra views.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
