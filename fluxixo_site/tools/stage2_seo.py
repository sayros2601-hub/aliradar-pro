"""Autonomous Stage-2 SEO optimizer & rollback engine for FLUXIXO.

Closed-loop daily SEO automation:
1. Evaluates active experiments (>14 days old) and auto-rolls back any underperformer.
2. Detects per-country & per-query opportunities across Google, Bing, and Yandex + technical dist/ health.
3. Calls ai_seo (Gemini/Groq/OpenRouter or deterministic strategist) through the check_texts firewall.
4. Writes validated overrides to tools/seo_overrides.json, rebuilds & runs verify_release.py;
   automatically reverts on ANY build or verification failure.
"""
from __future__ import annotations

from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
import collections
import json
import os
import re
import subprocess
import sys
import urllib.parse

TOOLS_DIR = Path(__file__).resolve().parent
SITE_DIR = TOOLS_DIR.parent
REPO_DIR = SITE_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import ai_seo  # noqa: E402
import check_texts  # noqa: E402

OVERRIDES_FILE = TOOLS_DIR / 'seo_overrides.json'
PROTECTED_ROUTES = frozenset(('/products/import-0024/',))
EVAL_DAYS = 14
GRADUATE_DAYS = 28
COOLDOWN_DAYS = 30
MAX_EDITS_PER_RUN = 5
MAX_PROACTIVE_PER_RUN = 2


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.description = ''
        self.h1 = ''
        self._tag = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        if tag == 'meta' and a.get('name') == 'description':
            self.description = a.get('content', '')
        elif tag in ('title', 'h1'):
            self._tag = tag
            self._buf = []

    def handle_endtag(self, tag):
        if self._tag == tag:
            text = ' '.join(''.join(self._buf).split())
            if tag == 'title':
                self.title = text
            elif tag == 'h1' and not self.h1:
                self.h1 = text
            self._tag = None

    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)


def load_overrides(path=OVERRIDES_FILE):
    path = Path(path)
    if not path.exists():
        return {'version': 1, 'routes': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('routes'), dict):
            return data
    except (OSError, ValueError):
        pass
    return {'version': 1, 'routes': {}}


