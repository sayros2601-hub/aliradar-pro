"""Durable, independent IndexNow notifications for current Russian routes."""
import json
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
import urllib.request
import xml.etree.ElementTree as ET


ORIGIN = 'https://www.fluxixo.shop'
ENDPOINT = 'https://yandex.com/indexnow'
STATE_FILENAME = 'yandex-indexnow-state.json'
RU_ROUTE = re.compile(r'/(?:|catalog/|about/|journal/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)?|(?:products|categories)/[a-z0-9]+(?:-[a-z0-9]+)*/)')
DIGEST = re.compile(r'[0-9a-f]{64}')


def _read(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invalid Yandex notification state')
    return value


def _save(path, state):
    """Replace atomically, without creating changes for an unchanged queue."""
    if path.exists() and _read(path) == state:
        return
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                     dir=path.parent, prefix='.yandex-indexnow-',
                                     suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(json.dumps(state, indent=2, sort_keys=True) + '\n')
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _current_versions(site_root, dist):
    fingerprints = _read(site_root / 'tools/search-build-state.json')
    canonical = {loc.text for loc in ET.parse(dist / 'sitemap.xml').findall('.//{*}loc')}
    versions = {}
    for loc in ET.parse(dist / 'sitemap-ru.xml').findall('.//{*}loc'):
        url = loc.text or ''
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != 'www.fluxixo.shop'
                or parsed.query or parsed.fragment or not RU_ROUTE.fullmatch(parsed.path)
                or url != ORIGIN + parsed.path or url not in canonical):
            raise ValueError('Only current canonical Russian URLs may be notified to Yandex')
        digest = fingerprints.get(parsed.path, {}).get('sha256', '')
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError('Russian route has no current page fingerprint')
        versions[url] = digest
    if not versions:
        raise ValueError('Russian sitemap is empty')
    return versions


def prepare(site_root, dist=None):
    """Persist changed RU versions during build, before the catalog commit/deploy."""
    site_root = Path(site_root)
    dist = Path(dist) if dist is not None else site_root / 'dist'
    current = _current_versions(site_root, dist)
    state_path = site_root / 'tools' / STATE_FILENAME
    if state_path.exists():
        state = _read(state_path)
        if (state.get('schema_version') != 1
                or any(not isinstance(state.get(name), dict)
                       for name in ('legacy_shared', 'acknowledged', 'pending'))):
            raise ValueError('Invalid Yandex notification state')
    else:
        shared_path = site_root / 'tools/indexnow-submitted.json'
        shared = _read(shared_path) if shared_path.exists() else {}
        # Historical shared success is a no-resend baseline, never proof that
        # Yandex accepted a version. Only this endpoint can fill acknowledged.
        state = {'schema_version': 1, 'baseline_provenance': 'legacy_shared',
                 'legacy_shared': {url: shared[url] for url in current if url in shared},
                 'acknowledged': {}, 'pending': {}}
    state['pending'] = {
        url: digest for url, digest in current.items()
        if state['acknowledged'].get(url, state['legacy_shared'].get(url)) != digest}
    _save(state_path, state)
    return state


def submit_pending(site_root, dist=None):
    """Accept only the exact versions sent to Yandex; failures remain pending."""
    site_root = Path(site_root)
    state = prepare(site_root, dist)
    versions = dict(state['pending'])
    if not versions:
        print('IndexNow (Yandex RU): no pending page versions.')
        return
    key = (site_root / 'tools/indexnow-key.txt').read_text(encoding='utf-8').strip()
    payload = {'host': 'www.fluxixo.shop', 'key': key,
               'keyLocation': f'{ORIGIN}/{key}.txt', 'urlList': sorted(versions)}
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json; charset=utf-8',
                 'User-Agent': 'FLUXIXO-SEO-Bot/2.0'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
    except OSError as error:
        print(f'IndexNow (Yandex RU): {type(error).__name__}; pending versions retained.')
        return
    if status in (200, 202):
        state_path = site_root / 'tools' / STATE_FILENAME
        latest = _read(state_path)
        for url, digest in versions.items():
            latest['acknowledged'][url] = digest
            if latest['pending'].get(url) == digest:
                del latest['pending'][url]
        _save(state_path, latest)
    print(f'IndexNow (Yandex RU): HTTP {status} for {len(versions)} URLs; '
          + ('accepted, indexing is not guaranteed.' if status in (200, 202)
             else 'pending versions retained.'))
