"""Bounded public phrase checks using Tavily's free, unauthenticated access mode.

No API key, account, Authorization header, automatic upgrade or provider fallback.
Official contract: https://docs.tavily.com/documentation/keyless.md
Only exact-text verdicts and evidence URLs are persisted, never search snippets.
The workflow must serialize writers and checkpoint this SQLite file before calls.
"""
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid

ENDPOINT = 'https://api.tavily.com/search'
DEFAULT_BUDGET_PATH = Path(__file__).resolve().parents[1] / 'data/fluxixo_free_search.sqlite3'
ADAPTER_VERSION = 'tavily-keyless-basic-v1'
DAILY_ATTEMPTS = 36
CACHE_TTL = 30 * 86400
NETWORK_TIMEOUT = 30
LEASE_SECONDS = 600
MAX_RESPONSE_BYTES = 1_000_000


class SearchDeferred(RuntimeError):
    def __init__(self, code, retry_at=None):
        self.code = re.sub(r'[^a-z0-9_]', '_', str(code).lower())[:80]
        self.retry_at = float(time.time() + 300 if retry_at is None else retry_at)
        super().__init__(self.code)


@contextmanager
def _db(path):
    path = Path(path)
    if path.is_symlink():
        raise OSError('unsafe_search_state')
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20, isolation_level=None)
    try:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, at REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS backoff (id INTEGER PRIMARY KEY, until REAL NOT NULL, reason TEXT NOT NULL)')
        db.execute('''CREATE TABLE IF NOT EXISTS checks (
            cache_key TEXT PRIMARY KEY, verdict TEXT, expires REAL NOT NULL DEFAULT 0,
            lease_until REAL NOT NULL DEFAULT 0, owner TEXT)''')
        with db:
            yield db
    finally:
        db.close()


def _checkpoint(now):
    try:
        from .state_checkpoint import checkpoint
        checkpoint()
    except Exception:
        raise SearchDeferred('search_checkpoint_unavailable', now + 900) from None


def _safe_url(value):
    if (not isinstance(value, str) or len(value) > 2048
            or any(ord(c) <= 32 or ord(c) == 127 for c in value) or '\\' in value):
        raise ValueError('unsafe_result_url')
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('unsafe_result_url')
    host = (parsed.hostname or '').rstrip('.').encode('idna').decode().lower()
    if not host or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise ValueError('unsafe_result_url')
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if '.' not in host or host.rsplit('.', 1)[-1].isdigit() or not re.fullmatch(r'[a-z0-9.-]+', host):
            raise ValueError('unsafe_result_url') from None
    else:
        if not ip.is_global:
            raise ValueError('unsafe_result_url')
        if ip.version == 6:
            host = '[' + host + ']'
    port = parsed.port
    authority = host + (':' + str(port) if port is not None else '')
    return urllib.parse.urlunsplit((parsed.scheme.lower(), authority, parsed.path or '/', parsed.query, ''))


def _results(payload, query):
    if not isinstance(payload, dict) or payload.get('query') != query:
        raise ValueError('search_schema_invalid')
    supported = {'query', 'results', 'answer', 'images', 'response_time', 'auto_parameters',
                 'usage', 'request_id', 'follow_up_questions', 'status'}
    if set(payload) - supported:
        raise ValueError('search_schema_invalid')
    if any(payload.get(key) for key in ('error', 'errors', 'detail', 'message', 'warning', 'warnings',
            'partial', 'is_partial', 'failed_results', 'incomplete', 'truncated', 'instructions', 'answer')):
        raise ValueError('search_incomplete')
    if payload.get('status', 'success') != 'success':
        raise ValueError('search_incomplete')
    rows = payload.get('results')
    if not isinstance(rows, list) or len(rows) > 5:
        raise ValueError('search_schema_invalid')
    normalized = []
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('title'), str)
                or not isinstance(row.get('content'), str) or not row['content'].strip()
                or len(row['title']) > 2000 or len(row['content']) > 20000):
            raise ValueError('search_schema_invalid')
        url = _safe_url(row.get('url'))
        host = urllib.parse.urlsplit(url).hostname
        if host == 'fluxixo.shop' or host.endswith('.fluxixo.shop'):
            continue
        normalized.append({'url': url, 'title': row['title'], 'snippet': row['content']})
    return normalized


