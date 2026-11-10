"""One-off: copy the open-licence (OFL) display fonts from Google Fonts into dist/assets/fonts.

The site's Content-Security-Policy only allows fonts from its own domain, so they are self-hosted.
Writes redesign/static/fonts.json: for each page group, the @font-face rules to inline.
Run again only to change fonts: python redesign/fetch_fonts.py
"""
import json
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / 'dist/assets/fonts'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
GROUPS = {
    'latin': ('family=Bricolage+Grotesque:wdth,wght@75,800&family=Instrument+Serif:ital@1', {'latin', 'latin-ext'}),
    'ru': ('family=Oswald:wght@600..700&family=Playfair+Display:ital,wght@1,500', {'cyrillic', 'latin'}),
    'he': ('family=Heebo:wght@400..900&family=Frank+Ruhl+Libre:wght@500', {'hebrew', 'latin'}),
}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30).read()


def main():
    result = {}
    for group, (query, subsets) in GROUPS.items():
        css = get(f'https://fonts.googleapis.com/css2?{query}&display=swap').decode('utf-8')
        rules = []
        for subset, block in re.findall(r'/\* ([a-z-]+) \*/\s*(@font-face \{.*?\})', css, flags=re.S):
            if subset not in subsets:
                continue
            family = re.search(r"font-family: '([^']+)'", block)[1]
            style = re.search(r'font-style: (\w+)', block)[1]
            url = re.search(r'url\((https://[^)]+\.woff2)\)', block)[1]
            name = f'{family.lower().replace(" ", "-")}-{style}-{subset}.woff2'
            target = FONTS / name
            if not target.exists():
                target.write_bytes(get(url))
            rule = re.sub(r'url\(https://[^)]+\)', f'url(/assets/fonts/{name})', block)
            rules.append(re.sub(r'\s+', ' ', rule).replace('; }', '}').replace('{ ', '{').replace(': ', ':').replace('; ', ';'))
            print(group, name, target.stat().st_size)
        result[group] = ''.join(rules)
    (HERE / 'static/fonts.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
