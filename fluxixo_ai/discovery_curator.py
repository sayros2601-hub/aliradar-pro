"""Rare-gadget discovery, anti-commodity stoplists, pre-search exclusivity, and 6-market verification."""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .policy import DETAIL, MARKETS, QUERY, normalize_product
from .search import HOT, _rows

ALL_MARKETS: tuple[str, ...] = MARKETS  # ('RU', 'US', 'BR', 'MX', 'IL', 'FR')
LANG_TO_MARKET: dict[str, str] = {
    'ru': 'RU',
    'en': 'US',
    'pt': 'BR',
    'es': 'MX',
    'fr': 'FR',
    'he': 'IL',
}

# Commodity household items, replacement parts, and generic clutter buyers already have everywhere.
COMMODITY_STOPLIST: frozenset[str] = frozenset({
    'cable', 'cables', 'charger', 'charging cable', 'usb cable', 'phone case', 'case',
    'cover', 'screen protector', 'tempered glass', 'adapter', 'plug adapter', 'extension cord',
    'earpads', 'watch band', 'strap', 'replacement', 'refill', 'spare', 'part', 'parts',
    'accessory', 'accessories', 'sleeve', 'casing', 'attachment', 'battery', 'batteries',
    'sticker', 'stickers', 'decal', 'decals', 'screw', 'screws', 'bolt', 'bolts', 'nut', 'nuts',
    'washer', 'gasket', 'o-ring', 'oring', 'sponge', 'towel', 'cloth', 'rag', 'hook', 'hooks',
    'keychain', 'keyring', 'pouch', 'bag', 'socks', 'apron', 'notebook', 'ballpoint',
    'lightbulb', 'bulb', 'fuse', 'filter cartridge', 'filter', 'filters', 'brush head', 'refills',
    'shoe lace', 'shoelace', 'hanger', 'hangers', 'toothpaste', 'cotton swab', 'cotton',
})

COMMODITY_PHRASE_RE = re.compile(
    r'\b(?:'
    r'phone\s+case|screen\s+protector|tempered\s+glass|charging\s+cable|usb\s+cable|'
    r'data\s+cable|power\s+cord|watch\s+band|watch\s+strap|ear\s*pads?|'
    r'plug\s+adapter|power\s+adapter|universal\s+adapter|travel\s+adapter|extension\s+cord|power\s+strip|'
    r'replacement\s+(?:part|head|filter|blade|pad|tips?|brush|battery)|'
    r'spare\s+parts?|adhesive\s+hook|wall\s+sticker|cleaning\s+cloth|'
    r'microfiber\s+towel|garbage\s+bag|trash\s+bag|ziplock|hair\s+tie|rubber\s+band'
    r')\b',
    re.IGNORECASE,
)

