"""Source-grounded daily discovery using existing AliExpress API credentials.

No network at import. The caller provides the existing signed API transport.
There is no advertising, rarity, quality or shipping inference; selection is a
deterministic comparison of actual seller titles against explicit task terms.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import deque
import copy
from io import BytesIO
from pathlib import Path
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from urllib.parse import urlsplit
from . import curated_copy, image_studio
from .policy import QUERY, DETAIL, normalize_product, image_host_allowed
from .search import _rows, generate_affiliate, ApiError
from .task_copy import task_description, task_headline

LANGS = ('ru', 'en', 'pt', 'es', 'fr', 'he')
CHECK = {
    'ru': 'Перед покупкой сверьте выбранный вариант и условия у продавца.',
    'en': 'Before buying, check the selected option and terms in the seller listing.',
    'pt': 'Antes de comprar, confira a opção escolhida e as condições do vendedor.',
    'es': 'Antes de comprar, revisa la opción elegida y las condiciones del vendedor.',
    'fr': 'Avant l’achat, vérifiez la variante choisie et les conditions du vendeur.',
    'he': 'לפני הקנייה יש לבדוק את האפשרות שנבחרה ואת תנאי המוכר.',
}


def _seed(key, query, groups, category, market, theme, names):
    # Pending-product JSON round trips must retain equality with the trusted seed.
    return {'key': key, 'query': query, 'groups': [list(group) for group in groups], 'category': category,
            'market': market, 'theme': theme, 'names': dict(zip(LANGS, names))}


# Task types are constrained to words actually present in the returned title.
SEEDS = [
    _seed('inspection_mirror', 'telescopic inspection mirror tool', (('inspection',), ('mirror',)), 'Инструменты','US','blue', ('Зеркало для осмотра','Inspection mirror','Espelho de inspeção','Espejo de inspección','Miroir d’inspection','מראת בדיקה')),
    _seed('magnetic_pickup', 'flexible magnetic pickup tool', (('magnetic','magnet'), ('pickup','pick')), 'Инструменты','BR','lavender', ('Магнитный захват','Magnetic pickup tool','Pegador magnético','Recogedor magnético','Outil de ramassage magnétique','כלי איסוף מגנטי')),
    _seed('screw_extractor', 'left hand screw extractor tool', (('screw','screws'), ('extractor','extractors')), 'Инструменты','MX','blue', ('Экстрактор винтов','Screw extractor','Extrator de parafusos','Extractor de tornillos','Extracteur de vis','חולץ ברגים')),
    _seed('sewing_seam_guide', 'magnetic seam guide sewing machine', (('sewing',), ('seam',), ('guide',)), 'Дом','FR','rose', ('Направитель шва','Sewing seam guide','Guia de costura','Guía de costura','Guide de couture','מכוון תפר')),
    _seed('watch_hand_tool', 'watch hand setting tool', (('watch',), ('hand','hands'), ('setting',)), 'Инструменты','IL','sand', ('Инструмент для установки стрелок часов','Watch hand setting tool','Ferramenta para ponteiros de relógio','Herramienta para agujas de reloj','Outil pour aiguilles de montre','כלי להתקנת מחוגי שעון')),
    _seed('irrigation_punch', 'drip irrigation hole punch tool', (('irrigation',), ('punch',)), 'На природе','BR','sand', ('Пробойник для полива','Irrigation punch','Perfurador para irrigação','Perforador de riego','Perforateur d’irrigation','מחורר לצינור השקיה')),
    _seed('reed_trimmer', 'saxophone reed trimmer tool', (('saxophone',), ('reed','reeds'), ('trimmer',)), 'Инструменты','US','rose', ('Триммер для трости саксофона','Saxophone reed trimmer','Cortador de palheta de saxofone','Cortador de cañas de saxofón','Coupe-anche de saxophone','קוצץ עלים לסקסופון')),
    _seed('aquarium_tweezers', 'aquarium curved aquascaping tweezers', (('aquarium',), ('tweezers',)), 'Питомцы','FR','blue', ('Пинцет для аквариума','Aquarium tweezers','Pinça para aquário','Pinzas para acuario','Pince pour aquarium','פינצטה לאקווריום')),
    _seed('keyboard_switch_opener', 'mechanical keyboard switch opener', (('keyboard',), ('switch','switches'), ('opener','opening')), 'Техника','IL','lavender', ('Открывалка переключателей клавиатуры','Keyboard switch opener','Abridor de switches de teclado','Abridor de interruptores de teclado','Ouvre-switch pour clavier','פותחן למתגי מקלדת')),
    _seed('bearing_puller', 'small bearing puller removal tool', (('bearing','bearings'), ('puller',)), 'Инструменты','MX','blue', ('Съёмник подшипника','Bearing puller','Extrator de rolamento','Extractor de rodamientos','Extracteur de roulement','חולץ מסבים')),
    _seed('cable_fish_tape', 'cable fish tape puller wiring', (('cable','wire','wiring'), ('fish',), ('tape',)), 'Инструменты','BR','sand', ('Протяжка для кабеля','Cable fish tape','Passa-fio para cabos','Pasacables de cinta','Tire-fil pour câble','סרט להשחלת כבלים')),
    _seed('button_hook', 'button hook dressing aid', (('button',), ('hook',)), 'Уход','IL','rose', ('Крючок для застёгивания пуговиц','Button hook','Gancho para abotoar','Gancho para abotonar','Crochet pour boutonner','וו לכפתור בגדים')),
    _seed('bead_spinner', 'manual bead spinner tool', (('bead','beads'), ('spinner',)), 'Дом','FR','lavender', ('Спиннер для бисера','Bead spinner','Enfiador giratório de miçangas','Ensartador giratorio de cuentas','Enfile-perles rotatif','מכשיר מסתובב להשחלת חרוזים')),
    _seed('fly_tying_vise', 'fly tying vise vice tool', (('fly',), ('tying',), ('vise','vice')), 'На природе','US','sand', ('Тиски для вязания мушек','Fly tying vise','Morsa para atar moscas','Torno para atar moscas','Étau pour montage de mouches','מלחציים לקשירת זבובים')),
]


class AutonomousError(Exception):
    pass


class DailyError(Exception):
    pass


def _words(value):
    return set(re.findall(r'[a-z0-9]+', value.casefold()))


def _headline(value):
    words = value[:70].split()
    if len(words) < 2:
        return [words[0] if words else 'AliExpress', 'AliExpress']
    split = max(1, len(words) // 2)
    return [' '.join(words[:split]), ' '.join(words[split:])]


def _import_tools_modules(site_root):
    import sys as _sys
    tools_dir = str(Path(site_root) / 'tools')
    if tools_dir not in _sys.path:
        _sys.path.insert(0, tools_dir)
    import ai_seo
    import copy_originality
    return ai_seo, copy_originality


def _bind_external_originality(record_item, translated, site_root):
    from .gemini_client import GeminiDeferred
    from .originality_receipt import ORIGINALITY_POLICY, description_hash, receipt_hashes
    ai_seo, _ = _import_tools_modules(site_root)
    if not ai_seo.free_web_check_enabled():
        return []
    from apply_text_fixes import publication_description
    translated['he'] = {**translated['he'], 'description':
                        publication_description('he', translated['he']['description'])}
    bundle = {'ru': record_item, **translated}
    locales = {}
    problems = ai_seo.external_copy_problems(bundle, receipt=locales)
    if problems:
        return problems
    receipt = {'policy': ORIGINALITY_POLICY, 'locales': locales}
    if receipt_hashes(receipt) != {lang: description_hash(entry['description']) for lang, entry in bundle.items()}:
        raise GeminiDeferred('search_receipt_incomplete')
    record_item['externalOriginality'] = receipt
    return []


def _load_catalog_copy_corpus(products, translations, site_root):
    try:
        _, copy_originality = _import_tools_modules(site_root)
    except Exception:
        if os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
            from .gemini_client import GeminiDeferred
            raise GeminiDeferred('catalog_originality_unavailable') from None
        return None
    overrides = {}
    ov_path = Path(site_root) / 'tools/seo_overrides.json'
    if ov_path.is_file():
        try:
            overrides = json.loads(ov_path.read_text(encoding='utf-8')).get('routes') or {}
        except Exception:
            overrides = {}
    return copy_originality.build_catalog_copy_corpus(
        products, translations, extra_routes=overrides,
    )


_SELLER_NOISE_RE = re.compile(
    r'(?:\[[^\]]*\]|\([^)]*\)|\b(?:free\s*shipping|hot\s*sale|new\s*arrival|202\d|dropshipping|wholesale|best\s*seller|high\s*quality|gift\s*for)\b)',
    re.IGNORECASE,
)

_SEED_CHECK_ANGLES = {
    'ru': (
        'Точные размеры, совместимость и содержимое набора смотрите в выбранной опции у продавца.',
        'Перед оформлением сверьте выбранный вариант, комплектацию и реальные фотографии в карточке товара.',
        'Назначение, аксессуары и детали сборки зависят от варианта — проверьте описание на AliExpress.',
    ),
    'en': (
        'Review exact sizing, included parts, and compatibility under the chosen option on AliExpress.',
        'Compare the selected kit thumbnail and seller photos carefully before confirming checkout.',
        'Check material finish, dimensions, and option contents in the AliExpress listing before ordering.',
    ),
    'pt': (
        'Confira dimensões exatas, compatibilidade e itens incluídos na variação selecionada no AliExpress.',
        'Compare as fotos reais do vendedor e os componentes da opção escolhida antes de fechar o pedido.',
        'Verifique medidas, encaixe e conteúdo da embalagem diretamente na página do produto.',
    ),
    'es': (
        'Revisa medidas exactas, compatibilidad y piezas incluidas dentro de la opción elegida en AliExpress.',
        'Compara las fotografías del vendedor y el detalle de cada variante antes de confirmar tu pedido.',
        'Verifica dimensiones, ajuste y contenido del paquete directamente en la publicación del vendedor.',
    ),
    'fr': (
        'Vérifiez les dimensions exactes, la compatibilité et les accessoires inclus selon la variante sur AliExpress.',
        'Comparez les photos du vendeur et le détail du coffret choisi avant de valider votre commande.',
        'Contrôlez le format, les matières et le contenu de l’option sélectionnée sur la fiche produit.',
    ),
    'he': (
        'בדקו מידות מדויקות, התאמה ותכולת הערכה לפי האפשרות שתבחרו בעמוד המוצר.',
        'השוו בין תמונות המוכר המקוריות למפרט של הדגם המסומן לפני ההזמנה.',
        'ודאו את החומרים, הגודל והאביזרים המצורפים בעמוד המוצר ב־AliExpress.',
    ),
}


def _sanitize_deterministic_copy(record_item, translated, candidate, site_root, catalog_corpus, copy_originality):
    """Avoid verbatim English seller title mirroring and duplicate template endings when AI is unavailable."""
    source_title = str(candidate.get('title') or record_item.get('sourceTitle') or '')
    bundle = {
        'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']},
        **{lang: dict(translated[lang]) for lang in LANGS if lang != 'ru' and lang in translated},
    }
    pid = str(record_item.get('id') or '')
    variant_idx = int(hashlib.sha256(pid.encode('utf-8')).hexdigest()[:2], 16) % 3

    # 1. Clean raw English seller title whenever English name mirrors sourceTitle or exceeds 62 chars
    if source_title and (record_item.get('sourceTask') == 'seller_title' or len(str(record_item.get('name', ''))) > 62):
        en_entry = bundle.get('en')
        if en_entry and (len(en_entry.get('name', '')) > 62 or copy_originality.check_source_title_mirroring({'en': en_entry}, source_title)):
            cleaned = _SELLER_NOISE_RE.sub(' ', en_entry.get('name', ''))
            words = [w for w in cleaned.split() if w.lower() not in {'for', 'with', 'and', 'to', 'in', 'of'}]
            # Keep compact informative noun core distinct from raw long AliExpress title
            compact = ' '.join(words[:4]).strip(' -,:;|/')
            if not compact or len(compact) < 4 or copy_originality.check_source_title_mirroring(
                {'en': {'name': compact, 'headline': en_entry.get('headline', []), 'description': ''}},
                source_title,
            ):
                compact = f"{words[-2]} {words[-1]}".strip() if len(words) >= 2 else (words[0] if words else 'Compact tool')
            en_entry['name'] = compact[:56]

    # 2. If catalog_corpus shows duplicate static description, swap the closing buyer check sentence cleanly
    if catalog_corpus and copy_originality.check_catalog_similarity(bundle, catalog_corpus):
        for lang in LANGS:
            loc = bundle.get(lang)
            if not isinstance(loc, dict):
                continue
            desc = str(loc.get('description') or '').strip()
            std_check = CHECK.get(lang, '')
            if std_check and desc.endswith(std_check):
                stem = desc[:-len(std_check)].strip()
                angle = _SEED_CHECK_ANGLES[lang][variant_idx]
                loc['description'] = f'{stem} {angle}'.strip() if stem else angle

    new_record = {**record_item, **bundle['ru'], 'details': bundle['ru']['description']}
    new_trans = {lang: bundle[lang] for lang in LANGS if lang != 'ru' and lang in bundle}
    return new_record, new_trans


_AI_STUDIO_KEY_NAMES = (
    'FLUXIXO_TEXT_PROVIDER',
    'FLUXIXO_TEXT_GEMINI_API_KEY',
    'CLOUDFLARE_AUTOPILOT_URL',
    'CLOUDFLARE_ACCOUNT_ID',
    'CLOUDFLARE_API_TOKEN',
    'AUTOPILOT_SYNC_TOKEN',
    'GITHUB_TOKEN',
    'FLUXIXO_AI_TRANSPORT',
    'GROQ_API_KEY',
    'OPENROUTER_API_KEY',
)


def _strict_copy_enabled():
    """Return True when strict copy validation is enabled via FLUXIXO_STRICT_COPY or STRICT_COPY."""
    raw = os.environ.get('FLUXIXO_STRICT_COPY')
    if raw is None:
        raw = os.environ.get('STRICT_COPY', '')
    return str(raw).strip().lower() in ('1', 'true', 'yes')


def _load_ai_studio_keys(ai_seo):
    """Select only provider settings explicitly supported by the studio."""
    if not hasattr(ai_seo, 'load_ai_keys'):
        return {}
    raw_keys = ai_seo.load_ai_keys(local=False) or {}
    return {k: raw_keys[k] for k in _AI_STUDIO_KEY_NAMES if k in raw_keys}


def _copy_validation_problems(
    record_item,
    translated,
    site_root,
    *,
    catalog_corpus=None,
    copy_originality=None,
    reject_placeholders=True,
):
    """Validate 6-language copy with check_texts and optional copy_originality checks."""
    from . import discovery_curator

    ct_mod = discovery_curator._lazy_check_texts()
    problems = list(
        ct_mod.lint_product_bundle(
            record_item['id'], record_item, translated, reject_placeholders=reject_placeholders,
        ) or ()
    )
    if problems:
        return problems
    try:
        if copy_originality is None:
            _, copy_originality = _import_tools_modules(site_root)
        full_bundle = {
            'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']},
            **translated,
        }
        problems.extend(copy_originality.check_source_title_mirroring(full_bundle, record_item.get('sourceTitle', '')) or ())
        problems.extend(copy_originality.check_catalog_similarity(full_bundle, catalog_corpus) or ())
    except Exception:
        if os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
            from .gemini_client import GeminiDeferred
            raise GeminiDeferred('copy_checks_unavailable') from None
    return problems


def _maybe_ai_enrich(record_item, translated, candidate, site_root, *, catalog_corpus=None, snippet_fetcher=None,
                     copy_state=None, checkpoint=None):
    """Optionally enhance 6-language copy with Google AI Studio when configured, strictly gated by check_texts."""
    ai_seo = copy_originality = None
    try:
        ai_seo, copy_originality = _import_tools_modules(site_root)
    except Exception:
        if os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
            from .gemini_client import GeminiDeferred
            raise GeminiDeferred('copy_checks_unavailable') from None
        return record_item, translated

    base = {
        'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']},
        **translated,
    }
    keys = _load_ai_studio_keys(ai_seo)
    revisions = ({'copy_state': copy_state, 'checkpoint': checkpoint}
                 if copy_state is not None and keys.get('FLUXIXO_TEXT_PROVIDER') == 'gemini' else {})
    if ai_seo.has_ai_provider(keys):
        try:
            enriched, provider = ai_seo.enrich_product_copy(
                {
                    'category': record_item.get('category', ''),
                    'market': record_item.get('sourceMarket', 'US'),
                    'source_title': candidate.get('title', record_item.get('sourceTitle', '')),
                },
                base,
                keys=keys,
                catalog_corpus=catalog_corpus,
                snippet_fetcher=snippet_fetcher,
                min_desc_len=160, **revisions,
            )
            if (
                isinstance(enriched, dict)
                and isinstance(enriched.get('ru'), dict)
                and provider != 'deterministic'
                and not provider.startswith('fallback:')
                and not provider.startswith('deterministic-after-lint')
            ):
                cand_record = {**record_item, **enriched['ru'], 'details': enriched['ru']['description']}
                cand_trans = {lang: enriched[lang] for lang in LANGS if lang != 'ru' and lang in enriched}
                problems = _copy_validation_problems(
                    cand_record, cand_trans, site_root, catalog_corpus=catalog_corpus,
                    copy_originality=copy_originality, reject_placeholders=True,
                )
                if problems and revisions:
                    ai_seo.reject_cached_copy(candidate.get('title') or record_item.get('sourceTitle', ''),
                                              copy_state, checkpoint, problems=problems)
                if not problems:
                    if hasattr(ai_seo, 'enrich_ru_long_copy'):
                        # Gemini's long-copy helper already makes its bounded correction attempt.
                        attempts = 1 if keys.get('FLUXIXO_TEXT_PROVIDER') == 'gemini' else 2
                        for _lc_attempt in range(attempts):
                            try:
                                long_entry, lc_provider = ai_seo.enrich_ru_long_copy(
                                    {
                                        'category': record_item.get('category', ''),
                                        'source_title': candidate.get('title', record_item.get('sourceTitle', '')),
                                    },
                                    {'ru': enriched['ru'], 'en': enriched.get('en', {})},
                                    keys=keys, **revisions,
                                )
                                if long_entry:
                                    cand_record['_ru_long'] = long_entry
                                    break
                                print(f'ru_long_copy empty ({record_item.get("id")}, attempt {_lc_attempt + 1}, {lc_provider})')
                            except Exception as lc_exc:
                                print(f'ru_long_copy warning ({record_item.get("id")}, attempt {_lc_attempt + 1}): {lc_exc}')
                    return cand_record, cand_trans
        except Exception as error:
            if os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
                from .gemini_client import GeminiDeferred
                if isinstance(error, GeminiDeferred):
                    raise
                raise GeminiDeferred('text_validation_unavailable') from None
            pass

    if os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
        from .gemini_client import GeminiDeferred
        raise GeminiDeferred('text_validation_failed')
    return _sanitize_deterministic_copy(record_item, translated, candidate, site_root, catalog_corpus, copy_originality)


def _matches(seed, title):
    from . import discovery_curator
    banned, _ = discovery_curator.is_ordinary_or_banned_listing(str(title or ''))
    if banned:
        return False
    words = _words(title)
    # A replacement/part with the target words is not the complete tool.
    # This is deliberately conservative; unknown semantic fit remains unknown.
    parts = {'replacement', 'refill', 'spare', 'part', 'parts', 'accessory', 'accessories',
             'case', 'cover', 'sleeve', 'casing', 'adapter', 'attachment', 'battery',
             'batteries', 'charger', 'sticker', 'stickers', 'decal', 'decals'}
    return not (words & parts) and all(any(word in words for word in group) for group in seed['groups'])


def _source_images(raw, primary):
    images = [primary] if primary else []
    value = raw.get('product_small_image_urls') if isinstance(raw, dict) else None
    if isinstance(value, dict):
        value = value.get('string', [])
    if isinstance(value, str):
        value = [value]
    if isinstance(value, list):
        images.extend(value[:8])
    result = []
    for image in images:
        if not isinstance(image, str):
            continue
        try:
            parsed = urlsplit(image)
            if (parsed.scheme != 'https' or not parsed.hostname
                    or not image_host_allowed(parsed.hostname) or parsed.username is not None
                    or parsed.password is not None or parsed.port not in (None, 443)
                    or parsed.fragment or '\\' in image):
                continue
            if image not in result:
                result.append(image)
        except (TypeError, ValueError):
            continue
    return result


_EXTRA_API_FIELDS = (
    'evaluate_rate',
    'lastest_volume',
    'target_sale_price',
    'target_original_price',
    'commission_rate',
    'hot_product_commission_rate',
    'product_video_url',
    'shop_id',
    'first_level_category_name',
    'second_level_category_name',
)


def discover(
    call,
    existing,
    count,
    now,
    *,
    seeds=None,
    use_curated_pool=False,
    check_all_markets=False,
    check_hot_background=False,
    presearch_fn=None,
    preferred_markets=None,
    required_markets=(),
    min_markets=None,
    use_ai_judge=None,
):
    """Compare API results, screen rarity/price/media, AI-judge uniqueness, verify markets, and request links.

    required_markets / min_markets (with check_all_markets): require specific countries or a minimum confirmed
    country count across the 6 storefront markets."""
    from . import discovery_curator
    if (isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 3
            or not isinstance(existing, list) or not callable(call)
            or not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None):
        raise AutonomousError('discovery_input_invalid')
    if count == 0:
        return []
    utc_now = now.astimezone(timezone.utc)
    pref_tuple = tuple(m for m in (preferred_markets or ()) if m in discovery_curator.ALL_MARKETS)
    effective_min_markets = max(0, int(min_markets or 0))
    enable_ai_judge = bool(use_curated_pool) if use_ai_judge is None else bool(use_ai_judge)
    category_counts = {}
    for item in existing:
        if isinstance(item, dict) and item.get('category'):
            cat = str(item['category'])
            category_counts[cat] = category_counts.get(cat, 0) + 1
    if seeds is not None:
        task_seeds = list(seeds)
    elif use_curated_pool:
        rotated = discovery_curator.select_rotating_queries(
            utc_now.date().toordinal(),
            discovery_curator.ALL_MARKETS,
            preferred_markets=pref_tuple or None,
            category_counts=category_counts,
        )
        ai_queries = discovery_curator.generate_ai_discovery_queries(
            existing, target_markets=pref_tuple or discovery_curator.ALL_MARKETS, limit=6,
        )
        # The tool seeds (with their own six-language copy) back up the curated pool once it runs low.
        task_seeds = ai_queries + rotated + list(SEEDS)
    else:
        task_seeds = list(SEEDS)
    # Never the same kind of product twice: drop every type the site already shows (by hand-audited list, by an
    # earlier product from the same task, or by the task's word groups in an existing English name/seller title).
    catalog_texts = [str(item[key]) for item in existing if isinstance(item, dict)
                     for key in ('name_en', 'sourceTitle') if item.get(key)]
    used_task_keys = {str(item['sourceTask']) for item in existing if isinstance(item, dict) and item.get('sourceTask')}
    task_seeds = [task for task in task_seeds
                  if not discovery_curator.type_already_listed(task, catalog_texts, used_task_keys)]
    if not task_seeds:
        return []
    if seeds is not None or not use_curated_pool:
        offset = utc_now.date().toordinal() % len(task_seeds)
        task_seeds = task_seeds[offset:] + task_seeds[:offset]
    known_ids = {str(item['sourceProductId']) for item in existing if isinstance(item, dict) and item.get('sourceProductId')}
    known_titles = {str(item[key]).strip().casefold() for item in existing if isinstance(item, dict)
                    for key in ('name', 'name_en', 'sourceTitle') if item.get(key)}
    known_models = {item.get('sourceModelKey') for item in existing if isinstance(item, dict) and item.get('sourceModelKey')}
    known_shop_ids = {str(item['sourceShopId']) for item in existing if isinstance(item, dict) and item.get('sourceShopId')}
    min_price_cents = os.environ.get('FLUXIXO_MIN_PRICE_CENTS', '1200').strip() or '1200'
    max_price_cents = os.environ.get('FLUXIXO_MAX_PRICE_CENTS', '12000').strip() or '12000'
    chosen = []
    for task in task_seeds:
        is_curated = str(task.get('key') or '').startswith(('rare_', 'ai_rare_'))
        matcher = discovery_curator.matches_rare_query if is_curated else _matches
        try:
            hot_ids, hot_titles = (
                discovery_curator.fetch_hot_background_ids(call, task['query'], task['market'])
                if check_hot_background else (set(), [])
            )
            query = {}
            pages = ('1', '2', '3') if use_curated_pool else ('1',)
            for page_no in pages:
                q_params = {
                    'keywords': task['query'],
                    'target_currency': 'USD',
                    'target_language': 'EN',
                    'ship_to_country': task['market'],
                    'page_size': '20',
                    'page_no': page_no,
                    'tracking_id': 'default',
                }
                if use_curated_pool:
                    q_params['min_sale_price'] = min_price_cents
                    q_params['max_sale_price'] = max_price_cents
                rows = _rows(call(QUERY, q_params), QUERY)
                for raw in rows[:20]:
                    try:
                        item = normalize_product(raw, task['market'], QUERY, utc_now.isoformat())
                        item['image_urls'] = _source_images(raw, item.get('image_url'))
                        item['_source_page'] = int(page_no)
                        for extra_key in _EXTRA_API_FIELDS:
                            if extra_key in raw and raw[extra_key] is not None:
                                item[extra_key] = raw[extra_key]
                        if (item['product_id'] not in query
                                and item['product_id'] not in known_ids
                                and item['title'].strip().casefold() not in known_titles):
                            query[item['product_id']] = item
                    except (ValueError, TypeError):
                        continue
                if len(rows) < 20 or len(query) >= 40:
                    break
            if not query:
                continue
            details = []
            all_pids = sorted(query)
            for start in range(0, len(all_pids), 20):
                chunk = all_pids[start:start + 20]
                details.extend(_rows(call(DETAIL, {
                    'product_ids': ','.join(chunk),
                    'country': task['market'],
                    'target_currency': 'USD',
                    'target_language': 'EN',
                    'tracking_id': 'default',
                }), DETAIL)[:20])
            eligible = []
            catalog_plus_chosen = existing + [
                {'id': c['product_id'], 'sourceTitle': c['title'], 'name_en': c['title'], 'name': c['title']}
                for c in chosen
            ]
            for raw in details:
                try:
                    item = normalize_product(raw, task['market'], DETAIL, utc_now.isoformat())
                    previous = query.get(item['product_id'])
                    if not previous or not matcher(task, item['title']):
                        continue
                    if item['title'].strip().casefold() in known_titles or (item.get('model_key') and item['model_key'] in known_models):
                        continue
                    item['image_url'] = item.get('image_url') or previous.get('image_url')
                    item['image_urls'] = list(dict.fromkeys(_source_images(raw, item['image_url']) + previous.get('image_urls', [])))[:8]
                    if not item['image_urls']:
                        continue
                    item['_source_page'] = previous.get('_source_page', 1)
                    for extra_key in _EXTRA_API_FIELDS:
                        if extra_key in raw and raw[extra_key] is not None:
                            item[extra_key] = raw[extra_key]
                        elif extra_key in previous:
                            item[extra_key] = previous[extra_key]
                    screen_ok, _, screen_meta = discovery_curator.presearch_exclusivity_check(
                        item,
                        catalog_plus_chosen,
                        hot_ids=hot_ids,
                        hot_titles=hot_titles,
                        presearch_fn=presearch_fn,
                        require_observed_metrics=bool(use_curated_pool),
                        known_shop_ids=known_shop_ids,
                    )
                    if not screen_ok:
                        continue
                    item['presearchStatus'] = screen_meta.get('presearch', {'checked': False, 'status': 'local_only'})
                    word_score = len(_words(task['query']) & _words(item['title']))
                    deep_page_bonus = 1.5 if item.get('_source_page', 1) >= 2 else 0.0
                    total_score = word_score + float(screen_meta.get('score') or 0.0) + deep_page_bonus
                    eligible.append((-total_score, item['product_id'], item))
                except (ValueError, TypeError):
                    continue
            sorted_eligible = sorted(eligible, key=lambda value: (value[0], value[1]))
            if enable_ai_judge and sorted_eligible:
                score_by_pid = {pid: -neg_score for neg_score, pid, _ in sorted_eligible}
                judged = discovery_curator.judge_candidates_uniqueness(
                    [item for _, _, item in sorted_eligible[:10]],
                    catalog_plus_chosen,
                )
                sorted_eligible = sorted(
                    [
                        (-(score_by_pid[it['product_id']] + float(it.get('_curator_judge_bonus', 0.0))), it['product_id'], it)
                        for it in judged
                    ],
                    key=lambda value: (value[0], value[1]),
                )
            pref_set = set(pref_tuple)
            verified_pool = []
            full_overlap_count = 0
            for base_neg_score, pid, item in sorted_eligible:
                if check_all_markets:
                    discovery_curator.verify_markets_for_candidate(
                        call, item, discovery_curator.ALL_MARKETS, utc_now.isoformat(),
                    )
                    avail = item.get('availableMarkets') or []
                    if not avail or len(avail) < effective_min_markets or not set(required_markets or ()) <= set(avail):
                        continue
                    overlap = len(set(avail) & pref_set) if pref_set else 0
                    extra_markets = max(0, len(avail) - max(1, effective_min_markets))
                    market_bonus = extra_markets * 1.0 + overlap * 0.5
                    verified_pool.append((0 if (not pref_set or overlap > 0) else 1, base_neg_score - market_bonus, -len(avail), pid, item))
                    if not pref_set or overlap == len(pref_set):
                        full_overlap_count += 1
                        if full_overlap_count >= 2:
                            break
                else:
                    verified_pool.append((0, base_neg_score, 0, pid, item))
            for _, _, _, _, item in sorted(verified_pool, key=lambda v: v[:4]):
                try:
                    affiliate = generate_affiliate(call, item)
                except (ApiError, ValueError, TypeError, KeyError):
                    continue
                item['affiliate_url'] = affiliate
                item['task'] = task
                chosen.append(item)
                known_ids.add(item['product_id'])
                known_titles.add(item['title'].strip().casefold())
                if item.get('model_key'):
                    known_models.add(item['model_key'])
                if item.get('shop_id'):
                    known_shop_ids.add(str(item['shop_id']))
                break
        except (ApiError, ValueError, KeyError, TypeError):
            continue
        if len(chosen) >= count:
            break
    return chosen


def build_record(candidate):
    """Build six honest labels only after the actual seller title matches task."""
    from . import discovery_curator
    from .publisher import CATEGORIES, source_content
    from .task_copy import TASK_COPY
    if not isinstance(candidate, dict):
        raise AutonomousError('candidate_invalid')
    task = candidate.get('task')
    title_str = str(candidate.get('title', ''))
    if task is not None:
        is_seed_task = task in SEEDS and _matches(task, title_str)
        is_curated_task = (
            isinstance(task, dict)
            and str(task.get('key') or '').startswith(('rare_', 'ai_rare_'))
            and task.get('category') in CATEGORIES
            and discovery_curator.matches_rare_query(task, title_str)
        )
        if not (is_seed_task or is_curated_task):
            raise AutonomousError('task_title_mismatch')
    curated = curated_copy.get_task_copy(task.get('key') if isinstance(task, dict) else None)
    if curated is not None:
        localized = copy.deepcopy(curated)
    elif task is None or not task.get('names'):
        category = candidate.get('category') if task is None else task.get('category')
        if category not in CATEGORIES:
            raise AutonomousError('candidate_category_invalid')
        localized = source_content({**candidate, 'category': category})
        for lang, content in localized.items():
            content['headline'] = task_headline('seller_title', lang, category)
        market = candidate.get('market', 'US') if task is None else task.get('market', 'US')
        theme = 'lavender' if task is None else task.get('theme', 'lavender')
        key = 'seller_title' if task is None else task['key']
        task = {'names': {lang: localized[lang]['name'] for lang in LANGS}, 'category': category,
                'market': market, 'theme': theme, 'key': key}
    product_id = candidate.get('product_id')
    if (not isinstance(product_id, str) or not re.fullmatch(r'[1-9][0-9]{0,31}', product_id)
            or candidate.get('detail_url') != f'https://www.aliexpress.com/item/{product_id}.html'
            or not candidate.get('affiliate_url') or not candidate.get('image_url')):
        raise AutonomousError('candidate_identity_invalid')
    if task['key'] in TASK_COPY:
        localized = {}
        for lang in LANGS:
            name = task['names'][lang]
            localized[lang] = {'name': name, 'headline': task_headline(task['key'], lang),
                               'description': task_description(task['key'], lang)}
    internal = 'auto-' + product_id
    record = {'id': internal, **localized['ru'], 'category': task['category'],
              'image': f'assets/images/{internal}.webp', 'original': f'assets/originals/{internal}.webp',
              'imageNote': 'Изображение подготовлено из фотографии продавца. Исходная фотография доступна для сравнения.',
              'affiliateUrl': candidate['affiliate_url'], 'sourceUrl': candidate['detail_url'],
              'sourceProductId': product_id, 'sourceDetailUrl': candidate['detail_url'],
              'sourceTitle': candidate['title'], 'sourceImageUrl': candidate['image_url'],
              'sourceModelKey': candidate.get('model_key'), 'sourceMarket': task['market'],
              'sourceTask': task['key'], 'demo': False, 'theme': task['theme'],
              'scale': 0.85, 'rotation': 0, 'details': localized['ru']['description'], 'facts': []}
    if isinstance(candidate.get('availableMarkets'), list) and candidate['availableMarkets']:
        record['availableMarkets'] = list(candidate['availableMarkets'])
    if isinstance(candidate.get('presearchStatus'), dict):
        record['presearchStatus'] = candidate['presearchStatus']
    if candidate.get('shop_id'):
        record['sourceShopId'] = str(candidate['shop_id'])
    if str(candidate.get('product_video_url') or '').startswith('https://'):
        record['hasVideo'] = True
    return record, {lang: localized[lang] for lang in LANGS if lang != 'ru'}


def refresh_queued(call, candidate, now):
    """Recheck a queued exact ID and affiliate link against current API data."""
    if not isinstance(candidate, dict):
        raise AutonomousError('queued_candidate_invalid')
    product_id = candidate.get('product_id')
    if not isinstance(product_id, str) or not re.fullmatch(r'[1-9][0-9]{0,31}', product_id):
        raise AutonomousError('queued_candidate_invalid')
    markets = candidate.get('markets')
    if not isinstance(markets, dict) or not markets:
        raise AutonomousError('queued_market_unknown')
    for market in markets:
        try:
            rows = _rows(call(DETAIL, {'product_ids': product_id, 'country': market, 'target_currency': 'USD',
                                      'target_language': 'EN', 'tracking_id': 'default'}), DETAIL)
            for raw in rows[:20]:
                item = normalize_product(raw, market, DETAIL, now.astimezone(timezone.utc).isoformat())
                if item['product_id'] != product_id or not item.get('image_url'):
                    continue
                item['image_urls'] = _source_images(raw, item['image_url'])
                if not item['image_urls']:
                    continue
                item['affiliate_url'] = generate_affiliate(call, item)
                item['category'] = candidate.get('category') or (candidate.get('task') or {}).get('category')
                item['market'] = market
                for extra_key in _EXTRA_API_FIELDS:
                    if extra_key in raw and raw[extra_key] is not None:
                        item[extra_key] = raw[extra_key]
                    elif extra_key in candidate and candidate[extra_key] is not None:
                        item[extra_key] = candidate[extra_key]
                if isinstance(candidate.get('availableMarkets'), list) and candidate['availableMarkets']:
                    item['availableMarkets'] = list(candidate['availableMarkets'])
                from . import discovery_curator
                old_task = candidate.get('task')
                if (isinstance(old_task, dict) and str(old_task.get('key') or '').startswith(('rare_', 'ai_rare_'))
                        and discovery_curator.matches_rare_query(old_task, item['title'])):
                    item['task'] = old_task
                else:
                    item['task'] = (
                        next((t for t in discovery_curator.CURATED_RARE_QUERIES
                              if (not item['category'] or t['category'] == item['category'])
                              and discovery_curator.matches_rare_query(t, item['title'])), None)
                        or next((task for task in SEEDS
                                 if (not item['category'] or task['category'] == item['category'])
                                 and _matches(task, item['title'])), None)
                    )
                if item['task'] and not item.get('category'):
                    item['category'] = item['task']['category']
                return item
        except (ApiError, ValueError, KeyError, TypeError):
            continue
    raise AutonomousError('queued_source_unconfirmed')


def mask_usable(image):
    """Conservative shape gate, not a guarantee of product accuracy."""
    from PIL import Image
    if not isinstance(image, Image.Image):
        return False
    alpha = image.convert('RGBA').getchannel('A')
    histogram = alpha.histogram()
    fraction = sum(histogram[128:]) / max(1, image.width * image.height)
    if fraction < 0.025 or fraction > 0.85:
        return False
    sample = alpha.resize((96, 96), Image.Resampling.BOX)
    values = sample.tobytes()
    foreground = {i for i, value in enumerate(values) if value >= 100}
    if not foreground:
        return False
    remaining = set(foreground)
    parts = []
    while remaining:
        first = remaining.pop()
        queue = deque([first])
        size, xs, ys = 0, [], []
        while queue:
            point = queue.popleft()
            size += 1
            x, y = point % 96, point // 96
            xs.append(x)
            ys.append(y)
            for neighbor in ((point-1 if x else -1), (point+1 if x<95 else -1),
                             (point-96 if y else -1), (point+96 if y<95 else -1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        parts.append((size, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    parts.sort(reverse=True)
    if parts[0][0] / len(foreground) < 0.5:
        return False
    # A solid, long strip beside the product is a seller's step-by-step panel, not part of it.
    for size, width, height in parts[1:]:
        if (size / len(foreground) > 0.06 and size / (width * height) > 0.85
                and max(width, height) / min(width, height) >= 2.5):
            return False
    return True


def ocr_poster(tsv):
    if not isinstance(tsv, str):
        raise DailyError('ocr_unavailable')
    words = []
    for line in tsv.splitlines()[1:]:
        cols = line.split('\t')
        if len(cols) < 12:
            continue
        try:
            confidence = float(cols[10])
        except ValueError:
            continue
        text = ''.join(ch for ch in cols[11] if ch.isalnum())
        if confidence >= 50 and len(text) >= 2:
            words.append(text)
    return len(words) >= 3 or (len(words) >= 2 and sum(map(len, words)) >= 16)


def _check_ocr(path):
    try:
        result = subprocess.run(['tesseract', str(path), 'stdout', '--psm', '11', 'tsv'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=25)
        if result.returncode != 0:
            raise ValueError()
        return ocr_poster(result.stdout.decode('utf-8', errors='replace'))
    except (OSError, ValueError, subprocess.SubprocessError):
        raise DailyError('ocr_unavailable') from None


def _image_bytes(url):
    import requests
    if not _source_images({}, url):
        raise DailyError('image_url_invalid')
    try:
        response = requests.get(url, headers={'Referer': 'https://www.aliexpress.com/'},
                                timeout=(5, 20), allow_redirects=False, stream=True)
        try:
            if response.status_code != 200 or not response.headers.get('Content-Type', '').lower().startswith('image/'):
                raise ValueError()
            out = bytearray()
            for block in response.iter_content(64 * 1024):
                out.extend(block)
                if len(out) > 10_000_000:
                    raise ValueError()
            return bytes(out)
        finally:
            response.close()
    except Exception:
        raise DailyError('source_image_unavailable') from None


def _pixel_hash(image):
    rgba = image.convert('RGBA')
    h = hashlib.sha256(f'{rgba.width}x{rgba.height}:'.encode())
    h.update(rgba.tobytes())
    return h.hexdigest()


PHOTOS_PER_PRODUCT = 3   # every new product gets three cut-out photos (main + two more views)
VIEW_REPEAT = 12         # dHash distance at or below which two cut-outs count as the same view
VIEW_MIN_SIDE = 600      # smaller seller photos give blurry cut-outs
MAX_ATTEMPTS = 30        # candidates tried per run; three clean views are rarer than one
SEARCH_BUDGET_SECONDS = 40 * 60   # stop looking in time for the build, push and deploy
LEASE_SECONDS = 75 * 60
CUT_MODEL = 'isnet-general-use'   # cleaner edges and less haze than u2net on seller photos


def _dhash(image):
    return int(image_studio.compute_dhash(image), 16)


def _on_white(image):
    from PIL import Image
    canvas = Image.new('RGB', image.size, 'white')
    canvas.paste(image, mask=image.getchannel('A'))
    return canvas


def _drop_specks(cutout, keep=0.015):
    """Remove what the matting leaves around the product: faint haze, ghost logos, loose bits of background.

    Pixels the model is unsure about (low alpha) are cleared, then only the solid parts of the product are kept
    (any part of at least 1.5% of the product), and everything farther than a few pixels from them is cleared."""
    from PIL import Image, ImageChops, ImageFilter
    alpha = cutout.getchannel('A').point(lambda a: 0 if a < 24 else a)
    parts = _parts(alpha)
    if not parts:
        return cutout
    total = sum(len(part) for part in parts)
    mask = Image.new('L', (128, 128), 0)
    for part in parts:
        if len(part) >= keep * total:
            for point in part:
                mask.putpixel((point % 128, point // 128), 255)
    mask = mask.filter(ImageFilter.MaxFilter(5)).resize(cutout.size, Image.Resampling.BILINEAR)
    mask = mask.point(lambda v: 255 if v >= 128 else 0)
    cleaned = cutout.copy()
    cleaned.putalpha(ImageChops.multiply(alpha, mask))
    return cleaned


def _major_parts(cutout):
    """How many separate big objects the cut-out holds (each at least 10% of it): a collage of zoomed panels or a
    call-out circle shows up as more objects than the product's own main photo."""
    parts = _parts(cutout.getchannel('A'))
    total = sum(len(part) for part in parts)
    return sum(1 for part in parts if len(part) >= 0.1 * total)


