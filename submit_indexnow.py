"""Notify IndexNow after verified publication; acceptance never means indexing."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from dealvault_core import BASE_DIR, DATA_DIR, DOMAIN, LANGUAGES, read_json, write_json, utc_now

STATE = BASE_DIR/'.local/search-before-release.json'
REPORT = BASE_DIR/'.local/indexnow-last-submission.json'


def get_json(name):
    request = Request(DOMAIN+'/'+name, headers={'User-Agent':'DealVault-Search-Update/1.0'})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def capture(path=STATE):
    try:
        state = {'available':True, 'build':get_json('build-info.json'), 'feed':get_json('feed.json')}
    except (OSError, ValueError) as error:
        state = {'available':False, 'error_type':type(error).__name__}
    write_json(path, state)
    print('[IndexNow] Previous public release observation saved.')
    return state


def safe_url(url):
    if not isinstance(url, str): return False
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.netloc == urlsplit(DOMAIN).netloc
            and not parsed.query and not parsed.fragment and '/.' not in parsed.path
            and parsed.path.startswith('/'))


def plan(previous, root=BASE_DIR/'dist', force=False):
    root = Path(root)
    current = read_json(root/'build-info.json')
    all_urls = [loc.text for loc in ET.parse(root/'sitemap.xml').findall('.//{*}loc')]
    if not all_urls or not all(safe_url(url) for url in all_urls):
        raise ValueError('Only this site canonical URLs may be notified')
    if force:
        return sorted(set(all_urls))
    if not previous.get('available'):
        raise ValueError('Previous public state unavailable; no automatic bulk notification')
    if previous['build']['catalog_sha256'] == current['catalog_sha256']:
        return []
    def items(feed):
        result = {}
        for item in feed['items']:
            url = item.get('url')
            if not safe_url(url) or not url.startswith(DOMAIN+'/deals/'):
                raise ValueError('Invalid product URL in release observation')
            result[url] = item
        return result
    old = items(previous['feed'])
    new = items(read_json(root/'feed.json'))
    changed = {url for url in old.keys() | new.keys() if old.get(url) != new.get(url)}
    if not changed:
        # Catalog-only changes may affect localized pages while the English feed stays identical.
        return sorted(set(all_urls))
    urls = {DOMAIN+('/' if lang == 'en' else f'/{lang}/') for lang in LANGUAGES}
    for url in changed:
        route = url.removeprefix(DOMAIN+'/')
        for lang in LANGUAGES:
            urls.add(DOMAIN+'/'+('' if lang == 'en' else lang+'/')+route)
    if not all(safe_url(url) for url in urls):
        raise ValueError('Unsafe changed URL')
    return sorted(urls)


def post(payload):
    request = Request('https://api.indexnow.org/indexnow',
                      data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type':'application/json; charset=utf-8',
                               'User-Agent':'DealVault-Search-Update/1.0'}, method='POST')
    try:
        with urlopen(request, timeout=30) as response:
            response.read(4096)
            return response.status
    except HTTPError as error:
        return error.code


def submit(urls, sender=post):
    if not urls:
        return {'status':'unchanged', 'notified_urls':0, 'indexing_confirmed':False}
    if not all(safe_url(url) for url in urls):
        raise ValueError('Foreign or unsafe URL rejected before any network request')
    key = read_json(DATA_DIR/'site_integrations.json')['indexnow_key']
    location = DOMAIN+'/'+key+'.txt'
    with urlopen(Request(location, headers={'User-Agent':'DealVault-Search-Update/1.0'}), timeout=15) as response:
        if response.read().decode().strip() != key:
            raise ValueError('Published IndexNow key does not match')
    batches = []
    for start in range(0, len(urls), 10000):
        batch = urls[start:start+10000]
        code = sender({'host':urlsplit(DOMAIN).netloc, 'key':key,
                       'keyLocation':location, 'urlList':batch})
        batches.append({'http_status':code, 'urls':len(batch)})
        if code not in (200, 202):
            raise RuntimeError(f'IndexNow did not accept the notification: HTTP {code}')
    return {'status':'accepted' if all(b['http_status']==200 for b in batches) else 'key_validation_pending',
            'notified_urls':len(urls), 'batches':batches, 'indexing_confirmed':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.capture:
        if args.submit or args.force: parser.error('Capture is separate from notification')
        capture(); return
    urls = plan(read_json(STATE, {}), force=args.force)
    if not args.submit:
        print(f'[IndexNow] Dry run: {len(urls)} changed URLs; nothing sent.'); return
    published = get_json('build-info.json')
    if published['catalog_sha256'] != read_json(BASE_DIR/'dist/build-info.json')['catalog_sha256']:
        raise ValueError('Published catalog differs; no notifications sent')
    result = submit(urls)
    write_json(REPORT, {'checked_at':utc_now(), **result})
    print(f"[IndexNow] {result['status']}: {result['notified_urls']} URLs. Indexing is not guaranteed.")


if __name__ == '__main__':
    main()
