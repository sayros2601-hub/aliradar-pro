"""Source-grounded daily discovery using existing AliExpress API credentials.

No network at import. The caller provides the existing signed API transport.
There is no advertising, rarity, quality or shipping inference; selection is a
deterministic comparison of actual seller titles against explicit task terms.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import deque
from io import BytesIO
from pathlib import Path
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from urllib.parse import urlsplit
from . import image_studio
from .policy import QUERY, DETAIL, normalize_product, image_host_allowed
from .search import _rows, generate_affiliate, ApiError
from .task_copy import task_description, task_headline

LANGS = ('ru', 'en', 'pt', 'es', 'fr', 'he')
CHECK = {
    'ru': 'Перед покупкой сверьте выбранный вариант и условия у продавца.',
    'en': 'Before buying, check the selected option and terms in the seller listing.',
    'pt': 'Antes de comprar, confira a opção escolhida e as condições do vendedor.',
    'es': 'Antes de comprar, revisa la opción elegida y las condiciones del vendedor.',
    'fr': 'Avant l’achat, vérifiez la variante choisie et les conditions du vendeur.',
    'he': 'לפני הקנייה יש לבדוק את האפשרות שנבחרה ואת תנאי המוכר.',
}


def _seed(key, query, groups, category, market, theme, names):
    return {'key': key, 'query': query, 'groups': groups, 'category': category,
            'market': market, 'theme': theme, 'names': dict(zip(LANGS, names))}


# Task types are constrained to words actually present in the returned title.
SEEDS = [
    _seed('inspection_mirror', 'telescopic inspection mirror tool', (('inspection',), ('mirror',)), 'Инструменты','US','blue', ('Зеркало для осмотра','Inspection mirror','Espelho de inspeção','Espejo de inspección','Miroir d’inspection','מראת בדיקה')),
    _seed('magnetic_pickup', 'flexible magnetic pickup tool', (('magnetic','magnet'), ('pickup','pick')), 'Инструменты','BR','lavender', ('Магнитный захват','Magnetic pickup tool','Pegador magnético','Recogedor magnético','Outil de ramassage magnétique','כלי איסוף מגנטי')),
    _seed('screw_extractor', 'left hand screw extractor tool', (('screw','screws'), ('extractor','extractors')), 'Инструменты','MX','blue', ('Экстрактор винтов','Screw extractor','Extrator de parafusos','Extractor de tornillos','Extracteur de vis','חולץ ברגים')),
    _seed('sewing_seam_guide', 'magnetic seam guide sewing machine', (('sewing',), ('seam',), ('guide',)), 'Дом','FR','rose', ('Направитель шва','Sewing seam guide','Guia de costura','Guía de costura','Guide de couture','מכוון תפר')),
    _seed('watch_hand_tool', 'watch hand setting tool', (('watch',), ('hand','hands'), ('setting',)), 'Инструменты','IL','sand', ('Инструмент для установки стрелок часов','Watch hand setting tool','Ferramenta para ponteiros de relógio','Herramienta para agujas de reloj','Outil pour aiguilles de montre','כלי להתקנת מחוגי שעון')),
    _seed('irrigation_punch', 'drip irrigation hole punch tool', (('irrigation',), ('punch',)), 'На природе','BR','sand', ('Пробойник для полива','Irrigation punch','Perfurador para irrigação','Perforador de riego','Perforateur d’irrigation','מחורר לצינור השקיה')),
    _seed('reed_trimmer', 'saxophone reed trimmer tool', (('saxophone',), ('reed','reeds'), ('trimmer',)), 'Инструменты','US','rose', ('Триммер для трости саксофона','Saxophone reed trimmer','Cortador de palheta de saxofone','Cortador de cañas de saxofón','Coupe-anche de saxophone','קוצץ עלים לסקסופון')),
    _seed('aquarium_tweezers', 'aquarium curved aquascaping tweezers', (('aquarium',), ('tweezers',)), 'Питомцы','FR','blue', ('Пинцет для аквариума','Aquarium tweezers','Pinça para aquário','Pinzas para acuario','Pince pour aquarium','פינצטה לאקווריום')),
    _seed('keyboard_switch_opener', 'mechanical keyboard switch opener', (('keyboard',), ('switch','switches'), ('opener','opening')), 'Техника','IL','lavender', ('Открывалка переключателей клавиатуры','Keyboard switch opener','Abridor de switches de teclado','Abridor de interruptores de teclado','Ouvre-switch pour clavier','פותחן למתגי מקלדת')),
    _seed('bearing_puller', 'small bearing puller removal tool', (('bearing','bearings'), ('puller',)), 'Инструменты','MX','blue', ('Съёмник подшипника','Bearing puller','Extrator de rolamento','Extractor de rodamientos','Extracteur de roulement','חולץ מסבים')),
    _seed('cable_fish_tape', 'cable fish tape puller wiring', (('cable','wire','wiring'), ('fish',), ('tape',)), 'Инструменты','BR','sand', ('Протяжка для кабеля','Cable fish tape','Passa-fio para cabos','Pasacables de cinta','Tire-fil pour câble','סרט להשחלת כבלים')),
    _seed('button_hook', 'button hook dressing aid', (('button',), ('hook',)), 'Уход','IL','rose', ('Крючок для застёгивания пуговиц','Button hook','Gancho para abotoar','Gancho para abotonar','Crochet pour boutonner','וו לכפתור בגדים')),
    _seed('bead_spinner', 'manual bead spinner tool', (('bead','beads'), ('spinner',)), 'Дом','FR','lavender', ('Спиннер для бисера','Bead spinner','Enfiador giratório de miçangas','Ensartador giratorio de cuentas','Enfile-perles rotatif','מכשיר מסתובב להשחלת חרוזים')),
    _seed('fly_tying_vise', 'fly tying vise vice tool', (('fly',), ('tying',), ('vise','vice')), 'На природе','US','sand', ('Тиски для вязания мушек','Fly tying vise','Morsa para atar moscas','Torno para atar moscas','Étau pour montage de mouches','מלחציים לקשירת זבובים')),
]


class AutonomousError(Exception):
    pass


class DailyError(Exception):
    pass


def _words(value):
    return set(re.findall(r'[a-z0-9]+', value.casefold()))


def _headline(value):
    words = value[:70].split()
    if len(words) < 2:
        return [words[0] if words else 'AliExpress', 'AliExpress']
    split = max(1, len(words) // 2)
    return [' '.join(words[:split]), ' '.join(words[split:])]


def _import_tools_modules(site_root):
    import sys as _sys
    tools_dir = str(Path(site_root) / 'tools')
    if tools_dir not in _sys.path:
        _sys.path.insert(0, tools_dir)
    import ai_seo
    import copy_originality
    return ai_seo, copy_originality


def _load_catalog_copy_corpus(products, translations, site_root):
    try:
        _, copy_originality = _import_tools_modules(site_root)
    except Exception:
        return None
    overrides = {}
    ov_path = Path(site_root) / 'tools/seo_overrides.json'
    if ov_path.is_file():
        try:
            overrides = json.loads(ov_path.read_text(encoding='utf-8')).get('routes') or {}
        except Exception:
            overrides = {}
    return copy_originality.build_catalog_copy_corpus(
        products, translations, extra_routes=overrides,
    )


_SELLER_NOISE_RE = re.compile(
    r'(?:\[[^\]]*\]|\([^)]*\)|\b(?:free\s*shipping|hot\s*sale|new\s*arrival|202\d|dropshipping|wholesale|best\s*seller|high\s*quality|gift\s*for)\b)',
    re.IGNORECASE,
)

_SEED_CHECK_ANGLES = {
    'ru': (
        'Точные размеры, совместимость и содержимое набора смотрите в выбранной опции у продавца.',
        'Перед оформлением сверьте выбранный вариант, комплектацию и реальные фотографии в карточке товара.',
        'Назначение, аксессуары и детали сборки зависят от варианта — проверьте описание на AliExpress.',
    ),
    'en': (
        'Review exact sizing, included parts, and compatibility under the chosen option on AliExpress.',
        'Compare the selected kit thumbnail and seller photos carefully before confirming checkout.',
        'Check material finish, dimensions, and option contents in the AliExpress listing before ordering.',
    ),
    'pt': (
        'Confira dimensões exatas, compatibilidade e itens incluídos na variação selecionada no AliExpress.',
        'Compare as fotos reais do vendedor e os componentes da opção escolhida antes de fechar o pedido.',
        'Verifique medidas, encaixe e conteúdo da embalagem diretamente na página do produto.',
    ),
    'es': (
        'Revisa medidas exactas, compatibilidad y piezas incluidas dentro de la opción elegida en AliExpress.',
        'Compara las fotografías del vendedor y el detalle de cada variante antes de confirmar tu pedido.',
        'Verifica dimensiones, ajuste y contenido del paquete directamente en la publicación del vendedor.',
    ),
    'fr': (
        'Vérifiez les dimensions exactes, la compatibilité et les accessoires inclus selon la variante sur AliExpress.',
        'Comparez les photos du vendeur et le détail du coffret choisi avant de valider votre commande.',
        'Contrôlez le format, les matières et le contenu de l’option sélectionnée sur la fiche produit.',
    ),
    'he': (
        'בדקו מידות מדויקות, התאמה ותכולת הערכה לפי האפשרות שתבחרו בעמוד המוצר.',
        'השוו בין תמונות המוכר המקוריות למפרט של הדגם המסומן לפני ההזמנה.',
        'ודאו את החומרים, הגודל והאביזרים המצורפים בעמוד המוצר ב־AliExpress.',
    ),
}


def _sanitize_deterministic_copy(record_item, translated, candidate, site_root, catalog_corpus, copy_originality):
    """Avoid verbatim English seller title mirroring and duplicate template endings when AI is unavailable."""
    source_title = str(candidate.get('title') or record_item.get('sourceTitle') or '')
    bundle = {
        'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']},
        **{lang: dict(translated[lang]) for lang in LANGS if lang != 'ru' and lang in translated},
    }
    pid = str(record_item.get('id') or '')
    variant_idx = int(hashlib.sha256(pid.encode('utf-8')).hexdigest()[:2], 16) % 3

    # 1. Clean raw English seller title if queued item came without template task
    if record_item.get('sourceTask') == 'seller_title' and source_title:
        en_entry = bundle.get('en')
        if en_entry and copy_originality.check_source_title_mirroring({'en': en_entry}, source_title):
            cleaned = _SELLER_NOISE_RE.sub(' ', en_entry.get('name', ''))
            words = [w for w in cleaned.split() if w.lower() not in {'for', 'with', 'and', 'to', 'in', 'of'}]
            # Keep compact informative noun core distinct from raw long AliExpress title
            compact = ' '.join(words[:4]).strip(' -,:;|/')
            if not compact or len(compact) < 4 or copy_originality.check_source_title_mirroring(
                {'en': {'name': compact, 'headline': en_entry.get('headline', []), 'description': ''}},
                source_title,
            ):
                compact = f"{words[-2]} {words[-1]}".strip() if len(words) >= 2 else (words[0] if words else 'Compact tool')
            en_entry['name'] = compact[:56]

    # 2. If catalog_corpus shows duplicate static description, swap the closing buyer check sentence cleanly
    if catalog_corpus and copy_originality.check_catalog_similarity(bundle, catalog_corpus):
        for lang in LANGS:
            loc = bundle.get(lang)
            if not isinstance(loc, dict):
                continue
            desc = str(loc.get('description') or '').strip()
            std_check = CHECK.get(lang, '')
            if std_check and desc.endswith(std_check):
                stem = desc[:-len(std_check)].strip()
                angle = _SEED_CHECK_ANGLES[lang][variant_idx]
                loc['description'] = f'{stem} {angle}'.strip() if stem else angle

    new_record = {**record_item, **bundle['ru'], 'details': bundle['ru']['description']}
    new_trans = {lang: bundle[lang] for lang in LANGS if lang != 'ru' and lang in bundle}
    return new_record, new_trans


def _maybe_ai_enrich(record_item, translated, candidate, site_root, *, catalog_corpus=None, snippet_fetcher=None):
    """Optionally enhance 6-language copy with free AI when keys are set, strictly gated by check_texts."""
    ai_seo = copy_originality = None
    try:
        ai_seo, copy_originality = _import_tools_modules(site_root)
    except Exception:
        return record_item, translated

    base = {
        'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']},
        **translated,
    }
    if ai_seo.has_ai_provider():
        try:
            enriched, provider = ai_seo.enrich_product_copy(
                {
                    'category': record_item.get('category', ''),
                    'market': record_item.get('sourceMarket', 'US'),
                    'source_title': candidate.get('title', record_item.get('sourceTitle', '')),
                },
                base,
                catalog_corpus=catalog_corpus,
                snippet_fetcher=snippet_fetcher,
            )
            if enriched and provider != 'deterministic' and not provider.startswith('fallback:') and not provider.startswith('deterministic-after-lint'):
                record_item = {**record_item, **enriched['ru'], 'details': enriched['ru']['description']}
                translated = {lang: enriched[lang] for lang in LANGS if lang != 'ru' and lang in enriched}
                return record_item, translated
        except Exception:
            pass

    return _sanitize_deterministic_copy(record_item, translated, candidate, site_root, catalog_corpus, copy_originality)


def _matches(seed, title):
    words = _words(title)
    # A replacement/part with the target words is not the complete tool.
    # This is deliberately conservative; unknown semantic fit remains unknown.
    parts = {'replacement', 'refill', 'spare', 'part', 'parts', 'accessory', 'accessories',
             'case', 'cover', 'sleeve', 'casing', 'adapter', 'attachment', 'battery',
             'batteries', 'charger', 'sticker', 'stickers', 'decal', 'decals'}
    return not (words & parts) and all(any(word in words for word in group) for group in seed['groups'])


def _source_images(raw, primary):
    images = [primary] if primary else []
    value = raw.get('product_small_image_urls') if isinstance(raw, dict) else None
    if isinstance(value, dict):
        value = value.get('string', [])
    if isinstance(value, str):
        value = [value]
    if isinstance(value, list):
        images.extend(value[:8])
    result = []
    for image in images:
        if not isinstance(image, str):
            continue
        try:
            parsed = urlsplit(image)
            if (parsed.scheme != 'https' or not parsed.hostname
                    or not image_host_allowed(parsed.hostname) or parsed.username is not None
                    or parsed.password is not None or parsed.port not in (None, 443)
                    or parsed.fragment or '\\' in image):
                continue
            if image not in result:
                result.append(image)
        except (TypeError, ValueError):
            continue
    return result


def discover(call, existing, count, now, *, seeds=None):
    """Compare API results, confirm exact IDs in a market, and request exact links."""
    if (isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 3
            or not isinstance(existing, list) or not callable(call)
            or not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None):
        raise AutonomousError('discovery_input_invalid')
    if count == 0:
        return []
    task_seeds = list(SEEDS if seeds is None else seeds)
    if not task_seeds:
        return []
    utc_now = now.astimezone(timezone.utc)
    offset = utc_now.date().toordinal() % len(task_seeds)
    task_seeds = task_seeds[offset:] + task_seeds[:offset]
    known_ids = {str(item['sourceProductId']) for item in existing if isinstance(item, dict) and item.get('sourceProductId')}
    known_titles = {str(item[key]).strip().casefold() for item in existing if isinstance(item, dict)
                    for key in ('name','sourceTitle') if item.get(key)}
    known_models = {item.get('sourceModelKey') for item in existing if isinstance(item, dict) and item.get('sourceModelKey')}
    chosen = []
    for task in task_seeds:
        try:
            rows = _rows(call(QUERY, {'keywords': task['query'], 'target_currency': 'USD', 'target_language': 'EN',
                                      'ship_to_country': task['market'], 'page_size': '20', 'page_no': '1',
                                      'tracking_id': 'default'}), QUERY)
            query = {}
            for raw in rows[:20]:
                try:
                    item = normalize_product(raw, task['market'], QUERY, utc_now.isoformat())
                    item['image_urls'] = _source_images(raw, item.get('image_url'))
                    if item['product_id'] not in known_ids and item['title'].strip().casefold() not in known_titles:
                        query[item['product_id']] = item
                except (ValueError, TypeError):
                    continue
            if not query:
                continue
            details = _rows(call(DETAIL, {'product_ids': ','.join(sorted(query)), 'country': task['market'],
                                        'target_currency': 'USD', 'target_language': 'EN', 'tracking_id': 'default'}), DETAIL)
            eligible = []
            for raw in details[:20]:
                try:
                    item = normalize_product(raw, task['market'], DETAIL, utc_now.isoformat())
                    previous = query.get(item['product_id'])
                    if not previous or not _matches(task, item['title']):
                        continue
                    if item['title'].strip().casefold() in known_titles or (item.get('model_key') and item['model_key'] in known_models):
                        continue
                    item['image_url'] = item.get('image_url') or previous.get('image_url')
                    item['image_urls'] = list(dict.fromkeys(_source_images(raw, item['image_url']) + previous.get('image_urls', [])))[:8]
                    if not item['image_urls']:
                        continue
                    score = len(_words(task['query']) & _words(item['title']))
                    eligible.append((-score, item['product_id'], item))
                except (ValueError, TypeError):
                    continue
            for _, _, item in sorted(eligible, key=lambda value: (value[0], value[1])):
                try:
                    affiliate = generate_affiliate(call, item)
                except (ApiError, ValueError, TypeError, KeyError):
                    continue
                item['affiliate_url'] = affiliate
                item['task'] = task
                chosen.append(item)
                known_ids.add(item['product_id'])
                known_titles.add(item['title'].strip().casefold())
                if item.get('model_key'):
                    known_models.add(item['model_key'])
                break
        except (ApiError, ValueError, KeyError, TypeError):
            continue
        if len(chosen) >= count:
            break
    return chosen


def build_record(candidate):
    """Build six honest labels only after the actual seller title matches task."""
    if not isinstance(candidate, dict):
        raise AutonomousError('candidate_invalid')
    task = candidate.get('task')
    if task is not None and (task not in SEEDS or not _matches(task, str(candidate.get('title', '')))):
        raise AutonomousError('task_title_mismatch')
    if task is None:
        from .publisher import CATEGORIES, source_content
        if candidate.get('category') not in CATEGORIES:
            raise AutonomousError('candidate_category_invalid')
        localized = source_content(candidate)
        for lang, content in localized.items():
            content['headline'] = task_headline('seller_title', lang, candidate['category'])
        task = {'names': {lang: localized[lang]['name'] for lang in LANGS}, 'category': candidate['category'],
                'market': candidate['market'], 'theme': 'lavender', 'key': 'seller_title'}
    product_id = candidate.get('product_id')
    if (not isinstance(product_id, str) or not re.fullmatch(r'[1-9][0-9]{0,31}', product_id)
            or candidate.get('detail_url') != f'https://www.aliexpress.com/item/{product_id}.html'
            or not candidate.get('affiliate_url') or not candidate.get('image_url')):
        raise AutonomousError('candidate_identity_invalid')
    if task['key'] != 'seller_title':
        localized = {}
        for lang in LANGS:
            name = task['names'][lang]
            localized[lang] = {'name': name, 'headline': task_headline(task['key'], lang),
                               'description': task_description(task['key'], lang)}
    internal = 'auto-' + product_id
    record = {'id': internal, **localized['ru'], 'category': task['category'],
              'image': f'assets/images/{internal}.webp', 'original': f'assets/originals/{internal}.webp',
              'imageNote': 'Изображение подготовлено из фотографии продавца. Исходная фотография доступна для сравнения.',
              'affiliateUrl': candidate['affiliate_url'], 'sourceUrl': candidate['detail_url'],
              'sourceProductId': product_id, 'sourceDetailUrl': candidate['detail_url'],
              'sourceTitle': candidate['title'], 'sourceImageUrl': candidate['image_url'],
              'sourceModelKey': candidate.get('model_key'), 'sourceMarket': task['market'],
              'sourceTask': task['key'], 'demo': False, 'theme': task['theme'],
              'scale': 0.85, 'rotation': 0, 'details': localized['ru']['description'], 'facts': []}
    return record, {lang: localized[lang] for lang in LANGS if lang != 'ru'}


def refresh_queued(call, candidate, now):
    """Recheck a queued exact ID and affiliate link against current API data."""
    if not isinstance(candidate, dict):
        raise AutonomousError('queued_candidate_invalid')
    product_id = candidate.get('product_id')
    if not isinstance(product_id, str) or not re.fullmatch(r'[1-9][0-9]{0,31}', product_id):
        raise AutonomousError('queued_candidate_invalid')
    markets = candidate.get('markets')
    if not isinstance(markets, dict) or not markets:
        raise AutonomousError('queued_market_unknown')
    for market in markets:
        try:
            rows = _rows(call(DETAIL, {'product_ids': product_id, 'country': market, 'target_currency': 'USD',
                                      'target_language': 'EN', 'tracking_id': 'default'}), DETAIL)
            for raw in rows[:20]:
                item = normalize_product(raw, market, DETAIL, now.astimezone(timezone.utc).isoformat())
                if item['product_id'] != product_id or not item.get('image_url'):
                    continue
                item['image_urls'] = _source_images(raw, item['image_url'])
                if not item['image_urls']:
                    continue
                item['affiliate_url'] = generate_affiliate(call, item)
                item['category'] = candidate.get('category')
                item['market'] = market
                item['task'] = next((task for task in SEEDS if task['category'] == item['category'] and _matches(task, item['title'])), None)
                return item
        except (ApiError, ValueError, KeyError, TypeError):
            continue
    raise AutonomousError('queued_source_unconfirmed')


def mask_usable(image):
    """Conservative shape gate, not a guarantee of product accuracy."""
    from PIL import Image
    if not isinstance(image, Image.Image):
        return False
    alpha = image.convert('RGBA').getchannel('A')
    histogram = alpha.histogram()
    fraction = sum(histogram[128:]) / max(1, image.width * image.height)
    if fraction < 0.025 or fraction > 0.85:
        return False
    sample = alpha.resize((96, 96), Image.Resampling.BOX)
    values = sample.tobytes()
    foreground = {i for i, value in enumerate(values) if value >= 100}
    if not foreground:
        return False
    remaining = set(foreground)
    parts = []
    while remaining:
        first = remaining.pop()
        queue = deque([first])
        size, xs, ys = 0, [], []
        while queue:
            point = queue.popleft()
            size += 1
            x, y = point % 96, point // 96
            xs.append(x)
            ys.append(y)
            for neighbor in ((point-1 if x else -1), (point+1 if x<95 else -1),
                             (point-96 if y else -1), (point+96 if y<95 else -1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        parts.append((size, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    parts.sort(reverse=True)
    if parts[0][0] / len(foreground) < 0.5:
        return False
    # A solid, long strip beside the product is a seller's step-by-step panel, not part of it.
    for size, width, height in parts[1:]:
        if (size / len(foreground) > 0.06 and size / (width * height) > 0.85
                and max(width, height) / min(width, height) >= 2.5):
            return False
    return True


def ocr_poster(tsv):
    if not isinstance(tsv, str):
        raise DailyError('ocr_unavailable')
    words = []
    for line in tsv.splitlines()[1:]:
        cols = line.split('\t')
        if len(cols) < 12:
            continue
        try:
            confidence = float(cols[10])
        except ValueError:
            continue
        text = ''.join(ch for ch in cols[11] if ch.isalnum())
        if confidence >= 50 and len(text) >= 2:
            words.append(text)
    return len(words) >= 3 or (len(words) >= 2 and sum(map(len, words)) >= 16)


def _check_ocr(path):
    try:
        result = subprocess.run(['tesseract', str(path), 'stdout', '--psm', '11', 'tsv'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=25)
        if result.returncode != 0:
            raise ValueError()
        return ocr_poster(result.stdout.decode('utf-8', errors='replace'))
    except (OSError, ValueError, subprocess.SubprocessError):
        raise DailyError('ocr_unavailable') from None


def _image_bytes(url):
    import requests
    if not _source_images({}, url):
        raise DailyError('image_url_invalid')
    try:
        response = requests.get(url, headers={'Referer': 'https://www.aliexpress.com/'},
                                timeout=(5, 20), allow_redirects=False, stream=True)
        try:
            if response.status_code != 200 or not response.headers.get('Content-Type', '').lower().startswith('image/'):
                raise ValueError()
            out = bytearray()
            for block in response.iter_content(64 * 1024):
                out.extend(block)
                if len(out) > 10_000_000:
                    raise ValueError()
            return bytes(out)
        finally:
            response.close()
    except Exception:
        raise DailyError('source_image_unavailable') from None


def _pixel_hash(image):
    rgba = image.convert('RGBA')
    h = hashlib.sha256(f'{rgba.width}x{rgba.height}:'.encode())
    h.update(rgba.tobytes())
    return h.hexdigest()


PHOTOS_PER_PRODUCT = 3   # every new product gets three cut-out photos (main + two more views)
VIEW_REPEAT = 12         # dHash distance at or below which two cut-outs count as the same view
VIEW_MIN_SIDE = 400      # smaller seller photos give blurry cut-outs
MAX_ATTEMPTS = 30        # candidates tried per run; three clean views are rarer than one
SEARCH_BUDGET_SECONDS = 40 * 60   # stop looking in time for the build, push and deploy
LEASE_SECONDS = 75 * 60
CUT_MODEL = 'isnet-general-use'   # cleaner edges and less haze than u2net on seller photos


def _dhash(image):
    return int(image_studio.compute_dhash(image), 16)


def _on_white(image):
    from PIL import Image
    canvas = Image.new('RGB', image.size, 'white')
    canvas.paste(image, mask=image.getchannel('A'))
    return canvas


def _drop_specks(cutout, keep=0.015):
    """Remove what the matting leaves around the product: faint haze, ghost logos, loose bits of background.

    Pixels the model is unsure about (low alpha) are cleared, then only the solid parts of the product are kept
    (any part of at least 1.5% of the product), and everything farther than a few pixels from them is cleared."""
    from PIL import Image, ImageChops, ImageFilter
    alpha = cutout.getchannel('A').point(lambda a: 0 if a < 24 else a)
    parts = _parts(alpha)
    if not parts:
        return cutout
    total = sum(len(part) for part in parts)
    mask = Image.new('L', (128, 128), 0)
    for part in parts:
        if len(part) >= keep * total:
            for point in part:
                mask.putpixel((point % 128, point // 128), 255)
    mask = mask.filter(ImageFilter.MaxFilter(5)).resize(cutout.size, Image.Resampling.BILINEAR)
    mask = mask.point(lambda v: 255 if v >= 128 else 0)
    cleaned = cutout.copy()
    cleaned.putalpha(ImageChops.multiply(alpha, mask))
    return cleaned


def _major_parts(cutout):
    """How many separate big objects the cut-out holds (each at least 10% of it): a collage of zoomed panels or a
    call-out circle shows up as more objects than the product's own main photo."""
    parts = _parts(cutout.getchannel('A'))
    total = sum(len(part) for part in parts)
    return sum(1 for part in parts if len(part) >= 0.1 * total)


