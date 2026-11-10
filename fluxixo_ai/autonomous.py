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
import json
import os
import re
import shutil
import subprocess
import tempfile

from urllib.parse import urlsplit
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
    largest = 0
    while remaining:
        first = remaining.pop()
        queue = deque([first])
        size = 0
        while queue:
            point = queue.popleft()
            size += 1
            x, y = point % 96, point // 96
            for neighbor in ((point-1 if x else -1), (point+1 if x<95 else -1),
                             (point-96 if y else -1), (point+96 if y<95 else -1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        largest = max(largest, size)
    return largest / len(foreground) >= 0.5


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


def _default_media_preparer():
    try:
        from PIL import Image
        from rembg import remove, new_session
        session = new_session('u2net')
    except Exception:
        raise DailyError('image_processor_unavailable') from None
    def prepare(candidate, internal_id, stage):
        urls = candidate.get('image_urls') or [candidate.get('image_url')]
        for index, url in enumerate(urls[:8]):
            try:
                raw = _image_bytes(url)
                with Image.open(BytesIO(raw)) as value:
                    if value.width < 1 or value.height < 1 or value.width * value.height > 25_000_000:
                        continue
                    value.load()
                    original = value.convert('RGBA')
                source = stage / f'{internal_id}-source-{index}.png'
                original.save(source, 'PNG')
                if _check_ocr(source):
                    continue
                cutout = remove(original, session=session).convert('RGBA')
                if not mask_usable(cutout):
                    continue
                bbox = cutout.getbbox()
                cutout = cutout.crop(bbox)
                scale = min(903 / cutout.width, 903 / cutout.height)
                size = (max(1, round(cutout.width * scale)), max(1, round(cutout.height * scale)))
                cutout = cutout.resize(size, Image.Resampling.LANCZOS)
                canvas = Image.new('RGBA', (1254, 1254), (0, 0, 0, 0))
                canvas.alpha_composite(cutout, ((1254 - size[0]) // 2, (1254 - size[1]) // 2))
                image_path = stage / f'{internal_id}-prepared.webp'
                original_path = stage / f'{internal_id}-original.webp'
                canvas.save(image_path, 'WEBP', quality=92)
                original.save(original_path, 'WEBP', quality=88)
                return {'image': image_path, 'original': original_path, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                        'pixel_sha256': _pixel_hash(original), 'source_url': url}
            except DailyError as error:
                if str(error) == 'ocr_unavailable':
                    raise
            except Exception:
                continue
        raise DailyError('visual_quality_failed')
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


def accumulate(*, count, site_root, dist, reserve_dir, ledger_path, now=None,
               discover_fn=None, media_fn=None, validation_run_id=None, queue_store=None, refresh_fn=None):
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
        def media_fn(candidate, internal_id, stage):
            if not media_holder:
                media_holder.append(_default_media_preparer())
            return media_holder[0](candidate, internal_id, stage)
    old = catalog['products']
    used_hashes = _old_image_hashes(old, dist)
    exclusions = []
    prepared = []
    attempts = 0
    owner = 'daily-' + (os.environ.get('GITHUB_RUN_ID') or 'run')
    queue_batch = []
    if queue_store is not None:
        claims = queue_store.claim(day, owner, needed, lease_seconds=1200, now=instant)
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
        while len(prepared) < needed and attempts < 12:
            if queue_batch:
                batch, queue_batch = queue_batch, []
            else:
                batch = discover_fn(old + exclusions + [x[0] for x in prepared], needed - len(prepared), instant)
            if not batch:
                break
            progress = False
            for candidate in batch:
                if len(prepared) >= needed or attempts >= 12:
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
                    media = media_fn(candidate, record_item['id'], stage)
                    if (not isinstance(media, dict) or not all(isinstance(media.get(k), str) and re.fullmatch(r'[0-9a-f]{64}', media[k]) for k in ('source_sha256', 'pixel_sha256'))
                            or media['source_sha256'] in used_hashes or media['pixel_sha256'] in used_hashes):
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    for key in ('image','original'):
                        path = Path(media[key]).resolve()
                        if not path.is_relative_to(stage) or not path.is_file():
                            raise DailyError('staging_invalid')
                    record_item['sourceImageSha256'] = media['source_sha256']
                    record_item['sourcePixelSha256'] = media['pixel_sha256']
                    record_item['sourceImageUrl'] = media.get('source_url', candidate['image_url'])
                    if queue_claim:
                        record_item['sourceQueueRequestId'] = queue_claim['request_id']
                        record_item['sourceQueueClaimId'] = queue_claim['claim_id']
                        record_item['sourceQueueOwner'] = owner
                    used_hashes.update((media['source_sha256'], media['pixel_sha256']))
                    prepared.append((record_item, translated, media))
                    progress = True
                except DailyError as error:
                    if str(error) in ('ocr_unavailable', 'image_processor_unavailable'):
                        raise
                    if queue_claim:
                        queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                    continue
            if not progress and attempts >= 12:
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
                for key, folder in (('image','images'), ('original','originals')):
                    target = (dist / 'assets' / folder / (product['id'] + '.webp')).resolve()
                    if not target.is_relative_to(dist.resolve()):
                        raise DailyError('asset_path_invalid')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with Path(media[key]).open('rb') as src, target.open('xb') as dst:
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
