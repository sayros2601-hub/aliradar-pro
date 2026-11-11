"""The FLUXIXO storefront ("editorial" design: paper, ink, one accent).

Reads the catalog (dist/js/catalog.js, tools/i18n_data.json) and writes every visitor-facing page.
  python redesign/build_redesign.py               local preview in redesign/site/ (noindex)
  python redesign/build_redesign.py --production  writes into dist/, after tools/build_search.py, which still owns
                                                  thumbnails, sitemaps, robots.txt and the feeds
"""
import colorsys
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from html import escape as e
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = ROOT / 'dist'
PROD = '--production' in sys.argv
OUT = DIST if PROD else HERE / 'site'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(HERE))
import locales as L  # noqa: E402
from ui_text import CATEGORY_COPY_RU, UI  # noqa: E402

ORIGIN = 'https://www.fluxixo.shop'
LANGS = ('es', 'pt', 'en', 'fr', 'he', 'ru')
RTL = {'he'}
ACCENT = '#e4007c'
INK = '#121014'
PAPER = '#f3f0e9'


def last_drop_day():
    """UTC day of the latest real addition, from the daily job's ledger; today when there is no ledger."""
    try:
        ledger = json.loads((ROOT.parent / 'data/fluxixo_daily_ledger.json').read_text(encoding='utf-8'))
        days = [day for day, rows in ledger.get('days', {}).items() if rows]
        days += [row['day'] for row in ledger.get('validation_runs', {}).values() if row.get('day')]
        if days:
            return max(days)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return datetime.now(timezone.utc).date().isoformat()


LAST_DROP = last_drop_day()

# One calm pastel per world; the page repaints to it as the world scrolls into the middle of the screen.
WORLDS = {
    'Техника': '#dfe5fb', 'Дом': '#f1e3cf', 'Кухня': '#d9eede', 'В дороге': '#fbe7a6', 'Инструменты': '#fdd8c4',
    'Уход': '#f8d9e6', 'Спорт': '#d3edf5', 'На природе': '#dfeac4', 'Питомцы': '#e9dcf8',
}


# Self-hosted @font-face rules (the site's CSP allows fonts from its own domain only); see fetch_fonts.py.
FONT_CSS = json.loads((HERE / 'static/fonts.json').read_text(encoding='utf-8'))
FONT_PRELOAD = {'ru': 'oswald-normal-cyrillic', 'he': 'heebo-normal-hebrew'}
CSS = re.sub(r'\s*\n\s*', ' ', re.sub(r'/\*.*?\*/', '', (HERE / 'static/style.css').read_text(encoding='utf-8'), flags=re.S)).strip().replace('</', '<\\/')
VERIFY = ('<meta name="google-site-verification" content="BUSamFSGELSfaWQEaVVj2QzUgKQvWovtg-ZaHCfKNb0">'
          '<meta name="msvalidate.01" content="49287D3DFF71EA9430905E14A0A426F2"><meta name="yandex-verification" content="deee62492f76cf5b">')
ROOT_TITLE = 'FLUXIXO | Curated AliExpress Finds'
ROOT_DESC = 'Three new AliExpress finds every day: gadgets, home and kitchen tools, and travel accessories, as clean studio cutouts with direct links.'


