"""Bounded shared GitHub inbox for the existing authorized AliExpress runtime.

Requests and results are public repository files. Do not put secrets or private
chat data in them. This module does not run on import and does not deploy or
publish products; GitHub Actions commits its results and ledger together.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .broker import handle_request
from .search import AliClient
from .store import Store, StoreError

REQUEST = re.compile(r'^[0-9a-f]{32}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
OPERATIONS = frozenset(('search', 'queue', 'ledger_status'))
MAX_REQUEST_BYTES = 56_000
MAX_PAYLOAD_BYTES = 28_000
MAX_RESULT_BYTES = 1_000_000
MAX_PENDING = 1000


class InboxError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate_json_key')
        out[key] = value
    return out


def _parse(raw, cap):
    if len(raw) > cap:
        raise ValueError('too_large')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))


def _payload_hash(payload):
    try:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        raise ValueError('request_binding_invalid') from None
    if len(body) > MAX_PAYLOAD_BYTES:
        raise ValueError('request_binding_invalid')
    return hashlib.sha256(body).hexdigest()


def _read_request(path):
    identifier = path.stem
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REQUEST_BYTES:
            raise ValueError()
        data = _parse(path.read_bytes(), MAX_REQUEST_BYTES)
        if (not isinstance(data, dict) or set(data) != {'request_id', 'operation', 'payload_sha256', 'payload'}
                or data.get('request_id') != identifier or not REQUEST.fullmatch(identifier)
                or data.get('operation') not in OPERATIONS or not isinstance(data.get('payload'), dict)
                or not isinstance(data.get('payload_sha256'), str) or not DIGEST.fullmatch(data['payload_sha256'])
                or _payload_hash(data['payload']) != data['payload_sha256']):
            raise ValueError()
        return data
    except (ValueError, OSError, UnicodeError, TypeError):
        raise ValueError('request_binding_invalid') from None


def _read_result(path):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RESULT_BYTES:
            raise ValueError()
        result = _parse(path.read_bytes(), MAX_RESULT_BYTES)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (ValueError, OSError, UnicodeError):
        raise ValueError('result_invalid') from None


def _write_result(path, result):
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(encoded) > MAX_RESULT_BYTES:
        raise ValueError('result_too_large')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.tmp-', delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def process_inbox(root, *, handler=handle_request, client_factory=AliClient, now=None):
    """Process every unprocessed request in one bounded checkout of latest main.

    Search requests are processed before queue requests so both can be pushed
    together. Existing results never change, including a same-ID collision.
    This function writes only local files; its caller commits results and DB
    atomically under the shared GitHub concurrency lock, then performs a
    non-forced push. If pending exceeds the bound, fail visibly without work.
    """
    root = Path(root).resolve()
    base, requests_dir, results_dir = root / '.fluxixo-ai', root / '.fluxixo-ai/requests', root / '.fluxixo-ai/results'
    if any(path.is_symlink() for path in (base, requests_dir, results_dir)):
        raise InboxError('unsafe_inbox_path')
    if not requests_dir.exists():
        return {'processed': 0, 'conflicts': 0}
    if not requests_dir.is_dir() or (results_dir.exists() and not results_dir.is_dir()):
        raise InboxError('unsafe_inbox_path')
    files = sorted((p for p in requests_dir.glob('*.json') if REQUEST.fullmatch(p.stem)), key=lambda p: p.name)
    pending = []
    conflicts = 0
    for path in files:
        identifier = path.stem
        try:
            item = _read_request(path)
            invalid = False
        except ValueError:
            item = {'request_id': identifier, 'operation': None, 'payload_sha256': None}
            invalid = True
        result_path = results_dir / (identifier + '.json')
        if result_path.exists() or result_path.is_symlink():
            try:
                existing = _read_result(result_path)
                if (invalid or existing.get('request_id') != identifier
                        or existing.get('operation') != item['operation']
                        or existing.get('payload_sha256') != item['payload_sha256']):
                    conflicts += 1
            except ValueError:
                conflicts += 1
            continue
        pending.append((path, item, invalid))
    if len(pending) > MAX_PENDING:
        raise InboxError('backlog_exceeds_limit')
    # Search artifacts are read by queue; order is by dependency, then ID.
    pending.sort(key=lambda entry: (0 if entry[1].get('operation') == 'search' else 1, entry[0].name))
    ledger = None
    client = None
    def call(method, params):
        nonlocal client
        if client is None:
            client = client_factory()
        return client(method, params)
    def load_search(identifier):
        if not isinstance(identifier, str) or not REQUEST.fullmatch(identifier):
            raise ValueError('search_not_complete')
        source = _read_request(requests_dir / (identifier + '.json'))
        result = _read_result(results_dir / (identifier + '.json'))
        if (source['operation'] != 'search' or result.get('operation') != 'search'
                or result.get('request_id') != identifier
                or result.get('payload_sha256') != source['payload_sha256']):
            raise ValueError('search_not_complete')
        return result
    for path, item, invalid in pending:
        identifier = item['request_id']
        result = {'request_id': identifier, 'operation': item['operation'],
                  'payload_sha256': item['payload_sha256'], 'status': 'failed'}
        if invalid:
            result['error'] = 'request_binding_invalid'
        else:
            try:
                if item['operation'] != 'search' and ledger is None:
                    ledger = Store(root / 'data/fluxixo_ai.sqlite3')
                value = handler(item['operation'], item['payload'], identifier, call, ledger, load_search, now=now)
                result.update({'status': 'complete', 'result': value})
            except Exception as error:
                # A multi-product request may have queued items before a later
                # failure. Persist and expose the real partial ledger state.
                partial = []
                if item['operation'] == 'queue' and ledger is not None:
                    try:
                        partial = ledger.status_batch(identifier)
                    except StoreError:
                        pass
                code = getattr(error, 'code', None)
                result['error'] = code if isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9_]{1,80}', code) else 'request_failed'
                if partial:
                    result['status'] = 'partial'
                    result['partial_queue'] = partial
        try:
            _write_result(results_dir / (identifier + '.json'), result)
        except (ValueError, OSError, UnicodeError):
            # Do not publish a successful result if it cannot be safely saved.
            raise InboxError('result_write_failed') from None
    return {'processed': len(pending), 'conflicts': conflicts}


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        summary = process_inbox(root)
        print(json.dumps(summary, separators=(',', ':')))
    except InboxError as error:
        print(json.dumps({'status': 'failed', 'error': error.code}, separators=(',', ':')))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
