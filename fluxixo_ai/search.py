"""Bounded official-API adapter. No API calls take place at import time."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from .policy import MARKETS, QUERY, DETAIL, normalize_product, merge_observations, image_field_shapes

LINK = 'aliexpress.affiliate.link.generate'
HOT = 'aliexpress.affiliate.hotproduct.query'
API_URL = 'https://api-sg.aliexpress.com/sync'
LIMITS = ('A country-filtered detail result is not SKU stock or address-level shipping.',
          'Recent sales have an unspecified period and geographic scope.',
          'Popular API results are a comparison background, not advertising saturation.',
          'No API observation proves global uniqueness or absence from social advertising.')

def _source_diagnostic(row,error):
    """Public URL shape only, never signed request data or response bodies."""
    if not isinstance(row,dict):return {'validation':'invalid_source','url_shape':{}}
    shape={}
    for field in ('product_detail_url','product_main_image_url','promotion_link'):
        try:
            value=urlsplit(str(row.get(field,'')))
            shape[field]={'scheme':value.scheme[:12],'host':(value.hostname or '')[:253]}
        except ValueError:shape[field]={'status':'malformed'}
    message=str(error)
    return {'validation':message if re.fullmatch(r'[A-Za-z_ .]{1,80}',message) else 'invalid_source', 'url_shape':shape}

class ApiError(RuntimeError):
    pass

class AliClient:
    """Instantiate only inside the existing authorized GitHub secret runtime."""
    def __init__(self):
        self.key=os.environ.get('ALI_APP_KEY','').strip()
        self.secret=os.environ.get('ALI_APP_SECRET','').strip()
        if not self.key or not self.secret:
            raise ApiError('aliexpress_credentials_missing')

    def __call__(self, method, params):
        if method not in (QUERY, DETAIL, LINK, HOT):
            raise ApiError('method_not_allowed')
        values={**params,'app_key':self.key,'method':method,'sign_method':'sha256',
                'timestamp':str(int(datetime.now(timezone.utc).timestamp()*1000))}
        signing=''.join(f'{k}{v}' for k,v in sorted(values.items()))
        values['sign']=hmac.new(self.secret.encode(),signing.encode(),hashlib.sha256).hexdigest().upper()
        try:
            with urlopen(Request(API_URL,data=urlencode(values).encode(),method='POST'),timeout=30) as response:
                raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError()
            result=json.loads(raw)
            if not isinstance(result,dict):raise ValueError()
            return result
        except Exception:
            # Do not return response bodies, signed requests or exception text.
            raise ApiError('aliexpress_request_failed') from None

def _rows(response,method):
    if not isinstance(response,dict) or 'error_response' in response:
        raise ApiError('api_method_unavailable')
    key=method.replace('.','_')+'_response'
    envelope=response.get(key)
    result=envelope.get('resp_result') if isinstance(envelope,dict) else None
    if not isinstance(result,dict) or 'resp_code' not in result:
        raise ApiError('api_shape_invalid')
    if str(result['resp_code']) not in ('200','0'):
        raise ApiError('api_result_unsuccessful')
    payload=result.get('result')
    if not isinstance(payload,dict):raise ApiError('api_shape_invalid')
    products=payload.get('products')
    if products is None and str(payload.get('current_record_count'))=='0':return []
    if not isinstance(products,dict):raise ApiError('api_shape_invalid')
    rows=products.get('product')
    if rows is None and str(payload.get('current_record_count'))=='0':return []
    if isinstance(rows,dict):rows=[rows]
    if not isinstance(rows,list):raise ApiError('api_shape_invalid')
    return rows


def _representative(candidates, markets, limit):
    """Cover observed confirmed markets first; this is not a quality or rarity score."""
    remaining=list(candidates);selected=[];covered=set();requested=set(markets)
    while remaining and len(selected)<limit:
        def key(candidate):
            confirmed={market for market in requested if candidate['markets'][market]['sellable']=='confirmed'}
            return (-len(confirmed-covered),-len(confirmed),int(candidate['product_id']))
        choice=min(remaining,key=key)
        remaining.remove(choice);selected.append(choice)
        covered.update(market for market in requested if choice['markets'][market]['sellable']=='confirmed')
    return selected

def search_products(call,query,markets,limit=20,observed_at=None):
    if not isinstance(query,str) or not 3<=len(query.strip())<=240 or any(ord(c)<32 for c in query):
        raise ValueError('query_invalid')
    if not isinstance(markets,list) or not markets or len(markets)>5 or len(set(markets))!=len(markets) or any(m not in MARKETS for m in markets):
        raise ValueError('market_not_configured')
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=50:raise ValueError('limit_invalid')
    stamp=observed_at or datetime.now(timezone.utc).isoformat()
    observations={};warnings=[];rejected=[];baseline=[]
    image_shapes={'product_main_image_url':[],'product_small_image_urls':[]}
    def record_image_shapes(row):
        for field, shapes in image_field_shapes(row).items():
            for shape in shapes:
                if shape not in image_shapes[field]:image_shapes[field].append(shape)
    for market in markets:
        for page in (1,2):
            try:
                rows=_rows(call(QUERY,{'keywords':query.strip(),'ship_to_country':market,'target_currency':'USD','target_language':'EN','page_size':'20','page_no':str(page),'tracking_id':'default'}),QUERY)
                if len(rows)>20:warnings.append({'market':market,'operation':'query','status':'response_truncated_to_page_size'})
                for row in rows[:20]:
                    record_image_shapes(row)
                    try:
                        item=normalize_product(row,market,QUERY,stamp)
                        observations.setdefault(item['product_id'],[]).append(item)
                    except ValueError as error:
                        rejected.append({'market':market,'reason':'invalid_or_mismatching_identity_or_source',**_source_diagnostic(row,error)})
            except (ApiError,ValueError):warnings.append({'market':market,'operation':'query','status':'unavailable'})
        try:
            rows=_rows(call(HOT,{'keywords':query.strip(),'ship_to_country':market,'target_currency':'USD','target_language':'EN','page_size':'20','tracking_id':'default'}),HOT)
            if len(rows)>20:warnings.append({'market':market,'operation':'hotproduct.query','status':'response_truncated_to_page_size'})
            for row in rows[:20]:
                # This list is a popular background only. It cannot confer or
                # erase sellability, quality or advertising/novelty evidence.
                if isinstance(row,dict) and re.fullmatch(r'[1-9][0-9]{0,31}',str(row.get('product_id',''))):
                    baseline.append({'product_id':str(row['product_id']),'title':str(row.get('product_title',''))[:2000],'market_query':market,'method':HOT,'observed_at':stamp,'scope':'API popularity; geography/period unspecified'})
        except (ApiError,ValueError):warnings.append({'market':market,'operation':'hotproduct.query','status':'unavailable_popularity_unknown'})
    # Discover across all requested markets before comparing every gathered ID
    # against each country's detail endpoint. A later market cannot leave an
    # earlier market unchecked for a newly discovered item.
    ids=list(observations)
    for market in markets:
        for start in range(0,len(ids),20):
            requested=set(ids[start:start+20])
            try:
                rows=_rows(call(DETAIL,{'product_ids':','.join(sorted(requested)),'country':market,'target_currency':'USD','target_language':'EN','tracking_id':'default'}),DETAIL)
                if len(rows)>20:warnings.append({'market':market,'operation':'productdetail.get','status':'response_truncated_to_page_size'})
                for row in rows[:20]:
                    record_image_shapes(row)
                    if not isinstance(row,dict):
                        rejected.append({'market':market,'reason':'invalid_detail_identity'});continue
                    if str(row.get('product_id')) not in requested:continue
                    try:
                        item=normalize_product(row,market,DETAIL,stamp)
                        observations[item['product_id']].append(item)
                    except ValueError:rejected.append({'market':market,'reason':'invalid_detail_identity'})
            except (ApiError,ValueError):warnings.append({'market':market,'operation':'productdetail.get','status':'unavailable_no_sellability_confirmation'})
    candidates=[merge_observations(v) for v in observations.values()]
    summary={market:{'confirmed':sum(p['markets'][market]['sellable']=='confirmed' for p in candidates),
                     'unknown':sum(p['markets'][market]['sellable']=='unknown' for p in candidates)} for market in markets}
    return {'query':query.strip(),'markets':markets,'observed_at':stamp,'considered_count':len(candidates),
            'candidates':_representative(candidates,markets,limit),'candidate_limit':limit,'truncated':len(candidates)>limit,
            'market_summary':summary,
            'source_image_field_shapes':image_shapes,
            'rejected':rejected,'warnings':warnings,'popular_background':baseline,'limitations':list(LIMITS),
            'selection':'Limited results prioritize coverage of confirmed markets, then confirmed market count and product ID; this is not a quality, popularity, ad or rarity score. The calling AI compares the pool and records reasons.'}

def generate_affiliate(call,candidate):
    pid=candidate.get('product_id');detail=candidate.get('detail_url')
    if not isinstance(pid,str) or not re.fullmatch(r'[1-9][0-9]{0,31}',pid) or detail!=f'https://www.aliexpress.com/item/{pid}.html':
        raise ValueError('identity_mismatch')
    response=call(LINK,{'promotion_link_type':'0','source_values':detail,'tracking_id':'default'})
    if not isinstance(response,dict) or 'error_response' in response:raise ApiError('affiliate_generation_failed')
    result=response.get('aliexpress_affiliate_link_generate_response',{}).get('resp_result',{})
    if str(result.get('resp_code')) not in ('200','0'):raise ApiError('affiliate_generation_failed')
    links=result.get('result',{}).get('promotion_links',{}).get('promotion_link',[])
    if isinstance(links,dict):links=[links]
    for link in links:
        if link.get('source_value')!=detail:continue
        url=link.get('promotion_link','');parsed=urlsplit(url)
        if parsed.scheme=='https' and parsed.hostname=='s.click.aliexpress.com' and not parsed.username and not parsed.password and parsed.port in (None,443) and '\\' not in url:
            return url
    raise ApiError('affiliate_generation_failed')
