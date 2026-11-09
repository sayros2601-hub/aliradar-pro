"""Refresh price, rating and order counts from the official AliExpress affiliate API.

Writes tools/offers.json for the page builder. Never fails the pipeline: on any problem the
previous file is kept and pages simply show no price once the data is older than the builder allows.

Usage: python refresh_offers.py [--resolve-only]
Needs ALI_APP_SECRET (and optionally ALI_APP_KEY) in the environment unless --resolve-only is given.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'dist' / 'js' / 'catalog.js'
ITEM_IDS = ROOT / 'tools' / 'item_ids.json'
OFFERS = ROOT / 'tools' / 'offers.json'
API_URL = 'https://api-sg.aliexpress.com/sync'
BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
BATCH = 40


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def load(path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')


def resolve_item_id(short_url):
    """Follow the affiliate short link until the numeric item id appears in a redirect target."""
    opener = urllib.request.build_opener(NoRedirect)
    url = short_url
    for _ in range(4):
        match = re.search(r'/item/(\d{8,})\.html', url)
        if match:
            return match.group(1)
        request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': BROWSER})
        try:
            opener.open(request, timeout=20)
            return None
        except urllib.error.HTTPError as error:
            url = error.headers.get('Location') or ''
            if not url:
                return None
        except OSError:
            return None
    match = re.search(r'/item/(\d{8,})\.html', url)
    return match.group(1) if match else None


def call_api(method, params, app_key, app_secret):
    payload = {'app_key': app_key, 'method': method, 'sign_method': 'sha256',
               'timestamp': str(int(time.time() * 1000)), **params}
    text = ''.join(f'{key}{value}' for key, value in sorted(payload.items()))
    payload['sign'] = hmac.new(app_secret.encode('utf-8'), text.encode('utf-8'), hashlib.sha256).hexdigest().upper()
    request = urllib.request.Request(API_URL, data=urllib.parse.urlencode(payload).encode('utf-8'))
    return json.loads(urllib.request.urlopen(request, timeout=25).read().decode('utf-8'))


def main():
    catalog = json.loads(CATALOG.read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
    products = [p for p in catalog['products'] if p.get('affiliateUrl') and not p.get('demo')]
    item_ids = load(ITEM_IDS, {})
    missing = [p for p in products if p['id'] not in item_ids]
    for product in missing[:120]:
        item_id = resolve_item_id(product['affiliateUrl'])
        if item_id:
            item_ids[product['id']] = item_id
        time.sleep(0.4)
    if missing:
        save(ITEM_IDS, item_ids)
    print(f'Item ids known for {sum(p["id"] in item_ids for p in products)} of {len(products)} products.')
    if '--resolve-only' in sys.argv:
        return

    app_secret = os.environ.get('ALI_APP_SECRET', '')
    app_key = os.environ.get('ALI_APP_KEY', '') or '557652'
    if not app_secret:
        print('ALI_APP_SECRET not set; offers not refreshed.')
        return
    by_item = {item_ids[p['id']]: p['id'] for p in products if p['id'] in item_ids}
    offers = load(OFFERS, {})
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    ids = list(by_item)
    refreshed = 0
    for start in range(0, len(ids), BATCH):
        chunk = ids[start:start + BATCH]
        try:
            response = call_api('aliexpress.affiliate.productdetail.get', {
                'product_ids': ','.join(chunk), 'target_currency': 'USD', 'target_language': 'EN',
                'tracking_id': 'default',
                'fields': 'product_id,target_sale_price,target_sale_price_currency,target_original_price,discount,evaluate_rate,lastest_volume',
            }, app_key, app_secret)
        except Exception as error:  # network or API outage: keep what we have
            print(f'Offer batch {start // BATCH + 1} failed: {type(error).__name__}')
            continue
        body = response.get('aliexpress_affiliate_productdetail_get_response', {}).get('resp_result', {})
        rows = (body.get('result') or {}).get('products', {}).get('product', []) if isinstance(body, dict) else []
        if not rows:
            # Shape only, never values: helps diagnose a changed response without leaking anything.
            print(f'Offer batch {start // BATCH + 1}: no products; keys={sorted(response)[:3]} code={body.get("resp_code") if isinstance(body, dict) else None}')
        for row in rows:
            product_id = by_item.get(str(row.get('product_id')))
            price = str(row.get('target_sale_price') or '').strip()
            if not product_id or not re.fullmatch(r'\d+(\.\d{1,2})?', price) or float(price) <= 0:
                continue
            offers[product_id] = {
                'item_id': str(row.get('product_id')),
                'price': price,
                'currency': str(row.get('target_sale_price_currency') or 'USD'),
                'original_price': str(row.get('target_original_price') or ''),
                'discount': str(row.get('discount') or ''),
                'rating': str(row.get('evaluate_rate') or ''),
                'orders': int(row.get('lastest_volume') or 0),
                'checked': now,
            }
            refreshed += 1
        time.sleep(1.5)
    save(OFFERS, offers)
    print(f'Offers refreshed for {refreshed} of {len(ids)} products.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Offer refresh skipped: {type(error).__name__}: {error}')
