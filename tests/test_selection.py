import copy
from datetime import datetime,timezone,timedelta
import unittest
from product_selection import evaluate_candidate,rank_candidates
from selection_fixture import evidence

class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.p,self.snap=evidence({'id':'fixture','item_id':'1005001234567','source':'portals','reviewed':True,'source_evidence':'Synthetic source identity evidence'})
    def evaluate(self):return evaluate_candidate(self.p,self.snap)
    def test_complete_evidence_passes(self):self.assertTrue(self.evaluate()['eligible'])
    def test_missing_or_conditional_shipping_fails(self):
        for field,value in [('shipping_cost',None),('shipping_cost',False),('shipping_cost',2),('minimum_order',10),('first_order_only',True),('membership_required',True),('conditional_bundle',True)]:
            with self.subTest(field=field,value=value):
                candidate=copy.deepcopy(self.p);candidate['offer'][field]=value
                self.assertIn('UNCONDITIONAL_FREE_SHIPPING_REQUIRED',evaluate_candidate(candidate,self.snap)['reasons'])
    def test_wrong_destination_or_variant_fails(self):
        self.p['offer']['ship_to']='US';self.assertFalse(self.evaluate()['eligible'])
        self.p['offer']['ship_to']='IL';self.p['offer']['variant_id']='';self.assertFalse(self.evaluate()['eligible'])
    def test_stale_or_future_offer_fails(self):
        for days in (-2,1):
            self.p['offer']['checked_at']=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()
            self.assertIn('OFFER_STALE_OR_MISSING',self.evaluate()['reasons'])
    def test_other_country_demand_is_not_reused(self):
        self.snap[0]['country']='US';self.assertIn('RECENT_COUNTRY_DEMAND_REQUIRED',self.evaluate()['reasons'])
    def test_sparse_demand_is_unknown(self):
        for week in self.snap[0]['weeks']:week['values']=[0]
        self.assertFalse(self.evaluate()['eligible'])
    def test_repeated_week_cannot_fake_history(self):
        self.snap[0]['weeks']=[self.snap[0]['weeks'][0]]*30
        self.assertFalse(self.evaluate()['eligible'])
    def test_stale_research_fails(self):
        self.snap[0]['observed_at']=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat()
        self.assertFalse(self.evaluate()['eligible'])
    def test_unknown_and_high_ad_saturation_fail(self):
        for value in ('unknown','high'):
            self.p['ad_review']['saturation']=value;self.assertFalse(self.evaluate()['eligible'])
    def test_missing_comparison_fails(self):
        self.p['selection']['alternatives']=[];self.assertIn('COMPARE_TWO_ALTERNATIVES',self.evaluate()['reasons'])
    def test_duplicate_alternative_cannot_count_twice(self):
        self.p['selection']['alternatives']=[self.p['selection']['alternatives'][0]]*2;self.assertFalse(self.evaluate()['eligible'])
    def test_missing_translation_fails(self):
        del self.p['editorial']['use_i18n']['he'];self.assertFalse(self.evaluate()['eligible'])
    def test_commission_and_ad_rank_do_not_change_score(self):
        score=self.evaluate()['score'];self.p['commission']=99;self.p['advertising_rank']=1
        self.assertEqual(score,self.evaluate()['score'])
    def test_unknown_rating_and_nan_fail(self):
        for value in (None,float('nan'),True,6):
            self.p['offer']['rating']=value;self.assertFalse(self.evaluate()['eligible'])
    def test_unreviewed_capture_cannot_auto_publish(self):
        self.p['reviewed']=False;self.assertFalse(self.evaluate()['eligible'])
    def test_rank_is_stable(self):
        q=copy.deepcopy(self.p);q['id']='aaa';ranked=rank_candidates([self.p,q],snapshots=self.snap)
        self.assertEqual(ranked[0][1]['id'],'aaa')

if __name__=='__main__':unittest.main()
