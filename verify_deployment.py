"""Verify our published artifact after deployment; never contacts marketplace links."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from dealvault_core import BASE_DIR, DOMAIN, LANGUAGES, public_path


def fetch(path):
    request = Request(DOMAIN+path, headers={'User-Agent':'DealVault-Deployment-Check/1.0','Cache-Control':'no-cache'})
    try:
        with urlopen(request,timeout=15) as response:
            return response.status,response.read(),dict(response.headers)
    except HTTPError as error:
        return error.code,error.read(),dict(error.headers)


def verify_deployment(root=BASE_DIR/'dist', getter=fetch):
    root=Path(root)
    # JSON and hashed static files remain byte-identical when Cloudflare injects analytics into HTML.
    paths=['build-info.json','robots.txt','sitemap.xml','feed.json']
    paths.extend(p.relative_to(root).as_posix() for p in (root/'assets').glob('*.js'))
    paths.extend(p.relative_to(root).as_posix() for p in (root/'assets').glob('*.css'))
    for path in paths:
        status,body,_=getter('/'+path)
        if status!=200 or hashlib.sha256(body).digest()!=hashlib.sha256((root/path).read_bytes()).digest():
            raise ValueError(f'Published artifact does not match: {path}')
    for lang in LANGUAGES:
        route='/' if lang=='en' else f'/{lang}/'
        status,body,headers=getter(route)
        text=body.decode('utf-8')
        if status!=200 or f'<html lang="{lang}"' not in text or f'href="{DOMAIN}{route}"' not in text:
            raise ValueError(f'Invalid public page: {route}')
        headers={k.lower():v for k,v in headers.items()}
        if headers.get('x-content-type-options')!='nosniff' or 'frame-ancestors' not in headers.get('content-security-policy',''):
            raise ValueError('Production security headers missing')
        if 'static.cloudflareinsights.com/beacon.min.js' not in text:
            raise ValueError('Cloudflare analytics beacon missing after deployment')
    sample=json.loads((root/'feed.json').read_text(encoding='utf-8'))['items'][0]['url']
    if not sample.startswith(DOMAIN+'/deals/'):raise ValueError('Unexpected product sample URL')
    status,body,_=getter(sample.removeprefix(DOMAIN))
    if status!=200 or b'data-aff-id' not in body:raise ValueError('Product landing page failed')
    for path in ('/this-page-does-not-exist-dealvault-check','/data/products.json','/.local/business/periods.json','/dealvault_core.py'):
        if getter(path)[0]!=404:raise ValueError(f'Private or missing route is public: {path}')
    print('[Deployment] Exact artifact, four languages, analytics beacon, headers, product page and private-path exclusions passed.')
    return {'status':'passed','checked_files':len(paths),'languages':4}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=BASE_DIR/'dist')
    args=parser.parse_args()
    for attempt in range(4):
        try:
            verify_deployment(args.root)
            break
        except (OSError,ValueError) as error:
            if attempt==3:raise
            print(f'[Deployment] Waiting for edge propagation: {type(error).__name__}')
            time.sleep(5)
