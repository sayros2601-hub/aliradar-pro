"""One Jerusalem-evening batch, with durable image allowance and publish recovery.

All callers must hold the workflow's shared concurrency lock and use current
main. Commit a reservation BEFORE generating images, and commit prepared state
with the catalog BEFORE deployment. Atomic replacement is not a distributed lock.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .daily_ledger import DAILY_MAX, LedgerError, read_ledger, remaining


class ScheduleError(Exception):
    pass


def _date(value):
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except (ValueError, TypeError):
        raise ScheduleError('day_invalid') from None
    return value


def _instant(now):
    value = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ScheduleError('time_invalid')
    return value.astimezone(timezone.utc)


def _local(instant):
    try:
        return instant.astimezone(ZoneInfo('Asia/Jerusalem'))
    except ZoneInfoNotFoundError:
        raise ScheduleError('jerusalem_timezone_data_missing') from None


def _validate_state(state):
    if (not isinstance(state, dict) or set(state) != {'version', 'days'}
            or type(state['version']) is not int or state['version'] != 1
            or not isinstance(state['days'], dict)):
        raise ScheduleError('publication_state_invalid')
    for day, entry in state['days'].items():
        _date(day)
        required = {'status', 'reserved_count', 'baseline_count', 'utc_day'}
        if (not isinstance(entry, dict)
                or set(entry) not in (required, required | {'published_day'})
                or entry['status'] not in ('preparing', 'prepared', 'published')):
            raise ScheduleError('publication_state_invalid')
        if 'published_day' in entry:
            _date(entry['published_day'])
            if entry['status'] != 'published' or entry['published_day'] < day:
                raise ScheduleError('publication_state_invalid')
        _date(entry['utc_day'])
        if (date.fromisoformat(day) - date.fromisoformat(entry['utc_day'])).days not in (0, 1):
            raise ScheduleError('publication_state_invalid')
        for name in ('reserved_count', 'baseline_count'):
            if type(entry[name]) is not int or not 0 <= entry[name] <= DAILY_MAX:
                raise ScheduleError('publication_state_invalid')
        if (entry['reserved_count'] + entry['baseline_count'] > DAILY_MAX
                or (entry['status'] == 'preparing' and entry['reserved_count'] == 0)):
            raise ScheduleError('publication_state_invalid')
    return state


def _done(ledger, day):
    # Reuse the existing fail-closed ledger validator and its global UTC cap.
    return DAILY_MAX - remaining(ledger, day, DAILY_MAX)


def _markets(day):
    ordinal = date.fromisoformat(day).toordinal()
    groups = (('RU', 'IL', 'FR'), ('US', 'MX', 'BR'))
    group = groups[ordinal % 2]
    offset = (ordinal // 2) % len(group)
    return list(group[offset:] + group[:offset])


def _covered(ledger, entry):
    return _done(ledger, entry['utc_day']) >= entry['baseline_count'] + entry['reserved_count']


def plan(ledger, state, *, now=None, manual_count=None):
    """Pure plan. Preparation is permitted once; publication can safely retry."""
    _validate_state(state)
    instant = _instant(now)
    local = _local(instant)
    day, utc_day = local.date().isoformat(), instant.date().isoformat()
    done = _done(ledger, utc_day)
    if manual_count is not None and (type(manual_count) is not int or not 0 <= manual_count <= DAILY_MAX):
        raise ScheduleError('count_invalid')
    entry = state['days'].get(day)
    # Leave two hours before local midnight. The workflow rechecks immediately
    # before a deployment capped at 15 minutes, so its public date cannot roll.
    publication_due = 19 <= local.hour < 22
    result = {'skip': True, 'add_count': 0, 'markets': _markets(day), 'day': day,
              'publication_day': day, 'action': 'skip', 'reason': '',
              'record_publication': False, 'publish': False}

    def answer(action, reason, count=0, track=False):
        return {**result, 'skip': action == 'skip', 'add_count': count,
                'action': action, 'reason': reason, 'record_publication': track,
                'publish': action != 'skip' and
                           (publication_due or (manual_count is not None and not track))}

    published_today = any(
        row['status'] == 'published' and row.get('published_day', batch_day) == day
        for batch_day, row in state['days'].items()
    )
    pending = None
    for batch_day, row in sorted(state['days'].items()):
        if batch_day > day or row['status'] == 'published':
            continue
        covered = _covered(ledger, row)
        if row['status'] == 'prepared' and not covered:
            raise ScheduleError('publication_ledger_mismatch')
        if covered and pending is None:
            pending = batch_day
    if pending is not None and not published_today:
        # A failed deployment must publish its existing batch before a later
        # day can create another batch. Otherwise one release could expose six
        # new products while both individual ledger days appear within quota.
        result.update(day=pending, markets=_markets(pending))
    if manual_count == 0:
        return answer('recover', 'manual_rebuild', track=pending is not None and not published_today)
    if published_today:
        return answer('skip', 'published')
    if pending is not None:
        if not publication_due:
            return answer('skip', 'waiting_publication')
        return answer('recover', 'prepared_catalog', track=True)
    if ((manual_count is None and local.hour * 60 + local.minute < 17 * 60 + 30)
            or local.hour >= 22):
        return answer('skip', 'outside_daily_window')
    if entry:
        if entry['status'] == 'published':
            return answer('skip', 'published')
        return answer('skip', 'interrupted_prepare')
    # An uncertain image reservation still consumes its UTC day's allowance,
    # even if a manual run happens just after the local date changes.
    if any(e['utc_day'] == utc_day and e['reserved_count'] for e in state['days'].values()):
        return answer('skip', 'utc_day_already_reserved')
    count = min(DAILY_MAX - done, DAILY_MAX if manual_count is None else manual_count)
    if count == 0:
        if not publication_due:
            return answer('skip', 'waiting_publication')
        return answer('recover', 'existing_daily_quota', track=True)
    return answer('prepare', 'daily_batch_due', count, track=True)


def guard_publication(ledger, state, publication_day, *, now=None, manual_count=None):
    """Recheck the built release's day/window immediately before deployment."""
    _date(publication_day)
    current = plan(ledger, state, now=now, manual_count=manual_count)
    if not current['publish'] or current['publication_day'] != publication_day:
        raise ScheduleError('publication_window_closed_or_day_changed')
    return current