_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true">{}</svg>'
ICONS = {
    'home': _SVG.format('<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'),
    'grid': _SVG.format('<rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/>'
                        '<rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/>'),
    'bag': _SVG.format('<path d="M5 8h14l-1 13H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>'),
    'search': _SVG.format('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
    'globe': _SVG.format('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'),
}

def product_metadata(name, description, lang, source_id, marker=None):
    """Preserve legacy metadata; keep new listings readable and bounded."""
    if source_id is None:
        return L.fit_title(name, lang), L.fit_description(description, lang)
    if not isinstance(source_id, str) or not re.fullmatch(r'[1-9][0-9]{0,31}', source_id):
        raise ValueError('Invalid source product ID')
    label = f'{marker} · {name}' if marker else name
    title = L.fit_title(label, lang)
    if len(title) > 70:
        suffix = ' | FLUXIXO'
        title = ' '.join(label.split())[:70 - len(suffix)].rstrip() + suffix
    desc = L.fit_description(f'{marker}. {description}' if marker else description, lang)
    return title, desc


_METADATA_MARKERS = {
    'ru': 'Предложение', 'en': 'Listing', 'pt': 'Oferta',
    'es': 'Opción', 'fr': 'Offre', 'he': 'אפשרות',
}


def assign_product_metadata(items_by_lang):
    """Resolve collisions across locales while preserving all legacy metadata."""
    from collections import Counter

    rows = []
    for lang in LANGS:
        for product in items_by_lang.get(lang, []):
            source_id = product.get('sourceProductId')
            base = product_metadata(product['name'], product['description'], lang, source_id)
            if lang == 'ru' and product['id'] == 'import-0024':
                base = WATCH_SEO_RU['title'], WATCH_SEO_RU['description']
            rows.append((lang, product, source_id, base))
    title_counts = Counter(row[3][0] for row in rows)
    desc_counts = Counter(row[3][1] for row in rows)
    result, used_titles, used_desc = {}, set(), set()
    pending = []
    for lang, product, source_id, base in rows:
        if source_id is None or (title_counts[base[0]] == 1 and desc_counts[base[1]] == 1):
            result[(lang, product['id'])] = base
            used_titles.add(base[0])
            used_desc.add(base[1])
        else:
            pending.append((lang, product, source_id, base))

    # Rank the complete same-name family, including unchanged legacy entries.
    families = {}
    for lang, product, source_id, _ in rows:
        key = (lang, ' '.join(product['name'].split()).casefold())
        sort_key = (0, product['id']) if source_id is None else (1, int(source_id), product['id'])
        families.setdefault(key, []).append((sort_key, product['id']))
    ranks = {}
    for key, members in families.items():
        for rank, (_, product_id) in enumerate(sorted(members), 1):
            ranks[(key[0], product_id)] = rank
    for lang, product, source_id, _ in sorted(pending, key=lambda row: (row[0], int(row[2]), row[1]['id'])):
        rank = ranks[(lang, product['id'])]
        while True:
            marker = f'{_METADATA_MARKERS[lang]} {rank}'
            title, desc = product_metadata(product['name'], product['description'], lang, source_id, marker)
            if title not in used_titles and desc not in used_desc:
                break
            rank += 1
        result[(lang, product['id'])] = title, desc
        used_titles.add(title)
        used_desc.add(desc)
    return result


WATCH_SEO_RU = {
    'title': 'Купить наручные часы — умные часы на AliExpress | FLUXIXO',
    'description': 'Купить наручные часы: умные часы с экраном. Сравните изображения и уточните характеристики, стоимость и доставку у продавца AliExpress.',
    'heading': 'Умные наручные часы',
    'copy': ('Умные наручные часы с экраном. Купить часы можно у продавца на AliExpress; '
             'модель и характеристики по сохранённому каталогу не подтверждены. До заказа '
             'проверьте совместимость со смартфоном, размер, цену, доставку и возврат.'),
}


def load():
    catalog = json.loads((DIST / 'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
    data = json.loads((ROOT / 'tools/i18n_data.json').read_text(encoding='utf-8'))
    products = [p for p in catalog['products'] if not p['demo']]
    # Extra cut-out views from tools/build_gallery.py; seller photos themselves are never shown.
    gallery_file = ROOT / 'tools/gallery.json'
    gallery = json.loads(gallery_file.read_text(encoding='utf-8')) if gallery_file.exists() else {}
    # Odd category names map onto the hub whose English label they share.
    by_label = {data['cats'][k]['en']: k for k in L.CATEGORY_SLUGS if k in data['cats']}
    for p in products:
        key = L.category_key(p['category'])
        p['world'] = key or by_label.get(data['cats'].get(p['category'], {}).get('en'), 'Дом')
        colour, p['dark'] = tint(p['image'])
        p['views'] = [p['image']] + [v for v in gallery.get(p['id'], {}).get('images', []) if (DIST / v).exists()]
        p['tint'] = colour or WORLDS[p['world']]
    return products, data


def tint(image):
    """A pastel of the product's own dominant colour; grey products get None and take their world's colour. Also says if the product is dark."""
    path = DIST / L.thumb(image)
    if not path.exists():
        path = DIST / image
    r = g = b = weight = light = seen = 0.0
    small = Image.open(path).convert('RGBA').resize((48, 48))
    # Pillow renamed getdata(); the daily build server and this PC may run different versions.
    for pr, pg, pb, pa in (small.get_flattened_data() if hasattr(small, 'get_flattened_data') else small.getdata()):
        if pa < 128:
            continue
        _, lum, sat = colorsys.rgb_to_hls(pr / 255, pg / 255, pb / 255)
        light, seen = light + lum, seen + 1
        w = sat * sat * (1 - abs(lum - 0.5) * 1.6) if 0.12 < lum < 0.92 else 0
        r, g, b, weight = r + pr * w, g + pg * w, b + pb * w, weight + w
    dark = seen > 0 and light / seen < 0.42
    if weight < 60:
        return None, dark
    hue, _, sat = colorsys.rgb_to_hls(r / weight / 255, g / weight / 255, b / weight / 255)
    rr, gg, bb = colorsys.hls_to_rgb(hue, 0.88, min(0.75, max(0.4, sat)))
    return f'#{round(rr * 255):02x}{round(gg * 255):02x}{round(bb * 255):02x}', dark


def slug(key):
    return L.CATEGORY_SLUGS[key]['en']


def img(path, width=None):
    if width:
        t = L.thumb(path, width)
        if (DIST / t).exists():
            return '/' + t
    return '/' + path


class Site:
    def __init__(self, products, data, lang, root=False):
        # root: the English home served at '/', outside the language clusters like the page it replaces.
        self.lang, self.data, self.ui, self.root = lang, data, UI[lang], root
        self.items = []
        self.rtl = lang in RTL
        self.fwd, self.back = ('←', '→') if self.rtl else ('→', '←')
        for p in products:
            t = p if lang == 'ru' else data['products'].get(p['id'], {}).get(lang)
            if t and all(t.get(k) for k in ('name', 'headline', 'description')):
                self.items.append({**p, **{k: t[k] for k in ('name', 'headline', 'description')}})
        self.worlds = [k for k in WORLDS if any(p['world'] == k for p in self.items)]

    def home(self):
        return '/' if self.root else L.catalog_path(self.lang)

    def copy(self, key):
        return CATEGORY_COPY_RU[key] if self.lang == 'ru' else L.CATEGORY_COPY[key][self.lang]

    def ppath(self, p):
        return L.product_path(p, self.lang)

    def cpath(self, key):
        return L.category_path(key, self.lang)

    def cat(self, key):
        return key if self.lang == 'ru' else self.data['cats'].get(key, {}).get(self.lang, key)

    def in_world(self, key):
        return [p for p in self.items if p['world'] == key]

    def buy(self, p, attrs=''):
        return (f'<a class="btn" href="{e(p["affiliateUrl"])}" target="_blank" rel="sponsored nofollow noopener" {attrs}>'
                f'{e(self.ui["cta"])} <span aria-hidden="true">{self.fwd}</span></a>')

    def page(self, title, desc, path, body, alt_paths, schema=None, image=None, colour=PAPER, hreflang=True, noindex=False, tab=None, buy=None):
        u = self.ui
        tag, og_locale = L.LANGUAGES[self.lang][:2]
        lang_links = ''.join(
            f'<a href="{alt_paths.get(l, L.catalog_path(l))}" hreflang="{L.LANGUAGES[l][0]}"{" aria-current=\"true\"" if l == self.lang and not self.root else ""}>'
            f'<b>{l.upper()}</b><span lang="{L.LANGUAGES[l][0]}">{e(L.LANGUAGES[l][2])}</span></a>'
            for l in LANGS)
        lang_button = (f'<button type="button" class="lang-btn" aria-label="{e(u["language"])}" aria-expanded="false">{ICONS["globe"]}{self.lang.upper()}</button>')
        nav = ''.join(f'<a href="{self.home()}#{anchor}">{e(label)}</a>' for anchor, label in zip(('drop', 'mundos', 'todo'), u['nav']))
        image = image or self.items[0]['image']
        ld = ('<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c') + '</script>') if schema else ''
        about = L.about_path(self.lang)
        robots = 'index,follow,max-image-preview:large' if PROD and not noindex else 'noindex,follow'
        rss = f'<link rel="alternate" type="application/rss+xml" title="FLUXIXO — Новые находки с AliExpress" href="{ORIGIN}/rss.xml">\n' if self.lang == 'ru' else ''
        alternates = '\n' + L.alternates(ORIGIN, alt_paths) if hreflang and alt_paths else ''
        fonts = FONT_CSS['latin'] + FONT_CSS.get(self.lang, '')
        preload = FONT_PRELOAD.get(self.lang, 'bricolage-grotesque-normal-latin')
        return f'''<!doctype html>
<html lang="{tag}" dir="{"rtl" if self.rtl else "ltr"}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="{colour}">
<link rel="canonical" href="{ORIGIN}{path}">
{rss}<meta name="robots" content="{robots}">
<meta property="og:type" content="website"><meta property="og:site_name" content="FLUXIXO">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{ORIGIN}{path}"><meta property="og:image" content="{ORIGIN}/{e(image)}">
<meta property="og:locale" content="{og_locale}"><meta name="twitter:card" content="summary_large_image">{alternates}
{VERIFY if self.root else ""}
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="FLUXIXO"><link rel="manifest" href="/{self.manifest_name()}"><link rel="icon" href="/assets/favicon.svg"><link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/{preload}.woff2" crossorigin>
<style>{fonts}{CSS}</style>
{ld}
</head>
<body style="--page:{colour}">
<header class="top"><a class="logo" href="{self.home()}">FLU<i>X</i>I<i>X</i>O</a><nav aria-label="Menu">{nav}</nav>{lang_button}<div class="langs">{lang_links}</div></header>
<main id="main">
{body}
</main>
<footer class="foot">
<p class="wordmark" aria-hidden="true">FLU<i>X</i>I<i>X</i>O</p>
<div class="foot-row"><p>{e(u["foot"])} {e(L.DISCLOSURE[self.lang])}</p>
<nav><a href="{self.home()}">{e(u["home"])}</a><a href="{about}">{e(u["about"])}</a><a href="{about}#privacy">{e(u["privacy"])}</a></nav></div>
</footer>
{self.tabs(tab, buy)}
<script src="/js/fx.js" defer></script>
</body>
</html>'''

    # ---------- components ----------
    def manifest_name(self):
        return 'app.webmanifest' if self.root else f'app-{self.lang}.webmanifest'

    def tabs(self, current=None, buy=None):
        """Phone bottom bar. On a product page it carries the buy button, so the way to the seller is always under the thumb."""
        home, labels = self.home(), self.ui['tabs']
        links = [('home', home, 'home', labels[0]), ('cats', f'{home}#cats', 'grid', labels[1]),
                 ('all', f'{home}#todo', 'bag', labels[2]), ('find', f'{home}#find', 'search', labels[3])]
        if buy:
            links = [links[0], links[2]]
        html = ''.join(f'<a href="{href}" data-tab="{name}"{" aria-current=\"page\"" if name == current else ""}>{ICONS[icon]}<span>{e(label)}</span></a>'
                       for name, href, icon, label in links)
        return f'<nav class="tabs{" buy" if buy else ""}" aria-label="{e(self.ui["app"])}">{html}{self.buy(buy) if buy else ""}</nav>'

    def rope(self, items, eager=False, lead=False, width=None):
        n = len(items)
        ts = [0.5] if n == 1 else [0.17 + i * (0.66 / (n - 1)) for i in range(n)]
        hangs = ''.join(
            f'<a class="hang" data-go href="{self.ppath(p)}" style="left:{t * 100:.1f}%;--y:{(40 + 360 * t * (1 - t)) / 300:.3f};--t:{p["tint"]}">'
            f'<i class="pin"></i><i class="str"></i>'
            f'<img class="cut" src="{img(p["image"], width or (800 if eager else 480))}" alt="{e(p["name"])}" width="480" height="480" loading="{"eager" if eager else "lazy"}" decoding="async"'
            f'{" fetchpriority=\"high\"" if lead and i == 0 else ""}>'
            f'<small>{i + 1:02d}</small><b>{e(p["name"])}</b>{"<span class=hl>" + e(" ".join(p["headline"])) + "</span>" if lead else ""}<em>{e(self.ui["more"])}</em></a>'
            for i, (p, t) in enumerate(zip(items, ts)))
        return (f'<div class="rope{" four" if n > 3 else ""}{" lead" if lead else ""}"{" data-dots" if lead else ""}><svg viewBox="0 0 1200 300" preserveAspectRatio="none" aria-hidden="true">'
                f'<path d="M0 40 Q 600 220 1200 40"/></svg>{hangs}</div>')

    def gallery(self, p, name):
        """Studio views of one product that swipe (phone) or step with arrows (desktop); one view means no controls."""
        views = ''.join(
            f'<img class="cut" src="{img(v, 800)}" alt="{e(name)}" width="800" height="800" decoding="async"'
            f'{" fetchpriority=\"high\"" if i == 0 else " loading=\"lazy\""}>' for i, v in enumerate(p['views']))
        many = len(p['views']) > 1
        arrows = (f' data-label-prev="{e(self.ui["prev"])}" data-label-next="{e(self.ui["next"])}"' if many else '')
        return f'<div class="p-gallery"{arrows}><div class="p-stage"{" data-dots" if many else ""}>{views}</div></div>'

    def card(self, p):
        return (f'<a class="card" data-go data-w="{slug(p["world"])}" href="{self.ppath(p)}" style="--t:{WORLDS[p["world"]]}">'
                f'<span class="ph"><img src="{img(p["image"], 480)}" alt="" width="480" height="480" loading="lazy" decoding="async"></span>'
                f'<span class="nm">{e(p["name"])}</span><span class="ct">{e(self.cat(p["world"]))}</span></a>')

    # ---------- pages ----------
    def build_home(self):
        u, items = self.ui, self.items
        drop = items[:3]
        star = drop[datetime.now(timezone.utc).toordinal() % len(drop)]
        hero = (f'<section class="drop" id="drop" data-page="{PAPER}"><div class="drop-bar">'
                f'<p class="eye"><b>●</b> {e(u["drop"])} · <time data-day datetime="{LAST_DROP}">{LAST_DROP}</time></p>'
                # GitHub starts the daily job hours late and at a different time each day, so no fake countdown:
                # "today" until today's drop lands, then "tomorrow".
                f'<p class="clock">{e(u["next_drop"])}<b data-next="{LAST_DROP}" data-when="{e(u["when"][0])}|{e(u["when"][1])}">'
                f'{e(u["when"][1] if LAST_DROP >= datetime.now(timezone.utc).date().isoformat() else u["when"][0])}</b></p></div>'
                f'<h1 class="d">{e(u["h1"][0])}<span class="s">{e(u["h1"][1])}</span></h1>'
                f'<p class="drop-sub">{e(u["drop_text"])}</p>{self.rope(drop, eager=True, lead=True)}</section>')

        # Phone only: every world one tap away, right under today's drop.
        tiles = ''.join(
            f'<a href="{self.cpath(k)}" style="--t:{WORLDS[k]}"><img src="{img(self.in_world(k)[0]["image"], 480)}" alt="" width="480" height="480" loading="lazy" decoding="async">'
            f'<b>{e(self.cat(k))}</b><small>{len(self.in_world(k))}</small></a>' for k in self.worlds)
        cats = f'<nav class="cats" id="cats" aria-label="{e(u["nav"][1])}"><h2 class="d">{e(u["nav"][1])}</h2><div>{tiles}</div></nav>'

        day = (f'<section class="day" id="hoy" style="--tint:{star["tint"]};--word:{ACCENT if star["dark"] else INK}" data-page="{star["tint"]}"><div class="day-pin"><div class="day-fill"></div>'
               f'<p class="eye day-eye"><b>★</b> {e(u["find_day"])} · {e(self.cat(star["world"]))}</p>'
               f'<div class="d day-word" aria-hidden="true">{e(star["name"])}</div>'
               f'<div class="day-prod"><img class="cut" src="{img(star["image"], 800)}" alt="{e(star["name"])}" width="800" height="800" loading="lazy" decoding="async"></div>'

               f'<div class="day-info"><h2 class="d">{e(star["name"])}</h2><p class="s">{e(" ".join(star["headline"]))}</p>'
               f'<p class="t">{e(star["description"])}</p><div class="row">{self.buy(star)}<a class="btn line" data-go href="{self.ppath(star)}">{e(u["more"])}</a></div></div>'
               f'</div></section>')

        bands = []
        total = len(self.worlds)
        for i, key in enumerate(self.worlds):
            group = self.in_world(key)
            minis = ''.join(
                f'<a class="mini" data-go href="{self.ppath(p)}"><img class="cut" src="{img(p["image"], 480)}" alt="{e(p["name"])}" width="480" height="480" loading="lazy" decoding="async"><b>{e(p["name"])}</b></a>'
                for p in [q for q in group if q not in drop][:8] or group[:8])
            bands.append(
                f'<section class="world"{" id=\"mundos\"" if i == 0 else ""} data-page="{WORLDS[key]}" style="--t:{WORLDS[key]}"><div class="rv">'
                f'<p class="eye">{e(u["world"])} {i + 1:02d} / {total:02d}</p><h2 class="d"><a href="{self.cpath(key)}">{e(self.cat(key))}</a></h2>'
                f'<p class="t">{e(self.copy(key))}</p>'
                f'<a class="btn line" href="{self.cpath(key)}">{e(u["enter"])} · {len(group)} <span aria-hidden="true">{self.fwd}</span></a></div>'
                f'<div class="strip rv">{minis}</div></section>')

        chips = (f'<button type="button" data-filter="*" aria-pressed="true">{e(u["filter_all"])}</button>'
                 + ''.join(f'<button type="button" data-filter="{slug(k)}" aria-pressed="false">{e(self.cat(k))}</button>' for k in self.worlds))
        everything = (f'<section class="all" id="todo" data-page="{PAPER}"><h2 class="d rv">{e(u["all"][0])} <span class="s">{len(items)}</span> {e(u["all"][1])}</h2>'
                      f'<div class="tools"><input class="find" id="find" type="search" inputmode="search" enterkeyhint="search" autocomplete="off" '
                      f'placeholder="{e(u["search"])}" aria-label="{e(u["tabs"][3])}"><div class="chips">{chips}</div></div>'
                      f'<p class="none" hidden>{e(u["nothing"])}</p><div class="grid">{"".join(self.card(p) for p in items)}</div></section>')

        listing = {'@type': 'ItemList', 'name': u['title'], 'numberOfItems': len(items),
                   'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': ORIGIN + self.ppath(p), 'name': p['name']} for i, p in enumerate(items)]}
        body = hero + cats + day + ''.join(bands) + everything
        paths = {l: L.catalog_path(l) for l in LANGS}
        if self.root:
            schema = {'@context': 'https://schema.org', '@graph': [
                {'@type': 'WebSite', 'name': 'FLUXIXO', 'url': ORIGIN + '/', 'inLanguage': 'en'},
                {'@type': 'Organization', 'name': 'FLUXIXO', 'url': ORIGIN + '/', 'logo': ORIGIN + '/apple-touch-icon.png'}, listing]}
            write('/', self.page(ROOT_TITLE, ROOT_DESC, '/', body, paths, schema, hreflang=False, tab='home'))
            return
        # Titles and descriptions stay exactly as search engines already know them.
        desc = (f'{len(items)} товаров из подборки FLUXIXO: студийные фотографии, описания, рубрики и партнёрские ссылки на AliExpress.'
                if self.lang == 'ru' else L.CATALOG_DESCRIPTION[self.lang])
        write(self.home(), self.page(L.CATALOG_TITLE[self.lang], desc, self.home(), body, paths, {'@context': 'https://schema.org', **listing}, tab='home'))

    def build_404(self):
        body = (f'<section class="c-hero"><p class="eye">404</p><h1 class="d">Page not found<span class="s">This link may have changed.</span></h1>'
                f'<div class="row" style="margin:30px 0 80px"><a class="btn" href="/">Back to the finds <span aria-hidden="true">→</span></a></div></section>')
        (OUT / '404.html').write_text(self.page('Page Not Found | FLUXIXO', 'The requested page was not found on FLUXIXO.', '/404.html', body, {},
                                                hreflang=False, noindex=True), encoding='utf-8', newline='\n')

    def build_products(self, siblings, metadata_by_product=None):
        u, n = self.ui, len(self.items)
        for i, p in enumerate(self.items):
            prev, nxt = self.items[i - 1], self.items[(i + 1) % n]
            key, path, name = p['world'], self.ppath(p), p['name']
            title, desc = (metadata_by_product[(self.lang, p['id'])] if metadata_by_product is not None
                           else product_metadata(name, p['description'], self.lang, p.get('sourceProductId')))
            page_description = p['description']
            if self.lang == 'ru' and p['id'] == 'import-0024':
                name, title = WATCH_SEO_RU['heading'], WATCH_SEO_RU['title']
                desc, page_description = WATCH_SEO_RU['description'], WATCH_SEO_RU['copy']
            crumbs = [(u['home'], self.home()), (self.cat(key), self.cpath(key)), (name, path)]
            schema = L.item_page_schema(ORIGIN, path, title, desc, p['image'], self.lang, L.STAGE_CAPTION[self.lang], crumbs)
            facts = ''.join(f'<li>{e(L.translate_fact(self.data, f["label"], self.lang))}: {e(L.translate_fact(self.data, f["value"], self.lang))}</li>'
                            for f in L.public_facts(p))
            crumb_html = ''.join(f'<li><a href="{href}">{e(label)}</a></li>' for label, href in crumbs[:-1])
            related = [q for q in self.in_world(key) if q['id'] != p['id']][:4]
            body = (f'<section class="p-hero{" dark" if p["dark"] else ""}">'
                    f'<ol class="crumbs" aria-label="{e(L.BREADCRUMB_ARIA[self.lang])}">{crumb_html}</ol><h1 class="d">{e(name)}</h1>'
                    f'<div class="p-body"><div class="p-text"><p class="s">{e(" ".join(p["headline"]))}</p><p class="t">{e(page_description)}</p>'
                    f'{"<ul class=facts>" + facts + "</ul>" if facts else ""}'
                    f'<div class="row">{self.buy(p, "data-main-cta")}</div><p class="note">{e(u["note"])} {e(L.DISCLOSURE[self.lang])}</p></div>'
                    f'{self.gallery(p, name)}</div></section>')
            if related:
                body += (f'<section class="related"><p class="eye"><b>●</b> {e(self.cat(key))}</p>'
                         f'<h2 class="d rv">{e(u["related"][0])} <span class="s">{e(u["related"][1])}</span></h2>{self.rope(related)}</section>')
            body += (f'<nav class="pn"><a data-go href="{self.ppath(prev)}"><img src="{img(prev["image"], 480)}" alt="" loading="lazy"><span><small>{self.back} {e(u["prev"])}</small><b>{e(prev["name"])}</b></span></a>'
                     f'<a data-go href="{self.ppath(nxt)}"><span><small>{e(u["next"])} {self.fwd}</small><b>{e(nxt["name"])}</b></span><img src="{img(nxt["image"], 480)}" alt="" loading="lazy"></a></nav>')
            alt = {l: L.product_path(p, l) for l in LANGS if p['id'] in siblings[l]}
            write(path, self.page(title, desc, path, body, alt, schema, p['image'], p['tint'], buy=p))

    def build_categories(self):
        u = self.ui
        for key in self.worlds:
            group, name, path = self.in_world(key), self.cat(key), self.cpath(key)
            chips = ''.join(f'<a href="{self.cpath(k)}"{" aria-current=\"page\"" if k == key else ""}>{e(self.cat(k))}</a>' for k in self.worlds)
            body = (f'<section class="c-hero"><ol class="crumbs"><li><a href="{self.home()}">{e(u["home"])}</a></li></ol>'
                    f'<h1 class="d">{e(name)}<span class="s">{e(u["count"](n=len(group)))}</span></h1><p class="t">{e(self.copy(key))}</p></section>'
                    f'<section class="c-body">{self.rope(group[:3], width=800) if len(group) >= 3 else ""}'
                    f'<div class="chips">{chips}</div><div class="grid">{"".join(self.card(p) for p in group)}</div></section>')
            title = L.CATEGORY_TITLE[self.lang].format(cat=name)
            desc = self.copy(key) + ' ' + L.CATEGORY_COUNT[self.lang].format(n=len(group))
            write(path, self.page(title, desc, path, body, {l: L.category_path(key, l) for l in LANGS}, colour=WORLDS[key], tab='cats'))

    def build_about(self):
        copy = L.ABOUT[self.lang]
        sections = ''.join(f'<section id="{a}"><h2>{e(h)}</h2><p>{e(t)}</p></section>' for a, h, t in copy['sections'])
        path = L.about_path(self.lang)
        write(path, self.page(copy['title'], copy['desc'], path, f'<article class="about"><h1 class="d">{e(copy["h1"])}</h1>{sections}</article>',
                              {l: L.about_path(l) for l in LANGS}))


