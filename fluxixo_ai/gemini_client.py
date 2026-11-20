"""Explicit FLUXIXO Gemini calls with durable, conservative quotas and no fallback.

The owner supplies a dedicated Free Tier key through an Actions secret. This
client cannot inspect or enforce the project's billing setting or account-wide
usage by other clients. A provider quota error always defers work, never switches
model/provider. All callers must preserve this ledger across runner restarts.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import sqlite3
import time
import urllib.error
import urllib.request

TEXT_MODEL = 'gemini-3.5-flash-lite'
COPY_POLICY = 'seller-title-claims-v2'
REVIEW_MODEL = 'gemini-3.8-flash'
# Rolling 24 hours is deliberately more conservative than a provider's day reset.
LIMITS = {TEXT_MODEL: (480, 4.1), REVIEW_MODEL: (18, 12.1)}
DEFAULT_BUDGET_PATH = Path(__file__).resolve().parents[1] / 'data/fluxixo_gemini_usage.sqlite3'


class GeminiDeferred(RuntimeError):
    """Non-sensitive resumable failure; retry_at is a UTC Unix timestamp."""
    def __init__(self, code: str, retry_at: float | None = None):
        self.code = code
        self.retry_at = float(retry_at if retry_at is not None else time.time() + 300)
        super().__init__(code)


@contextmanager
def _connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        # Rollback journal, not WAL: one committed sqlite3 file is checkpointed by CI.
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, model TEXT NOT NULL, at REAL NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS request_times ON requests(model, at)')
        db.execute('CREATE TABLE IF NOT EXISTS backoff (model TEXT PRIMARY KEY, until REAL NOT NULL, reason TEXT NOT NULL)')
        with db:
            yield db
    finally:
        db.close()


def _reserve(path, model, now):
    """Reserve before network I/O, including failures; competing processes serialize."""
    limit, interval = LIMITS[model]
    with _connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        blocked = db.execute('SELECT until, reason FROM backoff WHERE model=?', (model,)).fetchone()
        if blocked and blocked[0] > now:
            raise GeminiDeferred(blocked[1], blocked[0])
        db.execute('DELETE FROM requests WHERE at <= ?', (now - 86400,))
        count, first, last = db.execute('SELECT count(*), min(at), max(at) FROM requests WHERE model=?', (model,)).fetchone()
        if count >= limit:
            raise GeminiDeferred('gemini_daily_budget', first + 86400.01)
        if last is not None and last + interval > now:
            raise GeminiDeferred('gemini_rate_wait', last + interval + 0.01)
        db.execute('INSERT INTO requests(model, at) VALUES (?, ?)', (model, now))


def _block(path, model, code, until):
    with _connect(path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT INTO backoff(model, until, reason) VALUES (?, ?, ?) '
                   'ON CONFLICT(model) DO UPDATE SET until=max(backoff.until, excluded.until), reason=excluded.reason',
                   (model, until, code))


def _retry_after(headers, now, default=3600):
    value = str((headers or {}).get('Retry-After') or '').strip()
    try:
        return max(now + 1, now + float(value))
    except ValueError:
        try:
            return max(now + 1, parsedate_to_datetime(value).timestamp())
        except (TypeError, ValueError, OverflowError):
            return now + default


def _post_json(url, body, headers):
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                     headers={'Content-Type': 'application/json', **headers}, method='POST')
    # Several exact images and HIGH reasoning can take longer than text-only copy.
    timeout = 240 if url.endswith(f'/{REVIEW_MODEL}:generateContent') else 90
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(5_000_001).decode('utf-8'))


def _image_part(image):
    if isinstance(image, tuple) and len(image) == 2:
        mime, raw = image
    else:
        raw = image
        if isinstance(raw, bytes) and raw.startswith(b'\x89PNG\r\n\x1a\n'):
            mime = 'image/png'
        elif isinstance(raw, bytes) and raw.startswith(b'\xff\xd8'):
            mime = 'image/jpeg'
        elif isinstance(raw, bytes) and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
            mime = 'image/webp'
        else:
            raise GeminiDeferred('gemini_image_invalid')
    if mime not in ('image/png', 'image/jpeg', 'image/webp') or not isinstance(raw, bytes) or not 0 < len(raw) <= 15_000_000:
        raise GeminiDeferred('gemini_image_invalid')
    return {'inlineData': {'mimeType': mime, 'data': base64.b64encode(raw).decode('ascii')}}


def _response_json(response):
    if not isinstance(response, dict) or response.get('promptFeedback', {}).get('blockReason'):
        raise GeminiDeferred('gemini_response_blocked')
    candidates = response.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise GeminiDeferred('gemini_invalid_response')
    candidate = candidates[0]
    if not isinstance(candidate, dict) or candidate.get('finishReason') != 'STOP':
        raise GeminiDeferred('gemini_incomplete_response')
    parts = (candidate.get('content') or {}).get('parts')
    if not isinstance(parts, list):
        raise GeminiDeferred('gemini_invalid_response')
    if any(not isinstance(part, dict) or (not part.get('thought') and not isinstance(part.get('text'), str))
           for part in parts):
        raise GeminiDeferred('gemini_invalid_response')
    output = ''.join(part['text'] for part in parts if isinstance(part, dict)
                     and not part.get('thought') and isinstance(part.get('text'), str)).strip()
    try:
        value = json.loads(output)
    except (ValueError, TypeError):
        raise GeminiDeferred('gemini_invalid_json') from None
    if not isinstance(value, dict) or not value:
        raise GeminiDeferred('gemini_invalid_json')
    return value


def call_json(system_prompt, user_prompt, *, model, api_key=None, images=(), transport=None, budget_path=None):
    """One bounded Gemini generateContent call, always HIGH and JSON-only.

    ``images`` contains raw PNG/JPEG/WebP bytes or (MIME type, bytes) tuples.
    An injected transport receives (url, body, headers), for offline testing.
    Missing keys, quota/network failures and uncertain responses raise GeminiDeferred.
    """
    if model not in LIMITS:
        raise GeminiDeferred('gemini_model_not_allowed')
    key = str(api_key if api_key is not None else os.environ.get('FLUXIXO_TEXT_GEMINI_API_KEY', '')).strip()
    if not key:
        raise GeminiDeferred('gemini_key_missing', time.time() + 3600)
    parts = [{'text': str(user_prompt)}] + [_image_part(image) for image in images]
    payload = {
        'systemInstruction': {'parts': [{'text': str(system_prompt)}]},
        'contents': [{'role': 'user', 'parts': parts}],
        'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 16384,
                             'thinkingConfig': {'thinkingLevel': 'HIGH'}},
    }
    path = budget_path or os.environ.get('FLUXIXO_GEMINI_BUDGET_PATH') or DEFAULT_BUDGET_PATH
    try:
        for attempt in range(3):
            try:
                _reserve(path, model, time.time())
                break
            except GeminiDeferred as exc:
                delay = exc.retry_at - time.time()
                if exc.code != 'gemini_rate_wait' or delay > 12.2 or attempt == 2:
                    raise
                time.sleep(max(0.01, delay))
    except (sqlite3.Error, OSError):
        raise GeminiDeferred('gemini_budget_unavailable') from None
    if os.environ.get('FLUXIXO_DURABLE_CHECKPOINT', '').strip().lower() == 'git':
        try:
            # Persist the reservation before spending provider quota. A runner may
            # disappear without executing workflow always() steps.
            from .state_checkpoint import checkpoint
            checkpoint()
        except Exception:
            raise GeminiDeferred('checkpoint_unavailable') from None
    try:
        response = (transport or _post_json)(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            payload, {'x-goog-api-key': key},
        )
        return _response_json(response)
    except urllib.error.HTTPError as exc:
        now = time.time()
        code = f'gemini_http_{exc.code}'
        until = _retry_after(exc.headers, now, default=3600 if exc.code == 429 else 300)
        try:
            _block(path, model, code, until)
        except (sqlite3.Error, OSError):
            raise GeminiDeferred('gemini_budget_unavailable', until) from None
        raise GeminiDeferred(code, until) from None
    except GeminiDeferred:
        raise
    except TimeoutError:
        raise GeminiDeferred('gemini_transport_timeout') from None
    except urllib.error.URLError as exc:
        code = 'gemini_transport_timeout' if isinstance(exc.reason, TimeoutError) else 'gemini_transport_unavailable'
        raise GeminiDeferred(code) from None
    except Exception:
        # Never propagate provider bodies, raw exceptions, request headers or credentials.
        raise GeminiDeferred('gemini_transport_unavailable') from None
