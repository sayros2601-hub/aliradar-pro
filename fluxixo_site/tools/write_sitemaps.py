"""Write sitemap.xml, sitemap-index.xml, and per-country/language sitemaps cleanly.

The page list comes from build_search.py (tools/sitemap-routes.json). Run this AFTER redesign/build_redesign.py,
so the fingerprints are taken from the pages visitors actually get, not from the plain pages it replaces.
  python tools/write_sitemaps.py
"""
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
ORIGIN = 'https://www.fluxixo.shop'
ROUTES = ROOT / 'tools/sitemap-routes.json'
STATE = ROOT / 'tools/search-build-state.json'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
VIDEO_NS = 'http://www.google.com/schemas/sitemap-video/1.1'
COUNTRY_LANGS = ('en', 'pt', 'es', 'fr', 'he')
PRODUCT_RE = re.compile(r'^/(?:(?:en|pt|es|fr|he)/)?products/([^/]+)/$')


def page_file(dist, path):
    return dist / (path.strip('/') + '/index.html' if path != '/' else 'index.html')


def _append_url(tree, path, lastmod, dist=None, include_video=False):
    url = ET.SubElement(tree, '{' + NS + '}url')
    ET.SubElement(url, '{' + NS + '}loc').text = ORIGIN + path
    ET.SubElement(url, '{' + NS + '}lastmod').text = lastmod
    if include_video and dist is not None:
        m = PRODUCT_RE.match(path)
        if m:
            pid = m.group(1)
            mp4 = Path(dist) / f'assets/video/{pid}.mp4'
            if mp4.exists():
                poster = Path(dist) / f'assets/video/{pid}.poster.jpg'
                thumb = f'{ORIGIN}/assets/video/{pid}.poster.jpg' if poster.exists() else f'{ORIGIN}/assets/images/{pid}.webp'
                vnode = ET.SubElement(url, '{' + VIDEO_NS + '}video')
                ET.SubElement(vnode, '{' + VIDEO_NS + '}thumbnail_loc').text = thumb
                ET.SubElement(vnode, '{' + VIDEO_NS + '}title').text = pid.replace('-', ' ')
                ET.SubElement(vnode, '{' + VIDEO_NS + '}description').text = f'Product preview video for {pid} on FLUXIXO'
                ET.SubElement(vnode, '{' + VIDEO_NS + '}content_loc').text = f'{ORIGIN}/assets/video/{pid}.mp4'


def write_sitemaps(dist, routes, update_state=True):
    """With update_state=False the stored dates are reused as they are (an interim map before the design is applied)."""
    dist = Path(dist)
    previous = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    state, changed_pages = {}, 0
    ET.register_namespace('', NS)
    ET.register_namespace('video', VIDEO_NS)

    sitemap = ET.Element('{' + NS + '}urlset')
    sitemap_ru = ET.Element('{' + NS + '}urlset')
    country_trees = {lang: ET.Element('{' + NS + '}urlset') for lang in COUNTRY_LANGS}
    latest_by_map = {}

    for path in routes:
        digest = hashlib.sha256(page_file(dist, path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        old = previous.get(path, {})
        changed_pages += old.get('sha256') != digest
        if update_state:
            changed = old.get('lastmod') if old.get('sha256') == digest and old.get('lastmod') else now
        else:
            changed = old.get('lastmod') or now
        state[path] = {'sha256': digest, 'lastmod': changed}

        _append_url(sitemap, path, changed, dist=dist, include_video=True)
        match = re.match(r'^/(en|pt|es|fr|he)(?:/|$)', path)
        if not match:
            _append_url(sitemap_ru, path, changed)
            latest_by_map['sitemap-ru.xml'] = max(latest_by_map.get('sitemap-ru.xml', ''), changed)
        else:
            lang = match.group(1)
            _append_url(country_trees[lang], path, changed)
            fname = f'sitemap-{lang}.xml'
            latest_by_map[fname] = max(latest_by_map.get(fname, ''), changed)

    outputs = [(sitemap, 'sitemap.xml'), (sitemap_ru, 'sitemap-ru.xml')]
    outputs.extend((country_trees[lang], f'sitemap-{lang}.xml') for lang in COUNTRY_LANGS)
    for tree, name in outputs:
        ET.indent(tree)
        (dist / name).write_text(ET.tostring(tree, encoding='unicode', xml_declaration=True) + '\n', encoding='utf-8', newline='\n')

    index = ET.Element('{' + NS + '}sitemapindex')
    for name in ('sitemap-ru.xml', *(f'sitemap-{lang}.xml' for lang in COUNTRY_LANGS)):
        if name in latest_by_map:
            node = ET.SubElement(index, '{' + NS + '}sitemap')
            ET.SubElement(node, '{' + NS + '}loc').text = f'{ORIGIN}/{name}'
            ET.SubElement(node, '{' + NS + '}lastmod').text = latest_by_map[name]
    ET.indent(index)
    (dist / 'sitemap-index.xml').write_text(ET.tostring(index, encoding='unicode', xml_declaration=True) + '\n', encoding='utf-8', newline='\n')

    if update_state:
        STATE.write_text(json.dumps(state, indent=2), encoding='utf-8', newline='\n')
    return changed_pages


def main():
    routes = json.loads(ROUTES.read_text(encoding='utf-8'))
    changed = write_sitemaps(DIST, routes)
    print(f'Sitemaps written: {len(routes)} URLs, {changed} changed since the last build.')


if __name__ == '__main__':
    main()
