import copy
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from business_health import analyse_periods
from dealvault_core import DATA_DIR, read_json, write_json
from published_routes import known_routes
from build_modern_hub import SiteBuilder, product_image, legacy_photo
from PIL import Image, UnidentifiedImageError
from product_selection import evaluate_candidate, rank_candidates, demand_signal
from selection_fixture import evidence
from verify_deployment import verify_deployment
from dealvault_core import DOMAIN


class EvidenceRobustnessTests(unittest.TestCase):
    def test_offline_rotation_cannot_silently_contact_marketplace(self):
        from dealvault_pipeline import run
        with patch('dealvault_pipeline.recover_transaction') as recover:
            with self.assertRaisesRegex(ValueError,'Offline mode'):
                run(offline=True,rotate=1)
            recover.assert_not_called()
    def setUp(self):
        self.p,self.snap=evidence({'id':'fixture','item_id':'1005001234567','source':'portals','reviewed':True,'source_evidence':'Synthetic identity evidence'})

    def test_malformed_records_are_rejected_not_a_pipeline_crash(self):
        for record in (None,[],1,'capture'):
            with self.subTest(record=record):self.assertFalse(evaluate_candidate(record,self.snap)['eligible'])
        for field in ('selection','offer','ad_review','editorial'):
            for value in ([],['x'],'not a mapping',True):
                p=copy.deepcopy(self.p);p[field]=value
                with self.subTest(field=field,value=value):self.assertFalse(evaluate_candidate(p,self.snap)['eligible'])
        self.assertEqual(len(rank_candidates([None,self.p],snapshots=self.snap)),2)

    def test_null_evidence_fields_are_rejected(self):
        for group,field in [('offer','evidence_text'),('ad_review','notes'),('ad_review','query'),('editorial','use_i18n')]:
            p=copy.deepcopy(self.p);p[group][field]=None
            with self.subTest(field=field):self.assertFalse(evaluate_candidate(p,self.snap)['eligible'])

    def test_item_id_must_be_exact_path_not_substring_or_query(self):
        for url in ('https://www.aliexpress.com/item/10050012345670.html','https://www.aliexpress.com/?id=1005001234567','https://www.aliexpress.com/item/1.html?other=1005001234567'):
            self.p['offer']['source_url']=url
            self.assertIn('EXACT_VARIANT_AND_DESTINATION_REQUIRED',evaluate_candidate(self.p,self.snap)['reasons'])

    def test_invalid_demand_records_do_not_break_valid_ones(self):
        self.assertIsNone(demand_signal({'terms':None},'fixture'))
        snap=copy.deepcopy(self.snap[0]);snap['weeks'].append(None)
        self.assertIsNotNone(demand_signal(snap,'test-need'))
        snap['terms']=[None];self.assertIsNone(demand_signal(snap,'test-need'))