def save_overrides(data, path=OVERRIDES_FILE):
    path = Path(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def lang_from_path(route_path):
    m = re.match(r'^/(en|pt|es|fr|he)(?:/|$)', route_path)
    return m.group(1) if m else 'ru'


def page_file_for_route(dist_dir, route_path):
    clean = route_path.strip('/')
    return Path(dist_dir) / (f'{clean}/index.html' if clean else 'index.html')


def read_route_meta(dist_dir, route_path):
    file = page_file_for_route(dist_dir, route_path)
    if not file.exists():
        return None
    p = _MetaParser()
    p.feed(file.read_text(encoding='utf-8', errors='replace'))
    return {'title': p.title, 'description': p.description, 'h1': p.h1}


def collect_existing_meta(dist_dir, routes):
    titles, descs = set(), set()
    for route_path in routes:
        meta = read_route_meta(dist_dir, route_path)
        if meta:
            if meta['title']:
                titles.add(meta['title'])
            if meta['description']:
                descs.add(meta['description'])
    return titles, descs


def technical_audit(dist_dir):
    """Inspect dist/ readiness: per-country sitemaps, katord route, redirect rule margin, text lint."""
    dist_dir = Path(dist_dir)
    issues = []
    expected_maps = ('sitemap.xml', 'sitemap-index.xml', 'sitemap-ru.xml',
                     'sitemap-en.xml', 'sitemap-pt.xml', 'sitemap-es.xml', 'sitemap-fr.xml', 'sitemap-he.xml')
    missing_maps = [m for m in expected_maps if not (dist_dir / m).exists()]
    if missing_maps:
        issues.append(f'отсутствуют карты сайта: {", ".join(missing_maps)}')
    red_file = dist_dir / '_redirects'
    red_count = 0
    if red_file.exists():
        red_count = sum(1 for l in red_file.read_text(encoding='utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#'))
        if red_count > 90:
            issues.append(f'правил _redirects слишком много: {red_count} > 90')
    kat_ok = (dist_dir / 'products/katord-wifi-repeater/index.html').exists()
    if not kat_ok:
        issues.append('страница /products/katord-wifi-repeater/ отсутствует')
    lint_problems = check_texts.run()
    if lint_problems:
        issues.append(f'ошибки check_texts: {len(lint_problems)}')
    return {
        'ok': not issues,
        'redirect_rules': red_count,
        'katord_live': kat_ok,
        'text_problems': len(lint_problems),
        'issues': issues,
    }


def _page_metrics(results, origin='https://www.fluxixo.shop'):
    """Aggregate current impressions, clicks, weighted position, and top queries per normalized route path."""
    stats = collections.defaultdict(lambda: {'clicks': 0, 'impressions': 0, '_w': 0.0, 'queries': []})
    for engine in ('google', 'bing'):
        data = results.get(engine) or {}
        for row in data.get('rows', []):
            page_url = row.get('page') or ''
            if not page_url:
                continue
            path = urllib.parse.urlsplit(page_url).path or '/'
            if not path.endswith('/'):
                path += '/'
            imp = row.get('impressions', 0) or 0
            clk = row.get('clicks', 0) or 0
            pos = row.get('position') or 0
            entry = stats[path]
            entry['clicks'] += clk
            entry['impressions'] += imp
            entry['_w'] += pos * imp
            q = row.get('query')
            if q and q not in entry['queries']:
                entry['queries'].append(q)
    for entry in stats.values():
        imp = entry['impressions']
        entry['position'] = round(entry.pop('_w') / imp, 1) if imp else None
        entry['ctr'] = round(entry['clicks'] / imp, 4) if imp else 0.0
    return dict(stats)


def evaluate_experiments(today, state, overrides, metrics):
    """Evaluate active Stage-2 experiments after EVAL_DAYS and auto-rollback underperformers."""
    experiments = state.setdefault('experiments', {})
    cooldowns = state.setdefault('cooldowns', {})
    rolled_back, graduated = [], []

    for path, exp in list(experiments.items()):
        if exp.get('status') != 'active':
            continue
        started = exp.get('date', '')
        if not started:
            continue
        age_days = (today - __import__('datetime').date.fromisoformat(started)).days
        if age_days < EVAL_DAYS:
            continue
        cur = metrics.get(path)
        base = exp.get('baseline') or {}
        if cur:
            base_imp = base.get('impressions', 0) or 0
            base_clk = base.get('clicks', 0) or 0
            base_pos = base.get('position')
            cur_imp = cur.get('impressions', 0) or 0
            cur_clk = cur.get('clicks', 0) or 0
            cur_pos = cur.get('position')
            base_ctr = (base_clk / base_imp) if base_imp else 0.0
            cur_ctr = cur.get('ctr', 0.0)
            degraded_ctr = cur_imp >= 25 and base_ctr > 0 and cur_ctr < base_ctr * 0.7 and cur_clk <= base_clk
            degraded_pos = (base_pos is not None and cur_pos is not None and cur_pos > base_pos + 3.0 and cur_clk <= base_clk)
            if degraded_ctr or degraded_pos:
                overrides.get('routes', {}).pop(path, None)
                exp['status'] = 'rolled_back'
                exp['evaluated'] = today.isoformat()
                exp['result'] = cur
                cooldowns[path] = (today + timedelta(days=COOLDOWN_DAYS)).isoformat()
                rolled_back.append({'path': path, 'reason': 'ctr_drop' if degraded_ctr else 'position_drop'})
                continue
        if age_days >= GRADUATE_DAYS:
            exp['status'] = 'kept'
            exp['evaluated'] = today.isoformat()
            graduated.append(path)
    return rolled_back, graduated


def _bing_keywords_by_name(state):
    return {
        name.lower(): [k['query'] for k in info.get('related', []) if k.get('query')]
        for name, info in state.get('keywords', {}).items()
        if isinstance(info, dict)
    }


def _route_catalog_map(dist_dir):
    cat_file = Path(dist_dir) / 'js/catalog.js'
    if not cat_file.exists():
        return {}, {}
    cat = json.loads(cat_file.read_text(encoding='utf-8').split('=', 1)[1].strip().rstrip(';'))
    i18n_file = TOOLS_DIR / 'i18n_data.json'
    i18n = json.loads(i18n_file.read_text(encoding='utf-8')) if i18n_file.exists() else {'products': {}}
    products = [p for p in cat.get('products', []) if not p.get('demo')]
    by_route = {}
    for p in products:
        pid = p['id']
        by_route[f'/products/{pid}/'] = {'product': p, 'lang': 'ru', 'name': p['name'], 'category': p['category']}
        for lang, tr in (i18n.get('products', {}).get(pid, {}) or {}).items():
            if lang != 'ru' and tr.get('name'):
                by_route[f'/{lang}/products/{pid}/'] = {'product': p, 'lang': lang, 'name': tr['name'], 'category': p['category']}
    return by_route, products


def select_candidates(today, dist_dir, state, overrides, results, metrics):
    """Select up to MAX_EDITS_PER_RUN high-leverage routes across weak-CTR, near-top, and market gaps."""
    cooldowns = state.get('cooldowns', {})
    experiments = state.get('experiments', {})
    active_routes = overrides.get('routes', {})
    by_route, _ = _route_catalog_map(dist_dir)
    bing_kw = _bing_keywords_by_name(state)
    today_iso = today.isoformat()

    def eligible(path):
        if path in PROTECTED_ROUTES:
            return False
        if cooldowns.get(path, '') > today_iso:
            return False
        if experiments.get(path, {}).get('status') == 'active':
            return False
        return page_file_for_route(dist_dir, path).exists()

    ranked = []
    seen = set()

    # Priority 1: Live search opportunities from GSC (preferring per-country rows) and Bing
    g_data = results.get('google') or {}
    country_rows = g_data.get('country_rows') or g_data.get('rows') or []
    for row in sorted(country_rows, key=lambda r: -(r.get('impressions') or 0)):
        page_url = row.get('page') or ''
        path = urllib.parse.urlsplit(page_url).path or '/'
        if not path.endswith('/'):
            path += '/'
        if path in seen or not eligible(path):
            continue
        imp = row.get('impressions', 0) or 0
        clk = row.get('clicks', 0) or 0
        pos = row.get('position') or 99
        weak = imp >= 25 and (clk / imp) < 0.02
        near_top = imp >= 8 and 6.0 <= pos <= 22.0
        if not (weak or near_top):
            continue
        info = by_route.get(path, {})
        lang = info.get('lang') or lang_from_path(path)
        m = metrics.get(path, {})
        p_name = info.get('name', '')
        ranked.append({
            'path': path,
            'lang': lang,
            'reason': 'weak_ctr' if weak else 'near_top',
            'country': row.get('country') or ai_seo.MARKET_PROFILES[lang]['country_code'],
            'top_query': row.get('query', ''),
            'queries': m.get('queries', [row.get('query', '')]),
            'bing_keywords': bing_kw.get(p_name.lower(), []),
            'product_name': p_name,
            'category': info.get('category', ''),
            'impressions': imp,
            'clicks': clk,
            'position': pos,
        })
        seen.add(path)
        if len(ranked) >= MAX_EDITS_PER_RUN:
            return ranked

    # Priority 2: Up to MAX_PROACTIVE_PER_RUN proactive upgrades on products with real Bing US demand or missing overrides
    proactive = 0
    for path, info in by_route.items():
        if len(ranked) >= MAX_EDITS_PER_RUN or proactive >= MAX_PROACTIVE_PER_RUN:
            break
        if path in seen or path in active_routes or not eligible(path):
            continue
        en_info = by_route.get(f'/en/products/{info["product"]["id"]}/', {})
        kw_list = bing_kw.get((en_info.get('name') or '').lower(), []) if info['lang'] == 'en' else []
        if info['lang'] == 'en' and not kw_list:
            continue
        ranked.append({
            'path': path,
            'lang': info['lang'],
            'reason': 'bing_keyword_align' if kw_list else 'market_faq_enrichment',
            'country': ai_seo.MARKET_PROFILES[info['lang']]['country_code'],
            'top_query': kw_list[0] if kw_list else '',
            'queries': kw_list[:5],
            'bing_keywords': kw_list[:6],
            'product_name': info['name'],
            'category': info['category'],
            'impressions': 0,
            'clicks': 0,
            'position': None,
        })
        seen.add(path)
        proactive += 1
        if len(ranked) >= MAX_EDITS_PER_RUN:
            break

    # Backfill 1-2 un-optimized localized product pages across countries if neither GSC nor Bing keywords matched
    for path, info in by_route.items():
        if len(ranked) >= MAX_PROACTIVE_PER_RUN or proactive >= MAX_PROACTIVE_PER_RUN:
            break
        if path in seen or path in active_routes or not eligible(path):
            continue
        ranked.append({
            'path': path,
            'lang': info['lang'],
            'reason': 'market_seo_enrichment',
            'country': ai_seo.MARKET_PROFILES[info['lang']]['country_code'],
            'top_query': '',
            'queries': [],
            'bing_keywords': [],
            'product_name': info['name'],
            'category': info['category'],
            'impressions': 0,
            'clicks': 0,
            'position': None,
        })
        seen.add(path)
        proactive += 1
    return ranked[:MAX_EDITS_PER_RUN]


def default_rebuild_and_verify():
    """Rebuild search + redesign + sitemaps + release and run strict verify_release gate."""
    commands = (
        [sys.executable, '-B', str(TOOLS_DIR / 'check_texts.py')],
        [sys.executable, '-B', str(TOOLS_DIR / 'build_search.py')],
        [sys.executable, '-B', str(SITE_DIR / 'redesign/build_redesign.py'), '--production'],
        [sys.executable, '-B', str(TOOLS_DIR / 'write_sitemaps.py')],
        [sys.executable, '-B', str(SITE_DIR / 'build_release.py')],
        [sys.executable, '-B', str(TOOLS_DIR / 'verify_release.py'), str(SITE_DIR / 'release')],
    )
    for cmd in commands:
        res = subprocess.run(cmd, cwd=str(REPO_DIR), capture_output=True, text=True, encoding='utf-8', errors='replace')
        if res.returncode != 0:
            raise RuntimeError(f'{Path(cmd[-1]).name} failed: {(res.stdout + res.stderr).strip()[:300]}')


def run_stage2(today, dist_dir, results, state, ai_keys, *, apply_changes=False,
               overrides_path=OVERRIDES_FILE, verify_fn=default_rebuild_and_verify, transport=None):
    """Run autonomous Stage-2 evaluation, proposal, validation, build verification, and rollback safety."""
    dist_dir = Path(dist_dir)
    overrides_path = Path(overrides_path)
    original_raw = overrides_path.read_text(encoding='utf-8') if overrides_path.exists() else ''
    overrides = load_overrides(overrides_path)
    metrics = _page_metrics(results)
    rolled_back, graduated = evaluate_experiments(today, state, overrides, metrics)
    audit = technical_audit(dist_dir)

    by_route, _ = _route_catalog_map(dist_dir)
    all_routes = list(by_route.keys())
    existing_titles, existing_descs = collect_existing_meta(dist_dir, all_routes[:120])

    candidates = select_candidates(today, dist_dir, state, overrides, results, metrics)
    proposed, applied, rejected = [], [], []
    kwargs = {'transport': transport} if transport is not None else {}

    for opp in candidates:
        path = opp['path']
        cur_meta = read_route_meta(dist_dir, path) or {'title': '', 'description': '', 'h1': opp.get('product_name', '')}
        other_titles = existing_titles - {cur_meta['title']}
        other_descs = existing_descs - {cur_meta['description']}
        proposal, provider = ai_seo.propose_route_optimization(
            opp, cur_meta, existing_titles=other_titles, existing_descs=other_descs, keys=ai_keys, **kwargs
        )
        if not proposal:
            rejected.append({'path': path, 'reason': provider})
            continue
        existing_titles.add(proposal['title'])
        existing_descs.add(proposal['description'])
        proposed.append({'path': path, 'lang': opp['lang'], 'reason': opp['reason'], 'provider': provider, 'proposal': proposal})
        if apply_changes:
            overrides.setdefault('routes', {})[path] = {
                **proposal,
                'updated': today.isoformat(),
                'reason': opp['reason'],
                'provider': provider,
            }
            applied.append({'path': path, 'lang': opp['lang'], 'reason': opp['reason'], 'provider': provider})

    changed = (overrides.get('routes') != load_overrides(overrides_path).get('routes')) or bool(rolled_back)
    verify_error = None
    if apply_changes and changed:
        save_overrides(overrides, overrides_path)
        try:
            verify_fn()
            # Record active experiments only after full verify_release passed cleanly
            experiments = state.setdefault('experiments', {})
            for item in applied:
                p = item['path']
                m = metrics.get(p, {})
                experiments[p] = {
                    'date': today.isoformat(),
                    'status': 'active',
                    'lang': item['lang'],
                    'reason': item['reason'],
                    'provider': item['provider'],
                    'baseline': {
                        'clicks': m.get('clicks', 0),
                        'impressions': m.get('impressions', 0),
                        'position': m.get('position'),
                    },
                }
        except Exception as exc:
            verify_error = str(exc)[:260]
            if original_raw:
                overrides_path.write_text(original_raw, encoding='utf-8', newline='\n')
            elif overrides_path.exists():
                overrides_path.unlink()
            applied.clear()
            try:
                verify_fn()
            except Exception:
                pass

    return {
        'audit': audit,
        'rolled_back': rolled_back,
        'graduated': graduated,
        'proposed': proposed,
        'applied': applied,
        'rejected': rejected,
        'verify_error': verify_error,
    }
