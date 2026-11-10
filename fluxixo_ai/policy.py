"""Deterministic, evidence-limited selection rules for AliExpress API results.

Only the trusted API adapter may call ``normalize_product``: the country, method
and raw record are assertions about an actual successful API response and must
never come from the MCP caller or model. This module validates their structure,
not the authenticity of their transport. No network access is performed here.
"""
from __future__ import annotations

import copy
from datetime import datetime
import math
import re
from urllib.parse import urlsplit

MARKETS = ('US', 'BR', 'MX', 'IL', 'FR')
QUERY = 'aliexpress.affiliate.product.query'
DETAIL = 'aliexpress.affiliate.productdetail.get'
_DETAIL_HOSTS = {'aliexpress.com', 'www.aliexpress.com', 'm.aliexpress.com'}

def image_host_allowed(host: str) -> bool:
    # aliexpress-media.com was observed in authenticated product-query results;
    # retain an exact domain boundary rather than accepting arbitrary URLs.
    return any(host==base or host.endswith('.'+base) for base in ('alicdn.com','aliexpress-media.com'))
_GENERIC = {
    'general', 'generic', 'everyday', 'everyday use', 'daily use', 'for daily use',
    'for everyday use', 'home', 'kitchen', 'travel', 'accessories', 'convenience',
    'useful', 'convenient', 'all purposes', 'phone', 'products',
    'для дома', 'для кухни', 'для дороги', 'дом', 'кухня', 'в дороге',
    'повседневное использование', 'для повседневного использования',
    'удобство', 'удобно', 'полезно', 'для всех', 'товары', 'аксессуары',
    'uso diario', 'uso cotidiano', 'uso diário', 'conveniente', 'maison',
    'usage quotidien', 'pratique', 'שימוש יומיומי', 'נוחות',
}


def _text(value: object, field: str, *, required: bool = False, limit: int = 4000) -> str | None:
    if value is None or value == '':
        if required:
            raise ValueError(f'{field} is required')
        return None
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError(f'Invalid {field}')
    value = value.strip()
    if not value:
        if required:
            raise ValueError(f'{field} is required')
        return None
    return value


def _url(value: object, field: str, host_allowed) -> str | None:
    value = _text(value, field, limit=4096)
    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or not host_allowed(parsed.hostname.lower())
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or '\\' in value or parsed.fragment):
            raise ValueError()
    except ValueError:
        raise ValueError(f'Invalid {field}') from None
    return value


def _id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Invalid product_id')
    value = str(value)
    if len(value) > 32 or not re.fullmatch(r'[1-9][0-9]*', value):
        raise ValueError('Invalid product_id')
    return value


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError('Invalid observed_at')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Invalid observed_at') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('observed_at must include timezone')
    return value


def _model_key(brand: str | None, model: str | None) -> str | None:
    # A model alone is not globally unique. Never infer either value from title.
    if not brand or not model:
        return None
    return ' '.join(brand.casefold().split()) + '\x1f' + ' '.join(model.casefold().split())


def _metric(value: object, field: str) -> dict:
    # Preserve the response value without converting percentages, dates or units.
    if isinstance(value, bool) or not isinstance(value, (str, int, float, type(None))):
        raise ValueError(f'Invalid {field}')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f'Invalid {field}')
    if isinstance(value, str) and (len(value) > 256 or any(ord(c) < 32 for c in value)):
        raise ValueError(f'Invalid {field}')
    return {'raw_value': value, 'scope': 'unknown', 'period': 'unknown', 'interpreted': False}


