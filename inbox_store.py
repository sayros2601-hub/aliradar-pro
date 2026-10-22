"""Shared offline queue lock and strict reads. No network or browser imports."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
from dealvault_core import affiliate_key
MAX_QUEUE_BYTES = 25 * 1024 * 1024


def ensure_queue_size(queue):
    # Match dealvault_core.write_json exactly, including indentation/newline.
    size = len((json.dumps(queue, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    if size > MAX_QUEUE_BYTES:
        raise ValueError('Queue exceeds the size limit')


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_queue(path):
    path = Path(path)
    if not path.exists():
        return []
    if not path.is_file() or path.stat().st_size > MAX_QUEUE_BYTES:
        raise ValueError('Queue is not a bounded regular file')
    queue = strict_json(path.read_text(encoding='utf-8-sig'))
    if not isinstance(queue, list):
        raise ValueError('Queue must be an array')
    for row in queue:
        if not isinstance(row, dict):
            raise ValueError('Queue contains a non-object record')
        url = row.get('affiliate_url') or row.get('original_affiliate_url')
        if not isinstance(url, str) or not affiliate_key(url):
            raise ValueError('Queue contains an invalid affiliate reference')
        if row.get('observation_id') is not None and not isinstance(row['observation_id'], str):
            raise ValueError('Queue contains an invalid observation ID')
        if row.get('affiliate_url') and row.get('original_affiliate_url') and row['affiliate_url'] != row['original_affiliate_url']:
            raise ValueError('Queue contains conflicting affiliate references')
    return queue


@contextmanager
def queue_lock(data_dir):
    directory = Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / '.portals_inbox.lock', 'a+b') as stream:
        stream.seek(0); stream.write(b'0'); stream.flush(); stream.seek(0)
        locked = False
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
            yield
        finally:
            if locked:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
