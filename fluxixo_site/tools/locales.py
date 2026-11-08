"""Localized catalog and product pages share the showroom's translation data."""
from html import escape as e
import json
import re

LANGUAGES = {
    'ru': ('ru', 'ru_RU', 'Русский', 'Каталог', 'Витрина', 'К товару на AliExpress', 'Фото продавца'),
    'en': ('en', 'en_US', 'English', 'Catalog', 'Showroom', 'View on AliExpress', 'Seller photo'),
    'pt': ('pt-BR', 'pt_BR', 'Português (Brasil)', 'Catálogo', 'Vitrine', 'Ver no AliExpress', 'Foto do vendedor'),
    'es': ('es-MX', 'es_MX', 'Español (México)', 'Catálogo', 'Vitrina', 'Ver en AliExpress', 'Foto del vendedor'),
    'fr': ('fr', 'fr_FR', 'Français', 'Catalogue', 'Vitrine', 'Voir sur AliExpress', 'Photo du vendeur'),
    'he': ('he-IL', 'he_IL', 'עברית', 'קטלוג', 'תצוגת מוצרים', 'למוצר ב־AliExpress', 'תמונת המוכר'),
}
INTRO = {
    'en': 'Browse a curated selection of gadgets, home and kitchen tools, travel accessories and more. Compare our studio images with seller photos and check US shipping at AliExpress.',
    'pt': 'Conheça nossa seleção de eletrônicos, utensílios para casa e cozinha e acessórios para viagens. Compare as imagens com as fotos dos vendedores e confira o frete para o Brasil no AliExpress.',
    'es': 'Explora nuestra selección de tecnología, utensilios para el hogar y la cocina, y accesorios de viaje. Compara las imágenes con las fotos del vendedor y consulta el envío a México en AliExpress.',
    'fr': 'Découvrez notre sélection de gadgets, d’articles pour la maison et la cuisine et d’accessoires de voyage. Comparez les visuels aux photos des vendeurs et vérifiez les conditions de livraison sur AliExpress.',
    'he': 'גלו מבחר גאדג׳טים, מוצרים לבית ולמטבח ואביזרים לנסיעות. השוו בין תמונת הסטודיו לתמונת המוכר ובדקו אם יש משלוח לישראל ב־AliExpress.',
}
DISCLOSURE = {
    'en': 'We may earn a commission through affiliate links. Check the current price, product options and shipping with the seller on AliExpress.',
    'pt': 'Podemos receber uma comissão por links de afiliados. Confira o preço, as opções e a entrega com o vendedor no AliExpress.',
    'es': 'Podemos recibir una comisión por los enlaces de afiliados. Consulta el precio, las variantes y el envío con el vendedor en AliExpress.',
    'fr': 'Nous pouvons toucher une commission via les liens affiliés. Vérifiez le prix, les options et la livraison auprès du vendeur sur AliExpress.',
    'he': 'אנחנו עשויים לקבל עמלה מרכישות דרך קישורי שותפים. את המחיר, הדגם וזמינות המשלוח יש לבדוק אצל המוכר ב־AliExpress.',
}

def catalog_path(language):
    return '/catalog/' if language == 'ru' else f'/{language}/'

def product_path(product, language):
    prefix = '' if language == 'ru' else f'/{language}'
    return f"{prefix}/products/{product['id']}/"

def alternates(origin, paths):
    tags = [
        f'<link rel="alternate" hreflang="{LANGUAGES[language][0]}" href="{origin}{path}">'
        for language, path in paths.items()
    ]
    if 'en' in paths:
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{origin}{paths["en"]}">')
    return '\n'.join(tags)

def language_links(paths):
    return '<nav class="locale-links" aria-label="Language">' + ''.join(
        f'<a class="button secondary" href="{path}" lang="{LANGUAGES[language][0]}" dir="auto">{LANGUAGES[language][2]}</a>'
        for language, path in paths.items()
    ) + '</nav>'

