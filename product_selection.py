"""Country-specific evidence gates. No commission signal, invented data or network scraping."""
import math
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from dealvault_core import DATA_DIR, read_json, write_json, utc_now

POLICY_FILE=DATA_DIR/'selection_policy.json'
SNAPSHOTS_FILE=DATA_DIR/'demand_snapshots.json'


def fresh(value, hours, now):
    try:
        date=datetime.fromisoformat(value.replace('Z','+00:00'))
        return date.tzinfo is not None and timedelta(0)<=now-date<=timedelta(hours=hours)
    except (ValueError,TypeError,AttributeError):return False


def number(value, low=0, high=float('inf')):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high


def official_url(value, hosts):
    try:
        u=urlparse(value)
        return u.scheme=='https' and u.hostname in hosts and not u.username and not u.password
    except (TypeError,ValueError):return False


def demand_signal(snapshot, need_id, now=None, policy=None):
    now=now or datetime.now(timezone.utc); policy=policy or read_json(POLICY_FILE)
    if not fresh(snapshot.get('observed_at'),policy['demand_max_age_days']*24,now):return None
    if snapshot.get('source')!='google_trends' or not official_url(snapshot.get('source_url'),{'trends.google.com'}):return None
    terms=snapshot.get('terms',[])
    indexes=[i for i,t in enumerate(terms) if t.get('need_id')==need_id]
    if len(indexes)!=1:return None
    index=indexes[0]; values=[]; seen_weeks=set()
    for row in snapshot.get('weeks',[]):
        try:
            date=datetime.fromisoformat(row['week']).replace(tzinfo=timezone.utc)
            value=row['values'][index]
            if date+timedelta(days=7)>now or date<now-timedelta(days=400) or date in seen_weeks or not number(value,0,100):continue
            seen_weeks.add(date);values.append(value)
        except (ValueError,KeyError,IndexError,TypeError):continue
    if len(values)<policy['minimum_observed_weeks']:return None
    coverage=sum(v>0 for v in values)/len(values)
    if coverage<policy['minimum_positive_share']:return None
    return {'term':terms[index]['term'],'coverage':round(coverage,3),'mean':round(sum(values)/len(values),2),'weeks':len(values),'search_type':snapshot['search_type']}


def evaluate_candidate(candidate, snapshots=None, policy=None, now=None):
    """Return reasons rather than treating missing facts as positive evidence."""
    now=now or datetime.now(timezone.utc); policy=policy or read_json(POLICY_FILE)
    snapshots=snapshots if snapshots is not None else read_json(SNAPSHOTS_FILE,{'snapshots':[]})['snapshots']
    reasons=[]; selection=candidate.get('selection') or {}; offer=candidate.get('offer') or {}; ads=candidate.get('ad_review') or {}
    country=selection.get('country'); need=selection.get('need_id'); item=str(candidate.get('item_id',''))
    if candidate.get('source')!='portals' or candidate.get('reviewed') is not True or not item or not candidate.get('source_evidence'):reasons.append('IDENTITY_REVIEW_REQUIRED')
    if country not in policy['countries']:reasons.append('DESTINATION_REQUIRED')
    if not need or selection.get('match_reviewed') is not True or not all(isinstance(selection.get(k),str) and len(selection[k].strip())>=12 for k in ('use_case','why_this','tradeoff')):reasons.append('USE_CASE_AND_TRADEOFF_REQUIRED')
    alternatives=selection.get('alternatives') or []
    valid_alternatives={str(a.get('item_id')) for a in alternatives if isinstance(a,dict) and str(a.get('item_id','')).isdigit() and str(a.get('item_id'))!=item and len(a.get('comparison','').strip())>=20 and official_url(a.get('source_url'),{'www.aliexpress.com','aliexpress.com'}) and str(a.get('item_id')) in a.get('source_url','')}
    if len(valid_alternatives)<2:reasons.append('COMPARE_TWO_ALTERNATIVES')
    source=offer.get('source_url','')
    if str(offer.get('item_id',''))!=item or not item or not isinstance(source,str) or item not in source or not official_url(source,{'www.aliexpress.com','aliexpress.com'}) or not offer.get('variant_id') or offer.get('ship_to')!=country or offer.get('reviewed') is not True or len(offer.get('evidence_text','').strip())<30:reasons.append('EXACT_VARIANT_AND_DESTINATION_REQUIRED')
    if not fresh(offer.get('checked_at'),policy['offer_max_age_hours'],now):reasons.append('OFFER_STALE_OR_MISSING')
    # Shipping cost and promotional shipping conditions are buyer choices, not admission gates.
    if offer.get('in_stock') is not True or not number(offer.get('item_price'),0.01) or offer.get('currency') not in {'USD','ILS','EUR','RUB'}:reasons.append('CURRENT_PRICE_AND_STOCK_REQUIRED')
    if not number(offer.get('shipping_days_max'),1,policy['maximum_delivery_days']):reasons.append('DELIVERY_ESTIMATE_REQUIRED')
    if not number(offer.get('rating'),policy['minimum_rating'],5) or not number(offer.get('review_count'),policy['minimum_reviews']) or not number(offer.get('seller_positive_pct'),policy['minimum_seller_positive_pct'],100):reasons.append('QUALITY_EVIDENCE_INSUFFICIENT')
    if not selection.get('negative_review_check') or selection.get('safety_reviewed') is not True:reasons.append('LIMITATIONS_AND_SAFETY_REVIEW_REQUIRED')
    snap=next((s for s in snapshots if s.get('id')==selection.get('demand_snapshot_id') and s.get('country')==country),{})
    signal=demand_signal(snap,need,now,policy)
    if not signal:reasons.append('RECENT_COUNTRY_DEMAND_REQUIRED')
    if ads.get('country')!=country or ads.get('reviewed') is not True or not fresh(ads.get('checked_at'),policy['ad_review_max_age_days']*24,now) or not official_url(ads.get('source_url'),{'adstransparency.google.com','www.facebook.com'}) or len(ads.get('query','').strip())<3 or len(ads.get('notes','').strip())<20:reasons.append('COUNTRY_AD_REVIEW_REQUIRED')
    if ads.get('saturation') not in {'low','moderate'}:reasons.append('AD_SATURATION_HIGH_OR_UNKNOWN')
    editorial=candidate.get('editorial') or {}
    for key in ('use_i18n','check_i18n'):
        if not all(isinstance(editorial.get(key,{}).get(lang),str) and 8<=len(editorial[key][lang].strip())<=(100 if key=='use_i18n' else 220) for lang in ('en','ru','he','es')):reasons.append('CONCISE_LOCALIZED_EDITORIAL_REQUIRED');break
    # Comparable bounded factors only. Trends magnitude is NOT compared across countries/cohorts.
    score=0
    if not reasons:
        score=round(40*signal['coverage'] + 20*(offer['rating']/5) + 15*min(offer['review_count']/200,1) + 15*offer['seller_positive_pct']/100 + 10*(1-offer['shipping_days_max']/policy['maximum_delivery_days']),2)
    return {'id':candidate.get('id'),'country':country,'need_id':need,'eligible':not reasons,'score':score,'reasons':list(dict.fromkeys(reasons)),'demand':signal}


