"""Future-only Pinterest RSS; never enroll the catalog present at activation.

first_seen is the first release-preparation time, not a confirmed deployment
timestamp. Persist it with tools/ so rebuilds and deployment retries retain it.
"""
from datetime import datetime, timezone
from email.utils import format_datetime
import json
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET

from PIL import Image


ORIGIN = 'https://www.fluxixo.shop'
FEED_URL = ORIGIN + '/pinterest-new.xml'
MEDIA_NS = 'http://search.yahoo.com/mrss/'
ATOM_NS = 'http://www.w3.org/2005/Atom'
ET.register_namespace('media', MEDIA_NS)
ET.register_namespace('atom', ATOM_NS)

PIN_WIDTH, PIN_HEIGHT = 1000, 1500
PIN_BG = (243, 240, 233)
DISCLOSURE = ('AI-assisted product summary. Affiliate disclosure: FLUXIXO uses '
              'affiliate links and may earn a commission from purchases.')
IMAGE_TYPES = {'.webp': 'image/webp', '.png': 'image/png',
               '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif'}
# Translate only the provenance notes used in the catalog and its publishers.
# A source URL, hash or quality flag alone does not identify AI image processing.
IMAGE_NOTES = {
    'Студийная ИИ-визуализация по фотографии продавца. Исходное фото доступно для сравнения; состав заказа уточняйте на AliExpress.':
        "AI-generated studio illustration based on the seller's photo.",
    'Студийная визуализация по исходному фото, созданная ИИ. Оригинал доступен ниже для сравнения деталей.':
        'AI-generated studio illustration based on the source photo.',
    'Изображение подготовлено из фотографии продавца. Исходная фотография доступна для сравнения.':
        "Image prepared from the seller's photo.",
    'Подготовленное изображение на основе фото продавца; исходное изображение доступно для сравнения.':
        "Image prepared from the seller's photo.",
    'Студийная визуализация по фото продавца, очищенная от фона. Оригинальная фотография доступна для сравнения ниже.':
        "Background-removed studio image based on the seller's photo.",
}


def _instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('timestamp must include a timezone')
    return result.astimezone(timezone.utc)


def _load_state(path):
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
        baseline = state['baseline_ids']
        seen = state['first_seen']
        if (state.get('version') != 1 or not isinstance(baseline, list)
                or not baseline or any(not isinstance(v, str) or not v for v in baseline)
                or len(set(baseline)) != len(baseline) or not isinstance(seen, dict)):
            raise ValueError('invalid baseline or timestamp map')
        for product_id, timestamp in seen.items():
            if not isinstance(product_id, str) or not product_id:
                raise ValueError('invalid product ID')
            _instant(timestamp)
        return state
    except (OSError, KeyError, TypeError, AttributeError, ValueError) as exc:
        # Failing closed is essential: an absent baseline must not enroll every
        # historical product and recreate the old Pins after a rebuild.
        raise ValueError(f'Pinterest feed state is missing or invalid: {path}') from exc


def _truncate_words(text, limit):
    """Shorten text at a sentence or word boundary without leaving a clipped word fragment."""
    clean = ' '.join(text.split())
    if limit <= 0:
        return ''
    if len(clean) <= limit:
        return clean
    cut = clean[:limit - 1].rstrip()
    for sep in ('. ', '! ', '? '):
        idx = cut.rfind(sep)
        if idx >= int(limit * 0.55):
            return cut[:idx + 1].rstrip()
    if ' ' in clean[:limit]:
        word_cut = clean[:limit].rsplit(' ', 1)[0].rstrip(' ,;:-')
        if word_cut:
            return word_cut + '…'
    return cut + '…'


