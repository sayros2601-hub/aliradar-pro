"""Copy originality, seller-title anti-mirroring, catalog similarity & optional snippet verification.

Pure Python standard library (zero external packages) so CI and offline tests
run deterministically with no network dependency.
"""
from __future__ import annotations

from collections import Counter
import json
import math
import os
import re
from typing import Any, Callable, Sequence
import urllib.error
import urllib.parse
import urllib.request

LANGS = ('ru', 'en', 'pt', 'es', 'fr', 'he')

STOPWORDS: dict[str, frozenset[str]] = {
    'en': frozenset({
        'a', 'an', 'and', 'as', 'at', 'by', 'for', 'from', 'in', 'into', 'is',
        'it', 'of', 'on', 'or', 'that', 'the', 'to', 'with', 'your', 'you',
    }),
    'ru': frozenset({
        'и', 'в', 'во', 'на', 'с', 'со', 'к', 'ко', 'по', 'для', 'из', 'от',
        'до', 'у', 'о', 'об', 'не', 'но', 'а', 'или', 'при', 'под', 'над',
        'без', 'перед', 'про', 'же', 'ли', 'для',
    }),
    'pt': frozenset({
        'a', 'o', 'as', 'os', 'um', 'uma', 'de', 'do', 'da', 'dos', 'das',
        'em', 'no', 'na', 'nos', 'nas', 'para', 'por', 'com', 'sem', 'e', 'ou',
        'que', 'seu', 'sua',
    }),
    'es': frozenset({
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del',
        'al', 'en', 'con', 'sin', 'por', 'para', 'y', 'o', 'que', 'su', 'tu',
    }),
    'fr': frozenset({
        'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'd', 'au', 'aux',
        'en', 'a', 'pour', 'par', 'avec', 'sans', 'et', 'ou', 'sur', 'dans', 'votre',
    }),
    'he': frozenset({
        'של', 'עם', 'את', 'על', 'אל', 'מן', 'גם', 'או', 'כי', 'אם', 'לא',
        'זה', 'זו', 'זאת', 'לפי', 'כדי', 'לפני', 'אחרי', 'בין', 'תוך',
    }),
}
_ALL_STOPWORDS = frozenset().union(*STOPWORDS.values())

