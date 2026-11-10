"""Durable, transactional product-intake ledger; never contacts external services.

One SQLite database is authoritative only if every writer uses the *same*
database and is serialized across checkout/commit/deploy. Separate copies on
different machines do not form a lock. A caller must verify catalog provenance,
Git and deployment evidence against the actual services before asserting it.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit
from uuid import uuid4

LANGUAGES = ('ru', 'en', 'pt', 'es', 'fr', 'he')
PRODUCT_ID = re.compile(r'^[1-9][0-9]{0,31}$')
KEY = re.compile(r'^[A-Za-z0-9_.:-]{1,128}$')
REASON = re.compile(r'^[a-z0-9_-]{1,80}$')
SHA = re.compile(r'^[0-9a-f]{40}$')
DEPLOYMENT = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
METHODS = frozenset(('aliexpress.affiliate.product.query', 'aliexpress.affiliate.productdetail.get'))
FIELDS = frozenset(('product_id', 'model_key', 'detail_url', 'title', 'evidence', 'content', 'markets',
                    'category', 'image_url', 'affiliate_url', 'theme', 'selection'))
EVIDENCE_FIELDS = frozenset(('method', 'product_id', 'request_id', 'observed_at', 'target_language',
                             'ship_to_country', 'response_sha256'))
FORBIDDEN_KEYS = frozenset(('secret', 'password', 'token', 'authorization', 'cookie', 'api_key', 'app_key', 'app_secret'))


class StoreError(Exception):
    """Stable, non-sensitive error suitable for a transport response."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _instant(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise StoreError('time_invalid')
    return value.astimezone(timezone.utc)


def _key(value: str, code: str) -> str:
    if not isinstance(value, str) or not KEY.fullmatch(value):
        raise StoreError(code)
    return value


def _sha(value: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise StoreError('commit_sha_invalid')
    return value


def _contains_sensitive_key(value) -> bool:
    if isinstance(value, dict):
        return any(not isinstance(k, str) or k.lower() in FORBIDDEN_KEYS or _contains_sensitive_key(v)
                   for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_sensitive_key(v) for v in value)
    return False


def _candidate(value: dict) -> tuple[str, str, str]:
    if not isinstance(value, dict) or set(value) - FIELDS or _contains_sensitive_key(value):
        raise StoreError('candidate_invalid')
    product_id = value.get('product_id')
    if not isinstance(product_id, str) or not PRODUCT_ID.fullmatch(product_id):
        raise StoreError('product_id_invalid')
    model_key = value.get('model_key')
    if model_key is not None and (not isinstance(model_key,str) or not model_key.strip() or len(model_key)>500):
        raise StoreError('model_key_invalid')
    title = value.get('title')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 1000:
        raise StoreError('candidate_invalid')
    detail_url = value.get('detail_url')
    try:
        parsed = urlsplit(detail_url) if isinstance(detail_url, str) else None
        if (parsed is None or parsed.scheme != 'https' or parsed.hostname not in ('aliexpress.com', 'www.aliexpress.com')
                or parsed.username is not None or parsed.password is not None or parsed.port is not None
                or parsed.path != f'/item/{product_id}.html' or parsed.query or parsed.fragment):
            raise ValueError()
    except ValueError:
        raise StoreError('detail_url_invalid') from None
    evidence = value.get('evidence')
    if (not isinstance(evidence, dict) or set(evidence) - EVIDENCE_FIELDS
            or evidence.get('method') not in METHODS or evidence.get('product_id') != product_id):
        raise StoreError('evidence_invalid')
    content = value.get('content')
    if not isinstance(content, dict) or set(content) != set(LANGUAGES):
        raise StoreError('locales_invalid')
    for locale in LANGUAGES:
        item = content[locale]
        if not isinstance(item, dict) or set(item) != {'name', 'headline', 'description'}:
            raise StoreError('locales_invalid')
        if any(not isinstance(item[k], str) or not item[k].strip() or len(item[k]) > 1500
               for k in ('name', 'description')):
            raise StoreError('locales_invalid')
        headline = item['headline']
        if isinstance(headline, str):
            valid_headline = bool(headline.strip()) and len(headline) <= 300
        elif isinstance(headline, list):
            valid_headline = bool(headline) and len(headline) <= 8 and all(
                isinstance(v, str) and v.strip() and len(v) <= 150 for v in headline)
        else:
            valid_headline = False
        if not valid_headline:
            raise StoreError('locales_invalid')
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError):
        raise StoreError('candidate_invalid') from None
    if len(encoded.encode('utf-8')) > 64_000:
        raise StoreError('candidate_invalid')
    return product_id, encoded, hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def _public(row: sqlite3.Row, *, include_candidate: bool = False) -> dict:
    result = {k: row[k] for k in ('request_id', 'product_id', 'state', 'claim_id', 'owner',
                                  'budget_day', 'commit_sha', 'deployment_id', 'reason',
                                  'created_at', 'updated_at')}
    if include_candidate:
        result['candidate'] = json.loads(row['candidate_json'])
    return result


