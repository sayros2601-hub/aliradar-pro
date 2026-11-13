"""Gate before deployment: refuse to publish a release folder with broken pages.

Usage: python verify_release.py [release_dir]. Exits non-zero and prints the problems when a check fails.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import collections
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
MAX_REDIRECT_RULES = 90

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
        if tag == 'meta' and a.get('name') == 'description':
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


def local_file(url_or_path):
    path = urlsplit(url_or_path).path.strip('/')
    if re.search(r'\.[a-z0-9]{2,5}$', path):
        return RELEASE / path
    return RELEASE / (path + '/index.html' if path else 'index.html')


def validate_ru_sitemap(release, all_urls):
    """Keep every current root/Russian route in Yandex's map, without foreign locales."""
    try:
        root = ET.parse(Path(release) / 'sitemap-ru.xml').getroot()
        urls = [(node.findtext(NS + 'loc') or '').strip() for node in root.findall(NS + 'url')]
    except (OSError, ET.ParseError) as exc:
        return [f'unreadable sitemap-ru.xml: {exc}']
    expected = {
        url for url in all_urls
        if url.startswith(ORIGIN + '/')
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


def main():
    problems = collections.defaultdict(list)
    urls = [node.find(NS + 'loc').text for node in ET.parse(RELEASE / 'sitemap.xml').getroot().findall(NS + 'url')]
    if len(urls) < 100 or len(urls) != len(set(urls)):
        problems['sitemap'].append(f'{len(urls)} urls, {len(set(urls))} unique')
    for error in validate_ru_sitemap(RELEASE, urls):
        problems['Yandex RU sitemap'].append(error)
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
        is_home = urlsplit(url).path == '/'
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
        if not is_home and not page.hreflang:
            problems['no language alternates'].append(url)
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
            bad = [u for u in murls if not urlsplit(u).path.startswith(f'/{lang}/')]
            if bad:
                problems[f'sitemap-{lang}.xml'].append(f'wrong locale URLs: {bad[:3]}')
            missing_from_all = [u for u in murls if u not in set(urls)]
            if missing_from_all:
                problems[f'sitemap-{lang}.xml'].append(f'unknown URLs: {missing_from_all[:3]}')
        except (OSError, ET.ParseError) as exc:
            problems[f'sitemap-{lang}.xml'].append(str(exc))
    for required in ('robots.txt', 'sitemap-ru.xml', 'sitemap-index.xml', '404.html', '_headers', '_redirects', 'js/catalog.js'):
        if not (RELEASE / required).exists():
            problems['missing file'].append(required)
    # Production silently ignored redirect rules beyond roughly the 106th, so keep a safe margin.
    redirect_file = RELEASE / '_redirects'
    if redirect_file.exists():
        rules = [line for line in redirect_file.read_text(encoding='utf-8').splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        if len(rules) > MAX_REDIRECT_RULES:
            problems['too many redirect rules'].append(f'{len(rules)} > {MAX_REDIRECT_RULES}')
    if problems:
        for kind, items in problems.items():
            print(f'FAIL {kind}: {len(items)} e.g. {items[:3]}')
        sys.exit(1)
    print(f'Release verified: {len(pages)} pages, no problems.')


if __name__ == '__main__':
    main()