def _valid_receipt(value):
    return (isinstance(value, dict) and type(value.get('passed')) is bool
            and value.get('issues') == ([] if value['passed'] else ['external_overlap'])
            and isinstance(value.get('evidence_urls'), list) and len(value['evidence_urls']) <= 5
            and all(_safe_url(url) == url for url in value['evidence_urls'])
            and type(value.get('checked_at')) in (int, float) and math.isfinite(value['checked_at']))


def _reserve(path, key, owner, now):
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT verdict,expires,lease_until FROM checks WHERE cache_key=?', (key,)).fetchone()
        if row and row[0] is not None and row[1] > now:
            receipt = json.loads(row[0])
            if not _valid_receipt(receipt):
                raise SearchDeferred('search_cache_invalid', now + 3600)
            return {**receipt, 'cache_hit': True}
        if row and row[2] > now:
            raise SearchDeferred('search_in_progress', row[2])
        blocked = db.execute('SELECT until,reason FROM backoff WHERE id=1').fetchone()
        if blocked and blocked[0] > now:
            raise SearchDeferred(blocked[1], blocked[0])
        db.execute('DELETE FROM requests WHERE at<=?', (now - 86400,))
        db.execute('DELETE FROM checks WHERE expires<=? AND lease_until<=?', (now, now))
        count, first = db.execute('SELECT count(*),min(at) FROM requests').fetchone()
        if count >= DAILY_ATTEMPTS:
            raise SearchDeferred('search_daily_budget', first + 86400.01)
        db.execute('INSERT INTO requests(at) VALUES(?)', (now,))
        db.execute('''INSERT INTO checks(cache_key,lease_until,owner) VALUES(?,?,?)
            ON CONFLICT(cache_key) DO UPDATE SET lease_until=excluded.lease_until,owner=excluded.owner''',
                   (key, now + LEASE_SECONDS, owner))
    return None


def require_search_capacity(*, db_path=None, now=None):
    """Read-only advisory check that at least one new search can be attempted.

    This neither reserves a slot nor guarantees capacity for all six locales.
    Actual searches still perform the atomic reservation immediately before I/O.
    A missing database means no recorded spend; this check creates nothing.
    """
    at = time.time() if now is None else float(now)
    path = Path(DEFAULT_BUDGET_PATH if db_path is None else db_path)
    try:
        if path.is_symlink():
            raise OSError('unsafe_search_state')
        try:
            path.stat()
        except FileNotFoundError:
            return
        db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=20)
        try:
            db.execute('BEGIN')
            blocked = db.execute('SELECT until,reason FROM backoff WHERE id=1').fetchone()
            if blocked and blocked[0] > at:
                raise SearchDeferred(blocked[1], blocked[0])
            count, first = db.execute('SELECT count(*),min(at) FROM requests WHERE at>?',
                                      (at - 86400,)).fetchone()
            if count >= DAILY_ATTEMPTS:
                raise SearchDeferred('search_daily_budget', first + 86400.01)
        finally:
            db.close()
    except (sqlite3.Error, OSError, ValueError, TypeError):
        raise SearchDeferred('search_budget_unavailable', at + 900) from None


def _failure(path, key, owner, code, until):
    with _db(path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE checks SET lease_until=0,owner=NULL WHERE cache_key=? AND owner=?', (key, owner))
        db.execute('''INSERT INTO backoff(id,until,reason) VALUES(1,?,?) ON CONFLICT(id)
            DO UPDATE SET until=max(backoff.until,excluded.until),reason=excluded.reason''', (until, code))


def _retry_after(headers, now, default):
    value = str((headers or {}).get('Retry-After', '')).strip()
    try:
        delay = float(value)
        if not math.isfinite(delay):
            raise ValueError()
        return max(now + 1, now + delay)
    except ValueError:
        try:
            return max(now + 1, parsedate_to_datetime(value).timestamp())
        except (ValueError, TypeError, OverflowError):
            return now + default


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post_json(url, payload, headers, timeout):
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode(),
                                     headers=headers, method='POST')
    with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError('search_status_invalid')
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('search_response_too_large')
        return json.loads(raw.decode('utf-8'))


