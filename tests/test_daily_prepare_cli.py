"""A generated batch can be saved before a later HTML build/deployment fails."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fluxixo_daily_rotate as daily


class PrepareOnlyTests(unittest.TestCase):
    def test_prepare_outputs_ids_without_starting_build_or_deployment(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'outputs'
            with patch('sys.argv', ['daily', '--add', '3', '--prepare-only', '--markets', 'RU,IL,FR']), \
                 patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), \
                 patch.object(daily, 'accumulate_catalog', return_value={'added': 3, 'ids': ['one', 'two', 'three']}) as accumulate, \
                 patch.object(daily.subprocess, 'run', side_effect=AssertionError('building before batch persistence')), \
                 patch.object(daily, 'deploy_release', side_effect=AssertionError('unexpected deployment')):
                daily.main()
            self.assertEqual({'added': '3', 'ids': 'one,two,three', 'deploy': '1'},
                             dict(line.split('=', 1) for line in output.read_text().splitlines()))
            self.assertEqual(3, accumulate.call_args.args[0])
            self.assertEqual(['RU', 'IL', 'FR'], accumulate.call_args.kwargs['preferred_markets'])

    def test_prepare_only_rejects_a_deployment_request_before_work(self):
        with patch('sys.argv', ['daily', '--add', '0', '--prepare-only', '--deploy']), \
             patch.object(daily, 'accumulate_catalog', side_effect=AssertionError('unexpected generation')), \
             patch.object(daily.subprocess, 'run', side_effect=AssertionError('unexpected build')):
            with self.assertRaises(SystemExit) as error:
                daily.main()
        self.assertEqual(2, error.exception.code)


if __name__ == '__main__':
    unittest.main()
