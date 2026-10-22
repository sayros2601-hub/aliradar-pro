"""Offline DealVault observations. No browser profiles or live account access.

Structurally valid imports remain pending; they are not approved product offers.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import uuid
from dealvault_core import affiliate_key, write_json
from inbox_store import queue_lock, read_queue, strict_json, ensure_queue_size

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR, INBOX_DIR = BASE_DIR / 'data', BASE_DIR / 'inbox'
PARSER_VERSION = 'dealvault-adapter-v1.1.0'
MAX_FILE_BYTES, MAX_RECORDS = 5 * 1024 * 1024, 2000
AFFILIATE_LINK_RE = re.compile(r'https://s\.click\.aliexpress\.com/e/_[A-Za-z0-9_-]+(?:\?[^\s<>"\']*)?')
ITEM_ID_RE = re.compile(r'^[0-9]+$')


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def safe_resolve_path(raw_path, root_dir=None):
    if not isinstance(raw_path, str) or not raw_path or '\x00' in raw_path:
        raise PermissionError('Invalid import path')
    root = Path(root_dir or INBOX_DIR).resolve()
    candidate = Path(raw_path)
    target = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not target.is_relative_to(root) or ':' in str(target.relative_to(root)):
        raise PermissionError('Import path escapes inbox or uses an alternate stream')
    return target


def _object(raw, key):
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('Invalid nested object')
    return value


def _text(value, limit=20000):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError('Invalid text')
    return value


def _timestamp(value):
    if value is None or value == '':
        return None
    value = _text(value, 80)
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError('Observation timestamp must be timezone-aware and not future')
    return value


def parse_observation_record(raw, imported_at):
    """Normalize without filling unknown fields or exposing raw data in errors."""
    try:
        if not isinstance(raw, dict):
            raise ValueError('Not an object')
        modal, offer, fields = (_object(raw, key) for key in ('modal', 'offer', 'fields'))
        fields = dict(fields)
        # Preserve legacy capture context without pretending it is normalized or verified.
        for key in ('offer', 'selection', 'ad_review', 'editorial'):
            context = _object(raw, key)
            if context:
                fields['source_' + key] = context
        images = raw.get('images') if raw.get('images') is not None else modal.get('images')
        if images is not None:
            if not isinstance(images, list) or len(images) > 100 or any(not isinstance(x, str) or len(x) > 4096 for x in images):
                raise ValueError('Invalid image references')
            fields['source_images'] = images
        text = _text(raw.get('text') or modal.get('text') or raw.get('source_evidence')) or ''
        explicit = [_text(raw.get(key), 4096) for key in ('original_affiliate_url', 'affiliate_url')]
        if all(explicit) and explicit[0] != explicit[1]:
            raise ValueError('Conflicting affiliate URLs')
        match = AFFILIATE_LINK_RE.search(text)
        url = explicit[0] or explicit[1] or (match.group(0) if match else None)
        if not affiliate_key(url):
            raise ValueError('Original affiliate shortlink required')
        title = _text(raw.get('raw_title'), 1000) or ''
        item = raw.get('item_id')
        if item is not None and (not isinstance(item, str) or not ITEM_ID_RE.fullmatch(item)):
            raise ValueError('Invalid item ID')
        variant = _text(raw.get('variant_id'), 200)
        country = _text(raw.get('country') or raw.get('target_country'), 2)
        currency = _text(raw.get('currency') or offer.get('currency'), 3)
        if country and not re.fullmatch('[A-Z]{2}', country):
            raise ValueError('Invalid country')
        if currency and not re.fullmatch('[A-Z]{3}', currency):
            raise ValueError('Invalid currency')
        observed = _timestamp(raw.get('observed_at'))
        source_kind = raw.get('source_kind') or 'export'
        if source_kind not in ('export', 'official_api'):
            raise ValueError('Invalid source kind')
        source_ref = _text(raw.get('source_ref'), 1000) or 'local_inbox'
        evidence = raw.get('evidence')
        if evidence is None:
            evidence = [text] if text else []
        if not isinstance(evidence, list) or len(evidence) > 50 or any(not isinstance(x, str) or len(x) > 20000 for x in evidence):
            raise ValueError('Invalid evidence')
        for key in ('item_price', 'shipping_cost', 'rating', 'review_count', 'seller_positive_pct', 'shipping_days_max'):
            value = fields.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError('Invalid numeric field')
        if fields.get('in_stock') is not None and type(fields['in_stock']) is not bool:
            raise ValueError('Invalid stock')
        json.dumps(fields, allow_nan=False)
        missing = [key for key, value in [('observation_time', observed), ('item_id', item), ('variant_id', variant), ('country', country), ('currency', currency), ('raw_title', title)] if not value]
        missing.extend(key for key in ('item_price', 'in_stock', 'rating') if fields.get(key) is None)
        envelope = {'schema_version': 'proposal-1', 'source_kind': source_kind, 'source_ref': source_ref,
                    'observed_at': observed, 'country': country, 'currency': currency, 'item_id': item,
                    'variant_id': variant, 'raw_title': title, 'original_affiliate_url': url,
                    'fields': fields, 'evidence': evidence, 'missing_fields': missing, 'review_status': 'pending'}
        identity = json.dumps(envelope, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')
        envelope['observation_id'] = 'obs-' + hashlib.sha256(identity).hexdigest()
        envelope['imported_at'] = imported_at
        return envelope, []
    except (ValueError, TypeError, OverflowError, RecursionError):
        return {}, ['INVALID_RECORD: check field types, identity, timestamp and source format']


class DealVaultAdapter:
    def __init__(self, inbox_dir=None, data_dir=None):
        self.inbox_dir = Path(inbox_dir or INBOX_DIR).resolve()
        self.data_dir = Path(data_dir or DATA_DIR).resolve()

    def get_status(self):
        warnings = []
        active, staged = 0, 0
        try:
            path = self.data_dir / 'products.json'
            if path.exists():
                content = strict_json(path.read_text(encoding='utf-8-sig'))
                if not isinstance(content, dict) or not isinstance(content.get('products'), list):
                    raise ValueError('Invalid catalog')
                active = len(content['products'])
        except (OSError, ValueError, RecursionError):
            active = None; warnings.append('CATALOG_UNREADABLE')
        try:
            staged = len(read_queue(self.data_dir / 'portals_inbox.json'))
        except (OSError, ValueError, RecursionError):
            staged = None; warnings.append('QUEUE_UNREADABLE')
        return {'schema_version': 'proposal-1', 'adapter_version': PARSER_VERSION, 'mode': 'offline_supported',
                'capabilities': {'validate_import': True, 'stage_import': True, 'status': True,
                                 'check_session': False, 'local_harvest': False, 'financial_summary': False, 'live_api_search': False},
                'environment': {'inbox_confinement': str(self.inbox_dir), 'active_catalog_count': active, 'staged_inbox_count': staged},
                'status': 'PARTIAL' if warnings else 'OK', 'warnings': warnings,
                'live_access': 'disabled; no authorized live integration verified; no browser profiles inspected'}

    @staticmethod
    def _result(operation):
        return {'schema_version': 'proposal-1', 'request_id': str(uuid.uuid4()), 'operation': operation,
                'started_at': utc_now(), 'finished_at': utc_now()}

    @staticmethod
    def _error(result, status, code):
        return {**result, 'status': status, 'finished_at': utc_now(), 'error': {'code': code}}

    def _validate(self, file_path, offline=True):
        result = self._result('validate_import')
        if not offline:
            return self._error(result, 'POLICY_BLOCKED', 'LIVE_DISABLED'), None
        try:
            path = safe_resolve_path(file_path, self.inbox_dir)
        except (PermissionError, ValueError, OSError, RuntimeError):
            return self._error(result, 'POLICY_BLOCKED', 'PATH_TRAVERSAL_DENIED'), None
        if not path.exists():
            return self._error(result, 'INVALID_INPUT', 'FILE_NOT_FOUND'), None
        try:
            if not path.is_file():
                return self._error(result, 'INVALID_INPUT', 'REGULAR_FILE_REQUIRED'), None
            with path.open('rb') as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                return self._error(result, 'INVALID_INPUT', 'FILE_TOO_LARGE'), None
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            return self._error(result, 'INVALID_INPUT', 'INVALID_ENCODING'), None
        except OSError:
            return self._error(result, 'INVALID_INPUT', 'FILE_UNREADABLE'), None
        if path.suffix.lower() != '.json':
            return self._error(result, 'UNSUPPORTED_FORMAT', 'JSON_REQUIRED'), None
        try:
            data = strict_json(text)
        except (ValueError, RecursionError):
            return self._error(result, 'INVALID_INPUT', 'MALFORMED_JSON'), None
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            wrapper = [key for key in ('records', 'products') if key in data]
            if len(wrapper) > 1:
                return self._error(result, 'UNSUPPORTED_FORMAT', 'AMBIGUOUS_CONTAINER'), None
            records = data[wrapper[0]] if wrapper else [data]
        else:
            records = None
        if not isinstance(records, list):
            return self._error(result, 'UNSUPPORTED_FORMAT', 'UNSUPPORTED_DATA_SHAPE'), None
        if len(records) > MAX_RECORDS:
            return self._error(result, 'INVALID_INPUT', 'TOO_MANY_RECORDS'), None
        valid, quarantine = [], []
        for index, row in enumerate(records):
            envelope, errors = parse_observation_record(row, utc_now())
            if errors:
                quarantine.append({'index': index, 'reasons': errors})
            else:
                valid.append(envelope)
        return {**result, 'finished_at': utc_now(), 'status': 'PARTIAL' if quarantine and valid else ('FAILED' if quarantine else 'OK'),
                'summary': {'total_records': len(records), 'valid_records': len(valid), 'quarantine_records': len(quarantine)},
                'valid_observations': valid, 'quarantine': quarantine,
                'warning': 'Structurally valid is not verified or approved for publication'}, hashlib.sha256(raw).hexdigest()

    def validate_import(self, file_path_str, offline=True):
        return self._validate(file_path_str, offline)[0]

    def stage_import(self, file_path_str, offline=True):
        result, input_hash = self._validate(file_path_str, offline)
        result['operation'] = 'stage_import'
        if result['status'] not in ('OK', 'PARTIAL'):
            return result
        if not result['valid_observations']:
            return {**result, 'staged_count': 0}
        path = self.data_dir / 'portals_inbox.json'
        try:
            with queue_lock(self.data_dir):
                queue = read_queue(path)
                ids = {row.get('observation_id') for row in queue}
                added = 0
                for observation in result['valid_observations']:
                    if observation['observation_id'] in ids:
                        continue
                    row = {**observation, 'id': observation['observation_id'],
                           'affiliate_url': observation['original_affiliate_url'], 'source': 'portals',
                           'source_evidence': '\n'.join(observation['evidence']), 'reviewed': False,
                           'captured_at': observation['observed_at'], 'import_file_sha256': input_hash,
                           'parser_version': PARSER_VERSION}
                    queue.append(row); ids.add(row['observation_id']); added += 1
                if added:
                    ensure_queue_size(queue)
                    write_json(path, queue)
        except (ValueError, RecursionError):
            return self._error(result, 'FAILED', 'QUEUE_INVALID_PRESERVED')
        except OSError:
            return self._error(result, 'FAILED', 'QUEUE_BUSY_OR_WRITE_FAILED')
        result.pop('valid_observations', None)
        return {**result, 'finished_at': utc_now(), 'staged_count': added,
                'message': 'Staged pending observations' if added else 'Idempotent: observations already staged'}

    def check_session(self):
        return self._error(self._result('check_session'), 'POLICY_BLOCKED', 'LIVE_ACCESS_NOT_ENABLED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status').add_argument('--json', action='store_true')
    for name in ('validate-import', 'stage-import'):
        command = commands.add_parser(name)
        command.add_argument('--file', required=True)
        command.add_argument('--offline', action='store_true', default=True)
    commands.add_parser('check-session', help='Report disabled live access without a browser')
    args = parser.parse_args()
    adapter = DealVaultAdapter()
    if args.command == 'status':
        result = adapter.get_status()
    elif args.command == 'check-session':
        result = adapter.check_session()
    else:
        result = getattr(adapter, args.command.replace('-', '_'))(args.file, offline=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'OK' else 2


if __name__ == '__main__':
    raise SystemExit(main())
