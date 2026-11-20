"""Gate before deployment: refuse to publish a release folder with broken pages.

Usage: python verify_release.py [release_dir]. Exits non-zero and prints the problems when a check fails.
"""
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import collections
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

ORIGIN = 'https://www.fluxixo.shop'
RELEASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'release'
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
# Invented offers and internal editorial notes must never reach visitors.
FORBIDDEN = ('"Product"', '"Offer"', 'priceCurrency', 'InStock', 'Подборка')
MAX_HTML_BYTES = 1_000_000
MAX_REDIRECT_RULES = 1800
MAX_STATIC_REDIRECT_RULES = 1800
MAX_DYNAMIC_REDIRECT_RULES = 90
MAX_PRODUCT_MAIN_MEDIAN_JACCARD = 0.45
# One-time migration exception, derived from Git blobs at the original main.
# Never rebuild this from the current catalog: doing so would approve changes.
LEGACY_MEDIA_SOURCE_COMMIT = '8a4caaf152ae7b382e8577a535091876ee15ff34'
LEGACY_MEDIA_BASELINE_PATH = Path(__file__).with_name('legacy_media_baseline.json')
LEGACY_MEDIA_BASELINE_SHA256 = '957b152f44ce8d52523cdf936b3730c9ff37f08f0eb912246a1287c85117b710'

import importlib.util as _importlib_util
import statistics as _statistics


def _load_check_texts():
    try:
        import check_texts as _ct
        return _ct
    except ImportError:
        spec = _importlib_util.spec_from_file_location('check_texts', Path(__file__).with_name('check_texts.py'))
        if spec is None or spec.loader is None:
            raise ImportError('Could not load check_texts.py next to verify_release.py')
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


_check_texts = _load_check_texts()

# Adding any one of these ImageObject keys activates Google Search Console's
# Image License Metadata ("Licensable") report and requires the entire companion set.
IMAGE_LICENSE_TRIGGERS = ('creator', 'creditText', 'copyrightNotice', 'license', 'acquireLicensePage')
IMAGE_LICENSE_REQUIRED_SET = ('contentUrl', 'creator', 'creditText', 'copyrightNotice', 'license', 'acquireLicensePage')


def _is_nonempty_str(value):
    return isinstance(value, str) and bool(value.strip())


def _is_https_url(value):
    return isinstance(value, str) and value.startswith('https://') and len(value) > len('https://')


def _is_iso_date(value, *, require_tz_with_time=False):
    from datetime import datetime as _datetime
    import re as _re

    if not _is_nonempty_str(value):
        return False
    text = value.strip()
    if 'T' in text and require_tz_with_time and not (text.endswith('Z') or _re.search(r'[+-]\d{2}:\d{2}$', text)):
        return False
    try:
        _datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return False
    return True


def _node_types(node):
    raw = node.get('@type')
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, str))
    return ()


