"""Measure public site health without inventing traffic or private channel status."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from dealvault_core import BASE_DIR, DOMAIN, read_json, write_json, utc_now


def fetch(path):
    request = Request(DOMAIN + path, headers={'User-Agent': 'DealVault-Health/2.0'})
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def measure(getter=fetch):
    paths = ['/', '/ru/', '/he/', '/es/', '/returns', '/contact',
             '/robots.txt', '/sitemap.xml', '/rss.xml', '/google_feed.xml',
             '/build-info.json']
    integrations = read_json(BASE_DIR / 'data/site_integrations.json', {})
    key = integrations.get('indexnow_key')
    if key:
        paths.append('/' + key + '.txt')

    def check(path):
        started = time.monotonic()
        result = {'url': DOMAIN + path, 'status': 0, 'valid': False}
        try:
            status, body, headers = getter(path)
            result.update(status=status, size_bytes=len(body))
            if status != 200:
                raise ValueError(f'HTTP {status}')
            if path == '/build-info.json':
                result['build'] = json.loads(body)
            elif path.endswith('.xml'):
                tree = ET.fromstring(body)
                result['items'] = len(tree.findall('.//item'))
                if path == '/sitemap.xml':
                    result['urls'] = len(tree.findall('.//{*}loc'))
            elif key and path == '/' + key + '.txt':
                if body.decode().strip() != key:
                    raise ValueError('IndexNow key content mismatch')
            elif path == '/robots.txt':
                if 'Disallow: /' in body.decode():
                    raise ValueError('Robots exclude crawlers')
            elif b'<html' not in body or b'<h1' not in body:
                raise ValueError('Expected HTML page, not an error or challenge')
            result['valid'] = True
        except Exception as error:
            result['error'] = str(error)
        result['latency_ms'] = round((time.monotonic() - started) * 1000, 1)
        return result

    with ThreadPoolExecutor(max_workers=4) as executor:
        checks = list(executor.map(check, paths))
    return {
        'schema_version': 2, 'timestamp': utc_now(),
        'site_health': {'total_endpoints_scanned': len(checks),
                        'endpoints_ok': sum(c['valid'] for c in checks),
                        'endpoints': checks},
        'traffic_metrics': {'total_clicks': None, 'pageviews': None,
                            'unique_visitors': None, 'orders': None,
                            'source': None, 'status': 'not_measured'},
        'channels': {name: {'status': 'not_checked', 'source': None}
                     for name in ('google_merchant_center', 'microsoft_merchant_center',
                                  'pinterest_business', 'indexnow_submission')},
        'note': 'HTTP health is measured. Verification files do not prove account '
                'approval, feed ingestion, indexing, visits, orders or commission.'
    }


def save_snapshot(path, snapshot):
    """Keep historical observations; invalid history must never be discarded."""
    path = Path(path)
    history = read_json(path, [])
    if not isinstance(history, list):
        raise ValueError('Audit history must be a list; existing file preserved')
    for entry in history:
        if isinstance(entry, dict) and entry.get('schema_version') != 2:
            entry['provenance_warning'] = 'Legacy snapshot contains unverified hard-coded claims; not a fresh measurement.'
    write_json(path, history + [snapshot])


def main(path=None):
    # The same lock protects concurrent local daily checks and pipeline operations.
    from dealvault_pipeline import pipeline_lock
    with pipeline_lock():
        snapshot = measure()
        save_snapshot(path or BASE_DIR.parent / 'traffic_daily_baseline.json', snapshot)
    health = snapshot['site_health']
    print(f"[Health] {health['endpoints_ok']}/{health['total_endpoints_scanned']} endpoints passed; traffic and account statuses are unmeasured.")
    return snapshot


if __name__ == '__main__':
    main()
