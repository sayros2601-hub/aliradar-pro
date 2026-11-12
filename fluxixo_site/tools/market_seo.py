"""Market-tailored country SEO checklists, localized FAQ, VideoObject schema, and rotating internal linking."""
from __future__ import annotations

from html import escape as e
from pathlib import Path
import json
import os
import re

TOOLS_DIR = Path(__file__).resolve().parent
SITE_DIR = TOOLS_DIR.parent
DEFAULT_OVERRIDES = TOOLS_DIR / 'seo_overrides.json'

POWERED_KEYS = frozenset(('Техника', 'Дом', 'Кухня', 'Инструменты', 'Уход'))

CHECKLIST_HEADING = {
    'ru': 'Что проверить перед заказом (Россия)',
    'en': 'Pre-order checklist for US buyers',
    'pt': 'Checklist antes de pedir no Brasil',
    'es': 'Qué revisar antes de pedir en México',
    'fr': 'Points à vérifier avant de commander (France)',
    'he': 'מה כדאי לבדוק לפני הזמנה לישראל',
}

MARKET_GUIDES = {
    'ru': {
        'powered': [
            'Выберите версию с евровилкой (220 В, тип C или F) либо уточните питание по USB в описании товара.',
            'Сверьте комплектацию на фото выбранного варианта, а не только на обложке карточки.',
            'Проверьте сроки доставки и условия отслеживания в ваш регион на странице оформления заказа.',
        ],
        'general': [
            'Выберите нужный вариант модели, размера или цвета перед сравнением условий у продавца.',
            'Сверьте содержимое упаковки в выбранной опции и на реальных фотографиях продавца.',
            'Уточните сроки доставки, пункт выдачи и условия спора на AliExpress до оплаты.',
        ],
    },
    'en': {
        'powered': [
            'Verify US plug compatibility (110-120V AC, Type A or Type B) or check if the item runs over standard USB.',
            'Confirm what accessories are included with the exact variant selected on AliExpress, not only in the main photo.',
            'Check USPS or local carrier tracking availability and seller return terms before placing the order.',
        ],
        'general': [
            'Compare sizes, materials, and exact SKU variant names directly on the AliExpress listing before checkout.',
            'Check the seller’s actual photos and package list rather than relying only on the studio visual.',
            'Verify estimated delivery timing to the United States and return coverage inside checkout.',
        ],
    },
    'pt': {
        'powered': [
            'Confira na página do vendedor se o modelo escolhido é bivolt (110V/220V) e compatível com tomada NBR 14136.',
            'Verifique os itens inclusos na variação exata selecionada antes de fechar o pedido.',
            'Consulte o prazo de entrega e os valores de envio e tributos exibidos no checkout do AliExpress Brasil.',
        ],
        'general': [
            'Compare medidas, cores e quantidade da variação selecionada diretamente no anúncio.',
            'Observe as fotos reais do vendedor e a descrição técnica completa da variação escolhida.',
            'Confira o prazo de frete para o seu CEP e o resumo final exibido no checkout do AliExpress.',
        ],
    },
    'es': {
        'powered': [
            'Verifica en la ficha del vendedor que la versión elegida sea compatible con 110-127V y clavija Tipo A/B en México, o alimentación USB.',
            'Revisa qué incluye exactamente la variante seleccionada antes de confirmar la compra.',
            'Consulta los tiempos de envío a México y los cargos mostrados en pantalla al pagar en AliExpress.',
        ],
        'general': [
            'Confirma medidas, color y piezas incluidas en la variante exacta que elijas en la publicación del vendedor.',
            'Compara la vista de estudio con las fotos originales del vendedor antes de confirmar tu compra.',
            'Revisa la fecha estimada de entrega en México y las condiciones de devolución del vendedor.',
        ],
    },
    'fr': {
        'powered': [
            'Vérifiez que la déclinaison choisie convient au réseau 230V avec prise européenne (Type E/F) ou alimentation USB.',
            'Contrôlez le contenu exact inclus dans l’option sélectionnée avant de valider la commande.',
            'Consultez le délai de livraison vers la France, la TVA affichée et les conditions de retour sur AliExpress.',
        ],
        'general': [
            'Comparez les dimensions, coloris et accessoires sur la déclinaison précise choisie chez le vendeur.',
            'Appuyez-vous sur les photos originales du vendeur pour vérifier les détails réels de fabrication.',
            'Vérifiez les délais d’expédition vers la France et les modalités de retour avant le paiement.',
        ],
    },
    'he': {
        'powered': [
            'בדקו בעמוד המוצר שהדגם מתאים לרשת החשמל בישראל (220–230V) עם תקע ישראלי או אירופי תואם, או פועל בחיבור USB.',
            'ודאו מה בדיוק מגיע בחבילה לפי הדגם או הערכה שבחרתם, ולא רק לפי התמונה הראשית.',
            'עברו על עלויות המשלוח לישראל, זמן ההגעה המשוער וסיכום התשלום הסופי ב־AliExpress לפני ההזמנה.',
        ],
        'general': [
            'השוו מידות, צבע ודגם מדויק ישירות בעמוד המוצר לפני שמוסיפים לעגלה.',
            'הציצו בתמונות המקוריות של המוכר ובמפרט הטכני כדי לוודא שהמוצר מתאים בדיוק למה שאתם מחפשים.',
            'בדקו את עלות המשלוח לישראל ואת מדיניות ההחזרה של המוכר לפני שמשלימים את ההזמנה.',
        ],
    },
}

