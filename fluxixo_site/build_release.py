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
    if rel in exclude or rel.startswith('assets/images/watch-layers/') and rel.endswith('.png'):continue
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
for route in ['/','/index.html','/catalog/*','/categories/*','/products/*','/en/*','/es/*','/pt/*','/fr/*','/he/*','/rss.xml','/sitemap.xml']:
    headers+='\n'+route+'\n  Cache-Control: public, max-age=0, must-revalidate\n'
headers+='\n/drop-status.json\n  Cache-Control: no-store\n'
(RELEASE/'_headers').write_text(headers,encoding='utf-8')
for file in RELEASE.rglob('*.html'):
    text=file.read_text(encoding='utf-8')
    def update(match):
        attr,url=match.groups()
        path=urlsplit(url).path
        key=path.lstrip('/')
        if key not in mapping:return match.group(0)
        return attr+'="'+('/' if path.startswith('/') else '')+mapping[key]+'"'
    text=re.sub(r'(href|src)="([^"]+)"',update,text)
    file.write_text(text,encoding='utf-8')
manifest={f.relative_to(RELEASE).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in RELEASE.rglob('*') if f.is_file()}
(BASE/'release-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(BASE/'asset-map.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
print(json.dumps({'files':len(manifest),'versioned_assets':len(mapping)}))
