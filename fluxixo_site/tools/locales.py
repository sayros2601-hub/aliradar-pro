"""Localized catalog and product pages share the showroom's translation data."""
from html import escape as e
import json
import re

LANGUAGES = {
    'ru': ('ru', 'ru_RU', 'Русский', 'Каталог', '3D-витрина', 'Посмотреть на AliExpress', 'Исходное фото продавца'),
    'en': ('en', 'en_US', 'English', 'Catalog', '3D Showroom', 'Open on AliExpress', 'Original seller photo'),
    'pt': ('pt-BR', 'pt_BR', 'Português (Brasil)', 'Catálogo', 'Vitrine 3D', 'Ver no AliExpress', 'Foto original do vendedor'),
    'es': ('es-MX', 'es_MX', 'Español (México)', 'Catálogo', 'Vitrina 3D', 'Ver en AliExpress', 'Foto original del vendedor'),
    'fr': ('fr', 'fr_FR', 'Français', 'Catalogue', 'Vitrine 3D', 'Voir sur AliExpress', 'Photo originale du vendeur'),
    'he': ('he-IL', 'he_IL', 'עברית', 'קטלוג', 'תצוגת 3D', 'למוצר ב־AliExpress', 'תמונת המוכר המקורית'),
}

SHORT_LABELS = {
    'en': 'EN · Eng',
    'ru': 'RU · Рус',
    'pt': 'PT · Bra',
    'es': 'ES · Méx',
    'fr': 'FR · Fra',
    'he': 'HE · עבר',
}

INTRO = {
    'en': 'Browse our curated collection of gadgets, home and kitchen tools, travel gear, and pet finds. Inspect studio cutouts, compare with seller photos, and open listings directly on AliExpress.',
    'pt': 'Conheça nossa seleção de eletrônicos, utensílios para casa e cozinha, itens de viagem e pets. Compare os visuais de estúdio com as fotos do vendedor e veja no AliExpress.',
    'es': 'Explora nuestra selección de tecnología, artículos para el hogar y la cocina, accesorios de viaje y mascotas. Compara las imágenes de estudio con las fotos del vendedor en AliExpress.',
    'fr': 'Découvrez notre sélection de gadgets, d’articles pour la maison et la cuisine, et d’accessoires de voyage. Comparez nos visuels studio aux photos des vendeurs sur AliExpress.',
    'he': 'גלו מבחר גאדג׳טים, כלים לבית ולמטבח, אביזרים לנסיעות ומוצרים לחיות מחמד. השוו בין תמונת הסטודיו לתמונת המוכר ופתחו את המוצר ב־AliExpress.',
}

DISCLOSURE = {
    'ru': 'По партнёрским ссылкам FLUXIXO может получить комиссию. Актуальную цену, модификацию и условия доставки уточняйте на странице продавца на AliExpress.',
    'en': 'We may earn a commission through affiliate links at no extra cost to you. Check the current price, option, and shipping details with the seller on AliExpress.',
    'pt': 'Podemos receber uma comissão por links de afiliados sem custo adicional. Confira o preço atual, a variação e o frete com o vendedor no AliExpress.',
    'es': 'Podemos recibir una comisión por enlaces de afiliados sin costo extra para ti. Consulta el precio actual, el modelo y el envío con el vendedor en AliExpress.',
    'fr': 'Nous pouvons percevoir une commission via les liens affiliés sans frais supplémentaires. Vérifiez le prix, le modèle et la livraison auprès du vendeur sur AliExpress.',
    'he': 'אנחנו עשויים לקבל עמלה מרכישות דרך קישורי שותפים ללא עלות נוספת עבורכם. בדקו את המחיר, הדגם וזמינות המשלוח אצל המוכר ב־AliExpress.',
}

RELATED_HEADING = {
    'ru': 'Похожие находки в коллекции',
    'en': 'More finds in this category',
    'pt': 'Mais achados nesta categoria',
    'es': 'Más hallazgos en esta categoría',
    'fr': 'Autres trouvailles dans cette catégorie',
    'he': 'מוצרים נוספים בקטגוריה זו',
}

