"""Write sitemap.xml and sitemap-ru.xml with a lastmod that changes only when the published page really changed.

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


def page_file(dist, path):
    return dist / (path.strip('/') + '/index.html' if path != '/' else 'index.html')


def write_sitemaps(dist, routes, update_state=True):
    """With update_state=False the stored dates are reused as they are (an interim map before the design is applied)."""
    previous = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    state, changed_pages = {}, 0
    ET.register_namespace('', NS)
    sitemap, sitemap_ru = ET.Element('{' + NS + '}urlset'), ET.Element('{' + NS + '}urlset')
    for path in routes:
        digest = hashlib.sha256(page_file(dist, path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        old = previous.get(path, {})
        changed_pages += old.get('sha256') != digest
        if update_state:
            changed = old.get('lastmod') if old.get('sha256') == digest and old.get('lastmod') else now
        else:
            changed = old.get('lastmod') or now
        state[path] = {'sha256': digest, 'lastmod': changed}
        # The Russian map is the one Yandex reads; it carries the Russian pages only.
        for target in (sitemap, sitemap_ru) if not re.match(r'/(en|pt|es|fr|he)/', path) else (sitemap,):
            url = ET.SubElement(target, '{' + NS + '}url')
            ET.SubElement(url, '{' + NS + '}loc').text = ORIGIN + path
            ET.SubElement(url, '{' + NS + '}lastmod').text = changed
    for tree, name in ((sitemap, 'sitemap.xml'), (sitemap_ru, 'sitemap-ru.xml')):
        ET.indent(tree)
        (dist / name).write_text(ET.tostring(tree, encoding='unicode', xml_declaration=True) + '\n', encoding='utf-8', newline='\n')
    if update_state:
        STATE.write_text(json.dumps(state, indent=2), encoding='utf-8', newline='\n')
    return changed_pages


def main():
    routes = json.loads(ROUTES.read_text(encoding='utf-8'))
    changed = write_sitemaps(DIST, routes)
    print(f'Sitemaps written: {len(routes)} URLs, {changed} changed since the last build.')


if __name__ == '__main__':
    main()
