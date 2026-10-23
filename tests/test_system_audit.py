"""Regression checks for the repeated whole-system audit; no external services."""
import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import xml.etree.ElementTree as ET

from dealvault_core import BASE_DIR, DATA_DIR, read_json, write_json, affiliate_key, recently_added
from build_modern_hub import SiteBuilder, build_site
from business_health import analyse_periods, build_report
from marketing_content import social_text
from site_content import COPY
from product_selection import evaluate_candidate
from selection_fixture import evidence
import import_portals
import build_operator_tools
import build_bulk_social_csvs
import marketing_content
import csv
from html import escape


class PublicPriceEvidenceTests(unittest.TestCase):
    def test_legacy_amounts_never_escape_into_pages_payload_feeds_or_drafts(self):
        db = read_json(DATA_DIR/'products.json')
        db['products'] = copy.deepcopy(db['products'][:1])
        db['products'][0]['price_usd'] = 987654.32
        with tempfile.TemporaryDirectory() as tmp:
            builder = SiteBuilder(db, tmp)
            builder.prepare_assets()
            self.assertNotIn('price_usd', builder.public_products[0])
            builder.feeds()
            for lang in ('en', 'ru', 'he', 'es'):
                builder.index(lang)
                builder.deal(db['products'][0], lang)
                prefix = Path(tmp)/('' if lang == 'en' else lang)
                for file in (prefix/'index.html', prefix/'deals'/(db['products'][0]['slug']+'.html')):
                    html = file.read_text(encoding='utf-8')
                    for forbidden in ('987654.32', 'price_usd', 'data-money=', 'id="price-select"', 'id="currency-select"'):
                        self.assertNotIn(forbidden, html)
                    self.assertIn(COPY[lang]['price_status'], html)
                    feed = 'rss.xml' if lang == 'en' else f'rss_{lang}.xml'
                    self.assertIn(f'href="/{feed}"', html)
                feed = Path(tmp)/('rss.xml' if lang == 'en' else f'rss_{lang}.xml')
                self.assertEqual(ET.parse(feed).findtext('./channel/language'), lang)
                self.assertNotIn('987654.32', feed.read_text(encoding='utf-8'))
                caption = social_text(db['products'][0], lang)
                self.assertNotIn('987654.32', caption)
                self.assertIn(COPY[lang]['price_note'], caption)

    def test_new_badges_expire_and_cannot_use_unknown_or_future_dates(self):
        now = datetime(2026, 10, 23, tzinfo=timezone.utc)
        for days, expected in ((1, True), (7, True), (8, False), (-1, False)):
            self.assertEqual(recently_added({'is_new':True,'added_at':(now-timedelta(days=days)).isoformat()},now),expected)
        self.assertFalse(recently_added({'is_new':True},now))
        self.assertFalse(recently_added({'is_new':True,'added_at':'2026-10-22'},now))


class SourcePreservationTests(unittest.TestCase):
    def test_build_output_cannot_replace_source_directories(self):
        for name in ('data','assets','tests','.local','dist.previous'):
            with self.subTest(name=name), patch('build_modern_hub.tempfile.mkdtemp') as stage:
                with self.assertRaisesRegex(ValueError,'Build destination'):
                    build_site(BASE_DIR/name, {'products':[]})
                stage.assert_not_called()

    def test_copy_desk_preserves_custom_dispatcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom = root/'promo_dispatcher.html'
            custom.write_text('Owner customization')
            with patch.object(build_operator_tools,'BASE_DIR',root), patch.object(build_operator_tools,'read_json',return_value={'products':[]}):
                output = build_operator_tools.build_operator_tools()
            self.assertEqual(custom.read_text(),'Owner customization')
            self.assertEqual(output,root/'.local/copy-desk.html')
            self.assertNotIn('unverified reference estimates',output.read_text(encoding='utf-8'))