def check_external_text(text, lang, *, compare, policy_version, query=None,
                        db_path=None, transport=None, now=None):
    """Compare fresh external hits once; reuse an exact-text verdict for 30 days.

    ``compare([{url,title,snippet}, ...])`` returns ``(passed, issues)``. It may
    inspect snippets in memory; only a standardized overlap reason and URLs are
    saved. Callers retain accepted publication receipts in their draft journals.
    Every transport attempt is reserved before I/O, including failed attempts.
    """
    clock = time.time if now is None else lambda: float(now)
    at = clock()
    if not math.isfinite(at) or not isinstance(text, str) or not text.strip() or len(text) > 50000:
        raise SearchDeferred('search_input_invalid', at + 3600)
    if not isinstance(lang, str) or not re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?', lang):
        raise SearchDeferred('search_language_invalid', at + 3600)
    if not isinstance(policy_version, str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,120}', policy_version) or not callable(compare):
        raise SearchDeferred('search_policy_invalid', at + 3600)
    clean = ' '.join(unicodedata.normalize('NFC', text).split())
    query = ('"' + ' '.join(clean.split()[:24]) + '"') if query is None else query
    if not isinstance(query, str) or not query.strip() or len(query) > 400:
        raise SearchDeferred('search_query_invalid', at + 3600)
    if transport is None and os.environ.get('FLUXIXO_OFFLINE') == '1':
        raise SearchDeferred('search_offline', at + 3600)
    key = hashlib.sha256(json.dumps([ADAPTER_VERSION, policy_version, lang, clean, query],
                                   ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    path = db_path if db_path is not None else DEFAULT_BUDGET_PATH
    owner = uuid.uuid4().hex
    try:
        cached = _reserve(path, key, owner, at)
        if cached is not None:
            return cached
    except (sqlite3.Error, OSError, ValueError, TypeError):
        raise SearchDeferred('search_budget_unavailable', at + 900) from None
    payload = {'query': query, 'search_depth': 'basic', 'topic': 'general', 'max_results': 5,
               'auto_parameters': False, 'include_answer': False, 'include_raw_content': False,
               'include_images': False, 'include_usage': True, 'exclude_domains': ['fluxixo.shop'], 'language': lang}
    headers = {'Content-Type': 'application/json', 'X-Tavily-Access-Mode': 'keyless'}
    try:
        _checkpoint(clock())
        response = (transport or _post_json)(ENDPOINT, payload, headers, NETWORK_TIMEOUT)
        hits = _results(response, query)
        verdict = compare(hits)
        if (not isinstance(verdict, (tuple, list)) or len(verdict) != 2 or type(verdict[0]) is not bool
                or not isinstance(verdict[1], list) or not all(isinstance(issue, str) for issue in verdict[1])
                or bool(verdict[1]) == verdict[0]):
            raise ValueError('search_comparison_invalid')
        receipt = {'passed': verdict[0], 'issues': [] if verdict[0] else ['external_overlap'],
                   'evidence_urls': sorted({hit['url'] for hit in hits}), 'checked_at': clock()}
        with _db(path) as db:
            changed = db.execute('''UPDATE checks SET verdict=?,expires=?,lease_until=0,owner=NULL
                WHERE cache_key=? AND owner=?''',
                (json.dumps(receipt, ensure_ascii=False), clock() + CACHE_TTL, key, owner)).rowcount
            if changed != 1:
                raise SearchDeferred('search_lease_lost', clock() + 300)
        _checkpoint(clock())
        return {**receipt, 'cache_hit': False}
    except urllib.error.HTTPError as exc:
        code = f'search_http_{exc.code}'
        until = _retry_after(exc.headers, clock(), 86400 if exc.code in (429, 432, 433) else 3600)
    except SearchDeferred as exc:
        code, until = exc.code, exc.retry_at
    except (ValueError, TypeError, KeyError, UnicodeError):
        code, until = 'search_response_unverified', clock() + 3600
    except Exception:
        code, until = 'search_unavailable', clock() + 300
    try:
        _failure(path, key, owner, code, until)
        _checkpoint(clock())
    except Exception:
        raise SearchDeferred('search_checkpoint_unavailable', clock() + 900) from None
    raise SearchDeferred(code, until) from None
