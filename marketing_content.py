"""One honest copy source for local social drafts. This module never sends posts."""
from dealvault_core import DOMAIN, page_path, product_title
from site_content import COPY


def social_text(product,lang='en',source='social',domain=DOMAIN):
    c=COPY[lang]
    link=f'{domain}/{page_path(lang,product["slug"])}?utm_source={source}&utm_medium=social&utm_campaign=collection'
    return (f'{product_title(product,lang)}\n\n'
            f'{c["reference"]}: ${product["price_usd"]:.2f} USD\n'
            f'{c["price_note"]}\n\n{c["affiliate"]}\n\n{link}')
