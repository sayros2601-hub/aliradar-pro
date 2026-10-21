"""Build a validated, public-only static site into dist/. No credentials or sources."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps
from dealvault_core import BASE_DIR, DATA_DIR, DOMAIN, LANGUAGES, read_json, page_path, product_title, validate_catalog, utc_now
from site_content import COPY, LANG_NAMES


def esc(value):
    return html.escape(str(value), quote=True)


def script_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def relative_url(path, current):
    return os.path.relpath(path, Path(current).parent).replace('\\', '/')


class SiteBuilder:
    def __init__(self, db, output):
        self.db, self.out = db, Path(output)
        self.domain = db['site_meta']['domain'].rstrip('/')
        if self.domain != DOMAIN:
            raise ValueError('Production domain must be changed deliberately in dealvault_core.py first')
        self.products = validate_catalog(db)
        self.cats = [c for c in db['categories'] if c['id'] != 'all' and any(p['category'] == c['id'] for p in self.products)]
        self.images = {}
        self.rates = read_json(DATA_DIR / 'exchange_rates.json', {'rates': {'USD': 1}, 'observed_at': None})
        self.public_products = []

    def write(self, path, content):
        target = self.out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8', newline='\n')

    def prepare_assets(self):
        for name in ('modern.css', 'modern_app.js', 'tracking.js', 'icon.svg'):
            source = BASE_DIR / 'assets' / name
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:10]
            self.images[name] = f'assets/{source.stem}.{digest}{source.suffix}'
            target = self.out / self.images[name]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for p in self.products:
            gallery = []
            for source in dict.fromkeys([p['image'], *p.get('gallery', [])]):
                if source not in self.images:
                    raw = BASE_DIR / source
                    digest = hashlib.sha256(raw.read_bytes()).hexdigest()[:10]
                    dest = f'assets/img/{raw.stem}.{digest}.webp'
                    target = self.out / dest
                    target.parent.mkdir(parents=True, exist_ok=True)
                    cache = BASE_DIR / '.cache' / dest
                    if cache.is_file():
                        shutil.copyfile(cache,target)
                    else:
                        with Image.open(raw) as image:
                            image = ImageOps.exif_transpose(image)
                            image.thumbnail((900, 900), Image.Resampling.LANCZOS)
                            if image.mode not in ('RGB', 'RGBA'):
                                image = image.convert('RGB')
                            image.save(target, 'WEBP', quality=82, method=5)
                        cache.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(target,cache)
                    # Keep original public photo URLs used by existing social posts.
                    original=self.out/source
                    original.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(raw,original)
                    self.images[source] = dest
                gallery.append(self.images[source])
            self.public_products.append({
                'id': p['id'], 'slug': p['slug'], 'category': p['category'],
                'title_i18n': p['title_i18n'], 'price_usd': p['price_usd'],
                'affiliate_url': p['affiliate_url'], 'image': gallery[0], 'gallery': gallery,
            })

    def category_name(self, category, lang):
        return next((c.get('name_i18n', {}).get(lang, category) for c in self.cats if c['id'] == category), category)

    def shell(self, lang, current, title, body, slug=None, legal=None, noindex=False, schemas=None):
        c = COPY[lang]
        rel = lambda path: esc(relative_url(path, current))
        url = f'{self.domain}/{current}'
        alt = lambda language: f'{self.domain}/{page_path(language, slug, legal)}'
        alternates = ''.join(f'<link rel="alternate" hreflang="{l}" href="{esc(alt(l))}">' for l in LANGUAGES)
        languages = ''.join(f'<a href="{rel(page_path(l, slug, legal))}" lang="{l}" hreflang="{l}" data-lang-link="{l}" {"aria-current=\"page\"" if l == lang else ""}>{LANG_NAMES[l]}</a>' for l in LANGUAGES)
        legal_nav = ''.join(f'<a href="{rel(page_path(lang, legal=name))}">{esc(c[name])}</a>' for name in ('privacy', 'terms', 'disclosure', 'contact'))
        cur_options = ''.join(f'<option value="{cur}">{cur}</option>' for cur in ('USD', 'ILS', 'EUR', 'RUB') if cur in self.rates['rates'])
        schema = {'@context':'https://schema.org', '@type':'WebPage', 'name':title, 'url':url, 'inLanguage':lang}
        visible_products = self.public_products
        if legal:
            visible_products = []
        elif slug:
            main_product = next(p for p in self.public_products if p['slug'] == slug)
            related = [p for p in self.public_products if p['id'] != main_product['id'] and p['category'] == main_product['category']][:4]
            if not related:
                related = [p for p in self.public_products if p['id'] != main_product['id']][:4]
            visible_products = [main_product,*related]
        payload = {'lang':lang, 'domain':self.domain, 'copy':c, 'products':visible_products,
                   'rates':self.rates, 'paths':{p['id']:relative_url(page_path(lang,p['slug']),current) for p in visible_products}}
        social_product = next((p for p in self.products if p['slug'] == slug),self.products[0])
        hero_image = self.images[social_product['image']]
        description = (f'{title}. {c["about_text"]}' if slug else c.get(f'{legal}_text',c['intro']))[:200]
        return f'''<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang == 'he' else 'ltr'}" data-theme="light">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | DealVault</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(url)}">{alternates}<link rel="alternate" hreflang="x-default" href="{esc(alt('en'))}">
{'<meta name="robots" content="noindex,follow">' if noindex else ''}
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)} | DealVault">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(url)}"><meta property="og:image" content="{self.domain}/{hero_image}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#f7f7f2">
<link rel="icon" type="image/svg+xml" href="{rel(self.images['icon.svg'])}"><link rel="manifest" href="{rel('manifest.json')}">
<link rel="alternate" type="application/rss+xml" title="DealVault" href="{rel('rss.xml')}">
<link rel="stylesheet" href="{rel(self.images['modern.css'])}">
<script>try{{var t=localStorage.getItem('sp_theme');document.documentElement.dataset.theme=['dark','light'].includes(t)?t:(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light')}}catch(e){{}}</script>
<script type="application/ld+json">{script_json(schemas or schema)}</script>
<script id="products-db" type="application/json">{script_json(payload)}</script>
<script defer src="{rel(self.images['tracking.js'])}"></script><script defer src="{rel(self.images['modern_app.js'])}"></script>
</head><body>
<a class="skip-link" href="#main">{esc(c['skip'])}</a>
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="{rel(page_path(lang))}" aria-label="DealVault"><span class="brand-mark" aria-hidden="true">d<span>v</span></span><span>DealVault<small>{esc(c['tagline'])}</small></span></a>
<div class="header-controls"><nav class="languages" aria-label="{esc(c['language'])}">{languages}</nav>
<label class="currency-label"><span class="sr-only">{esc(c['currency'])}</span><select id="currency-select" aria-label="{esc(c['currency'])}">{cur_options}</select></label>
<button class="theme-toggle" id="theme-toggle" type="button" aria-label="{esc(c['theme'])}" title="{esc(c['theme'])}">◐</button></div></div></header>
{body}
<footer class="site-footer"><div class="wrap footer-inner"><div><a class="footer-brand" href="{rel(page_path(lang))}">DealVault<span>↗</span></a><p>{esc(c['affiliate'])}</p></div><nav aria-label="DealVault">{legal_nav}<a href="{rel('rss.xml')}">RSS</a><a href="https://www.exchangerate-api.com" rel="noopener">Rates by ExchangeRate-API</a></nav></div><div class="wrap footer-bottom"><span>© 2026 DealVault</span><span>{esc(c['seller_note'])}</span></div></footer>
<dialog id="product-modal" aria-labelledby="modal-title"><button type="button" class="modal-close" data-close-modal aria-label="{esc(c['close'])}">×</button><div id="modal-content-area"></div></dialog>
<div id="toast" class="toast" role="status" aria-live="polite" hidden></div>
</body></html>'''

    def card(self, p, lang, current, index=10):
        c = COPY[lang]
        title = product_title(p, lang)
        link = esc(relative_url(page_path(lang, p['slug']), current))
        image = esc(relative_url(self.images[p['image']], current))
        search = ' '.join([*p['title_i18n'].values(), p['slug'], *[self.category_name(p['category'], l) for l in LANGUAGES]])
        return f'''<article class="product-card" data-id="{esc(p['id'])}" data-category="{esc(p['category'])}" data-price="{p['price_usd']}" data-order="{index}" data-search="{esc(search)}">
<a href="{link}" class="card-image"><img src="{image}" alt="{esc(title)}" width="600" height="600" loading="{'eager' if index < 4 else 'lazy'}" decoding="async"></a>
<div class="card-content"><span class="card-category">{esc(self.category_name(p['category'], lang))}</span><h3><a href="{link}">{esc(title)}</a></h3>
<div class="card-price"><span class="price-caption">{esc(c['reference'])}</span><strong data-money="{p['price_usd']}">${p['price_usd']:.2f}</strong></div>
<div class="card-actions"><a href="{esc(p['affiliate_url'])}" target="_blank" rel="sponsored nofollow noopener" data-aff-id="{esc(p['id'])}" class="detail-link">{esc(c['shop'])} <span aria-hidden="true">↗</span></a><button class="quick-button" type="button" data-modal-id="{esc(p['id'])}" aria-label="{esc(c['quick'] + ': ' + title)}">＋</button></div></div></article>'''

    def index(self, lang):
        c, current = COPY[lang], page_path(lang)
        rel = lambda path: esc(relative_url(path, current))
        feature = next((p for p in self.products if p['id'] == 'real-101'), self.products[0])
        pills = f'<button type="button" data-cat="all" class="category-pill active" aria-pressed="true">{esc(c["all"])}<span>{len(self.products)}</span></button>'
        for cat in self.cats:
            count = sum(p['category'] == cat['id'] for p in self.products)
            pills += f'<button type="button" data-cat="{esc(cat["id"])}" class="category-pill" aria-pressed="false">{esc(cat["name_i18n"][lang])}<span>{count}</span></button>'
        cards = ''.join(self.card(p, lang, current, i) for i,p in enumerate(self.products))
        body = f'''<main id="main"><section class="wrap hero"><div class="hero-copy"><p class="eyebrow"><span></span>{esc(c['eyebrow'])}</p><h1>{c['hero']}</h1><p class="hero-intro">{esc(c['intro'])}</p><div class="hero-actions"><a class="button primary" href="#collection">{esc(c['explore'])}<span aria-hidden="true">↗</span></a><a class="text-link" href="#approach">{esc(c['how'])}</a></div><div class="hero-proof"><span>○ {esc(c['independent'])}</span><span>↗ {esc(c['direct'])}</span></div></div>
<a class="spotlight" href="{rel(page_path(lang, feature['slug']))}"><div class="spotlight-top"><span>{esc(c['spotlight'])}</span><span class="round-arrow">↗</span></div><img src="{rel(self.images[feature['image']])}" width="600" height="600" fetchpriority="high" alt="{esc(product_title(feature,lang))}"><div class="spotlight-bottom"><span>{esc(product_title(feature,lang))}</span><span class="spotlight-price" data-money="{feature['price_usd']}">${feature['price_usd']:.2f}</span></div><span class="spotlight-caption">{esc(c['reference'])}</span></a></section>
<div class="wrap disclosure-strip"><span aria-hidden="true">↗</span><p>{esc(c['affiliate'])}</p></div>
<section class="wrap collection" id="collection" aria-labelledby="collection-title"><div class="section-title"><div><p class="eyebrow">DEALVAULT / 01</p><h2 id="collection-title">{esc(c['collection'])}</h2><p>{esc(c['collection_sub'])}</p></div><span id="items-counter" role="status" aria-live="polite">{len(self.products)} {esc(c['found'])}</span></div>
<div class="category-nav" id="category-nav" aria-label="{esc(c['collection'])}">{pills}</div>
<div class="filter-bar"><label class="search"><span aria-hidden="true">⌕</span><span class="sr-only">{esc(c['search_label'])}</span><input type="search" id="global-search-input" placeholder="{esc(c['search'])}" autocomplete="off"></label>
<label class="filter-select"><span class="sr-only">{esc(c['budget'])}</span><select id="price-select" aria-label="{esc(c['budget'])}"><option value="all">{esc(c['any'])}</option><option value="10">{esc(c['under'].format(price='$10'))}</option><option value="25">{esc(c['under'].format(price='$25'))}</option><option value="50">{esc(c['under'].format(price='$50'))}</option><option value="over50">{esc(c['over'].format(price='$50'))}</option></select></label>
<label class="filter-select"><span class="sr-only">{esc(c['sort'])}</span><select id="sort-select" aria-label="{esc(c['sort'])}"><option value="curated">{esc(c['curated'])}</option><option value="price_asc">{esc(c['asc'])}</option><option value="price_desc">{esc(c['desc'])}</option></select></label></div>
<div class="price-notice"><p>{esc(c['price_note'])}</p><span id="rates-note"></span></div>
<div class="product-grid" id="product-grid">{cards}</div><div id="empty-state" class="empty-state" hidden><h3>{esc(c['empty'])}</h3><button class="button primary" type="button" id="clear-filters">{esc(c['reset'])}</button></div></section>
<section class="wrap approach" id="approach"><div><p class="eyebrow">DEALVAULT / 02</p><h2>{esc(c['method'])}</h2></div><p>{esc(c['method_text'])}</p></section></main>'''
        schema = {'@context':'https://schema.org','@type':'CollectionPage','name':c['collection'],'url':f'{self.domain}/{current}','inLanguage':lang,'mainEntity':{'@type':'ItemList','numberOfItems':len(self.products),'itemListElement':[{'@type':'ListItem','position':i+1,'url':f'{self.domain}/{page_path(lang,p["slug"])}','name':product_title(p,lang)} for i,p in enumerate(self.products)]}}
        self.write(current, self.shell(lang,current,c['collection'],body,schemas=schema))

    def deal(self, p, lang):
        c, current = COPY[lang], page_path(lang,p['slug'])
        rel = lambda path: esc(relative_url(path,current))
        gallery = list(dict.fromkeys([p['image'], *p.get('gallery',[])]))
        images = ''.join(f'<a href="{rel(self.images[src])}" class="gallery-image"><img src="{rel(self.images[src])}" alt="{esc(product_title(p,lang))} · {i+1}" width="800" height="800" loading="{"eager" if i==0 else "lazy"}"></a>' for i,src in enumerate(gallery))
        others = [x for x in self.products if x['id'] != p['id'] and x['category'] == p['category']][:4]
        if not others:
            others = [x for x in self.products if x['id'] != p['id']][:4]
        related = ''.join(self.card(x,lang,current,i+10) for i,x in enumerate(others))
        body = f'''<main id="main" class="wrap deal-page"><a class="back-link" href="{rel(page_path(lang))}">← {esc(c['back'])}</a><div class="deal-layout"><div class="deal-gallery">{images}</div><div class="deal-info"><p class="eyebrow">{esc(self.category_name(p['category'],lang))}</p><h1>{esc(product_title(p,lang))}</h1><div class="deal-price"><span>{esc(c['reference'])}</span><strong data-money="{p['price_usd']}">${p['price_usd']:.2f}</strong></div><p class="muted">{esc(c['price_note'])}</p><p class="rate-detail" id="rates-note"></p><a class="button primary buy-button" href="{esc(p['affiliate_url'])}" target="_blank" rel="sponsored nofollow noopener" data-aff-id="{esc(p['id'])}">{esc(c['shop'])} ↗</a><p class="affiliate-note">{esc(c['affiliate'])}</p><div class="buyer-check"><h2>{esc(c['before'])}</h2><ul>{''.join(f'<li>{esc(c[k])}</li>' for k in ('check1','check2','check3'))}</ul></div><h2 class="small-heading">{esc(c['about'])}</h2><p class="muted">{esc(c['about_text'])}</p><div class="share-row" data-product-id="{esc(p['id'])}"><span>{esc(c['share'])}</span><button type="button" data-share="copy">{esc(c['copy'])}</button><button type="button" data-share="whatsapp">WhatsApp</button><button type="button" data-share="telegram">Telegram</button></div></div></div><section class="related"><h2>{esc(c['related'])}</h2><div class="product-grid">{related}</div></section></main>'''
        schema = {'@context':'https://schema.org','@type':'WebPage','url':f'{self.domain}/{current}','name':product_title(p,lang),'inLanguage':lang,'about':{'@type':'Product','name':product_title(p,lang),'image':[f'{self.domain}/{self.images[src]}' for src in gallery]},'breadcrumb':{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'DealVault','item':f'{self.domain}/{page_path(lang)}'},{'@type':'ListItem','position':2,'name':product_title(p,lang),'item':f'{self.domain}/{current}'}]}}
        self.write(current,self.shell(lang,current,product_title(p,lang),body,slug=p['slug'],schemas=schema))

    def legal(self, lang, name):
        c, current = COPY[lang], page_path(lang,legal=name)
        extra = f'<button type="button" class="button primary" id="clear-preferences">{esc(c["clear"])}</button>' if name == 'privacy' else ''
        email = self.db['site_meta'].get('contact_email')
        if name == 'contact' and email:
            extra = f'<p><a href="mailto:{esc(email)}">{esc(email)}</a></p>'
        body = f'<main id="main" class="wrap prose"><p class="eyebrow">DEALVAULT</p><h1>{esc(c[name])}</h1><p>{esc(c[name+"_text"])}</p>{extra}<a class="back-link" href="{esc(relative_url(page_path(lang),current))}">← {esc(c["back"])}</a></main>'
        self.write(current,self.shell(lang,current,c[name],body,legal=name))

    def feeds(self):
        channel = ET.Element('channel')
        for k,v in [('title','DealVault — everyday finds'),('link',self.domain),('description',COPY['en']['intro']),('language','en')]:
            ET.SubElement(channel,k).text=v
        items=[]
        for p in self.products:
            link=f'{self.domain}/{page_path("en",p["slug"])}'
            text=f'{product_title(p)}. {COPY["en"]["reference"]}: ${p["price_usd"]:.2f}. {COPY["en"]["price_note"]} {COPY["en"]["affiliate"]}'
            item=ET.SubElement(channel,'item')
            for k,v in [('title',product_title(p)),('link',link),('description',text)]:
                ET.SubElement(item,k).text=v
            ET.SubElement(item,'guid',isPermaLink='true').text=link
            items.append({'id':link,'url':link,'title':product_title(p),'content_text':text,'image':f'{self.domain}/{self.images[p["image"]]}'})
        rss=ET.Element('rss',version='2.0'); rss.append(channel)
        self.write('rss.xml','<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(rss,encoding='unicode'))
        self.write('feed.json',json.dumps({'version':'https://jsonfeed.org/version/1.1','title':'DealVault','home_page_url':self.domain,'feed_url':f'{self.domain}/feed.json','items':items},ensure_ascii=False,indent=2))

    def build(self):
        self.prepare_assets()
        for lang in LANGUAGES:
            self.index(lang)
            for p in self.products:
                self.deal(p,lang)
            for name in ('privacy','terms','disclosure','contact'):
                self.legal(lang,name)
        self.feeds()
        urls=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        for page in sorted(self.out.rglob('*.html')):
            ET.SubElement(ET.SubElement(urls,'url'),'loc').text=f'{self.domain}/{page.relative_to(self.out).as_posix()}'
        self.write('sitemap.xml','<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(urls,encoding='unicode'))
        self.write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {self.domain}/sitemap.xml\n')
        self.write('CNAME',self.domain.removeprefix('https://')+'\n')
        self.write('manifest.json',json.dumps({'name':'DealVault','short_name':'DealVault','start_url':'./index.html','display':'standalone','background_color':'#f7f7f2','theme_color':'#246849','icons':[{'src':self.images['icon.svg'],'sizes':'any','type':'image/svg+xml','purpose':'any'}]}))
        self.write('build-info.json',json.dumps({'version':'2026.10','built_at':utc_now(),'products':len(self.products),'languages':list(LANGUAGES),'catalog_sha256':hashlib.sha256(json.dumps(self.db,sort_keys=True,ensure_ascii=False).encode()).hexdigest()},indent=2))
        self.write('404.html',self.shell('en','404.html','Page not found',f'<main id="main" class="wrap prose"><p class="eyebrow">404</p><h1>{COPY["en"]["unavailable"]}</h1><a class="button primary" href="index.html">{COPY["en"]["home"]} ↗</a></main>',noindex=True))


def build_site(output=None, db=None):
    db=db or read_json(DATA_DIR/'products.json')
    dest=Path(output or BASE_DIR/'dist').resolve()
    if dest == BASE_DIR or BASE_DIR not in dest.parents:
        raise ValueError('Build destination must be a child of the project directory')
    stage=Path(tempfile.mkdtemp(prefix='.build-',dir=BASE_DIR)).resolve()
    previous=dest.with_name(dest.name+'.previous')
    try:
        report=read_json(DATA_DIR/'link_health_report.json',{'results':[]})
        checks={r['id']:r for r in report['results']}
        excluded=[p for p in db['products'] if checks.get(p['id'],{}).get('affiliate_url') == p['affiliate_url'] and checks[p['id']]['status'] in ('INVALID','MISMATCH','UNAVAILABLE')]
        if excluded:
            if len(excluded) > max(1,len(db['products'])//5):
                raise ValueError('Unusual link failure volume; retaining the previous build for review')
            excluded_ids={p['id'] for p in excluded}
            db={**db,'products':[p for p in db['products'] if p['id'] not in excluded_ids]}
        SiteBuilder(db,stage).build()
        from verify_site import verify_site
        verify_site(stage)
        if previous.exists():
            if BASE_DIR not in previous.resolve().parents:
                raise ValueError('Unsafe previous build directory')
            shutil.rmtree(previous)
        if dest.exists():
            dest.rename(previous)
        try:
            stage.rename(dest)
        except Exception:
            if previous.exists() and not dest.exists():
                previous.rename(dest)
            raise
        print(f'[Build] {len(db["products"])} products × {len(LANGUAGES)} languages; public-only output: {dest}')
        return dest
    finally:
        if stage.exists() and BASE_DIR in stage.parents:
            shutil.rmtree(stage)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=None)
    build_site(parser.parse_args().output)
