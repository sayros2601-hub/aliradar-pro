"""Fail-closed UTC limit for the one serialized daily catalog writer.

The file must be read and written only while every scheduled/manual writer
holds the same cross-job lock and starts from current main. Atomic file replace
is not a distributed lock and is not a substitute for the GitHub concurrency
group. Catalog and ledger are committed together before any deployment.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile

DAILY_MAX = 3
CATALOG_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
PRODUCT_ID = re.compile(r'^[1-9][0-9]{0,31}$')
SEED_DAY = '2026-11-10'
SEED_RUN = '42853498987'
SEED_IDS = frozenset(('find-064-book-light', 'find-065-spice-grinder', 'find-067-pill-organizer'))
VALIDATION_RUN = 'fluxixo-validation-20261110-01'


class LedgerError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def utc_day(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise LedgerError('time_invalid')
    return now.astimezone(timezone.utc).date().isoformat()


def _day(day):
    if not isinstance(day, str):
        raise LedgerError('day_invalid')
    try:
        parsed = date.fromisoformat(day)
    except ValueError:
        raise LedgerError('day_invalid') from None
    if parsed.isoformat() != day:
        raise LedgerError('day_invalid')
    return day


def _row(value, day):
    if not isinstance(value, dict):
        raise LedgerError('ledger_invalid')
    source = value.get('source')
    required = {'catalog_id', 'product_id', 'source'}
    if source == 'github_actions':
        required.add('run_id')
    if set(value) != required:
        raise LedgerError('ledger_invalid')
    catalog_id, product_id = value.get('catalog_id'), value.get('product_id')
    if not isinstance(catalog_id, str) or not CATALOG_ID.fullmatch(catalog_id):
        raise LedgerError('ledger_invalid')
    if source == 'github_actions':
        if (day != SEED_DAY or catalog_id not in SEED_IDS or product_id is not None
                or value.get('run_id') != SEED_RUN):
            raise LedgerError('ledger_invalid')
    elif source == 'api':
        if not isinstance(product_id, str) or not PRODUCT_ID.fullmatch(product_id):
            raise LedgerError('ledger_invalid')
    else:
        raise LedgerError('ledger_invalid')
    return value


def _validate(ledger):
    if not isinstance(ledger, dict) or set(ledger) != {'version', 'days', 'validation_runs'} or type(ledger['version']) is not int or ledger['version'] != 1 or not isinstance(ledger['days'], dict) or not isinstance(ledger['validation_runs'], dict):
        raise LedgerError('ledger_invalid')
    catalog_ids, product_ids = set(), set()
    for day, rows in ledger['days'].items():
        _day(day)
        if not isinstance(rows, list) or len(rows) > DAILY_MAX:
            raise LedgerError('ledger_invalid')
        for value in rows:
            item = _row(value, day)
            if item['catalog_id'] in catalog_ids:
                raise LedgerError('ledger_invalid')
            catalog_ids.add(item['catalog_id'])
            product_id = item['product_id']
            if product_id is not None:
                if product_id in product_ids:
                    raise LedgerError('ledger_invalid')
                product_ids.add(product_id)
    for run_id, entry in ledger['validation_runs'].items():
        if run_id != VALIDATION_RUN or not isinstance(entry, dict) or set(entry) != {'day', 'catalog_id', 'product_id', 'source'} or entry.get('day') != SEED_DAY:
            raise LedgerError('ledger_invalid')
        item = _row({k: entry[k] for k in ('catalog_id', 'product_id', 'source')}, SEED_DAY)
        if item['source'] != 'api' or item['catalog_id'] in catalog_ids or item['product_id'] in product_ids:
            raise LedgerError('ledger_invalid')
        catalog_ids.add(item['catalog_id'])
        product_ids.add(item['product_id'])
    # Seed is authoritative for this day and must remain intact. A missing or
    # edited seed cannot silently reset today's already-confirmed quota.
    seed = ledger['days'].get(SEED_DAY)
    if seed is not None:
        github = [item for item in seed if item['source'] == 'github_actions']
        if github and ({item['catalog_id'] for item in github} != SEED_IDS or len(github) != DAILY_MAX):
            raise LedgerError('ledger_invalid')
    return ledger


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def _require_seed(ledger):
    rows = ledger['days'].get(SEED_DAY)
    if (not isinstance(rows, list) or len(rows) != DAILY_MAX
            or {row.get('catalog_id') for row in rows} != SEED_IDS
            or any(row.get('source') != 'github_actions' or row.get('run_id') != SEED_RUN
                   or row.get('product_id') is not None for row in rows)):
        raise LedgerError('ledger_seed_missing')


def read_ledger(path) -> dict:
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 10_000_000:
            raise LedgerError('ledger_missing')
        value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_object_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
        _validate(value)
        _require_seed(value)
        return value
    except LedgerError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError):
        raise LedgerError('ledger_invalid') from None


def remaining(ledger: dict, day: str, requested: int = 3) -> int:
    _validate(ledger)
    _day(day)
    if isinstance(requested, bool) or not isinstance(requested, int) or not 0 <= requested <= DAILY_MAX:
        raise LedgerError('requested_invalid')
    return min(requested, DAILY_MAX - len(ledger['days'].get(day, [])))


def record(ledger: dict, day: str, records: list[dict]) -> dict:
    _validate(ledger)
    _day(day)
    if not isinstance(records, list) or len(records) > DAILY_MAX:
        raise LedgerError('records_invalid')
    result = deepcopy(ledger)
    for item in records:
        _row(item, day)
        existing = next(((old_day, row) for old_day, rows in result['days'].items() for row in rows
                         if row['catalog_id'] == item['catalog_id']), None)
        if existing:
            if existing[0] == day and existing[1] == item:
                continue
            raise LedgerError('catalog_id_conflict')
        if any(row['catalog_id'] == item['catalog_id'] for row in result['validation_runs'].values()):
            raise LedgerError('catalog_id_conflict')
        if item['product_id'] is not None and any(row['product_id'] == item['product_id']
                for rows in result['days'].values() for row in rows):
            raise LedgerError('product_id_conflict')
        if item['product_id'] is not None and any(row['product_id'] == item['product_id'] for row in result['validation_runs'].values()):
            raise LedgerError('product_id_conflict')
        if len(result['days'].get(day, [])) >= DAILY_MAX:
            raise LedgerError('daily_limit')
        result['days'].setdefault(day, []).append(deepcopy(item))
    return _validate(result)


def remaining_validation(ledger: dict, day: str, run_id: str, *, now: datetime | None = None) -> int:
    """Only the explicitly authorized single validation can use this slot."""
    _validate(ledger)
    _require_seed(ledger)
    if _day(day) != SEED_DAY or run_id != VALIDATION_RUN:
        raise LedgerError('validation_not_authorized')
    if run_id in ledger['validation_runs']:
        return 0
    if utc_day(now) != day:
        raise LedgerError('validation_not_authorized')
    return 1


def record_validation(ledger: dict, day: str, run_id: str, item: dict, *, now: datetime | None = None) -> dict:
    _validate(ledger)
    _require_seed(ledger)
    if _day(day) != SEED_DAY or run_id != VALIDATION_RUN:
        raise LedgerError('validation_not_authorized')
    _row(item, day)
    if item['source'] != 'api':
        raise LedgerError('validation_invalid')
    entry = {'day': day, **deepcopy(item)}
    existing = ledger['validation_runs'].get(run_id)
    if existing is not None:
        if existing == entry:
            return deepcopy(ledger)
        raise LedgerError('validation_conflict')
    if utc_day(now) != day:
        raise LedgerError('validation_not_authorized')
    for rows in ledger['days'].values():
        for row in rows:
            if row['catalog_id'] == item['catalog_id']:
                raise LedgerError('catalog_id_conflict')
            if row['product_id'] is not None and row['product_id'] == item['product_id']:
                raise LedgerError('product_id_conflict')
    result = deepcopy(ledger)
    result['validation_runs'][run_id] = entry
    return _validate(result)


def verify_catalog(ledger: dict, catalog: dict) -> None:
    _validate(ledger)
    _require_seed(ledger)
    if not isinstance(catalog, dict) or not isinstance(catalog.get('products'), list):
        raise LedgerError('ledger_catalog_mismatch')
    by_id = {}
    for item in catalog['products']:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in by_id:
            raise LedgerError('ledger_catalog_mismatch')
        by_id[item['id']] = item
    for rows in ledger['days'].values():
        for row in rows:
            product = by_id.get(row['catalog_id'])
            if product is None or (row['product_id'] is not None and product.get('sourceProductId') != row['product_id']):
                raise LedgerError('ledger_catalog_mismatch')
    for row in ledger['validation_runs'].values():
        product = by_id.get(row['catalog_id'])
        if product is None or product.get('sourceProductId') != row['product_id']:
            raise LedgerError('ledger_catalog_mismatch')


def atomic_write(path, ledger: dict) -> None:
    _validate(ledger)
    _require_seed(ledger)
    path = Path(path)
    if path.is_symlink():
        raise LedgerError('ledger_write_failed')
    temp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix='.ledger-', suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            json.dump(ledger, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except OSError:
        raise LedgerError('ledger_write_failed') from None
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
