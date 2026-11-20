import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fluxixo_ai.state_checkpoint import checkpoint, CheckpointUnavailable


class StateCheckpointTests(unittest.TestCase):
    def test_local_mode_never_runs_git(self):
        with patch.dict(os.environ, {'FLUXIXO_DURABLE_CHECKPOINT': ''}), patch('subprocess.run') as run:
            checkpoint()
        run.assert_not_called()

    def test_branch_or_non_actions_cannot_push_production(self):
        with patch.dict(os.environ, {'FLUXIXO_DURABLE_CHECKPOINT': 'git', 'GITHUB_ACTIONS': '', 'GITHUB_REF': 'refs/heads/main'}):
            with self.assertRaises(CheckpointUnavailable):
                checkpoint()

    def test_only_internal_state_and_media_are_checkpointed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'data').mkdir()
            (root/'data/fluxixo_pending.sqlite3').write_bytes(b'pending')
            (root/'data/unrelated.txt').write_text('do not publish')
            images = root/'fluxixo_site/reserve/reviewed-media/item'
            images.mkdir(parents=True)
            (images/'state.json').write_text('{}')
            (images/'.lock').write_text('lock')
            (images/'key.txt').write_text('not allowed')
            calls = []
            def run(args, **kw):
                calls.append((args, kw))
                from subprocess import CompletedProcess
                return CompletedProcess(args, 1 if 'diff' in args else 0, b'', b'')
            with patch.dict(os.environ, {'FLUXIXO_DURABLE_CHECKPOINT': 'git', 'GITHUB_ACTIONS': 'true', 'GITHUB_REF': 'refs/heads/main'}), patch('subprocess.run', side_effect=run):
                checkpoint(root=root)
            staged = next(kw['input'] for args, kw in calls if 'add' in args)
            self.assertIn(b'data/fluxixo_pending.sqlite3', staged)
            self.assertIn(b'state.json', staged)
            self.assertNotIn(b'.lock', staged)
            self.assertNotIn(b'unrelated', staged)
            self.assertNotIn(b'key.txt', staged)
            self.assertIn(['git', 'push', 'origin', 'HEAD:main'], [args for args, kw in calls])

    def test_real_git_push_excludes_a_separately_staged_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            bare = Path(temp) / 'origin.git'
            root = Path(temp) / 'work'
            subprocess.run(['git', 'init', '-q', '--bare', str(bare)], check=True)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)

            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True,
                                      text=True).stdout.strip()

            git('config', 'user.email', 'local@example.invalid')
            git('config', 'user.name', 'Checkpoint test')
            git('remote', 'add', 'origin', str(bare))
            git('commit', '-q', '--allow-empty', '-m', 'Initial')
            (root / 'data').mkdir()
            (root / 'data/fluxixo_gemini_usage.sqlite3').write_bytes(b'durable quota')
            (root / 'catalog.js').write_text('unpublished', encoding='utf-8')
            git('add', 'catalog.js')
            with patch.dict(os.environ, {'FLUXIXO_DURABLE_CHECKPOINT': 'git',
                                         'GITHUB_ACTIONS': 'true', 'GITHUB_REF': 'refs/heads/main'}):
                checkpoint(root=root)
                checkpoint(root=root)
            self.assertEqual(git('ls-tree', '--name-only', '-r', 'origin/main'),
                             'data/fluxixo_gemini_usage.sqlite3')
            self.assertEqual(git('diff', '--cached', '--name-only'), 'catalog.js')
            self.assertEqual(git('rev-list', '--count', 'origin/main'), '2')
