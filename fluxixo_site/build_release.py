"""Prepare a deployable copy. Internal editor stays in source, never in production."""
from pathlib import Path
import hashlib,json,re,shutil
from urllib.parse import urlsplit

BASE=Path(__file__).resolve().parent
SOURCE=BASE/'dist'
RELEASE=BASE/'release'
assert RELEASE.parent==BASE and RELEASE.name=='release'
if RELEASE.exists():
    # This exact staging path is disposable and always recreated from source.
    shutil.rmtree(RELEASE)
RELEASE.mkdir()
exclude={'editor.html','js/editor.js','css/editor.css'}
for file in SOURCE.rglob('*'):
    if not file.is_file():continue
    rel=file.relative_to(SOURCE).as_posix()
    # Keep raw AliExpress source originals out of Cloudflare Pages deployments (never rendered on public pages).
    if rel in exclude or rel.startswith('assets/originals/') or (rel.startswith('assets/images/watch-layers/') and rel.endswith('.png')):continue
    target=RELEASE/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(file,target)

# Content hashes in resource filenames prevent browsers/CDN mixing different releases.
mapping={}
for folder in ['js','css']:
    for file in (RELEASE/folder).glob('*'):
        if file.suffix not in ('.js','.css'):continue
        digest=hashlib.sha256(file.read_bytes()).hexdigest()[:12]
        hashed=file.with_name(file.stem+'.'+digest+file.suffix)
        shutil.copyfile(file,hashed)
        mapping[file.relative_to(RELEASE).as_posix()]=hashed.relative_to(RELEASE).as_posix()
favicon=RELEASE/'assets/favicon.svg'
hashed=favicon.with_name('favicon.'+hashlib.sha256(favicon.read_bytes()).hexdigest()[:12]+'.svg')
shutil.copyfile(favicon,hashed)
mapping['assets/favicon.svg']=hashed.relative_to(RELEASE).as_posix()
headers=(RELEASE/'_headers').read_text(encoding='utf-8')
headers=headers.replace('  Cache-Control: public, max-age=0, must-revalidate\n','')
for original,versioned in mapping.items():
    headers+='\n/'+versioned+'\n  Cache-Control: public, max-age=31536000, immutable\n'
for route in ['/','/index.html','/catalog/*','/categories/*','/products/*','/en/*','/es/*','/pt/*','/fr/*','/he/*','/rss.xml','/pinterest-new.xml','/sitemap.xml']:
    headers+='\n'+route+'\n  Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=60, must-revalidate\n'
headers+='\n/drop-status.json\n  Cache-Control: no-store\n'
headers+='\nhttps://*.dealvault.pages.dev/*\n  X-Robots-Tag: noindex, nofollow\n'
(RELEASE/'_headers').write_text(headers,encoding='utf-8')
_IMAGE_VERSION_PREFIXES = ('assets/thumbs/', 'assets/images/', 'assets/featured/')
_image_versions = {}


def version_image_url(url):
    """Append a content hash query tag to cached local images without changing canonical filenames."""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or parts.query:
        return url
    key = parts.path.lstrip('/')
    is_poster = key.startswith('assets/video/') and key.endswith('.poster.jpg')
    if not (key.startswith(_IMAGE_VERSION_PREFIXES) or is_poster):
        return url
    if key not in _image_versions:
        target = RELEASE / key
        _image_versions[key] = hashlib.sha256(target.read_bytes()).hexdigest()[:10] if target.is_file() else ''
    digest = _image_versions[key]
    if not digest:
        return url
    prefix = '/' if parts.path.startswith('/') else ''
    suffix = f'#{parts.fragment}' if parts.fragment else ''
    return f'{prefix}{key}?v={digest}{suffix}'


for file in RELEASE.rglob('*.html'):
    text = file.read_text(encoding='utf-8')

    def update(match):
        attr, url = match.groups()
        path = urlsplit(url).path
        key = path.lstrip('/')
        if key in mapping:
            return attr + '="' + ('/' if path.startswith('/') else '') + mapping[key] + '"'
        if attr != 'href':
            versioned = version_image_url(url)
            if versioned != url:
                return f'{attr}="{versioned}"'
        return match.group(0)

    def update_srcset(match):
        items = []
        for candidate in match.group(1).split(','):
            tokens = candidate.strip().split()
            if not tokens:
                continue
            tokens[0] = version_image_url(tokens[0])
            items.append(' '.join(tokens))
        return f'srcset="{", ".join(items)}"'

    text = re.sub(r'(href|src|poster)="([^"]+)"', update, text)
    text = re.sub(r'srcset="([^"]+)"', update_srcset, text)
    file.write_text(text, encoding='utf-8')
manifest={f.relative_to(RELEASE).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in RELEASE.rglob('*') if f.is_file()}
(BASE/'release-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(BASE/'asset-map.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
print(json.dumps({'files':len(manifest),'versioned_assets':len(mapping)}))