class Store:
    """Transactional queue on one authoritative SQLite file.

    `verified=True` means the trusted caller has independently checked the
    corresponding Git commit or deployment; SQLite itself does not contact or
    attest those services. Recovery also requires a catalog/HEAD inspection
    conducted while all repository writers are locked.
    """
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('PRAGMA journal_mode = DELETE')
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE IF NOT EXISTS intake (
                request_id TEXT PRIMARY KEY, product_id TEXT NOT NULL UNIQUE,
                candidate_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('queued','reserved','committed','published','failed')),
                claim_id TEXT UNIQUE, owner TEXT, lease_until REAL, budget_day TEXT,
                commit_sha TEXT, deployment_id TEXT, reason TEXT,
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            )''')
            db.execute('CREATE INDEX IF NOT EXISTS intake_queue ON intake(state,created_at,request_id)')
            db.execute('CREATE INDEX IF NOT EXISTS intake_day ON intake(budget_day,state)')
            if 'model_key' not in {r['name'] for r in db.execute('PRAGMA table_info(intake)')}:
                db.execute('ALTER TABLE intake ADD COLUMN model_key TEXT')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS intake_model ON intake(model_key) WHERE model_key IS NOT NULL')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout = 30000')
        # DELETE journal mode permits a committed, closed DB to be snapshotted
        # into git without accidentally leaving committed data in a WAL sidecar.
        db.execute('PRAGMA synchronous = FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, request_id: str, candidate: dict, *, now: datetime | None = None) -> dict:
        _key(request_id, 'request_id_invalid')
        product_id, encoded, fingerprint = _candidate(candidate)
        timestamp = _instant(now).timestamp()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT * FROM intake WHERE request_id=?', (request_id,)).fetchone()
            if existing is not None:
                if existing['fingerprint'] != fingerprint:
                    raise StoreError('idempotency_conflict')
                return _public(existing)
            if db.execute('SELECT 1 FROM intake WHERE product_id=?', (product_id,)).fetchone():
                raise StoreError('duplicate_product')
            if candidate.get('model_key') is not None and db.execute('SELECT 1 FROM intake WHERE model_key=?',(candidate['model_key'],)).fetchone():
                raise StoreError('duplicate_model')
            db.execute('''INSERT INTO intake(request_id,product_id,candidate_json,fingerprint,state,created_at,updated_at,model_key)
                          VALUES (?,?,?,?,'queued',?,?,?)''', (request_id, product_id, encoded, fingerprint, timestamp, timestamp,candidate.get('model_key')))
            row = db.execute('SELECT * FROM intake WHERE request_id=?', (request_id,)).fetchone()
            return _public(row)

    def status(self, request_id: str) -> dict | None:
        _key(request_id, 'request_id_invalid')
        with self._connect() as db:
            row = db.execute('SELECT * FROM intake WHERE request_id=?', (request_id,)).fetchone()
            return _public(row) if row else None

    def status_batch(self, batch_id: str) -> list[dict]:
        if not isinstance(batch_id,str) or not re.fullmatch(r'[0-9a-f]{32}',batch_id):
            raise StoreError('batch_invalid')
        with self._connect() as db:
            return [_public(row) for row in db.execute('SELECT * FROM intake WHERE substr(request_id,1,33)=? ORDER BY created_at,request_id',(batch_id+':',))]

    def list_status(self, limit: int = 100) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise StoreError('limit_invalid')
        with self._connect() as db:
            rows = db.execute('SELECT * FROM intake ORDER BY created_at,request_id LIMIT ?', (limit,)).fetchall()
            return [_public(row) for row in rows]

    def outstanding(self) -> list[dict]:
        """All unfinished writer states, without truncating at a UI page size."""
        with self._connect() as db:
            rows = db.execute("SELECT * FROM intake WHERE state IN ('reserved','committed') ORDER BY created_at,request_id").fetchall()
            return [_public(row) for row in rows]

    def state_digest(self) -> str:
        """Fingerprint all public state transitions without exposing content."""
        with self._connect() as db:
            rows = db.execute('SELECT * FROM intake ORDER BY request_id').fetchall()
            state = [_public(row) for row in rows]
        payload = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def claim(self, day: str, owner: str, limit: int = 3, *, lease_seconds: int = 300,
              now: datetime | None = None) -> list[dict]:
        instant = _instant(now)
        _key(owner, 'owner_invalid')
        if day != instant.date().isoformat():
            raise StoreError('day_invalid')
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 3:
            raise StoreError('limit_invalid')
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or not 1 <= lease_seconds <= 86400:
            raise StoreError('lease_invalid')
        if (instant + timedelta(seconds=lease_seconds)).date() != instant.date():
            raise StoreError('day_end_window')
        timestamp = instant.timestamp()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            used = db.execute('SELECT count(*) FROM intake WHERE budget_day=?', (day,)).fetchone()[0]
            count = min(limit, max(0, 3 - used))
            if not count:
                return []
            pending = db.execute("SELECT * FROM intake WHERE state='queued' ORDER BY created_at,request_id LIMIT ?", (count,)).fetchall()
            result = []
            for item in pending:
                claim_id = str(uuid4())
                db.execute("""UPDATE intake SET state='reserved',claim_id=?,owner=?,lease_until=?,budget_day=?,updated_at=?
                              WHERE request_id=? AND state='queued'""",
                           (claim_id, owner, timestamp + lease_seconds, day, timestamp, item['request_id']))
                row = db.execute('SELECT * FROM intake WHERE request_id=?', (item['request_id'],)).fetchone()
                result.append(_public(row, include_candidate=True))
            return result

    def mark_committed(self, claim_id: str, owner: str, commit_sha: str, *, verified: bool = False,
                       now: datetime | None = None) -> dict:
        _key(claim_id, 'claim_id_invalid')
        _key(owner, 'owner_invalid')
        _sha(commit_sha)
        if verified is not True:
            raise StoreError('commit_not_verified')
        instant = _instant(now)
        timestamp = instant.timestamp()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone()
            if row is None:
                raise StoreError('claim_not_found')
            if row['state'] in ('committed', 'published'):
                if row['commit_sha'] != commit_sha:
                    raise StoreError('commit_conflict')
                return _public(row)
            if row['state'] != 'reserved' or row['owner'] != owner:
                raise StoreError('claim_owner_or_state_invalid')
            if row['lease_until'] <= timestamp:
                raise StoreError('lease_expired')
            day = instant.date().isoformat()
            if row['budget_day'] != day:
                # Caller must reserve the target day before any external write;
                # fail closed at midnight rather than silently exceed quota.
                raise StoreError('day_changed_reconcile_required')
            db.execute("UPDATE intake SET state='committed',commit_sha=?,updated_at=? WHERE claim_id=?", (commit_sha, timestamp, claim_id))
            return _public(db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone())

    def mark_published(self, claim_id: str, commit_sha: str, deploy_id: str, *, verified: bool = False,
                       now: datetime | None = None) -> dict:
        _key(claim_id, 'claim_id_invalid')
        _sha(commit_sha)
        if not isinstance(deploy_id, str) or not DEPLOYMENT.fullmatch(deploy_id):
            raise StoreError('deployment_id_invalid')
        if verified is not True:
            raise StoreError('deployment_not_verified')
        instant = _instant(now)
        timestamp = instant.timestamp()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone()
            if row is None:
                raise StoreError('claim_not_found')
            if row['state'] == 'published':
                if row['commit_sha'] != commit_sha or row['deployment_id'] != deploy_id:
                    raise StoreError('deployment_conflict')
                return _public(row)
            if row['state'] != 'committed' or row['commit_sha'] != commit_sha:
                raise StoreError('commit_mismatch')
            db.execute("UPDATE intake SET state='published',deployment_id=?,updated_at=? WHERE claim_id=?", (deploy_id, timestamp, claim_id))
            return _public(db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone())

    def fail(self, claim_id: str, owner: str, reason: str, *, now: datetime | None = None) -> dict:
        _key(claim_id, 'claim_id_invalid')
        _key(owner, 'owner_invalid')
        if not isinstance(reason, str) or not REASON.fullmatch(reason):
            raise StoreError('reason_invalid')
        timestamp = _instant(now).timestamp()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone()
            if row is None:
                raise StoreError('claim_not_found')
            if row['state'] == 'failed' and row['owner'] == owner and row['reason'] == reason:
                return _public(row)
            if row['state'] != 'reserved' or row['owner'] != owner:
                raise StoreError('claim_owner_or_state_invalid')
            db.execute("UPDATE intake SET state='failed',reason=?,updated_at=? WHERE claim_id=?", (reason, timestamp, claim_id))
            return _public(db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone())

    def recover_claim(self, claim_id: str, owner: str, observed_head_sha: str, catalog_contains_product: bool,
                      *, lease_seconds: int = 300, now: datetime | None = None) -> dict:
        """Reconcile an expired lease after an externally verified HEAD/catalog check.

        If the exact marketplace item is already in that head, record the head
        as committed; otherwise transfer the *same* claim without duplicating a
        budget reservation. The caller must hold the cross-job writer lock while
        verifying and acting on that evidence. Never infer absence from timeout.
        """
        _key(claim_id, 'claim_id_invalid')
        _key(owner, 'owner_invalid')
        _sha(observed_head_sha)
        if not isinstance(catalog_contains_product, bool):
            raise StoreError('catalog_evidence_invalid')
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int) or not 1 <= lease_seconds <= 86400:
            raise StoreError('lease_invalid')
        instant = _instant(now)
        timestamp = instant.timestamp()
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone()
            if row is None:
                raise StoreError('claim_not_found')
            if row['state'] != 'reserved' or row['lease_until'] > timestamp:
                raise StoreError('claim_not_expired')
            day = instant.date().isoformat()
            if catalog_contains_product:
                # Presence in HEAD alone does not prove which UTC day the
                # product was committed. Do not silently miscount that day.
                if row['budget_day'] != day:
                    raise StoreError('day_changed_reconcile_required')
                db.execute("UPDATE intake SET state='committed',owner=?,commit_sha=?,updated_at=? WHERE claim_id=?",
                           (owner, observed_head_sha, timestamp, claim_id))
                include = False
            else:
                if (instant + timedelta(seconds=lease_seconds)).date() != instant.date():
                    raise StoreError('day_end_window')
                if row['budget_day'] != day:
                    used = db.execute('SELECT count(*) FROM intake WHERE budget_day=?', (day,)).fetchone()[0]
                    if used >= 3:
                        raise StoreError('daily_limit')
                db.execute('UPDATE intake SET owner=?,lease_until=?,budget_day=?,updated_at=? WHERE claim_id=?',
                           (owner, timestamp + lease_seconds, day, timestamp, claim_id))
                include = True
            return _public(db.execute('SELECT * FROM intake WHERE claim_id=?', (claim_id,)).fetchone(), include_candidate=include)