def _render_pinterest_jpeg(dist, source_image, product_id):
    """Render a 2:3 (1000x1500) warm-paper RGB JPEG for reliable Pinterest RSS ingestion."""
    target = (dist / 'assets/pinterest' / f'{product_id}.jpg').resolve()
    if not target.is_relative_to(dist):
        raise ValueError(f'Unsafe Pinterest feed image path: {product_id}')
    if target.is_file() and target.stat().st_size > 0 and target.stat().st_mtime >= source_image.stat().st_mtime:
        try:
            with Image.open(target) as existing:
                if existing.format == 'JPEG' and existing.size == (PIN_WIDTH, PIN_HEIGHT):
                    return target
        except OSError:
            pass
    try:
        with Image.open(source_image) as opened:
            rgba = opened.convert('RGBA')
    except OSError as exc:
        raise ValueError(f'Pinterest feed image is unreadable: {product_id}') from exc
    bbox = rgba.getbbox()
    subject = rgba.crop(bbox) if bbox else rgba
    max_w, max_h = 840, 1180
    scale = min(max_w / max(subject.width, 1), max_h / max(subject.height, 1))
    resized = subject.resize(
        (max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
        Image.LANCZOS,
    )
    canvas = Image.new('RGB', (PIN_WIDTH, PIN_HEIGHT), PIN_BG)
    canvas.paste(resized, ((PIN_WIDTH - resized.width) // 2, (PIN_HEIGHT - resized.height) // 2), resized.getchannel('A'))
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix('.jpg.tmp')
    canvas.save(tmp, format='JPEG', quality=88, optimize=True)
    tmp.replace(target)
    return target


def build_pinterest_feed(dist, products, translations, state_path, *, now=None):
    """Return RSS and atomically persist first-seen dates, without generating assets."""
    dist, state_path = Path(dist).resolve(), Path(state_path)
    state = _load_state(state_path)
    baseline = set(state['baseline_ids'])
    instant = now if now is not None else datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Pinterest feed clock must include a timezone')
    timestamp = instant.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    items, ids, changed = [], set(), False
    for product in products:
        product_id = product.get('id')
        if product.get('demo') or product_id in baseline:
            continue
        if (not isinstance(product_id, str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', product_id)
                or product_id in ids):
            raise ValueError('Pinterest feed requires unique safe product IDs')
        ids.add(product_id)
        english = translations.get('products', {}).get(product_id, {}).get('en', {})
        name, description = english.get('name'), english.get('description')
        if not isinstance(name, str) or not name.strip() or not isinstance(description, str) or not description.strip():
            raise ValueError(f'Pinterest feed requires English copy: {product_id}')
        image_value = product.get('image')
        if not isinstance(image_value, str) or not image_value:
            raise ValueError(f'Pinterest feed requires an existing image: {product_id}')
        image = (dist / image_value).resolve()
        if (not image.is_relative_to(dist) or not image.is_file()
                or image.suffix.lower() not in IMAGE_TYPES or image.stat().st_size == 0):
            raise ValueError(f'Pinterest feed image is missing or invalid: {product_id}')
        pin_image = _render_pinterest_jpeg(dist, image, product_id)
        if product_id not in state['first_seen']:
            state['first_seen'][product_id] = timestamp
            changed = True
        image_note = product.get('imageNote')
        image_disclosure = IMAGE_NOTES.get(
            image_note.strip() if isinstance(image_note, str) else '',
            'Image preparation details are not confirmed.')
        items.append((state['first_seen'][product_id], product_id, name.strip(),
                      description.strip(), pin_image, image_disclosure + ' ' + DISCLOSURE))

    rss = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, f'{{{ATOM_NS}}}link', {
        'href': FEED_URL,
        'rel': 'self',
        'type': 'application/rss+xml',
    })
    for tag, value in (
        ('title', 'FLUXIXO — New product finds'),
        ('link', ORIGIN + '/en/'),
        ('description', 'Curated everyday product finds from AliExpress, updated daily with studio photos and direct seller links.'),
        ('language', 'en'),
    ):
        ET.SubElement(channel, tag).text = value
    if items:
        ET.SubElement(channel, 'lastBuildDate').text = format_datetime(
            max(_instant(row[0]) for row in items))
    for first_seen, product_id, name, description, pin_image, disclosure in sorted(
            items, key=lambda row: (-_instant(row[0]).timestamp(), row[1])):
        item = ET.SubElement(channel, 'item')
        url = f'{ORIGIN}/en/products/{product_id}/'
        pin_url = ORIGIN + '/' + quote(pin_image.relative_to(dist).as_posix(), safe='/-._~')
        pin_size = str(pin_image.stat().st_size)
        ET.SubElement(item, 'title').text = _truncate_words(name, 100)
        ET.SubElement(item, 'link').text = url
        ET.SubElement(item, 'guid', {'isPermaLink': 'true'}).text = url
        ET.SubElement(item, 'pubDate').text = format_datetime(_instant(first_seen))
        summary = _truncate_words(description, 499 - len(disclosure))
        ET.SubElement(item, 'description').text = (
            f'{summary} {disclosure}' if summary else disclosure)
        ET.SubElement(item, 'enclosure', {
            'url': pin_url,
            'type': 'image/jpeg',
            'length': pin_size,
        })
        ET.SubElement(item, f'{{{MEDIA_NS}}}content', {
            'url': pin_url,
            'type': 'image/jpeg',
            'medium': 'image',
            'width': str(PIN_WIDTH),
            'height': str(PIN_HEIGHT),
            'fileSize': pin_size,
        })
    ET.indent(rss, space='  ')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding='unicode') + '\n'
    if changed:
        temporary = state_path.with_suffix(state_path.suffix + '.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                             encoding='utf-8', newline='\n')
        temporary.replace(state_path)
    return xml