class ImportAndEvidenceTests(unittest.TestCase):
    def test_same_observation_time_with_enriched_capture_is_not_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root/'products.json', {'products':[]})
            record = {'affiliate_url':'https://s.click.aliexpress.com/e/_capture',
                      'raw_title':'Captured organizer','observed_at':'2026-10-20T12:00:00Z'}
            with patch.object(import_portals, 'DATA_DIR', root):
                self.assertEqual(len(import_portals.stage_records([record])),1)
                for key,value in [('images',['https://example.invalid/photo.jpg']),
                                  ('editorial',{'use_i18n':{'en':'A documented use'}}),
                                  ('source_ref','new-export.json')]:
                    richer = {**record,key:value}
                    self.assertEqual(len(import_portals.stage_records([richer])),1)
                    self.assertEqual(import_portals.stage_records([richer]),[])
            self.assertEqual(len(read_json(root/'portals_inbox.json')),4)

    def test_new_observation_of_existing_product_is_kept_but_replay_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            url = 'https://s.click.aliexpress.com/e/_existing?original=A%2FB'
            db = {'products':[{'affiliate_url':url}]}
            write_json(root/'products.json',db)
            record = {'affiliate_url':url,'raw_title':'Captured organizer','observed_at':'2026-10-20T12:00:00Z','fields':{'item_price':10}}
            checker = Mock(return_value={'status':'SAVED_EVIDENCE_ONLY','item_id':'1005001234567'})
            with patch.object(import_portals,'DATA_DIR',root), patch('socket.create_connection',side_effect=AssertionError('No networking')):
                self.assertEqual(len(import_portals.stage_records([record],check_links=True,link_checker=checker)),1)
                self.assertEqual(import_portals.stage_records([record],check_links=True,link_checker=checker),[])
                new = {**record,'observed_at':'2026-10-21T12:00:00Z','fields':{'item_price':11}}
                self.assertEqual(len(import_portals.stage_records([new])),1)
            self.assertEqual(read_json(root/'products.json'),db)
            rows=read_json(root/'portals_inbox.json')
            self.assertEqual(len(rows),2)
            self.assertTrue(all(not r['reviewed'] for r in rows))
            self.assertTrue(all(r['affiliate_url']==url for r in rows))

    def test_control_characters_in_affiliate_url_cannot_be_normalized_into_valid_link(self):
        for value in ('\nhttps://s.click.aliexpress.com/e/_real','https://s.click.aliexpress.com/e/_real\n','https://s.click.aliexpress.com/e/_real?x=with space'):
            self.assertIsNone(affiliate_key(value))
        self.assertTrue(affiliate_key('https://s.click.aliexpress.com/e/_real?x=encoded%20space'))

    def test_malformed_selection_ids_and_nontext_variant_do_not_pass(self):
        product,snapshots=evidence({'id':'fixture','item_id':'1005001234567','source':'portals','reviewed':True,'source_evidence':'Synthetic source identity'})
        for key in ('country','need_id','demand_snapshot_id'):
            for value in ([],{},True):
                candidate=copy.deepcopy(product);candidate['selection'][key]=value
                self.assertFalse(evaluate_candidate(candidate,snapshots)['eligible'])
        for value in ({'id':'invented'},True,17):
            candidate=copy.deepcopy(product);candidate['offer']['variant_id']=value
            self.assertFalse(evaluate_candidate(candidate,snapshots)['eligible'])


class BusinessEvidenceTests(unittest.TestCase):
    def test_truthy_nontext_or_blank_reference_cannot_certify_revenue(self):
        for evidence_ref in (True,1,{},['report'],'   '):
            with self.subTest(evidence_ref=evidence_ref), self.assertRaises(ValueError):
                analyse_periods([{'start':'2026-01-01','end':'2026-01-02','currency':'USD','paid_commission':1,'evidence':{'paid_commission':evidence_ref}}])

    def test_empty_measurements_do_not_claim_revenue_was_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(Path(tmp)/'periods.json',{'periods':[{'start':'2026-01-01','end':'2026-01-02','currency':'USD','evidence':{}}]})
            self.assertEqual(build_report(tmp)['revenue_status'],'not_measured')


class DraftBatchTests(unittest.TestCase):
    def test_batch_reads_editorial_once_and_preserves_identical_copy(self):
        db=read_json(DATA_DIR/'products.json');db['products']=db['products'][:2]
        editorial=read_json(DATA_DIR/'editorial.json')
        expected={lang:[social_text(product,lang) for product in db['products']] for lang in ('en','ru','he','es')}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(build_bulk_social_csvs,'BASE_DIR',root), patch.object(build_bulk_social_csvs,'read_json',return_value=editorial) as reader, patch.object(marketing_content,'read_json',side_effect=AssertionError('Per-item disk read')):
                build_bulk_social_csvs.generate_csvs(db)
                reader.assert_called_once()
            for lang, texts in expected.items():
                with (root/'broadcasts/current'/f'dealvault_{lang}.csv').open(encoding='utf-8-sig',newline='') as stream:
                    rows=list(csv.DictReader(stream))
                self.assertEqual([row['Text'] for row in rows],texts)
            with patch.object(build_operator_tools,'BASE_DIR',root), patch.object(build_operator_tools,'read_json',side_effect=[db,editorial]) as reader, patch.object(marketing_content,'read_json',side_effect=AssertionError('Per-item disk read')):
                output=build_operator_tools.build_operator_tools()
                self.assertEqual(reader.call_count,2)
            text=output.read_text(encoding='utf-8')
            for captions in expected.values():
                for caption in captions:self.assertIn(escape(caption,quote=True),text)


if __name__ == '__main__':
    unittest.main()
