"""Offline contract checks. All records below are synthetic, never live API evidence."""
import unittest

class SearchTests(unittest.TestCase):
    def test_affiliate_requires_success_and_exact_source_binding(self):
        _,generate=self.api()
        candidate={'product_id':'100000000001','detail_url':'https://www.aliexpress.com/item/100000000001.html'}
        for code,source in ((500,candidate['detail_url']),(200,None),(200,'https://www.aliexpress.com/item/100000000002.html')):
            with self.subTest(code=code,source=source),self.assertRaises(RuntimeError):
                generate(lambda *_:{'aliexpress_affiliate_link_generate_response':{'resp_result':{'resp_code':code,'result':{'promotion_links':{'promotion_link':[{'source_value':source,'promotion_link':'https://s.click.aliexpress.com/e/_fixture'}]}}}}},candidate)
    def api(self):
        from fluxixo_ai.search import search_products, generate_affiliate
        return search_products, generate_affiliate

    def test_compares_pool_and_queries_each_country_detail_separately(self):
        search,_=self.api(); calls=[]
        def call(method,params):
            calls.append((method,params))
            rows=[{'product_id':str(n),'product_title':'Synthetic angled inspection fixture '+str(n),'product_detail_url':f'https://www.aliexpress.com/item/{n}.html','product_main_image_url':'https://ae01.alicdn.com/kf/test.jpg'} for n in (100000000001,100000000002)]
            key='aliexpress_affiliate_product_query_response' if method.endswith('query') else 'aliexpress_affiliate_productdetail_get_response'
            return {key:{'resp_result':{'resp_code':200,'result':{'products':{'product':rows}}}}}
        result=search(call,'inspection access behind narrow radiator',['US','MX'],limit=10,observed_at='2026-11-10T12:00:00Z')
        self.assertEqual(len(result['candidates']),2)
        self.assertEqual({p['country'] for m,p in calls if m.endswith('productdetail.get')},{'US','MX'})
        self.assertTrue(all(c['markets']['US']['sellable']=='confirmed' for c in result['candidates']))
        self.assertTrue(all(c['markets']['US']['ads']=='unknown' for c in result['candidates']))

    def test_detail_failure_does_not_become_shipping_confirmation(self):
        search,_=self.api()
        def call(method,params):
            if method.endswith('productdetail.get'): return {'error_response':{'code':'InvalidApi'}}
            return {'aliexpress_affiliate_product_query_response':{'resp_result':{'resp_code':200,'result':{'products':{'product':[{'product_id':'100000000001','product_title':'Synthetic fixture','product_detail_url':'https://www.aliexpress.com/item/100000000001.html','product_main_image_url':'https://ae01.alicdn.com/kf/test.jpg'}]}}}}}
        result=search(call,'narrow inaccessible inspection task',['IL'],observed_at='2026-11-10T12:00:00Z')
        self.assertEqual(result['candidates'][0]['markets']['IL']['sellable'],'unknown')
        self.assertTrue(result['warnings'])

    def test_unresolved_russian_audience_and_spain_not_silently_enabled(self):
        search,_=self.api()
        for market in ['RU','ES']:
            with self.subTest(market=market),self.assertRaises(ValueError):search(lambda *_:self.fail('must not call API'),'fixture',[market])

    def test_affiliate_link_generated_only_from_exact_detail_identity(self):
        _,generate=self.api();calls=[]
        candidate={'product_id':'100000000001','detail_url':'https://www.aliexpress.com/item/100000000001.html'}
        def call(method,p):
            calls.append(p)
            return {'aliexpress_affiliate_link_generate_response':{'resp_result':{'resp_code':200,'result':{'promotion_links':{'promotion_link':[{'source_value':candidate['detail_url'],'promotion_link':'https://s.click.aliexpress.com/e/_synthetic'}]}}}}}
        self.assertEqual(generate(call,candidate),'https://s.click.aliexpress.com/e/_synthetic')
        self.assertEqual(calls[0]['source_values'],candidate['detail_url'])
        with self.assertRaises(ValueError):generate(call,{**candidate,'detail_url':'https://www.aliexpress.com/item/999999999999.html'})

    def test_items_discovered_in_later_market_are_checked_in_all_markets(self):
        search,_=self.api();calls=[]
        def row(pid):
            return {'product_id':pid,'product_title':'Synthetic inspection fixture',
                    'product_detail_url':f'https://www.aliexpress.com/item/{pid}.html',
                    'product_main_image_url':'https://ae01.alicdn.com/kf/test.jpg'}
        def call(method,params):
            calls.append((method,dict(params)))
            if method.endswith('productdetail.get'):
                rows=[row(pid) for pid in params['product_ids'].split(',')]
            elif method=='aliexpress.affiliate.product.query':
                rows=[row('100000000001' if params['ship_to_country']=='US' else '100000000002')]
            else:
                rows=[]
            return {method.replace('.','_')+'_response':{'resp_result':{'resp_code':200,'result':{'products':{'product':rows}}}}}
        result=search(call,'reach behind an inaccessible radiator',['US','BR'],observed_at='2026-11-10T12:00:00Z')
        products={p['product_id']:p for p in result['candidates']}
        self.assertEqual(set(products),{'100000000001','100000000002'})
        self.assertTrue(all(product['markets'][m]['sellable']=='confirmed'
                            for product in products.values() for m in ('US','BR')))
        details=[params for method,params in calls if method.endswith('productdetail.get')]
        self.assertEqual({p['country'] for p in details},{'US','BR'})
        self.assertTrue(all(set(p['product_ids'].split(','))==set(products) for p in details))

    def test_malformed_or_unsuccessful_api_is_warned_but_valid_empty_is_not(self):
        search,_=self.api()
        for response in ({}, {'aliexpress_affiliate_product_query_response':{'resp_result':{}}},
                         {'aliexpress_affiliate_product_query_response':{'resp_result':{'result':{'products':{'product':[]}}}}},
                         {'aliexpress_affiliate_product_query_response':{'resp_result':{'resp_code':500,'result':{'products':{'product':[]}}}}}):
            with self.subTest(response=response):
                result=search(lambda *_:response,'inspection fixture',['US'],observed_at='2026-11-10T12:00:00Z')
                self.assertEqual(result['candidates'],[])
                self.assertTrue(any(w['operation']=='query' for w in result['warnings']))
        def valid_empty(method,_):
            return {method.replace('.','_')+'_response':{'resp_result':{'resp_code':200,'result':{'products':{'product':[]}}}}}
        result=search(valid_empty,'inspection fixture',['US'],observed_at='2026-11-10T12:00:00Z')
        self.assertEqual(result['candidates'],[])
        self.assertFalse(any(w['operation']=='query' for w in result['warnings']))

    def test_limited_results_cover_later_market_and_summary_counts_all_candidates(self):
        search,_=self.api()
        def row(pid):
            value={'product_id':pid,'product_title':'Synthetic inspect fixture '+pid,
                   'product_detail_url':f'https://www.aliexpress.com/item/{pid}.html',
                   'product_main_image_url':'https://ae01.alicdn.com/kf/test.jpg'}
            if pid=='100000000002':value['product_small_image_urls']={'string':['https://ae01.alicdn.com/kf/small.jpg']}
            return value
        ids=[str(100000000001+n) for n in range(4)]
        def call(method,params):
            if method=='aliexpress.affiliate.product.query':
                rows=[row(pid) for pid in (ids[:3] if params['ship_to_country']=='US' else ids[3:])]
            elif method.endswith('productdetail.get'):
                requested=set(params['product_ids'].split(','))
                rows=[row(pid) for pid in (ids[:3] if params['country']=='US' else ids[3:]) if pid in requested]
            else:rows=[]
            return {method.replace('.','_')+'_response':{'resp_result':{'resp_code':200,'result':{'products':{'product':rows}}}}}
        result=search(call,'synthetic fixture',['US','MX'],limit=2,observed_at='2026-11-10T12:00:00Z')
        self.assertEqual(result['considered_count'],4)
        self.assertEqual([p['product_id'] for p in result['candidates']],[ids[0],ids[3]])
        self.assertEqual(result['market_summary']['US'],{'confirmed':3,'unknown':1})
        self.assertEqual(result['market_summary']['MX'],{'confirmed':1,'unknown':3})
        self.assertIn('object.string:list',result['source_image_field_shapes']['product_small_image_urls'])
        self.assertTrue(result['truncated'])

    def test_malformed_non_object_rows_do_not_crash_the_whole_search(self):
        search,_=self.api()
        def call(method,params):
            return {method.replace('.','_')+'_response':{'resp_result':{'resp_code':200,'result':{'products':{'product':[None,'not-a-product',123]}}}}}
        result=search(call,'inspection fixture',['US'],observed_at='2026-11-10T12:00:00Z')
        self.assertEqual(result['candidates'],[])
        self.assertGreater(len(result['rejected']),0)

if __name__=='__main__':unittest.main()
