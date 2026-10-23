"""Headless functional browser checks; no visible windows or live social/affiliate clicks."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dealvault_core import DATA_DIR, DOMAIN, read_json
from preview_server import PagesHandler


class QuietHandler(PagesHandler):
    def log_message(self,*args): pass


def run(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    db=read_json(DATA_DIR/'products.json'); expected=len(db['products']); first=db['products'][0]
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'dist')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    errors=[]; checks=[]
    def passed(name): checks.append(name)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1100},color_scheme='light')
            context.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:async(text)=>{window.__copied=text}}})")
            page=context.new_page(); page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base+'/index.html',wait_until='networkidle')
            assert page.locator('.product-card:visible').count()==expected
            assert page.locator('html').get_attribute('lang')=='en'
            assert page.locator('img').first.evaluate('(img)=>img.complete && img.naturalWidth > 0')
            page.screenshot(path=str(output/'dealvault-desktop.png'),full_page=False)
            passed('English static collection and local product photos')
            heart=page.locator('[data-save-id]').first
            heart.click(); assert heart.get_attribute('aria-pressed')=='true'
            page.locator('#saved-filter').click()
            assert page.locator('#product-grid .product-card:visible').count()>=1
            page.reload(wait_until='networkidle')
            assert page.locator('#product-grid .product-card:visible').count()>=1
            page.locator('[data-save-id]:visible').click()
            assert page.locator('#empty-state').is_visible()
            page.locator('#clear-filters').click()
            assert page.locator('#product-grid .product-card:visible').count()==expected
            passed('Saved items persist, filter through URL, remove cleanly and reset')
            page.locator('#motion-toggle').click()
            assert page.locator('html').get_attribute('data-motion')=='off'
            page.reload(wait_until='networkidle')
            assert page.locator('html').get_attribute('data-motion')=='off'
            assert page.locator('.orbit-ring').first.evaluate("e=>getComputedStyle(e).animationName")=='none'
            page.locator('#motion-toggle').click()
            page.locator('#country-select').select_option('IL')
            assert page.locator('html').get_attribute('lang')=='en'
            assert page.locator('#currency-select').count()==0
            page.reload(wait_until='networkidle')
            assert page.locator('#country-select').input_value()=='IL'
            passed('Motion preference persists; country choice does not change English')
            russian=browser.new_context(locale='ru-RU',reduced_motion='reduce',color_scheme='light')
            rp=russian.new_page();rp.goto(base+'/',wait_until='networkidle')
            assert rp.locator('html').get_attribute('lang')=='en'
            assert rp.locator('#motion-toggle').is_hidden()
            assert rp.locator('.orbit-ring').first.evaluate("e=>getComputedStyle(e).animationName")=='none'
            russian.close()
            passed('English entry even with Russian browser; reduced motion disables animation')

            page.locator('#global-search-input').fill('ugreen')
            assert page.locator('#product-grid .product-card:visible').count()>=1
            page.locator('#global-search-input').fill('definitely-no-match')
            assert page.locator('#empty-state').is_visible()
            page.locator('#clear-filters').click()
            page.locator('[data-cat=tech]').click()
            assert all(value=='tech' for value in page.locator('#product-grid .product-card:visible').evaluate_all('(els)=>els.map(x=>x.dataset.category)'))
            page.locator('[data-cat=all]').click()
            passed('Search, empty state, reset and category filters')
            assert page.locator('[data-money], #price-select, #sort-select, #currency-select').count()==0
            assert 'price_usd' not in page.locator('#products-db').text_content()
            assert page.locator('.price-unavailable').count()==expected
            page.goto(base+'/index.html?budget=10&sort=price_asc',wait_until='networkidle')
            assert page.locator('#product-grid .product-card:visible').count()==expected
            page.locator('#global-search-input').fill('ugreen')
            assert 'budget=' not in page.url and 'sort=' not in page.url
            passed('Unverified prices are absent; old price-filter URLs cannot hide items')
            page.goto(base+'/index.html?utm_source=qa',wait_until='networkidle')
            quick=page.locator('[data-modal-id]').first; quick.focus(); quick.click()
            assert page.locator('#product-modal').is_visible()
            assert page.locator('#product-modal [data-money]').count()==0
            assert page.locator('#product-modal [data-aff-id]').get_attribute('href')==first['affiliate_url']
            page.locator('#product-modal [data-share=copy]').click()
            assert page.evaluate('window.__copied')==f'{DOMAIN}/deals/{first["slug"]}'
            page.keyboard.press('Escape')
            assert not page.locator('#product-modal').is_visible()
            assert not page.evaluate('location.hash')
            assert page.evaluate('document.activeElement.hasAttribute("data-modal-id")')
            page.locator('[data-modal-id]').first.click()
            page.go_back()
            assert not page.locator('#product-modal').is_visible()
            passed('Modal, exact partner URL, canonical share, Escape, focus restore and browser Back')
            page.goto(base+f'/index.html?q=ugreen#{first["slug"]}',wait_until='networkidle')
            assert page.locator('#product-modal').is_visible()
            assert page.locator('#product-modal [data-money]').count()==0
            page.keyboard.press('Escape')
            passed('Direct search URLs and product deep links')
            for lang in ('ru','he','es','en'):
                prefix='' if lang=='en' else lang+'/'
                page.goto(base+'/'+prefix+'index.html',wait_until='networkidle')
                assert page.locator('html').get_attribute('lang')==lang
                assert page.locator('html').get_attribute('dir')==('rtl' if lang=='he' else 'ltr')
                assert page.locator('#product-grid .product-card:visible').count()==expected
                page.locator('#product-grid h3 a').first.click()
                assert '/deals/' in page.url
                assert page.locator('.buy-button').get_attribute('href')==first['affiliate_url']
                page.locator('.share-row [data-share=copy]').click()
                assert page.evaluate('window.__copied')==f'{DOMAIN}/{prefix}deals/{first["slug"]}'
            passed('All four homepages, translated deal pages and correct language share URLs')
            page.goto(base+'/index.html?utm_campaign=test',wait_until='networkidle')
            page.locator('[data-lang-link=ru]').click()
            page.wait_for_load_state('networkidle')
            assert 'utm_campaign=test' in page.url
            page.locator('#theme-toggle').click()
            page.reload(wait_until='networkidle')
            assert page.locator('html').get_attribute('data-theme')=='dark'
            assert page.locator('#currency-select').count()==0
            passed('Campaign context and persisted theme')
            for width in (360,390,768,1440):
                page.set_viewport_size({'width':width,'height':900})
                for lang in ('en','he','ru','es'):
                    prefix='' if lang=='en' else lang+'/'
                    page.goto(base+'/'+prefix+'index.html',wait_until='networkidle')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'), f'Overflow {width} {lang}'
                    if width==390 and lang=='he': page.screenshot(path=str(output/'dealvault-mobile-hebrew.png'))
                    if width==390 and lang=='ru': page.screenshot(path=str(output/'dealvault-mobile-russian.png'))
                    if width==1440 and lang=='he': page.screenshot(path=str(output/'dealvault-hebrew.png'))
                if width==390:
                    page.locator('[data-modal-id]').first.click()
                    assert page.locator('#product-modal').bounding_box()['width']<=width
                    page.screenshot(path=str(output/'dealvault-mobile-modal.png'))
                    page.keyboard.press('Escape')
            passed('16 viewport/language combinations, RTL and mobile quick view')
            blocked=browser.new_context()
            blocked.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}});Object.defineProperty(window,'sessionStorage',{get(){throw new Error('blocked')}})")
            bp=blocked.new_page(); bp.on('pageerror',lambda error:errors.append(str(error)))
            bp.goto(base+'/index.html',wait_until='networkidle')
            assert bp.locator('.product-card:visible').count()==expected
            bp.locator('#theme-toggle').click()
            bp.locator('[data-save-id]').first.click();bp.locator('#saved-filter').click()
            assert bp.locator('#product-grid .product-card:visible').count()>=1
            passed('Storage disabled: catalog, theme and saved filtering still work')
            nojs=browser.new_context(java_script_enabled=False)
            np=nojs.new_page(); np.goto(base+'/index.html',wait_until='networkidle')
            assert np.locator('.product-card').count()==expected
            np.locator('#product-grid h3 a').first.click()
            assert np.locator('.buy-button').get_attribute('href')==first['affiliate_url']
            passed('JavaScript disabled: complete catalog and purchase links remain usable')
            context.close(); blocked.close(); nojs.close(); browser.close()
        assert not errors,errors
        report={'checks':checks,'passed':len(checks),'javascript_errors':errors,'visible_windows':0}
        (output/'browser-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return report
    finally:
        server.shutdown(); server.server_close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