FAQ_HEADING = {
    'ru': 'Частые вопросы перед покупкой',
    'en': 'Quick buyer questions',
    'pt': 'Perguntas rápidas antes de comprar',
    'es': 'Preguntas frecuentes antes de pedir',
    'fr': 'Questions fréquentes avant l’achat',
    'he': 'שאלות נפוצות לפני ההזמנה',
}


def load_overrides(path=None):
    override_path = Path(path) if path else Path(os.environ.get('FLUXIXO_SEO_OVERRIDES') or DEFAULT_OVERRIDES)
    if not override_path.exists():
        return {}
    try:
        data = json.loads(override_path.read_text(encoding='utf-8'))
        routes = data.get('routes', {})
        return routes if isinstance(routes, dict) else {}
    except (OSError, ValueError):
        return {}


def route_override(overrides, route_path):
    if not isinstance(overrides, dict):
        return {}
    normalized = route_path if route_path.endswith('/') else route_path + '/'
    return overrides.get(route_path) or overrides.get(normalized) or {}


def market_checklist_html(category_key, lang):
    guides = MARKET_GUIDES.get(lang, MARKET_GUIDES['en'])
    bullets = guides['powered'] if category_key in POWERED_KEYS else guides['general']
    heading = CHECKLIST_HEADING.get(lang, CHECKLIST_HEADING['en'])
    items = ''.join(f'<li>{e(text)}</li>' for text in bullets)
    return f'<section class="market-guide"><h2>{e(heading)}</h2><ul>{items}</ul></section>'


