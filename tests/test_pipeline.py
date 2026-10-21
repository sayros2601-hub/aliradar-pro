import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
from dealvault_core import DATA_DIR, affiliate_key, read_json, validate_catalog, write_json
from link_health_guard import check_single_link, audit_catalog
from build_modern_hub import script_json, build_site
import daily_rotator as rotation
from marketing_content import social_text
from social_posters import format_telegram_caption


class Response(io.BytesIO):
    def __init__(self,code=302,location=None):
        super().__init__(b'')
        self.code=code
        self.headers={'Location':location} if location else {}


class Opener:
    def __init__(self,*responses): self.responses=iter(responses)
    def open(self,*args,**kwargs):
        response=next(self.responses)
        if isinstance(response,Exception): raise response
        return response


class LinkTests(unittest.TestCase):
    def setUp(self): self.product={'id':'test','slug':'test','affiliate_url':'https://s.click.aliexpress.com/e/_genuine'}
    def check(self,*responses): return check_single_link(self.product,Opener(*responses))
    def test_timeout_is_unknown(self):
        self.assertEqual(self.check(TimeoutError())['status'],'UNKNOWN')
    def test_200_challenge_is_unknown(self):
        self.assertEqual(self.check(Response(200))['status'],'UNKNOWN')
    def test_403_is_unknown(self):
        self.assertEqual(self.check(Response(403))['status'],'UNKNOWN')
    def test_404_is_unavailable(self):
        self.assertEqual(self.check(Response(404))['status'],'UNAVAILABLE')
    def test_homepage_is_unavailable(self):
        self.assertEqual(self.check(Response(302,'https://best.aliexpress.com/'))['status'],'UNAVAILABLE')
    def test_product_redirect_resolves_without_claiming_stock(self):
        result=self.check(Response(302,'https://www.aliexpress.com/item/1005001234567.html?aff_fsk=original'))
        self.assertEqual(result['status'],'RESOLVED'); self.assertEqual(result['item_id'],'1005001234567')
        self.assertEqual(result['reason'],'PRODUCT_DESTINATION_ONLY')
    def test_relative_intermediate_redirect(self):
        self.assertEqual(self.check(Response(302,'/intermediate'),Response(302,'https://www.aliexpress.com/item/1005001234567.html'))['status'],'RESOLVED')
    def test_foreign_domain_never_followed(self):
        self.assertEqual(self.check(Response(302,'https://aliexpress.com.attacker.test/item/1005001234567.html'))['status'],'UNKNOWN')
    def test_wrong_product_id(self):
        self.product['item_id']='1005007654321'
        self.assertEqual(self.check(Response(302,'https://www.aliexpress.com/item/1005001234567.html'))['status'],'MISMATCH')
    def test_audit_preserves_catalog_and_order(self):
        before=copy.deepcopy(self.product)
        with patch('link_health_guard.check_single_link',return_value={'id':'test','status':'UNKNOWN'}):
            result=audit_catalog([self.product],write=False)
        self.assertEqual(self.product,before); self.assertEqual(result['summary'],{'UNKNOWN':1})
    def test_affiliate_host_validation(self):
        self.assertIsNone(affiliate_key('https://s.click.aliexpress.com.attacker.test/e/_key'))
        self.assertIsNone(affiliate_key('javascript:alert(1)'))
        self.assertIsNone(affiliate_key('https://user@s.click.aliexpress.com/e/_key'))


