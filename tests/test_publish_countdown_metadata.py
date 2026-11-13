"""Only completed releases (or the release being built) advance the public clock."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'fluxixo_site/redesign/build_redesign.py'
spec = importlib.util.spec_from_file_location('fluxixo_countdown_metadata_test', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CountdownMetadataTests(unittest.TestCase):
    def metadata(self, days, prepared=''):
        self.assertTrue(callable(getattr(module, 'countdown_metadata', None)),
                        'the storefront needs publication-aware countdown metadata')
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'state.json'
            state.write_text(json.dumps({'days': days}), encoding='utf-8')
            return module.countdown_metadata(state_path=state, prepared_day=prepared,
                now=datetime(2026, 11, 13, 22, 30, tzinfo=timezone.utc))

    def test_pending_state_does_not_claim_a_new_publication(self):
        result = self.metadata({'2026-11-12': {'status': 'published'},
                                '2026-11-13': {'status': 'prepared'}})
        self.assertEqual('2026-11-12', result['published_day'])
        self.assertEqual('2026-11-13', result['due_day'])

    def test_prepared_release_override_updates_metadata_that_will_go_live(self):
        result = self.metadata({'2026-11-12': {'status': 'published'}}, prepared='2026-11-13')
        self.assertEqual('2026-11-13', result['published_day'])
        self.assertEqual('2026-11-14', result['due_day'])

    def test_initial_due_day_uses_israel_date_not_utc_date(self):
        result = self.metadata({})
        self.assertEqual('', result['published_day'])
        self.assertEqual('2026-11-14', result['due_day'])

    def test_recovered_batch_uses_actual_publication_day_for_the_next_countdown(self):
        result = self.metadata({'2026-11-12': {'status': 'published', 'published_day': '2026-11-13'}})
        self.assertEqual('2026-11-13', result['published_day'])
        self.assertEqual('2026-11-14', result['due_day'])


if __name__ == '__main__':
    unittest.main()