def validate_google_structured_data(payload):
    """Validate parsed JSON-LD against Google Search Central structured data rules."""
    errors = set()

    def check_image(node):
        if any(k in node for k in IMAGE_LICENSE_TRIGGERS):
            has_all = all(bool(node.get(k)) for k in IMAGE_LICENSE_REQUIRED_SET)
            has_urls = _is_https_url(node.get('license')) and _is_https_url(node.get('acquireLicensePage'))
            if not (has_all and has_urls):
                errors.add('incomplete image license metadata in JSON-LD')
        if not (_is_https_url(node.get('contentUrl')) or _is_https_url(node.get('url'))):
            errors.add('ImageObject missing HTTPS contentUrl/url')
        for dim in ('width', 'height'):
            if dim in node:
                val = node[dim]
                if isinstance(val, bool) or not isinstance(val, (int, float)) or val <= 0:
                    errors.add('ImageObject invalid dimensions')

    def check_video(node):
        thumbs = node.get('thumbnailUrl')
        thumb_ok = _is_https_url(thumbs) or (
            isinstance(thumbs, list) and bool(thumbs) and all(_is_https_url(t) for t in thumbs)
        )
        media_ok = _is_https_url(node.get('contentUrl')) or _is_https_url(node.get('embedUrl'))
        if not (_is_nonempty_str(node.get('name')) and _is_nonempty_str(node.get('description'))
                and thumb_ok and _is_iso_date(node.get('uploadDate'), require_tz_with_time=True) and media_ok):
            errors.add('invalid VideoObject structured data')

    def check_article(node):
        headline = node.get('headline')
        author = node.get('author')
        authors = author if isinstance(author, list) else ([author] if isinstance(author, dict) else [])
        author_ok = bool(authors) and all(isinstance(a, dict) and _is_nonempty_str(a.get('name')) for a in authors)
        img = node.get('image')
        img_ok = _is_https_url(img) or (isinstance(img, dict) and _is_https_url(img.get('url') or img.get('contentUrl'))) or (
            isinstance(img, list) and bool(img)
        )
        if not (_is_nonempty_str(headline) and len(headline) <= 200 and img_ok
                and _is_iso_date(node.get('datePublished')) and author_ok):
            errors.add('invalid Article structured data')

    def check_breadcrumbs(node):
        els = node.get('itemListElement')
        if not isinstance(els, list) or not els:
            errors.add('invalid BreadcrumbList structured data')
            return
        for idx, el in enumerate(els, 1):
            if not isinstance(el, dict) or el.get('position') != idx:
                errors.add('invalid BreadcrumbList structured data')
                return
            item = el.get('item')
            name_ok = _is_nonempty_str(el.get('name')) or (isinstance(item, dict) and _is_nonempty_str(item.get('name')))
            item_url = item.get('@id') if isinstance(item, dict) else item
            url_ok = _is_https_url(item_url) if (idx < len(els) or item is not None) else True
            if not (name_ok and url_ok):
                errors.add('invalid BreadcrumbList structured data')
                return

    def check_faq(node):
        entities = node.get('mainEntity')
        if not isinstance(entities, list) or not entities:
            errors.add('invalid FAQPage structured data')
            return
        for q in entities:
            ans = q.get('acceptedAnswer') if isinstance(q, dict) else None
            if not (isinstance(q, dict) and q.get('@type') == 'Question' and _is_nonempty_str(q.get('name'))
                    and isinstance(ans, dict) and ans.get('@type') == 'Answer' and _is_nonempty_str(ans.get('text'))):
                errors.add('invalid FAQPage structured data')
                return

    def check_item_list(node):
        els = node.get('itemListElement')
        if els is None:
            return
        if not isinstance(els, list):
            errors.add('invalid ItemList structured data')
            return
        for idx, el in enumerate(els, 1):
            if not isinstance(el, dict) or el.get('position') != idx or not _is_nonempty_str(el.get('name')):
                errors.add('invalid ItemList structured data')
                return
            target = el.get('url') or el.get('item')
            if not _is_https_url(target):
                errors.add('invalid ItemList structured data')
                return

    def walk(value):
        if isinstance(value, list):
            for entry in value:
                walk(entry)
            return
        if not isinstance(value, dict):
            return
        types = _node_types(value)
        if 'ImageObject' in types:
            check_image(value)
        if 'VideoObject' in types:
            check_video(value)
        if any(t in types for t in ('Article', 'NewsArticle', 'BlogPosting')):
            check_article(value)
        if 'BreadcrumbList' in types:
            check_breadcrumbs(value)
        if 'FAQPage' in types:
            check_faq(value)
        if 'ItemList' in types:
            check_item_list(value)
        if any(t in types for t in ('WebSite', 'Organization', 'ItemPage', 'CollectionPage')):
            if not _is_nonempty_str(value.get('name')) or ('url' in value and not _is_https_url(value.get('url'))):
                errors.add('invalid WebSite/Organization/Page JSON-LD')
        for child in value.values():
            walk(child)

    walk(payload)
    return sorted(errors)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.description = None
        self.canonical = None
        self.language = ''
        self.robots = ''
        self.h1 = 0
        self.hreflang = {}
        self.links = []
        self.assets = []
        self.jsonld = []
        self._capture = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        if tag == 'html':
            self.language = a.get('lang', '')
        elif tag == 'meta' and a.get('name') == 'description':
            self.description = a.get('content', '')
        elif tag == 'meta' and a.get('name') == 'robots':
            self.robots = a.get('content', '')
        elif tag == 'link' and a.get('rel') == 'canonical':
            self.canonical = a.get('href')
        elif tag == 'link' and a.get('rel') == 'alternate' and a.get('hreflang'):
            self.hreflang[a['hreflang']] = a.get('href')
        elif tag == 'h1':
            self.h1 += 1
        elif tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        for key in ('src', 'href'):
            value = a.get(key, '')
            if tag in ('img', 'script', 'link', 'source', 'video') and re.match(r'/?(assets|css|js)/', value):
                self.assets.append(value)
        for part in a.get('srcset', '').split(','):
            if part.strip():
                self.assets.append(part.strip().split(' ')[0])
        if tag == 'title' or (tag == 'script' and a.get('type') == 'application/ld+json'):
            self._capture = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if self._capture == tag:
            text = ''.join(self._buffer)
            if tag == 'title':
                self.title = ' '.join(text.split())
            else:
                self.jsonld.append(text)
            self._capture = None

    def handle_data(self, data):
        if self._capture:
            self._buffer.append(data)


