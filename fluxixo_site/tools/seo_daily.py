"""Daily SEO watch for www.fluxixo.shop across Google Search Console, Bing Webmaster and Yandex Webmaster.

Stage 1 (this file): read every engine's numbers, find opportunities, ask engines to recrawl pages that are not in
their index yet, and keep a private history. It never edits the site; stage 2 will use the history to adjust titles
and texts slowly (one change per page per few weeks, rolled back when a page does worse).

The repository is public, so search queries are never written in the clear: the history and the full Russian report
are encrypted with SEO_DATA_KEY (data/seo/*.enc). The GitHub job summary only shows totals.

Secrets (GitHub Actions) or, with --local, the DPAPI store in .local/ on the owner's PC:
  GSC_SERVICE_ACCOUNT_JSON   Google service account JSON (the account is added as a user in Search Console)
  BING_WEBMASTER_API_KEY     Bing Webmaster API key                        (.local/bing-api-key.dpapi)
  YANDEX_WEBMASTER_TOKEN     Yandex OAuth token with webmaster:hostinfo     (.local/yandex-oauth-token.dpapi)
  SEO_DATA_KEY               Fernet key for data/seo/*.enc                  (.local/seo-data-key.dpapi)

  python tools/seo_daily.py [--local] [--dry-run] [--summary FILE] [--report FILE]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parent
DIST = SITE / 'dist'
DATA = REPO / 'data/seo'
STATE_FILE = DATA / 'state.enc'
REPORT_FILE = DATA / 'report.enc'
ORIGIN = 'https://www.fluxixo.shop'
SITEMAPS = ('sitemap.xml', 'sitemap-ru.xml')

KEEP_DAYS = 400              # daily totals per engine
KEEP_WEEKS = 26              # weekly page/query snapshots for stage 2
SNAPSHOT_ROWS = 400          # rows kept per engine per weekly snapshot
GOOGLE_INSPECT_PER_DAY = 60  # URL Inspection API allows 2000/day; a slow rotation covers the site every ~10 days
YANDEX_RECRAWL_PER_DAY = 20  # stays well under the daily recrawl quota
RECRAWL_AGAIN_DAYS = 14      # the same page is not asked for twice within two weeks
KEYWORD_LOOKUPS_PER_DAY = 8  # Bing keyword research per day (product names, rotating)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ---------- plumbing ----------

class ApiError(Exception):
    pass


def http(method, url, *, headers=None, body=None, timeout=40):
    data = None
    headers = {'User-Agent': 'fluxixo-seo-daily/1.0', 'Accept': 'application/json', **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json; charset=utf-8'
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method),
                                        timeout=timeout) as response:
                text = response.read().decode('utf-8', 'replace')
                return json.loads(text) if text.strip() else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', 'replace')[:300]
            if error.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                last = ApiError(f'HTTP {error.code}: {detail}')
                continue
            raise ApiError(f'HTTP {error.code}: {detail}') from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last = ApiError(type(error).__name__)
            time.sleep(3 * (attempt + 1))
    raise last


def secrets(local):
    names = {'GSC_SERVICE_ACCOUNT_JSON': 'gsc-service-account.dpapi', 'BING_WEBMASTER_API_KEY': 'bing-api-key.dpapi',
             'YANDEX_WEBMASTER_TOKEN': 'yandex-oauth-token.dpapi', 'SEO_DATA_KEY': 'seo-data-key.dpapi'}
    found = {name: (os.environ.get(name) or '').strip() for name in names}
    if local:
        sys.path.insert(0, str(SITE / 'tools'))
        from dpapi_store import load_credential
        for name, file in names.items():
            if not found[name]:
                found[name] = (load_credential(file) or '').strip()
    return found


def sitemap_urls():
    urls = []
    for name in SITEMAPS:
        path = DIST / name
        if not path.exists():
            continue
        for loc in ET.parse(path).getroot().iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            if loc.text and loc.text not in urls:
                urls.append(loc.text.strip())
    return urls


def ru_url(url):
    path = urllib.parse.urlsplit(url).path
    return not path.startswith(('/en/', '/pt/', '/es/', '/fr/', '/he/')) and path != '/'


# ---------- encrypted state ----------

def load_state(key):
    empty = {'version': 1, 'days': {}, 'weeks': {}, 'inspected': {}, 'recrawled': {}, 'keywords': {}}
    if not key or not STATE_FILE.exists():
        return empty
    from cryptography.fernet import Fernet, InvalidToken
    try:
        state = json.loads(zlib.decompress(Fernet(key.encode()).decrypt(STATE_FILE.read_bytes())).decode('utf-8'))
    except (InvalidToken, ValueError, zlib.error):
        raise SystemExit('data/seo/state.enc cannot be opened with SEO_DATA_KEY (wrong key?); stopping so history is not lost.')
    for field, value in empty.items():
        state.setdefault(field, value)
    return state


def encrypt(key, value):
    from cryptography.fernet import Fernet
    raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return Fernet(key.encode()).encrypt(zlib.compress(raw, 9))


def trim(state, today):
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    state['days'] = {d: v for d, v in state['days'].items() if d >= cutoff}
    weeks = sorted(state['weeks'])
    state['weeks'] = {w: state['weeks'][w] for w in weeks[-KEEP_WEEKS:]}
    old = (today - timedelta(days=90)).isoformat()
    state['recrawled'] = {u: d for u, d in state['recrawled'].items() if d >= old}


# ---------- Google Search Console ----------

def google(secret, urls, state, today, dry_run):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    info = json.loads(secret)
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/webmasters'])
    credentials.refresh(Request())
    auth = {'Authorization': f'Bearer {credentials.token}'}
    sites = http('GET', 'https://www.googleapis.com/webmasters/v3/sites', headers=auth).get('siteEntry', [])
    owned = [s['siteUrl'] for s in sites if s.get('permissionLevel') != 'siteUnverifiedUser']
    site = next((s for s in ('sc-domain:fluxixo.shop', ORIGIN + '/') if s in owned), None)
    if not site:
        raise ApiError(f'служебный аккаунт {info.get("client_email")} не добавлен в Search Console для fluxixo.shop')
    enc = urllib.parse.quote(site, safe='')
    end = today - timedelta(days=2)              # Google's numbers settle after about two days
    start = end - timedelta(days=27)
    def query(dimensions, limit=25000):
        body = {'startDate': start.isoformat(), 'endDate': end.isoformat(), 'dimensions': dimensions,
                'rowLimit': limit, 'dataState': 'all'}
        return http('POST', f'https://www.googleapis.com/webmasters/v3/sites/{enc}/searchAnalytics/query',
                    headers=auth, body=body).get('rows', [])
    rows = [{'query': r['keys'][0], 'page': r['keys'][1], 'clicks': r['clicks'], 'impressions': r['impressions'],
             'position': round(r['position'], 1)} for r in query(['query', 'page'])]
    daily = {r['keys'][0]: {'clicks': r['clicks'], 'impressions': r['impressions'], 'position': round(r['position'], 1)}
             for r in query(['date'], 100)}
    # Index coverage: a slow rotation through the sitemap, pages never checked or checked longest ago first.
    inspected = state['inspected']
    order = sorted(urls, key=lambda u: inspected.get(u, {}).get('date', ''))
    checked = 0
    for url in order[:GOOGLE_INSPECT_PER_DAY]:
        try:
            result = http('POST', 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', headers=auth,
                          body={'inspectionUrl': url, 'siteUrl': site}).get('inspectionResult', {}).get('indexStatusResult', {})
        except ApiError:
            break
        inspected[url] = {'date': today.isoformat(), 'verdict': result.get('verdict'),
                          'coverage': result.get('coverageState'), 'crawled': result.get('lastCrawlTime')}
        checked += 1
    # Sitemaps: resubmitted once a week so Google re-reads them.
    sitemaps = http('GET', f'https://www.googleapis.com/webmasters/v3/sites/{enc}/sitemaps', headers=auth).get('sitemap', [])
    known = {s.get('path'): s for s in sitemaps}
    submitted = []
    for name in SITEMAPS:
        feed = f'{ORIGIN}/{name}'
        last = (known.get(feed) or {}).get('lastSubmitted', '')[:10]
        if not dry_run and (not last or last <= (today - timedelta(days=7)).isoformat()):
            http('PUT', f'https://www.googleapis.com/webmasters/v3/sites/{enc}/sitemaps/{urllib.parse.quote(feed, safe="")}', headers=auth)
            submitted.append(name)
    states = [inspected[u] for u in urls if u in inspected]
    return {
        'property': site, 'period': [start.isoformat(), end.isoformat()], 'rows': rows, 'daily': daily,
        'totals': totals(rows),
        'index': {'checked_today': checked, 'known': len(states),
                  'indexed': sum(1 for s in states if s.get('verdict') == 'PASS'),
                  'not_indexed': sorted(u for u in urls if inspected.get(u, {}).get('verdict') not in (None, 'PASS'))},
        'sitemaps': {s.get('path'): {'errors': s.get('errors'), 'warnings': s.get('warnings'),
                                     'lastDownloaded': s.get('lastDownloaded')} for s in sitemaps},
        'sitemaps_resubmitted': submitted,
    }


# ---------- Bing Webmaster ----------

def bing(key, state, today, products):
    q = urllib.parse.quote
    def call(method, **params):
        query = '&'.join(f'{k}={q(str(v))}' for k, v in {'apikey': key, **params}.items())
        result = http('GET', f'https://ssl.bing.com/webmaster/api.svc/json/{method}?{query}')
        return result.get('d') if isinstance(result, dict) else result
    site = ORIGIN + '/'
    sites = [s.get('Url') for s in call('GetUserSites') or []]
    if site not in sites:
        raise ApiError('www.fluxixo.shop нет в этом кабинете Bing Webmaster')
    queries = call('GetQueryStats', siteUrl=site) or []
    pages = call('GetPageStats', siteUrl=site) or []
    issues = call('GetCrawlIssues', siteUrl=site) or []
    quota = call('GetUrlSubmissionQuota', siteUrl=site) or {}
    def last_28_days(items, key_name):
        """Bing returns weekly rows for months; keep the last 28 days and add them up per query or page."""
        since = (datetime.combine(today - timedelta(days=28), datetime.min.time(), timezone.utc).timestamp()) * 1000
        merged = {}
        for item in items:
            stamp = str(item.get('Date', ''))
            digits = ''.join(ch for ch in stamp.split('+')[0].split('-')[0] if ch.isdigit())
            if digits and int(digits) < since:
                continue
            row = merged.setdefault(item.get('Query'), {key_name: item.get('Query'), 'clicks': 0, 'impressions': 0, '_w': 0.0})
            impressions = item.get('Impressions', 0) or 0
            row['clicks'] += item.get('Clicks', 0) or 0
            row['impressions'] += impressions
            row['_w'] += (item.get('AvgImpressionPosition', 0) or 0) * impressions
        for row in merged.values():
            row['position'] = round(row.pop('_w') / row['impressions'], 1) if row['impressions'] else None
        return list(merged.values())
    query_rows = last_28_days(queries, 'query')
    page_rows = last_28_days(pages, 'page')
    # Keyword research: real Bing search volume around our product names, a few names per day in rotation.
    research = state['keywords']
    names = [n for n in products if n not in research] + sorted((n for n in products if n in research),
                                                                key=lambda n: research[n].get('date', ''))
    looked = 0
    end = today - timedelta(days=3)
    for name in names[:KEYWORD_LOOKUPS_PER_DAY]:
        try:
            related = call('GetRelatedKeywords', q=name, country='us', language='en-US',
                           startDate=(end - timedelta(days=90)).isoformat(), endDate=end.isoformat()) or []
        except ApiError:
            break
        research[name] = {'date': today.isoformat(),
                          'related': sorted(({'query': k.get('Query'), 'impressions': k.get('Impressions', 0),
                                              'broad': k.get('BroadImpressions', 0)} for k in related),
                                            key=lambda k: -k['impressions'])[:15]}
        looked += 1
    return {'rows': query_rows, 'pages': page_rows, 'totals': totals(query_rows),
            'crawl_issues': [{'url': i.get('Url'), 'issue': i.get('Issues')} for i in issues][:200],
            'submission_quota': {'daily': quota.get('DailyQuota'), 'monthly': quota.get('MonthlyQuota')},
            'keyword_lookups_today': looked}


# ---------- Yandex Webmaster ----------

def yandex(token, urls, state, today, dry_run):
    auth = {'Authorization': f'OAuth {token}'}
    api = 'https://api.webmaster.yandex.net/v4'
    user = http('GET', f'{api}/user', headers=auth)['user_id']
    hosts = http('GET', f'{api}/user/{user}/hosts', headers=auth).get('hosts', [])
    host = next((h['host_id'] for h in hosts if 'www.fluxixo.shop' in h.get('host_id', '')), None)
    if not host:
        raise ApiError('www.fluxixo.shop нет в этом кабинете Яндекс Вебмастера')
    base = f'{api}/user/{user}/hosts/{urllib.parse.quote(host, safe="")}'
    pending = []
    def read(path, default):
        """A new site answers HOST_NOT_LOADED until Yandex has processed it: that is 'no data yet', not a failure."""
        try:
            return http('GET', f'{base}/{path}', headers=auth)
        except ApiError as error:
            if 'ACCESS_FORBIDDEN' in str(error):
                raise ApiError('у токена Яндекса нет нужных прав, нужен новый токен') from None
            if 'HOST_NOT_LOADED' in str(error) or 'HTTP 404' in str(error):
                pending.append(path.split('?')[0])
                return default
            raise
    summary = read('summary', {})
    indicators = '&'.join(f'query_indicator={i}' for i in ('TOTAL_SHOWS', 'TOTAL_CLICKS', 'AVG_SHOW_POSITION', 'AVG_CLICK_POSITION'))
    popular = read(f'search-queries/popular?order_by=TOTAL_SHOWS&{indicators}&limit=500', {})
    rows = []
    for item in popular.get('queries', []):
        values = item.get('indicators', {})
        rows.append({'query': item.get('query_text'), 'clicks': values.get('TOTAL_CLICKS') or 0,
                     'impressions': values.get('TOTAL_SHOWS') or 0,
                     'position': round(values.get('AVG_SHOW_POSITION') or 0, 1)})
    problems = read('diagnostics', {}).get('problems', {})
    in_search, offset = set(), 0
    while offset < 3000:
        page = read(f'search-urls/in-search/samples?offset={offset}&limit=100', {})
        samples = page.get('samples', [])
        in_search.update(s.get('url') for s in samples if s.get('url'))
        offset += 100
        if len(samples) < 100:
            break
    # Sitemaps: Yandex only learns the page list once the sitemaps are added in Webmaster; add any that are missing.
    known = {s.get('sitemap_url') for s in read('sitemaps', {}).get('sitemaps', [])}
    known |= {s.get('sitemap_url') for s in read('user-added-sitemaps', {}).get('sitemaps', [])}
    sitemaps_added, recrawl_error = [], None
    for name in SITEMAPS:
        feed = f'{ORIGIN}/{name}'
        if feed in known or dry_run:
            continue
        try:
            http('POST', f'{base}/user-added-sitemaps', headers=auth, body={'url': feed})
            sitemaps_added.append(name)
        except ApiError as error:
            recrawl_error = f'sitemap {name}: {error}'[:200]
    # Recrawl: Russian pages that are not in Yandex search yet, not asked within two weeks, a few per day.
    quota = read('recrawl/quota', {})
    allowed = min(YANDEX_RECRAWL_PER_DAY, int(quota.get('quota_remainder') or 0))
    again = (today - timedelta(days=RECRAWL_AGAIN_DAYS)).isoformat()
    missing = [u for u in urls if ru_url(u) and u not in in_search]
    sent = []
    for url in [u for u in missing if state['recrawled'].get(u, '') < again][:allowed]:
        if dry_run:
            sent.append(url)
            continue
        try:
            http('POST', f'{base}/recrawl/queue', headers=auth, body={'url': url})
        except ApiError as error:
            recrawl_error = f'переобход: {error}'[:200]  # tried again tomorrow
            break
        state['recrawled'][url] = today.isoformat()
        sent.append(url)
    return {'rows': rows, 'totals': totals(rows),
            'summary': {'sqi': summary.get('sqi'), 'searchable': summary.get('searchable_pages_count'),
                        'excluded': summary.get('excluded_pages_count'), 'problems': summary.get('site_problems')},
            'problems': {k: v.get('state') for k, v in problems.items() if isinstance(v, dict) and v.get('state') == 'PRESENT'},
            'in_search': len(in_search), 'ru_missing': len(missing), 'recrawl_sent': sent,
            'recrawl_quota_left': quota.get('quota_remainder'), 'not_loaded': sorted(set(pending)),
            'sitemaps_added': sitemaps_added, 'recrawl_error': recrawl_error}


# ---------- analysis ----------

def totals(rows):
    clicks = sum(r.get('clicks', 0) for r in rows)
    impressions = sum(r.get('impressions', 0) for r in rows)
    weighted = sum(r.get('position', 0) * r.get('impressions', 0) for r in rows)
    return {'clicks': clicks, 'impressions': impressions,
            'ctr': round(100 * clicks / impressions, 2) if impressions else 0.0,
            'position': round(weighted / impressions, 1) if impressions else None, 'queries': len(rows)}


def opportunities(rows):
    """Two kinds the stage-2 editor will act on: shown but not clicked, and almost on page one."""
    weak_ctr = [r for r in rows if r.get('impressions', 0) >= 30 and (r.get('clicks') or 0) / r['impressions'] < 0.015]
    near_top = [r for r in rows if 8 <= (r.get('position') or 0) <= 20 and r.get('impressions', 0) >= 10]
    key = lambda r: -r.get('impressions', 0)
    return {'weak_ctr': sorted(weak_ctr, key=key)[:30], 'near_top': sorted(near_top, key=key)[:30]}


def product_names():
    try:
        data = json.loads((SITE / 'tools/i18n_data.json').read_text(encoding='utf-8'))['products']
        catalog = json.loads((DIST / 'js/catalog.js').read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
    except (OSError, ValueError, KeyError):
        return []
    names = []
    for product in catalog['products']:
        name = (data.get(product['id'], {}).get('en') or {}).get('name')
        if name and name not in names:
            names.append(name)
    return names


def report_text(today, results, errors, keywords=()):
    lines = [f'# FLUXIXO — SEO за {today.isoformat()}', '']
    titles = {'google': 'Google', 'bing': 'Bing', 'yandex': 'Яндекс'}
    for engine, title in titles.items():
        lines.append(f'## {title}')
        if engine in errors:
            lines += [f'Не подключено: {errors[engine]}', '']
            continue
        data = results[engine]
        t = data['totals']
        lines.append(f'Клики {t["clicks"]}, показы {t["impressions"]}, CTR {t["ctr"]}%, средняя позиция {t["position"] or "—"}, запросов {t["queries"]}.')
        if engine == 'google':
            i = data['index']
            lines.append(f'Индекс: проверено страниц {i["known"]}, в индексе {i["indexed"]}, не в индексе {len(i["not_indexed"])}.')
            lines += [f'- не в индексе: {u}' for u in i['not_indexed'][:20]]
        if engine == 'yandex':
            s = data['summary']
            lines.append(f'ИКС {s["sqi"]}, страниц в поиске {s["searchable"]}, исключено {s["excluded"]}; русских страниц вне поиска {data["ru_missing"]}, отправлено на переобход {len(data["recrawl_sent"])}.')
            if data['problems']:
                lines.append('Проблемы сайта: ' + ', '.join(data['problems']))
            if data['not_loaded']:
                lines.append('Яндекс ещё не загрузил данные по сайту (новый сайт): ' + ', '.join(data['not_loaded']))
            if data['sitemaps_added']:
                lines.append('Добавлены sitemap в Вебмастер: ' + ', '.join(data['sitemaps_added']))
            if data['recrawl_error']:
                lines.append('Яндекс не принял запрос: ' + data['recrawl_error'])
        if engine == 'bing' and data['crawl_issues']:
            lines.append(f'Ошибки обхода: {len(data["crawl_issues"])}')
        if engine == 'bing' and keywords:
            lines.append('Что ищут в Bing рядом с нашими товарами (показы за 3 месяца, США):')
            for name, found in keywords:
                top = ', '.join(f'{k["query"]} ({k["impressions"]})' for k in found[:6])
                lines.append(f'- {name}: {top}')
        chances = opportunities(data['rows'])
        if chances['weak_ctr']:
            lines.append('Показывают, но не кликают (заголовок/описание стоит переписать):')
            lines += [f'- «{r["query"]}» — показы {r["impressions"]}, клики {r["clicks"]}, позиция {r["position"]}' for r in chances['weak_ctr'][:10]]
        if chances['near_top']:
            lines.append('Почти на первой странице (позиция 8–20):')
            lines += [f'- «{r["query"]}» — позиция {r["position"]}, показы {r["impressions"]}' for r in chances['near_top'][:10]]
        lines.append('')
    return '\n'.join(lines)


def summary_text(today, results, errors):
    """Totals only: the repository and its job pages are public."""
    lines = [f'### FLUXIXO SEO — {today.isoformat()}', '', '| | Клики | Показы | CTR | Позиция | Статус |', '|---|---|---|---|---|---|']
    for engine, title in (('google', 'Google'), ('bing', 'Bing'), ('yandex', 'Яндекс')):
        if engine in errors:
            lines.append(f'| {title} | — | — | — | — | не подключено: {errors[engine]} |')
            continue
        t = results[engine]['totals']
        extra = ''
        if engine == 'google':
            i = results[engine]['index']
            extra = f'в индексе {i["indexed"]} из {i["known"]} проверенных'
        elif engine == 'yandex':
            extra = f'в поиске {results[engine]["in_search"]}, на переобход {len(results[engine]["recrawl_sent"])}'
            if results[engine]['not_loaded']:
                extra += '; Яндекс ещё не загрузил данные по сайту'
            if results[engine]['sitemaps_added']:
                extra += f'; добавлено sitemap: {len(results[engine]["sitemaps_added"])}'
        elif engine == 'bing':
            extra = f'ключевых слов изучено {results[engine]["keyword_lookups_today"]}'
        lines.append(f'| {title} | {t["clicks"]} | {t["impressions"]} | {t["ctr"]}% | {t["position"] or "—"} | {extra} |')
    return '\n'.join(lines) + '\n'


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='read keys from the DPAPI store on this PC')
    parser.add_argument('--dry-run', action='store_true', help='no recrawl or sitemap requests, no files written')
    parser.add_argument('--summary', help='append the totals table here (GITHUB_STEP_SUMMARY)')
    parser.add_argument('--report', help='also write the full Russian report here (local use only)')
    parser.add_argument('--show-report', action='store_true', help='print the latest stored report (needs the key)')
    args = parser.parse_args()
    today = datetime.now(timezone.utc).date()
    keys = secrets(args.local)
    if args.show_report:
        from cryptography.fernet import Fernet
        if not (keys['SEO_DATA_KEY'] and REPORT_FILE.exists()):
            raise SystemExit('No stored report or no SEO_DATA_KEY.')
        print(zlib.decompress(Fernet(keys['SEO_DATA_KEY'].encode()).decrypt(REPORT_FILE.read_bytes())).decode('utf-8'))
        return
    state = load_state(keys['SEO_DATA_KEY'])
    urls = sitemap_urls()
    results, errors = {}, {}
    jobs = (('google', 'GSC_SERVICE_ACCOUNT_JSON', 'нет ключа Google (GSC_SERVICE_ACCOUNT_JSON)',
             lambda k: google(k, urls, state, today, args.dry_run)),
            ('bing', 'BING_WEBMASTER_API_KEY', 'нет ключа Bing (BING_WEBMASTER_API_KEY)',
             lambda k: bing(k, state, today, product_names())),
            ('yandex', 'YANDEX_WEBMASTER_TOKEN', 'нет токена Яндекса (YANDEX_WEBMASTER_TOKEN)',
             lambda k: yandex(k, urls, state, today, args.dry_run)))
    for engine, secret, missing, run in jobs:
        if not keys[secret]:
            errors[engine] = missing
            continue
        try:
            results[engine] = run(keys[secret])
        except Exception as error:  # one engine failing never stops the others
            errors[engine] = (str(error) if isinstance(error, ApiError) else f'{type(error).__name__}: {error}')[:300]
        print(f'{engine}: {"ok" if engine in results else errors[engine]}', flush=True)

    day = state['days'].setdefault(today.isoformat(), {})
    week = today.isocalendar()
    week_key = f'{week[0]}-W{week[1]:02d}'
    snapshot = state['weeks'].setdefault(week_key, {})
    for engine, data in results.items():
        day[engine] = data['totals'] | ({'index': {k: v for k, v in data['index'].items() if k != 'not_indexed'}}
                                         if engine == 'google' else {})
        snapshot[engine] = {'rows': sorted(data['rows'], key=lambda r: -r.get('impressions', 0))[:SNAPSHOT_ROWS],
                            **({'pages': data['pages'][:SNAPSHOT_ROWS]} if 'pages' in data else {})}
        if engine == 'google':
            snapshot[engine]['daily'] = data['daily']
        if engine == 'yandex':
            day[engine] |= {'in_search': data['in_search'], 'recrawl_sent': len(data['recrawl_sent']),
                            'sqi': data['summary']['sqi']}
    trim(state, today)
    fresh = [(name, k['related']) for name, k in state['keywords'].items() if k.get('date') == today.isoformat() and k['related']]
    report = report_text(today, results, errors, fresh)
    summary = summary_text(today, results, errors)
    print(summary)
    if args.summary:
        with open(args.summary, 'a', encoding='utf-8') as stream:
            stream.write(summary)
    if args.report:
        Path(args.report).write_text(report, encoding='utf-8')
    if args.dry_run:
        return
    if not keys['SEO_DATA_KEY']:
        print('SEO_DATA_KEY is not set: history is not stored (the repository is public).')
        return
    DATA.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_bytes(encrypt(keys['SEO_DATA_KEY'], state))
    REPORT_FILE.write_bytes(encrypt(keys['SEO_DATA_KEY'], report.encode('utf-8')))


if __name__ == '__main__':
    main()
