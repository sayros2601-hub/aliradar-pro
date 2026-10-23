"""Check every generated page, local link, image, canonical and feed before release."""
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET
from dealvault_core import BASE_DIR, DOMAIN, public_path, affiliate_key


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]; self.canonical=[]; self.alternates=[]; self.affiliates=[]; self.ids=[]; self.lang=None
        self.script_type=None; self.script_buffer=''; self.json_blocks=[]; self.headings=0; self.errors=[]

    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag == 'html': self.lang=a.get('lang')
        if tag == 'h1': self.headings+=1
        if 'id' in a: self.ids.append(a['id'])
        if any(k.startswith('on') for k in a): self.errors.append('Inline event handler')
        if tag in ('a','link') and a.get('href'): self.links.append(a['href'])
        if tag in ('img','script') and a.get('src'): self.links.append(a['src'])
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a.get('href'))
        if tag == 'link' and a.get('hreflang'): self.alternates.append(a['hreflang'])
        if tag == 'a' and 'data-aff-id' in a:
            self.affiliates.append(a['href'])
            if not {'sponsored','noopener','nofollow'}.issubset(set(a.get('rel','').split())):
                self.errors.append('Missing affiliate relationship/safety attributes')
        if tag == 'script': self.script_type=a.get('type'); self.script_buffer=''

    def handle_data(self, data):
        if self.script_type in ('application/json','application/ld+json'): self.script_buffer+=data

    def handle_endtag(self, tag):
        if tag == 'script':
            if self.script_type in ('application/json','application/ld+json'):
                self.json_blocks.append(json.loads(self.script_buffer))
            self.script_type=None


def read_pages(paths):
    """Bounded parallel reads avoid thousands of serial Windows file-open delays."""
    def read(path):
        try:
            return path, path.read_text(encoding='utf-8'), None
        except OSError as error:
            return path, '', type(error).__name__
    with ThreadPoolExecutor(max_workers=8) as executor:
        for start in range(0, len(paths), 32):
            yield from executor.map(read, paths[start:start+32])


def verify_site(root=BASE_DIR/'dist'):
    root=Path(root).resolve()
    errors=[]; pages=list(root.rglob('*.html')); affiliate_count=0
    checked_references = {}
    if not pages: errors.append('No generated HTML')
    for path, content, read_error in read_pages(pages):
        relative=path.relative_to(root).as_posix()
        if read_error:
            errors.append(f'{relative}: read failure {read_error}'); continue
        page=Page()
        try:
            page.feed(content)
        except Exception as error:
            errors.append(f'{relative}: parse failure {type(error).__name__}'); continue
        if page.canonical != [DOMAIN+public_path(relative)]: errors.append(f'{relative}: wrong canonical')
        if page.headings != 1: errors.append(f'{relative}: expected one h1')
        if page.lang not in ('en','ru','he','es'): errors.append(f'{relative}: language missing')
        if set(page.alternates) != {'en','ru','he','es','x-default'}: errors.append(f'{relative}: alternate languages missing')
        if len(page.ids) != len(set(page.ids)): errors.append(f'{relative}: duplicate element IDs')
        for link in page.links:
            u=urlparse(link)
            if u.scheme in ('mailto','tel') or (u.netloc and u.netloc != urlparse(DOMAIN).netloc): continue
            if not u.path: continue
            cache_key = ('' if u.path.startswith('/') or u.netloc else str(path.parent), u.path)
            if cache_key in checked_references:
                if not checked_references[cache_key]: errors.append(f'{relative}: missing/unsafe reference {link}')
                continue
            target=(root/unquote(u.path).lstrip('/') if u.path.startswith('/') or u.netloc else path.parent/unquote(u.path)).resolve()
            if target.is_dir(): target=target/'index.html'
            elif not target.is_file() and target.suffix == '': target=target.with_suffix('.html')
            valid = root in target.parents and target.is_file()
            checked_references[cache_key] = valid
            if not valid: errors.append(f'{relative}: missing/unsafe reference {link}')
        for link in page.affiliates:
            affiliate_count+=1
            if not affiliate_key(link): errors.append(f'{relative}: invalid affiliate link')
        errors.extend(f'{relative}: {error}' for error in page.errors)
    for p in root.rglob('*'):
        if p.is_file() and (p.suffix.lower() not in ('.html','.json','.webp','.jpg','.jpeg','.png','.svg','.css','.js','.txt','.xml') and p.name not in ('CNAME','_headers','_redirects')):
            errors.append('Non-public file in artifact: '+str(p.relative_to(root)))
        if any(part.startswith('.') for part in p.relative_to(root).parts): errors.append('Hidden file in public artifact')
    try:
        sitemap=ET.parse(root/'sitemap.xml')
        for loc in sitemap.findall('.//{*}loc'):
            if not loc.text.startswith(DOMAIN+'/'): errors.append('Foreign sitemap domain')
            path=root/loc.text.removeprefix(DOMAIN+'/')
            if path.is_dir(): path=path/'index.html'
            elif not path.is_file(): path=path.with_suffix('.html')
            if not path.is_file(): errors.append('Missing sitemap target')
        expected = json.loads((root/'build-info.json').read_text(encoding='utf-8'))['products']
        for lang in ('en', 'ru', 'he', 'es'):
            rss_path = root / ('rss.xml' if lang == 'en' else f'rss_{lang}.xml')
            items = ET.parse(rss_path).findall('./channel/item')
            if len(items) != expected:
                errors.append(f'{rss_path.name}: catalog count mismatch')
            for item in items:
                enclosure = item.find('enclosure')
                if enclosure is None:
                    errors.append(f'{rss_path.name}: missing image enclosure'); continue
                url = enclosure.get('url', '')
                if not url.startswith(DOMAIN + '/assets/'):
                    errors.append(f'{rss_path.name}: foreign or unsafe image'); continue
                image = root / url.removeprefix(DOMAIN + '/')
                if not image.is_file() or enclosure.get('type') != 'image/webp' or enclosure.get('length') != str(image.stat().st_size):
                    errors.append(f'{rss_path.name}: incorrect image format/length')
            if not (root / ('' if lang == 'en' else lang) / 'returns.html').is_file():
                errors.append(f'{lang}: returns page missing')
        for name in ('google_feed.xml', 'google_feed_es.xml'):
            if ET.parse(root / name).findall('./channel/item'):
                errors.append('Unsupported merchant offers must not be exported')
        integrations = json.loads((BASE_DIR/'data/site_integrations.json').read_text(encoding='utf-8'))
        key = integrations.get('indexnow_key')
        if key and (root / (key + '.txt')).read_text(encoding='utf-8').strip() != key:
            errors.append('IndexNow verification key mismatch')
        feed=json.loads((root/'feed.json').read_text(encoding='utf-8'))
        if not all(item.get('content_text') or item.get('content_html') for item in feed['items']): errors.append('Invalid JSON Feed content')
        if len({item['id'] for item in feed['items']}) != len(feed['items']): errors.append('Duplicate feed IDs')
    except (OSError,ValueError,ET.ParseError): errors.append('Invalid feed or sitemap')
    if errors:
        raise ValueError('Site verification failed:\n'+'\n'.join(errors[:40]))
    print(f'[Verify] {len(pages)} pages, {affiliate_count} original affiliate links, internal assets, feeds and sitemap passed.')
    return {'pages':len(pages),'affiliate_links':affiliate_count,'errors':0}


if __name__ == '__main__':
    verify_site()