def normalize_product(raw: dict, market: str, method: str, timestamp: str) -> dict:
    """Normalize one *returned* product, without interpreting missing fields as facts.

    Detail confirmation is scoped to ``country`` in the successful detail API
    request. The adapter must ensure that the row was in that response, had the
    requested ID, and the request actually included ``country=market``. It is
    not proof of stock, delivery, SKU availability, current prices or quality.
    """
    if not isinstance(raw, dict) or market not in MARKETS or method not in (QUERY, DETAIL):
        raise ValueError('Invalid API source or market')
    observed_at = _timestamp(timestamp)
    product_id = _id(raw.get('product_id'))
    title = _text(raw.get('product_title'), 'product_title', required=True, limit=2000)
    detail = _url(raw.get('product_detail_url'), 'product_detail_url', lambda host: host in _DETAIL_HOSTS)
    if detail is None or re.fullmatch(r'/item/([1-9][0-9]*)\.html', urlsplit(detail).path) is None:
        raise ValueError('Invalid product_detail_url')
    if urlsplit(detail).path != f'/item/{product_id}.html':
        raise ValueError('Product ID does not match detail URL')
    canonical_detail = f'https://www.aliexpress.com/item/{product_id}.html'
    image = _url(raw.get('product_main_image_url'), 'product_main_image_url',
                 image_host_allowed)
    raw_promotion = _text(raw.get('promotion_link'), 'promotion_link', limit=4096)
    promotion_status = 'not_provided'
    promotion = None
    if raw_promotion:
        try:
            parsed_promotion = urlsplit(raw_promotion)
            if (parsed_promotion.scheme == 'http' and parsed_promotion.hostname == 's.click.aliexpress.com'
                    and parsed_promotion.username is None and parsed_promotion.password is None
                    and parsed_promotion.port in (None, 80) and not parsed_promotion.fragment and '\\' not in raw_promotion):
                # Do not expose or silently rewrite an insecure API example. A fresh,
                # HTTPS link must be obtained through link.generate before publication.
                promotion_status = 'discarded_insecure'
            else:
                promotion = _url(raw_promotion, 'promotion_link', lambda host: host == 's.click.aliexpress.com')
                promotion_status = 'provided_https'
        except ValueError:
            raise ValueError('Invalid promotion_link') from None
    brand = _text(raw.get('brand'), 'brand', limit=200)
    model = _text(raw.get('model'), 'model', limit=200)
    metrics = {key: _metric(raw.get(key), key) for key in ('lastest_volume', 'evaluate_rate')}
    metric_observation = {'market': market, 'market_is_scope': False, 'method': method,
                          'observed_at': observed_at, 'metrics': copy.deepcopy(metrics)}
    markets = {m: {'sellable': 'unknown', 'shipping': 'unknown', 'ads': 'unknown', 'rarity': 'unknown'} for m in MARKETS}
    if method == DETAIL:
        markets[market]['sellable'] = 'confirmed'
        markets[market]['sellability_evidence'] = {'method': method, 'country': market,
                                                    'product_id': product_id, 'observed_at': observed_at}
    return {
        'product_id': product_id, 'title': title, 'detail_url': canonical_detail,
        'source_detail_url': detail, 'image_url': image, 'promotion_link': promotion, 'promotion_link_status': promotion_status,
        'brand': brand, 'model': model, 'model_key': _model_key(brand, model),
        'source': {'method': method, 'queried_market': market, 'observed_at': observed_at},
        'markets': markets, 'seller_metrics': metrics, 'seller_metric_observations': [metric_observation],
    }


def merge_observations(observations: list[dict]) -> dict:
    """Combine independently normalized observations of the same exact item."""
    if not isinstance(observations, list) or not observations:
        raise ValueError('No observations')
    merged = copy.deepcopy(observations[0])
    if not isinstance(merged, dict) or not merged.get('product_id'):
        raise ValueError('Invalid observation')
    for current in observations[1:]:
        if not isinstance(current, dict) or current.get('product_id') != merged['product_id']:
            raise ValueError('Cannot merge different products')
        if current.get('detail_url') != merged.get('detail_url'):
            raise ValueError('Inconsistent product identity')
        for observation in current.get('seller_metric_observations', []):
            if observation not in merged['seller_metric_observations']:
                merged['seller_metric_observations'].append(copy.deepcopy(observation))
        for market in MARKETS:
            state = current.get('markets', {}).get(market, {})
            if state.get('sellable') == 'confirmed':
                # A later query-only observation cannot erase an earlier detail result.
                merged['markets'][market] = copy.deepcopy(state)
    return merged


