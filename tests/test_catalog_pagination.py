import copy
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from build_modern_hub import SiteBuilder, catalog_path
from dealvault_core import DATA_DIR, read_json, public_path, DOMAIN


class CatalogPaginationTests(unittest.TestCase):
    def test_static_pages_cover_every_product_once_and_keep_heading_before_data(self):
        db=read_json(DATA_DIR/'products.json')
        db['products']=copy.deepcopy(db['products'][:7])
        with tempfile.TemporaryDirectory() as tmp, patch('build_modern_hub.CATALOG_PAGE_SIZE',3):
            builder=SiteBuilder(db,tmp)
            builder.prepare_assets()
            for lang in ('en','ru','he','es'):
                seen=[]
                for number in (1,2,3):
                    builder.index(lang,number)
                    page=(Path(tmp)/catalog_path(lang,number)).read_text(encoding='utf-8')
                    self.assertLess(len(page.encode()),1_000_000)
                    self.assertLess(page.index('<h1'),page.index('id="products-db"'))
                    seen+=re.findall(r'<article[^>]+data-id="([^"]+)"',page)
                    self.assertIn('href="'+DOMAIN+public_path(catalog_path(lang,number))+'"',page)
                    for other in ('en','ru','he','es'):
                        self.assertIn('href="'+public_path(catalog_path(other,number))+'"',page)
                self.assertEqual(seen,[p['id'] for p in db['products']])
                full=json.loads((Path(tmp)/builder.catalog_assets[lang]).read_text(encoding='utf-8'))
                self.assertEqual(len(full['products']),7)
                self.assertEqual(len(re.findall('<article ',full['cards'])),7)
                self.assertNotIn('price_usd',json.dumps(full))
                for p in db['products']:
                    self.assertEqual(full['paths'][p['id']],public_path(('' if lang=='en' else lang+'/')+'deals/'+p['slug']+'.html'))