def write(path, html):
    target = OUT / path.strip('/') / 'index.html' if path.strip('/') else OUT / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding='utf-8', newline='\n')


def link_assets():
    # A junction keeps the 38 MB of product images in one place instead of copying them.
    link = OUT / 'assets'
    if not link.exists():
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(DIST / 'assets')], check=True, capture_output=True)
    for name in ('favicon.ico', 'favicon-96x96.png', 'apple-touch-icon.png'):
        shutil.copy2(DIST / name, OUT / name)


def app_icons():
    """Home-screen icons, drawn from the same shape as assets/favicon.svg (64 x 64 units)."""
    from PIL import ImageDraw
    letter = [(20, 15), (49, 15), (49, 23), (29, 23), (29, 31), (46, 31), (46, 39), (29, 39), (29, 53), (20, 53)]
    for name, size, rounded in (('icon-192.png', 192, True), ('icon-512.png', 512, True), ('icon-maskable-512.png', 512, False)):
        k = size * 4 / 64
        big = Image.new('RGBA', (size * 4, size * 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(big)
        if rounded:
            draw.rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1), radius=14 * k, fill='#162d57')
        else:
            draw.rectangle((0, 0, size * 4, size * 4), fill='#162d57')
        draw.polygon([(x * k, y * k) for x, y in letter], fill='#f6f1e8')
        big.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)