_WORD_RE = re.compile(r"[0-9A-Za-z\u00c0-\u024f\u0400-\u04ff\u05d0-\u05ea]+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_LATIN_WORD_RE = re.compile(r"[A-Za-z\u00c0-\u024f]{2,}")

DEFAULT_CATALOG_THRESHOLDS: dict[str, tuple[float, float, int]] = {
    'name': (0.55, 0.78, 5),
    'headline': (0.60, 0.80, 5),
    'description': (0.40, 0.72, 6),
}

SnippetFetcher = Callable[[str, str, float], list[dict[str, str]]]


def _flatten(val: Any) -> str:
    if isinstance(val, (list, tuple)):
        return ' '.join(str(x) for x in val if x)
    return str(val or '')


def normalize_copy_text(text: str) -> str:
    """Normalize text for stable cross-variant copy comparison."""
    import unicodedata

    raw = unicodedata.normalize('NFKC', _flatten(text))
    raw = _URL_RE.sub(' ', raw)
    raw = _HTML_TAG_RE.sub(' ', raw)
    raw = raw.replace('\u05be', ' ').replace('’', ' ').replace("'", ' ')
    # Keep letters, digits and spaces across all 6 target alphabets.
    tokens = _WORD_RE.findall(raw.casefold())
    return ' '.join(tokens)


def _strip_accents(text: str) -> str:
    import unicodedata

    return ''.join(
        ch for ch in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(ch)
    )


def tokenize_meaningful(
    text: str,
    lang: str | None = None,
    *,
    drop_stopwords: bool = True,
    fold_accents: bool = False,
) -> list[str]:
    """Extract normalized meaningful word tokens across Latin, Cyrillic and Hebrew."""
    norm = normalize_copy_text(text)
    if fold_accents:
        norm = _strip_accents(norm)
    stops = STOPWORDS.get(lang, _ALL_STOPWORDS) if drop_stopwords else frozenset()
    out: list[str] = []
    for tok in norm.split():
        if len(tok) < 2 and not tok.isdigit():
            continue
        if drop_stopwords and tok in stops:
            continue
        out.append(tok)
    return out


def word_shingles(tokens: Sequence[str], k: int = 3) -> set[tuple[str, ...]]:
    """Build sliding k-word shingles with bounded k for shorter strings."""
    if not tokens or k <= 0:
        return set()
    eff_k = min(k, len(tokens))
    return {tuple(tokens[i:i + eff_k]) for i in range(len(tokens) - eff_k + 1)}


def char_ngrams(text: str, n: int = 4) -> dict[str, int]:
    """Character n-gram frequency dict over normalized text."""
    norm = normalize_copy_text(text)
    if not norm or n <= 0:
        return {}
    if len(norm) < n:
        return {norm: 1}
    counts = Counter(norm[i:i + n] for i in range(len(norm) - n + 1))
    return dict(counts)


def _vec_norm(vec: dict[str, int]) -> float:
    return math.sqrt(sum(v * v for v in vec.values()))


def _vector_cosine(
    va: dict[str, int],
    norm_a: float,
    vb: dict[str, int],
    norm_b: float,
) -> float:
    if not norm_a or not norm_b:
        return 0.0
    if len(va) > len(vb):
        va, vb = vb, va
    dot = sum(cnt * vb.get(gram, 0) for gram, cnt in va.items())
    return dot / (norm_a * norm_b)


def shingle_jaccard(
    text_a: str,
    text_b: str,
    *,
    lang: str | None = None,
    k: int = 3,
    fold_accents: bool = False,
) -> float:
    """Jaccard similarity over shared word shingles."""
    ta = tokenize_meaningful(text_a, lang, fold_accents=fold_accents)
    tb = tokenize_meaningful(text_b, lang, fold_accents=fold_accents)
    if not ta or not tb:
        return 0.0
    eff_k = min(k, len(ta), len(tb))
    sa = word_shingles(ta, k=eff_k)
    sb = word_shingles(tb, k=eff_k)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def ngram_cosine(text_a: str, text_b: str, *, n: int = 4) -> float:
    """Cosine similarity between character n-gram vectors."""
    va = char_ngrams(text_a, n=n)
    vb = char_ngrams(text_b, n=n)
    return _vector_cosine(va, _vec_norm(va), vb, _vec_norm(vb))


def longest_common_token_run(tokens_a: Sequence[str], tokens_b: Sequence[str]) -> int:
    """Length of longest contiguous shared run between two token sequences."""
    if not tokens_a or not tokens_b:
        return 0
    best = 0
    prev = [0] * (len(tokens_b) + 1)
    for ta in tokens_a:
        cur = [0] * (len(tokens_b) + 1)
        for j, tb in enumerate(tokens_b, 1):
            if ta == tb:
                run = prev[j - 1] + 1
                cur[j] = run
                if run > best:
                    best = run
        prev = cur
    return best


def check_source_title_mirroring(
    bundle: dict[str, dict[str, Any]],
    source_title: str,
    *,
    max_contiguous_words: int = 4,
    max_shingle_jaccard: float = 0.45,
    max_char_cosine: float = 0.62,
) -> list[str]:
    """Reject locale bundles that mirror the raw seller listing title verbatim or nearly verbatim."""
    if not isinstance(source_title, str) or not source_title.strip():
        return []
    src_norm = normalize_copy_text(source_title)
    src_tokens = tokenize_meaningful(source_title, 'en', drop_stopwords=True, fold_accents=True)
    if not src_tokens:
        return []
    src_norm_folded = _strip_accents(src_norm)
    src_vec = char_ngrams(src_norm_folded, n=4)
    src_vec_norm = _vec_norm(src_vec)

    problems: list[str] = []
    for lang, fields in (bundle or {}).items():
        if not isinstance(fields, dict):
            continue
        for fname in ('name', 'headline', 'description'):
            raw_val = _flatten(fields.get(fname, ''))
            if not raw_val.strip():
                continue
            norm_val = normalize_copy_text(raw_val)
            if not norm_val:
                continue
            cand_folded = _strip_accents(norm_val)
            cand_tokens = tokenize_meaningful(raw_val, lang, drop_stopwords=True, fold_accents=True)
            if not cand_tokens:
                continue

            # Exact or full substring mirror of meaningful source title (when title >= 12 chars)
            if len(src_norm_folded) >= 12 and (
                cand_folded == src_norm_folded or src_norm_folded in cand_folded
            ):
                problems.append(f'{lang}.{fname}: mirrors source_title verbatim')
                continue

            # Contiguous overlapping meaningful-word run check across ALL scripts (catches leaked EN chunks)
            run = longest_common_token_run(cand_tokens, src_tokens)
            # Filter out if run only reflects tiny short-code match; >=4 contiguous tokens is mirroring
            if run >= max_contiguous_words:
                problems.append(
                    f'{lang}.{fname}: mirrors {run} contiguous source_title words'
                )
                continue

            # Shingle + character n-gram gates for Latin scripts or Latin-heavy lines in ru/he
            is_latin_locale = lang in ('en', 'pt', 'es', 'fr')
            latin_words = _LATIN_WORD_RE.findall(raw_val)
            if fname in ('name', 'description') and (is_latin_locale or len(latin_words) >= 4):
                eff_k = min(3, len(cand_tokens), len(src_tokens))
                jacc = 0.0
                if eff_k >= 2:
                    sa = word_shingles(cand_tokens, k=eff_k)
                    sb = word_shingles(src_tokens, k=eff_k)
                    if sa and sb:
                        jacc = len(sa & sb) / len(sa | sb)
                cand_vec = char_ngrams(cand_folded, n=4)
                cos = _vector_cosine(cand_vec, _vec_norm(cand_vec), src_vec, src_vec_norm)
                # Slightly tighter threshold specifically for English to ensure genuine rewrite
                jacc_limit = max_shingle_jaccard * (0.85 if lang == 'en' else 1.15)
                cos_limit = max_char_cosine if lang == 'en' else min(0.82, max_char_cosine + 0.14)
                if jacc > jacc_limit or cos > cos_limit:
                    problems.append(
                        f'{lang}.{fname}: too close to source_title '
                        f'(shingle={jacc:.2f}, cosine={cos:.2f})'
                    )
    return problems


def _index_entry(entry_id: str, text: str, lang: str) -> dict[str, Any] | None:
    norm = normalize_copy_text(text)
    if not norm:
        return None
    tokens = tokenize_meaningful(text, lang, drop_stopwords=True)
    shingles = word_shingles(tokens, k=3)
    ngrams = char_ngrams(norm, n=4)
    return {
        'id': entry_id,
        'text': _flatten(text),
        'norm': norm,
        'tokens': tokens,
        'shingles': shingles,
        'ngrams': ngrams,
        'vec_norm': _vec_norm(ngrams),
    }


def _infer_route_lang(path: str) -> str:
    m = re.match(r'^/(en|pt|es|fr|he)(?:/|$)', path or '')
    return m.group(1) if m else 'ru'


def build_catalog_copy_corpus(
    products: Sequence[dict[str, Any]],
    i18n: dict[str, Any] | None = None,
    *,
    extra_routes: dict[str, dict[str, Any]] | None = None,
    exclude_ids: set[str] | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Pre-index all catalog copy across all 6 languages plus optional SEO overrides."""
    corpus: dict[str, dict[str, list[dict[str, Any]]]] = {
        lang: {'name': [], 'headline': [], 'description': []} for lang in LANGS
    }
    excluded = exclude_ids or set()
    i18n_products = (i18n or {}).get('products') or {}
    seen_ids: set[str] = set()

    for item in products or ():
        if item.get('demo'):
            continue
        pid = item.get('id')
        if not pid or pid in excluded:
            continue
        seen_ids.add(pid)
        for field in ('name', 'headline', 'description'):
            entry = _index_entry(pid, _flatten(item.get(field, '')), 'ru')
            if entry:
                corpus['ru'][field].append(entry)
        tr = i18n_products.get(pid) or {}
        for lang in ('en', 'pt', 'es', 'fr', 'he'):
            loc = tr.get(lang)
            if not isinstance(loc, dict):
                continue
            for field in ('name', 'headline', 'description'):
                entry = _index_entry(pid, _flatten(loc.get(field, '')), lang)
                if entry:
                    corpus[lang][field].append(entry)

    for pid, tr in i18n_products.items():
        if pid in seen_ids or pid in excluded or not isinstance(tr, dict):
            continue
        for lang in ('en', 'pt', 'es', 'fr', 'he'):
            loc = tr.get(lang)
            if not isinstance(loc, dict):
                continue
            for field in ('name', 'headline', 'description'):
                entry = _index_entry(pid, _flatten(loc.get(field, '')), lang)
                if entry:
                    corpus[lang][field].append(entry)

    for route, meta in (extra_routes or {}).items():
        if not isinstance(meta, dict):
            continue
        lang = _infer_route_lang(route)
        if meta.get('title'):
            entry = _index_entry(f'route:{route}', meta['title'], lang)
            if entry:
                corpus[lang]['name'].append(entry)
        if meta.get('description'):
            entry = _index_entry(f'route:{route}', meta['description'], lang)
            if entry:
                corpus[lang]['description'].append(entry)

    return corpus


def append_bundle_to_corpus(
    corpus: dict[str, dict[str, list[dict[str, Any]]]],
    entry_id: str,
    bundle: dict[str, dict[str, Any]],
) -> None:
    """Incrementally register a newly accepted product bundle into an active corpus."""
    for lang, loc in (bundle or {}).items():
        if lang not in corpus or not isinstance(loc, dict):
            continue
        for field in ('name', 'headline', 'description'):
            entry = _index_entry(entry_id, _flatten(loc.get(field, '')), lang)
            if entry:
                corpus[lang][field].append(entry)


def check_catalog_similarity(
    bundle: dict[str, dict[str, Any]],
    corpus: dict[str, dict[str, list[dict[str, Any]]]] | None,
    *,
    thresholds: dict[str, tuple[float, float, int]] | None = None,
) -> list[str]:
    """Detect exact or near-duplicate copy against indexed catalog entries."""
    if not corpus:
        return []
    limits = thresholds or DEFAULT_CATALOG_THRESHOLDS
    problems: list[str] = []
    for lang, fields in (bundle or {}).items():
        if lang not in corpus or not isinstance(fields, dict):
            continue
        for fname in ('name', 'headline', 'description'):
            raw = _flatten(fields.get(fname, ''))
            norm = normalize_copy_text(raw)
            if not norm:
                continue
            tokens = tokenize_meaningful(raw, lang, drop_stopwords=True)
            ngrams = char_ngrams(norm, n=4)
            vnorm = _vec_norm(ngrams)
            max_jacc, max_cos, max_run = limits.get(fname, (0.45, 0.75, 6))

            for entry in corpus[lang].get(fname, ()):
                if norm == entry['norm']:
                    problems.append(
                        f'{lang}.{fname}: duplicate {fname} already used by {entry["id"]}'
                    )
                    break
                run = longest_common_token_run(tokens, entry['tokens'])
                if run >= max_run:
                    problems.append(
                        f'{lang}.{fname}: shares {run}-word phrase with {entry["id"]}'
                    )
                    break
                eff_k = min(3, len(tokens), len(entry['tokens']))
                jacc = 0.0
                if eff_k >= 2:
                    sa = word_shingles(tokens, k=eff_k)
                    sb = word_shingles(entry['tokens'], k=eff_k) if eff_k != 3 else entry['shingles']
                    if sa and sb:
                        jacc = len(sa & sb) / len(sa | sb)
                cos = _vector_cosine(ngrams, vnorm, entry['ngrams'], entry['vec_norm'])
                if jacc >= max_jacc or cos >= max_cos:
                    problems.append(
                        f'{lang}.{fname}: near-duplicate of {entry["id"]} '
                        f'(shingle={jacc:.2f}, cosine={cos:.2f})'
                    )
                    break
    return problems


def _is_self_domain(url: str) -> bool:
    try:
        host = (urllib.parse.urlsplit(url or '').hostname or '').lower()
    except ValueError:
        return False
    return host == 'fluxixo.shop' or host.endswith('.fluxixo.shop') or host.startswith('fluxixo.')


def _serper_fetcher(api_key: str) -> SnippetFetcher:
    def _fetch(query: str, lang: str, timeout_s: float) -> list[dict[str, str]]:
        body = json.dumps({'q': query, 'hl': lang, 'num': 5}).encode('utf-8')
        req = urllib.request.Request(
            'https://google.serper.dev/search',
            data=body,
            headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode('utf-8', 'replace'))
        return [
            {
                'url': str(item.get('link', '')),
                'title': str(item.get('title', '')),
                'snippet': str(item.get('snippet', '')),
            }
            for item in (payload.get('organic') or [])
            if isinstance(item, dict)
        ]

    return _fetch


def _google_cse_fetcher(api_key: str, cx: str) -> SnippetFetcher:
    def _fetch(query: str, lang: str, timeout_s: float) -> list[dict[str, str]]:
        qs = urllib.parse.urlencode({
            'key': api_key,
            'cx': cx,
            'q': query,
            'lr': f'lang_{lang}',
            'num': 5,
        })
        req = urllib.request.Request(
            f'https://www.googleapis.com/customsearch/v1?{qs}',
            method='GET',
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode('utf-8', 'replace'))
        return [
            {
                'url': str(item.get('link', '')),
                'title': str(item.get('title', '')),
                'snippet': str(item.get('snippet', '')),
            }
            for item in (payload.get('items') or [])
            if isinstance(item, dict)
        ]

    return _fetch


def _resolve_env_snippet_fetcher() -> SnippetFetcher | None:
    if str(os.environ.get('FLUXIXO_WEB_CHECK', '')).strip().lower() not in ('1', 'true', 'yes'):
        return None
    serper_key = (os.environ.get('SERPER_API_KEY') or '').strip()
    if serper_key:
        return _serper_fetcher(serper_key)
    cse_key = (os.environ.get('GOOGLE_CSE_KEY') or '').strip()
    cse_cx = (os.environ.get('GOOGLE_CSE_CX') or '').strip()
    if cse_key and cse_cx:
        return _google_cse_fetcher(cse_key, cse_cx)
    return None


def verify_snippet_uniqueness(
    candidates: Sequence[tuple[str, str]],
    *,
    lang: str = 'en',
    snippet_fetcher: SnippetFetcher | None = None,
    max_snippet_shingle: float = 0.45,
    max_snippet_cosine: float = 0.70,
    min_exact_phrase_words: int = 6,
    timeout_s: float = 4.0,
    fail_on_network_error: bool = False,
    cache: dict[str, list[dict[str, str]]] | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Optionally verify copy against external public search snippets without breaking offline CI."""
    if str(os.environ.get('FLUXIXO_OFFLINE', '')).strip().lower() in ('1', 'true', 'yes'):
        return True, [], {'skipped': 'offline'}

    fetcher = snippet_fetcher if snippet_fetcher is not None else _resolve_env_snippet_fetcher()
    if fetcher is None:
        return True, [], {'skipped': 'disabled_or_unconfigured'}

    queries_run = 0
    issues: list[str] = []
    seen_texts: set[str] = set()
    for field_name, text in candidates or ():
        clean = ' '.join(str(text or '').split())
        if not clean or clean in seen_texts:
            continue
        seen_texts.add(clean)
        if queries_run >= 2:
            break
        # Keep search queries compact and focused (up to first 12 words).
        query = f'"{ " ".join(clean.split()[:12]) }"'
        cache_key = f'{lang}:{query}'
        if cache is not None and cache_key in cache:
            results = cache[cache_key]
        else:
            try:
                results = fetcher(query, lang, timeout_s)
                queries_run += 1
            except Exception as exc:
                if fail_on_network_error:
                    return False, [f'{lang}.{field_name}: snippet check error ({type(exc).__name__})'], {'error': str(exc)[:160]}
                return True, [], {'skipped': 'network_error', 'error': str(exc)[:160]}
            if cache is not None:
                cache[cache_key] = results

        cand_toks = tokenize_meaningful(clean, lang, drop_stopwords=True, fold_accents=True)
        for item in results or ():
            if not isinstance(item, dict):
                continue
            url = str(item.get('url') or item.get('link') or '')
            if _is_self_domain(url):
                continue
            snip_text = f'{item.get("title", "")} {item.get("snippet", "")}'.strip()
            if not snip_text:
                continue
            snip_toks = tokenize_meaningful(snip_text, lang, drop_stopwords=True, fold_accents=True)
            run = longest_common_token_run(cand_toks, snip_toks)
            jacc = shingle_jaccard(clean, snip_text, lang=lang, k=3, fold_accents=True)
            cos = ngram_cosine(_strip_accents(clean), _strip_accents(snip_text), n=4)
            if run >= min_exact_phrase_words or jacc >= max_snippet_shingle or cos >= max_snippet_cosine:
                issues.append(
                    f'{lang}.{field_name}: external snippet overlap ({url or "search"}) '
                    f'[run={run}, shingle={jacc:.2f}, cos={cos:.2f}]'
                )
                break

    return (len(issues) == 0), issues, {'queries': queries_run}
