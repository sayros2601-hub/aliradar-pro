"""Durable pending candidates. The daily workflow serializes checkout/commit writers.

SQLite protects local claims; GitHub's shared concurrency group protects separate
runner checkouts. This is not a lock for unrelated clients or another repository.
Only public candidate data and validated copy belong here, never credentials.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from contextlib import contextmanager


class PendingProducts:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS pending (
                product_id TEXT PRIMARY KEY, payload TEXT NOT NULL, fingerprint TEXT NOT NULL,
                created REAL NOT NULL, updated REAL NOT NULL, next_attempt REAL NOT NULL,
                lease_until REAL NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT 'pending', copy TEXT)''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, candidate, *, now=None):
        now = time.time() if now is None else now
        clean = {k: v for k, v in candidate.items() if not k.startswith('_')}
        pid = str(clean['product_id'])
        if not re.fullmatch(r'[0-9]{1,32}', pid):
            raise ValueError('invalid_pending_product_id')
        payload = json.dumps(clean, sort_keys=True, ensure_ascii=False)
        source_context = {k: clean.get(k) for k in ('product_id', 'title', 'image_url', 'image_urls', 'category', 'task', 'model_key')}
        fingerprint = hashlib.sha256(json.dumps(source_context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._db() as db:
            # Changed source data invalidates cached copy but preserves age and fairness.
            db.execute('''INSERT INTO pending(product_id,payload,fingerprint,created,updated,next_attempt)
                VALUES(?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET
                payload=excluded.payload, updated=excluded.updated,
                copy=CASE WHEN pending.fingerprint=excluded.fingerprint THEN pending.copy ELSE NULL END,
                fingerprint=excluded.fingerprint''', (pid, payload, fingerprint, now, now, now))
        from .state_checkpoint import checkpoint
        checkpoint()

    def claim(self, *, now=None, lease=900):
        now = time.time() if now is None else now
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('''SELECT product_id,payload FROM pending
                WHERE next_attempt<=? AND lease_until<=?
                ORDER BY next_attempt, created, product_id LIMIT 1''', (now, now)).fetchone()
            if not row:
                return None
            db.execute("UPDATE pending SET lease_until=?,updated=?,attempts=attempts+1,reason='working' WHERE product_id=?",
                       (now + max(1, lease), now, row[0]))
            return json.loads(row[1])

    def is_due(self, product_id, *, now=None):
        now = time.time() if now is None else now
        with self._db() as db:
            row = db.execute('SELECT next_attempt,lease_until FROM pending WHERE product_id=?', (str(product_id),)).fetchone()
        return row is None or max(row) <= now

    def defer(self, product_id, reason, *, retry_at=None, now=None):
        now = time.time() if now is None else now
        safe_reason = re.sub(r'[^a-z0-9_-]', '_', str(reason).lower())[:100]
        with self._db() as db:
            row = db.execute('SELECT attempts FROM pending WHERE product_id=?', (str(product_id),)).fetchone()
            backoff = min(86400, 900 * 2 ** min(7, max(0, (row[0] if row else 1) - 1)))
            when = max(now + 60, float(retry_at) if retry_at is not None else now + backoff)
            db.execute('UPDATE pending SET lease_until=0,next_attempt=?,reason=?,updated=? WHERE product_id=?',
                       (when, safe_reason, now, str(product_id)))

    def hold(self, product_id, *, now=None, lease=900):
        now = time.time() if now is None else now
        with self._db() as db:
            db.execute("UPDATE pending SET attempts=attempts+CASE WHEN lease_until<=? THEN 1 ELSE 0 END, lease_until=max(lease_until,?), reason='working' WHERE product_id=?",
                       (now, now + lease, str(product_id)))

    def save_text(self, product_id, bundle, *, now=None):
        with self._db() as db:
            db.execute('UPDATE pending SET copy=?,updated=? WHERE product_id=?',
                       (json.dumps(bundle, ensure_ascii=False), time.time() if now is None else now, str(product_id)))

    def text(self, product_id):
        with self._db() as db:
            row = db.execute('SELECT copy FROM pending WHERE product_id=?', (str(product_id),)).fetchone()
        return json.loads(row[0]) if row and row[0] else None

    def complete(self, product_id):
        with self._db() as db:
            db.execute('DELETE FROM pending WHERE product_id=?', (str(product_id),))

    def reconcile(self, catalog):
        with self._db() as db:
            db.executemany('DELETE FROM pending WHERE product_id=?',
                           [(str(p['sourceProductId']),) for p in catalog if p.get('sourceProductId')])

    def exclusions(self):
        """Discovery must not bypass a persisted lease/backoff by finding it again."""
        with self._db() as db:
            rows = db.execute('SELECT product_id,payload FROM pending ORDER BY created,product_id').fetchall()
        return [{'id': 'auto-' + pid, 'sourceProductId': pid, 'sourceTitle': json.loads(payload).get('title', '')}
                for pid, payload in rows]
