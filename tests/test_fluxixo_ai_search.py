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

if __name__=='__main__':unittest.main()
