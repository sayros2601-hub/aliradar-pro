"""Sync deployable FLUXIXO storefront media to Cloudflare R2 and pack lean Pages bundles.

Keeps local `fluxixo_site/release/` 100% intact for `verify_release.py`, uploads new or changed
images/thumbs/featured/video files to R2 bucket `fluxixo` (served from https://media.fluxixo.shop/),
and builds `fluxixo_site/release_pages/` with media URLs rewritten to `MEDIA_ORIGIN` and
offloaded asset directories omitted so Cloudflare Pages stays well below the 20,000-file cap.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.error
import urllib.request

DEFAULT_ACCOUNT_ID = 'a4be28e05f73ad2b3939d364ea8b2817'
DEFAULT_BUCKET = 'fluxixo'
DEFAULT_MEDIA_ORIGIN = 'https://media.fluxixo.shop'
DEFAULT_SITE_ORIGIN = 'https://www.fluxixo.shop'
DEFAULT_AUTOPILOT_URL = 'https://fluxixo-autopilot.sayros2601.workers.dev'
DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / 'data' / 'r2_media_manifest.json'
OFFLOAD_PREFIXES = ('assets/images/', 'assets/thumbs/', 'assets/featured/', 'assets/video/')
MIME_BY_EXT = {
    '.webp': 'image/webp',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.mp4': 'video/mp4',
    '.json': 'application/json; charset=utf-8',
}


def _load_dpapi_secret(name: str) -> str:
    tools_dir = str(Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        from dpapi_store import load_credential
        return (load_credential(name) or '').strip()
    except Exception:
        return ''


def _content_type_for(key: str) -> str:
    return MIME_BY_EXT.get(Path(key).suffix.lower(), 'application/octet-stream')


def collect_media_files(source_dir: Path) -> list[tuple[str, Path]]:
    source_dir = Path(source_dir).resolve()
    items: list[tuple[str, Path]] = []
    for file in sorted(source_dir.rglob('*')):
        if not file.is_file():
            continue
        rel = file.relative_to(source_dir).as_posix()
        if rel.startswith(OFFLOAD_PREFIXES):
            if rel.startswith('assets/images/watch-layers/') and rel.endswith('.png'):
                continue
            items.append((rel, file))
    return items


def load_manifest(manifest_path: Path) -> dict:
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding='utf-8'))
            if isinstance(data, dict) and isinstance(data.get('objects'), dict):
                return data
        except (OSError, ValueError):
            pass
    return {
        'version': 1,
        'bucket': DEFAULT_BUCKET,
        'media_origin': DEFAULT_MEDIA_ORIGIN,
        'objects': {},
    }


def _upload_via_worker(autopilot_url: str, sync_token: str, key: str, raw: bytes, content_type: str) -> None:
    url = f"{autopilot_url.rstrip('/')}/api/r2-media/{key}"
    req = urllib.request.Request(
        url,
        data=raw,
        headers={
            'Authorization': f'Bearer {sync_token}',
            'Content-Type': content_type,
            'User-Agent': 'FLUXIXO-R2-Sync/1.0',
        },
        method='PUT',
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(f'Worker R2 upload HTTP {resp.status} for {key}')


def _upload_via_cf_api(account_id: str, bucket: str, cf_token: str, key: str, raw: bytes, content_type: str) -> None:
    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/buckets/{bucket}/objects/{key}'
    req = urllib.request.Request(
        url,
        data=raw,
        headers={
            'Authorization': f'Bearer {cf_token}',
            'Content-Type': content_type,
            'Cache-Control': 'public, max-age=31536000, immutable',
            'User-Agent': 'FLUXIXO-R2-Sync/1.0',
        },
        method='PUT',
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(f'Cloudflare R2 API upload HTTP {resp.status} for {key}')


def _upload_one(key: str, raw: bytes, content_type: str, *, autopilot_url: str, sync_token: str,
                account_id: str, bucket: str, cf_token: str) -> str:
    last_err = None
    for attempt in range(3):
        if attempt:
            time.sleep(0.5 * (2 ** (attempt - 1)))
        if autopilot_url and sync_token:
            try:
                _upload_via_worker(autopilot_url, sync_token, key, raw, content_type)
                return 'worker'
            except Exception as exc:
                last_err = exc
        if cf_token:
            try:
                _upload_via_cf_api(account_id, bucket, cf_token, key, raw, content_type)
                return 'cf_api'
            except Exception as exc:
                last_err = exc
    raise RuntimeError(f'R2 upload failed for {key}: {last_err}')


def sync_media_to_r2(
    source_dir: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    bucket: str = DEFAULT_BUCKET,
    media_origin: str = DEFAULT_MEDIA_ORIGIN,
    workers: int = 8,
    verify_live: bool = True,
) -> dict:
    """Upload changed or new deployable media files from `source_dir` into Cloudflare R2."""
    media_origin = media_origin.rstrip('/')
    autopilot_url = (os.environ.get('CLOUDFLARE_AUTOPILOT_URL') or DEFAULT_AUTOPILOT_URL).strip().rstrip('/')
    sync_token = (os.environ.get('AUTOPILOT_SYNC_TOKEN') or _load_dpapi_secret('autopilot-sync-token.dpapi')).strip()
    cf_token = (os.environ.get('CLOUDFLARE_API_TOKEN') or _load_dpapi_secret('cloudflare-token.dpapi')).strip()
    account_id = (os.environ.get('CLOUDFLARE_ACCOUNT_ID') or DEFAULT_ACCOUNT_ID).strip()

    if not ((autopilot_url and sync_token) or cf_token):
        raise RuntimeError('Neither AUTOPILOT_SYNC_TOKEN nor CLOUDFLARE_API_TOKEN is available for R2 media sync')

    manifest = load_manifest(manifest_path)
    objects: dict = manifest.setdefault('objects', {})
    manifest['bucket'] = bucket
    manifest['media_origin'] = media_origin

    files = collect_media_files(source_dir)
    to_upload: list[tuple[str, Path, str, str]] = []
    for rel, path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        prev = objects.get(rel) or {}
        if prev.get('sha256') == digest:
            continue
        to_upload.append((rel, path, digest, _content_type_for(rel)))

    uploaded = 0
    if to_upload:
        with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
            futs = {}
            for rel, path, digest, ctype in to_upload:
                raw = path.read_bytes()
                fut = pool.submit(
                    _upload_one, rel, raw, ctype,
                    autopilot_url=autopilot_url, sync_token=sync_token,
                    account_id=account_id, bucket=bucket, cf_token=cf_token,
                )
                futs[fut] = (rel, len(raw), digest, ctype)
            for fut in as_completed(futs):
                rel, nbytes, digest, ctype = futs[fut]
                fut.result()
                objects[rel] = {'sha256': digest, 'bytes': nbytes, 'content_type': ctype}
                uploaded += 1

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')

    if verify_live and files:
        samples = [files[0][0], files[len(files) // 2][0], files[-1][0]]
        for rel in dict.fromkeys(samples):
            url = f'{media_origin}/{rel}'
            req = urllib.request.Request(url, headers={'User-Agent': 'FLUXIXO-R2-Verify/1.0'}, method='HEAD')
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f'Live R2 verify failed: {url} -> HTTP {resp.status}')
            except urllib.error.HTTPError as exc:
                if exc.code == 405:
                    with urllib.request.urlopen(url, timeout=15) as gresp:
                        if gresp.status != 200:
                            raise RuntimeError(f'Live R2 verify failed: {url} -> HTTP {gresp.status}')
                else:
                    raise RuntimeError(f'Live R2 verify failed: {url} -> HTTP {exc.code}')

    return {'total_media': len(files), 'uploaded': uploaded, 'cached': len(files) - uploaded}


_REWRITE_ABS_RE = re.compile(
    r'https://www\.fluxixo\.shop/(assets/(?:images|thumbs|featured|video)/[^"\'\s<>)]+)'
)
_REWRITE_REL_RE = re.compile(
    r'(["\'\s,(=])/(assets/(?:images|thumbs|featured|video)/[^"\'\s<>)]+)'
)


def rewrite_media_urls(text: str, media_origin: str = DEFAULT_MEDIA_ORIGIN) -> str:
    """Rewrite site media URLs (`assets/images|thumbs|featured|video`) to `media_origin`."""
    origin = media_origin.rstrip('/')
    out = _REWRITE_ABS_RE.sub(rf'{origin}/\1', text)
    out = _REWRITE_REL_RE.sub(rf'\1{origin}/\2', out)
    return out


def pack_pages_bundle(
    source_dir: Path,
    pages_dir: Path,
    *,
    media_origin: str = DEFAULT_MEDIA_ORIGIN,
) -> dict:
    """Copy `source_dir` into `pages_dir`, dropping offloaded media folders and rewriting media URLs."""
    source_dir = Path(source_dir).resolve()
    pages_dir = Path(pages_dir).resolve()
    if pages_dir == source_dir:
        raise ValueError('pages_dir must differ from source_dir')
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)

    kept_files = 0
    rewritten_files = 0
    for file in sorted(source_dir.rglob('*')):
        if not file.is_file():
            continue
        rel = file.relative_to(source_dir).as_posix()
        if rel.startswith(OFFLOAD_PREFIXES):
            continue
        dest = pages_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if file.suffix.lower() in ('.html', '.xml', '.json'):
            raw_text = file.read_text(encoding='utf-8')
            updated = rewrite_media_urls(raw_text, media_origin)
            if updated != raw_text:
                rewritten_files += 1
            dest.write_text(updated, encoding='utf-8', newline='\n')
        else:
            shutil.copyfile(file, dest)
        kept_files += 1
    return {'pages_files': kept_files, 'rewritten_files': rewritten_files}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='fluxixo_site/release', help='Verified release directory')
    parser.add_argument('--manifest', default=str(DEFAULT_MANIFEST), help='R2 media manifest JSON path')
    parser.add_argument('--bucket', default=DEFAULT_BUCKET, help='Cloudflare R2 bucket name')
    parser.add_argument('--media-origin', default=DEFAULT_MEDIA_ORIGIN, help='Public R2 custom origin')
    parser.add_argument('--pack-pages', default='', help='Optional slim Cloudflare Pages output directory')
    parser.add_argument('--pack-only', action='store_true', help='Rewrite and pack without remote R2 upload')
    parser.add_argument('--no-verify-live', action='store_true', help='Skip live HEAD checks against media_origin')
    parser.add_argument('--workers', type=int, default=8, help='Concurrent R2 upload threads')
    args = parser.parse_args()

    src = Path(args.source)
    summary: dict = {}
    if not args.pack_only:
        summary['sync'] = sync_media_to_r2(
            src,
            Path(args.manifest),
            bucket=args.bucket,
            media_origin=args.media_origin,
            workers=args.workers,
            verify_live=not args.no_verify_live,
        )
    if args.pack_pages:
        summary['pack'] = pack_pages_bundle(src, Path(args.pack_pages), media_origin=args.media_origin)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