def default_faq(product_name, category_key, lang):
    powered = category_key in POWERED_KEYS
    templates = {
        'ru': [
            (f'Как выбрать нужную комплектацию «{product_name}»?',
             'Откройте карточку на AliExpress и нажмите на конкретный вариант модели или размера: фото, комплектация и условия привязаны к выбранной опции.'),
            ('На что обратить внимание при доставке в Россию?',
             ('Перед оплатой проверьте тип вилки (220 В) или USB-питание, ' if powered else 'Перед оплатой проверьте размеры и материалы, ')
             + 'актуальные сроки доставки и условия возврата у продавца.'),
        ],
        'en': [
            (f'How do I pick the right variant of {product_name}?',
             'Open the AliExpress listing and click the exact option thumbnail so the kit contents and specs match what you plan to order.'),
            ('What should US shoppers verify before ordering?',
             ('Verify US 110-120V voltage/plug compatibility or USB power specs, ' if powered else 'Verify item dimensions, material notes, ')
             + 'current shipping window, and return coverage on the seller listing.'),
        ],
        'pt': [
            (f'Como conferir a opção certa de {product_name}?',
             'Acesse o anúncio no AliExpress e clique exatamente na variação desejada para confirmar o que acompanha o pacote e as medidas reais.'),
            ('O que checar para entrega no Brasil?',
             ('Confira se é bivolt (110V/220V) ou compatível com a tomada NBR 14136, ' if powered else 'Confira dimensões e acabamento, ')
             + 'além do prazo estimado e dos valores mostrados no checkout do AliExpress.'),
        ],
        'es': [
            (f'¿Cómo elegir la variante correcta de {product_name}?',
             'Abre la ficha del vendedor en AliExpress y selecciona la variante exacta para revisar qué piezas incluye y sus especificaciones reales.'),
            ('¿Qué revisar antes de pedir con envío a México?',
             ('Confirma compatibilidad de 110-127V o alimentación USB, ' if powered else 'Confirma las medidas y materiales exactos, ')
             + 'junto con los tiempos de envío y cargos mostrados al finalizar la compra.'),
        ],
        'fr': [
            (f'Comment choisir la bonne version de {product_name} ?',
             'Ouvrez la fiche vendeur sur AliExpress et sélectionnez la déclinaison précise afin de voir le contenu exact et les caractéristiques associées.'),
            ('Que contrôler pour une livraison en France ?',
             ('Vérifiez la prise européenne 230V ou l’alimentation USB, ' if powered else 'Vérifiez les dimensions et matériaux indiqués, ')
             + 'ainsi que la TVA et le délai de livraison affichés par le vendeur.'),
        ],
        'he': [
            (f'איך לבחור את הגרסה הנכונה של {product_name}?',
             'היכנסו לעמוד המוצר ב־AliExpress ובחרו בדגם או באפשרות הרצויה — רק כך רואים את תכולת הערכה והמפרט המדויק של אותה גרסה.'),
            ('מה חשוב לבדוק בהזמנה לישראל?',
             ('ודאו שהדגם מתאים לחשמל בישראל (220–230V) ולתקע מתאים או לחיבור USB, ' if powered else 'בדקו מידות מדויקות וחומרים, ')
             + 'ובדקו מראש את זמני המשלוח, המסים או המע״מ ותנאי ההחזרה במסך התשלום.'),
        ],
    }
    return [{'q': q, 'a': a} for q, a in templates.get(lang, templates['en'])]


def faq_section_and_schema(product_name, category_key, lang, overrides=None):
    custom = (overrides or {}).get('faq')
    items = [item for item in (custom or []) if isinstance(item, dict) and item.get('q') and item.get('a')]
    if not items:
        items = default_faq(product_name, category_key, lang)
    heading = FAQ_HEADING.get(lang, FAQ_HEADING['en'])
    details_html = ''.join(
        f'<details class="faq-item"><summary>{e(item["q"])}</summary><p>{e(item["a"])}</p></details>'
        for item in items
    )
    html = f'<section class="product-faq"><h2>{e(heading)}</h2>{details_html}</section>'
    schema = {
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': item['q'],
                'acceptedAnswer': {'@type': 'Answer', 'text': item['a']},
            }
            for item in items
        ],
    }
    return html, schema


def discover_video(dist_dir, product_id):
    """Detect real web-ready video files for a product inside dist/assets/video."""
    dist_dir = Path(dist_dir)
    mp4 = dist_dir / f'assets/video/{product_id}.mp4'
    if not mp4.exists():
        return None
    hevc = dist_dir / f'assets/video/{product_id}.hevc.mp4'
    av1 = dist_dir / f'assets/video/{product_id}.av1.mp4'
    poster = dist_dir / f'assets/video/{product_id}.poster.jpg'
    return {
        'mp4': f'assets/video/{product_id}.mp4',
        'hevc': f'assets/video/{product_id}.hevc.mp4' if hevc.exists() else None,
        'av1': f'assets/video/{product_id}.av1.mp4' if av1.exists() else None,
        'poster': f'assets/video/{product_id}.poster.jpg' if poster.exists() else None,
    }


