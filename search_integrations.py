"""Persistent, public ownership verification and per-language discovery maps."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from dealvault_core import BASE_DIR, DATA_DIR, DOMAIN, LANGUAGES, read_json

NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def build_search_integrations(root=BASE_DIR/'dist', config=None):
    root = Path(root)
    config = read_json(DATA_DIR/'site_integrations.json') if config is None else config
    key = config.get('bing_site_verification')
    if key:
        if not re.fullmatch(r'[A-Fa-f0-9]{32}', key):
            raise ValueError('Invalid public Bing verification key')
        users = ET.Element('users')
        ET.SubElement(users, 'user').text = key
        ET.ElementTree(users).write(root/'BingSiteAuth.xml', encoding='utf-8', xml_declaration=True)
    urls = [loc.text for loc in ET.parse(root/'sitemap.xml').findall('.//{*}loc')]
    if not urls or len(urls) != len(set(urls)):
        raise ValueError('Discovery map must contain distinct canonical pages')
    for url in urls:
        if not url or not url.startswith(DOMAIN+'/') or '?' in url or '#' in url:
            raise ValueError('Discovery map contains a foreign or noncanonical URL')
    index = ET.Element('sitemapindex', xmlns=NS)
    for lang in LANGUAGES:
        def language(url):
            route = url.removeprefix(DOMAIN+'/')
            return next((l for l in LANGUAGES if l != 'en' and route.startswith(l+'/')), 'en')
        subset = [url for url in urls if language(url) == lang]
        if not subset:
            continue
        name = f'sitemap-{lang}.xml'
        document = ET.Element('urlset', xmlns=NS)
        for url in subset:
            ET.SubElement(ET.SubElement(document, 'url'), 'loc').text = url
        ET.ElementTree(document).write(root/name, encoding='utf-8', xml_declaration=True)
        ET.SubElement(ET.SubElement(index, 'sitemap'), 'loc').text = DOMAIN+'/'+name
    ET.ElementTree(index).write(root/'sitemap-index.xml', encoding='utf-8', xml_declaration=True)
    (root/'robots.txt').write_text(
        f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\nSitemap: {DOMAIN}/sitemap-index.xml\n',
        encoding='utf-8')
    return len(urls)


if __name__ == '__main__':
    print(f'[Search] {build_search_integrations()} canonical URLs in language maps; ownership files preserved.')
