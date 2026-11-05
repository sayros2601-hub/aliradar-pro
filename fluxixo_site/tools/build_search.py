"""Rebuild crawlable FLUXIXO pages from the portable catalog; never deploy automatically."""
from pathlib import Path
from html import escape
import json
import re
import secrets
import hashlib
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
ORIGIN = 'https://www.fluxixo.shop'
GOOGLE = 'BUSamFSGELSfaWQEaVVj2QzUgKQvWovtg-ZaHCfKNb0'
BING = '49287D3DFF71EA9430905E14A0A426F2'
catalog = json.loads((DIST/'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
products = [p for p in catalog['products'] if not p['demo']]
e = escape

def write(path, text):
    dest = DIST/path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding='utf-8')

def route(p):
    return '/products/' + p['id'] + '/'

def structured(data):
    return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'

def metadata(title, description, path, image='assets/images/import-0024.webp'):
    return f'''<link rel="canonical" href="{ORIGIN}{path}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:site_name" content="FLUXIXO">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{ORIGIN}{path}"><meta property="og:image" content="{ORIGIN}/{e(image)}">
<meta property="og:locale" content="ru_RU"><meta name="twitter:card" content="summary_large_image">'''

def page(title, description, path, body, data=None, image='assets/images/import-0024.webp', noindex=False):
    meta=metadata(title, description,path,image)
    if noindex: meta=meta.replace('index,follow,max-image-preview:large','noindex,follow')
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description)}">{meta}
<link rel="icon" href="/assets/favicon.svg?v=mira213-fluxixo-20261030"><link rel="stylesheet" href="/css/search.css?v=mira213-fluxixo-20261030">
{structured(data) if data else ''}</head><body>
<header><a class="brand" href="/" aria-label="FLUXIXO — интерактивная витрина">FLUXIXO</a><nav aria-label="Основная навигация"><a href="/catalog/">Каталог</a><a href="/">Витрина</a></nav></header>
<main>{body}</main><footer><p>FLUXIXO — небольшая коллекция интересных вещей.</p><p>Ссылки на AliExpress — партнёрские: мы можем получить комиссию. Цены, варианты, наличие, доставка и возврат определяются продавцом на AliExpress.</p><a href="/catalog/">Все товары</a></footer></body></html>'''

# css/search.css is maintained separately; rebuilding SEO must preserve design fixes.

items=[]
for p in products:
    path=route(p)
    title=p['name']+' — фото и описание | FLUXIXO'
    items.append(f'<li><a class="card" href="{path}"><img src="/{e(p["image"])}" alt="{e(p["name"])}" loading="lazy" width="400" height="300"><p class="eyebrow">{e(p["category"])}</p><h2>{e(p["name"])}</h2><p>{e(p["description"])}</p></a></li>')
    facts=''.join(f'<dt>{e(f["label"])}</dt><dd>{e(f["value"])}</dd>' for f in p['facts'])
    source=f'<section class="source"><h2>Исходное фото товара</h2><img src="/{e(p["original"])}" alt="Исходное фото: {e(p["name"])}" loading="lazy"><p>Сравните визуализацию с исходным фото. Актуальный вариант и комплектацию уточняйте у продавца.</p></section>' if p.get('original') else ''
    body=f'''<nav class="breadcrumb" aria-label="Навигационная цепочка"><a href="/">FLUXIXO</a> / <a href="/catalog/">Каталог</a></nav>
