"""Deploy dist/ to Cloudflare Pages using decrypted local credentials."""
import os
import sys
import json
import subprocess
import ctypes
import ctypes.wintypes
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(r"C:\Users\Nika\.gemini\antigravity\scratch\aliexpress_seo_hub")

class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

def unprotect(data):
    blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return out
    return None

def get_token():
    dpapi_path = BASE_DIR / ".local" / "cloudflare-token.dpapi"
    if not dpapi_path.exists():
        raise FileNotFoundError(f"Missing {dpapi_path}")
    raw = unprotect(dpapi_path.read_bytes()).decode('utf-8').strip()
    return raw

def deploy():
    token = get_token()
    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = token
    env["CLOUDFLARE_ACCOUNT_ID"] = "a4be28e05f73ad2b3939d364ea8b2817"
    
    cmd = [
        "npx.cmd", "wrangler", "pages", "deploy", "dist",
        "--project-name=dealvault",
        "--branch=main",
        "--commit-dirty=true"
    ]
    print("[Deploy] Starting Cloudflare Pages deployment...")
    proc = subprocess.run(cmd, cwd=BASE_DIR, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print("STDOUT:")
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:")
        print(proc.stderr)
    if proc.returncode != 0:
        print(f"[Deploy] Failed with exit code {proc.returncode}")
        sys.exit(proc.returncode)
    print("[Deploy] Cloudflare Pages deployment completed successfully!")

if __name__ == '__main__':
    deploy()
