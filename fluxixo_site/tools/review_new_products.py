"""Review the products a local prepare step added (tools/local_daily.py prepare) before they are built and published.

  python fluxixo_site/tools/review_new_products.py [--out DIR]

New products are those in dist/js/catalog.js that are not in the last commit. For each one it prints the seller title,
link, markets, the texts in all six languages with the text checker's findings, the seller-title mirroring check, the
Russian "who / what to check" notes, and existing products whose English names share two or more meaningful words.

It also writes one sheet per product (default .qa/review-new/<id>.png): every photo over the site's paper colour and
again over magenta. Magenta shows what the paper hides: half-transparent patches where the cut-out model was unsure,
as with a pale product or paw on a pale table (2026-11-15, the cat ball's third photo). Look at every sheet: an
automatic transparency limit cannot tell such a patch from a product that is really see-through (a mesh, clear plastic).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parent
sys.path.insert(0, str(SITE / 'tools'))
import check_texts  # noqa: E402
import copy_originality  # noqa: E402

LANGS = ('en', 'es', 'pt', 'fr', 'he')
PAPER = (243, 240, 233, 255)
MAGENTA = (255, 0, 255, 255)
STOP = {'with', 'for', 'and', 'the', 'smart', 'portable', 'mini', 'digital', 'electric', 'wireless', 'usb', 'led',
        'rechargeable', 'automatic', 'interactive', 'pet', 'car', 'home', 'kit', 'set', 'pro', 'light'}


def catalog_products(text):
    return json.loads(text.split('=', 1)[1].strip().rstrip(';'))['products']


def words(text):
    return {w for w in re.findall(r'[a-z]+', (text or '').casefold()) if len(w) > 3 and w not in STOP}


def photo_sheet(product, out):
    from PIL import Image
    images = [product['image'], *(product.get('views') or [])]
    cell = 320
    sheet = Image.new('RGB', (cell * len(images), cell * 2), (255, 255, 255))
    missing = []
    for col, image in enumerate(images):
        path = SITE / 'dist' / image
        if not path.exists():
            missing.append(image)
            continue
        with Image.open(path) as picture:
            picture.load()
            photo = picture.convert('RGBA')
        photo.thumbnail((cell - 8, cell - 8), Image.Resampling.LANCZOS)
        for row, colour in enumerate((PAPER, MAGENTA)):
            tile = Image.new('RGBA', (cell - 8, cell - 8), colour)
            tile.alpha_composite(photo, ((cell - 8 - photo.width) // 2, (cell - 8 - photo.height) // 2))
            sheet.paste(tile.convert('RGB'), (col * cell + 4, row * cell + 4))
    target = out / f'{product["id"]}.png'
    sheet.save(target)
    return target, len(images), missing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(REPO / '.qa' / 'review-new'))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    head = subprocess.run(['git', '-C', str(REPO), 'show', 'HEAD:fluxixo_site/dist/js/catalog.js'],
                          capture_output=True, check=True).stdout.decode('utf-8')
    old = catalog_products(head)
    now = catalog_products((SITE / 'dist/js/catalog.js').read_text(encoding='utf-8'))
    i18n = json.loads((SITE / 'tools/i18n_data.json').read_text(encoding='utf-8'))
    long_copy = json.loads((SITE / 'tools/ru_long_copy.json').read_text(encoding='utf-8'))
    old_ids = {p['id'] for p in old}
    new = [p for p in now if p['id'] not in old_ids and not p.get('demo')]
    print(f'new products: {len(new)} | catalog now {len(now)}')
    total_problems = 0
    for p in new:
        pid = p['id']
        print('\n' + '=' * 100)
        print(pid, '| category', p.get('category'), '| type', p.get('sourceTask'), '| markets', p.get('availableMarkets'))
        print('seller title:', p.get('sourceTitle'))
        print('link:', p.get('affiliateUrl'), '| listing', p.get('sourceUrl'))
        en_name = i18n['products'].get(pid, {}).get('en', {}).get('name', '')
        mine = words(en_name + ' ' + (p.get('sourceTitle') or ''))
        close = []
        for q in old:
            name = i18n['products'].get(q['id'], {}).get('en', {}).get('name', '')
            shared = mine & words(name)
            if len(shared) >= 2:
                close.append(f'{q["id"]} "{name}" shares {sorted(shared)}')
        print('similar existing products:', close or 'none')
        problems = []
        bundle = {'ru': {'name': p['name'], 'headline': p.get('headline', []), 'description': p['description']}}
        bundle.update({lang: i18n['products'].get(pid, {}).get(lang) for lang in LANGS})
        for lang, texts in bundle.items():
            if not texts:
                problems.append(f'{lang}: texts missing')
                continue
            print(f'{lang.upper()}  {texts["name"]}\n    {" ".join(texts.get("headline", []))}\n    {texts["description"]}')
            for part in (texts['name'], *texts.get('headline', []), texts['description']):
                check_texts.check_string(part, lang, f'{pid}/{lang}', problems)
        problems += copy_originality.check_source_title_mirroring(
            {k: v for k, v in bundle.items() if v}, p.get('sourceTitle') or '')
        more = long_copy.get(pid)
        if more:
            print('RU who:', more['who'])
            for item in more['check']:
                print('   check:', item)
            for part in (more['who'], *more['check']):
                check_texts.check_string(part, 'ru', f'{pid}/more', problems)
        else:
            problems.append('ru: "who / what to check" notes missing (tools/ru_long_copy.json)')
        sheet, count, missing = photo_sheet(p, out)
        if count < 3:
            problems.append(f'only {count} photo(s); new products get three')
        problems += [f'photo file missing: {m}' for m in missing]
        print(f'photos: {count} -> {sheet}  (top row over paper, bottom row over magenta)')
        print('problems:', problems or 'none')
        total_problems += len(problems)
    print('\nproblems in total:', total_problems)
    return 1 if total_problems else 0


if __name__ == '__main__':
    sys.exit(main())
