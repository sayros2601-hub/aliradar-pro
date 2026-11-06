"""Rebuild crawlable FLUXIXO pages, category SEO hubs, RSS/Pinterest feeds, and sitemap."""
from pathlib import Path
from html import escape
from locales import LANGUAGES, DISCLOSURE, alternates, catalog_path, generate, language_links, product_path, sync_showroom, translations
import csv
import hashlib
import io
import json
import re
import secrets
from datetime import datetime, timezone
from email.utils import format_datetime
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
ORIGIN = 'https://www.fluxixo.shop'
GOOGLE = 'BUSamFSGELSfaWQEaVVj2QzUgKQvWovtg-ZaHCfKNb0'
BING = '49287D3DFF71EA9430905E14A0A426F2'
catalog = json.loads((DIST/'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
products = [p for p in catalog['products'] if not p['demo']]
e = escape
i18n = json.loads((ROOT/'tools/i18n_data.json').read_text(encoding='utf-8'))
sync_showroom(DIST, i18n)
first_product = catalog['products'][0]
default_image = first_product['image']

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
    dest.write_text(text, encoding='utf-8')

def route(p):
    return '/products/' + p['id'] + '/'

def cat_route(slug):
    return f'/categories/{slug}/'

def structured(data):
    return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'

def metadata(title, description, path, image=default_image, language="ru"):
    return f'''<link rel="canonical" href="{ORIGIN}{path}">
<link rel="alternate" type="application/rss+xml" title="FLUXIXO — Новые находки с AliExpress" href="{ORIGIN}/rss.xml">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:site_name" content="FLUXIXO">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{ORIGIN}{path}"><meta property="og:image" content="{ORIGIN}/{e(image)}">
<meta property="og:locale" content="{LANGUAGES[language][1]}"><meta name="twitter:card" content="summary_large_image">'''

def page(title, description, path, body, data=None, image=default_image, noindex=False, language='ru', alternate_paths=None):
    tag, _, _, catalog_label, showroom, _, _ = LANGUAGES[language]
    direction = 'rtl' if language == 'he' else 'ltr'
    home = f'/?lang={language}'
    catalog_url = catalog_path(language)
    disclosure = DISCLOSURE.get(language, 'По партнёрским ссылкам FLUXIXO может получить комиссию. Цены, наличие и доставку уточняйте у продавца на AliExpress.')
    meta=metadata(title, description, path, image, language)
    if alternate_paths:
        meta += '\n' + alternates(ORIGIN, alternate_paths)
    if noindex: meta=meta.replace('index,follow,max-image-preview:large','noindex,follow')
    return f'''<!doctype html>
<html lang="{tag}" dir="{direction}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description)}">{meta}
<link rel="icon" href="/assets/favicon.svg?v=mira213-fluxixo-20261030"><link rel="stylesheet" href="/css/search.css?v=mira213-fluxixo-20261030">
{structured(data) if data else ''}</head><body>
<header><a class="brand" href="{home}">FLUXIXO</a><nav><a href="{catalog_url}">{e(catalog_label)}</a><a href="{home}">{e(showroom)}</a></nav></header>
<main>{body}</main><footer><p>{e(disclosure)}</p><a href="{catalog_url}">{e(catalog_label)}</a> · <a href="/rss.xml">RSS</a></footer></body></html>'''

# Group products by category slug
by_cat = {}
cat_titles = {}
for p in products:
    slug = cat_slug(p['category'])
    by_cat.setdefault(slug, []).append(p)
    if slug not in cat_titles:
        cat_titles[slug] = 'Питомцы' if slug == 'pitomcy' else p['category']

items=[]
for idx, p in enumerate(products):
    path=route(p)
    slug=cat_slug(p['category'])
    c_path=cat_route(slug)
    title=f"{p['name']} ({p['category']}) — обзор, фото и ссылка на AliExpress | FLUXIXO"
    seo_desc=f"{p['name']}: {p['description']} Сравните студийную визуализацию с реальным фото продавца и откройте карточку на AliExpress."
    items.append(f'<li><a class="card" href="{path}"><img src="/{e(p["image"])}" alt="{e(p["name"])}" loading="lazy" width="400" height="300"><p class="eyebrow">{e(p["category"])}</p><h2>{e(p["name"])}</h2><p>{e(p["description"])}</p></a></li>')
    facts=''.join(f'<dt>{e(f["label"])}</dt><dd>{e(f["value"])}</dd>' for f in p['facts'])
    source=f'<section class="source"><h2>Исходное фото товара</h2><img src="/{e(p["original"])}" alt="Исходное фото: {e(p["name"])}" loading="lazy"><p>Сравните визуализацию с исходным фото. Актуальный вариант и комплектацию уточняйте у продавца.</p></section>' if p.get('original') else ''
    
    # Related products in same category (up to 4) for strong internal SEO linking
    same_cat = [other for other in by_cat.get(slug, []) if other['id'] != p['id']]
    if len(same_cat) < 4:
        others = [other for other in products if other['id'] != p['id'] and other not in same_cat]
        same_cat.extend(others[:4 - len(same_cat)])
    rel_cards = ''.join(
        f'<li><a class="card" href="{route(r)}"><img src="/{e(r["image"])}" alt="{e(r["name"])}" loading="lazy" width="300" height="225"><p class="eyebrow">{e(r["category"])}</p><h3>{e(r["name"])}</h3><p>{e(r["description"])}</p></a></li>'
        for r in same_cat[:4]
    )
    related_section = f'<section class="related"><h2>Ещё в категории «<a href="{c_path}">{e(cat_titles[slug])}</a>»</h2><ul class="grid">{rel_cards}</ul></section>'

    body=f'''<nav class="breadcrumb" aria-label="Навигационная цепочка"><a href="/">FLUXIXO</a> / <a href="/catalog/">Каталог</a> / <a href="{c_path}">{e(cat_titles[slug])}</a></nav>
<article><div class="product"><figure><img class="hero-image" src="/{e(p['image'])}" alt="{e(p['name'])}" width="600" height="600"><figcaption>{e(p.get('imageNote',''))}</figcaption></figure><section><p class="eyebrow"><a href="{c_path}">{e(p['category'])}</a></p><h1>{e(p['name'])}</h1><p>{e(p['description'])}</p><a class="button" href="{e(p['affiliateUrl'])}" target="_blank" rel="sponsored noopener">Посмотреть на AliExpress ↗</a><a class="button secondary" href="/#{e(p['id'])}">Открыть в 3D-витрине</a><p class="muted">Партнёрская ссылка. FLUXIXO может получить комиссию за покупку. Покупка оформляется на AliExpress.</p><dl>{facts}</dl></section></div><section><h2>О товаре</h2><p class="detail-text">{e(p['details'])}</p></section>{source}{related_section}</article>'''
    body = body.replace('href="/#', 'href="/?lang=ru#')
    if p.get('pendingLink'):
        body=re.sub(r'<a class="button" href="".*?</a>', '<p class="muted">Ссылка на продавца уточняется.</p>', body)
    data={
        '@context':'https://schema.org',
        '@graph':[
            {
                '@type':'WebPage',
                '@id':ORIGIN+path,
                'url':ORIGIN+path,
                'name':title,
                'description':seo_desc,
                'inLanguage':'ru',
                'primaryImageOfPage':{
                    '@type':'ImageObject',
                    'url':ORIGIN+'/'+p['image'],
                    'contentUrl':ORIGIN+'/'+p['image'],
                    'width':1254,
                    'height':1254,
                    'caption':f"{p['name']} — {p['description']}"
                }
            },
            {
                '@type':'BreadcrumbList',
                'itemListElement':[
                    {'@type':'ListItem','position':1,'name':'FLUXIXO','item':ORIGIN+'/'},
                    {'@type':'ListItem','position':2,'name':'Каталог','item':ORIGIN+'/catalog/'},
                    {'@type':'ListItem','position':3,'name':cat_titles[slug],'item':ORIGIN+c_path},
                    {'@type':'ListItem','position':4,'name':p['name'],'item':ORIGIN+path}
                ]
            },
            {
                '@type':'FAQPage',
                'mainEntity':[
                    {
                        '@type':'Question',
                        'name':f"Для чего подходит {p['name'].lower()}?",
                        'acceptedAnswer':{'@type':'Answer','text':p['description']}
                    },
                    {
                        '@type':'Question',
                        'name':f"Где уточнить цену, доставку и комплектацию товара «{p['name']}»?",
                        'acceptedAnswer':{'@type':'Answer','text':'Актуальная стоимость, выбор модификации, условия доставки и возврата указаны напрямую на странице продавца на AliExpress по кнопке в карточке.'}
                    }
                ]
            }
        ]
    }
    variant_paths = {language: product_path(p, language) for language in ('ru', *translations(i18n, p))}
    body += language_links(variant_paths)
    data['@graph'] = [entry for entry in data['@graph'] if entry['@type'] != 'FAQPage']
    write(path.strip('/')+'/index.html',page(title,seo_desc,path,body,data,p['image'], alternate_paths=variant_paths))

# Build category hub pages (/categories/<slug>/index.html)
cat_nav_links = []
cat_paths = []
for slug, c_prods in by_cat.items():
    c_name = cat_titles[slug]
    c_path = cat_route(slug)
    cat_paths.append(c_path)
    cat_nav_links.append(f'<a class="button secondary" href="{c_path}">{e(c_name)} ({len(c_prods)})</a>')
    c_cards = ''.join(
        f'<li><a class="card" href="{route(cp)}"><img src="/{e(cp["image"])}" alt="{e(cp["name"])}" loading="lazy" width="400" height="300"><p class="eyebrow">{e(cp["category"])}</p><h2>{e(cp["name"])}</h2><p>{e(cp["description"])}</p></a></li>'
        for cp in c_prods
    )
    c_title = f"{c_name} — подборка {len(c_prods)} находок с AliExpress | FLUXIXO"
    c_desc = f"{cat_desc(c_name)}. {len(c_prods)} проверенных позиций со студийными фото, сравнением с оригиналом и прямыми ссылками на AliExpress."
    c_listing = {
        '@context':'https://schema.org',
        '@type':'ItemList',
        'name':f'Категория {c_name} — FLUXIXO',
        'numberOfItems':len(c_prods),
        'itemListElement':[{'@type':'ListItem','position':i+1,'url':ORIGIN+route(cp),'name':cp['name']} for i,cp in enumerate(c_prods)]
    }
    c_body = f'''<nav class="breadcrumb" aria-label="Навигационная цепочка"><a href="/">FLUXIXO</a> / <a href="/catalog/">Каталог</a> / {e(c_name)}</nav>
<p class="eyebrow">Рубрика каталога</p><h1>{e(c_name)} ({len(c_prods)})</h1><p>{e(c_desc)}</p><ul class="grid">{c_cards}</ul>'''
    write(c_path.strip('/')+'/index.html', page(c_title, c_desc, c_path, c_body, c_listing, c_prods[0]['image']))

cat_bar = '<div class="cat-links" style="display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 24px">' + ''.join(cat_nav_links) + '</div>'
catalog_paths = {language: catalog_path(language) for language in LANGUAGES}
lang_bar = language_links(catalog_paths)

listing={'@context':'https://schema.org','@type':'ItemList','name':'Каталог FLUXIXO','numberOfItems':len(products),'itemListElement':[{'@type':'ListItem','position':i+1,'url':ORIGIN+route(p),'name':p['name']} for i,p in enumerate(products)]}
write('catalog/index.html',page('Каталог FLUXIXO — техника, товары для дома, кухни и поездок с AliExpress',f'{len(products)} товаров из подборки FLUXIXO: студийные фотографии, описания, рубрики и партнёрские ссылки на AliExpress.','/catalog/','<p class="eyebrow">Находки с другой стороны</p><h1>Коллекция FLUXIXO ('+str(len(products))+')</h1><p>Техника, инструменты, товары для дома, кухни, поездок и питомцев. Выберите язык, рубрику или рассмотрите все находки ниже.</p>'+lang_bar+cat_bar+'<ul class="grid">'+''.join(items)+'</ul>',listing, alternate_paths=catalog_paths))

localized_paths = generate(ORIGIN, i18n, products, page, write, default_image)

index = (DIST/'index.html').read_text(encoding='utf-8')
title = 'FLUXIXO | Curated AliExpress Finds'
description = 'Explore gadgets, home and kitchen tools, and travel accessories in the interactive FLUXIXO showroom. Compare studio images with original seller photos.'
meta = metadata(title, description, '/', default_image, 'en')
meta += f'\n<meta name="google-site-verification" content="{GOOGLE}"><meta name="msvalidate.01" content="{BING}">'
meta += structured({'@context':'https://schema.org','@type':'WebSite','name':'FLUXIXO','url':ORIGIN+'/','inLanguage':'en'})
block = '<!-- SEARCH START -->\n'+meta+'\n<!-- SEARCH END -->'
if '<!-- SEARCH START -->' in index:
    index = re.sub(r'<!-- SEARCH START -->.*?<!-- SEARCH END -->',lambda _:block,index,flags=re.S)
else:
    index = index.replace('</head>',block+'\n</head>')
index = re.sub(r'<title>.*?</title>', lambda _: f'<title>{e(title)}</title>', index, count=1)
index = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{e(description)}">', index, count=1)
first_p = dict(first_product)
first_p.update(translations(i18n, first_product).get('en', {}))
first_p['category'] = i18n['cats'].get(first_product['category'], {}).get('en', first_product['category'])
h1_spans = ''.join(
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
write('index.html',index)

write('404.html',page('Страница не найдена | FLUXIXO','Такой страницы в FLUXIXO нет.','/404.html','<h1>Такой страницы нет</h1><p>Возможно, адрес изменился. Загляните в актуальную коллекцию.</p><a class="button" href="/catalog/">Открыть каталог</a>',noindex=True))
write('robots.txt',f'User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n')
write('BingSiteAuth.xml',f'<?xml version="1.0" encoding="UTF-8"?>\n<users><user>{BING}</user></users>\n')
keyfile=ROOT/'tools/indexnow-key.txt'
if not keyfile.exists(): keyfile.write_text(secrets.token_hex(16),encoding='utf-8')
key=keyfile.read_text().strip()
write(key+'.txt',key)

# Generate RSS 2.0 feed (/rss.xml) for automatic Pinterest & feed reader syndication
now_dt = datetime.now(timezone.utc)
rss_items = []
for p in products[:40]:
    p_url = f"{ORIGIN}{route(p)}?utm_source=rss&utm_medium=organic"
    img_url = f"{ORIGIN}/{p['image']}"
    rss_items.append(f'''    <item>
      <title>{e(p['name'])} — {e(p['category'])}</title>
      <link>{e(p_url)}</link>
      <guid isPermaLink="true">{ORIGIN}{route(p)}</guid>
      <pubDate>{format_datetime(now_dt)}</pubDate>
      <description>{e(p['description'])}</description>
      <enclosure url="{e(img_url)}" type="image/webp" length="65000"/>
    </item>''')
rss_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
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
'''
write('rss.xml', rss_xml)

# Generate Pinterest Bulk Create CSV (/pinterest-feed.csv) & Telegram/Social feed (/social-feed.json)
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

statefile=ROOT/'tools/search-build-state.json'
previous=json.loads(statefile.read_text()) if statefile.exists() else {}
state={}
ns='http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('',ns)
sitemap=ET.Element('{'+ns+'}urlset')
all_routes = ['/', '/catalog/'] + localized_paths + sorted(cat_paths) + [route(p) for p in products]
for path in all_routes:
    file=DIST/(path.strip('/')+'/index.html' if path!='/' else 'index.html')
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    old=previous.get(path,{})
    changed=old.get('lastmod') if old.get('sha256')==digest else datetime.now(timezone.utc).isoformat(timespec='seconds')
    state[path]={'sha256':digest,'lastmod':changed}
    url=ET.SubElement(sitemap,'{'+ns+'}url')
    ET.SubElement(url,'{'+ns+'}loc').text=ORIGIN+path
    ET.SubElement(url,'{'+ns+'}lastmod').text=changed
ET.indent(sitemap)
write('sitemap.xml',ET.tostring(sitemap,encoding='unicode',xml_declaration=True)+'\n')
statefile.write_text(json.dumps(state,indent=2),encoding='utf-8')
print(f'Built {len(products)} product pages, {len(cat_paths)} category hubs, catalog, rss.xml, pinterest-feed.csv, sitemap ({len(state)} URLs), robots, verification and IndexNow files.')
