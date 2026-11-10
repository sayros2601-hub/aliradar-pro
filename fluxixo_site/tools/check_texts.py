"""Mechanical proofreading of every product text in every language.

Catches what a spell-checker cannot: missing translations, text left in the wrong alphabet, Spain/Portugal words
on pages meant for Mexico/Brazil, broken punctuation, and copies that were never translated.
Run: python tools/check_texts.py            (exit code 1 if anything is wrong)
     python tools/check_texts.py --dump DIR (also writes one readable file per language for human review)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ('en', 'pt', 'es', 'fr', 'he')
FIELDS = ('name', 'headline', 'description')

CYRILLIC = re.compile(r'[Ѐ-ӿ]')
HEBREW = re.compile(r'[֐-׿]')
LATIN_WORD = re.compile(r'[A-Za-zÀ-ÿ]{2,}')
# Brand names, units and tech terms that legitimately stay in Latin letters inside Hebrew or Russian text.
LATIN_OK = re.compile(r'^(AliExpress|FLUXIXO|PETKIT|ATTACK|SHARK|CABLETIME|UGREEN|Logitech|Baseus|Vgate|XOSS|AGM|USB|LED|LCD|UV|GPS|TPMS|HUD|RGB|AI|NFC|RJ\d*|E\d+|Type|C|Bluetooth|Wi|Fi|WiFi|App|iOS|Android|'
                      r'mm|cm|ml|kg|mAh|W|V|Hz|IP\d*|IPX\d*|HD|FHD|K|D|in|pH|TDS|PD|AC|DC|OLED|IPS|SOS|PSI|BMS|MagSafe|CarPlay|OBD|DIY|Sous|Vide|'
                      r'[A-Z]{1,5}\d*|\d+[A-Za-z]+)$')

# Words that mark the wrong regional variety.
SPAIN = ('ordenador', 'móvil', 'móviles', 'coche', 'coches', 'zumo', 'patata', 'gafas', 'nevera', 'altavoz', 'altavoces', 'auriculares',
         'vosotros', 'vuestro', 'vuestra', 'ratón', 'mando', 'aparcar', 'aparcamiento', 'grifo', 'conducir', 'maletero', 'neumático', 'neumáticos',
         'fregar', 'bombilla', 'tarta', 'piscina', 'vale', 'echar un vistazo', 'aquí tenéis', 'podéis')
PORTUGAL = ('ecrã', 'telemóvel', 'telemóveis', 'utilizador', 'utilizadores', 'ficheiro', 'autocarro', 'casa de banho', 'frigorífico',
            'pequeno-almoço', 'comboio', 'rato', 'tu podes', 'vós', 'aplicação móvel', 'câmara', 'controlo', 'planear', 'registo',
            'equipa', 'facto', 'contacto', 'óptimo', 'electr', 'acção', 'direcção', 'objecto', 'projecto', 'actual')
BRITISH = ('colour', 'favourite', 'tyre', 'tyres', 'aluminium', 'centre', 'metre', 'litre', 'organise', 'torch', 'boot of')


def texts():
    data = json.loads((ROOT / 'tools/i18n_data.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT / 'dist/js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
    return data, [p for p in catalog['products'] if not p['demo']]


def flat(value):
    return ' '.join(value) if isinstance(value, list) else value


def check_string(text, lang, where, problems):
    def bad(message):
        problems.append(f'{where}: {message} -> {text[:90]!r}')
    if text != text.strip():
        bad('space at the start or end')
    if '  ' in text:
        bad('double space')
    if re.search(r'\s[,.]', text):
        bad('space before a comma or full stop')
    if re.search(r'[,;:!?][A-Za-zА-Яа-я֐-׿]', text):
        bad('missing space after punctuation')
    if re.search(r'\.\.(?!\.)|,,|;;', text) and '...' not in text:
        bad('doubled punctuation')
    if text.count('(') != text.count(')') or text.count('«') != text.count('»'):
        bad('unbalanced brackets or quotes')
    if lang != 'ru' and CYRILLIC.search(text):
        bad('Russian letters in a non-Russian text')
    if lang != 'he' and HEBREW.search(text):
        bad('Hebrew letters in a non-Hebrew text')
    if lang in ('he', 'ru'):
        odd = [w for w in LATIN_WORD.findall(text) if not LATIN_OK.match(w)]
        if odd:
            bad(f'Latin words left untranslated {odd}')
        if lang == 'he' and not HEBREW.search(text):
            bad('no Hebrew letters at all')
    low = ' ' + re.sub(r'[^\w\s-]', ' ', text.lower()) + ' '
    for words, target, tag in ((SPAIN, 'es', 'Spain word (site is for Mexico)'), (PORTUGAL, 'pt', 'Portugal word (site is for Brazil)'),
                               (BRITISH, 'en', 'British spelling (site uses US English)')):
        if lang == target:
            for word in words:
                if f' {word} ' in low or (word == 'electr' and ' electr' in low):
                    bad(f'{tag}: "{word}"')
    if lang == 'es':
        if text.count('!') != text.count('¡') or text.count('?') != text.count('¿'):
            bad('Spanish needs opening ¡ or ¿')
    if lang == 'fr' and re.search(r'[^\s  ][!?;:](\s|$)', text) and not re.search(r'https?:', text):
        bad('French needs a (non-breaking) space before ! ? ; :')


def words(text):
    return re.findall(r'[\w֐-׿]+', text.casefold())


# Filler a generator puts in when it has nothing to say.
FILLER = {'aliexpress', 'fluxixo', 'seller', 'title', 'vendedor', 'vendeur', 'título', 'titre', 'продавца', 'название'}


def check_slogan(name, headline, where, problems):
    """A slogan must add something: not the name cut in two, not a shorter copy of it, not filler."""
    slogan = words(flat(headline))
    if not slogan:
        problems.append(f'{where}/headline: empty')
        return
    if set(slogan) <= set(words(name)):
        problems.append(f'{where}/headline: only repeats the product name -> {flat(headline)!r}')
    elif set(slogan) & FILLER:
        problems.append(f'{where}/headline: filler instead of a slogan -> {flat(headline)!r}')


def run(dump=None):
    data, products = texts()
    problems = []
    known = {p['id'] for p in products}
    ru = {p['id']: p for p in products}
    for pid, entry in data['products'].items():
        for lang in LANGS:
            t = entry.get(lang)
            if not t or not all(t.get(k) for k in FIELDS):
                if pid in known:
                    problems.append(f'{pid}/{lang}: translation missing or incomplete')
                continue
            if not isinstance(t['headline'], list) or len(t['headline']) != 2:
                problems.append(f'{pid}/{lang}: headline must be two lines')
            check_slogan(t['name'], t['headline'], f'{pid}/{lang}', problems)
            for field in FIELDS:
                check_string(flat(t[field]), lang, f'{pid}/{lang}/{field}', problems)
            if not t['description'].rstrip().endswith(('.', '!', '?', '…')):
                problems.append(f'{pid}/{lang}/description: no full stop at the end')
            if len(t['name']) > 62:
                problems.append(f'{pid}/{lang}/name: {len(t["name"])} characters, too long for a page title')
        seen = {}
        for lang in LANGS:
            name = entry.get(lang, {}).get('name')
            if name and lang != 'he':
                seen.setdefault(name, []).append(lang)
        for name, langs in seen.items():
            if len(langs) > 2:
                problems.append(f'{pid}: the same name in {langs}, probably not translated -> {name!r}')
    for pid in known - set(data['products']):
        problems.append(f'{pid}: no translations at all')
    for p in products:
        for field in FIELDS:
            check_string(flat(p[field]), 'ru', f'{p["id"]}/ru/{field}', problems)
        check_slogan(p['name'], p['headline'], f'{p["id"]}/ru', problems)
        for fact in p.get('facts', []):
            for part in (fact.get('label'), fact.get('value')):
                if part and part not in ('Подборка',) and fact.get('label') != 'Подборка':
                    for lang in LANGS:
                        if not (data.get('facts', {}).get(part, {}).get(lang) or data.get('cats', {}).get(part, {}).get(lang)):
                            problems.append(f'{p["id"]}: fact "{part}" has no {lang} translation')
    for cat, labels in data['cats'].items():
        for lang in LANGS:
            if not labels.get(lang):
                problems.append(f'category "{cat}": no {lang} name')
            else:
                check_string(labels[lang], lang, f'category {cat}/{lang}', problems)

    if dump:
        out = Path(dump)
        out.mkdir(parents=True, exist_ok=True)
        for lang in LANGS:
            lines = []
            for pid, entry in data['products'].items():
                t = entry.get(lang)
                if t:
                    base = ru.get(pid, {})
                    lines.append(f'{pid} | RU: {base.get("name", "-")}\n  N: {t.get("name")}\n  H: {flat(t.get("headline", ""))}\n  D: {t.get("description")}')
            (out / f'{lang}.txt').write_text('\n'.join(lines), encoding='utf-8')
        (out / 'ru.txt').write_text('\n'.join(
            f'{p["id"]}\n  N: {p["name"]}\n  H: {flat(p["headline"])}\n  D: {p["description"]}\n  C: {p["category"]} F: {p.get("facts")}' for p in products), encoding='utf-8')
    return problems


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    found = run(sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--dump' else None)
    for line in found:
        print(line)
    print(f'{len(found)} problem(s)')
    sys.exit(1 if found else 0)