def rank_candidates(candidates, snapshots=None, policy=None, now=None):
    policy=policy or read_json(POLICY_FILE)
    ranked=[(evaluate_candidate(p,snapshots,policy,now),p) for p in candidates]
    ranked.sort(key=lambda pair:(-pair[0]['score'],str(pair[1].get('id',''))))
    return ranked



def research_plan(now=None):
    now=now or datetime.now(timezone.utc)
    terms={'usb-c-charging':('tech','usb c charger pd'), 'dash-camera':('auto','dash cam'), 'pet-water':('pets','cat water fountain'), 'smart-plug':('smarthome','smart plug')}
    plans=[]; seen=set()
    snapshots=read_json(SNAPSHOTS_FILE,{'snapshots':[]})['snapshots']
    # Prefer shopping-intent searches; web search remains exploratory.
    for snap in sorted(snapshots,key=lambda s:s.get('search_type')!='shopping'):
        for term in snap.get('terms',[]):
            need=term['need_id']; key=(snap['country'],need)
            if need not in terms or key in seen:continue
            signal=demand_signal(snap,need,now)
            if not signal:continue
            seen.add(key);category,query=terms[need]
            plans.append({'country':snap['country'],'need_id':need,'category':category,'query':query,'demand_snapshot_id':snap['id'],'signal':signal,'action':'Compare at least three exact variants; verify delivery and local compatibility; inspect country ad libraries. This is a research lead, not an approved product.'})
    return plans

def write_selection_report():
    reserve=read_json(DATA_DIR/'reserve_pool.json',[])
    inbox=read_json(DATA_DIR/'portals_inbox.json',[])
    records={p['id']:p for p in inbox+reserve}
    ranked=rank_candidates(list(records.values()))
    report={'checked_at':utc_now(),'mode':'evidence_based_screening','eligible':sum(r['eligible'] for r,p in ranked),'review_queue':[r for r,p in ranked],'research_plan':research_plan(),'note':'No qualified new candidate means no rotation. Free shipping is optional and does not affect eligibility or score. Buyers confirm final delivery terms on AliExpress. Research and observations are updated through editorial review; this module does not access private ad targeting or infer sales.'}
    write_json(DATA_DIR/'selection_report.json',report)
    return report


if __name__=='__main__':
    result=write_selection_report()
    print(f"[Selection] {result['eligible']} eligible; {len(result['review_queue'])} evaluated. See data/selection_report.json.")
