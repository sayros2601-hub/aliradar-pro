"""Check every generated page, local link, image, canonical and feed before release."""
from html.parser import HTMLParser
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


def verify_site(root=BASE_DIR/'dist'):
    root=Path(root).resolve()
    errors=[]; pages=list(root.rglob('*.html')); affiliate_count=0
    if not pages: errors.append('No generated HTML')
    for path in pages:
        relative=path.relative_to(root).as_posix()
        page=Page()
        try:
            page.feed(path.read_text(encoding='utf-8'))
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
            target=(root/unquote(u.path).lstrip('/') if u.path.startswith('/') or u.netloc else path.parent/unquote(u.path)).resolve()
            if target.is_dir(): target=target/'index.html'
            elif not target.is_file() and target.suffix == '': target=target.with_suffix('.html')
            if root not in target.parents or not target.is_file(): errors.append(f'{relative}: missing/unsafe reference {link}')
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
        ET.parse(root/'rss.xml')
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
