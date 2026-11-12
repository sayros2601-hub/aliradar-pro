"""Apply the proofreading corrections in text_fixes.json to the product texts.

Translations live in tools/i18n_data.json, Russian (the base language) in dist/js/catalog.js.
Re-running is safe: a correction that is already in place changes nothing.
Run: python tools/apply_text_fixes.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / 'tools/i18n_data.json'
CATALOG = ROOT / 'dist/js/catalog.js'
FR_SMALL = {'de', 'du', 'des', 'à', 'au', 'aux', 'pour', 'avec', 'en', 'et', 'sur', 'la', 'le', 'les', 'un', 'une'}


def resolve(prefix, ids):
    hits = [i for i in ids if i == prefix or i.startswith(prefix + '-')]
    if len(hits) != 1:
        raise SystemExit(f'text_fixes.json: "{prefix}" matches {len(hits)} products')
    return hits[0]


def value(field, text):
    return text.split('|') if field == 'headline' else text


def fr_title(name):
    """French names follow the Title Case used by the rest of the catalog."""
    def cap(part, first):
        m = re.match(r"^([dl]['’])(.+)$", part, flags=re.I)
        if m:
            return m[1].lower() + m[2][:1].upper() + m[2][1:]
        if part.lower() in FR_SMALL and not first:
            return part
        return part[:1].upper() + part[1:]
    return ' '.join('-'.join(cap(piece, i == 0 and j == 0) for j, piece in enumerate(word.split('-'))) for i, word in enumerate(name.split(' ')))


def main():
    fixes = json.loads((ROOT / 'tools/text_fixes.json').read_text(encoding='utf-8'))
    raw = I18N.read_text(encoding='utf-8')
    data = json.loads(raw)
    changed = 0
    for lang in ('es', 'pt', 'en', 'fr', 'he'):
        for prefix, fields in fixes.get(lang, {}).items():
            entry = data['products'][resolve(prefix, data['products'])][lang]
            for field, text in fields.items():
                new = value(field, text)
                if entry.get(field) != new:
                    entry[field], changed = new, changed + 1
    # House rules that apply to every product, present and future.
    for entry in data['products'].values():
        fr, he = entry.get('fr'), entry.get('he')
        if fr and fr.get('name') and fr_title(fr['name']) != fr['name']:
            fr['name'], changed = fr_title(fr['name']), changed + 1
        if he:
            for field in ('name', 'description'):
                fixed = re.sub(r'(?<![֐-׿])לד(?![֐-׿])', 'LED', he.get(field, ''))
                if fixed != he.get(field, ''):
                    he[field], changed = fixed, changed + 1
    indent = 2 if raw.startswith('{\n  "') else (1 if raw.startswith('{\n "') else None)
    I18N.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + ('\n' if raw.endswith('\n') else ''), encoding='utf-8', newline='\n')

    source = CATALOG.read_text(encoding='utf-8')
    head, body = source.split('=', 1)
    catalog = json.loads(body.strip().rstrip(';'))
    ids = [p['id'] for p in catalog['products']]
    for prefix, fields in fixes.get('ru', {}).items():
        hits = [i for i in ids if i == prefix or i.startswith(prefix + '-')]
        if not hits:
            continue  # not in the showroom yet
        product = next(p for p in catalog['products'] if p['id'] == hits[0])
        for field, text in fields.items():
            new = value(field, text)
            if product.get(field) != new:
                if field == 'description' and product.get('details', '').startswith(product['description']):
                    product['details'] = new + product['details'][len(product['description']):]
                product[field], changed = new, changed + 1
    CATALOG.write_text(head + '= ' + json.dumps(catalog, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8', newline='\n')
    print(f'{changed} text(s) corrected')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
