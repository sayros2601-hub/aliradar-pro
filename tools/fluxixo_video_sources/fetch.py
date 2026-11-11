"""Read-only: ask the official AliExpress affiliate API, per market, for the product video of every catalog item.

Writes work/video-sources.json (public product data only). Never prints credentials, signed requests or raw bodies.
"""
import hashlib, hmac, json, os, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://api-sg.aliexpress.com/sync'
METHOD = 'aliexpress.affiliate.productdetail.get'
MARKETS = ('US', 'BR', 'MX', 'IL', 'FR')
HERE = Path(__file__).parent
KEY, SECRET = os.environ['ALI_APP_KEY'].strip(), os.environ['ALI_APP_SECRET'].strip()


def call(params):
    values = {**params, 'app_key': KEY, 'method': METHOD, 'sign_method': 'sha256',
              'timestamp': str(int(datetime.now(timezone.utc).timestamp() * 1000))}
    values['sign'] = hmac.new(SECRET.encode(), ''.join(f'{k}{v}' for k, v in sorted(values.items())).encode(),
                              hashlib.sha256).hexdigest().upper()
    with urlopen(Request(API, data=urlencode(values).encode(), method='POST'), timeout=40) as r:
        return json.loads(r.read())


def rows(response):
    result = response.get('aliexpress_affiliate_productdetail_get_response', {}).get('resp_result', {})
    if str(result.get('resp_code')) not in ('200', '0'):
        return None, str(result.get('resp_code')) + ' ' + str(result.get('resp_msg', ''))[:120]
    found = ((result.get('result') or {}).get('products') or {}).get('product') or []
    return ([found] if isinstance(found, dict) else found), None


ids = json.loads((HERE / 'ids.json').read_text(encoding='utf-8'))  # {catalog id: AliExpress item id}
items = sorted(set(ids.values()))
out = {item: {'markets': {}, 'video': {}} for item in items}
problems = []
for market in MARKETS:
    for start in range(0, len(items), 20):
        batch = items[start:start + 20]
        try:
            found, error = rows(call({'product_ids': ','.join(batch), 'country': market, 'target_currency': 'USD',
                                      'target_language': 'EN', 'tracking_id': 'default'}))
        except Exception as e:
            found, error = None, type(e).__name__
        if found is None:
            problems.append({'market': market, 'batch': start, 'error': error})
            continue
        for row in found:
            item = str(row.get('product_id'))
            if item not in out:
                continue
            out[item]['markets'][market] = True
            out[item]['title'] = str(row.get('product_title', ''))[:300]
            for k, v in row.items():
                if 'video' in k.lower() and v:
                    out[item]['video'][k] = v
        time.sleep(0.4)
for item in items:
    for market in MARKETS:
        out[item]['markets'].setdefault(market, False)
Path('work').mkdir(exist_ok=True)
Path('work/video-sources.json').write_text(json.dumps({'ids': ids, 'items': out, 'problems': problems,
                                                        'observed_at': datetime.now(timezone.utc).isoformat()},
                                                       ensure_ascii=False, indent=1), encoding='utf-8')
with_video = sum(1 for v in out.values() if v['video'])
print(f'{len(items)} items, {with_video} with a video field, {len(problems)} failed batches')