def video_block_and_schema(origin, dist_dir, product, name, description, lang, fallback_image):
    vid = discover_video(dist_dir, product['id'])
    if not vid:
        return '', None
    poster_rel = vid['poster'] or fallback_image
    sources = []
    if vid['av1']:
        sources.append(f'<source src="/{e(vid["av1"])}" type="video/mp4; codecs=av01.0.04M.08">')
    if vid['hevc']:
        sources.append(f'<source src="/{e(vid["hevc"])}" type="video/mp4; codecs=hvc1">')
    sources.append(f'<source src="/{e(vid["mp4"])}" type="video/mp4">')
    caption = {
        'ru': 'Короткий видеообзор деталей и внешнего вида',
        'en': 'Quick product showcase clip',
        'pt': 'Prévia em vídeo do produto',
        'es': 'Clip de vista rápida del producto',
        'fr': 'Aperçu vidéo du produit',
        'he': 'סרטון הדגמה קצר של המוצר',
    }.get(lang, 'Quick product showcase clip')
    html = (
        f'<figure class="product-video">'
        f'<video controls muted loop playsinline preload="metadata" poster="/{e(poster_rel)}" width="720" height="720">'
        f'{"".join(sources)}'
        f'</video><figcaption>{e(caption)}</figcaption></figure>'
    )
    schema = {
        '@type': 'VideoObject',
        'name': name,
        'description': description,
        'thumbnailUrl': [origin + '/' + poster_rel],
        'contentUrl': origin + '/' + vid['mp4'],
        'uploadDate': '2026-11-01T00:00:00Z',
        'inLanguage': lang,
    }
    return html, schema


def rotating_related(all_products, current_product, category_items, limit=4):
    """Select deterministic rotating peer products so every item receives contextual inbound links."""
    pid = current_product['id']
    peers = [p for p in category_items if p['id'] != pid]
    if len(category_items) > 1:
        ids = [p['id'] for p in category_items]
        idx = ids.index(pid) if pid in ids else 0
        rotated = category_items[idx + 1:] + category_items[:idx]
        peers = [p for p in rotated if p['id'] != pid]
    chosen = list(peers[:limit])
    if len(chosen) < limit:
        seen = {pid, *(p['id'] for p in chosen)}
        fallback_pool = [p for p in all_products if p['id'] not in seen]
        if fallback_pool:
            all_ids = [p['id'] for p in all_products]
            offset = (all_ids.index(pid) if pid in all_ids else 0) % len(fallback_pool)
            cycled = fallback_pool[offset:] + fallback_pool[:offset]
            chosen.extend(cycled[:limit - len(chosen)])
    return chosen[:limit]


def breadcrumb_schema(origin, crumbs):
    return {
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': index + 1, 'name': label, 'item': origin + target}
            for index, (label, target) in enumerate(crumbs)
        ],
    }


def collection_schema(origin, path, title, description, lang, items, crumbs):
    """Unified CollectionPage + ItemList + BreadcrumbList schema for category and catalog hubs."""
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'CollectionPage',
                '@id': origin + path,
                'url': origin + path,
                'name': title,
                'description': description,
                'inLanguage': lang,
                'isPartOf': {'@type': 'WebSite', 'name': 'FLUXIXO', 'url': origin + '/'},
            },
            {
                '@type': 'ItemList',
                'name': title,
                'numberOfItems': len(items),
                'itemListElement': [
                    {'@type': 'ListItem', 'position': idx + 1, 'url': origin + item_url, 'name': item_name}
                    for idx, (item_url, item_name) in enumerate(items)
                ],
            },
            breadcrumb_schema(origin, crumbs),
        ],
    }


def full_alternates(origin, paths):
    """Emit country+language, generic language, and x-default reciprocal hreflang clusters."""
    pairs = {
        'ru': ('ru', 'ru-RU'),
        'en': ('en', 'en-US'),
        'pt': ('pt-BR', 'pt'),
        'es': ('es-MX', 'es'),
        'fr': ('fr', 'fr-FR'),
        'he': ('he-IL', 'he'),
    }
    tags = []
    seen = set()
    for key in ('en', 'ru', 'pt', 'es', 'fr', 'he'):
        path = paths.get(key)
        if not path:
            continue
        for code in pairs[key]:
            if code in seen:
                continue
            seen.add(code)
            tags.append(f'<link rel="alternate" hreflang="{code}" href="{origin}{path}">')
    default_target = paths.get('en') or paths.get('ru')
    if default_target:
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{origin}{default_target}">')
    return '\n'.join(tags)
