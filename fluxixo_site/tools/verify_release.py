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
FORBIDDEN = ('InStock', '"19.99"', 'Подборка')
MAX_HTML_BYTES = 1_000_000


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
            if tag in ('img', 'script', 'link') and re.match(r'/?(assets|css|js)/', value):
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


def main():
    problems = collections.defaultdict(list)
    urls = [node.find(NS + 'loc').text for node in ET.parse(RELEASE / 'sitemap.xml').getroot().findall(NS + 'url')]
    if len(urls) < 100 or len(urls) != len(set(urls)):
        problems['sitemap'].append(f'{len(urls)} urls, {len(set(urls))} unique')
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
        # A price in structured data is allowed only when the same page shows it to the visitor.
        if '"Offer"' in text and 'class="price-line"' not in text:
            problems['offer markup without visible price'].append(url)
        for word in FORBIDDEN:
            if word in text:
                problems['forbidden text ' + word].append(url)
        for block in page.jsonld:
            try:
                json.loads(block)
            except ValueError:
                problems['invalid structured data'].append(url)
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
    for required in ('robots.txt', 'sitemap-ru.xml', '404.html', '_headers', '_redirects', 'js/catalog.js'):
        if not (RELEASE / required).exists():
            problems['missing file'].append(required)
    if problems:
        for kind, items in problems.items():
            print(f'FAIL {kind}: {len(items)} e.g. {items[:3]}')
        sys.exit(1)
    print(f'Release verified: {len(pages)} pages, no problems.')


if __name__ == '__main__':
    main()
