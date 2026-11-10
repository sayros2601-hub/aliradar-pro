"""Trusted runner for an explicitly dispatched GitHub Actions request.

No network, credentials or catalog mutation occurs on import. The runner never
publishes: queue acknowledgements must not be described as published products.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import hashlib,json,os,re
from pathlib import Path
from .search import AliClient,ApiError,search_products,generate_affiliate
from .policy import evaluate_candidate
from .store import Store,StoreError

CATEGORIES={'Дом','Техника','Кухня','Инструменты','В дороге','Уход','Спорт','На природе','Питомцы'}
REQUEST=re.compile(r'^[0-9a-f]{32}$')

def handle_request(operation,payload,identifier,call,store,load_search,*,now=None):
    if not REQUEST.fullmatch(identifier) or not isinstance(payload,dict):raise ValueError('request_invalid')
    instant=now or datetime.now(timezone.utc)
    if operation=='ledger_status':
        batch=payload.get('batch_request_id')
        if set(payload)!={'batch_request_id'} or not isinstance(batch,str) or not REQUEST.fullmatch(batch):raise ValueError('batch_invalid')
        return {'batch_request_id':batch,'observed_at':instant.isoformat(),
                'items':store.status_batch(batch),
                'published':False,'note':'Inspect individual item states; no aggregate publication claim.'}
    if operation=='search':
        if set(payload)-{'query','markets','limit'}:raise ValueError('payload_invalid')
        return search_products(call,payload.get('query'),payload.get('markets'),payload.get('limit',20),instant.isoformat())
    if operation!='queue' or set(payload)!={'search_id','selections'}:raise ValueError('operation_invalid')
    ref=payload['search_id'];selections=payload['selections']
    if not isinstance(ref,str) or not REQUEST.fullmatch(ref) or not isinstance(selections,list) or not 1<=len(selections)<=3:
        raise ValueError('selection_invalid')
    artifact=load_search(ref)
    if artifact.get('request_id')!=ref or artifact.get('operation')!='search' or artifact.get('status')!='complete':
        raise ValueError('search_not_complete')
    result=artifact.get('result',{})
    try:age=instant-datetime.fromisoformat(result['observed_at'].replace('Z','+00:00'))
    except (KeyError,TypeError,ValueError):raise ValueError('search_evidence_invalid') from None
    if age<timedelta(0) or age>timedelta(hours=1):raise ValueError('search_expired_repeat_search')
    candidates={c['product_id']:c for c in result.get('candidates',[])}
    queued=[];rejected=[]
    digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for selection in selections:
        pid=selection.get('product_id') if isinstance(selection,dict) else None
        candidate=candidates.get(pid)
        if candidate is None:
            rejected.append({'product_id':pid,'reasons':['NOT_IN_TRUSTED_SEARCH_RESULT']});continue
        decision=evaluate_candidate(candidate,selection)
        markets=selection.get('markets')
        if not isinstance(markets,list) or not markets or len(set(markets))!=len(markets) or any(m not in decision['confirmed_markets'] for m in markets):
            decision['reasons'].append('REQUESTED_MARKET_NOT_CONFIRMED')
        if selection.get('category') not in CATEGORIES:decision['reasons'].append('CATEGORY_INVALID')
        if decision['reasons']:
            rejected.append({'product_id':pid,'reasons':decision['reasons']});continue
        key=f'{identifier}:{digest[:12]}:{pid}'
        previous=store.status(key)
        if previous is not None:queued.append(previous);continue
        try:
            # Only source-bound, neutral server content is publishable; optional
            # AI prose is reasoning, never silently promoted to seller facts.
            from .publisher import source_content
            entry={'product_id':pid,'model_key':candidate.get('model_key'),'detail_url':candidate['detail_url'],'title':candidate['title'],
                   'image_url':candidate['image_url'],'affiliate_url':generate_affiliate(call,candidate),
                   'category':selection['category'],'content':source_content(candidate),
                   'markets':{m:candidate['markets'][m] for m in markets},
                   'evidence':{'method':candidate['source']['method'],'product_id':pid,'request_id':ref,
                               'observed_at':result['observed_at'],'response_sha256':hashlib.sha256(json.dumps(candidate,sort_keys=True,ensure_ascii=False).encode()).hexdigest()},
                   'selection':{'decision':decision,'input_sha256':digest}}
            queued.append(store.enqueue(key,entry,now=instant))
        except StoreError as error:rejected.append({'product_id':pid,'reasons':[error.code]})
        except ApiError:rejected.append({'product_id':pid,'reasons':['AFFILIATE_LINK_NOT_CONFIRMED']})
    return {'queued':queued,'rejected':rejected,'published':False,'publication':'scheduled_daily_maximum_3',
            'historical_deduplication':'initial_identity_reconciliation_required'}

def main():
    identifier=os.environ.get('INPUT_REQUEST_ID','');operation=os.environ.get('INPUT_OPERATION','')
    raw=os.environ.get('INPUT_PAYLOAD_JSON','');digest=os.environ.get('INPUT_PAYLOAD_SHA256','')
    envelope={'request_id':identifier,'operation':operation,'payload_sha256':digest,'status':'failed'}
    output=Path(os.environ.get('FLUXIXO_AI_RESULT_PATH','work/fluxixo-ai-result/result.json'))
    try:
        if not REQUEST.fullmatch(identifier) or not re.fullmatch(r'[0-9a-f]{64}',digest) or len(raw.encode())>28000 or hashlib.sha256(raw.encode()).hexdigest()!=digest:
            raise ValueError('request_binding_invalid')
        payload=json.loads(raw)
        from fluxixo_mcp.github_backend import GitHubActionsBackend
        client=None
        def call(method,params):
            nonlocal client
            if client is None:client=AliClient()
            return client(method,params)
        envelope['result']=handle_request(operation,payload,identifier,call,Store('data/fluxixo_ai.sqlite3'),GitHubActionsBackend().read_result)
        envelope['status']='complete'
    except (ValueError,StoreError) as error:
        code=getattr(error,'code',str(error))
        envelope['error']=code if re.fullmatch(r'[A-Za-z0-9_]{1,80}',code) else 'request_failed'
    except Exception:
        envelope['error']='request_failed'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(envelope,ensure_ascii=False,indent=2),encoding='utf-8')
    # Errors are represented in the authenticated artifact; never print payload,
    # signed API parameters, environment variables or external exception text.
    print('Broker result written: '+envelope['status'])

if __name__=='__main__':main()
