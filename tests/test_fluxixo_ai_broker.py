"""Broker integration with synthetic API evidence and a real temporary ledger."""
import tempfile,unittest
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from fluxixo_ai.policy import normalize_product,DETAIL
from fluxixo_ai.store import Store

class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'state.sqlite3');self.now=datetime(2026,11,10,12,tzinfo=timezone.utc)
        self.candidate=normalize_product({'product_id':'100000000001','product_title':'Synthetic narrow inspection mirror','product_detail_url':'https://www.aliexpress.com/item/100000000001.html','product_main_image_url':'https://ae01.alicdn.com/kf/fixture.jpg'},'MX',DETAIL,self.now.isoformat())
        self.content={lang:{'name':'Synthetic fixture','headline':['Synthetic','fixture'],'description':'Invented claim must never be published.'} for lang in ('ru','en','pt','es','fr','he')}
        self.selection={'product_id':'100000000001','category':'Инструменты','markets':['MX'],'problem':'Cannot inspect a narrow gap behind the radiator','use':'Inspect the inaccessible gap using a small mirror','rationale':'The title identifies an inspection mirror for a specific access task','evidence':[{'field':'title','quote':'inspection mirror'}],'content':self.content}
        self.artifact={'request_id':'1'*32,'operation':'search','status':'complete','result':{'observed_at':self.now.isoformat(),'candidates':[self.candidate]}}
        self.calls=[]
    def api(self,method,params):
        self.calls.append(method)
        return {'aliexpress_affiliate_link_generate_response':{'resp_result':{'resp_code':200,'result':{'promotion_links':{'promotion_link':[{'source_value':self.candidate['detail_url'],'promotion_link':'https://s.click.aliexpress.com/e/_synthetic'}]}}}}}
    def run_queue(self,payload=None,artifact=None):
        from fluxixo_ai.broker import handle_request
        return handle_request('queue',payload or {'search_id':'1'*32,'selections':[self.selection]},'2'*32,self.api,self.store,lambda _:artifact or self.artifact,now=self.now)
    def test_queue_replays_without_new_links_or_publication(self):
        first=self.run_queue();second=self.run_queue()
        self.assertEqual(first,second);self.assertEqual(len(self.calls),1)
        self.assertFalse(first['published']);self.assertEqual(first['queued'][0]['state'],'queued')
    def test_client_cannot_forge_candidate_or_unknown_country(self):
        forged={**self.selection,'product_id':'100000000002'}
        result=self.run_queue({'search_id':'1'*32,'selections':[forged]})
        self.assertFalse(result['queued']);self.assertFalse(self.calls)
        wrong={**self.selection,'markets':['US']}
        result=self.run_queue({'search_id':'1'*32,'selections':[wrong]})
        self.assertFalse(result['queued']);self.assertFalse(self.calls)
    def test_client_description_is_not_copied_as_source_facts(self):
        bad={**self.selection,'content':{'ru':self.content['ru']}}
        result=self.run_queue({'search_id':'1'*32,'selections':[bad]})
        self.assertTrue(result['queued']);self.assertFalse(result['rejected']); claims=self.store.claim('2026-11-10','test',now=self.now); self.assertNotIn('Invented claim',str(claims[0]['candidate']['content']))
    def test_untrusted_pending_artifact_is_rejected(self):
        with self.assertRaises(ValueError):self.run_queue(artifact={'request_id':'1'*32,'status':'pending'})
    def test_stale_search_is_not_treated_as_fresh(self):
        artifact={**self.artifact,'result':{**self.artifact['result'],'observed_at':'2026-01-01T00:00:00Z'}}
        with self.assertRaises(ValueError):self.run_queue(artifact=artifact)
    def test_current_batch_status_survives_more_than_500_historical_items(self):
        result=self.run_queue()
        with sqlite3.connect(self.store.path) as db:
            for n in range(501):
                db.execute("INSERT INTO intake(request_id,product_id,candidate_json,fingerprint,state,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",(f'old-{n}',str(n+1),'{}','fixture','published',0,0))
        db.close()
        from fluxixo_ai.broker import handle_request
        status=handle_request('ledger_status',{'batch_request_id':'2'*32},'3'*32,None,self.store,None,now=self.now)
        self.assertEqual(status['items'],result['queued'])

if __name__=='__main__':unittest.main()
