"""Private, local copy desk. It exports drafts; it cannot broadcast messages."""
from dealvault_core import BASE_DIR, DATA_DIR, LANGUAGES, read_json
from build_modern_hub import esc
from marketing_content import social_text
from site_content import LANG_NAMES


def build_operator_tools():
    db=read_json(DATA_DIR/'products.json')
    sections=[]
    for lang in LANGUAGES:
        posts=''.join(f'<article><h2>{esc(p["title_i18n"][lang])}</h2><textarea readonly rows="9">{esc(social_text(p,lang))}</textarea><button type="button">Copy draft</button></article>' for p in db['products'])
        sections.append(f'<section data-lang="{lang}" {"hidden" if lang != "en" else ""}>{posts}</section>')
    document='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DealVault — local copy desk</title><style>body{font:15px system-ui;background:#f7f7f2;color:#17241f;max-width:1000px;margin:35px auto;padding:20px}section{display:grid;grid-template-columns:1fr 1fr;gap:20px}[hidden]{display:none}article{padding:20px;background:white;border:1px solid #dfe4db;border-radius:14px}h2{font-size:16px}textarea{box-sizing:border-box;width:100%;padding:12px;font:13px system-ui}button,select{padding:10px 15px;margin:12px 0;cursor:pointer}@media(max-width:650px){section{grid-template-columns:1fr}}</style></head><body><h1>DealVault · Local copy desk</h1><p>Drafts only. No posts are sent or scheduled. Prices are unverified reference estimates.</p><label>Language <select id="lang">'''
    document+=''.join(f'<option value="{l}">{LANG_NAMES[l]}</option>' for l in LANGUAGES)+'</select></label>'+''.join(sections)
    document+='''<p id="status" role="status"></p><script>document.getElementById('lang').addEventListener('change',e=>document.querySelectorAll('section').forEach(s=>s.hidden=s.dataset.lang!==e.target.value));document.addEventListener('click',async e=>{if(e.target.tagName!=='BUTTON')return;const t=e.target.previousElementSibling;try{await navigator.clipboard.writeText(t.value);document.getElementById('status').textContent='Draft copied'}catch{t.focus();t.select();document.getElementById('status').textContent='Press Ctrl+C to copy'}})</script></body></html>'''
    (BASE_DIR/'promo_dispatcher.html').write_text(document,encoding='utf-8')
    print('[Copy desk] Local promo_dispatcher.html generated; excluded from public artifact.')


if __name__ == '__main__':
    build_operator_tools()