def app_manifest(site):
    """Lets a phone add the storefront to its home screen and open it without browser chrome, in the visitor's language."""
    manifest = {
        'name': f'FLUXIXO · {site.ui["app"]}', 'short_name': 'FLUXIXO', 'lang': L.LANGUAGES[site.lang][0],
        'dir': 'rtl' if site.rtl else 'ltr', 'start_url': site.home(), 'scope': '/', 'display': 'standalone',
        'background_color': PAPER, 'theme_color': PAPER,
        'icons': [{'src': '/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
                  {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
                  {'src': '/icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}],
    }
    (OUT / site.manifest_name()).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')

def proofread():
    """Mechanical proofreading of every product and interface text. A preview build stops on a problem;
    the daily production build reports it as a warning so that one odd word never blocks new products."""
    import check_texts
    problems = check_texts.run()
    for lang, strings in UI.items():
        for key, text in strings.items():
            for part in (text if isinstance(text, tuple) else (text,)):
                if isinstance(part, str) and part:
                    check_texts.check_string(part, lang, f'interface/{lang}/{key}', problems)
    if problems and not PROD:
        sys.exit('Text problems, build stopped:\n' + '\n'.join(problems))
    for problem in problems:
        print(f'::warning title=Text needs proofreading::{problem}')


def main():
    proofread()
    products, data = load()
    if not PROD:
        if OUT.exists():
            for child in OUT.iterdir():
                if child.name != 'assets':
                    shutil.rmtree(child) if child.is_dir() else child.unlink()
        OUT.mkdir(exist_ok=True)
        link_assets()
    (OUT / 'js').mkdir(exist_ok=True)
    shutil.copyfile(HERE / 'static/app.js', OUT / 'js/fx.js')
    sites = {lang: Site(products, data, lang) for lang in LANGS}
    siblings = {lang: {p['id'] for p in s.items} for lang, s in sites.items()}
    metadata_by_product = assign_product_metadata({lang: site.items for lang, site in sites.items()})
    for lang, site in sites.items():
        site.build_home()
        site.build_products(siblings, metadata_by_product)
        site.build_categories()
        site.build_about()
        app_manifest(site)
        print(f'{lang}: {len(site.items)} products, {len(site.worlds)} worlds')
    root = Site(products, data, 'en', root=True)
    root.build_home()
    app_manifest(root)
    app_icons()
    sites['en'].build_404()
    print(f'Storefront written to {OUT}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
