"""One honest copy source for local social drafts. This module never sends posts."""
from urllib.parse import urlencode
from dealvault_core import DOMAIN, DATA_DIR, read_json, page_path, public_path, product_title
from site_content import COPY


def social_text(product,lang='en',source='social',domain=DOMAIN):
    c=COPY[lang]
    query=urlencode({'utm_source':source,'utm_medium':'social','utm_campaign':'collection','utm_content':product['slug']})
    link=f'{domain}{public_path(page_path(lang,product["slug"]))}?{query}'
    editorial=product.get('editorial') or read_json(DATA_DIR/'editorial.json',{'products':{}})['products'].get(product['id'],{})
    purpose=editorial.get('use_i18n',{}).get(lang,'')
    check=editorial.get('check_i18n',{}).get(lang,'')
    return (f'{product_title(product,lang)}\n\n'
            f'{purpose}\n{c["before"]}: {check}\n\n'
            f'{c["reference"]}: ${product["price_usd"]:.2f} USD\n'
            f'{c["price_note"]}\n\n{c["affiliate"]}\n\n{link}')
