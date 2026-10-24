"""Persistent, public ownership verification and per-language discovery maps."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from dealvault_core import BASE_DIR, DATA_DIR, DOMAIN, LANGUAGES, read_json

NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def legacy_redirects():
    """Preserve product URLs already distributed in Pinterest imports and convenience sitemap aliases."""
    deal_rules = ''.join(
        f'{prefix}/deal/:slug {prefix}/deals/:slug 301\n'
        for prefix in ('', '/ru', '/he', '/es')
    )
    sitemap_rules = (
        '/sitemap /sitemap.xml 301\n'
        '/sitemap/ /sitemap.xml 301\n'
        '/sitemap-index /sitemap-index.xml 301\n'
    )
    return deal_rules + sitemap_rules


def build_search_integrations(root=BASE_DIR/'dist', config=None):
    root = Path(root)
    config = read_json(DATA_DIR/'site_integrations.json') if config is None else config
    (root/'_redirects').write_text(legacy_redirects(), encoding='utf-8')
    key = config.get('bing_site_verification')
    if key:
        if not re.fullmatch(r'[A-Fa-f0-9]{32}', key):
            raise ValueError('Invalid public Bing verification key')
        users = ET.Element('users')
        ET.SubElement(users, 'user').text = key
        ET.indent(users)
        (root/'BingSiteAuth.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(users, encoding='unicode')+'\n', encoding='utf-8')
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
        ET.indent(document)
        (root/name).write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(document, encoding='unicode')+'\n', encoding='utf-8')
        ET.SubElement(ET.SubElement(index, 'sitemap'), 'loc').text = DOMAIN+'/'+name
    ET.indent(index)
    (root/'sitemap-index.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(index, encoding='unicode')+'\n', encoding='utf-8')
    (root/'robots.txt').write_text(
        f'User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\nSitemap: {DOMAIN}/sitemap-index.xml\n',
        encoding='utf-8')
    return len(urls)


if __name__ == '__main__':
    print(f'[Search] {build_search_integrations()} canonical URLs in language maps; ownership files preserved.')
