"""Push only internal retry/quota state before external AI calls.

Requires the existing GitHub Actions shared concurrency lock. No site/catalog
files are included. Failure closes the outgoing AI path; no raw git errors or
environment variables are logged. A lost response still consumes its reservation.
"""
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
_LAST_CHECKPOINT_AT = 0.0


class CheckpointUnavailable(RuntimeError):
    pass


def checkpoint(*, root=ROOT, force=False):
    global _LAST_CHECKPOINT_AT
    if os.environ.get('FLUXIXO_DURABLE_CHECKPOINT') != 'git':
        return
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise CheckpointUnavailable('checkpoint_requires_trusted_main_job')
    try:
        min_interval = float(os.environ.get('FLUXIXO_CHECKPOINT_MIN_INTERVAL', '0') or '0')
    except ValueError:
        min_interval = 0.0
    now_mono = time.monotonic()
    if not force and min_interval > 0 and _LAST_CHECKPOINT_AT and (now_mono - _LAST_CHECKPOINT_AT) < min_interval:
        return
    root = Path(root).resolve()
    paths = []
    for relative in ('data/fluxixo_pending.sqlite3', 'data/fluxixo_gemini_usage.sqlite3',
                     'data/fluxixo_free_search.sqlite3', 'data/fluxixo_cf_image_usage.sqlite3'):
        file = root / relative
        if file.is_file() and not file.is_symlink():
            paths.append(relative)
    folder = root / 'fluxixo_site/reserve/reviewed-media'
    if folder.is_dir() and not folder.is_symlink():
        for file in folder.rglob('*'):
            if (file.is_file() and not file.is_symlink() and file.resolve().is_relative_to(folder.resolve())
                    and (file.name == 'state.json' or file.suffix in ('.png', '.webp'))):
                paths.append(file.relative_to(root).as_posix())
    if not paths:
        return
    payload = b'\0'.join(p.encode('utf-8') for p in sorted(paths)) + b'\0'
    def git(*args, data=None, allowed=(0,)):
        try:
            result = subprocess.run(['git', *args], cwd=root, input=data,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        except (OSError, subprocess.SubprocessError):
            raise CheckpointUnavailable('checkpoint_unavailable') from None
        if result.returncode not in allowed:
            raise CheckpointUnavailable('checkpoint_unavailable')
        return result.returncode
    git('add', '-f', '--pathspec-from-file=-', '--pathspec-file-nul', data=payload)
    # Inspect only the allowlist, then commit only that list (never caller's staged catalog).
    changed = git('diff', '--cached', '--quiet', '--', 'data/fluxixo_pending.sqlite3',
                  'data/fluxixo_gemini_usage.sqlite3', 'data/fluxixo_free_search.sqlite3',
                  'data/fluxixo_cf_image_usage.sqlite3',
                  'fluxixo_site/reserve/reviewed-media', allowed=(0, 1))
    if changed:
        git('commit', '--only', '-m', 'chore(fluxixo): checkpoint AI retry state [skip ci]',
            '--pathspec-from-file=-', '--pathspec-file-nul', data=payload)
    # Retry transient git push errors cleanly (still closes the path if remote truly fails).
    for attempt in range(3):
        try:
            git('push', 'origin', 'HEAD:main')
            _LAST_CHECKPOINT_AT = time.monotonic()
            return
        except CheckpointUnavailable:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))


if __name__ == '__main__':
    checkpoint(force=True)
