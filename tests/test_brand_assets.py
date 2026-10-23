import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from brand_assets import build_brand_icons
from build_modern_hub import SiteBuilder
from dealvault_core import DATA_DIR, DOMAIN, read_json
from verify_site import Page


class BrandTests(unittest.TestCase):
    def test_search_and_app_icons_have_real_supported_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            build_brand_icons(root)
            for name,size in [('favicon.png',96),('apple-touch-icon.png',180),
                              ('favicon-192.png',192),('favicon-512.png',512)]:
                with Image.open(root/name) as image:
                    self.assertEqual(image.format,'PNG')
                    self.assertEqual(image.size,(size,size))
            with Image.open(root/'favicon.ico') as image:
                self.assertEqual(image.format,'ICO')

    def test_site_name_is_explicit_and_product_preview_keeps_its_photo(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=read_json(DATA_DIR/'products.json')
            db['products']=db['products'][:1]
            builder=SiteBuilder(db,Path(tmp))
            builder.prepare_assets()
            home=builder.shell('en','index.html','Home','<main><h1>DealVault</h1></main>')
            page=Page(); page.feed(home)
            nodes=[n for block in page.json_blocks if isinstance(block,list) for n in block]
            site=next(n for n in nodes if n.get('@type')=='WebSite')
            self.assertEqual(site['name'],'DealVault')
            self.assertEqual(site['url'],DOMAIN+'/')
            self.assertIn(builder.images['brand/dealvault-cover.png'],home)
            p=builder.products[0]
            product=builder.shell('en','deals/'+p['slug']+'.html',p['title_i18n']['en'],'',slug=p['slug'])
            self.assertIn('property="og:image" content="'+DOMAIN+'/'+builder.images[p['image']]+'"',product)
            self.assertNotIn('"@type":"WebSite"',product)


if __name__=='__main__':
    unittest.main()
