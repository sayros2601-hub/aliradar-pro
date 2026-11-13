"""Behavioral coverage for the single daily batch and publication recovery."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fluxixo_ai import daily_schedule as schedule
from fluxixo_ai.daily_ledger import record

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc)
DAY = '2026-11-14'


def seed_ledger():
    live = json.loads((ROOT / 'data/fluxixo_daily_ledger.json').read_text(encoding='utf-8'))
    return {'version': 1, 'days': {'2026-11-10': live['days']['2026-11-10']}, 'validation_runs': {}}


def added(ledger, count, day=DAY):
    return record(ledger, day, [
        {'catalog_id': f'auto-{i}', 'product_id': str(i), 'source': 'api'}
        for i in range(1000, 1000 + count)
    ])


class DailyScheduleTests(unittest.TestCase):
    def setUp(self):
        self.ledger = seed_ledger()
        self.state = {'version': 1, 'days': {}}

    def test_prepares_at_1730_and_publishes_at_19_in_both_winter_and_summer(self):
        cases = [
            ('2026-11-14T15:29:59+00:00', True, False),
            ('2026-11-14T15:30:00+00:00', False, False),
            ('2026-11-14T16:59:59+00:00', False, False),
            ('2026-11-14T17:00:00+00:00', False, True),
            ('2026-07-14T14:29:59+00:00', True, False),
            ('2026-07-14T14:30:00+00:00', False, False),
            ('2026-07-14T15:59:59+00:00', False, False),
            ('2026-07-14T16:00:00+00:00', False, True),
            ('2026-11-14T22:00:00+00:00', True, False),
            ('2026-07-14T21:00:00+00:00', True, False),
        ]
        for instant, skip, publish in cases:
            with self.subTest(instant=instant):
                result = schedule.plan(self.ledger, self.state, now=datetime.fromisoformat(instant))
                self.assertEqual(skip, result['skip'])
                self.assertEqual(0 if skip else 3, result['add_count'])
                self.assertEqual(publish, result['publish'])

    def test_prepared_batch_waits_until_19_without_generating_again(self):
        early = NOW - timedelta(minutes=90)
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=early)
        ledger = added(self.ledger, 3)
        prepared = schedule.mark_prepared(ledger, reserved, DAY, now=early)
        waiting = schedule.plan(ledger, prepared, now=NOW - timedelta(hours=1))
        self.assertEqual((True, False, 0, 'waiting_publication'),
                         (waiting['skip'], waiting['publish'], waiting['add_count'], waiting['reason']))
        due = schedule.plan(ledger, prepared, now=NOW)
        self.assertEqual((False, True, 0, 'recover'),
                         (due['skip'], due['publish'], due['add_count'], due['action']))

    def test_tracked_publication_closes_at_22_israel_in_winter_and_summer(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        ledger = added(self.ledger, 3)
        prepared = schedule.mark_prepared(ledger, reserved, DAY, now=NOW)
        for instant in ('2026-11-14T20:00:00+00:00', '2027-07-14T19:00:00+00:00'):
            with self.subTest(instant=instant):
                at = datetime.fromisoformat(instant)
                self.assertFalse(schedule.plan(ledger, prepared, now=at)['publish'])
                self.assertFalse(schedule.plan(ledger, prepared, now=at, manual_count=0)['publish'])
                self.assertEqual(0, schedule.plan(ledger, prepared, now=at)['add_count'])

    def test_late_generation_does_not_start_after_local_22(self):
        result = schedule.plan(self.ledger, self.state,
                               now=datetime.fromisoformat('2026-11-14T20:00:00+00:00'))
        self.assertTrue(result['skip'])
        self.assertEqual(0, result['add_count'])

    def test_deployment_guard_rechecks_day_and_window_after_the_build(self):
        self.assertTrue(callable(getattr(schedule, 'guard_publication', None)))
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        ledger = added(self.ledger, 3)
        prepared = schedule.mark_prepared(ledger, reserved, DAY, now=NOW)
        schedule.guard_publication(ledger, prepared, DAY, now=NOW)
        for instant in ('2026-11-14T20:00:00+00:00', '2026-11-15T17:00:00+00:00'):
            with self.subTest(instant=instant), self.assertRaises(schedule.ScheduleError):
                schedule.guard_publication(ledger, prepared, DAY,
                    now=datetime.fromisoformat(instant))

    def test_untracked_manual_zero_remains_available_late_without_recording_publication(self):
        result = schedule.plan(self.ledger, self.state,
            now=datetime.fromisoformat('2026-11-14T20:30:00+00:00'), manual_count=0)
        self.assertTrue(result['publish'])
        self.assertFalse(result['record_publication'])

    def test_migration_respects_items_already_added_today(self):
        for done, expected in ((0, 3), (1, 2), (2, 1), (3, 0)):
            with self.subTest(done=done):
                result = schedule.plan(added(self.ledger, done), self.state, now=NOW)
                self.assertFalse(result['skip'])
                self.assertEqual(expected, result['add_count'])
                self.assertEqual('recover' if done == 3 else 'prepare', result['action'])

    def test_alternating_groups_cover_each_market_in_each_priority_position(self):
        results = [schedule.plan(self.ledger, self.state, now=NOW + timedelta(days=i))['markets'] for i in range(6)]
        groups = [set(markets) for markets in results]
        self.assertIn(groups[0], ({'RU', 'IL', 'FR'}, {'US', 'MX', 'BR'}))
        self.assertEqual(set(), groups[0] & groups[1])
        self.assertEqual({'RU', 'IL', 'FR', 'US', 'MX', 'BR'}, groups[0] | groups[1])
        self.assertEqual(groups[0], groups[2])
        self.assertEqual(groups[1], groups[3])
        for position in range(3):
            self.assertEqual({'RU', 'IL', 'FR', 'US', 'MX', 'BR'}, {markets[position] for markets in results})

    def test_reservation_survives_interrupted_generation_without_spending_again(self):
        before = deepcopy(self.state)
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        self.assertEqual(before, self.state)
        result = schedule.plan(self.ledger, reserved, now=NOW + timedelta(minutes=30))
        self.assertEqual((True, 0, 'interrupted_prepare'), (result['skip'], result['add_count'], result['reason']))
        with self.assertRaises(schedule.ScheduleError):
            schedule.reserve(self.ledger, reserved, DAY, 3, now=NOW)

    def test_committed_catalog_recovers_even_before_prepared_marker_was_saved(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        ledger = added(self.ledger, 3)
        retry = schedule.plan(ledger, reserved, now=NOW + timedelta(minutes=30))
        self.assertEqual((False, 0, 'recover'), (retry['skip'], retry['add_count'], retry['action']))
        prepared = schedule.mark_prepared(ledger, reserved, DAY, now=NOW)
        self.assertEqual('prepared', prepared['days'][DAY]['status'])
        self.assertEqual('recover', schedule.plan(ledger, prepared, now=NOW)['action'])

    def test_successful_publication_stops_duplicate_runs_for_same_day(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        ledger = added(self.ledger, 3)
        prepared = schedule.mark_prepared(ledger, reserved, DAY, now=NOW)
        published = schedule.mark_published(ledger, prepared, DAY, now=NOW)
        result = schedule.plan(ledger, published, now=NOW + timedelta(hours=1))
        self.assertEqual((True, 0, 'published'), (result['skip'], result['add_count'], result['reason']))
        self.assertEqual(published, schedule.mark_published(ledger, published, DAY, now=NOW + timedelta(days=1)))

    def test_failed_evening_deploy_recovers_old_batch_before_any_new_generation(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        ledger = added(self.ledger, 3)
        prepared = schedule.mark_prepared(ledger, reserved, DAY, now=NOW)
        next_day = NOW + timedelta(days=1)
        waiting = schedule.plan(ledger, prepared, now=next_day - timedelta(hours=1))
        self.assertEqual((True, 0, 'waiting_publication'),
                         (waiting['skip'], waiting['add_count'], waiting['reason']))
        recovery = schedule.plan(ledger, prepared, now=next_day)
        self.assertEqual(('recover', 0, DAY, '2026-11-15', True),
                         (recovery['action'], recovery['add_count'], recovery['day'],
                          recovery['publication_day'], recovery['publish']))
        with self.assertRaises(schedule.ScheduleError):
            schedule.reserve(ledger, prepared, '2026-11-15', 3, now=next_day)
        published = schedule.mark_published(ledger, prepared, DAY, now=next_day)
        self.assertEqual('2026-11-15', published['days'][DAY]['published_day'])
        after_recovery = schedule.plan(ledger, published, now=next_day + timedelta(hours=1))
        self.assertEqual((True, 0, 'published'),
                         (after_recovery['skip'], after_recovery['add_count'], after_recovery['reason']))
        self.assertEqual(3, schedule.plan(ledger, published, now=next_day + timedelta(days=1))['add_count'])

    def test_unmarked_but_committed_old_catalog_also_recovers_without_new_images(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        result = schedule.plan(added(self.ledger, 3), reserved, now=NOW + timedelta(days=1))
        self.assertEqual(('recover', 0, DAY, True),
                         (result['action'], result['add_count'], result['day'], result['record_publication']))

    def test_incomplete_old_reservation_does_not_block_the_next_utc_day(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        result = schedule.plan(self.ledger, reserved, now=NOW + timedelta(days=1))
        self.assertEqual(('prepare', 3, '2026-11-15'),
                         (result['action'], result['add_count'], result['day']))

    def test_legacy_published_state_without_actual_date_remains_readable(self):
        legacy = {'version': 1, 'days': {DAY: {
            'status': 'published', 'reserved_count': 3, 'baseline_count': 0, 'utc_day': DAY,
        }}}
        result = schedule.plan(added(self.ledger, 3), legacy, now=NOW)
        self.assertEqual((True, 'published'), (result['skip'], result['reason']))

    def test_published_day_cannot_precede_batch_or_appear_on_unpublished_state(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        invalid = deepcopy(reserved)
        invalid['days'][DAY]['published_day'] = DAY
        with self.assertRaises(schedule.ScheduleError):
            schedule.plan(self.ledger, invalid, now=NOW)
        invalid['days'][DAY]['status'] = 'published'
        invalid['days'][DAY]['published_day'] = '2026-11-13'
        with self.assertRaises(schedule.ScheduleError):
            schedule.plan(added(self.ledger, 3), invalid, now=NOW)

    def test_cannot_mark_incomplete_generation_prepared_or_publish_unprepared_batch(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        with self.assertRaises(schedule.ScheduleError):
            schedule.mark_prepared(added(self.ledger, 2), reserved, DAY, now=NOW)
        with self.assertRaises(schedule.ScheduleError):
            schedule.mark_published(added(self.ledger, 3), reserved, DAY)

    def test_manual_zero_rebuild_does_not_consume_evening_batch(self):
        morning = NOW - timedelta(hours=8)
        result = schedule.plan(self.ledger, self.state, now=morning, manual_count=0)
        self.assertEqual((False, 0, 'recover', False), (result['skip'], result['add_count'], result['action'], result['record_publication']))
        self.assertTrue(result['publish'])
        self.assertEqual(3, schedule.plan(self.ledger, self.state, now=NOW)['add_count'])

    def test_manual_zero_rebuild_can_recover_or_leave_consumed_interrupted_reservation(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        incomplete = schedule.plan(self.ledger, reserved, now=NOW, manual_count=0)
        self.assertEqual((False, 0, False), (incomplete['skip'], incomplete['add_count'], incomplete['record_publication']))
        complete = schedule.plan(added(self.ledger, 3), reserved, now=NOW, manual_count=0)
        self.assertTrue(complete['record_publication'])

    def test_new_local_day_does_not_reuse_an_uncertain_reservation_in_same_utc_day(self):
        reserved = schedule.reserve(self.ledger, self.state, DAY, 3, now=NOW)
        after_local_midnight = datetime(2026, 11, 14, 22, 10, tzinfo=timezone.utc)
        result = schedule.plan(self.ledger, reserved, now=after_local_midnight, manual_count=3)
        self.assertTrue(result['skip'])
        self.assertEqual(0, result['add_count'])

    def test_migrated_full_quota_can_be_published_and_recorded_without_reservation(self):
        ledger = added(self.ledger, 3)
        prepared = schedule.mark_prepared(ledger, self.state, DAY, now=NOW)
        published = schedule.mark_published(ledger, prepared, DAY, now=NOW)
        self.assertTrue(schedule.plan(ledger, published, now=NOW)['skip'])

    def test_invalid_time_state_and_manual_counts_fail_closed(self):
        with self.assertRaises(schedule.ScheduleError):
            schedule.plan(self.ledger, self.state, now=datetime(2026, 11, 14, 19))
        for count in (-1, 4, True):
            with self.subTest(count=count), self.assertRaises(schedule.ScheduleError):
                schedule.plan(self.ledger, self.state, now=NOW, manual_count=count)
        with self.assertRaises(schedule.ScheduleError):
            schedule.plan(self.ledger, {'version': 1, 'days': {DAY: {'status': 'published'}}}, now=NOW)


class DailyScheduleCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.ledger = self.directory / 'ledger.json'
        self.state = self.directory / 'publication.json'
        self.output = self.directory / 'output.txt'
        self.ledger.write_text(json.dumps(seed_ledger()), encoding='utf-8')

    def cli(self, command, *args):
        return subprocess.run([sys.executable, '-m', 'fluxixo_ai.daily_schedule', command,
            '--ledger', str(self.ledger), '--state', str(self.state), *args],
            cwd=ROOT, capture_output=True, text=True)

    def test_real_cli_persists_reservation_then_recovers_and_marks_publication(self):
        planned = self.cli('plan', '--output', str(self.output), '--now', NOW.isoformat())
        self.assertEqual(0, planned.returncode, planned.stderr)
        self.assertIn('add_count=3\n', self.output.read_text())
        reserve = self.cli('reserve', '--day', DAY, '--count', '3', '--now', NOW.isoformat())
        self.assertEqual(0, reserve.returncode, reserve.stderr)
        self.assertEqual('preparing', json.loads(self.state.read_text())['days'][DAY]['status'])
        self.ledger.write_text(json.dumps(added(seed_ledger(), 3)), encoding='utf-8')
        prepared = self.cli('mark-prepared', '--day', DAY, '--now', NOW.isoformat())
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        published = self.cli('mark-published', '--day', DAY, '--now', NOW.isoformat())
        self.assertEqual(0, published.returncode, published.stderr)
        self.assertEqual('published', json.loads(self.state.read_text())['days'][DAY]['status'])
        self.assertEqual({'ledger.json', 'publication.json', 'output.txt'}, {p.name for p in self.directory.iterdir()})

    def test_missing_or_corrupt_ledger_and_corrupt_state_never_reset_allowance(self):
        for bad in ('{', '{"version":1,"days":{},"validation_runs":{}}'):
            self.ledger.write_text(bad, encoding='utf-8')
            result = self.cli('plan', '--now', NOW.isoformat())
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(self.state.exists())
        self.ledger.unlink()
        self.assertNotEqual(0, self.cli('plan', '--now', NOW.isoformat()).returncode)
        self.ledger.write_text(json.dumps(seed_ledger()), encoding='utf-8')
        self.state.write_text('{"version":1,"version":1,"days":{}}', encoding='utf-8')
        self.assertNotEqual(0, self.cli('plan', '--now', NOW.isoformat()).returncode)


if __name__ == '__main__':
    unittest.main()