def _parts(alpha):
    """Connected solid regions of an alpha mask on a 128 x 128 grid, as lists of grid indices."""
    from PIL import Image
    values = alpha.resize((128, 128), Image.Resampling.BOX).tobytes()
    remaining = {i for i, value in enumerate(values) if value >= 100}
    parts = []
    while remaining:
        first = remaining.pop()
        queue, part = deque([first]), [first]
        while queue:
            point = queue.popleft()
            x, y = point % 128, point // 128
            for neighbor in ((point-1 if x else -1), (point+1 if x < 127 else -1),
                             (point-128 if y else -1), (point+128 if y < 127 else -1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
                    part.append(neighbor)
        parts.append(part)
    return parts



def _light_share(cutout):
    """Share of the solid cut-out that is near-white neutral: high when a slab of the photo's backdrop survived the cut
    (a card, an arch, a table top), or when the product itself is white."""
    from PIL import Image
    small = cutout.copy()
    small.thumbnail((256, 256), Image.Resampling.BOX)
    solid = light = 0
    for r, g, b, a in (small.get_flattened_data() if hasattr(small, 'get_flattened_data') else small.getdata()):
        if a >= 200:
            solid += 1
            if min(r, g, b) >= 232 and max(r, g, b) - min(r, g, b) <= 12:
                light += 1
    return 1.0 if solid == 0 else light / solid


def _has_text(canvas, stage, name):
    """OCR of the cut-out on white, upright and turned (packaging text often runs sideways or upside down)."""
    picture = _on_white(canvas)
    for turn in (0, 90, 180, 270):
        check = stage / f'{name}-r{turn}.png'
        (picture.rotate(turn, expand=True) if turn else picture).save(check, 'PNG')
        if _check_ocr(check):
            return True
    return False


def _studio(cutout):
    """FLUXIXO studio framing: clean edges, tight trim, tonal balance, and subtle grounding shadow."""
    return image_studio.compose_studio_frame(
        cutout,
        canvas_size=1254,
        max_box=890,
        normalize_tonality=True,
        add_contact_shadow=True,
    )


STUDIO_VIEW_ANGLES = (
    ('hero studio view', 'diagonal three-quarter hero studio view, clear full silhouette'),
    ('45-degree isometric studio angle', 'elevated side isometric studio view'),
    ('close-up detail studio view', 'angled macro close-up detail studio view'),
)


def _load_verified_source_image(url, sources, perceptual_index):
    """Download, size-check, and deduplicate one seller image against known sources."""
    from PIL import Image
    if not isinstance(url, str) or not url.strip():
        return None
    raw = _image_bytes(url)
    digest = hashlib.sha256(raw).hexdigest()
    if digest in sources:
        return None
    sources.add(digest)
    with Image.open(BytesIO(raw)) as value:
        if value.width < 1 or value.height < 1 or value.width * value.height > 25_000_000:
            return None
        value.load()
        original = value.convert('RGBA')
    if min(original.size) < VIEW_MIN_SIDE:
        return None
    source_hashes = image_studio.compute_perceptual_hashes(original)
    if perceptual_index:
        is_dup, _ = image_studio.is_perceptually_duplicate(source_hashes, perceptual_index)
        if is_dup:
            return None
    return original, digest, source_hashes


def _build_media_record(image_path, original_path, original, digest, url, cut_hashes, source_hashes, q_metrics):
    """Assemble standardized media payload expected by accumulate()."""
    return {
        'image': image_path,
        'original': original_path,
        'source_sha256': digest,
        'pixel_sha256': _pixel_hash(original),
        'source_url': url,
        'image_dhash': cut_hashes['dhash'],
        'image_ahash': cut_hashes['ahash'],
        'image_aspect': cut_hashes['aspect'],
        'source_dhash': source_hashes['dhash'],
        'source_ahash': source_hashes['ahash'],
        'source_aspect': source_hashes['aspect'],
        'image_quality': q_metrics,
        'image_quality_verified': True,
    }


def _resolve_worker_transport_url():
    """Return Cloudflare Worker HTTP proxy URL when Worker transport is active."""
    resolver = getattr(image_studio, '_resolve_worker_transport_url', None)
    if callable(resolver):
        return resolver()
    transport = os.environ.get('FLUXIXO_AI_TRANSPORT', '').strip().lower()
    if transport in ('direct', 'none', 'disabled'):
        return ''
    explicit_url = os.environ.get('CLOUDFLARE_AUTOPILOT_URL')
    if explicit_url is not None:
        cleaned = explicit_url.strip().rstrip('/')
        if cleaned:
            return cleaned
        if not transport:
            return ''
    if transport in ('worker', 'cloudflare_worker', 'autopilot'):
        return getattr(image_studio, 'DEFAULT_CLOUDFLARE_AUTOPILOT_URL', '').rstrip('/')
    return ''


def _resolve_cloudflare_media_ready():
    """Return (worker_url, cf_token, has_cloudflare) for Workers AI image generation."""
    worker_url = _resolve_worker_transport_url()
    token_fn = getattr(image_studio, 'resolve_cloudflare_ai_token', None)
    cf_token = ''
    if callable(token_fn):
        cf_token, _ = token_fn(local=not bool(worker_url))
    return worker_url, (cf_token or '').strip(), bool(worker_url or (cf_token or '').strip())


def _extract_rembg_view(
    original,
    index,
    internal_id,
    stage,
    remove_fn,
    session,
    *,
    perceptual_index=None,
    kept=None,
    main_ready=False,
    extra_slot_open=True,
    main_light=0.0,
    main_parts=1,
):
    """Extract and verify one studio cutout via local rembg + Tesseract OCR check."""
    from PIL import Image

    source = stage / f'{internal_id}-source-{index}.png'
    original.save(source, 'PNG')
    poster = _check_ocr(source)
    if poster and not main_ready and not extra_slot_open:
        return None
    work = original
    if max(work.size) > 1600:
        work = work.copy()
        work.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    cutout = _drop_specks(remove_fn(work, session=session).convert('RGBA'))
    if not cutout.getbbox() or not mask_usable(cutout):
        return None
    if main_ready or poster:
        cutout = _drop_specks(cutout, keep=0.06)
    raw_bbox = cutout.getbbox()
    raw_fg_size = (
        max(1, round((raw_bbox[2] - raw_bbox[0]) * (original.width / work.width))),
        max(1, round((raw_bbox[3] - raw_bbox[1]) * (original.height / work.height))),
    ) if raw_bbox else original.size
    canvas = _studio(cutout)
    q_ok, q_metrics = image_studio.verify_studio_image(
        cutout,
        raw_fg_size=raw_fg_size,
        composed=canvas,
    )
    if not q_ok:
        return None
    if main_ready or poster:
        if (
            _light_share(canvas) > max(0.3, main_light + 0.2)
            or _major_parts(canvas) > main_parts
            or _has_text(canvas, stage, f'{internal_id}-check-{index}')
        ):
            return None
    cut_hashes = image_studio.compute_perceptual_hashes(canvas)
    if perceptual_index:
        is_dup, _ = image_studio.is_perceptually_duplicate(cut_hashes, perceptual_index)
        if is_dup:
            return None
    fingerprint = _dhash(_on_white(canvas))
    if kept and any(bin(fingerprint ^ other).count('1') <= VIEW_REPEAT for other in kept):
        return None
    return canvas, q_metrics, cut_hashes, fingerprint, poster


def _generate_cf_slot_view(
    *,
    title,
    slot_ref,
    angle_choices,
    target_bg,
    category,
    visual_spec,
    provider,
    slot_idx=0,
    perceptual_index=None,
    kept=(),
):
    """Generate and validate one transparent RGBA studio cutout via Cloudflare Workers AI."""
    from PIL import Image

    direct_bg = os.environ.get('FLUXIXO_DIRECT_STUDIO_BG', '').strip().lower() in ('1', 'true', 'yes')
    # Slot 0 (hero) and Slot 2 (active effect) use FLUX.2 Klein 9B; Slot 1 (45° side angle) uses FLUX.2 Klein 4B (~115 Neurons)
    slot_model = '@cf/black-forest-labs/flux-2-klein-4b' if slot_idx == 1 else None
    # Transparent RGBA cutout mode generates on neutral pure #FFFFFF to eliminate bright category color casts
    # and ensure clean alpha extraction; only explicit direct_bg opt-in uses a category world backdrop.
    if direct_bg:
        effective_bg = target_bg or image_studio.resolve_world_background(category) or '#F3F0E9'
    else:
        effective_bg = '#FFFFFF'

    for angle in angle_choices:
        try:
            gen_kwargs = {
                'reference_image': slot_ref,
                'angle': angle,
                'background_hex': effective_bg,
                'category': category or None,
                'visual_spec': visual_spec or None,
                'provider': provider,
            }
            if slot_model:
                gen_kwargs['model'] = slot_model
            gen_kwargs['cutout_alpha'] = not direct_bg
            try:
                canvas = image_studio.generate_studio_cutout(title, **gen_kwargs)
            except TypeError:
                gen_kwargs.pop('cutout_alpha', None)
                gen_kwargs.pop('model', None)
                canvas = image_studio.generate_studio_cutout(title, **gen_kwargs)
            if not isinstance(canvas, Image.Image) or not canvas.getbbox():
                continue
            if direct_bg:
                q_ok, q_metrics = image_studio.verify_direct_studio_image(canvas)
            else:
                if not mask_usable(canvas):
                    continue
                q_ok, q_metrics = image_studio.verify_studio_image(canvas, composed=canvas)
            if not q_ok:
                continue
            cut_hashes = image_studio.compute_perceptual_hashes(canvas)
            if perceptual_index:
                is_dup, _ = image_studio.is_perceptually_duplicate(cut_hashes, perceptual_index)
                if is_dup:
                    continue
            fingerprint = _dhash(_on_white(canvas))
            if any(bin(fingerprint ^ other).count('1') <= VIEW_REPEAT for other in kept):
                continue
            return canvas, q_metrics, cut_hashes, fingerprint
        except Exception:
            continue
    return None


def _default_media_preparer():
    if os.environ.get('FLUXIXO_REVIEW_REQUIRED') == '1':
        from .reviewed_media import ReviewedMediaPreparer
        root = Path(os.environ.get('FLUXIXO_REVIEW_STATE_DIR', 'fluxixo_site/reserve/reviewed-media'))
        # Shared Workers Paid usage cannot be bounded from delayed analytics.
        # No FLUX transport is supplied: use authenticated seller imagery and review it.
        return ReviewedMediaPreparer(root).prepare
    # Studio image preparation modes (strictly Google/Gemini-free):
    # - 'hybrid': rembg cutouts on GitHub for Slots 1-2 + Cloudflare FLUX.2 active-effect generation for Slot 3 (0 Google quota).
    # - 'generate': Cloudflare Workers AI (FLUX.2 Klein 9B/4B) for all 3 slots without rembg/OCR.
    # - 'cut': local rembg cutouts for all 3 slots.
    mode = (os.environ.get('FLUXIXO_IMAGE_MODE') or 'generate').strip().lower()
    worker_url, _cf_token, has_cloudflare = _resolve_cloudflare_media_ready()
    use_vision_spec = os.environ.get('FLUXIXO_USE_VISION_SPEC', '').strip().lower() in ('1', 'true', 'yes')
    provider = image_studio.resolve_image_provider(autopilot_url=worker_url)

    def _run_cloudflare_generation(candidate, internal_id, stage, *, perceptual_index=None, preloaded=None):
        urls = candidate.get('image_urls') or [candidate.get('image_url')]
        sources = set()
        loaded_candidates = list(preloaded or [])
        for url in urls[:9]:
            if len(loaded_candidates) >= 4:
                break
            try:
                loaded = _load_verified_source_image(url, sources, perceptual_index)
            except Exception:
                continue
            if loaded is not None:
                cand_img = loaded[0].convert('RGB')
                bg = image_studio._estimate_studio_backdrop(cand_img)
                bg_luma = sum(bg) / 3.0
                loaded_candidates.append((bg_luma, loaded, url))
        if not loaded_candidates:
            raise DailyError('visual_quality_failed')

        hero_idx = max(range(len(loaded_candidates)), key=lambda i: loaded_candidates[i][0])
        _, ref_item, ref_url = loaded_candidates[hero_idx]
        alt_items = [loaded_candidates[i][1] for i in range(len(loaded_candidates)) if i != hero_idx]
        ref_original, ref_digest, ref_hashes = ref_item
        title = str(candidate.get('title') or '').strip() or 'compact precision product'
        category = str(candidate.get('category') or (candidate.get('task') or {}).get('category') or '').strip()
        target_bg = image_studio.resolve_world_background(category)
        visual_spec = ''
        if use_vision_spec:
            visual_spec = image_studio.describe_product_from_reference(
                ref_original,
                product_title=title,
            )
        slot_refs = [
            ref_original,
            alt_items[0][0] if alt_items else ref_original,
            alt_items[1][0] if len(alt_items) > 1 else (alt_items[0][0] if alt_items else ref_original),
        ]
        main, views, kept = None, [], []
        for slot_idx, angle_choices in enumerate(STUDIO_VIEW_ANGLES[:PHOTOS_PER_PRODUCT]):
            accepted = _generate_cf_slot_view(
                title=title,
                slot_ref=slot_refs[slot_idx],
                angle_choices=angle_choices,
                target_bg=target_bg,
                category=category,
                visual_spec=visual_spec,
                provider=provider,
                slot_idx=slot_idx,
                perceptual_index=perceptual_index,
                kept=kept,
            )
            if accepted is None:
                break
            canvas, q_metrics, cut_hashes, fingerprint = accepted
            kept.append(fingerprint)
            if slot_idx == 0:
                image_path = stage / f'{internal_id}-prepared.webp'
                original_path = stage / f'{internal_id}-original.webp'
                canvas.save(image_path, 'WEBP', quality=95, method=6)
                ref_original.save(original_path, 'WEBP', quality=90, method=6)
                main = _build_media_record(
                    image_path, original_path, ref_original, ref_digest,
                    ref_url, cut_hashes, ref_hashes, q_metrics,
                )
            else:
                view_path = stage / f'{internal_id}-view-{len(views) + 2}.webp'
                canvas.save(view_path, 'WEBP', quality=92, method=6)
                views.append(view_path)

        if main is None or len(views) < PHOTOS_PER_PRODUCT - 1:
            raise DailyError('visual_quality_failed')
        main['views'] = views
        return main

    if mode == 'generate' and has_cloudflare:
        return lambda candidate, internal_id, stage, *, perceptual_index=None: _run_cloudflare_generation(
            candidate, internal_id, stage, perceptual_index=perceptual_index,
        )

    rembg_session = None
    rembg_remove = None
    try:
        from rembg import remove as _rembg_remove, new_session
        rembg_session = new_session(CUT_MODEL)
        rembg_remove = _rembg_remove
    except Exception:
        rembg_session = None
        rembg_remove = None

    if mode == 'hybrid' and has_cloudflare:
        if rembg_session is None:
            return lambda candidate, internal_id, stage, *, perceptual_index=None: _run_cloudflare_generation(
                candidate, internal_id, stage, perceptual_index=perceptual_index,
            )

        def prepare_hybrid(candidate, internal_id, stage, *, perceptual_index=None):
            """Use local rembg for Slots 1-2 (0 Neurons) and Cloudflare FLUX.2 for Slot 3 active-effect demo."""
            urls = candidate.get('image_urls') or [candidate.get('image_url')]
            main, views, kept, sources, main_light, main_parts = None, [], [], set(), 0.0, 1
            loaded_sources = []
            max_cut_views = max(0, PHOTOS_PER_PRODUCT - 2)  # Slot 1 + Slot 2; reserve final slot for FLUX.2 active effect
            for index, url in enumerate(urls[:9]):
                if main is not None and len(views) >= max_cut_views and len(loaded_sources) >= 3:
                    break
                try:
                    loaded = _load_verified_source_image(url, sources, perceptual_index)
                    if loaded is None:
                        continue
                    original, digest, source_hashes = loaded
                    cand_img = original.convert('RGB')
                    bg_luma = sum(image_studio._estimate_studio_backdrop(cand_img)) / 3.0
                    loaded_sources.append((bg_luma, loaded, url))
                    if main is not None and len(views) >= max_cut_views:
                        continue
                    extracted = _extract_rembg_view(
                        original,
                        index,
                        internal_id,
                        stage,
                        rembg_remove,
                        rembg_session,
                        perceptual_index=perceptual_index,
                        kept=kept,
                        main_ready=main is not None,
                        extra_slot_open=len(views) < max_cut_views,
                        main_light=main_light,
                        main_parts=main_parts,
                    )
                    if extracted is None:
                        continue
                    canvas, q_metrics, cut_hashes, fingerprint, poster = extracted
                    kept.append(fingerprint)
                    if main is None and not poster:
                        image_path = stage / f'{internal_id}-prepared.webp'
                        original_path = stage / f'{internal_id}-original.webp'
                        canvas.save(image_path, 'WEBP', quality=95, method=6)
                        original.save(original_path, 'WEBP', quality=90, method=6)
                        main_light, main_parts = _light_share(canvas), _major_parts(canvas)
                        main = _build_media_record(
                            image_path, original_path, original, digest,
                            url, cut_hashes, source_hashes, q_metrics,
                        )
                    elif len(views) < max_cut_views:
                        view_path = stage / f'{internal_id}-view-{len(views) + 2}.webp'
                        canvas.save(view_path, 'WEBP', quality=92, method=6)
                        views.append(view_path)
                    else:
                        kept.pop()
                except DailyError as error:
                    if str(error) == 'ocr_unavailable':
                        raise
                except Exception:
                    continue

            if not loaded_sources:
                raise DailyError('visual_quality_failed')
            if main is None:
                return _run_cloudflare_generation(
                    candidate,
                    internal_id,
                    stage,
                    perceptual_index=perceptual_index,
                    preloaded=loaded_sources[:4],
                )

            title = str(candidate.get('title') or '').strip() or 'compact precision product'
            category = str(candidate.get('category') or (candidate.get('task') or {}).get('category') or '').strip()
            target_bg = image_studio.resolve_world_background(category)
            ref_item = max(loaded_sources, key=lambda row: row[0])[1]
            ref_original = ref_item[0]
            alt_items = [row[1][0] for row in loaded_sources if row[1][1] != ref_item[1]]
            visual_spec = ''
            if use_vision_spec:
                visual_spec = image_studio.describe_product_from_reference(
                    ref_original,
                    product_title=title,
                )

            # Fill Slot 2 via Cloudflare only if seller gallery lacked a second clean cutout; always generate Slot 3 effect.
            while len(views) < PHOTOS_PER_PRODUCT - 1:
                slot_idx = len(views) + 1
                angle_choices = STUDIO_VIEW_ANGLES[min(slot_idx, len(STUDIO_VIEW_ANGLES) - 1)]
                slot_ref = (alt_items[-1] if alt_items else ref_original) if slot_idx >= PHOTOS_PER_PRODUCT - 1 else (alt_items[0] if alt_items else ref_original)
                accepted = _generate_cf_slot_view(
                    title=title,
                    slot_ref=slot_ref,
                    angle_choices=angle_choices,
                    target_bg=target_bg,
                    category=category,
                    visual_spec=visual_spec,
                    provider=provider,
                    perceptual_index=perceptual_index,
                    kept=kept,
                )
                if accepted is None:
                    break
                canvas, _q_metrics, _cut_hashes, fingerprint = accepted
                kept.append(fingerprint)
                view_path = stage / f'{internal_id}-view-{len(views) + 2}.webp'
                canvas.save(view_path, 'WEBP', quality=92, method=6)
                views.append(view_path)

            if len(views) < PHOTOS_PER_PRODUCT - 1:
                raise DailyError('visual_quality_failed')
            main['views'] = views
            return main

        return prepare_hybrid

    if rembg_session is None:
        raise DailyError('image_processor_unavailable') from None

    def prepare(candidate, internal_id, stage, *, perceptual_index=None):
        """Main photo plus two more views of the same listing, all cut out; fewer than three means another product."""
        urls = candidate.get('image_urls') or [candidate.get('image_url')]
        main, views, kept, sources, main_light, main_parts = None, [], [], set(), 0.0, 1
        for index, url in enumerate(urls[:9]):
            if main is not None and len(views) >= PHOTOS_PER_PRODUCT - 1:
                break
            try:
                loaded = _load_verified_source_image(url, sources, perceptual_index)
                if loaded is None:
                    continue
                original, digest, source_hashes = loaded
                extracted = _extract_rembg_view(
                    original,
                    index,
                    internal_id,
                    stage,
                    rembg_remove,
                    rembg_session,
                    perceptual_index=perceptual_index,
                    kept=kept,
                    main_ready=main is not None,
                    extra_slot_open=len(views) < PHOTOS_PER_PRODUCT - 1,
                    main_light=main_light,
                    main_parts=main_parts,
                )
                if extracted is None:
                    continue
                canvas, q_metrics, cut_hashes, fingerprint, poster = extracted
                kept.append(fingerprint)
                if main is None and not poster:
                    image_path = stage / f'{internal_id}-prepared.webp'
                    original_path = stage / f'{internal_id}-original.webp'
                    canvas.save(image_path, 'WEBP', quality=95, method=6)
                    original.save(original_path, 'WEBP', quality=90, method=6)
                    main_light, main_parts = _light_share(canvas), _major_parts(canvas)
                    main = _build_media_record(
                        image_path, original_path, original, digest,
                        url, cut_hashes, source_hashes, q_metrics,
                    )
                elif len(views) < PHOTOS_PER_PRODUCT - 1:
                    view_path = stage / f'{internal_id}-view-{len(views) + 2}.webp'
                    canvas.save(view_path, 'WEBP', quality=92, method=6)
                    views.append(view_path)
                else:
                    kept.pop()
            except DailyError as error:
                if str(error) == 'ocr_unavailable':
                    raise
            except Exception:
                continue
        if main is None or len(views) < PHOTOS_PER_PRODUCT - 1:
            raise DailyError('visual_quality_failed')
        main['views'] = views
        return main
    return prepare


def _old_image_hashes(products, dist):
    from PIL import Image
    result = set()
    for product in products:
        for name in ('sourceImageSha256', 'sourcePixelSha256'):
            if isinstance(product.get(name), str):
                result.add(product[name])
        relative = product.get('original')
        if not isinstance(relative, str):
            continue
        path = (dist / relative).resolve()
        if not path.is_relative_to(dist.resolve()) or not path.is_file() or path.stat().st_size > 10_000_000:
            continue
        try:
            raw = path.read_bytes()
            result.add(hashlib.sha256(raw).hexdigest())
            with Image.open(BytesIO(raw)) as image:
                if image.width * image.height <= 25_000_000:
                    image.load()
                    result.add(_pixel_hash(image))
        except Exception:
            continue
    return result


def _atomic_bytes(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.daily-', suffix='.tmp', delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def _media_accepts_perceptual(fn):
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return any(
        p.kind == inspect.Parameter.VAR_KEYWORD or p.name == 'perceptual_index'
        for p in sig.parameters.values()
    )


def _extract_media_perceptual(media):
    """Read dHash/aHash descriptors from media dict or image file; returns None on synthetic test bytes."""
    from PIL import Image
    out = {}
    if isinstance(media.get('image_dhash'), str) and isinstance(media.get('image_ahash'), str):
        out['image'] = {
            'dhash': media['image_dhash'],
            'ahash': media['image_ahash'],
            **({'aspect': media['image_aspect']} if media.get('image_aspect') else {}),
        }
    else:
        try:
            with Image.open(media['image']) as img:
                img.load()
                out['image'] = image_studio.compute_perceptual_hashes(img)
        except Exception:
            pass
    if isinstance(media.get('source_dhash'), str) and isinstance(media.get('source_ahash'), str):
        out['original'] = {
            'dhash': media['source_dhash'],
            'ahash': media['source_ahash'],
            **({'aspect': media['source_aspect']} if media.get('source_aspect') else {}),
        }
    elif media.get('original'):
        try:
            with Image.open(media['original']) as orig_img:
                orig_img.load()
                out['original'] = image_studio.compute_perceptual_hashes(orig_img)
        except Exception:
            pass
    return out


def required_markets():
    """Countries every new product must be sold in (FLUXIXO_REQUIRED_MARKETS, default all six).

    Each language's front-page rope shows the first three products sold in its country, so a new product missing
    one country leaves an older product hanging under "today's drop" there (2026-11-15: a borescope not sold in
    Russia and France, a radio not sold in the US and Brazil). 'none' switches the rule off."""
    from .discovery_curator import ALL_MARKETS
    raw = os.environ.get('FLUXIXO_REQUIRED_MARKETS', '').strip().upper()
    if raw == 'NONE':
        return ()
    if not raw:
        return tuple(ALL_MARKETS)
    markets = tuple(dict.fromkeys(m.strip() for m in raw.split(',') if m.strip()))
    if not markets or any(m not in ALL_MARKETS for m in markets):
        raise DailyError('required_markets_invalid')
    return markets


def min_confirmed_markets():
    """Minimum number of target countries a product must sell in (FLUXIXO_MIN_MARKETS, default 0)."""
    from .discovery_curator import ALL_MARKETS
    raw = os.environ.get('FLUXIXO_MIN_MARKETS', '').strip()
    if not raw:
        return 0
    if not re.fullmatch(r'[0-9]+', raw):
        raise DailyError('min_markets_invalid')
    value = int(raw)
    if not 0 <= value <= len(ALL_MARKETS):
        raise DailyError('min_markets_invalid')
    return value


def accumulate(*, count, site_root, dist, reserve_dir, ledger_path, now=None,
               discover_fn=None, media_fn=None, validation_run_id=None, queue_store=None, refresh_fn=None,
               enforce_unique_copy=None, snippet_fetcher=None, preferred_markets=None):
    """Prepare full batch before mutation; catalog and ledger commit together later."""
    from .daily_ledger import read_ledger, verify_catalog, remaining, record, atomic_write, utc_day
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 3:
        raise DailyError('count_invalid')
    if validation_run_id is not None and count != 1:
        raise DailyError('validation_requires_one')
    if count == 0:
        return {'added': 0}
    # Only the paid AI-generation mode caps image attempts (the workflow exports it then); unset, the free cut-out
    # mode keeps trying up to MAX_ATTEMPTS, so one rejected photo no longer cancels the whole evening.
    raw_media_budget = os.environ.get('FLUXIXO_MAX_MEDIA_PRODUCTS')
    if raw_media_budget is not None and not re.fullmatch(r'[0-3]', raw_media_budget.strip()):
        raise DailyError('media_budget_invalid')
    # The workflow durably reserves this allowance before starting. Count every
    # candidate sent to image processing, including candidates later rejected.
    media_budget = MAX_ATTEMPTS if raw_media_budget is None else int(raw_media_budget.strip())
    instant = now or datetime.now(timezone.utc)
    day = utc_day(instant)
    site_root, dist, reserve_dir, ledger_path = map(Path, (site_root, dist, reserve_dir, ledger_path))
    catalog_path, translations_path = dist / 'js/catalog.js', site_root / 'tools/i18n_data.json'
    try:
        original_catalog = catalog_path.read_bytes()
        original_i18n = translations_path.read_bytes()
        original_ledger = ledger_path.read_bytes()
        catalog = json.loads(original_catalog.decode('utf-8').split('=', 1)[1].strip().removesuffix(';'))
        translations = json.loads(original_i18n)
        if not isinstance(translations.get('products'), dict):
            raise ValueError()
        ledger = read_ledger(ledger_path)
        verify_catalog(ledger, catalog)
        if validation_run_id is None:
            needed = remaining(ledger, day, count)
        else:
            from .daily_ledger import remaining_validation, SEED_DAY
            validation_day = SEED_DAY if validation_run_id in ledger['validation_runs'] else day
            needed = remaining_validation(ledger, validation_day, validation_run_id, now=now)
    except Exception as error:
        raise DailyError(getattr(error, 'code', 'daily_input_invalid')) from None
    if needed == 0:
        return {'added': 0, 'validation_existing': validation_run_id is not None}
    if media_budget == 0:
        raise DailyError('media_budget_exhausted')
    if (instant.astimezone(timezone.utc) + timedelta(minutes=26)).date().isoformat() != day:
        raise DailyError('utc_day_end_window')
    api_holder = []
    def get_api():
        if not api_holder:
            from .search import AliClient
            api_holder.append(AliClient())
        return api_holder[0]
    from . import discovery_curator
    using_default_discover = discover_fn is None
    must_sell_in = required_markets() if using_default_discover else ()
    min_mkts = min_confirmed_markets() if using_default_discover else 0
    if discover_fn is None:
        discover_fn = lambda existing, amount, when: discover(
            get_api(),
            existing,
            amount,
            when,
            use_curated_pool=True,
            check_all_markets=True,
            check_hot_background=True,
            presearch_fn=None,
            preferred_markets=preferred_markets,
            required_markets=must_sell_in,
            min_markets=min_mkts,
        )
    if refresh_fn is None:
        refresh_fn = lambda entry, when: refresh_queued(get_api(), entry, when)
    if queue_store is None:
        queue_file = ledger_path.parent / 'fluxixo_ai.sqlite3'
        if queue_file.is_file():
            from .store import Store
            queue_store = Store(queue_file)
    if media_fn is None:
        media_holder = []
        def media_fn(candidate, internal_id, stage, *, perceptual_index=None):
            if not media_holder:
                media_holder.append(_default_media_preparer())
            return media_holder[0](candidate, internal_id, stage, perceptual_index=perceptual_index)
    strict_copy = (
        _strict_copy_enabled()
        if enforce_unique_copy is None else bool(enforce_unique_copy)
    )
    old = catalog['products']
    review_required = os.environ.get('FLUXIXO_REVIEW_REQUIRED') == '1'
    pending = None
    if review_required:
        from .pending_products import PendingProducts
        from .gemini_client import COPY_POLICY, GeminiDeferred
        from .reviewed_media import MediaDeferred, MediaStopped, verify_review_bindings
        from .copy_revisions import GeminiCopyStopped
        pending = PendingProducts(ledger_path.parent / 'fluxixo_pending.sqlite3')
        pending.reconcile(old)
    def enrich_candidate(record_item, translated, candidate):
        revisions = {}
        if pending and os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
            pid = candidate['product_id']
            journal = pending.copy_state(pid)
            revisions = {'copy_state': journal, 'checkpoint': lambda: pending.save_copy_state(pid, journal)}
        return _maybe_ai_enrich(record_item, translated, candidate, site_root, catalog_corpus=catalog_corpus,
                                snippet_fetcher=snippet_fetcher, **revisions)

    used_hashes = _old_image_hashes(old, dist)
    perceptual_index = image_studio.load_catalog_perceptual_index(
        old, dist, cache_path=site_root / 'tools' / '.image_hash_cache.json',
    )
    catalog_corpus = _load_catalog_copy_corpus(old, translations, site_root)
    pass_perceptual = _media_accepts_perceptual(media_fn)
    exclusions = []
    prepared = []
    attempts = 0
    media_attempts = 0
    owner = 'daily-' + (os.environ.get('GITHUB_RUN_ID') or 'run')
    queue_batch = []
    if queue_store is not None:
        # Cutting three photos per product takes longer; the claim must outlive the build and the push,
        # but a lease may not cross midnight (the store refuses that).
        midnight = datetime.combine(instant.astimezone(timezone.utc).date() + timedelta(days=1), datetime.min.time(), timezone.utc)
        lease = max(300, min(LEASE_SECONDS, int((midnight - instant).total_seconds()) - 120))
        claims = queue_store.claim(day, owner, needed, lease_seconds=lease, now=instant)
        for claim in claims:
            try:
                refreshed = refresh_fn(claim['candidate'], instant)
                refreshed['_queue_claim'] = claim
                queue_batch.append(refreshed)
            except Exception:
                queue_store.release_claim(claim['claim_id'], owner, catalog_unchanged=True, now=instant)
    reserve_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.daily-stage-', dir=reserve_dir) as folder:
        stage = Path(folder).resolve()
        if not stage.is_relative_to(reserve_dir.resolve()):
            raise DailyError('staging_invalid')
        deadline = time.monotonic() + SEARCH_BUDGET_SECONDS
        now_ts = (lambda: time.time()) if now is None else (lambda: instant.timestamp())
        while len(prepared) < needed and attempts < MAX_ATTEMPTS and media_attempts < media_budget and time.monotonic() < deadline:
            resumed = pending.claim(now=now_ts()) if pending else None
            if resumed:
                resumed['_pending_retry'] = True
                batch = [resumed]
            elif queue_batch:
                batch, queue_batch = queue_batch, []
            else:
                # English names let discovery recognise a product type that is already on the site.
                known = [{**p, 'name_en': translations.get('products', {}).get(p.get('id'), {}).get('en', {}).get('name', '')}
                         if isinstance(p, dict) else p for p in old]
                waiting = pending.exclusions() if pending else []
                batch = discover_fn(known + exclusions + waiting + [x[0] for x in prepared], needed - len(prepared), instant)
            if not batch:
                break
            progress = False
            for candidate in batch:
                if len(prepared) >= needed or attempts >= MAX_ATTEMPTS or media_attempts >= media_budget or time.monotonic() >= deadline:
                    break
                attempts += 1
                pid = str(candidate.get('product_id', ''))
                queue_claim = candidate.get('_queue_claim')
                if pending:
                    parked = pending.terminal_info(candidate['product_id'])
                    if parked:
                        # Natural discovery excludes parked IDs. Only an explicit fresh submission
                        # can compare new seller evidence and reopen a previously stopped candidate.
                        if not queue_claim:
                            continue
                        try:
                            reopened = _reconsider_source(pending, candidate, parked, reserve_dir, now=now_ts())
                        except (MediaDeferred, ValueError, OSError):
                            reopened = False
                        if not reopened:
                            queue_store.fail(queue_claim['claim_id'], owner, 'source_review_stopped', now=instant)
                            continue
                    if not candidate.get('_pending_retry') and not pending.is_due(candidate['product_id'], now=now_ts()):
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    if candidate.get('_pending_retry') and using_default_discover:
                        try:
                            refresh_mkts = candidate.get('availableMarkets') or must_sell_in or discovery_curator.ALL_MARKETS
                            candidate = refresh_fn({**candidate, 'markets': {m: {} for m in refresh_mkts}}, instant)
                        except Exception:
                            pending.defer(candidate['product_id'], 'source_refresh_unavailable', now=now_ts())
                            continue
                    pending.put(candidate, now=now_ts())
                record_item, translated = build_record(candidate)
                if any(p.get('id') == record_item['id'] or p.get('sourceProductId') == record_item['sourceProductId']
                       or (record_item.get('sourceModelKey') and p.get('sourceModelKey') == record_item['sourceModelKey'])
                       or (record_item.get('sourceImageUrl') and p.get('sourceImageUrl') == record_item['sourceImageUrl'])
                       for p in old + exclusions + [x[0] for x in prepared]):
                    if queue_claim:
                        queue_store.fail(queue_claim['claim_id'], owner, 'duplicate_existing', now=instant)
                    if pending and any(p.get('sourceProductId') == record_item['sourceProductId'] for p in old):
                        pending.complete(candidate['product_id'])
                    continue
                exclusions.append({'id': record_item['id'], 'sourceProductId': record_item['sourceProductId'], 'sourceTitle': record_item['sourceTitle']})
                if pending:
                    pending.hold(candidate['product_id'], now=now_ts())
                avail_now = set(candidate.get('availableMarkets') or ())
                if (must_sell_in and not set(must_sell_in) <= avail_now) or (min_mkts and len(avail_now) < min_mkts):
                    # A queued candidate was found before this rule: check every country now, before any image work.
                    try:
                        discovery_curator.verify_markets_for_candidate(
                            get_api(), candidate, discovery_curator.ALL_MARKETS, instant.astimezone(timezone.utc).isoformat())
                    except Exception:
                        pass
                    avail_now = set(candidate.get('availableMarkets') or ())
                    if (must_sell_in and not set(must_sell_in) <= avail_now) or (min_mkts and len(avail_now) < min_mkts):
                        if queue_claim:
                            queue_store.fail(queue_claim['claim_id'], owner, 'markets_incomplete', now=instant)
                        if pending:
                            pending.defer(candidate['product_id'], 'markets_incomplete', now=now_ts())
                        continue
                    record_item['availableMarkets'] = list(candidate['availableMarkets'])
                if review_required:
                    print(f'[prepare] candidate={pid} attempt={attempts}/{MAX_ATTEMPTS} prepared={len(prepared)}/{needed}', flush=True)
                try:
                    if strict_copy:
                        # Reject untranslated or duplicated copy before spending
                        # one of the day's limited image-product attempts.
                        cached_copy = pending.text(candidate['product_id']) if pending else None
                        if cached_copy and cached_copy.get('policy') == COPY_POLICY:
                            record_item.update(cached_copy['record'])
                            translated = cached_copy['translated']
                        else:
                            record_item, translated = enrich_candidate(record_item, translated, candidate)
                        problems = _copy_validation_problems(record_item, translated, site_root,
                                                             catalog_corpus=catalog_corpus, reject_placeholders=True)
                        reason = 'copy_validation_failed'
                        if not problems and os.environ.get('FLUXIXO_WEB_CHECK_PROVIDER', '').strip().lower() in ('tavily_keyless', 'tavily_free'):
                            problems = _bind_external_originality(record_item, translated, site_root)
                            reason = 'copy_external_overlap'
                        if problems:
                            if review_required:
                                print(f'[prepare] candidate={pid} copy_rejected reason={reason} count={len(problems)}', flush=True)
                            if pending:
                                pid = candidate['product_id']
                                pending.save_text(pid, None)
                                if os.environ.get('FLUXIXO_TEXT_PROVIDER') == 'gemini':
                                    from .copy_revisions import reject_cached_copy
                                    journal = pending.copy_state(pid)
                                    reject_cached_copy(candidate['title'], journal,
                                                       lambda: pending.save_copy_state(pid, journal), reason=reason, problems=problems)
                                pending.defer(pid, reason, now=now_ts())
                            if queue_claim:
                                queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                            continue
                        if pending:
                            pending.save_text(candidate['product_id'], {
                                'policy': COPY_POLICY,
                                'record': {k: record_item[k] for k in ('name', 'headline', 'description', 'details', '_ru_long') if k in record_item},
                                'translated': translated,
                            })
                        if review_required:
                            print(f'[prepare] candidate={pid} copy_verified -> media_review', flush=True)
                    media_attempts += 1
                    media = (
                        media_fn(candidate, record_item['id'], stage, perceptual_index=perceptual_index)
                        if pass_perceptual else media_fn(candidate, record_item['id'], stage)
                    )
                    if review_required:
                        if not verify_review_bindings(media):
                            raise MediaDeferred('review_binding_invalid')
                        record_item['mediaReview'] = media['media_review']
                        record_item['mediaReviewRequired'] = True
                    if (not isinstance(media, dict) or not all(isinstance(media.get(k), str) and re.fullmatch(r'[0-9a-f]{64}', media[k]) for k in ('source_sha256', 'pixel_sha256'))
                            or media['source_sha256'] in used_hashes or media['pixel_sha256'] in used_hashes):
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    views = media.get('views') or []
                    if not isinstance(views, list) or len(views) > PHOTOS_PER_PRODUCT - 1:
                        raise DailyError('staging_invalid')
                    media_paths = [media['image'], media['original'], *views]
                    if review_required:
                        media_paths.extend([media['identity_source'], *media['review_sources']])
                    for path in media_paths:
                        path = Path(path).resolve()
                        allowed = path.is_relative_to(stage) or (review_required and path.is_relative_to((reserve_dir / 'reviewed-media').resolve()))
                        if not allowed or not path.is_file():
                            raise DailyError('staging_invalid')
                    cand_perceptual = _extract_media_perceptual(media)
                    if any(
                        image_studio.is_perceptually_duplicate(cand_hashes, perceptual_index)[0]
                        for cand_hashes in cand_perceptual.values()
                    ):
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    if views:
                        record_item['views'] = [f'assets/images/{record_item["id"]}-v{n}.webp' for n in range(2, len(views) + 2)]
                    record_item['sourceImageSha256'] = media['source_sha256']
                    record_item['sourcePixelSha256'] = media['pixel_sha256']
                    record_item['sourceImageUrl'] = media.get('source_url', candidate['image_url'])
                    if 'image' in cand_perceptual:
                        record_item['imageDhash'] = cand_perceptual['image']['dhash']
                        record_item['imageAhash'] = cand_perceptual['image']['ahash']
                        if cand_perceptual['image'].get('aspect'):
                            record_item['imageAspect'] = cand_perceptual['image']['aspect']
                    if 'original' in cand_perceptual:
                        record_item['sourceImageDhash'] = cand_perceptual['original']['dhash']
                        record_item['sourceImageAhash'] = cand_perceptual['original']['ahash']
                    if media.get('image_quality_verified') is not None:
                        record_item['imageQualityVerified'] = bool(media['image_quality_verified'])
                    if isinstance(media.get('image_quality'), dict):
                        record_item['imageQualityMetrics'] = media['image_quality']
                    if queue_claim:
                        record_item['sourceQueueRequestId'] = queue_claim['request_id']
                        record_item['sourceQueueClaimId'] = queue_claim['claim_id']
                        record_item['sourceQueueOwner'] = owner
                    if not strict_copy:
                        record_item, translated = enrich_candidate(record_item, translated, candidate)
                    used_hashes.update((media['source_sha256'], media['pixel_sha256']))
                    for kind_name, cand_hashes in cand_perceptual.items():
                        perceptual_index.append({'id': record_item['id'], 'path': kind_name, 'kind': kind_name, **cand_hashes})
                    if catalog_corpus is not None:
                        try:
                            _, co_mod = _import_tools_modules(site_root)
                            co_mod.append_bundle_to_corpus(
                                catalog_corpus,
                                record_item['id'],
                                {'ru': {'name': record_item['name'], 'headline': record_item['headline'], 'description': record_item['description']}, **translated},
                            )
                        except Exception:
                            pass
                    prepared.append((record_item, translated, media))
                    if review_required:
                        print(f'[prepare] candidate={pid} ACCEPTED ({len(prepared)}/{needed})', flush=True)
                    progress = True
                except Exception as error:
                    if pending and isinstance(error, (GeminiCopyStopped, MediaStopped)):
                        kind = 'copy' if isinstance(error, GeminiCopyStopped) else 'media'
                        print(f'[prepare] candidate={pid} PARKED kind={kind} reason={error.reason}', flush=True)
                        pending.park(candidate['product_id'], error.reason, kind=kind,
                                     source_version=error.source_version, now=now_ts())
                        if queue_claim:
                            queue_store.fail(queue_claim['claim_id'], owner, 'source_review_stopped', now=instant)
                        continue
                    if pending and isinstance(error, (GeminiDeferred, MediaDeferred)):
                        print(f'[prepare] candidate={pid} DEFERRED code={error.code}', flush=True)
                        pending.defer(candidate['product_id'], error.code, retry_at=error.retry_at, now=now_ts())
                        if queue_claim:
                            queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                        continue
                    if not isinstance(error, DailyError):
                        raise
                    if str(error) in ('ocr_unavailable', 'image_processor_unavailable'):
                        raise
                    if pending:
                        pending.defer(candidate['product_id'], str(error), now=instant.timestamp())
                    if queue_claim:
                        queue_store.release_claim(queue_claim['claim_id'], owner, catalog_unchanged=True, now=instant)
                    continue
            if not progress and attempts >= MAX_ATTEMPTS:
                break
        if review_required and not prepared:
            return {'added': 0, 'ids': [], 'deferred': True}
        if len(prepared) < needed and not review_required:
            if raw_media_budget is not None and media_attempts >= media_budget:
                raise DailyError('media_budget_exhausted')
            raise DailyError('underfilled_no_publication')
        from . import discovery_curator
        gate_ok, gate_errors = discovery_curator.pre_deploy_catalog_gate(
            [p[0] for p in prepared],
            old,
            require_markets=using_default_discover,
            translations={p[0]['id']: p[1] for p in prepared},
        )
        if not gate_ok:
            raise DailyError('pre_deploy_gate_failed:' + ','.join(gate_errors[:4]))
        fresh_catalog = dict(catalog)
        ru_long_entries = {}
        prepared_clean = []
        for product, lang, media in prepared:
            prod_copy = dict(product)
            ru_long = prod_copy.pop('_ru_long', None)
            if isinstance(ru_long, dict) and ru_long.get('who') and ru_long.get('check'):
                ru_long_entries[prod_copy['id']] = ru_long
            prepared_clean.append((prod_copy, lang, media))
        prepared = prepared_clean
        fresh_catalog['products'] = [p[0] for p in prepared] + old
        fresh_i18n = dict(translations)
        fresh_i18n['products'] = dict(translations['products'])
        for product, lang, _ in prepared:
            fresh_i18n['products'][product['id']] = lang
        long_ru_path = site_root / 'tools/ru_long_copy.json'
        original_long_ru = long_ru_path.read_bytes() if long_ru_path.is_file() else None
        rows = [{'catalog_id': p['id'], 'product_id': p['sourceProductId'], 'source': 'api'} for p, _, _ in prepared]
        if validation_run_id is None:
            next_ledger = record(ledger, day, rows)
        else:
            from .daily_ledger import record_validation
            next_ledger = record_validation(ledger, day, validation_run_id, rows[0], now=now)
        verify_catalog(next_ledger, fresh_catalog)
        if now is None and utc_day() != day:
            raise DailyError('utc_day_changed_before_write')
        created = []
        try:
            for product, _, media in prepared:
                copies = [(media['image'], dist / 'assets/images' / (product['id'] + '.webp')),
                          (media['original'], dist / 'assets/originals' / (product['id'] + '.webp'))]
                copies += [(view, dist / relative) for view, relative in zip(media.get('views') or [], product.get('views', []))]
                if review_required:
                    if not verify_review_bindings(media):
                        raise DailyError('review_binding_changed_before_commit')
                    copies.append((media['identity_source'], dist / media['media_review']['identity_source_asset']))
                    copies += [(source, dist / frame['source_asset']) for source, frame in
                               zip(media['review_sources'], media['media_review']['frames'])]
                for source_path, target in copies:
                    target = target.resolve()
                    if not target.is_relative_to(dist.resolve()):
                        raise DailyError('asset_path_invalid')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with Path(source_path).open('rb') as src, target.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
                    created.append(target)
            text = '/* FLUXIXO catalog: existing collection + daily accumulated finds. */\nwindow.MIRA_CATALOG = ' + json.dumps(fresh_catalog, ensure_ascii=False, indent=2) + ';\n'
            _atomic_bytes(catalog_path, text.encode('utf-8'))
            _atomic_bytes(translations_path, (json.dumps(fresh_i18n, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            if ru_long_entries and long_ru_path.parent.is_dir():
                existing_long = json.loads(original_long_ru.decode('utf-8')) if original_long_ru else {}
                existing_long.update(ru_long_entries)
                _atomic_bytes(long_ru_path, (json.dumps(existing_long, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            atomic_write(ledger_path, next_ledger)
        except Exception:
            _atomic_bytes(catalog_path, original_catalog)
            _atomic_bytes(translations_path, original_i18n)
            if original_long_ru is not None:
                _atomic_bytes(long_ru_path, original_long_ru)
            _atomic_bytes(ledger_path, original_ledger)
            for target in created:
                if target.is_relative_to(dist.resolve()):
                    target.unlink(missing_ok=True)
            raise DailyError('daily_write_failed') from None
    print('Historical product IDs are incomplete; exact old-item deduplication cannot be guaranteed.')
    return {'added': len(prepared), 'ids': [p[0]['id'] for p in prepared]}


def mark_queued_committed(catalog, queue_store, ids, commit_sha, *, verify_commit, now=None):
    """Mark only products present in the verified pushed catalog commit."""
    if (not isinstance(commit_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', commit_sha)
            or not callable(verify_commit) or verify_commit(commit_sha) is not True
            or not isinstance(catalog, dict) or not isinstance(catalog.get('products'), list)
            or not isinstance(ids, list) or len(ids) > 3 or len(set(ids)) != len(ids)):
        raise DailyError('commit_unconfirmed')
    products = {p.get('id'): p for p in catalog['products'] if isinstance(p, dict)}
    marked = []
    for internal_id in ids:
        item = products.get(internal_id)
        if item is None:
            raise DailyError('commit_catalog_mismatch')
        request = item.get('sourceQueueRequestId')
        if not request:
            continue
        status = queue_store.status(request)
        if (not status or status['product_id'] != item.get('sourceProductId')
                or status['claim_id'] != item.get('sourceQueueClaimId')
                or status['owner'] != item.get('sourceQueueOwner')):
            raise DailyError('queue_commit_mismatch')
        if status['state'] == 'reserved':
            queue_store.mark_committed(status['claim_id'], status['owner'], commit_sha, verified=True, now=now)
            marked.append(request)
        elif status['state'] not in ('committed', 'published'):
            raise DailyError('queue_commit_mismatch')
    return marked


def _verify_remote_head(commit_sha):
    try:
        local = subprocess.run(['git','rev-parse','HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=True, timeout=20).stdout.decode('ascii').strip()
        remote = subprocess.run(['git','ls-remote','--heads','origin','refs/heads/main'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=True, timeout=45).stdout.decode('ascii').strip()
        return local == commit_sha and remote == commit_sha + '\trefs/heads/main'
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return False


def _reconsider_source(pending, candidate, parked, reserve_dir, *, now=None):
    from .copy_revisions import copy_source_version
    from .reviewed_media import verified_media_source_version

    pid = candidate['product_id']
    if not re.fullmatch(r'[1-9][0-9]{0,31}', pid):
        raise ValueError('invalid_product_id')
    if parked['kind'] == 'copy':
        version = copy_source_version(candidate['title'])
    else:
        path = Path(reserve_dir) / 'reviewed-media' / ('auto-' + pid) / 'state.json'
        version = verified_media_source_version(candidate, state_path=path)
    return pending.reconsider(pid, source_version=version, now=now)


def main():
    import argparse
    from .store import Store
    parser = argparse.ArgumentParser(description='Manage daily product queue state')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--mark-committed')
    action.add_argument('--reconsider-product', metavar='SELLER_ID', help='Compare fresh seller evidence for one stopped product')
    parser.add_argument('--ids', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.reconsider_product:
        from .pending_products import PendingProducts
        from .search import AliClient
        pending = PendingProducts(root / 'data/fluxixo_pending.sqlite3')
        pid = args.reconsider_product
        stored = pending.parked_candidate(pid)
        if not stored:
            print('No stopped product with that ID.')
            return
        markets = stored.get('availableMarkets') or [stored.get('market') or 'US']
        fresh = refresh_queued(AliClient(), {**stored, 'markets': dict.fromkeys(markets)}, datetime.now(timezone.utc))
        reopened = _reconsider_source(pending, fresh, pending.terminal_info(pid), root / 'fluxixo_site/reserve')
        print('Queued for ordinary preparation.' if reopened else 'Already considered this seller material.')
        return
    db_path = root / 'data/fluxixo_ai.sqlite3'
    ids = [item for item in args.ids.split(',') if item]
    if not ids or not db_path.is_file():
        print('No queued product status to update.')
        return
    try:
        text = (root / 'fluxixo_site/dist/js/catalog.js').read_text(encoding='utf-8')
        catalog = json.loads(text.split('=', 1)[1].strip().removesuffix(';'))
        marked = mark_queued_committed(catalog, Store(db_path), ids, args.mark_committed, verify_commit=_verify_remote_head)
        print(f'Queue entries recorded as committed: {len(marked)}; publication not yet asserted.')
    except Exception:
        raise SystemExit('Queue commit verification failed; deployment stopped.') from None


if __name__ == '__main__':
    main()