def _parts(alpha):
    """Connected solid regions of an alpha mask on a 128 x 128 grid, as lists of grid indices."""
    from PIL import Image
    values = alpha.resize((128, 128), Image.Resampling.BOX).tobytes()
    remaining = {i for i, value in enumerate(values) if value >= 100}
    parts = []
    while remaining:
        first = remaining.pop()
        queue, part = deque([first]), [first]
        while queue:
            point = queue.popleft()
            x, y = point % 128, point // 128
            for neighbor in ((point-1 if x else -1), (point+1 if x < 127 else -1),
                             (point-128 if y else -1), (point+128 if y < 127 else -1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
                    part.append(neighbor)
        parts.append(part)
    return parts



def _light_share(cutout):
    """Share of the solid cut-out that is near-white neutral: high when a slab of the photo's backdrop survived the cut
    (a card, an arch, a table top), or when the product itself is white."""
    from PIL import Image
    small = cutout.copy()
    small.thumbnail((256, 256), Image.Resampling.BOX)
    solid = light = 0
    for r, g, b, a in (small.get_flattened_data() if hasattr(small, 'get_flattened_data') else small.getdata()):
        if a >= 200:
            solid += 1
            if min(r, g, b) >= 232 and max(r, g, b) - min(r, g, b) <= 12:
                light += 1
    return 1.0 if solid == 0 else light / solid


def _has_text(canvas, stage, name):
    """OCR of the cut-out on white, upright and turned (packaging text often runs sideways or upside down)."""
    picture = _on_white(canvas)
    for turn in (0, 90, 180, 270):
        check = stage / f'{name}-r{turn}.png'
        (picture.rotate(turn, expand=True) if turn else picture).save(check, 'PNG')
        if _check_ocr(check):
            return True
    return False


def _studio(cutout):
    """FLUXIXO studio framing: clean edges, tight trim, tonal balance, and subtle grounding shadow."""
    return image_studio.compose_studio_frame(
        cutout,
        canvas_size=1254,
        max_box=890,
        normalize_tonality=True,
        add_contact_shadow=True,
    )


def _default_media_preparer():
    try:
        from PIL import Image
        from rembg import remove, new_session
        session = new_session(CUT_MODEL)
    except Exception:
        raise DailyError('image_processor_unavailable') from None
    def prepare(candidate, internal_id, stage, *, perceptual_index=None):
        """Main photo plus two more views of the same listing, all cut out; fewer than three means another product."""
        urls = candidate.get('image_urls') or [candidate.get('image_url')]
        main, views, kept, sources, main_light, main_parts = None, [], [], set(), 0.0, 1
        for index, url in enumerate(urls[:9]):
            if main is not None and len(views) >= PHOTOS_PER_PRODUCT - 1:
                break
            try:
                raw = _image_bytes(url)
                digest = hashlib.sha256(raw).hexdigest()
                if digest in sources:
                    continue
                sources.add(digest)
                with Image.open(BytesIO(raw)) as value:
                    if value.width < 1 or value.height < 1 or value.width * value.height > 25_000_000:
                        continue
                    value.load()
                    original = value.convert('RGBA')
                if min(original.size) < VIEW_MIN_SIDE:
                    continue
                source_hashes = image_studio.compute_perceptual_hashes(original)
                if perceptual_index:
                    is_dup, _ = image_studio.is_perceptually_duplicate(source_hashes, perceptual_index)
                    if is_dup:
                        continue
                source = stage / f'{internal_id}-source-{index}.png'
                original.save(source, 'PNG')
                poster = _check_ocr(source)
                if poster and main is None and len(views) >= PHOTOS_PER_PRODUCT - 1:
                    continue  # the main photo itself must be a clean shot
                work = original
                if max(work.size) > 1600:
                    work = work.copy()
                    work.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                cutout = _drop_specks(remove(work, session=session).convert('RGBA'))
                if not cutout.getbbox() or not mask_usable(cutout):
                    continue
                if main is not None or poster:
                    # Extra views keep only sizeable parts: no seller logo, no stray dimension lines.
                    cutout = _drop_specks(cutout, keep=0.06)
                canvas = _studio(cutout)
                if main is not None or poster:
                    # Extra views: no leftover backdrop and no words anywhere on the cut-out (boxes, logos,
                    # captions). A photo with text may still give a clean view once its background is cut away.
                    # A white product is allowed to be white; a backdrop slab makes a view much lighter than the main.
                    if (_light_share(canvas) > max(0.3, main_light + 0.2) or _major_parts(canvas) > main_parts
                            or _has_text(canvas, stage, f'{internal_id}-check-{index}')):
                        continue
                cut_hashes = image_studio.compute_perceptual_hashes(canvas)
                if perceptual_index:
                    is_dup, _ = image_studio.is_perceptually_duplicate(cut_hashes, perceptual_index)
                    if is_dup:
                        continue
                fingerprint = _dhash(_on_white(canvas))
                if any(bin(fingerprint ^ other).count('1') <= VIEW_REPEAT for other in kept):
                    continue
                kept.append(fingerprint)
                if main is None and not poster:
                    image_path = stage / f'{internal_id}-prepared.webp'
                    original_path = stage / f'{internal_id}-original.webp'
                    canvas.save(image_path, 'WEBP', quality=92)
                    original.save(original_path, 'WEBP', quality=88)
                    main_light, main_parts = _light_share(canvas), _major_parts(canvas)
                    main = {
                        'image': image_path,
                        'original': original_path,
                        'source_sha256': digest,
                        'pixel_sha256': _pixel_hash(original),
                        'source_url': url,
                        'image_dhash': cut_hashes['dhash'],
                        'image_ahash': cut_hashes['ahash'],
                        'image_aspect': cut_hashes['aspect'],
                        'source_dhash': source_hashes['dhash'],
                        'source_ahash': source_hashes['ahash'],
                        'source_aspect': source_hashes['aspect'],
                    }
                elif len(views) < PHOTOS_PER_PRODUCT - 1:
                    view_path = stage / f'{internal_id}-view-{len(views) + 2}.webp'
                    canvas.save(view_path, 'WEBP', quality=90)
                    views.append(view_path)
                else:
                    kept.pop()
            except DailyError as error:
                if str(error) == 'ocr_unavailable':
                    raise
            except Exception:
                continue
        if main is None or len(views) < PHOTOS_PER_PRODUCT - 1:
            raise DailyError('visual_quality_failed')
        main['views'] = views
        return main
    return prepare


def _old_image_hashes(products, dist):
    from PIL import Image
    result = set()
    for product in products:
        for name in ('sourceImageSha256', 'sourcePixelSha256'):
            if isinstance(product.get(name), str):
                result.add(product[name])
        relative = product.get('original')
        if not isinstance(relative, str):
            continue
        path = (dist / relative).resolve()
        if not path.is_relative_to(dist.resolve()) or not path.is_file() or path.stat().st_size > 10_000_000:
            continue
        try:
            raw = path.read_bytes()
            result.add(hashlib.sha256(raw).hexdigest())
            with Image.open(BytesIO(raw)) as image:
                if image.width * image.height <= 25_000_000:
                    image.load()
                    result.add(_pixel_hash(image))
        except Exception:
            continue
    return result


def _atomic_bytes(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.daily-', suffix='.tmp', delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def _media_accepts_perceptual(fn):
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD or p.name == 'perceptual_index'
        for p in sig.parameters.values()
    )


def _extract_media_perceptual(media):
    """Read dHash/aHash descriptors from media dict or image file; returns None on synthetic test bytes."""
    from PIL import Image
    out = {}
    if isinstance(media.get('image_dhash'), str) and isinstance(media.get('image_ahash'), str):
        out['image'] = {
            'dhash': media['image_dhash'],
            'ahash': media['image_ahash'],
            **({'aspect': media['image_aspect']} if media.get('image_aspect') else {}),
        }
    else:
        try:
            with Image.open(media['image']) as img:
                img.load()
                out['image'] = image_studio.compute_perceptual_hashes(img)
        except Exception:
            pass
    if isinstance(media.get('source_dhash'), str) and isinstance(media.get('source_ahash'), str):
        out['original'] = {
            'dhash': media['source_dhash'],
            'ahash': media['source_ahash'],
            **({'aspect': media['source_aspect']} if media.get('source_aspect') else {}),
        }
    elif media.get('original'):
        try:
            with Image.open(media['original']) as orig_img:
                orig_img.load()
                out['original'] = image_studio.compute_perceptual_hashes(orig_img)
        except Exception:
            pass
    return out


def accumulate(*, count, site_root, dist, reserve_dir, ledger_path, now=None,
               discover_fn=None, media_fn=None, validation_run_id=None, queue_store=None, refresh_fn=None,
               enforce_unique_copy=None, snippet_fetcher=None):
    """Prepare full batch before mutation; catalog and ledger commit together later."""
    from .daily_ledger import read_ledger, verify_catalog, remaining, record, atomic_write, utc_day
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 3:
        raise DailyError('count_invalid')
    if validation_run_id is not None and count != 1:
        raise DailyError('validation_requires_one')
    if count == 0:
        return {'added': 0}
    instant = now or datetime.now(timezone.utc)
    day = utc_day(instant)
    site_root, dist, reserve_dir, ledger_path = map(Path, (site_root, dist, reserve_dir, ledger_path))
    catalog_path, translations_path = dist / 'js/catalog.js', site_root / 'tools/i18n_data.json'
    try:
        original_catalog = catalog_path.read_bytes()
        original_i18n = translations_path.read_bytes()
        original_ledger = ledger_path.read_bytes()
        catalog = json.loads(original_catalog.decode('utf-8').split('=', 1)[1].strip().removesuffix(';'))
        translations = json.loads(original_i18n)
        if not isinstance(translations.get('products'), dict):
            raise ValueError()
        ledger = read_ledger(ledger_path)
        verify_catalog(ledger, catalog)
        if validation_run_id is None:
            needed = remaining(ledger, day, count)
        else:
            from .daily_ledger import remaining_validation, SEED_DAY
            validation_day = SEED_DAY if validation_run_id in ledger['validation_runs'] else day
            needed = remaining_validation(ledger, validation_day, validation_run_id, now=now)
    except Exception as error:
        raise DailyError(getattr(error, 'code', 'daily_input_invalid')) from None
    if needed == 0:
        return {'added': 0, 'validation_existing': validation_run_id is not None}
    if (instant.astimezone(timezone.utc) + timedelta(minutes=26)).date().isoformat() != day:
        raise DailyError('utc_day_end_window')
    api_holder = []
    def get_api():
        if not api_holder:
            from .search import AliClient
            api_holder.append(AliClient())
        return api_holder[0]
    if discover_fn is None:
        discover_fn = lambda existing, amount, when: discover(get_api(), existing, amount, when)
    if refresh_fn is None:
        refresh_fn = lambda entry, when: refresh_queued(get_api(), entry, when)
    if queue_store is None:
        queue_file = ledger_path.parent / 'fluxixo_ai.sqlite3'
        if queue_file.is_file():
            from .store import Store
            queue_store = Store(queue_file)
    if media_fn is None:
        media_holder = []
        def media_fn(candidate, internal_id, stage, *, perceptual_index=None):
            if not media_holder:
                media_holder.append(_default_media_preparer())
            return media_holder[0](candidate, internal_id, stage, perceptual_index=perceptual_index)
    strict_copy = (
        str(os.environ.get('FLUXIXO_STRICT_COPY', '')).strip().lower() in ('1', 'true', 'yes')
        if enforce_unique_copy is None else bool(enforce_unique_copy)
    )
    old = catalog['products']
    used_hashes = _old_image_hashes(old, dist)
    perceptual_index = image_studio.load_catalog_perceptual_index(
        old, dist, cache_path=site_root / 'tools' / '.image_hash_cache.json',
    )
    catalog_corpus = _load_catalog_copy_corpus(old, translations, site_root)
    pass_perceptual = _media_accepts_perceptual(media_fn)
    exclusions = []
    prepared = []
    attempts = 0
    owner = 'daily-' + (os.environ.get('GITHUB_RUN_ID') or 'run')
    queue_batch = []
    if queue_store is not None:
        # Cutting three photos per product takes longer; the claim must outlive the build and the push,
        # but a lease may not cross midnight (the store refuses that).
        midnight = datetime.combine(instant.astimezone(timezone.utc).date() + timedelta(days=1), datetime.min.time(), timezone.utc)
        lease = max(300, min(LEASE_SECONDS, int((midnight - instant).total_seconds()) - 120))
        claims = queue_store.claim(day, owner, needed, lease_seconds=lease, now=instant)
        for claim in claims:
            try:
                refreshed = refresh_fn(claim['candidate'], instant)
                refreshed['_queue_claim'] = claim
                queue_batch.append(refreshed)
            except Exception:
                queue_store.release_claim(claim['claim_id'], owner, catalog_unchanged=True, now=instant)
    reserve_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.daily-stage-', dir=reserve_dir) as folder:
        stage = Path(folder).resolve()
        if not stage.is_relative_to(reserve_dir.resolve()):
            raise DailyError('staging_invalid')
        deadline = time.monotonic() + SEARCH_BUDGET_SECONDS
        while len(prepared) < needed and attempts < MAX_ATTEMPTS and time.monotonic() < deadline:
            if queue_batch:
                batch, queue_batch = queue_batch, []
            else:
                batch = discover_fn(old + exclusions + [x[0] for x in prepared], needed - len(prepared), instant)
            if not batch:
                break
            progress = False
            for candidate in batch:
                if len(prepared) >= needed or attempts >= MAX_ATTEMPTS or time.monotonic() >= deadline:
                    break
                attempts += 1
                queue_claim = candidate.get('_queue_claim')
                record_item, translated = build_record(candidate)
                if any(p.get('id') == record_item['id'] or p.get('sourceProductId') == record_item['sourceProductId']
                       or (record_item.get('sourceModelKey') and p.get('sourceModelKey') == record_item['sourceModelKey'])
                       or (record_item.get('sourceImageUrl') and p.get('sourceImageUrl') == record_item['sourceImageUrl'])
                       for p in old + exclusions + [x[0] for x in prepared]):
                    if queue_claim:
                        queue_store.fail(queue_claim['claim_id'], owner, 'duplicate_existing', now=instant)
                    continue
                exclusions.append({'id': record_item['id'], 'sourceProductId': record_item['sourceProductId'], 'sourceTitle': record_item['sourceTitle']})
                try:
                    media = (
                        media_fn(candidate, record_item['id'], stage, perceptual_index=perceptual_index)
                        if pass_perceptual else media_fn(candidate, record_item['id'], stage)
                    )
                    if (not isinstance(media, dict) or not all(isinstance(media.get(k), str) and re.fullmatch(r'[0-9a-f]{64}', media[k]) for k in ('source_sha256', 'pixel_sha256'))
                            or media['source_sha256'] in used_hashes or media['pixel_sha256'] in used_hashes):
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    views = media.get('views') or []
                    if not isinstance(views, list) or len(views) > PHOTOS_PER_PRODUCT - 1:
                        raise DailyError('staging_invalid')
                    for path in [media['image'], media['original'], *views]:
                        path = Path(path).resolve()
                        if not path.is_relative_to(stage) or not path.is_file():
                            raise DailyError('staging_invalid')
                    cand_perceptual = _extract_media_perceptual(media)
                    if any(
                        image_studio.is_perceptually_duplicate(cand_hashes, perceptual_index)[0]
                        for cand_hashes in cand_perceptual.values()
                    ):
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    if views:
                        record_item['views'] = [f'assets/images/{record_item["id"]}-v{n}.webp' for n in range(2, len(views) + 2)]
                    record_item['sourceImageSha256'] = media['source_sha256']
                    record_item['sourcePixelSha256'] = media['pixel_sha256']
                    record_item['sourceImageUrl'] = media.get('source_url', candidate['image_url'])
                    if 'image' in cand_perceptual:
                        record_item['imageDhash'] = cand_perceptual['image']['dhash']
                        record_item['imageAhash'] = cand_perceptual['image']['ahash']
                        if cand_perceptual['image'].get('aspect'):
                            record_item['imageAspect'] = cand_perceptual['image']['aspect']
                    if 'original' in cand_perceptual:
                        record_item['sourceImageDhash'] = cand_perceptual['original']['dhash']
                        record_item['sourceImageAhash'] = cand_perceptual['original']['ahash']
                    if queue_claim:
                        record_item['sourceQueueRequestId'] = queue_claim['request_id']
                        record_item['sourceQueueClaimId'] = queue_claim['claim_id']
                        record_item['sourceQueueOwner'] = owner
                    record_item, translated = _maybe_ai_enrich(
                        record_item, translated, candidate, site_root,
                        catalog_corpus=catalog_corpus, snippet_fetcher=snippet_fetcher,
                    )
                    if strict_copy:
                        try:
                            _, co_mod = _import_tools_modules(site_root)
                            full_bundle = {
                                'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']},
                                **translated,
                            }
                            if (co_mod.check_source_title_mirroring(full_bundle, record_item.get('sourceTitle', ''))
                                    or co_mod.check_catalog_similarity(full_bundle, catalog_corpus)):
                                if queue_claim:
                                    queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                                continue
                        except Exception:
                            pass
                    used_hashes.update((media['source_sha256'], media['pixel_sha256']))
                    for kind_name, cand_hashes in cand_perceptual.items():
                        perceptual_index.append({'id': record_item['id'], 'path': kind_name, 'kind': kind_name, **cand_hashes})
                    if catalog_corpus is not None:
                        try:
                            _, co_mod = _import_tools_modules(site_root)
                            co_mod.append_bundle_to_corpus(
                                catalog_corpus,
                                record_item['id'],
                                {'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']}, **translated},
                            )
                        except Exception:
                            pass
                    prepared.append((record_item, translated, media))
                    progress = True
                except DailyError as error:
                    if str(error) in ('ocr_unavailable', 'image_processor_unavailable'):
                        raise
                    if queue_claim:
                        queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                    continue
            if not progress and attempts >= MAX_ATTEMPTS:
                break
        if len(prepared) < needed:
            raise DailyError('underfilled_no_publication')
        fresh_catalog = dict(catalog)
        fresh_catalog['products'] = [p[0] for p in prepared] + old
        fresh_i18n = dict(translations)
        fresh_i18n['products'] = dict(translations['products'])
        for product, lang, _ in prepared:
            fresh_i18n['products'][product['id']] = lang
        rows = [{'catalog_id': p['id'], 'product_id': p['sourceProductId'], 'source': 'api'} for p, _, _ in prepared]
        if validation_run_id is None:
            next_ledger = record(ledger, day, rows)
        else:
            from .daily_ledger import record_validation
            next_ledger = record_validation(ledger, day, validation_run_id, rows[0], now=now)
        verify_catalog(next_ledger, fresh_catalog)
        if now is None and utc_day() != day:
            raise DailyError('utc_day_changed_before_write')
        created = []
        try:
            for product, _, media in prepared:
                copies = [(media['image'], dist / 'assets/images' / (product['id'] + '.webp')),
                          (media['original'], dist / 'assets/originals' / (product['id'] + '.webp'))]
                copies += [(view, dist / relative) for view, relative in zip(media.get('views') or [], product.get('views', []))]
                for source_path, target in copies:
                    target = target.resolve()
                    if not target.is_relative_to(dist.resolve()):
                        raise DailyError('asset_path_invalid')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with Path(source_path).open('rb') as src, target.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
                    created.append(target)
            text = '/* FLUXIXO catalog: existing collection + daily accumulated finds. */\nwindow.MIRA_CATALOG = ' + json.dumps(fresh_catalog, ensure_ascii=False, indent=2) + ';\n'
            _atomic_bytes(catalog_path, text.encode('utf-8'))
            _atomic_bytes(translations_path, (json.dumps(fresh_i18n, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            atomic_write(ledger_path, next_ledger)
        except Exception:
            _atomic_bytes(catalog_path, original_catalog)
            _atomic_bytes(translations_path, original_i18n)
            _atomic_bytes(ledger_path, original_ledger)
            for target in created:
                if target.is_relative_to(dist.resolve()):
                    target.unlink(missing_ok=True)
            raise DailyError('daily_write_failed') from None
    print('Historical product IDs are incomplete; exact old-item deduplication cannot be guaranteed.')
    return {'added': len(prepared), 'ids': [p[0]['id'] for p in prepared]}


def mark_queued_committed(catalog, queue_store, ids, commit_sha, *, verify_commit, now=None):
    """Mark only products present in the verified pushed catalog commit."""
    if (not isinstance(commit_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', commit_sha)
            or not callable(verify_commit) or verify_commit(commit_sha) is not True
            or not isinstance(catalog, dict) or not isinstance(catalog.get('products'), list)
            or not isinstance(ids, list) or len(ids) > 3 or len(set(ids)) != len(ids)):
        raise DailyError('commit_unconfirmed')
    products = {p.get('id'): p for p in catalog['products'] if isinstance(p, dict)}
    marked = []
    for internal_id in ids:
        item = products.get(internal_id)
        if item is None:
            raise DailyError('commit_catalog_mismatch')
        request = item.get('sourceQueueRequestId')
        if not request:
            continue
        status = queue_store.status(request)
        if (not status or status['product_id'] != item.get('sourceProductId')
                or status['claim_id'] != item.get('sourceQueueClaimId')
                or status['owner'] != item.get('sourceQueueOwner')):
            raise DailyError('queue_commit_mismatch')
        if status['state'] == 'reserved':
            queue_store.mark_committed(status['claim_id'], status['owner'], commit_sha, verified=True, now=now)
            marked.append(request)
        elif status['state'] not in ('committed', 'published'):
            raise DailyError('queue_commit_mismatch')
    return marked


def _verify_remote_head(commit_sha):
    try:
        local = subprocess.run(['git','rev-parse','HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=True, timeout=20).stdout.decode('ascii').strip()
        remote = subprocess.run(['git','ls-remote','--heads','origin','refs/heads/main'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=True, timeout=45).stdout.decode('ascii').strip()
        return local == commit_sha and remote == commit_sha + '\trefs/heads/main'
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return False


def main():
    import argparse
    from .store import Store
    parser = argparse.ArgumentParser(description='Record queued items after verified Git push')
    parser.add_argument('--mark-committed', required=True)
    parser.add_argument('--ids', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    db_path = root / 'data/fluxixo_ai.sqlite3'
    ids = [item for item in args.ids.split(',') if item]
    if not ids or not db_path.is_file():
        print('No queued product status to update.')
        return
    try:
        text = (root / 'fluxixo_site/dist/js/catalog.js').read_text(encoding='utf-8')
        catalog = json.loads(text.split('=', 1)[1].strip().removesuffix(';'))
        marked = mark_queued_committed(catalog, Store(db_path), ids, args.mark_committed, verify_commit=_verify_remote_head)
        print(f'Queue entries recorded as committed: {len(marked)}; publication not yet asserted.')
    except Exception:
        raise SystemExit('Queue commit verification failed; deployment stopped.') from None


if __name__ == '__main__':
    main()