class DataTests(unittest.TestCase):
    def test_marketing_preserves_original_link_and_uses_localized_page(self):
        product=read_json(DATA_DIR/'products.json')['products'][0]
        caption,buttons=format_telegram_caption(product,'ru')
        self.assertIn('/ru/deals/'+product['slug'],caption)
        self.assertEqual(buttons['inline_keyboard'][0][0]['url'],product['affiliate_url'])
        for unsupported in ['AEIL02','Free Shipping','4.8+','% OFF']:
            self.assertNotIn(unsupported,caption)
    def test_script_json_cannot_end_script(self):
        payload={'title':'</script><img src=x onerror=alert(1)>&"'}
        encoded=script_json(payload)
        self.assertNotIn('<',encoded); self.assertEqual(json.loads(encoded),payload)
    def test_duplicate_unrelated_links_fail_build(self):
        db=read_json(DATA_DIR/'products.json')
        db['products'][1]['affiliate_url']=db['products'][0]['affiliate_url']
        with self.assertRaises(ValueError): validate_catalog(db)
    def test_empty_catalog_fails(self):
        with self.assertRaises(ValueError): validate_catalog({'products':[]})
    def test_mass_link_failure_cannot_replace_last_build(self):
        db=read_json(DATA_DIR/'products.json')
        report={'results':[{'id':p['id'],'affiliate_url':p['affiliate_url'],'status':'UNAVAILABLE'} for p in db['products']]}
        with patch('build_modern_hub.read_json',return_value=report):
            with self.assertRaisesRegex(ValueError,'Unusual link failure'):
                build_site(db=db)
    def test_atomic_json_preserves_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.json'; write_json(path,{'text':'עברית / Русский'})
            self.assertEqual(read_json(path),{'text':'עברית / Русский'})
            self.assertEqual(list(Path(tmp).glob('*.tmp')),[])


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.db=read_json(DATA_DIR/'products.json')
        self.files={name:self.root/filename for name,filename in [('PRODUCTS_FILE','products.json'),('RESERVE_FILE','reserve.json'),('LOG_FILE','log.json'),('JOURNAL','pending.json')]}
        self.patches=[patch.object(rotation,name,path) for name,path in self.files.items()]
        for p in self.patches:p.start()
        write_json(self.files['PRODUCTS_FILE'],self.db); write_json(self.files['RESERVE_FILE'],[])
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def snapshot(self): return {p.name:p.read_bytes() for p in self.root.iterdir()}
    def candidate(self):
        p=copy.deepcopy(self.db['products'][0]); p.update(id='new-test',slug='new-test',affiliate_url='https://s.click.aliexpress.com/e/_reviewed',source='portals',reviewed=True,item_id='1005001234567',source_evidence='Imported from Portals record with matching item id')
        return p
    def test_dry_run_writes_nothing(self):
        write_json(self.files['RESERVE_FILE'],[self.candidate()]); before=self.snapshot()
        rotation.rotate_deals(1,True,checker=lambda p:{'status':'RESOLVED'})
        self.assertEqual(before,self.snapshot())
    def test_placeholder_is_not_admitted(self):
        candidate=self.candidate(); candidate['source']='unverified'; write_json(self.files['RESERVE_FILE'],[candidate]); before=self.snapshot()
        self.assertEqual(rotation.rotate_deals(1,checker=lambda p:{'status':'RESOLVED'}),[])
        self.assertEqual(before,self.snapshot())
    def test_unknown_candidate_is_not_admitted(self):
        write_json(self.files['RESERVE_FILE'],[self.candidate()]); before=self.snapshot()
        self.assertEqual(rotation.rotate_deals(1,checker=lambda p:{'status':'UNKNOWN'}),[])
        self.assertEqual(before,self.snapshot())
    def test_fixed_size_idempotent_and_transactional(self):
        write_json(self.files['RESERVE_FILE'],[self.candidate()])
        rotation.rotate_deals(1,checker=lambda p:{'status':'RESOLVED'})
        db=read_json(self.files['PRODUCTS_FILE'])
        self.assertEqual(len(db['products']),len(self.db['products']))
        self.assertEqual(db['products'][0]['id'],'new-test')
        before=self.snapshot(); rotation.rotate_deals(1,checker=lambda p:{'status':'RESOLVED'})
        self.assertEqual(before,self.snapshot()); self.assertFalse(self.files['JOURNAL'].exists())
    def test_invalid_count(self):
        with self.assertRaises(ValueError): rotation.rotate_deals(-1)
    def test_interrupted_transaction_recovers_all_files(self):
        write_json(self.files['JOURNAL'],{'catalog':self.db,'reserve':[self.candidate()],'log':[{'date':'2026-01-01'}]})
        rotation.recover_transaction()
        self.assertEqual(read_json(self.files['RESERVE_FILE'])[0]['id'],'new-test')
        self.assertEqual(read_json(self.files['LOG_FILE']),[{'date':'2026-01-01'}])
        self.assertFalse(self.files['JOURNAL'].exists())


if __name__ == '__main__': unittest.main()
