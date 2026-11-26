"""Durable SQLite rolling-24h budget guard for free Cloudflare Workers AI image calls.

Cloudflare Workers Free allocates 10,000 Neurons per day. Reserving conservatively
before each remote image request keeps combined image + text/vision failover usage
safely inside the free tier without unexpected overages.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import time

MODEL_COSTS = {
    '9b': 1600,     # @cf/black-forest-labs/flux-2-klein-9b (1024x1024 + reference is ~1,546 Neurons)
    '4b': 200,      # @cf/black-forest-labs/flux-2-klein-4b (1024x1024 + reference is ~126 Neurons)
    'schnell': 300, # @cf/black-forest-labs/flux-1-schnell (fallback)
}
DEFAULT_NEURON_LIMIT = 8000
DEFAULT_CALL_LIMIT = 6
DEFAULT_BUDGET_PATH = Path(__file__).resolve().parents[1] / 'data/fluxixo_cf_image_usage.sqlite3'


class BudgetExhausted(RuntimeError):
    """Raised when reserving another FLUX.2 image call would exceed the 24h free cap."""

    def __init__(self, code: str = 'cf_image_daily_budget', retry_at: float | None = None):
        self.code = code
        self.retry_at = float(retry_at if retry_at is not None else time.time() + 3600)
        super().__init__(code)


def infer_model_tag(model_tag: str | None) -> str:
    key = str(model_tag or '9b').strip().lower()
    if 'schnell' in key:
        return 'schnell'
    if '4b' in key:
        return '4b'
    return '9b'


def cost_for_model(model_tag: str | None) -> int:
    return MODEL_COSTS[infer_model_tag(model_tag)]


def _budget_path(path=None) -> Path:
    if path is not None:
        return Path(path)
    return Path(os.environ.get('FLUXIXO_CF_IMAGE_BUDGET_PATH') or DEFAULT_BUDGET_PATH)


def _limits(neuron_limit=None, call_limit=None) -> tuple[int, int]:
    def _parse(explicit, env_name, fallback):
        if explicit is not None:
            return max(0, int(explicit))
        raw = os.environ.get(env_name, '').strip()
        if raw:
            try:
                return max(0, int(raw))
            except ValueError:
                pass
        return fallback

    return (
        _parse(neuron_limit, 'FLUXIXO_CF_IMAGE_DAILY_NEURONS', DEFAULT_NEURON_LIMIT),
        _parse(call_limit, 'FLUXIXO_CF_IMAGE_DAILY_CALLS', DEFAULT_CALL_LIMIT),
    )


@contextmanager
def _connect(path):
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    try:
        # Rollback journal (no WAL) so CI git checkpoints capture one atomic file.
        db.execute('PRAGMA synchronous=FULL')
        db.execute(
            'CREATE TABLE IF NOT EXISTS image_requests '
            '(id INTEGER PRIMARY KEY, model TEXT NOT NULL, neurons INTEGER NOT NULL, at REAL NOT NULL)'
        )
        db.execute('CREATE INDEX IF NOT EXISTS image_request_times ON image_requests(at)')
        with db:
            yield db
    finally:
        db.close()


def usage_snapshot(*, path=None, now=None, neuron_limit=None, call_limit=None) -> dict:
    ts = float(now if now is not None else time.time())
    n_lim, c_lim = _limits(neuron_limit, call_limit)
    with _connect(_budget_path(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM image_requests WHERE at <= ?', (ts - 86400,))
        calls, neurons, first_at = db.execute(
            'SELECT count(*), coalesce(sum(neurons), 0), min(at) FROM image_requests'
        ).fetchone()
    return {
        'calls': int(calls or 0),
        'neurons': int(neurons or 0),
        'call_limit': c_lim,
        'neuron_limit': n_lim,
        'oldest_at': first_at,
    }


def can_spend(model_tag: str = '9b', *, path=None, now=None, neuron_limit=None, call_limit=None) -> bool:
    cost = cost_for_model(model_tag)
    snap = usage_snapshot(path=path, now=now, neuron_limit=neuron_limit, call_limit=call_limit)
    return (snap['calls'] + 1 <= snap['call_limit']) and (snap['neurons'] + cost <= snap['neuron_limit'])


def reserve(model_tag: str = '9b', *, path=None, now=None, neuron_limit=None, call_limit=None) -> dict:
    """Atomically verify and record one FLUX.2 image generation reservation before remote I/O."""
    ts = float(now if now is not None else time.time())
    key = infer_model_tag(model_tag)
    cost = cost_for_model(key)
    n_lim, c_lim = _limits(neuron_limit, call_limit)
    with _connect(_budget_path(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM image_requests WHERE at <= ?', (ts - 86400,))
        calls, neurons, first_at = db.execute(
            'SELECT count(*), coalesce(sum(neurons), 0), min(at) FROM image_requests'
        ).fetchone()
        calls = int(calls or 0)
        neurons = int(neurons or 0)
        if calls + 1 > c_lim or neurons + cost > n_lim:
            retry_at = (float(first_at) + 86400.01) if first_at is not None else (ts + 3600.0)
            raise BudgetExhausted('cf_image_daily_budget', retry_at)
        db.execute('INSERT INTO image_requests(model, neurons, at) VALUES (?, ?, ?)', (key, cost, ts))
    return {'model': key, 'neurons': cost, 'calls': calls + 1, 'used_neurons': neurons + cost}