# High-curiosity, unusual gadgets ("things people do not already own at home") rotating across all 9 worlds & 6 markets.
CURATED_RARE_QUERIES: list[dict[str, Any]] = [
    {'key': 'rare_stirling_stove_fan', 'query': 'heat powered wood stove fan thermal', 'groups': (('stove', 'fireplace'), ('fan',)), 'category': 'Дом', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_endoscope_borescope', 'query': 'articulated usb borescope inspection camera', 'groups': (('borescope', 'endoscope'), ('camera',)), 'category': 'Техника', 'market': 'IL', 'theme': 'blue'},
    {'key': 'rare_ultrasonic_cleaner_pod', 'query': 'ultrasonic jewelry denture retainer cleaner pod', 'groups': (('ultrasonic',), ('cleaner',)), 'category': 'Уход', 'market': 'US', 'theme': 'lavender'},
    {'key': 'rare_gyro_powerball', 'query': 'auto start gyroscopic wrist ball exerciser', 'groups': (('gyro', 'gyroscopic', 'wrist'), ('ball',)), 'category': 'Спорт', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_gravity_spice_mill', 'query': 'gravity induction electric pepper grinder', 'groups': (('gravity',), ('grinder', 'mill')), 'category': 'Кухня', 'market': 'BR', 'theme': 'sand'},
    {'key': 'rare_obd_windshield_hud', 'query': 'car obd2 windshield head up display hud', 'groups': (('hud', 'head up'), ('car', 'obd', 'windshield')), 'category': 'В дороге', 'market': 'MX', 'theme': 'rose'},
    {'key': 'rare_contour_profile_gauge', 'query': 'locking contour profile duplicator gauge tool', 'groups': (('contour', 'profile'), ('gauge',)), 'category': 'Инструменты', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_plasma_arc_lighter', 'query': 'waterproof dual arc plasma lighter usb outdoor', 'groups': (('plasma', 'arc'), ('lighter',)), 'category': 'На природе', 'market': 'US', 'theme': 'blue'},
    {'key': 'rare_auto_rolling_pet_ball', 'query': 'smart automatic rolling interactive cat dog ball', 'groups': (('automatic', 'smart', 'interactive'), ('ball',)), 'category': 'Питомцы', 'market': 'IL', 'theme': 'lavender'},
    {'key': 'rare_laser_level_inclinometer', 'query': 'digital magnetic inclinometer angle cube gauge', 'groups': (('angle', 'inclinometer'), ('digital', 'gauge')), 'category': 'Инструменты', 'market': 'FR', 'theme': 'sand'},
    {'key': 'rare_vacuum_wine_preserver', 'query': 'electric vacuum wine bottle stopper preserver', 'groups': (('vacuum',), ('wine',)), 'category': 'Кухня', 'market': 'MX', 'theme': 'rose'},
    {'key': 'rare_uv_toothbrush_pod', 'query': 'portable uv toothbrush sanitizer travel case', 'groups': (('uv', 'uvc'), ('toothbrush',)), 'category': 'Уход', 'market': 'BR', 'theme': 'lavender'},
    {'key': 'rare_solar_crank_beacon', 'query': 'hand crank solar emergency weather radio lantern', 'groups': (('crank', 'solar'), ('radio', 'lantern')), 'category': 'На природе', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_pixel_desk_clock', 'query': 'smart pixel art desk clock ambient weather display', 'groups': (('pixel',), ('clock', 'display')), 'category': 'Техника', 'market': 'US', 'theme': 'blue'},
    {'key': 'rare_rapid_defrost_tray', 'query': 'conductive aluminum rapid meat defrosting tray', 'groups': (('defrost', 'thaw'), ('tray', 'plate')), 'category': 'Кухня', 'market': 'IL', 'theme': 'sand'},
    {'key': 'rare_turbine_air_duster', 'query': 'jet dry compressed air blower turbo duster fan', 'groups': (('turbo', 'jet'), ('duster', 'blower')), 'category': 'Техника', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_magnetic_vortex_mug', 'query': 'automatic magnetic self stirring insulated coffee mug', 'groups': (('magnetic', 'self stirring'), ('mug', 'cup')), 'category': 'Кухня', 'market': 'US', 'theme': 'rose'},
    {'key': 'rare_folding_camping_shower', 'query': 'rechargeable portable outdoor electric camping shower', 'groups': (('portable', 'electric'), ('shower',)), 'category': 'На природе', 'market': 'BR', 'theme': 'blue'},
    {'key': 'rare_tennis_ball_pressurizer', 'query': 'tennis padel ball pressurizer saver canister', 'groups': (('pressurizer', 'pressure'), ('tennis', 'padel')), 'category': 'Спорт', 'market': 'MX', 'theme': 'sand'},
    {'key': 'rare_digital_spoon_scale', 'query': 'digital gram measuring spoon lcd scale coffee', 'groups': (('spoon',), ('scale',)), 'category': 'Кухня', 'market': 'RU', 'theme': 'coral'},
    {'key': 'rare_mini_thermal_printer', 'query': 'pocket inkless thermal bluetooth note printer', 'groups': (('thermal',), ('printer',)), 'category': 'Техника', 'market': 'BR', 'theme': 'lavender'},
    {'key': 'rare_timed_lock_vault', 'query': 'timer lock box container phone habit vault', 'groups': (('timer', 'time'), ('lock', 'box')), 'category': 'Дом', 'market': 'IL', 'theme': 'rose'},
    {'key': 'rare_bike_laser_lane_light', 'query': 'bicycle rear taillight laser lane safety signal', 'groups': (('laser',), ('bicycle', 'bike', 'taillight')), 'category': 'Спорт', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_pet_grooming_vacuum', 'query': 'low noise pet nail grinder clipper led light', 'groups': (('nail', 'claw'), ('grinder',)), 'category': 'Питомцы', 'market': 'US', 'theme': 'sand'},
    {'key': 'rare_usb_voltage_analyzer', 'query': 'usb c digital power meter tester ammeter screen', 'groups': (('usb', 'type c'), ('tester', 'meter')), 'category': 'Техника', 'market': 'RU', 'theme': 'blue'},
    {'key': 'rare_auto_soap_foamer', 'query': 'touchless automatic infrared foaming soap dispenser', 'groups': (('touchless', 'automatic', 'sensor'), ('dispenser',)), 'category': 'Дом', 'market': 'MX', 'theme': 'coral'},
    {'key': 'rare_portable_tire_compressor', 'query': 'cordless digital air compressor car tire inflator', 'groups': (('inflator', 'compressor'), ('tire',)), 'category': 'В дороге', 'market': 'IL', 'theme': 'blue'},
    {'key': 'rare_infrared_pizza_thermometer', 'query': 'non contact infrared laser surface thermometer gun', 'groups': (('infrared',), ('thermometer',)), 'category': 'Кухня', 'market': 'FR', 'theme': 'sand'},
    {'key': 'rare_survival_filter_straw', 'query': 'personal hollow fiber emergency water filter straw', 'groups': (('water',), ('filter', 'straw')), 'category': 'На природе', 'market': 'MX', 'theme': 'coral'},
    {'key': 'rare_cordless_precision_driver', 'query': 'electric precision micro screwdriver magnetic bit set', 'groups': (('electric',), ('screwdriver',)), 'category': 'Инструменты', 'market': 'US', 'theme': 'lavender'},
    {'key': 'rare_hydroponic_herb_pod', 'query': 'smart indoor desktop hydroponic grow garden led', 'groups': (('hydroponic',), ('garden', 'grow')), 'category': 'Дом', 'market': 'FR', 'theme': 'blue'},
    {'key': 'rare_sonic_brush_spinner', 'query': 'electric makeup brush cleaner spinner dryer', 'groups': (('makeup', 'brush'), ('cleaner', 'spinner')), 'category': 'Уход', 'market': 'RU', 'theme': 'rose'},
    {'key': 'rare_car_gap_caddy', 'query': 'car seat gap console organizer pocket usb', 'groups': (('gap',), ('seat', 'car', 'organizer')), 'category': 'В дороге', 'market': 'BR', 'theme': 'sand'},
    {'key': 'rare_visual_ear_otoscope', 'query': 'wifi visual ear cleaner camera led otoscope', 'groups': (('camera', 'visual', 'otoscope'), ('ear',)), 'category': 'Уход', 'market': 'IL', 'theme': 'lavender'},
    {'key': 'rare_cordless_electric_scissors', 'query': 'rechargeable electric rotary fabric cardboard scissors', 'groups': (('electric', 'cordless'), ('scissors', 'cutter')), 'category': 'Инструменты', 'market': 'BR', 'theme': 'coral'},
    {'key': 'rare_leakproof_dog_flask', 'query': 'portable dog water bottle dispenser outdoor cup', 'groups': (('dog', 'pet'), ('bottle', 'water')), 'category': 'Питомцы', 'market': 'MX', 'theme': 'blue'},
]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r'[a-z0-9а-яё]+', (text or '').casefold()))


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Normalized token overlap between two product titles or descriptions."""
    a = _tokens(text_a)
    b = _tokens(text_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_ordinary_or_banned_listing(title: str) -> tuple[bool, str | None]:
    """Reject everyday commodity basics, parts, cables, covers, and generic refill items."""
    clean = (title or '').strip()
    if len(clean) < 10:
        return True, 'title_too_short'
    if COMMODITY_PHRASE_RE.search(clean):
        return True, 'commodity_phrase'
    words = set(re.findall(r'[a-z0-9]+', clean.casefold()))
    # Single utility words like "replacement", "refill", "spare", "cable" disqualify non-complete items.
    strict_single_ban = {
        'replacement', 'refill', 'refills', 'spare', 'part', 'parts', 'accessory',
        'accessories', 'sticker', 'stickers', 'decal', 'decals', 'casing', 'sleeve',
        'earpads', 'shoelace', 'gasket', 'oring', 'o-ring', 'keychain', 'keyring',
        'socks', 'toothpaste', 'hanger', 'hangers', 'sponge', 'sponges', 'towel',
        'towels', 'rag', 'rags', 'ballpoint', 'notebook', 'apron', 'lightbulb',
    }
    hit = words & strict_single_ban
    if hit:
        return True, f'banned_token:{sorted(hit)[0]}'
    # Catch commodity cable/case/adapter listings unless paired with specialty diagnostic/novelty hardware.
    diagnostic_whitelist = {
        'borescope', 'endoscope', 'tester', 'analyzer', 'otoscope', 'scanner',
        'thermal', 'laser', 'ultrasonic', 'gyroscopic', 'stirling', 'sanitizer',
        'uv', 'uvc', 'inclinometer', 'microscope', 'oscilloscope', 'soldering',
        'telemetry', 'hud',
    }
    if {'cable', 'charger', 'adapter', 'case', 'cover'} & words and not (words & diagnostic_whitelist):
        return True, 'everyday_commodity_accessory'
    return False, None


def compatible_markets_for_title(title: str, candidate_markets: tuple[str, ...] | list[str] = ALL_MARKETS) -> list[str]:
    """Filter out countries whose mains voltage/plug standard conflicts with an explicit single-voltage title."""
    text = (title or '').casefold()
    markets = [m for m in candidate_markets if m in ALL_MARKETS]

    has_110 = bool(re.search(r'\b110\s*v\b|\b120\s*v\b|\bus\s+plug\b', text))
    has_220 = bool(re.search(r'\b220\s*v\b|\b230\s*v\b|\b240\s*v\b|\beu\s+plug\b', text))
    is_dual_voltage = any(tok in text for tok in (
        'bivolt', '100-240v', '100~240v', '110-240v', '110v-240v', '110-220v', '110v/220v',
    )) or (has_110 and has_220)

    if is_dual_voltage or (not has_110 and not has_220):
        return markets
    if has_110 and not has_220:
        # 110V-only mains device -> unsafe for 220V regions (RU, IL, FR) and mixed-grid BR.
        return [m for m in markets if m in ('US', 'MX')]
    if has_220 and not has_110:
        # 220V-only mains device -> unsuitable for 110-127V regions (US, MX) and 127V states in BR.
        return [m for m in markets if m in ('RU', 'IL', 'FR')]
    return markets


def parse_evaluate_rate(raw_val: Any) -> float | None:
    if raw_val is None:
        return None
    if isinstance(raw_val, (int, float)):
        return float(raw_val)
    match = re.search(r'(\d+(?:[.,]\d+)?)', str(raw_val))
    if not match:
        return None
    return float(match.group(1).replace(',', '.'))


def parse_volume(raw_val: Any) -> int | None:
    if raw_val is None or isinstance(raw_val, bool):
        return None
    if isinstance(raw_val, (int, float)):
        return int(raw_val)
    digits = re.sub(r'[^\d]', '', str(raw_val))
    return int(digits) if digits else None


def seller_quality_check(raw: dict[str, Any]) -> tuple[bool, str, float]:
    """Evaluate seller reliability & non-commodity niche sweet-spot without inventing missing metrics."""
    rate = parse_evaluate_rate(
        raw.get('evaluate_rate')
        or (raw.get('seller_metrics', {}) or {}).get('evaluate_rate', {}).get('raw_value')
    )
    volume = parse_volume(
        raw.get('lastest_volume')
        or (raw.get('seller_metrics', {}) or {}).get('lastest_volume', {}).get('raw_value')
    )
    if rate is not None and rate < 88.0:
        return False, f'low_seller_rating:{rate}', -100.0
    bonus = 0.0
    if rate is not None:
        bonus += min(10.0, max(0.0, (rate - 88.0) * 0.8))
    if volume is not None:
        if volume > 30000:
            return False, f'mass_commodity_volume:{volume}', -50.0
        if 15 <= volume <= 3500:
            bonus += 6.0
        elif volume == 0:
            bonus -= 2.0
    return True, 'ok', bonus


def matches_rare_query(task: dict[str, Any], title: str) -> bool:
    banned, _ = is_ordinary_or_banned_listing(title)
    if banned:
        return False
    words = set(re.findall(r'[a-z0-9]+', (title or '').casefold()))
    return all(
        any(all(w in words for w in group_term.split()) for group_term in group)
        for group in task['groups']
    )


def select_rotating_queries(now_ordinal: int, target_markets: tuple[str, ...] = ALL_MARKETS, pool: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Order curated queries so each run balances categories and rotates across target countries."""
    items = list(pool if pool is not None else CURATED_RARE_QUERIES)
    if not items:
        return []
    offset = now_ordinal % len(items)
    rotated = items[offset:] + items[:offset]
    # Interleave different categories & markets rather than clustered blocks.
    buckets: dict[str, list[dict[str, Any]]] = {}
    for entry in rotated:
        mkt = entry.get('market', 'US')
        if mkt in target_markets:
            buckets.setdefault(mkt, []).append(entry)
    ordered: list[dict[str, Any]] = []
    market_cycle = list(target_markets[now_ordinal % len(target_markets):] + target_markets[:now_ordinal % len(target_markets)])
    while any(buckets.values()):
        for m in market_cycle:
            lst = buckets.get(m)
            if lst:
                ordered.append(lst.pop(0))
    return ordered


def fetch_hot_background_ids(call: Callable[[str, dict[str, str]], dict], query: str, market: str) -> tuple[set[str], list[str]]:
    """Pre-search check against AliExpress hot-products list to spot saturated commodity clones."""
    try:
        rows = _rows(
            call(
                HOT,
                {
                    'keywords': query.strip(),
                    'ship_to_country': market,
                    'target_currency': 'USD',
                    'target_language': 'EN',
                    'page_size': '20',
                    'tracking_id': 'default',
                },
            ),
            HOT,
        )
    except Exception:
        return set(), []
    hot_ids: set[str] = set()
    hot_titles: list[str] = []
    for r in rows[:20]:
        if isinstance(r, dict) and r.get('product_id'):
            hot_ids.add(str(r['product_id']))
            if r.get('product_title'):
                hot_titles.append(str(r['product_title']))
    return hot_ids, hot_titles


def default_web_presearch(query_title: str, *, timeout: float = 4.0) -> dict[str, Any]:
    """Optional lightweight web pre-search for market saturation check (non-blocking offline fallback)."""
    # Query DuckDuckGo Instant Answer JSON (public, zero-key) to verify if title matches common retail commodities.
    q = ' '.join(re.findall(r'[A-Za-z0-9]+', query_title)[:6])
    if not q:
        return {'checked': False, 'status': 'empty_query', 'saturated': False}
    url = 'https://api.duckduckgo.com/?q=' + urllib.parse.quote_plus(q) + '&format=json&no_redirect=1&no_html=1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'fluxixo-presearch/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read(200_000).decode('utf-8', 'replace')
        import json
        data = json.loads(payload)
        heading = str(data.get('Heading') or '')
        abstract = str(data.get('AbstractText') or '')
        # Note: a generic Wikipedia entry directly matching an everyday staple indicates mundane commodity rather than novel gadget.
        generic_signals = ('basic tool', 'everyday object', 'common household', 'stationery')
        saturated = any(sig in abstract.casefold() for sig in generic_signals)
        return {'checked': True, 'status': 'ok', 'heading': heading[:80], 'saturated': saturated}
    except Exception as exc:
        return {'checked': False, 'status': f'unavailable:{type(exc).__name__}', 'saturated': False}


def presearch_exclusivity_check(
    candidate: dict[str, Any],
    existing_items: list[dict[str, Any]],
    *,
    hot_ids: set[str] | None = None,
    hot_titles: list[str] | None = None,
    presearch_fn: Callable[[str], dict[str, Any]] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Run pre-publication uniqueness and non-commodity screening before downloading media."""
    title = str(candidate.get('title') or candidate.get('product_title') or '').strip()
    pid = str(candidate.get('product_id') or '')

    banned, ban_reason = is_ordinary_or_banned_listing(title)
    if banned:
        return False, f'rejected:{ban_reason}', {'stage': 'stoplist', 'reason': ban_reason}

    q_ok, q_reason, q_bonus = seller_quality_check(candidate)
    if not q_ok:
        return False, f'rejected:{q_reason}', {'stage': 'seller_quality', 'reason': q_reason}

    # Check semantic overlap against existing published catalog so we avoid clones of similar gadgets.
    for existing in existing_items:
        if not isinstance(existing, dict):
            continue
        for field in ('sourceTitle', 'name'):
            other = str(existing.get(field) or '').strip()
            if not other:
                continue
            sim = jaccard_similarity(title, other)
            if sim >= 0.58:
                return False, f'rejected:catalog_concept_duplicate:{existing.get("id", "")}', {
                    'stage': 'catalog_overlap',
                    'similarity': round(sim, 3),
                    'matched_id': existing.get('id', ''),
                }

    # Check AliExpress Hot Product flood: exact ID inside top commodity spam OR >=3 clones.
    hot_penalty = 0.0
    if hot_ids and pid in hot_ids:
        hot_penalty -= 8.0
    clone_hits = sum(1 for ht in (hot_titles or ()) if jaccard_similarity(title, ht) >= 0.60)
    if clone_hits >= 3:
        return False, 'rejected:hotproduct_commodity_saturation', {
            'stage': 'hot_saturation',
            'clone_hits': clone_hits,
        }

    presearch_info: dict[str, Any] = {'checked': False, 'status': 'not_run', 'saturated': False}
    if presearch_fn is not None:
        try:
            res = presearch_fn(title)
            if isinstance(res, dict):
                presearch_info = res
                if res.get('saturated'):
                    return False, 'rejected:web_presearch_ordinary', {'stage': 'web_presearch', **res}
        except Exception as exc:
            presearch_info = {'checked': False, 'status': f'error:{type(exc).__name__}', 'saturated': False}

    score = 10.0 + q_bonus + hot_penalty - (clone_hits * 1.5)
    return True, 'passed', {'score': round(score, 2), 'presearch': presearch_info}


def verify_markets_for_candidate(
    call: Callable[[str, dict[str, str]], dict],
    candidate: dict[str, Any],
    markets_to_check: tuple[str, ...] | list[str],
    utc_iso: str,
) -> dict[str, Any]:
    """Query AliExpress productdetail.get per market and enforce regional voltage/plug compatibility."""
    pid = str(candidate['product_id'])
    title = str(candidate.get('title') or '')
    primary_market = candidate.get('source', {}).get('queried_market') or candidate.get('market')
    voltage_ok = set(compatible_markets_for_title(title, tuple(markets_to_check)))

    confirmed: list[str] = []
    market_states = dict(candidate.get('markets') or {})
    if primary_market and market_states.get(primary_market, {}).get('sellable') == 'confirmed':
        if primary_market in voltage_ok:
            confirmed.append(primary_market)

    for market in markets_to_check:
        if market not in ALL_MARKETS:
            continue
        if market == primary_market and market in market_states:
            continue
        try:
            rows = _rows(
                call(
                    DETAIL,
                    {
                        'product_ids': pid,
                        'country': market,
                        'target_currency': 'USD',
                        'target_language': 'EN',
                        'tracking_id': 'default',
                    },
                ),
                DETAIL,
            )
            matched = [r for r in rows[:20] if isinstance(r, dict) and str(r.get('product_id')) == pid]
            if matched:
                norm = normalize_product(matched[0], market, DETAIL, utc_iso)
                market_states[market] = norm['markets'][market]
                if market in voltage_ok and market not in confirmed:
                    confirmed.append(market)
        except Exception:
            continue

    # Preserve canonical order from ALL_MARKETS.
    ordered_confirmed = [m for m in ALL_MARKETS if m in confirmed]
    candidate['markets'] = market_states
    candidate['availableMarkets'] = ordered_confirmed
    return candidate


def generate_ai_discovery_queries(
    existing_items: list[dict[str, Any]],
    *,
    target_markets: tuple[str, ...] = ALL_MARKETS,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Optionally brainstorm fresh rare-gadget searches via configured free AI keys."""
    try:
        from fluxixo_site.tools import ai_seo
    except Exception:
        return []
    keys = ai_seo.load_ai_keys(local=False)
    if not ai_seo.has_ai_provider(keys):
        return []

    sample_names = [str(p.get('name', '')) for p in existing_items[:25] if isinstance(p, dict)]
    sys_prompt = (
        'You curate unusual, genuinely clever non-everyday physical gadgets from AliExpress '
        'that people do NOT already own at home (kinetic/physics items, optical borescopes, '
        'ultrasonic cleaners, clever compact tools). Avoid common commodity cables, phone cases, '
        'stickers, screws, or spare parts. Reply strictly with JSON: '
        '{"queries":[{"query":"english 4-6 word query","keyword_required":"single core word","category":"Техника|Дом|Кухня|В дороге|Инструменты|Уход|Спорт|На природе|Питомцы"}]}'
    )
    user_prompt = f'Avoid topics already in catalog: {sample_names[:18]}. Propose {limit} distinct ideas.'
    raw_obj = None
    for caller_key, env_name in ((ai_seo._call_gemini, 'GEMINI_API_KEY'), (ai_seo._call_groq, 'GROQ_API_KEY'), (ai_seo._call_openrouter, 'OPENROUTER_API_KEY')):
        if not keys.get(env_name):
            continue
        try:
            raw_obj, _ = caller_key(keys[env_name], sys_prompt, user_prompt)
            break
        except Exception:
            continue
    if not isinstance(raw_obj, dict) or not isinstance(raw_obj.get('queries'), list):
        return []

    categories = {'Техника', 'Дом', 'Кухня', 'В дороге', 'Инструменты', 'Уход', 'Спорт', 'На природе', 'Питомцы'}
    themes = ('blue', 'coral', 'sand', 'lavender', 'rose')
    out: list[dict[str, Any]] = []
    for idx, q in enumerate(raw_obj['queries'][:limit]):
        if not isinstance(q, dict):
            continue
        text = str(q.get('query') or '').strip()
        req = re.sub(r'[^a-z0-9]', '', str(q.get('keyword_required') or '').casefold())
        cat = str(q.get('category') or 'Техника').strip()
        if not text or len(req) < 3 or cat not in categories:
            continue
        banned, _ = is_ordinary_or_banned_listing(text)
        if banned:
            continue
        out.append({
            'key': 'ai_rare_' + req,
            'query': text[:100],
            'groups': ((req,),),
            'category': cat,
            'market': target_markets[idx % len(target_markets)],
            'theme': themes[idx % len(themes)],
        })
    return out


def pre_deploy_catalog_gate(
    prepared_items: list[dict[str, Any]],
    existing_catalog: list[dict[str, Any]],
    *,
    require_markets: bool = True,
) -> tuple[bool, list[str]]:
    """Final strict pre-publication audit before any newly prepared item can be committed/deployed."""
    errors: list[str] = []
    seen_ids = {str(p.get('id') or '') for p in existing_catalog if isinstance(p, dict)}
    seen_source_ids = {str(p.get('sourceProductId') or '') for p in existing_catalog if isinstance(p, dict) and p.get('sourceProductId')}

    for item in prepared_items:
        pid = str(item.get('id') or '')
        spid = str(item.get('sourceProductId') or '')
        src_title = str(item.get('sourceTitle') or item.get('name') or '')
        if not pid or pid in seen_ids:
            errors.append(f'{pid}:duplicate_catalog_id')
        if spid and spid in seen_source_ids:
            errors.append(f'{pid}:duplicate_source_product_id')
        seen_ids.add(pid)
        if spid:
            seen_source_ids.add(spid)

        banned, reason = is_ordinary_or_banned_listing(src_title)
        if banned:
            errors.append(f'{pid}:ordinary_or_banned:{reason}')

        avail = item.get('availableMarkets')
        if require_markets:
            if not isinstance(avail, list) or not avail or any(m not in ALL_MARKETS for m in avail):
                errors.append(f'{pid}:missing_verified_availableMarkets')
            else:
                compat = set(compatible_markets_for_title(src_title, tuple(avail)))
                if not compat or set(avail) - compat:
                    errors.append(f'{pid}:voltage_incompatible_market')

        if item.get('imageQualityVerified') is False:
            errors.append(f'{pid}:image_quality_not_verified')

    return not errors, errors
