"""Keys kept on the owner's Windows PC in .local/*.dpapi, encrypted with Windows DPAPI for the current user.

Same format as tools/check_search_connections.py uses, so both read the same files.
"""
import ctypes
import ctypes.wintypes
from pathlib import Path

LOCAL_DIR = Path(__file__).resolve().parents[2] / '.local'


class _Blob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _call(function, raw):
    buffer = ctypes.create_string_buffer(raw, len(raw))
    blob_in = _Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = _Blob()
    if not function(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        return None
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def load_credential(filename):
    path = LOCAL_DIR / filename
    if not path.exists():
        return None
    raw = _call(ctypes.windll.crypt32.CryptUnprotectData, path.read_bytes())
    return raw.decode('utf-8', errors='replace').strip() if raw is not None else None


def save_credential(filename, secret_text):
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = _call(ctypes.windll.crypt32.CryptProtectData, secret_text.strip().encode('utf-8'))
    if encrypted is None:
        raise OSError('CryptProtectData failed')
    (LOCAL_DIR / filename).write_bytes(encrypted)
    return LOCAL_DIR / filename