class PublishedRouteTests(unittest.TestCase):
    def test_old_route_survives_without_price_or_affiliate_link(self):
        db=read_json(DATA_DIR/'products.json')
        old=db['products'][0]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'routes.json';write_json(path,[old])
            routes=known_routes(db['products'][1:],path)
            self.assertEqual(len(routes),len(db['products']))
            self.assertNotIn('affiliate_url',routes[0]);self.assertNotIn('price_usd',routes[0])
            builder=SiteBuilder(db,Path(temp)/'site')
            builder.images.update({name:f'assets/{name}' for name in ('modern.css','vault.css','modern_app.js','object_studio.js','tracking.js','icon.svg')})
            builder.images[old['image']]='assets/photo.webp'
            builder.archived_deal(old,'en')
            html=(Path(temp)/'site'/'deals'/f'{old["slug"]}.html').read_text(encoding='utf-8')
            self.assertIn('noindex,follow',html)
            self.assertNotIn('data-aff-id',html)
            self.assertNotIn(old['affiliate_url'],html)
            self.assertIn('hreflang="he"',html)

    def test_unsafe_archive_slug_cannot_write_outside_site(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'routes.json';write_json(path,[])
            with self.assertRaises(ValueError):known_routes([{'slug':'../../evil'}],path)


class ImageAdmissionTests(unittest.TestCase):
    def test_imported_avif_with_jpeg_name_becomes_real_public_jpeg(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            Image.new('RGB',(10,10),'blue').save(root/'import.jpg',format='AVIF')
            legacy_photo(root/'import.jpg',root/'public.jpg')
            with Image.open(root/'public.jpg') as result:
                self.assertEqual(result.format,'JPEG');self.assertEqual(result.size,(10,10))
    def test_photo_decoder_accepts_png_but_rejects_non_photo_and_animation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            Image.new('RGB',(10,10),'blue').save(root/'photo.png')
            with product_image(root/'photo.png') as image:self.assertEqual(image.size,(10,10))
            # A harmless PPM disguised with a photo extension must not load an unused plugin.
            (root/'disguised.jpg').write_bytes(b'P6\n1 1\n255\n\x00\x00\x00')
            with self.assertRaises(UnidentifiedImageError):
                with product_image(root/'disguised.jpg'):pass
            Image.new('RGB',(10,10),'blue').save(root/'animation.png',save_all=True,append_images=[Image.new('RGB',(10,10),'red')],duration=100)
            with self.assertRaisesRegex(ValueError,'static image'):
                with product_image(root/'animation.png'):pass


class RevenueEvidenceTests(unittest.TestCase):
    def period(self):
        return {'start':'2026-01-01','end':'2026-01-07','currency':'USD','evidence':{}}
    def test_no_data_does_not_become_zero_income(self):
        result=analyse_periods([self.period()])[0]
        self.assertIsNone(result['paid_commission']);self.assertIsNone(result['cash_after_recorded_costs'])
    def test_zero_and_positive_amounts_need_evidence(self):
        p=self.period()
        for n in (0,25):
            p['paid_commission']=n
            with self.assertRaises(ValueError):analyse_periods([p])
    def test_cash_does_not_use_pending_or_approved_commission(self):
        p=self.period();p.update(paid_commission=10,approved_commission=90,ad_spend=2,other_costs=3)
        p['evidence']={k:'fixture report' for k in ('paid_commission','approved_commission','ad_spend','other_costs')}
        self.assertEqual(analyse_periods([p])[0]['cash_after_recorded_costs'],5)
    def test_different_channels_do_not_make_a_fake_epc(self):
        p=self.period();p.update(partner_clicks=100,approved_commission=20)
        p['evidence']={k:'fixture report' for k in ('partner_clicks','approved_commission')}
        self.assertIsNone(analyse_periods([p])[0]['approved_epc'])
        p['attribution_scope']='matched_cohort'
        self.assertEqual(analyse_periods([p])[0]['approved_epc'],.2)
    def test_duplicate_periods_and_negative_amounts_are_rejected(self):
        with self.assertRaises(ValueError):analyse_periods([self.period(),self.period()])
        p=self.period();p['paid_commission']=-1
        with self.assertRaises(ValueError):analyse_periods([p])


class DeploymentVerificationTests(unittest.TestCase):
    def test_stale_or_uninstrumented_release_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets').mkdir()
            for name in ('build-info.json','robots.txt','sitemap.xml'):
                (root/name).write_text('fixture',encoding='utf-8')
            write_json(root/'feed.json',{'items':[{'url':DOMAIN+'/deals/current-product'}]})
            def getter(path):
                file=root/path.lstrip('/')
                if file.is_file():return 200,file.read_bytes(),{}
                for lang in ('en','ru','he','es'):
                    route='/' if lang=='en' else f'/{lang}/'
                    if path==route:return 200,f'<html lang="{lang}"><a href="{DOMAIN}{route}">static.cloudflareinsights.com/beacon.min.js'.encode(),{'X-Content-Type-Options':'nosniff','Content-Security-Policy':"frame-ancestors 'none'"}
                if path=='/deals/current-product':return 200,b'data-aff-id',{}
                return 404,b'',{}
            self.assertEqual(verify_deployment(root,getter)['status'],'passed')
            def stale(path):
                return (200,b'older build',{}) if path=='/build-info.json' else getter(path)
            with self.assertRaisesRegex(ValueError,'does not match'):verify_deployment(root,stale)
            def no_beacon(path):
                status,body,headers=getter(path)
                return status,body.replace(b'static.cloudflareinsights.com/beacon.min.js',b''),headers
            with self.assertRaisesRegex(ValueError,'beacon missing'):verify_deployment(root,no_beacon)


if __name__=='__main__':unittest.main()
