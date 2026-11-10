"""Policy tests use only invented AliExpress-shaped fixtures; no network or secrets."""
import copy
import unittest

from fluxixo_ai.policy import (MARKETS, normalize_product, merge_observations,
                               evaluate_candidate, deduplicate_candidates)


NOW = '2026-11-10T16:20:00Z'


def raw(pid='1005001234567890', title='Rechargeable clip-on reading light for books', **extra):
    return {'product_id': pid, 'product_title': title,
            'product_detail_url': f'https://www.aliexpress.com/item/{pid}.html?source=search',
            'product_main_image_url': 'https://ae01.alicdn.com/kf/example.jpg',
            'promotion_link': 'https://s.click.aliexpress.com/e/_abc', **extra}


def product(pid='1005001234567890', market='US', method='aliexpress.affiliate.productdetail.get', **extra):
    return normalize_product(raw(pid, **extra), market, method, NOW)


def selection():
    return {'problem': 'Reading in low light without disturbing others', 'use': 'Clip the light to a book',
            'rationale': 'The listing describes a clip-on reading light.',
            'evidence': [{'field': 'title', 'quote': 'clip-on reading light'}]}


class AliPolicyTests(unittest.TestCase):
    def test_query_destination_is_not_availability_or_shipping_evidence(self):
        p = product(market='BR', method='aliexpress.affiliate.product.query')
        self.assertEqual(set(p['markets']), set(MARKETS))
        for market in MARKETS:
            self.assertEqual(p['markets'][market]['sellable'], 'unknown')
            self.assertEqual(p['markets'][market]['shipping'], 'unknown')
            self.assertEqual(p['markets'][market]['ads'], 'unknown')
            self.assertEqual(p['markets'][market]['rarity'], 'unknown')
        self.assertEqual(p['source']['queried_market'], 'BR')

    def test_raw_seller_metrics_are_retained_without_scope_period_or_rarity_inference(self):
        p=product(lastest_volume='300',evaluate_rate='92.1%')
        self.assertEqual(p['seller_metrics']['lastest_volume']['raw_value'],'300')
        self.assertEqual(p['seller_metrics']['evaluate_rate']['raw_value'],'92.1%')
        for metric in p['seller_metrics'].values():
            self.assertEqual(metric['scope'],'unknown');self.assertEqual(metric['period'],'unknown')
            self.assertFalse(metric['interpreted'])
        self.assertEqual(p['markets']['US']['rarity'],'unknown')
        self.assertEqual(product()['seller_metrics']['lastest_volume']['raw_value'],None)
        self.assertEqual(product(lastest_volume=0)['seller_metrics']['lastest_volume']['raw_value'],0)
        for value in (True,{},float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                product(lastest_volume=value)

    def test_market_specific_metric_observations_are_not_collapsed(self):
        combined=merge_observations([product(market='US',lastest_volume='300'),
                                     product(market='BR',lastest_volume='50')])
        observed=combined['seller_metric_observations']
        self.assertEqual([(item['market'],item['metrics']['lastest_volume']['raw_value'])
                          for item in observed],[('US','300'),('BR','50')])
        self.assertTrue(all(item['metrics']['lastest_volume']['period']=='unknown' for item in observed))

    def test_exact_detail_response_confirms_only_the_queried_country(self):
        p = product(market='MX')
        self.assertEqual(p['markets']['MX']['sellable'], 'confirmed')
        self.assertEqual(p['markets']['MX']['shipping'], 'unknown')
        self.assertEqual(p['markets']['MX']['ads'], 'unknown')
        self.assertEqual(p['markets']['MX']['rarity'], 'unknown')
        self.assertTrue(all(p['markets'][m]['sellable'] == 'unknown' for m in MARKETS if m != 'MX'))

    def test_no_method_or_country_can_be_invented(self):
        with self.assertRaises(ValueError): product(market='XX')
        with self.assertRaises(ValueError): product(method='untrusted-method')
        with self.assertRaises(ValueError): normalize_product(raw(),'US','aliexpress.affiliate.productdetail.get','today')

    def test_product_id_and_canonical_detail_path_match_exactly(self):
        base = raw()
        for invalid in ('not-an-id', True, '-5', '0', '12e3', ''):
            with self.subTest(id=invalid), self.assertRaises(ValueError):
                normalize_product({**base,'product_id':invalid},'US','aliexpress.affiliate.product.query',NOW)
        for url in ('https://evil.aliexpress.com/item/1005001234567890.html',
                    'https://www.aliexpress.com/item/10050012345678901.html',
                    'https://www.aliexpress.com/search?q=1005001234567890',
                    'https://www.aliexpress.com@evil.test/item/1005001234567890.html',
                    'http://www.aliexpress.com/item/1005001234567890.html'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_product({**base,'product_detail_url':url},'US','aliexpress.affiliate.product.query',NOW)
        self.assertEqual(product()['detail_url'], 'https://www.aliexpress.com/item/1005001234567890.html')

    def test_untrusted_images_and_promotion_links_cannot_enter_output(self):
        for field, value in [('product_main_image_url','https://alicdn.com.evil.test/x.jpg'),
                             ('product_main_image_url','http://ae01.alicdn.com/x.jpg'),
                             ('promotion_link','https://s.click.aliexpress.com.evil.test/e/x'),
                             ('promotion_link','javascript:alert(1)')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                normalize_product({**raw(),field:value},'US','aliexpress.affiliate.product.query',NOW)

    def test_insecure_official_example_promotion_link_is_discarded_not_upgraded_or_exposed(self):
        # Alibaba's documented legacy query example returns an http promotion link.
        # Keep the real item so a separately generated HTTPS affiliate link can be requested.
        p=normalize_product({**raw(),'promotion_link':'http://s.click.aliexpress.com/e/_abc'},
                            'US','aliexpress.affiliate.product.query',NOW)
        self.assertIsNone(p['promotion_link'])
        self.assertEqual(p['promotion_link_status'],'discarded_insecure')
        self.assertEqual(p['product_id'],'1005001234567890')

    def test_merge_keeps_confirmed_observations_country_scoped_and_checks_identity(self):
        combined = merge_observations([product(market='US'), product(market='BR'),
                                       product(market='MX',method='aliexpress.affiliate.product.query')])
        self.assertEqual(combined['markets']['US']['sellable'], 'confirmed')
        self.assertEqual(combined['markets']['BR']['sellable'], 'confirmed')
        self.assertEqual(combined['markets']['MX']['sellable'], 'unknown')
        self.assertEqual(combined['markets']['IL']['sellable'], 'unknown')
        with self.assertRaises(ValueError): merge_observations([product(),product('1005009999999999')])

    def test_specific_selection_accepted_without_inventing_rarity_ad_or_shipping(self):
        p = product()
        result = evaluate_candidate(p, selection())
        self.assertTrue(result['eligible'], result)
        self.assertEqual(result['grounding']['quote_match'], 'confirmed')
        self.assertEqual(result['grounding']['semantic_entailment'], 'not_checked')
        self.assertIn('ads', result['unknown_facts'])
        self.assertIn('rarity', result['unknown_facts'])
        self.assertIn('shipping', result['unknown_facts'])
        self.assertNotIn('score',result)

    def test_query_only_cannot_be_claimed_to_sell_in_market(self):
        result=evaluate_candidate(product(method='aliexpress.affiliate.product.query'),selection())
        self.assertFalse(result['eligible'])
        self.assertIn('NO_CONFIRMED_MARKET',result['reasons'])

    def test_partial_or_tampered_normalized_input_never_becomes_eligible(self):
        partial={'product_id':'1005001234567890','title':raw()['product_title'],
                 'markets':{'US':{'sellable':'confirmed'}}}
        cases=[partial]
        invalid=product();invalid['detail_url']='https://www.aliexpress.com/item/999.html';cases.append(invalid)
        invalid=product();invalid['markets']['US']['sellability_evidence']['product_id']='999';cases.append(invalid)
        invalid=product();invalid['markets']['US']['shipping']='confirmed';cases.append(invalid)
        for case in cases:
            with self.subTest(case=case):
                result=evaluate_candidate(case,selection())
                self.assertFalse(result['eligible'])
                self.assertIn('INVALID_SOURCE_EVIDENCE',result['reasons'])

    def test_rejects_generic_tasks_and_unfounded_or_missing_quotes(self):
        for s in [dict(selection(),problem='everyday use'), dict(selection(),use='дом'),
                  dict(selection(),rationale=''), dict(selection(),evidence=[]),
                  dict(selection(),evidence=[{'field':'title','quote':'medical cure'}]),
                  dict(selection(),evidence=[{'field':'unsupported','quote':'clip-on'}])]:
            with self.subTest(s=s):
                self.assertFalse(evaluate_candidate(product(),s)['eligible'])

    def test_known_historical_id_is_rejected_and_unknown_old_ids_are_not_claimed_checked(self):
        p=product();result=evaluate_candidate(p,selection(),history_ids={p['product_id']})
        self.assertFalse(result['eligible']);self.assertIn('DUPLICATE_ITEM',result['reasons'])
        unknown=evaluate_candidate(p,selection(),history_ids=set())
        self.assertEqual(unknown['historical_identity_coverage'],'unknown')

    def test_pool_dedup_uses_exact_ids_and_only_explicit_brand_model_pairs(self):
        a=product(brand='Acme',model='R3')
        b=product('1005001234567891',brand='ACME',model='r3')
        c=product('1005001234567892',model='r3')
        d=product('1005001234567893',model='r3')
        result=deduplicate_candidates([a,copy.deepcopy(a),b,c,d])
        self.assertEqual([x['product_id'] for x in result['unique']], [a['product_id'],c['product_id'],d['product_id']])
        self.assertEqual([x['reason'] for x in result['duplicates']],['same_product_id','same_explicit_brand_model'])
        self.assertTrue(result['duplicates'][1]['inferred_equivalence'])

    def test_duplicate_model_from_history_is_a_comparison_not_a_verified_variant(self):
        p=product(brand='Acme',model='R3')
        result=evaluate_candidate(p,selection(),history_models={'acme\x1fr3'})
        self.assertFalse(result['eligible']);self.assertIn('DUPLICATE_MODEL',result['reasons'])
        self.assertEqual(result['model_equivalence'],'inferred_from_explicit_brand_model')


if __name__ == '__main__':
    unittest.main()