def _specific(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        return False
    folded = ' '.join(value.casefold().strip(' \t\r\n.,:;!?-—').split())
    return bool(folded and folded not in _GENERIC)


def _valid_candidate(candidate: dict) -> bool:
    """Recheck structure and cross-field consistency, not API authenticity."""
    try:
        source = candidate['source']
        metrics = candidate['seller_metrics']
        reconstructed = normalize_product({
            'product_id': candidate['product_id'], 'product_title': candidate['title'],
            'product_detail_url': candidate['source_detail_url'],
            'product_main_image_url': candidate.get('image_url'),
            'promotion_link': candidate.get('promotion_link'),
            'brand': candidate.get('brand'), 'model': candidate.get('model'),
            'lastest_volume': metrics['lastest_volume']['raw_value'],
            'evaluate_rate': metrics['evaluate_rate']['raw_value'],
        }, source['queried_market'], source['method'], source['observed_at'])
        if any(candidate.get(key) != reconstructed[key]
               for key in ('product_id', 'title', 'detail_url', 'source_detail_url', 'image_url',
                           'promotion_link', 'brand', 'model', 'model_key', 'seller_metrics')):
            return False
        observations = candidate['seller_metric_observations']
        if not isinstance(observations, list) or not observations or reconstructed['seller_metric_observations'][0] not in observations:
            return False
        for observation in observations:
            if (not isinstance(observation, dict) or observation.get('market') not in MARKETS
                    or observation.get('market_is_scope') is not False or observation.get('method') not in (QUERY, DETAIL)):
                return False
            _timestamp(observation['observed_at'])
            observed = observation['metrics']
            if (not isinstance(observed, dict) or set(observed) != {'lastest_volume', 'evaluate_rate'}
                    or any(observed[key] != _metric(observed[key]['raw_value'], key) for key in observed)):
                return False
        markets = candidate['markets']
        if not isinstance(markets, dict) or set(markets) != set(MARKETS):
            return False
        for market in MARKETS:
            state = markets[market]
            if not isinstance(state, dict) or state.get('sellable') not in ('confirmed', 'unknown'):
                return False
            if any(state.get(key) != 'unknown' for key in ('shipping', 'ads', 'rarity')):
                return False
            if state['sellable'] == 'confirmed':
                proof = state['sellability_evidence']
                if (not isinstance(proof, dict) or proof.get('method') != DETAIL
                        or proof.get('country') != market or proof.get('product_id') != candidate['product_id']):
                    return False
                _timestamp(proof['observed_at'])
        return True
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_candidate(candidate: dict, selection: dict, history_ids=(), history_models=()) -> dict:
    """Return a transparent gate, never a speculative demand/rarity score.

    ``selection`` is agent reasoning, not an assertion of verified seller facts.
    Evidence quotes are checked for exact occurrence, not semantic entailment.
    Its prose must not be copied into product facts as if it were source data.
    ``history_ids`` and ``history_models`` only cover identities actually known.
    """
    reasons = []
    if not isinstance(candidate, dict) or not isinstance(selection, dict):
        return {'eligible': False, 'reasons': ['MALFORMED_CANDIDATE'],
                'unknown_facts': ['shipping', 'ads', 'rarity'],
                'historical_identity_coverage': 'unknown',
                'grounding': {'quote_match': 'not_checked', 'semantic_entailment': 'not_checked'}}
    if not _valid_candidate(candidate):
        reasons.append('INVALID_SOURCE_EVIDENCE')
    if not _specific(selection.get('problem')):
        reasons.append('PROBLEM_NOT_SPECIFIC')
    if not _specific(selection.get('use')):
        reasons.append('USE_NOT_SPECIFIC')
    if not _specific(selection.get('rationale')):
        reasons.append('RATIONALE_MISSING_OR_GENERIC')
    evidence = selection.get('evidence')
    quotes_valid = isinstance(evidence, list) and bool(evidence) and len(evidence) <= 20
    if quotes_valid:
        for item in evidence:
            if (not isinstance(item, dict) or item.get('field') != 'title'
                    or not isinstance(item.get('quote'), str) or not item['quote'].strip()
                    or item['quote'].strip().casefold() not in str(candidate.get('title', '')).casefold()):
                quotes_valid = False
                break
    if not quotes_valid:
        reasons.append('MISSING_OR_UNSUPPORTED_EVIDENCE')
    market_states = candidate.get('markets', {})
    confirmed = [m for m in MARKETS if isinstance(market_states.get(m), dict)
                 and market_states[m].get('sellable') == 'confirmed'] if isinstance(market_states, dict) else []
    if not confirmed:
        reasons.append('NO_CONFIRMED_MARKET')
    if candidate.get('product_id') in (history_ids or ()):
        reasons.append('DUPLICATE_ITEM')
    model_key = candidate.get('model_key')
    if model_key and model_key in (history_models or ()):
        reasons.append('DUPLICATE_MODEL')
    return {
        'eligible': not reasons, 'reasons': reasons, 'confirmed_markets': confirmed,
        'unknown_facts': ['shipping', 'ads', 'rarity', 'sku_stock', 'listing_accuracy',
                          'seller_metric_scope', 'seller_metric_period'],
        'historical_identity_coverage': 'unknown',
        'model_equivalence': 'inferred_from_explicit_brand_model' if model_key else 'unknown',
        'grounding': {'quote_match': 'confirmed' if quotes_valid else 'not_confirmed',
                      'semantic_entailment': 'not_checked'},
    }


def deduplicate_candidates(candidates: list[dict]) -> dict:
    """Keep the first item ID, or an explicit identical brand+model pair.

    A same-brand/model grouping is an inference, not proof that listings or
    variants are identical. Missing brand/model never causes a model merge.
    """
    if not isinstance(candidates, list):
        raise ValueError('Candidates must be a list')
    unique, duplicates = [], []
    ids, models = {}, {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError('Invalid candidate')
        item_id = _id(candidate.get('product_id'))
        key = candidate.get('model_key')
        if item_id in ids:
            duplicates.append({'product_id': item_id, 'duplicate_of': ids[item_id],
                               'reason': 'same_product_id', 'inferred_equivalence': False})
        elif key and key in models:
            duplicates.append({'product_id': item_id, 'duplicate_of': models[key],
                               'reason': 'same_explicit_brand_model', 'inferred_equivalence': True})
            ids[item_id] = models[key]
        else:
            ids[item_id] = item_id
            if key:
                models[key] = item_id
            unique.append(candidate)
    return {'unique': unique, 'duplicates': duplicates}