def reserve(ledger, state, day, count, *, now=None):
    """Reserve allowance once; persist and push this before starting generation."""
    _date(day)
    instant = _instant(now)
    planned = plan(ledger, state, now=instant, manual_count=count)
    if (planned['day'] != day or planned['action'] != 'prepare'
            or planned['add_count'] != count):
        raise ScheduleError('reservation_not_allowed')
    result = deepcopy(state)
    utc_day = instant.date().isoformat()
    result['days'][day] = {'status': 'preparing', 'reserved_count': count,
                           'baseline_count': _done(ledger, utc_day), 'utc_day': utc_day}
    return _validate_state(result)


def mark_prepared(ledger, state, day, *, now=None):
    _validate_state(state)
    _date(day)
    result = deepcopy(state)
    entry = result['days'].get(day)
    if entry is None:
        instant = _instant(now)
        utc_day = instant.date().isoformat()
        # Migration: existing full ledger quota still needs one deploy; no new
        # image reservation is created and no product is generated.
        if _local(instant).date().isoformat() != day or _done(ledger, utc_day) != DAILY_MAX:
            raise ScheduleError('prepared_reservation_missing')
        entry = {'status': 'prepared', 'reserved_count': 0,
                 'baseline_count': DAILY_MAX, 'utc_day': utc_day}
        result['days'][day] = entry
    elif not _covered(ledger, entry):
        raise ScheduleError('prepared_catalog_incomplete')
    elif entry['status'] != 'published':
        entry['status'] = 'prepared'
    return _validate_state(result)


def mark_published(ledger, state, day, *, now=None):
    _validate_state(state)
    _date(day)
    entry = state['days'].get(day)
    if entry is None or entry['status'] not in ('prepared', 'published') or not _covered(ledger, entry):
        raise ScheduleError('publication_not_prepared')
    result = deepcopy(state)
    if entry['status'] == 'published':
        return result
    published_day = _local(_instant(now)).date().isoformat()
    if any(row['status'] == 'published' and row.get('published_day', batch_day) == published_day
           for batch_day, row in state['days'].items() if batch_day != day):
        raise ScheduleError('publication_day_already_used')
    result['days'][day]['status'] = 'published'
    result['days'][day]['published_day'] = published_day
    return _validate_state(result)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def read_state(path):
    path = Path(path)
    if path.is_symlink():
        raise ScheduleError('publication_state_invalid')
    if not path.exists():
        return {'version': 1, 'days': {}}
    try:
        if not path.is_file() or path.stat().st_size > 10_000_000:
            raise ValueError()
        value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
        return _validate_state(value)
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ScheduleError('publication_state_invalid') from None


def write_state(path, state):
    _validate_state(state)
    path = Path(path)
    if path.is_symlink():
        raise ScheduleError('publication_state_write_failed')
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.publication-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        raise ScheduleError('publication_state_write_failed') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'guard-publication', 'reserve', 'mark-prepared', 'mark-published'))
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--now', help='Aware ISO timestamp for offline diagnosis')
    parser.add_argument('--output', help='Append plan outputs to the GitHub Actions output file')
    parser.add_argument('--manual-count', type=int)
    parser.add_argument('--day')
    parser.add_argument('--count', type=int)
    args = parser.parse_args()
    try:
        now = datetime.fromisoformat(args.now) if args.now else None
        ledger, state = read_ledger(args.ledger), read_state(args.state)
        if args.command == 'guard-publication':
            guard_publication(ledger, state, args.day, now=now, manual_count=args.manual_count)
            print(f'{args.day}: publication window verified')
        elif args.command == 'plan':
            result = plan(ledger, state, now=now, manual_count=args.manual_count)
            if args.output:
                with open(args.output, 'a', encoding='utf-8') as stream:
                    for name, value in result.items():
                        if isinstance(value, bool):
                            value = 'true' if value else 'false'
                        elif isinstance(value, list):
                            value = ','.join(value)
                        stream.write(f'{name}={value}\n')
            print(json.dumps(result, ensure_ascii=False))
        else:
            if args.command == 'reserve':
                updated = reserve(ledger, state, args.day, args.count, now=now)
            elif args.command == 'mark-prepared':
                updated = mark_prepared(ledger, state, args.day, now=now)
            else:
                updated = mark_published(ledger, state, args.day, now=now)
            write_state(args.state, updated)
            print(f'{args.day}: {updated["days"][args.day]["status"]}')
    except (ScheduleError, LedgerError, ValueError, OSError) as error:
        parser.exit(1, f'Daily schedule stopped: {error}\n')


if __name__ == '__main__':
    main()