_PRODUCT_ROUTE_RE = re.compile(r'^/(?:(?:en|pt|es|fr|he)/)?products/[^/]+/?$')
_BOILERPLATE_SECTION_RE = re.compile(
    r'<section\b[^>]*class=["\'][^"\']*\b(market-guide|product-faq)\b[^"\']*["\'][^>]*>(.*?)</section>',
    re.S | re.I,
)
_MAIN_BLOCK_RE = re.compile(r'<main\b[^>]*>(.*?)</main>', re.S | re.I)
_PRODUCT_PT_RE = re.compile(r'<p\b[^>]*class=["\'][^"\']*\bt\b[^"\']*["\'][^>]*>(.*?)</p>', re.S | re.I)
_STRIP_NONVISIBLE_RE = re.compile(r'<(script|style)\b[^>]*>.*?</\1>', re.S | re.I)
_HTML_TAGS_RE = re.compile(r'<[^>]+>')
_WORD_TOK_RE = re.compile(r'[0-9A-Za-z\u00c0-\u024f\u0400-\u04ff\u05d0-\u05ea]+')


def _strip_html_to_text(fragment):
    """Strip scripts, styles, and tags cleanly for boilerplate and token comparisons."""
    cleaned = _STRIP_NONVISIBLE_RE.sub(' ', fragment or '')
    return ' '.join(_HTML_TAGS_RE.sub(' ', cleaned).split())


