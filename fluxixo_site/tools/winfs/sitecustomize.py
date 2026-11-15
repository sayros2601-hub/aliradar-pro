"""Loaded by every Python process that tools/local_daily.py starts (it puts this folder on PYTHONPATH).

On this PC the real-time antivirus briefly holds a file that was just written or read. Opening it for writing then
fails with EINVAL (Errno 22) or EACCES, and deleting or replacing it fails with "access denied" (WinError 5 / 32).
A build rewrites and replaces thousands of pages, so one unlucky file used to stop the whole build
(2026-11-15: dist/404.html when writing, release/about/index.html when clearing the old release).
These calls are retried for a few seconds; reading is untouched and any other error is raised at once, as before.
"""
import builtins
import errno
import io
import os
import time

_TRANSIENT = (errno.EINVAL, errno.EACCES)
_ATTEMPTS = 10


def _retry(action, *args, **kwargs):
    for attempt in range(_ATTEMPTS):
        try:
            return action(*args, **kwargs)
        except OSError as exc:
            if exc.errno not in _TRANSIENT or attempt == _ATTEMPTS - 1:
                raise
            time.sleep(0.15 * (attempt + 1))


_open = io.open


def _retrying_open(file, mode='r', *args, **kwargs):
    if not isinstance(mode, str) or not any(flag in mode for flag in 'wax+'):
        return _open(file, mode, *args, **kwargs)
    return _retry(_open, file, mode, *args, **kwargs)


def _wrap(action):
    def retrying(*args, **kwargs):
        return _retry(action, *args, **kwargs)
    retrying.__name__ = retrying.__qualname__ = action.__name__
    retrying.__doc__ = action.__doc__
    return retrying


io.open = builtins.open = _retrying_open
for _name in ('unlink', 'remove', 'rmdir', 'replace', 'rename'):
    setattr(os, _name, _wrap(getattr(os, _name)))
