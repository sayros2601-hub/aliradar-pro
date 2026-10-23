"""Stage captured Portals records offline for review; never publish or browse."""
import argparse
import hashlib
import re
import json
from pathlib import Path

from dealvault_core import DATA_DIR, affiliate_key, read_json, write_json, utc_now
from inbox_store import queue_lock, read_queue, ensure_queue_size


# Capture the complete URL, including tracking parameters. affiliate_key performs
# the actual host/path validation; this expression is only a text tokenizer.
_TEXT_URL = re.compile(r'https://s\.click\.aliexpress\.com/[^\s<>"\']+')


def _string(value):
    return value if isinstance(value, str) and value.strip() else None


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _record_url(record, text=''):
    for field in ('original_affiliate_url', 'affiliate_url'):
        value = record.get(field)
        if value is not None and value != '':
            # Do not conceal an explicitly invalid URL by falling back to text.
            return value if isinstance(value, str) and affiliate_key(value) else None
    for match in _TEXT_URL.finditer(text):
        value = match.group(0)
        if affiliate_key(value):
            return value
    return None


def _catalog_keys(db):
    if not isinstance(db, dict) or not isinstance(db.get('products'), list):
        raise ValueError('Invalid products.json: expected an object with a products list')
    keys = set()
    for index, product in enumerate(db['products']):
        url = _record_url(product) if isinstance(product, dict) else None
        if not url:
            raise ValueError(f'Invalid products.json record at index {index}; inbox unchanged')
        keys.add(affiliate_key(url))
    return keys


def _item_id(value):
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        value = str(value)
    return value if isinstance(value, str) and re.fullmatch(r'[0-9]+', value) else None


def _candidate(raw):
    if not isinstance(raw, dict):
        return None
    modal = _mapping(raw.get('modal'))
    text = (_string(modal.get('text')) or _string(raw.get('text'))
            or _string(raw.get('source_evidence')) or '')
    url = _record_url(raw, text)
    if not url:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = _string(raw.get('raw_title')) or (lines[1] if len(lines) > 1 else None)
    # A search query is not evidence of the actual product title.
    if not title:
        return None
    key = affiliate_key(url)
    observed = _string(raw.get('observed_at'))
    images = raw.get('images')
    if not isinstance(images, list):
        images = modal.get('images')
    images = [item for item in images if _string(item)] if isinstance(images, list) else []
    offer = _mapping(raw.get('offer'))
    result = {
        'id': 'portals-' + hashlib.sha256(key.encode()).hexdigest()[:12],
        'affiliate_url': url,
        'original_affiliate_url': url,
        'raw_title': title,
        'source': 'portals',
        'source_evidence': text,
        'category': _string(raw.get('category')),
        'images': images,
        'observed_at': observed,
        'imported_at': utc_now(),
        'captured_at': observed,
        'reviewed': False,
        'review_status': 'pending',
        'status': 'pending',
        'query': _string(raw.get('query')),
        'target_country': _string(raw.get('target_country')) or _string(raw.get('country')),
        'currency': _string(raw.get('currency')) or _string(offer.get('currency')),
        'item_id': _item_id(raw.get('item_id')),
        'selection': _mapping(raw.get('selection')),
        'offer': offer,
        'ad_review': _mapping(raw.get('ad_review')),
        'editorial': _mapping(raw.get('editorial')),
        'fields': _mapping(raw.get('fields')),
    }
    # Keep supplied observation evidence for review without treating it as verified.
    for field in ('schema_version', 'observation_id', 'source_kind', 'source_ref', 'variant_id'):
        result[field] = _string(raw.get(field))
    result['evidence'] = raw.get('evidence') if isinstance(raw.get('evidence'), list) else []
    result['missing_fields'] = (raw.get('missing_fields')
                                if isinstance(raw.get('missing_fields'), list) else [])
    return result


def stage_records(records, check_links=False, link_checker=None):
    """Append genuine captures to the shared queue, leaving the catalog untouched.

    No network checker is included. ``check_links=True`` is retained only as an
    injection point for a caller-supplied, trusted offline evidence checker. It
    fails before any file access unless that callable is explicitly supplied.
    The normal path never calls a checker, even if one was passed accidentally.
    Existing queue corruption fails closed instead of replacing user data.
    """
    if check_links and not callable(link_checker):
        raise ValueError('Live link checks are unavailable; supply an explicit offline checker or use the default offline mode')
    if not isinstance(records, (list, tuple)):
        raise ValueError('Expected a list of captured records')
    with queue_lock(DATA_DIR):
        inbox = read_queue(DATA_DIR / 'portals_inbox.json')
        existing = _catalog_keys(read_json(DATA_DIR / 'products.json'))
        existing.update(affiliate_key(_record_url(item)) for item in inbox)
        observations = {item.get('capture_fingerprint') or observation_key(item) for item in inbox}
        added = []
        for raw in records:
            candidate = _candidate(raw)
            if candidate is None:
                continue
            key = affiliate_key(candidate['affiliate_url'])
            observation = observation_key(candidate)
            # A fresh timestamped capture can update evidence for an existing item.
            # Undated legacy duplicates still cannot grow the queue on every run.
            if observation in observations or (key in existing and not candidate.get('observed_at')):
                continue
            candidate['capture_fingerprint'] = observation
            check = (link_checker(candidate) if check_links
                     else {'status': 'UNCHECKED_OFFLINE', 'item_id': candidate['item_id']})
            if not isinstance(check, dict):
                raise ValueError('The supplied checker must return an evidence object; inbox unchanged')
            candidate['destination_check'] = check
            candidate['item_id'] = _item_id(check.get('item_id')) or candidate['item_id']
            inbox.append(candidate)
            added.append(candidate)
            existing.add(key)
            observations.add(observation)
        if added:
            ensure_queue_size(inbox)
            write_json(DATA_DIR / 'portals_inbox.json', inbox)
    print(f'[Portals] Staged {len(added)} captured records for review. Live catalog unchanged.')
    return added


def observation_key(record):
    fields = ('affiliate_url', 'observed_at', 'raw_title', 'source_evidence', 'item_id',
              'variant_id', 'currency', 'target_country', 'offer', 'fields', 'evidence',
              'images', 'category', 'query', 'selection', 'ad_review', 'editorial',
              'source_ref', 'source_kind', 'schema_version', 'missing_fields')
    content = {key: record.get(key) for key in fields}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--offline', action='store_true', help='Compatibility option: imports are always offline')
    parser.add_argument('--check-links', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check_links:
        parser.error('Live link checking is unavailable; import captured data offline')
    try:
        stage_records(read_json(args.capture))
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
