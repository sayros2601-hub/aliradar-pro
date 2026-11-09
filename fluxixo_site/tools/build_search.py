"""Rebuild crawlable FLUXIXO pages, category SEO hubs, RSS/Pinterest feeds, and sitemap."""
from pathlib import Path
from html import escape
from locales import (
    ABOUT, BREADCRUMB_ARIA, CATALOG_TITLE, CATEGORY_TITLE, IMAGE_SIZES, LANGUAGES, OFFERS, DISCLOSURE, STAGE_CAPTION, about_path, alternates, offer_block,
    card_image, catalog_path, category_key, category_paths, fit_description, fit_title, generate, generate_about,
    header_lang_select, hero_image, item_page_schema, language_links, product_path, public_facts, sticky_cta, sync_showroom, thumb,
    translations
)
from PIL import Image
import csv
import hashlib
import io
import json
import re
import secrets
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
ORIGIN = 'https://www.fluxixo.shop'
GOOGLE = 'BUSamFSGELSfaWQEaVVj2QzUgKQvWovtg-ZaHCfKNb0'
BING = '49287D3DFF71EA9430905E14A0A426F2'
YANDEX = 'deee62492f76cf5b'
# Inlined because the render-blocking stylesheet cost about 900 ms on mobile.
INLINE_CSS = re.sub(r'\s*\n\s*', ' ', re.sub(r'/\*.*?\*/', '', (DIST/'css/search.css').read_text(encoding='utf-8'), flags=re.S)).strip().replace('</', '<\\/')
catalog = json.loads((DIST/'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
products = [p for p in catalog['products'] if not p['demo']]
e = escape
i18n = json.loads((ROOT/'tools/i18n_data.json').read_text(encoding='utf-8'))
sync_showroom(DIST, i18n)
first_product = catalog['products'][0]
default_image = first_product['image']

# Clean up obsolete category folder if present
obsolete_cat = DIST / 'categories' / 'raznoe'
if obsolete_cat.exists():
    shutil.rmtree(obsolete_cat, ignore_errors=True)

CAT_SLUGS = {
    'Техника': ('tehnika', 'Гаджеты, электроника и умные аксессуары для дома и работы'),
    'Дом': ('dom', 'Практичные приборы, освещение и полезные находки для уюта и порядка дома'),
    'Кухня': ('kuhnya', 'Кухонные гаджеты, приборы для готовки, вакууматоры и аксессуары для напитков'),
    'В дороге': ('v-doroge', 'Автомобильные аксессуары, дорожные гаджеты и снаряжение для поездок'),
    'Инструменты': ('instrumenty', 'Лазерные дальномеры, паяльники, детекторы и компактный электроинструмент'),
    'Уход': ('uhod', 'Приборы для ухода за собой, стерилизаторы, стайлеры и массажёры'),
    'Спорт': ('sport', 'Спортивные тренажёры, велоаксессуары и инвентарь для домашних тренировок'),
    'На природе': ('na-prirode', 'Снаряжение для кемпинга, рыбалки, походов и активного отдыха'),
    'Питомцы': ('pitomcy', 'Автоматические игрушки, трекеры и аксессуары для собак и кошек'),
    'Для питомцев': ('pitomcy', 'Автоматические игрушки, трекеры и аксессуары для собак и кошек'),
}

def cat_slug(cat_name):
    return CAT_SLUGS.get(cat_name, ('raznoe', 'Интересные находки и аксессуары с AliExpress'))[0]

def cat_desc(cat_name):
    return CAT_SLUGS.get(cat_name, ('raznoe', 'Интересные находки и аксессуары с AliExpress'))[1]

def write(path, text):
    dest = DIST/path
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Fixed line endings keep content hashes, and so sitemap lastmod, equal between Windows and CI builds.
    dest.write_text(text, encoding='utf-8', newline='\n')

def make_thumbnails():
    for p in products:
        source = DIST/p['image']
        if not source.exists():
            continue
        with Image.open(source) as picture:
            IMAGE_SIZES[p['image']] = picture.size
        for width in (480, 800):
            relative = thumb(p['image'], width)
            target = DIST/relative
            # A zero-byte file is the leftover of an interrupted run, so it is rebuilt.
            if not (target.exists() and target.stat().st_size):
                target.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(source) as picture:
                    picture.thumbnail((width, width), Image.Resampling.LANCZOS)
                    picture.save(target, 'WEBP', quality=82, method=4)
            with Image.open(target) as picture:
                IMAGE_SIZES[relative] = picture.size

make_thumbnails()

offers_file = ROOT/'tools/offers.json'
if offers_file.exists():
    try:
        OFFERS.update(json.loads(offers_file.read_text(encoding='utf-8')))
    except ValueError:
        pass  # a damaged file means pages are built without prices

def route(p):
    return '/products/' + p['id'] + '/'

def cat_route(slug):
    return f'/categories/{slug}/'

def structured(data):
    return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'

def metadata(title, description, path, image=default_image, language="ru"):
    rss = f'<link rel="alternate" type="application/rss+xml" title="FLUXIXO — Новые находки с AliExpress" href="{ORIGIN}/rss.xml">\n' if language == 'ru' else ''
    return f"""<meta name="theme-color" content="#100f26">
<link rel="canonical" href="{ORIGIN}{path}">
{rss}<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:site_name" content="FLUXIXO">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{ORIGIN}{path}"><meta property="og:image" content="{ORIGIN}/{e(image)}">
<meta property="og:locale" content="{LANGUAGES[language][1]}"><meta name="twitter:card" content="summary_large_image">"""

def page(title, description, path, body, data=None, image=default_image, noindex=False, language='ru', alternate_paths=None, studio_url=None, theme=None):
    tag, _, _, catalog_label, showroom, _, _ = LANGUAGES[language]
    direction = 'rtl' if language == 'he' else 'ltr'
    home = studio_url or f'/?lang={language}'
    catalog_url = catalog_path(language)
    disclosure = DISCLOSURE.get(language, DISCLOSURE['ru'])
    meta = metadata(title, description, path, image, language)
    if alternate_paths:
        meta += '\n' + alternates(ORIGIN, alternate_paths)
    if noindex:
        meta = meta.replace('index,follow,max-image-preview:large', 'noindex,follow')
    lang_dropdown = header_lang_select(language, alternate_paths)
    theme_attr = f' data-theme="{theme}"' if theme else ''
    rss_link = '<span>·</span><a href="/rss.xml">RSS</a>' if language == 'ru' else ''
    return f"""<!doctype html>
<html lang="{tag}" dir="{direction}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description)}"><meta http-equiv="content-language" content="{tag}">{meta}
<link rel="icon" href="/assets/favicon.svg?v=mira213-fluxixo-20261030"><link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><style>{INLINE_CSS}</style>
<script defer src="/js/search-nav.js?v=mira213-fluxixo-20261030"></script>
{structured(data) if data else ''}</head><body{theme_attr}>
<header><a class="brand" href="/?lang={language}">FLUXIXO</a><nav>{lang_dropdown}<a class="nav-pill" href="{catalog_url}">{e(catalog_label)}</a><a class="nav-pill showroom-pill" href="{home}">{e(showroom)}</a></nav></header>
<main>{body}</main><footer><p>{e(disclosure)}</p><div class="footer-links"><a href="{catalog_url}">{e(catalog_label)}</a><span>·</span><a href="{home}">{e(showroom)}</a><span>·</span><a href="{about_path(language)}">{e(ABOUT[language]['nav'])}</a>{rss_link}</div></footer></body></html>"""

# Group products by category slug
by_cat = {}
cat_titles = {}
for p in products:
    slug = cat_slug(p['category'])
    by_cat.setdefault(slug, []).append(p)
    if slug not in cat_titles:
        cat_titles[slug] = 'Питомцы' if slug == 'pitomcy' else p['category']

items = []
for idx, p in enumerate(products):
    path = route(p)
    slug = cat_slug(p['category'])
    c_path = cat_route(slug)
    title = fit_title(p['name'], 'ru')
    seo_desc = fit_description(p['description'], 'ru')
    items.append(
        f'<li><a class="card" href="{path}">'
        f'<div class="card-visual">{card_image(p["image"], p["name"], idx)}</div>'
        f'<p class="eyebrow">{e(p["category"])}</p><h2>{e(p["name"])}</h2><p>{e(p["description"])}</p></a></li>'
    )
    facts = ''.join(f'<dt>{e(f["label"])}</dt><dd>{e(f["value"])}</dd>' for f in public_facts(p))
    facts_block = f'<dl class="specs-grid">{facts}</dl>' if facts else ''
    source = (
        f'<details class="source-details"><summary>Посмотреть исходное фото продавца</summary>'
        f'<img src="/{e(p["original"])}" alt="Исходное фото: {e(p["name"])}" loading="lazy" width="460" height="420">'
        f'<p>Сравните студийную визуализацию с исходным фото. Актуальный вариант и комплектацию уточняйте у продавца.</p></details>'
        if p.get('original') else ''
    )

    same_cat = [other for other in by_cat.get(slug, []) if other['id'] != p['id']]
    if len(same_cat) < 4:
        others = [other for other in products if other['id'] != p['id'] and other not in same_cat]
        same_cat.extend(others[:4 - len(same_cat)])
    rel_cards = ''.join(
        f'<li><a class="card" href="{route(r)}">'
        f'<div class="card-visual">{card_image(r["image"], r["name"], width=300, height=225)}</div>'
        f'<p class="eyebrow">{e(r["category"])}</p><h3>{e(r["name"])}</h3><p>{e(r["description"])}</p></a></li>'
        for r in same_cat[:4]
    )
    related_section = f'<section class="related"><h2>Ещё в категории «<a href="{c_path}">{e(cat_titles[slug])}</a>»</h2><ul class="grid">{rel_cards}</ul></section>'
    headline_ru = ' '.join(p.get('headline', []))
    studio_ru = f"/?lang=ru#{e(p['id'])}"
    cta_ru = (
        f'<a class="button" href="{e(p["affiliateUrl"])}" target="_blank" rel="sponsored noopener"><span>Посмотреть на AliExpress</span><span aria-hidden="true">↗</span></a>'
        if p.get('affiliateUrl') and not p.get('pendingLink')
        else '<p class="muted">Ссылка на продавца уточняется.</p>'
    )
    body = f"""<nav class="breadcrumb" aria-label="Навигационная цепочка"><a href="/?lang=ru">FLUXIXO</a><span class="breadcrumb-sep">/</span><a href="/catalog/">Каталог</a><span class="breadcrumb-sep">/</span><a href="{c_path}">{e(cat_titles[slug])}</a></nav>
<article><div class="product"><figure class="arcade-stage-card">{hero_image(p['image'], p['name'])}<div class="stage-podium-bar" aria-hidden="true"></div><figcaption>{e(STAGE_CAPTION['ru'])}</figcaption></figure><section><p class="eyebrow"><a href="{c_path}">{e(p['category'])}</a></p><h1>{e(p['name'])}</h1><p class="product-headline-sub">{e(headline_ru)}</p><p>{e(p['description'])}</p>{offer_block(p['id'], 'ru')}<div class="cta-row">{cta_ru}<a class="button secondary" href="{studio_ru}">Открыть в 3D-витрине</a></div><p class="affiliate-disclosure">Партнёрская ссылка. FLUXIXO может получить комиссию за покупку. Покупка оформляется на AliExpress.</p>{facts_block}</section></div>{source}{related_section}</article>"""
    # Product/Offer markup appears only with a price read from the official API and shown on the page; never invented.
    data = item_page_schema(ORIGIN, path, title, seo_desc, p['image'], 'ru', f"{p['name']} — {p['description']}", [
        ('FLUXIXO', '/'), ('Каталог', '/catalog/'), (cat_titles[slug], c_path), (p['name'], path)
    ], product=(p['id'], p['name'], p['description'], p.get('affiliateUrl')))
    variant_paths = {language: product_path(p, language) for language in ('ru', *translations(i18n, p))}
    body += language_links(variant_paths) + sticky_cta(cta_ru)
    write(path.strip('/')+'/index.html', page(title, seo_desc, path, body, data, p['image'], alternate_paths=variant_paths, studio_url=studio_ru, theme=p.get('theme')))

# Build category hub pages (/categories/<slug>/index.html)
cat_nav_links = []
cat_paths = []
for slug, c_prods in by_cat.items():
    c_name = cat_titles[slug]
    c_path = cat_route(slug)
    cat_paths.append(c_path)
    cat_nav_links.append(f'<a class="button secondary" href="{c_path}">{e(c_name)} ({len(c_prods)})</a>')

cat_bar = '<div class="cat-links">' + ''.join(cat_nav_links) + '</div>'

for slug, c_prods in by_cat.items():
    c_name = cat_titles[slug]
    c_path = cat_route(slug)
    c_cards = ''.join(
        f'<li><a class="card" href="{route(cp)}">'
        f'<div class="card-visual">{card_image(cp["image"], cp["name"], c_idx)}</div>'
        f'<p class="eyebrow">{e(cp["category"])}</p><h2>{e(cp["name"])}</h2><p>{e(cp["description"])}</p></a></li>'
        for c_idx, cp in enumerate(c_prods)
    )
    c_title = CATEGORY_TITLE['ru'].format(cat=c_name)
    c_desc = f"{cat_desc(c_name)}. {len(c_prods)} находок с фото и ссылками на AliExpress."
    c_listing = {
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        'name': f'Категория {c_name} — FLUXIXO',
        'numberOfItems': len(c_prods),
        'itemListElement': [{'@type': 'ListItem', 'position': i+1, 'url': ORIGIN+route(cp), 'name': cp['name']} for i, cp in enumerate(c_prods)]
    }
    c_key = category_key(c_name)
    c_alternates = category_paths(c_key) if c_key else None
    c_locale_bar = language_links(c_alternates) if c_alternates else ''
    c_body = f"""<nav class="breadcrumb" aria-label="{e(BREADCRUMB_ARIA['ru'])}"><a href="/?lang=ru">FLUXIXO</a><span class="breadcrumb-sep">/</span><a href="/catalog/">Каталог</a><span class="breadcrumb-sep">/</span><span>{e(c_name)}</span></nav>
<p class="eyebrow">Рубрика каталога</p><h1>{e(c_name)} ({len(c_prods)})</h1><p>{e(c_desc)}</p>{cat_bar}<ul class="grid">{c_cards}</ul>{c_locale_bar}"""
    write(c_path.strip('/')+'/index.html', page(c_title, c_desc, c_path, c_body, c_listing, c_prods[0]['image'], alternate_paths=c_alternates))

catalog_paths = {language: catalog_path(language) for language in LANGUAGES}
lang_bar = language_links(catalog_paths)

listing = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': 'Каталог FLUXIXO', 'numberOfItems': len(products), 'itemListElement': [{'@type': 'ListItem', 'position': i+1, 'url': ORIGIN+route(p), 'name': p['name']} for i, p in enumerate(products)]}
write('catalog/index.html', page(CATALOG_TITLE['ru'], f'{len(products)} товаров из подборки FLUXIXO: студийные фотографии, описания, рубрики и партнёрские ссылки на AliExpress.', '/catalog/', '<p class="eyebrow">Находки с другой стороны</p><h1>Коллекция FLUXIXO ('+str(len(products))+')</h1><p>Техника, инструменты, товары для дома, кухни, поездок и питомцев. Выберите язык, рубрику или рассмотрите все находки ниже.</p>'+cat_bar+'<ul class="grid">'+''.join(items)+'</ul>'+lang_bar, listing, alternate_paths=catalog_paths))

localized_paths = generate(ORIGIN, i18n, products, page, write, default_image) + generate_about(page, write)

index = (DIST/'index.html').read_text(encoding='utf-8')
title = 'FLUXIXO | Curated AliExpress Finds'
description = 'Explore gadgets, home and kitchen tools, and travel accessories in the interactive FLUXIXO showroom. Compare studio images with original seller photos.'
meta = metadata(title, description, '/', default_image, 'en')
# The showroom is not a translation of any catalog page, so it stays outside the hreflang clusters.
stage_small = thumb(default_image, 800)
# Phones and tablets get the 800px copy, matching the breakpoint app.js uses for the stage image.
meta += f'\n<link rel="preload" as="image" href="/{e(stage_small)}" media="(max-width: 1100px)" fetchpriority="high"><link rel="preload" as="image" href="/{e(default_image)}" media="(min-width: 1101px)" fetchpriority="high"><link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">'
meta += f'\n<meta name="google-site-verification" content="{GOOGLE}"><meta name="msvalidate.01" content="{BING}"><meta name="yandex-verification" content="{YANDEX}">'
meta += structured({'@context': 'https://schema.org', '@graph': [
    {'@type': 'WebSite', 'name': 'FLUXIXO', 'url': ORIGIN+'/', 'inLanguage': 'en'},
    {'@type': 'Organization', 'name': 'FLUXIXO', 'url': ORIGIN+'/', 'logo': ORIGIN+'/apple-touch-icon.png'}
]})
block = '<!-- SEARCH START -->\n'+meta+'\n<!-- SEARCH END -->'
if '<!-- SEARCH START -->' in index:
    index = re.sub(r'<!-- SEARCH START -->.*?<!-- SEARCH END -->', lambda _: block, index, flags=re.S)
else:
    index = index.replace('</head>', block+'\n</head>')
index = re.sub(r'<title>.*?</title>', lambda _: f'<title>{e(title)}</title>', index, count=1)
index = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{e(description)}">', index, count=1)
first_p = dict(first_product)
first_p.update(translations(i18n, first_product).get('en', {}))
first_p['category'] = i18n['cats'].get(first_product['category'], {}).get('en', first_product['category'])
h1_spans = ' '.join(
    f'<span>{e(line[:-1])}<span class="accent-dot">.</span></span>' if line.endswith('.') else f'<span>{e(line)}</span>'
    for line in first_p['headline']
)
index = re.sub(r'<h1 id="product-heading">.*?</h1>', lambda _: f'<h1 id="product-heading">{h1_spans}</h1>', index, flags=re.S)
index = re.sub(r'<h2 id="product-name">.*?</h2>', lambda _: f'<h2 id="product-name">{e(first_p["name"])}</h2>', index, flags=re.S)
index = re.sub(r'<p id="product-description">.*?</p>', lambda _: f'<p id="product-description">{e(first_p["description"])}</p>', index, flags=re.S)
index = re.sub(r'<span id="product-category">.*?</span>', lambda _: f'<span id="product-category">{e(first_p["category"])}</span>', index)
index = re.sub(r'<span id="object-category">.*?</span>', lambda _: f'<span id="object-category">{e(first_p["category"])}</span>', index)
index = re.sub(r'<span id="collection-count">.*?</span>', lambda _: f'<span id="collection-count">{len(products):02d}</span>', index)
index = re.sub(r'<span id="large-total">.*?</span>', lambda _: f'<span id="large-total">{len(products):02d}</span>', index)
# The first product is in the markup itself, so it can paint before the scripts finish loading.
index = re.sub(r'<div class="product-plane"><img [^>]*fetchpriority="high"[^>]*>',
               lambda _: f'<div class="product-plane"><img src="{e(stage_small)}" alt="{e(first_p["name"])}" draggable="false" decoding="async" fetchpriority="high">',
               index, count=1)
write('index.html', index)

write('404.html', page('Page Not Found | FLUXIXO', 'The requested page was not found on FLUXIXO.', '/404.html', '<p class="eyebrow">404</p><h1>Page not found</h1><p>This link may have changed. Explore the full interactive showroom or browse the catalog below.</p><div class="cta-row"><a class="button" href="/">Open 3D Showroom</a><a class="button secondary" href="/en/">Browse Catalog</a></div>', noindex=True, language='en'))
# Yandex serves the Russian audience only; Google and Bing handle Mexico, Brazil and the other locales.
robots_txt = f"""User-agent: *
Allow: /

User-agent: Yandex
Allow: /
Disallow: /en/
Disallow: /pt/
Disallow: /es/
Disallow: /fr/
Disallow: /he/
Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term
Clean-param: lang /

Sitemap: {ORIGIN}/sitemap.xml
Sitemap: {ORIGIN}/sitemap-ru.xml
"""
write('robots.txt', robots_txt)
write('BingSiteAuth.xml', f'<?xml version="1.0" encoding="UTF-8"?>\n<users><user>{BING}</user></users>\n')
keyfile = ROOT/'tools/indexnow-key.txt'
if not keyfile.exists():
    keyfile.write_text(secrets.token_hex(16), encoding='utf-8')
key = keyfile.read_text().strip()
write(key+'.txt', key)
write('indexnow.txt', key)
write('indexnow-key.txt', key)

# Generate RSS 2.0 feed (/rss.xml)
now_dt = datetime.now(timezone.utc)
rss_items = []
for p in products[:40]:
    p_url = f"{ORIGIN}{route(p)}?utm_source=rss&utm_medium=organic"
    img_url = f"{ORIGIN}/{p['image']}"
    rss_items.append(f"""    <item>
      <title>{e(p['name'])} — {e(p['category'])}</title>
      <link>{e(p_url)}</link>
      <guid isPermaLink="true">{ORIGIN}{route(p)}</guid>
      <pubDate>{format_datetime(now_dt)}</pubDate>
      <description>{e(p['description'])}</description>
      <enclosure url="{e(img_url)}" type="image/webp" length="65000"/>
    </item>""")
rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>FLUXIXO — Находки с другой стороны</title>
    <link>{ORIGIN}/</link>
    <description>Ежедневно пополняемая коллекция полезных находок с AliExpress</description>
    <language>ru</language>
    <lastBuildDate>{format_datetime(now_dt)}</lastBuildDate>
{chr(10).join(rss_items)}
  </channel>
</rss>
"""
write('rss.xml', rss_xml)

# Generate Pinterest Bulk Create CSV (/pinterest-feed.csv) & Social feed (/social-feed.json)
csv_buf = io.StringIO()
writer = csv.writer(csv_buf)
writer.writerow(['Title', 'Media URL', 'Pinterest board', 'Thumbnail', 'Description', 'Link', 'Publish date', 'Keywords'])
social_posts = []
for p in products:
    p_link = f"{ORIGIN}{route(p)}?utm_source=pinterest&utm_medium=organic"
    img_url = f"{ORIGIN}/{p['image']}"
    writer.writerow([
        f"{p['name']} | Находки FLUXIXO",
        img_url,
        f"FLUXIXO — {p['category']}",
        '',
        f"{p['description']} Смотрите студийный 3D-обзор и сравнение с фото продавца на FLUXIXO.",
        p_link,
        '',
        f"AliExpress, {p['category']}, {p['name']}, находки для дома, гаджеты"
    ])
    social_posts.append({
        'id': p['id'],
        'title': p['name'],
        'category': p['category'],
        'text': f"✨ {p['name']} ({p['category']})\n\n{p['description']}\n\n👉 3D-витрина и обзор: {ORIGIN}{route(p)}?utm_source=social&utm_medium=organic\n🛒 Карточка AliExpress: {p['affiliateUrl']}",
        'image_url': img_url,
        'page_url': f"{ORIGIN}{route(p)}",
        'affiliate_url': p['affiliateUrl']
    })
write('pinterest-feed.csv', csv_buf.getvalue())
write('social-feed.json', json.dumps(social_posts, ensure_ascii=False, indent=2))

statefile = ROOT/'tools/search-build-state.json'
previous = json.loads(statefile.read_text()) if statefile.exists() else {}
state = {}
ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('', ns)
sitemap = ET.Element('{'+ns+'}urlset')
sitemap_ru = ET.Element('{'+ns+'}urlset')
all_routes = ['/', '/catalog/'] + localized_paths + sorted(cat_paths) + [route(p) for p in products]
for path in all_routes:
    file = DIST/(path.strip('/')+'/index.html' if path != '/' else 'index.html')
    digest = hashlib.sha256(file.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    old = previous.get(path, {})
    changed = old.get('lastmod') if old.get('sha256') == digest else datetime.now(timezone.utc).isoformat(timespec='seconds')
    state[path] = {'sha256': digest, 'lastmod': changed}
    for target in (sitemap, sitemap_ru) if not re.match(r'/(en|pt|es|fr|he)/', path) else (sitemap,):
        url = ET.SubElement(target, '{'+ns+'}url')
        ET.SubElement(url, '{'+ns+'}loc').text = ORIGIN+path
        ET.SubElement(url, '{'+ns+'}lastmod').text = changed
ET.indent(sitemap)
ET.indent(sitemap_ru)
write('sitemap.xml', ET.tostring(sitemap, encoding='unicode', xml_declaration=True)+'\n')
write('sitemap-ru.xml', ET.tostring(sitemap_ru, encoding='unicode', xml_declaration=True)+'\n')
statefile.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(f'Built {len(products)} product pages, {len(cat_paths)} category hubs, catalog, rss.xml, pinterest-feed.csv, sitemap ({len(state)} URLs), robots, verification and IndexNow files.')
