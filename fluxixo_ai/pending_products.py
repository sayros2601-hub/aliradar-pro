"""Durable pending candidates. The daily workflow serializes checkout/commit writers.

SQLite protects local claims; GitHub's shared concurrency group protects separate
runner checkouts. This is not a lock for unrelated clients or another repository.
Only public candidate data and validated copy belong here, never credentials.
Terminal source versions and copy journals outlive queue rows: rediscovery,
changed URLs and process restarts must not replenish exhausted AI attempts.
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
            db.execute('''CREATE TABLE IF NOT EXISTS pending_terminals (
                product_id TEXT PRIMARY KEY, kind TEXT NOT NULL, source_version TEXT NOT NULL,
                reason TEXT NOT NULL, updated REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS pending_source_versions (
                product_id TEXT NOT NULL, kind TEXT NOT NULL, source_version TEXT NOT NULL,
                first_seen REAL NOT NULL, reason TEXT NOT NULL,
                PRIMARY KEY(product_id,kind,source_version))''')
            db.execute('''CREATE TABLE IF NOT EXISTS pending_copy_journals (
                product_id TEXT PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL)''')

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
            row = db.execute('''SELECT p.product_id,p.payload FROM pending p
                WHERE p.next_attempt<=? AND p.lease_until<=?
                AND NOT EXISTS (SELECT 1 FROM pending_terminals t WHERE t.product_id=p.product_id)
                ORDER BY p.next_attempt, p.created, p.product_id LIMIT 1''', (now, now)).fetchone()
            if not row:
                return None
            db.execute("UPDATE pending SET lease_until=?,updated=?,attempts=attempts+1,reason='working' WHERE product_id=?",
                       (now + max(1, lease), now, row[0]))
            return json.loads(row[1])

    def is_due(self, product_id, *, now=None):
        now = time.time() if now is None else now
        with self._db() as db:
            if db.execute('SELECT 1 FROM pending_terminals WHERE product_id=?', (str(product_id),)).fetchone():
                return False
            row = db.execute('SELECT next_attempt,lease_until FROM pending WHERE product_id=?', (str(product_id),)).fetchone()
        return row is None or max(row) <= now

    def terminal_info(self, product_id):
        with self._db() as db:
            row = db.execute('SELECT kind,reason,source_version FROM pending_terminals WHERE product_id=?',
                             (str(product_id),)).fetchone()
        return dict(zip(('kind', 'reason', 'source_version'), row)) if row else None

    def parked_candidate(self, product_id):
        """Public saved seller data for one explicit, non-AI recheck request."""
        with self._db() as db:
            row = db.execute('''SELECT p.payload FROM pending p JOIN pending_terminals t
                ON t.product_id=p.product_id WHERE p.product_id=?''', (str(product_id),)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _checked_source_version(source_version):
        if not isinstance(source_version, str) or not re.fullmatch(r'[0-9a-f]{64}', source_version):
            raise ValueError('verified_source_version_required')
        return source_version

    def park(self, product_id, reason, *, source_version, kind, now=None):
        """Stop automatic work for exhausted copy/actual-pixel source versions.

        ``source_version`` comes from the bounded copy/media engine, never a URL
        or a refreshed candidate fingerprint. Those engines retain their own
        attempts and drafts; parking does not replace or reset their journals.
        """
        source_version = self._checked_source_version(source_version)
        if kind not in ('copy', 'media'):
            raise ValueError('terminal_kind_invalid')
        now = time.time() if now is None else now
        pid = str(product_id)
        safe_reason = re.sub(r'[^a-z0-9_-]', '_', str(reason).lower())[:100]
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM pending WHERE product_id=?', (pid,)).fetchone():
                raise ValueError('pending_product_missing')
            db.execute('''INSERT INTO pending_source_versions(product_id,kind,source_version,first_seen,reason)
                VALUES(?,?,?,?,?) ON CONFLICT(product_id,kind,source_version) DO UPDATE SET reason=excluded.reason''',
                       (pid, kind, source_version, now, safe_reason))
            db.execute('''INSERT INTO pending_terminals(product_id,kind,source_version,reason,updated)
                VALUES(?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET
                kind=excluded.kind,source_version=excluded.source_version,reason=excluded.reason,updated=excluded.updated''',
                       (pid, kind, source_version, safe_reason, now))
            db.execute('UPDATE pending SET lease_until=0,reason=?,updated=? WHERE product_id=?',
                       (safe_reason, now, pid))
        from .state_checkpoint import checkpoint
        checkpoint()

    def reconsider(self, product_id, *, source_version, now=None):
        """Admit an explicitly re-submitted, independently verified NEW source.

        No timer or discovery refresh calls this method. For unchanged URLs the
        media resolver must fetch/decode seller pixels and prove a new digest;
        copy versions bind the normalized seller text. A version
        previously admitted or stopped for this kind never gets another reset.
        """
        source_version = self._checked_source_version(source_version)
        now = time.time() if now is None else now
        pid = str(product_id)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT kind FROM pending_terminals WHERE product_id=?', (pid,)).fetchone()
            if not row or db.execute('''SELECT 1 FROM pending_source_versions
                    WHERE product_id=? AND kind=? AND source_version=?''', (pid, row[0], source_version)).fetchone():
                return False
            db.execute('''INSERT INTO pending_source_versions(product_id,kind,source_version,first_seen,reason)
                VALUES(?,?,?,?,?)''', (pid, row[0], source_version, now, 'explicit_source_change'))
            db.execute('DELETE FROM pending_terminals WHERE product_id=?', (pid,))
            db.execute("UPDATE pending SET lease_until=0,next_attempt=?,updated=?,reason='source_version_changed' WHERE product_id=?",
                       (now, now, pid))
        from .state_checkpoint import checkpoint
        checkpoint()
        return True

    def defer(self, product_id, reason, *, retry_at=None, now=None):
        now = time.time() if now is None else now
        safe_reason = re.sub(r'[^a-z0-9_-]', '_', str(reason).lower())[:100]
        with self._db() as db:
            row = db.execute('SELECT attempts FROM pending WHERE product_id=?', (str(product_id),)).fetchone()
            backoff = min(86400, 900 * 2 ** min(7, max(0, (row[0] if row else 1) - 1)))
            when = max(now + 60, float(retry_at) if retry_at is not None else now + backoff)
            db.execute('''UPDATE pending SET lease_until=0,next_attempt=?,reason=?,updated=? WHERE product_id=?
                AND NOT EXISTS (SELECT 1 FROM pending_terminals t WHERE t.product_id=pending.product_id)''',
                       (when, safe_reason, now, str(product_id)))

    def hold(self, product_id, *, now=None, lease=900):
        now = time.time() if now is None else now
        with self._db() as db:
            db.execute("""UPDATE pending SET attempts=attempts+CASE WHEN lease_until<=? THEN 1 ELSE 0 END,
                lease_until=max(lease_until,?), reason='working' WHERE product_id=?
                AND NOT EXISTS (SELECT 1 FROM pending_terminals t WHERE t.product_id=pending.product_id)""",
                       (now, now + lease, str(product_id)))

    def save_text(self, product_id, bundle, *, now=None):
        with self._db() as db:
            db.execute('UPDATE pending SET copy=?,updated=? WHERE product_id=?',
                       (json.dumps(bundle, ensure_ascii=False), time.time() if now is None else now, str(product_id)))

    def text(self, product_id):
        with self._db() as db:
            row = db.execute('SELECT copy FROM pending WHERE product_id=?', (str(product_id),)).fetchone()
        return json.loads(row[0]) if row and row[0] else None

    def copy_state(self, product_id):
        """Return the complete source-version copy journal, never just a cache."""
        with self._db() as db:
            row = db.execute('SELECT state FROM pending_copy_journals WHERE product_id=?',
                             (str(product_id),)).fetchone()
        return json.loads(row[0]) if row else {}

    def save_copy_state(self, product_id, state, *, now=None):
        if not isinstance(state, dict):
            raise ValueError('copy_state_invalid')
        payload = json.dumps(state, ensure_ascii=False, allow_nan=False)
        with self._db() as db:
            db.execute('''INSERT INTO pending_copy_journals(product_id,state,updated) VALUES(?,?,?)
                ON CONFLICT(product_id) DO UPDATE SET state=excluded.state,updated=excluded.updated''',
                       (str(product_id), payload, time.time() if now is None else now))
        from .state_checkpoint import checkpoint
        checkpoint()

    def complete(self, product_id):
        with self._db() as db:
            db.execute('DELETE FROM pending WHERE product_id=?', (str(product_id),))

    def reconcile(self, catalog):
        with self._db() as db:
            db.executemany('DELETE FROM pending WHERE product_id=?',
                           [(str(p['sourceProductId']),) for p in catalog if p.get('sourceProductId')])

    def exclusions(self):
        """Discovery must not bypass a persisted lease, backoff or terminal stop."""
        with self._db() as db:
            rows = db.execute('SELECT product_id,payload FROM pending ORDER BY created,product_id').fetchall()
            archived = db.execute('''SELECT t.product_id FROM pending_terminals t
                WHERE NOT EXISTS (SELECT 1 FROM pending p WHERE p.product_id=t.product_id)
                ORDER BY t.product_id''').fetchall()
        return [{'id': 'auto-' + pid, 'sourceProductId': pid, 'sourceTitle': json.loads(payload).get('title', '')}
                for pid, payload in rows] + [
                    {'id': 'auto-' + pid, 'sourceProductId': pid, 'sourceTitle': ''} for (pid,) in archived]
