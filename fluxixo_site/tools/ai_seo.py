"""Free multi-provider AI SEO orchestrator with strict verification & deterministic fallback.

Supports three free-tier LLM providers with zero credit card requirement:
1. Google Gemini API (GEMINI_API_KEY -> generativelanguage.googleapis.com)
2. Groq API (GROQ_API_KEY -> api.groq.com)
3. OpenRouter free router (OPENROUTER_API_KEY -> openrouter.ai)

Every candidate output passes through the repository's own check_texts firewall,
policy banlist (FORBIDDEN), unverified-claim filter, length bounds, uniqueness
checks, and source-fact grounding before it can touch catalog data or live SEO overrides.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
SITE_DIR = TOOLS_DIR.parent
REPO_DIR = SITE_DIR.parent

for candidate in (str(TOOLS_DIR), str(SITE_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import check_texts  # noqa: E402

LANGS = ('ru', 'en', 'pt', 'es', 'fr', 'he')

MARKET_PROFILES = {
    'ru': {
        'country_code': 'RU',
        'hreflang': ('ru', 'ru-RU'),
        'market_name': 'Россия',
        'voltage_note': '220 В, евровилка (тип C/F)',
        'shipping_note': 'сроки доставки, отслеживание и комплектация у продавца на AliExpress',
        'title_suffix': ' | FLUXIXO',
    },
    'en': {
        'country_code': 'US',
        'hreflang': ('en', 'en-US'),
        'market_name': 'United States & Global',
        'voltage_note': '110-120V AC / US Type A-B plug when powered',
        'shipping_note': 'USPS tracking, seller option selection, and return terms on AliExpress',
        'title_suffix': ' on AliExpress | FLUXIXO',
    },
    'pt': {
        'country_code': 'BR',
        'hreflang': ('pt-BR', 'pt'),
        'market_name': 'Brasil',
        'voltage_note': '110V/220V ou bivolt e tomada padrão NBR 14136',
        'shipping_note': 'opções de envio ao Brasil e valores exibidos no checkout do AliExpress',
        'title_suffix': ' no AliExpress Brasil | FLUXIXO',
    },
    'es': {
        'country_code': 'MX',
        'hreflang': ('es-MX', 'es'),
        'market_name': 'México y Latinoamérica',
        'voltage_note': '110-127V y clavija Tipo A/B en equipos eléctricos',
        'shipping_note': 'tiempos de envío a México y cargos mostrados al pagar en AliExpress',
        'title_suffix': ' en AliExpress México | FLUXIXO',
    },
    'fr': {
        'country_code': 'FR',
        'hreflang': ('fr', 'fr-FR'),
        'market_name': 'France',
        'voltage_note': '230V / prise européenne Type E-F et notice',
        'shipping_note': 'délai de livraison et informations affichées chez le vendeur AliExpress',
        'title_suffix': ' sur AliExpress | FLUXIXO',
    },
    'he': {
        'country_code': 'IL',
        'hreflang': ('he-IL', 'he'),
        'market_name': 'ישראל',
        'voltage_note': 'מתח 220-230V ותקע ישראלי Type H או מתאם',
        'shipping_note': 'תנאי המשלוח לישראל והפרטים בעמוד המוכר ב־AliExpress',
        'title_suffix': ' ב־AliExpress | FLUXIXO',
    },
}

FORBIDDEN_POLICY = ('"Product"', '"Offer"', 'priceCurrency', 'InStock', 'Подборка', 'DealVault', 'dealvault')
BANNED_CLAIMS_RE = re.compile(
    r'(?:[$€£₽₪]'
    r'|\b(?:free shipping|best price|lowest price|limited offer|guaranteed|lifetime warranty|'
    r'5 stars|top rated|bestseller|best seller|discount code|promo code)\b'
    r'|бесплатн\w+\s+доставк|лучш\w+\s+цен|гарантир\w+\s+качество|отзывы\s+покупателей|высокий\s+рейтинг|промокод|акция\b'
    r'|frete grátis|melhor preço|mais vendido|nota máxima'
    r'|envío gratis|mejor precio|más vendido|código promocional'
    r'|livraison gratuite|meilleur prix|mieux noté'
    r'|משלוח חינם|הכי זול|דירוג גבוה|מומלץ ביותר)',
    re.IGNORECASE,
)

GEMINI_MODELS = (
    'gemini-3.8-flash',
    'gemini-3.5-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.0-flash-lite',
)
GROQ_MODELS = (
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'openai/gpt-oss-20b',
)
OPENROUTER_MODELS = (
    'openrouter/free',
    'meta-llama/llama-3.3-70b-instruct:free',
)


def load_ai_keys(local=False, explicit=None):
    """Read optional free AI keys from explicit mapping, environment, or Windows DPAPI."""
    mapping = {
        'GEMINI_API_KEY': 'gemini-api-key.dpapi',
        'GROQ_API_KEY': 'groq-api-key.dpapi',
        'OPENROUTER_API_KEY': 'openrouter-api-key.dpapi',
    }
    found = {}
    for env_name in mapping:
        val = (explicit or {}).get(env_name) or os.environ.get(env_name) or ''
        found[env_name] = str(val).strip()
    if local:
        try:
            from dpapi_store import load_credential
        except ImportError:
            load_credential = None
        if load_credential is not None:
            for env_name, filename in mapping.items():
                if not found[env_name]:
                    found[env_name] = (load_credential(filename) or '').strip()
    return found


def has_ai_provider(keys=None):
    k = keys if keys is not None else load_ai_keys(local=False)
    return any(bool(k.get(name)) for name in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENROUTER_API_KEY'))


def _post_json(url, payload, headers, timeout=35):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req_headers = {
        'User-Agent': 'fluxixo-seo-ai/2.0',
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        **headers,
    }
    last_error = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, data=data, headers=req_headers, method='POST')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8', 'replace'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', 'replace')[:240]
            last_error = RuntimeError(f'HTTP {exc.code}: {detail}')
            if exc.code in (429, 500, 502, 503) and attempt == 0:
                time.sleep(2.0)
                continue
            raise last_error from None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1.5)
                continue
            raise RuntimeError(str(exc)) from None
    raise RuntimeError(str(last_error))


def _extract_json_object(raw_text):
    text = (raw_text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except ValueError:
        pass
    start, end = text.find('{'), text.rfind('}')
    if start != -1 and end > start:
        parsed = json.loads(text[start:end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError('AI response did not contain a JSON object')


def _call_gemini(key, system_prompt, user_prompt, transport=_post_json):
    errors = []
    for model in GEMINI_MODELS:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        payload = {
            'systemInstruction': {'parts': [{'text': system_prompt}]},
            'contents': [{'role': 'user', 'parts': [{'text': user_prompt}]}],
            'generationConfig': {
                'responseMimeType': 'application/json',
                'temperature': 0.25,
                'maxOutputTokens': 1800,
            },
        }
        try:
            res = transport(url, payload, {'x-goog-api-key': key})
            candidates = res.get('candidates') or []
            parts = ((candidates[0].get('content') or {}).get('parts') or []) if candidates else []
            text = ''.join(p.get('text', '') for p in parts if isinstance(p, dict))
            return _extract_json_object(text), f'gemini:{model}'
        except Exception as exc:
            errors.append(f'{model}:{exc}')
    raise RuntimeError('Gemini failed: ' + '; '.join(errors[:2]))


def _call_openai_compat(url, key, models, label, system_prompt, user_prompt, extra_headers=None, transport=_post_json):
    errors = []
    headers = {'Authorization': f'Bearer {key}', **(extra_headers or {})}
    for model in models:
        payload = {
            'model': model,
            'temperature': 0.25,
            'max_tokens': 1800,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        if label == 'groq':
            payload['response_format'] = {'type': 'json_object'}
        try:
            res = transport(url, payload, headers)
            choices = res.get('choices') or []
            msg = (choices[0].get('message') or {}).get('content', '') if choices else ''
            return _extract_json_object(msg), f'{label}:{model}'
        except Exception as exc:
            errors.append(f'{model}:{exc}')
    raise RuntimeError(f'{label} failed: ' + '; '.join(errors[:2]))


def complete_json(system_prompt, user_prompt, keys=None, transport=_post_json):
    """Query the first working free AI provider and return (parsed_dict, provider_tag)."""
    resolved = keys if keys is not None else load_ai_keys(local=False)
    errors = []
    if resolved.get('GEMINI_API_KEY'):
        try:
            return _call_gemini(resolved['GEMINI_API_KEY'], system_prompt, user_prompt, transport=transport)
        except Exception as exc:
            errors.append(str(exc))
    if resolved.get('GROQ_API_KEY'):
        try:
            return _call_openai_compat(
                'https://api.groq.com/openai/v1/chat/completions',
                resolved['GROQ_API_KEY'],
                GROQ_MODELS,
                'groq',
                system_prompt,
                user_prompt,
                transport=transport,
            )
        except Exception as exc:
            errors.append(str(exc))
    if resolved.get('OPENROUTER_API_KEY'):
        try:
            return _call_openai_compat(
                'https://openrouter.ai/api/v1/chat/completions',
                resolved['OPENROUTER_API_KEY'],
                OPENROUTER_MODELS,
                'openrouter',
                system_prompt,
                user_prompt,
                extra_headers={'HTTP-Referer': 'https://www.fluxixo.shop/', 'X-Title': 'FLUXIXO SEO'},
                transport=transport,
            )
        except Exception as exc:
            errors.append(str(exc))
    if not errors:
        return None, 'deterministic'
    return None, 'fallback:' + '; '.join(errors)[:180]


def _numeric_units(text):
    return set(re.findall(r'\b\d+(?:[.,]\d+)?\s?(?:w|v|a|mah|wh|gb|tb|mbps|ghz|mhz|ml|l|mm|cm|m|kg|g|oz|db|lm|k)\b', text.lower()))


def validate_text_field(text, lang, where, max_len=None, min_len=None, allow_numbers_from=None):
    """Run all hard editorial, policy, and check_texts lint checks on a single string."""
    problems = []
    if not isinstance(text, str) or not text.strip():
        return [f'{where}: empty text']
    clean = ' '.join(text.split())
    if min_len is not None and len(clean) < min_len:
        problems.append(f'{where}: too short ({len(clean)} < {min_len})')
    if max_len is not None and len(clean) > max_len:
        problems.append(f'{where}: too long ({len(clean)} > {max_len})')
    for token in FORBIDDEN_POLICY:
        if token in clean:
            problems.append(f'{where}: forbidden policy token {token!r}')
    if BANNED_CLAIMS_RE.search(clean):
        problems.append(f'{where}: unverified price/shipping/review claim')
    check_texts.check_string(clean, lang, where, problems)
    if allow_numbers_from is not None:
        allowed_units = _numeric_units(allow_numbers_from)
        # Market-level standard mains voltages mentioned purely in buyer check reminders are safe when generic.
        allowed_units |= {'110v', '120v', '127v', '220v', '230v'}
        invented = _numeric_units(clean) - allowed_units
        if invented:
            problems.append(f'{where}: ungrounded specs {sorted(invented)}')
    return problems


def validate_product_bundle(bundle, source_text='', extra_allowed_text=''):
    """Validate a complete 6-language product SEO bundle (name, headline, description)."""
    if not isinstance(bundle, dict):
        return ['bundle must be an object']
    grounding = f'{source_text} {extra_allowed_text}'.strip()
    problems = []
    for lang in LANGS:
        entry = bundle.get(lang)
        if not isinstance(entry, dict):
            problems.append(f'{lang}: missing locale object')
            continue
        name = entry.get('name', '')
        headline = entry.get('headline', [])
        desc = entry.get('description', '')
        problems.extend(validate_text_field(name, lang, f'{lang}.name', max_len=72, min_len=4, allow_numbers_from=grounding or None))
        problems.extend(validate_text_field(desc, lang, f'{lang}.description', max_len=360, min_len=35, allow_numbers_from=grounding or None))
        if not isinstance(headline, list) or len(headline) != 2 or not all(isinstance(h, str) and h.strip() for h in headline):
            problems.append(f'{lang}.headline: must be a 2-line array')
        else:
            for idx, line in enumerate(headline):
                problems.extend(validate_text_field(line, lang, f'{lang}.headline[{idx}]', max_len=36, min_len=2, allow_numbers_from=grounding or None))
            if isinstance(name, str) and name.strip():
                check_texts.check_slogan(name, headline, f'{lang}.slogan', problems)
    return problems


def validate_route_override(candidate, lang, *, existing_titles=(), existing_descs=(), grounding_text=''):
    """Validate Stage-2 route metadata & FAQ overrides against every firewall rule."""
    if not isinstance(candidate, dict):
        return ['override must be an object']
    problems = []
    title = ' '.join(str(candidate.get('title') or '').split())
    desc = ' '.join(str(candidate.get('description') or '').split())
    if title:
        problems.extend(validate_text_field(title, lang, f'{lang}.title', max_len=60, min_len=20, allow_numbers_from=grounding_text or None))
        if title in existing_titles:
            problems.append(f'{lang}.title: duplicate title in catalog')
    if desc:
        problems.extend(validate_text_field(desc, lang, f'{lang}.description', max_len=158, min_len=65, allow_numbers_from=grounding_text or None))
        if desc in existing_descs:
            problems.append(f'{lang}.description: duplicate description in catalog')
        if desc == title:
            problems.append(f'{lang}.description: identical to title')
    faq = candidate.get('faq')
    if faq is not None:
        if not isinstance(faq, list) or len(faq) > 3:
            problems.append(f'{lang}.faq: must be a list of at most 3 Q&A objects')
        else:
            for idx, item in enumerate(faq):
                if not isinstance(item, dict):
                    problems.append(f'{lang}.faq[{idx}]: not an object')
                    continue
                q = ' '.join(str(item.get('q') or '').split())
                a = ' '.join(str(item.get('a') or '').split())
                problems.extend(validate_text_field(q, lang, f'{lang}.faq[{idx}].q', max_len=110, min_len=10, allow_numbers_from=grounding_text or None))
                problems.extend(validate_text_field(a, lang, f'{lang}.faq[{idx}].a', max_len=240, min_len=20, allow_numbers_from=grounding_text or None))
    return problems


def _sanitize_for_prompt(value):
    return ' '.join(str(value or '').split())[:300]


def enrich_product_copy(product_context, base_bundle, keys=None, transport=_post_json):
    """Use free AI (when configured) to craft natural 6-language copy for new products, gated strictly by validation."""
    resolved = keys if keys is not None else load_ai_keys(local=False)
    if not has_ai_provider(resolved):
        return base_bundle, 'deterministic'

    system_prompt = (
        'You are the multilingual product editor for FLUXIXO, an informational AliExpress showcase. '
        'Return strict JSON only with keys: ru, en, pt, es, fr, he. Each key maps to '
        '{"name": string (4-65 chars), "headline": [short line 1, short line 2], "description": string (60-240 chars)}. '
        'Rules: 1) Base claims ONLY on the verified seller title, task keywords, and existing copy provided; '
        '2) NEVER mention prices, discounts, shipping speed, star ratings, warranties, or customer reviews; '
        '3) NEVER leave untranslated English words inside ru or he (except standard technical tokens like USB-C, Wi-Fi, LED, LCD, GaN, 2.4G, 5G); '
        '4) In fr, ALWAYS put a space before ?, !, :, ;. In es, ALWAYS use opening ¿ / ¡ if asking/exclaiming. Use Mexican Spanish (es), Brazilian Portuguese (pt), US English (en); '
        '5) End every description with a neutral reminder to check the selected variant and shipping conditions with the seller.'
    )
    user_payload = {
        'category': _sanitize_for_prompt(product_context.get('category')),
        'market': _sanitize_for_prompt(product_context.get('market')),
        'source_title': _sanitize_for_prompt(product_context.get('source_title')),
        'baseline_6_languages': base_bundle,
    }
    grounding = f"{product_context.get('source_title', '')} {json.dumps(base_bundle, ensure_ascii=False)}"
    prompt = json.dumps(user_payload, ensure_ascii=False)

    for attempt in range(2):
        candidate, provider = complete_json(system_prompt, prompt, keys=resolved, transport=transport)
        if not candidate:
            return base_bundle, provider
        problems = validate_product_bundle(candidate, source_text=grounding)
        if not problems:
            normalized = {}
            for lang in LANGS:
                normalized[lang] = {
                    'name': ' '.join(candidate[lang]['name'].split()),
                    'headline': [' '.join(candidate[lang]['headline'][0].split()), ' '.join(candidate[lang]['headline'][1].split())],
                    'description': ' '.join(candidate[lang]['description'].split()),
                }
            return normalized, provider
        prompt = json.dumps({
            **user_payload,
            'previous_validation_errors': problems[:8],
            'instruction': 'Fix every validation error strictly and return valid JSON.',
        }, ensure_ascii=False)

    return base_bundle, 'deterministic-after-lint'


def _fit_title_with_suffix(core, lang):
    profile = MARKET_PROFILES[lang]
    core = ' '.join(core.split()).strip(' -—:|')
    for candidate_suffix in (profile['title_suffix'], ' | FLUXIXO'):
        if len(core) + len(candidate_suffix) <= 60:
            return core + candidate_suffix
    max_core = 60 - len(' | FLUXIXO')
    trimmed = core[:max_core].rsplit(' ', 1)[0].rstrip(' ,;:—-') or core[:max_core]
    return trimmed + ' | FLUXIXO'


def _deterministic_route_proposal(opportunity, current_meta, market_profile):
    lang = opportunity.get('lang', 'en')
    name = _sanitize_for_prompt(opportunity.get('product_name') or current_meta.get('h1') or 'FLUXIXO')
    query = _sanitize_for_prompt(opportunity.get('top_query') or '')
    title_core = name
    if query and len(query) <= 38 and query.lower() not in name.lower():
        # Include exact search query words carefully for non-RU/HE or matching script.
        same_script = not (lang in ('ru', 'he') and re.search(r'[A-Za-z]{4,}', query))
        if same_script and len(f'{name} — {query}') <= 46:
            title_core = f'{name} — {query}'
    title = _fit_title_with_suffix(title_core, lang)
    base_desc = _sanitize_for_prompt(current_meta.get('description') or name)
    note = market_profile['shipping_note']
    candidate_desc = base_desc if len(base_desc) >= 95 else f'{base_desc.rstrip(".")}. {note.capitalize()}.'
    if len(candidate_desc) > 158:
        candidate_desc = candidate_desc[:157].rsplit(' ', 1)[0].rstrip(' ,;:—-') + '…'
    faq_templates = {
        'ru': [
            {'q': f'Что проверить перед заказом «{name}» ?', 'a': f'Сверьте комплектацию, {market_profile["voltage_note"]} и сроки доставки у продавца на AliExpress.'},
        ],
        'en': [
            {'q': f'What should US buyers check before ordering {name}?', 'a': f'Check the exact variant, {market_profile["voltage_note"]}, and {market_profile["shipping_note"]}.'},
        ],
        'pt': [
            {'q': f'O que conferir antes de pedir {name} para o Brasil?', 'a': f'Confira o modelo selecionado, {market_profile["voltage_note"]} e {market_profile["shipping_note"]}.'},
        ],
        'es': [
            {'q': f'¿Qué revisar antes de pedir {name} en México?', 'a': f'Revisa la variante exacta, {market_profile["voltage_note"]} y {market_profile["shipping_note"]}.'},
        ],
        'fr': [
            {'q': f'Que vérifier avant de commander {name} en France ?', 'a': f'Vérifiez la variante choisie, {market_profile["voltage_note"]} et {market_profile["shipping_note"]}.'},
        ],
        'he': [
            {'q': f'מה לבדוק לפני הזמנת {name} לישראל?', 'a': f'בדקו את הדגם המדויק, {market_profile["voltage_note"]} ואת {market_profile["shipping_note"]}.'},
        ],
    }
    faq = []
    for item in faq_templates.get(lang, faq_templates['en']):
        q = item['q'].replace(' ?', '?') if lang != 'fr' else item['q']
        a = item['a']
        faq.append({'q': q[:108], 'a': a[:235]})
    return {'title': title, 'description': candidate_desc, 'faq': faq}, 'deterministic'


def propose_route_optimization(opportunity, current_meta, *, existing_titles=(), existing_descs=(), keys=None, transport=_post_json):
    """Propose & validate a title/description/FAQ upgrade for one weak-CTR or near-top route."""
    lang = opportunity.get('lang', 'en')
    profile = MARKET_PROFILES.get(lang, MARKET_PROFILES['en'])
    resolved = keys if keys is not None else load_ai_keys(local=False)
    grounding = ' '.join(str(x or '') for x in (
        opportunity.get('product_name'),
        opportunity.get('category'),
        opportunity.get('top_query'),
        current_meta.get('h1'),
        current_meta.get('title'),
        current_meta.get('description'),
    ))

    if has_ai_provider(resolved):
        system_prompt = (
            f'You are the autonomous SEO strategist for FLUXIXO targeting market {profile["market_name"]} ({lang}). '
            'Return strict JSON with keys: "title" (<=60 chars), "description" (75-156 chars), '
            '"faq" (array of 2 concise {"q": string, "a": string} items for FAQPage JSON-LD). '
            'Rules: 1) Improve organic CTR and relevance for the search queries without keyword stuffing; '
            '2) Respect country specifics (' + profile['voltage_note'] + '); '
            '3) NEVER invent prices, percentages, shipping times, ratings, warranties, or claims not in the source context; '
            '4) NEVER leave untranslated English words in ru or he (except USB-C, Wi-Fi, LED, LCD, Type-C, GaN, AliExpress, FLUXIXO); '
            '5) In fr add space before ? ! : ;. In es use opening ¿/¡ for questions/exclamations.'
        )
        req_payload = {
            'path': opportunity.get('path'),
            'lang': lang,
            'country': profile['country_code'],
            'product_name': _sanitize_for_prompt(opportunity.get('product_name') or current_meta.get('h1')),
            'category': _sanitize_for_prompt(opportunity.get('category')),
            'top_queries': opportunity.get('queries', [])[:6],
            'bing_keywords': opportunity.get('bing_keywords', [])[:6],
            'current_title': current_meta.get('title', ''),
            'current_description': current_meta.get('description', ''),
            'impressions': opportunity.get('impressions', 0),
            'clicks': opportunity.get('clicks', 0),
            'position': opportunity.get('position'),
        }
        prompt = json.dumps(req_payload, ensure_ascii=False)
        for _ in range(2):
            candidate, provider = complete_json(system_prompt, prompt, keys=resolved, transport=transport)
            if not candidate:
                break
            problems = validate_route_override(
                candidate, lang,
                existing_titles=existing_titles,
                existing_descs=existing_descs,
                grounding_text=grounding,
            )
            if not problems:
                return {
                    'title': ' '.join(candidate['title'].split()),
                    'description': ' '.join(candidate['description'].split()),
                    'faq': [
                        {'q': ' '.join(f['q'].split()), 'a': ' '.join(f['a'].split())}
                        for f in (candidate.get('faq') or [])[:3]
                    ],
                }, provider
            prompt = json.dumps({
                **req_payload,
                'validation_errors': problems[:8],
                'instruction': 'Fix every validation error strictly and keep title <= 60 chars and description 75..156 chars.',
            }, ensure_ascii=False)

    proposal, mode = _deterministic_route_proposal(opportunity, current_meta, profile)
    problems = validate_route_override(
        proposal, lang,
        existing_titles=existing_titles,
        existing_descs=existing_descs,
        grounding_text=grounding,
    )
    if problems:
        return None, 'rejected:' + '; '.join(problems)[:160]
    return proposal, mode