STAGE_CAPTION = {
    'ru': 'Студийная визуализация FLUXIXO · проверьте комплектацию у продавца',
    'en': 'FLUXIXO studio visualization · verify options on the seller listing',
    'pt': 'Visualização de estúdio FLUXIXO · confira as opções no anúncio',
    'es': 'Visualización de estudio FLUXIXO · verifica las opciones con el vendedor',
    'fr': 'Visuel studio FLUXIXO · vérifiez les options sur la fiche vendeur',
    'he': 'הדמיית סטודיו של FLUXIXO · בדקו את הדגם והמפרט בעמוד המוכר',
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

def header_lang_select(current_lang, alternate_paths=None):
    paths = alternate_paths or {lang: catalog_path(lang) for lang in LANGUAGES}
    options = []
    for lang in ('en', 'ru', 'pt', 'es', 'fr', 'he'):
        target = paths.get(lang, catalog_path(lang))
        sel = ' selected' if lang == current_lang else ''
        options.append(f'<option value="{e(target)}" data-lang="{lang}"{sel}>{e(SHORT_LABELS[lang])}</option>')
    return f'<select class="lang-select" aria-label="Language">{"".join(options)}</select>'

def translations(data, product):
    return {language: value for language, value in data['products'].get(product['id'], {}).items()
            if language in LANGUAGES and language != 'ru' and all(value.get(key) for key in ('name', 'headline', 'description'))}

def translate_fact(data, text, language):
    if language == 'ru' or not text:
        return text
    return data.get('facts', {}).get(text, {}).get(language) or data.get('cats', {}).get(text, {}).get(language) or text

def sync_showroom(dist, data):
    file = dist/'js/i18n.js'
    script = file.read_text(encoding='utf-8')
    for constant, key in [('UI', 'ui'), ('CATS', 'cats'), ('FACTS', 'facts'), ('PRODUCTS', 'products')]:
        if key not in data:
            continue
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
            headline = ' '.join(translated.get('headline', []))
            cat = data['cats'].get(product['category'], {}).get(language, product['category'])
            studio = f"/?lang={language}#{product['id']}"
            entries.append(
                f'<li><a class="card" href="{path}">'
                f'<div class="card-visual"><img src="/{e(product["image"])}" alt="{e(name)}" loading="lazy" width="400" height="300"></div>'
                f'<p class="eyebrow">{e(cat)}</p><h2>{e(name)}</h2><p>{e(desc)}</p></a></li>'
            )
            buy = (f'<a class="button" href="{e(product["affiliateUrl"])}" target="_blank" rel="sponsored noopener"><span>{e(ali)}</span><span aria-hidden="true">↗</span></a>'
                   if product['affiliateUrl'] and not product.get('pendingLink') else f'<p class="muted">{e(ui["ctaPending"])}</p>')
            facts_html = ''.join(
                f'<dt>{e(translate_fact(data, f["label"], language))}</dt><dd>{e(translate_fact(data, f["value"], language))}</dd>'
                for f in product.get('facts', [])
            )
            dl_block = f'<dl class="specs-grid">{facts_html}</dl>' if facts_html else ''
            original = (
                f'<details class="source-details"><summary>{e(seller_photo)}</summary>'
                f'<img src="/{e(product["original"])}" alt="{e(name)}" loading="lazy">'
                f'<p>{e(ui["sourceNote"])}</p></details>'
                if product.get('original') else ''
            )
            # Related products in the same category (localized)
            same_cat = [other for other in products if other['id'] != product['id'] and other['category'] == product['category']]
            if len(same_cat) < 4:
                others = [other for other in products if other['id'] != product['id'] and other not in same_cat]
                same_cat.extend(others[:4 - len(same_cat)])
            rel_cards = []
            for r in same_cat[:4]:
                r_tr = translations(data, r).get(language, {})
                r_name = r_tr.get('name', r['name'])
                r_desc = r_tr.get('description', r['description'])
                r_cat = data['cats'].get(r['category'], {}).get(language, r['category'])
                r_path = product_path(r, language)
                rel_cards.append(
                    f'<li><a class="card" href="{r_path}">'
                    f'<div class="card-visual"><img src="/{e(r["image"])}" alt="{e(r_name)}" loading="lazy" width="300" height="225"></div>'
                    f'<p class="eyebrow">{e(r_cat)}</p><h3>{e(r_name)}</h3><p>{e(r_desc)}</p></a></li>'
                )
            related_block = f'<section class="related"><h2>{e(RELATED_HEADING[language])}</h2><ul class="grid">{"".join(rel_cards)}</ul></section>'

            body = (
                f'<nav class="breadcrumb"><a href="/?lang={language}">FLUXIXO</a><span class="breadcrumb-sep">/</span><a href="{catalog}">{e(catalog_label)}</a></nav>'
                f'<article><div class="product">'
                f'<figure class="arcade-stage-card"><img class="hero-image" src="/{e(product["image"])}" alt="{e(name)}" width="600" height="600"><div class="stage-podium-bar" aria-hidden="true"></div>'
                f'<figcaption>{e(STAGE_CAPTION[language])}</figcaption></figure>'
                f'<section><p class="eyebrow">{e(cat)}</p><h1>{e(name)}</h1>'
                f'<p class="product-headline-sub">{e(headline)}</p><p>{e(desc)}</p>'
                f'<div class="cta-row">{buy}<a class="button secondary" href="{studio}">{e(showroom)}</a></div>'
                f'<p class="affiliate-disclosure">{e(ui["affiliateNote"])}</p>'
                f'{dl_block}</section></div>{original}{related_block}</article>{language_links(paths)}'
            )
            schema = {'@context': 'https://schema.org', '@type': 'WebPage', 'url': origin+path,
                      'name': name, 'description': desc, 'inLanguage': LANGUAGES[language][0]}
            write(path.strip('/')+'/index.html', page(f'{name} | FLUXIXO', desc, path, body, schema,
                  product['image'], language=language, alternate_paths=paths, studio_url=studio))
        if not entries:
            continue
        title = f'{catalog_label} FLUXIXO ({len(entries)}) | AliExpress'
        body = f'<p class="eyebrow">{e(ui["brandLine"])}</p><h1>{e(catalog_label)} FLUXIXO ({len(entries)})</h1><p>{e(INTRO[language])}</p><ul class="grid">{"".join(entries)}</ul>{links}'
        write(catalog.strip('/')+'/index.html', page(title, INTRO[language], catalog, body, image=image,
              language=language, alternate_paths=catalogs))
        routes.append(catalog)
    return routes