def translations(data, product):
    return {language: value for language, value in data['products'].get(product['id'], {}).items()
            if language in LANGUAGES and language != 'ru' and all(value.get(key) for key in ('name', 'headline', 'description'))}

def sync_showroom(dist, data):
    file = dist/'js/i18n.js'
    script = file.read_text(encoding='utf-8')
    for constant, key in [('UI', 'ui'), ('CATS', 'cats'), ('PRODUCTS', 'products')]:
        pattern = rf'(  const {constant} = )\{{.*?\n\}};'
        script, count = re.subn(pattern, lambda m: m[1] + json.dumps(data[key], ensure_ascii=False, indent=2) + ';',
                                script, count=1, flags=re.S)
        if count != 1:
            raise ValueError(f'Missing {constant} dictionary in i18n.js')
    file.write_text(script, encoding='utf-8')

def generate(origin, data, products, page, write, image):
    catalogs = {language: catalog_path(language) for language in LANGUAGES}
    routes = []
    for language, (_, _, _, catalog_label, showroom, ali, seller_photo) in LANGUAGES.items():
        if language == 'ru':
            continue
        catalog = catalogs[language]
        ui = data['ui'][language]
        links = language_links(catalogs)
        entries = []
        for product in products:
            translated = translations(data, product).get(language)
            if not translated:
                continue
            paths = {key: product_path(product, key) for key in ('ru', *translations(data, product))}
            path = paths[language]
            routes.append(path)
            name, desc = translated['name'], translated['description']
            cat = data['cats'].get(product['category'], {}).get(language, '')
            studio = f"/?lang={language}#{product['id']}"
            entries.append(f'<li><a class="card" href="{path}"><img src="/{e(product["image"])}" alt="{e(name)}" loading="lazy" width="400" height="300"><p class="eyebrow">{e(cat)}</p><h2>{e(name)}</h2><p>{e(desc)}</p></a></li>')
            buy = (f'<a class="button" href="{e(product["affiliateUrl"])}" target="_blank" rel="sponsored noopener">{e(ali)} <span aria-hidden="true">↗</span></a>'
                   if product['affiliateUrl'] and not product.get('pendingLink') else f'<p>{e(ui["ctaPending"])}</p>')
            original = (f'<section class="source"><h2>{e(seller_photo)}</h2><img src="/{e(product["original"])}" alt="{e(name)}" loading="lazy"><p>{e(ui["sourceNote"])}</p></section>'
                        if product.get('original') else '')
            body = (f'<nav class="breadcrumb"><a href="/?lang={language}">FLUXIXO</a><a href="{catalog}">{e(catalog_label)}</a></nav>'
                    f'<article><div class="product"><figure><img class="hero-image" src="/{e(product["image"])}" alt="{e(name)}" width="600" height="600">'
                    f'<figcaption>{e(ui["sourceNote"])}</figcaption></figure><section><p class="eyebrow">{e(cat)}</p><h1>{e(name)}</h1><p>{e(desc)}</p>'
                    f'{buy}<a class="button secondary" href="{studio}">{e(showroom)}</a></section></div>{original}</article>{language_links(paths)}')
            schema = {'@context': 'https://schema.org', '@type': 'WebPage', 'url': origin+path,
                      'name': name, 'description': desc, 'inLanguage': LANGUAGES[language][0]}
            write(path.strip('/')+'/index.html', page(f'{name} | FLUXIXO', desc, path, body, schema,
                  product['image'], language=language, alternate_paths=paths))
        if not entries:
            continue
        title = f'{catalog_label} FLUXIXO | AliExpress'
        body = f'<h1>{e(title)}</h1><p>{e(INTRO[language])}</p>{links}<ul class="grid">{"".join(entries)}</ul>'
        write(catalog.strip('/')+'/index.html', page(title, INTRO[language], catalog, body, image=image,
              language=language, alternate_paths=catalogs))
        routes.append(catalog)
    return routes