def validate_product_page_uniqueness(
    html_by_url,
    *,
    max_median_main_jaccard=MAX_PRODUCT_MAIN_MEDIAN_JACCARD,
    min_pages_for_jaccard=6,
):
    """Detect placeholder seller-title fallbacks and cloned boilerplate across product pages."""
    errors = []
    by_locale = collections.defaultdict(list)
    for url, html in sorted((html_by_url or {}).items()):
        path = urlsplit(url).path
        if not _PRODUCT_ROUTE_RE.match(path):
            continue
        if _check_texts.has_placeholder_copy(html):
            errors.append(f'placeholder copy on product page: {url}')
        loc_match = re.match(r'^/(en|pt|es|fr|he)/', path)
        loc = loc_match.group(1) if loc_match else 'ru'
        by_locale[loc].append((url, html))

    for loc, items in sorted(by_locale.items()):
        section_pages = collections.defaultdict(list)
        pt_pages = collections.defaultdict(list)
        pt_shingles = []
        word_sets = []

        for url, html in items:
            if 'Quick buyer questions' in html or 'Частые вопросы перед покупкой' in html:
                errors.append(f'forbidden Quick buyer questions block on product page: {url}')
            for cls_name, inner in _BOILERPLATE_SECTION_RE.findall(html):
                if cls_name.lower() == 'product-faq':
                    errors.append(f'forbidden <section class="product-faq"> on product page: {url}')
                norm_sec = _strip_html_to_text(inner).casefold()
                if norm_sec:
                    section_pages[(cls_name.lower(), norm_sec)].append(url)

            pt_match = _PRODUCT_PT_RE.search(html)
            if pt_match:
                norm_pt = _strip_html_to_text(pt_match.group(1)).casefold()
                if norm_pt:
                    pt_pages[norm_pt].append(url)
                    pt_toks = [w for w in _WORD_TOK_RE.findall(norm_pt) if len(w) > 1]
                    if len(pt_toks) >= 5:
                        sh = {tuple(pt_toks[k:k + 3]) for k in range(len(pt_toks) - 2)}
                        pt_shingles.append((url, sh))

            main_match = _MAIN_BLOCK_RE.search(html)
            main_txt = _strip_html_to_text(main_match.group(1) if main_match else html)
            word_sets.append(set(_WORD_TOK_RE.findall(main_txt.casefold())))

        for (cls_name, _), urls in sorted(section_pages.items(), key=lambda kv: kv[0]):
            if cls_name != 'product-faq' and len(urls) >= 3:
                errors.append(
                    f'repeated <section class="{cls_name}"> on {len(urls)} {loc} product pages ({urls[0]}..)'
                )

        for _, urls in sorted(pt_pages.items(), key=lambda kv: kv[1][0]):
            if len(urls) > 1:
                errors.append(
                    f'duplicate product <p class="t"> in {loc}: {urls[:3]}'
                )

        # Inverted index on 3-word shingles: checks every candidate pair sharing >= 2 shingles in O(N) average time.
        shingle_docs = collections.defaultdict(list)
        for idx, (_, sh) in enumerate(pt_shingles):
            for gram in sh:
                shingle_docs[gram].append(idx)
        pair_shared = collections.Counter()
        for doc_ids in shingle_docs.values():
            if len(doc_ids) < 2 or len(doc_ids) > 80:
                continue
            for a_pos in range(len(doc_ids)):
                ia = doc_ids[a_pos]
                for b_pos in range(a_pos + 1, len(doc_ids)):
                    pair_shared[(ia, doc_ids[b_pos])] += 1
        for (i, j), shared in sorted(pair_shared.items()):
            if shared < 2:
                continue
            u_a, sh_a = pt_shingles[i]
            u_b, sh_b = pt_shingles[j]
            union = len(sh_a | sh_b)
            if union and (len(sh_a & sh_b) / union) >= 0.70:
                errors.append(f'near-duplicate product <p class="t"> in {loc}: {u_a} ~ {u_b}')

        if len(word_sets) >= min_pages_for_jaccard:
            jaccards = []
            n_ws = len(word_sets)
            if n_ws <= 60:
                for i in range(n_ws):
                    a = word_sets[i]
                    for j in range(i + 1, n_ws):
                        b = word_sets[j]
                        union = len(a | b)
                        jaccards.append((len(a & b) / union) if union else 0.0)
            else:
                # Deterministic bounded sample keeps verify_release fast even at 5,000+ products.
                step = max(1, n_ws // 50)
                sample_idx = list(range(0, n_ws, step))[:50]
                for idx_pos, i in enumerate(sample_idx):
                    a = word_sets[i]
                    for j in sample_idx[idx_pos + 1:]:
                        b = word_sets[j]
                        union = len(a | b)
                        jaccards.append((len(a & b) / union) if union else 0.0)
            median_j = _statistics.median(jaccards)
            if median_j > max_median_main_jaccard:
                errors.append(
                    f'high template similarity in {loc} product pages '
                    f'(median <main> Jaccard={median_j:.3f} > {max_median_main_jaccard:.2f})'
                )
    return errors


def local_file(url_or_path):
    path = urlsplit(url_or_path).path.strip('/')
    if re.search(r'\.[a-z0-9]{2,5}$', path):
        return RELEASE / path
    return RELEASE / (path + '/index.html' if path else 'index.html')


def validate_home_languages(pages):
    """Keep the English landing in the home cluster, separate from its full catalog."""
    paths = {'en': '/', 'ru': '/catalog/', 'pt': '/pt/', 'es': '/es/', 'fr': '/fr/', 'he': '/he/'}
    aliases = {'en': ('en', 'en-US'), 'ru': ('ru', 'ru-RU'), 'pt': ('pt', 'pt-BR'),
               'es': ('es', 'es-MX'), 'fr': ('fr', 'fr-FR'), 'he': ('he', 'he-IL')}
    expected = {tag: ORIGIN + paths[lang] for lang, tags in aliases.items() for tag in tags}
    expected['x-default'] = ORIGIN + '/'
    errors = []
    for lang, path in [*paths.items(), ('en', '/en/')]:
        url = ORIGIN + path
        page = pages.get(url)
        if page is None:
            errors.append(f'missing language entry page: {url}')
            continue
        if page.language.lower().split('-', 1)[0] != lang:
            errors.append(f'wrong HTML language for {url}: expected {lang}')
        if page.canonical != url:
            errors.append(f'wrong home canonical: {url}')
        if path == '/en/':
            if page.hreflang:
                errors.append('standalone /en/ catalog must not declare home hreflang')
        elif page.hreflang != expected:
            errors.append(f'wrong home hreflang cluster: {url}')
    return errors


def validate_ru_sitemap(release, all_urls):
    """Keep current Russian routes in Yandex's map, excluding the English landing."""
    try:
        root = ET.parse(Path(release) / 'sitemap-ru.xml').getroot()
        urls = [(node.findtext(NS + 'loc') or '').strip() for node in root.findall(NS + 'url')]
    except (OSError, ET.ParseError) as exc:
        return [f'unreadable sitemap-ru.xml: {exc}']
    expected = {
        url for url in all_urls
        if url.startswith(ORIGIN + '/')
        and urlsplit(url).path != '/'
        and not re.match(r'^/(en|pt|es|fr|he)(/|$)', urlsplit(url).path)
    }
    errors = []
    duplicates = [url for url, count in collections.Counter(urls).items() if count > 1]
    if duplicates:
        errors.append(f'duplicate RU URLs: {duplicates[:3]}')
    missing, unexpected = sorted(expected - set(urls)), sorted(set(urls) - expected)
    if missing:
        errors.append(f'missing current RU URLs: {missing[:3]}')
    if unexpected:
        errors.append(f'unexpected or noncanonical RU URLs: {unexpected[:3]}')
    return errors


def validate_search_engine_parity(release):
    """Verify Google, Microsoft Bing, and Yandex (Russian-only) verification/crawl artifacts."""
    errors = []
    rel = Path(release)
    home = rel / 'index.html'
    if home.exists():
        html = home.read_text(encoding='utf-8', errors='replace')
        for marker in ('google-site-verification', 'msvalidate.01', 'yandex-verification'):
            if f'name="{marker}"' not in html:
                errors.append(f'homepage missing <meta name="{marker}">')
    bing_auth = rel / 'BingSiteAuth.xml'
    if not bing_auth.exists():
        errors.append('missing BingSiteAuth.xml')
    else:
        try:
            users = [u.text.strip() for u in ET.parse(bing_auth).findall('.//user') if u.text]
            if not users:
                errors.append('BingSiteAuth.xml has empty <user>')
        except ET.ParseError as exc:
            errors.append(f'invalid BingSiteAuth.xml: {exc}')
    key_path = rel / 'indexnow-key.txt'
    idx_path = rel / 'indexnow.txt'
    if not key_path.exists() or not idx_path.exists():
        errors.append('missing indexnow-key.txt or indexnow.txt')
    else:
        key = key_path.read_text(encoding='utf-8').strip()
        if not re.fullmatch(r'[0-9a-f]{16,128}', key):
            errors.append('invalid IndexNow key format')
        elif idx_path.read_text(encoding='utf-8').strip() != key:
            errors.append('indexnow.txt mismatch with indexnow-key.txt')
        elif not (rel / f'{key}.txt').exists() or (rel / f'{key}.txt').read_text(encoding='utf-8').strip() != key:
            errors.append(f'missing or mismatched {key}.txt')
    rss_path = rel / 'rss.xml'
    if not rss_path.exists():
        errors.append('missing rss.xml for Bing feed sync')
    else:
        try:
            rroot = ET.parse(rss_path).getroot()
            if not rroot.findall('.//item'):
                errors.append('rss.xml contains zero <item> entries')
        except ET.ParseError as exc:
            errors.append(f'invalid rss.xml: {exc}')
    # Pinterest auto-publish subscribes to this feed; it may be empty (future products only) but must parse.
    pin_path = rel / 'pinterest-new.xml'
    if not pin_path.exists():
        errors.append('missing pinterest-new.xml for Pinterest auto-publish')
    else:
        try:
            for it in ET.parse(pin_path).getroot().findall('.//item'):
                if it.find('enclosure') is None or '/en/products/' not in (it.findtext('link') or ''):
                    errors.append(f'pinterest-new.xml item without image or English link: {it.findtext("guid")}')
                    break
        except ET.ParseError as exc:
            errors.append(f'invalid pinterest-new.xml: {exc}')
    idx_xml = rel / 'sitemap-index.xml'
    if idx_xml.exists():
        try:
            iroot = ET.parse(idx_xml).getroot()
            ilocs = {(n.findtext(NS + 'loc') or '').strip() for n in iroot.findall(NS + 'sitemap')}
            for lang in ('ru', 'en', 'pt', 'es', 'fr', 'he'):
                if f'{ORIGIN}/sitemap-{lang}.xml' not in ilocs:
                    errors.append(f'sitemap-index.xml missing sitemap-{lang}.xml')
        except ET.ParseError as exc:
            errors.append(f'invalid sitemap-index.xml: {exc}')
    robots_path = rel / 'robots.txt'
    if robots_path.exists():
        rtxt = robots_path.read_text(encoding='utf-8', errors='replace')
        yandex_block = ''
        m = re.search(r'(?ms)^User-agent:\s*Yandex\b.*?(?=^User-agent:|\Z)', rtxt)
        if not m:
            errors.append('robots.txt missing User-agent: Yandex block')
        else:
            yandex_block = m.group(0)
            for req_line in ('Allow: /', 'Disallow: /en/', 'Disallow: /pt/', 'Disallow: /es/', 'Disallow: /fr/', 'Disallow: /he/', 'Clean-param:'):
                if req_line not in yandex_block:
                    errors.append(f'robots.txt Yandex block missing {req_line}')
        for sm in ('sitemap.xml', 'sitemap-index.xml', 'sitemap-ru.xml'):
            if f'Sitemap: {ORIGIN}/{sm}' not in rtxt:
                errors.append(f'robots.txt missing Sitemap: {ORIGIN}/{sm}')
    return errors


def _load_legacy_media_baseline():
    raw = LEGACY_MEDIA_BASELINE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEGACY_MEDIA_BASELINE_SHA256:
        raise ValueError('legacy media baseline digest mismatch')
    baseline = json.loads(raw)
    if (baseline.get('version') != 1 or baseline.get('source_commit') != LEGACY_MEDIA_SOURCE_COMMIT
            or not isinstance(baseline.get('products'), dict)):
        raise ValueError('legacy media baseline provenance mismatch')
    return baseline['products']


def _release_image_file(root, relative):
    if (not isinstance(relative, str) or not relative.startswith('assets/images/')
            or '\\' in relative or PurePosixPath(relative).as_posix() != relative
            or '..' in PurePosixPath(relative).parts):
        return None
    root = Path(root).resolve()
    target = root / relative
    if target.is_symlink() or not target.resolve().is_relative_to(root) or not target.is_file():
        return None
    return target


def _unchanged_legacy_gallery(product, rel, baseline):
    # Explicit tags always demand review, including empty/false tags. Removing
    # them cannot exempt a new ID, changed identity, gallery order or file bytes.
    if 'mediaReviewRequired' in product or 'mediaReview' in product:
        return False
    original = baseline.get(product.get('id'))
    if not isinstance(original, dict) or not isinstance(product.get('views', []), list):
        return False
    identity = [product.get(key) for key in
                ('id', 'sourceProductId', 'sourceTitle', 'sourceImageUrl', 'sourceDetailUrl')]
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    paths = [product.get('image'), *product.get('views', [])]
    gallery = original.get('gallery')
    if (digest != original.get('identity_sha256') or not isinstance(gallery, list)
            or paths != [entry[0] for entry in gallery]):
        return False
    for relative, expected in gallery:
        target = _release_image_file(rel, relative)
        try:
            if target is None or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                return False
        except OSError:
            return False
    return True


def validate_transparent_product_images(rel):
    """Ensure every active catalog product image and gallery view is a transparent RGBA cutout (no opaque color boxes)."""
    errors = []
    cat_file = rel / 'js' / 'catalog.js'
    if not cat_file.is_file():
        return errors
    try:
        from PIL import Image
        raw = cat_file.read_text(encoding='utf-8')
        catalog = json.loads(raw.split('=', 1)[1].strip().rstrip(';'))
    except Exception as exc:
        return [f'could not parse catalog.js for image check: {exc}']
    try:
        legacy = _load_legacy_media_baseline()
    except (OSError, ValueError, TypeError):
        errors.append('legacy media baseline is missing or invalid')
        legacy = {}
    for product in catalog.get('products', []):
        if product.get('demo'):
            continue
        pid = product.get('id', '?')
        if not _unchanged_legacy_gallery(product, rel, legacy):
            repo = Path(__file__).resolve().parents[2]
            if str(repo) not in sys.path:
                sys.path.insert(0, str(repo))
            from fluxixo_ai.reviewed_media import verify_product_review
            # Seller originals stay in the source checkout, never in public release.
            references = repo / 'fluxixo_site' / 'dist'
            if not verify_product_review(product, rel, reference_root=references):
                errors.append(f'{pid}: current source/output review is missing or invalid')
        rels = [product.get('image')] + list(product.get('views') or [])
        for img_rel in rels:
            if not isinstance(img_rel, str) or not img_rel:
                continue
            target = _release_image_file(rel, img_rel)
            if target is None:
                errors.append(f'{pid}: {img_rel} is missing or outside the release image directory')
                continue
            try:
                with Image.open(target) as im:
                    if 'A' not in im.getbands():
                        errors.append(f'{pid}: {img_rel} is opaque ({im.mode}) without transparency')
                        continue
                    alpha = im.getchannel('A')
                    w, h = alpha.size
                    corners = (
                        alpha.getpixel((0, 0)),
                        alpha.getpixel((max(0, w - 1), 0)),
                        alpha.getpixel((0, max(0, h - 1))),
                        alpha.getpixel((max(0, w - 1), max(0, h - 1))),
                    )
                    if alpha.getextrema()[0] > 24 or min(corners) > 24:
                        errors.append(f'{pid}: {img_rel} has opaque background corners {corners}')
            except Exception as exc:
                errors.append(f'{pid}: {img_rel} unreadable ({exc})')
    return errors


def main():
    problems = collections.defaultdict(list)
    urls = [node.find(NS + 'loc').text for node in ET.parse(RELEASE / 'sitemap.xml').getroot().findall(NS + 'url')]
    if len(urls) < 100 or len(urls) != len(set(urls)):
        problems['sitemap'].append(f'{len(urls)} urls, {len(set(urls))} unique')
    for error in validate_ru_sitemap(RELEASE, urls):
        problems['Yandex RU sitemap'].append(error)
    for error in validate_search_engine_parity(RELEASE):
        problems['Search engine parity'].append(error)
    for error in validate_transparent_product_images(RELEASE):
        problems['opaque product image'].append(error)
    pages = {}
    for url in urls:
        file = local_file(url)
        if not file.exists():
            problems['missing page'].append(url)
            continue
        raw = file.read_bytes()
        if len(raw) > MAX_HTML_BYTES:
            problems['page too large'].append(url)
        text = raw.decode('utf-8')
        page = Page()
        page.feed(text)
        pages[url] = page
        if page.canonical != url:
            problems['canonical'].append(url)
        if page.h1 != 1:
            problems['h1 count'].append(url)
        if not page.title or len(page.title) > 70:
            problems['title'].append(url)
        if not page.description or not 50 <= len(page.description) <= 170:
            problems['description'].append(url)
        if 'noindex' in page.robots:
            problems['noindex in sitemap'].append(url)
        for word in FORBIDDEN:
            if word in text:
                problems['forbidden text ' + word].append(url)
        if _check_texts.has_placeholder_copy(text):
            problems['placeholder fallback copy'].append(url)
        for block in page.jsonld:
            try:
                payload = json.loads(block)
            except ValueError:
                problems['invalid structured data'].append(url)
            else:
                for schema_err in validate_google_structured_data(payload):
                    problems[schema_err].append(url)
        for asset in page.assets:
            if not local_file(asset.split('?')[0]).exists():
                problems['missing asset'].append(f'{url} -> {asset}')
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme in ('http', 'https') and parts.netloc != urlsplit(ORIGIN).netloc:
                continue
            if parts.scheme in ('mailto', 'tel') or not parts.path:
                continue
            target = parts.path if parts.path.startswith('/') else '/' + parts.path
            if not local_file(target).exists():
                problems['broken link'].append(f'{url} -> {link}')
        if urlsplit(url).path != '/en/' and not page.hreflang:
            problems['no language alternates'].append(url)
    for error in validate_home_languages(pages):
        problems['home language migration'].append(error)
    for url, page in pages.items():
        for language, target in page.hreflang.items():
            other = pages.get(target)
            if other is None:
                problems['alternate target missing'].append(f'{url} -> {target}')
            elif url not in other.hreflang.values():
                problems['alternate not reciprocal'].append(f'{url} -> {target}')
    for field in ('title', 'description'):
        counts = collections.Counter(getattr(page, field) for page in pages.values())
        duplicates = [value for value, count in counts.items() if count > 1]
        if duplicates:
            problems['duplicate ' + field].append(str(duplicates[:3]))
    product_html = {
        url: local_file(url).read_text('utf-8', errors='replace')
        for url in pages
        if _PRODUCT_ROUTE_RE.match(urlsplit(url).path) and local_file(url).is_file()
    }
    for err in validate_product_page_uniqueness(product_html):
        problems['product page uniqueness'].append(err)
    for lang in ('en', 'pt', 'es', 'fr', 'he'):
        map_path = RELEASE / f'sitemap-{lang}.xml'
        if not map_path.exists():
            problems[f'sitemap-{lang}.xml'].append(f'missing sitemap-{lang}.xml')
            continue
        try:
            mroot = ET.parse(map_path).getroot()
            murls = [(node.findtext(NS + 'loc') or '').strip() for node in mroot.findall(NS + 'url')]
            dups = [u for u, c in collections.Counter(murls).items() if c > 1]
            if dups:
                problems[f'sitemap-{lang}.xml'].append(f'duplicate URLs: {dups[:3]}')
            bad = [u for u in murls if not urlsplit(u).path.startswith(f'/{lang}/')
                   and not (lang == 'en' and u == ORIGIN + '/')]
            if bad:
                problems[f'sitemap-{lang}.xml'].append(f'wrong locale URLs: {bad[:3]}')
            if lang == 'en' and ORIGIN + '/' in urls and ORIGIN + '/' not in murls:
                problems['sitemap-en.xml'].append('English landing / is missing')
            missing_from_all = [u for u in murls if u not in set(urls)]
            if missing_from_all:
                problems[f'sitemap-{lang}.xml'].append(f'unknown URLs: {missing_from_all[:3]}')
        except (OSError, ET.ParseError) as exc:
            problems[f'sitemap-{lang}.xml'].append(str(exc))
    for required in ('robots.txt', 'sitemap-ru.xml', 'sitemap-index.xml', 'BingSiteAuth.xml', 'rss.xml', '404.html', '_headers', '_redirects', 'js/catalog.js'):
        if not (RELEASE / required).exists():
            problems['missing file'].append(required)
    # Cloudflare Pages allows up to 2,000 static and 100 dynamic (_redirects with :param or *) rules.
    redirect_file = RELEASE / '_redirects'
    if redirect_file.exists():
        rules = [line.strip() for line in redirect_file.read_text(encoding='utf-8').splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        dynamic_rules = [r for r in rules if '*' in r.split()[0] or ':' in r.split()[0]]
        static_rules = [r for r in rules if r not in dynamic_rules]
        if len(static_rules) > MAX_STATIC_REDIRECT_RULES:
            problems['too many static redirect rules'].append(f'{len(static_rules)} > {MAX_STATIC_REDIRECT_RULES}')
        if len(dynamic_rules) > MAX_DYNAMIC_REDIRECT_RULES:
            problems['too many dynamic redirect rules'].append(f'{len(dynamic_rules)} > {MAX_DYNAMIC_REDIRECT_RULES}')
    if problems:
        for kind, items in problems.items():
            print(f'FAIL {kind}: {len(items)} e.g. {items[:3]}')
        sys.exit(1)
    print(f'Release verified: {len(pages)} pages, no problems.')


if __name__ == '__main__':
    main()
