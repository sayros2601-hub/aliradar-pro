"""Visible editorial names stay searchable without changing seller records."""
import copy
import tempfile
import unittest
from html.parser import HTMLParser
from build_modern_hub import SiteBuilder
from dealvault_core import DATA_DIR,read_json
from studio_content import display_title

class Card(HTMLParser):
    def __init__(self):super().__init__();self.search='';self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article':self.search=a.get('data-search','')
        if tag=='a' and 'data-aff-id' in a:self.links.append(a['href'])

class StudioTests(unittest.TestCase):
    def test_visible_label_and_seller_name_are_both_searchable_in_all_languages(self):
        db=read_json(DATA_DIR/'products.json');snapshot=copy.deepcopy(db)
        product=next(p for p in db['products'] if p['id']=='magnetic-levitating-3d-moon-lamp')
        with tempfile.TemporaryDirectory() as tmp:
            builder=SiteBuilder(db,tmp);builder.thumbnails[product['image']]='assets/photo.webp'
            for lang in ('en','ru','he','es'):
                card=Card();card.feed(builder.card(product,lang,'index.html'))
                self.assertIn(display_title(product,lang),card.search)
                self.assertIn(product['title_i18n'][lang],card.search)
                self.assertEqual(card.links,[product['affiliate_url']])
        self.assertEqual(db,snapshot)