<article><div class="product"><figure><img class="hero-image" src="/{e(p['image'])}" alt="{e(p['name'])}" width="600" height="600"><figcaption>{e(p.get('imageNote',''))}</figcaption></figure><section><p class="eyebrow">{e(p['category'])}</p><h1>{e(p['name'])}</h1><p>{e(p['description'])}</p><a class="button" href="{e(p['affiliateUrl'])}" target="_blank" rel="sponsored noopener">Посмотреть на AliExpress ↗</a><a class="button secondary" href="/#{e(p['id'])}">Открыть в витрине</a><p class="muted">Партнёрская ссылка. FLUXIXO может получить комиссию за покупку. Покупка оформляется на AliExpress.</p><dl>{facts}</dl></section></div><section><h2>О товаре</h2><p class="detail-text">{e(p['details'])}</p></section>{source}</article>'''
    if p.get('pendingLink'):
        body=re.sub(r'<a class="button" href="".*?</a>', '<p class="muted">Ссылка на продавца уточняется.</p>', body)
    data={'@context':'https://schema.org','@graph':[{'@type':'WebPage','@id':ORIGIN+path,'url':ORIGIN+path,'name':title,'description':p['description'],'inLanguage':'ru','primaryImageOfPage':{'@type':'ImageObject','url':ORIGIN+'/'+p['image']}},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'FLUXIXO','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'Каталог','item':ORIGIN+'/catalog/'},{'@type':'ListItem','position':3,'name':p['name'],'item':ORIGIN+path}]}]}
    write(path.strip('/')+'/index.html',page(title,p['description'],path,body,data,p['image']))

listing={'@context':'https://schema.org','@type':'ItemList','name':'Каталог FLUXIXO','numberOfItems':len(products),'itemListElement':[{'@type':'ListItem','position':i+1,'url':ORIGIN+route(p),'name':p['name']} for i,p in enumerate(products)]}
write('catalog/index.html',page('Каталог FLUXIXO — техника, аксессуары и товары для питомцев','26 товаров из подборки FLUXIXO: фотографии, описания и партнёрские ссылки на AliExpress.','/catalog/','<p class="eyebrow">Находки с другой стороны</p><h1>Коллекция FLUXIXO</h1><p>Техника, аксессуары для поездок и товары для питомцев. Рассмотрите предмет и исходное фото, а актуальные условия покупки уточните на AliExpress.</p><ul class="grid">'+''.join(items)+'</ul>',listing))

index=(DIST/'index.html').read_text(encoding='utf-8')
meta=metadata('FLUXIXO — находки с другой стороны','Небольшая коллекция техники, аксессуаров и товаров для питомцев. Фотографии, описания и ссылки на AliExpress.','/')
meta+=f'\n<meta name="google-site-verification" content="{GOOGLE}"><meta name="msvalidate.01" content="{BING}">'
meta+=structured({'@context':'https://schema.org','@type':'WebSite','name':'FLUXIXO','url':ORIGIN+'/','inLanguage':'ru'})
block='<!-- SEARCH START -->\n'+meta+'\n<!-- SEARCH END -->'
if '<!-- SEARCH START -->' in index:
    index=re.sub(r'<!-- SEARCH START -->.*?<!-- SEARCH END -->',lambda _:block,index,flags=re.S)
else:
    index=index.replace('</head>',block+'\n</head>')
write('index.html',index)
# Public editor and security/redirect configuration are owned by the release process.
write('404.html',page('Страница не найдена | FLUXIXO','Такой страницы в FLUXIXO нет.','/404.html','<h1>Такой страницы нет</h1><p>Возможно, адрес изменился. Загляните в актуальную коллекцию.</p><a class="button" href="/catalog/">Открыть каталог</a>',noindex=True))
write('robots.txt',f'User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n')
write('BingSiteAuth.xml',f'<?xml version="1.0" encoding="UTF-8"?>\n<users><user>{BING}</user></users>\n')
keyfile=ROOT/'tools/indexnow-key.txt'
if not keyfile.exists(): keyfile.write_text(secrets.token_hex(16),encoding='utf-8')
key=keyfile.read_text().strip()
write(key+'.txt',key)

statefile=ROOT/'tools/search-build-state.json'
previous=json.loads(statefile.read_text()) if statefile.exists() else {}
state={}
ns='http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('',ns)
sitemap=ET.Element('{'+ns+'}urlset')
for path in ['/', '/catalog/']+[route(p) for p in products]:
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
print(f'Built {len(products)} product pages, catalog, sitemap ({len(state)} URLs), robots, verification and IndexNow files.')
