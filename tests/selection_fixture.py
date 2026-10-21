from datetime import datetime, timezone, timedelta


def evidence(candidate):
    now=datetime.now(timezone.utc); date=now.isoformat(); item=candidate['item_id']
    candidate['selection']={'country':'IL','need_id':'test-need','use_case':'A documented everyday problem','why_this':'Fits the documented dimensions and budget','tradeoff':'Requires a compatible device and connector','match_reviewed':True,'negative_review_check':'Checked repeated failures and compatibility complaints','safety_reviewed':True,'demand_snapshot_id':'fixture','alternatives':[{'item_id':str(1005000000001+i),'source_url':f'https://www.aliexpress.com/item/{1005000000001+i}.html','comparison':'Synthetic test comparison: candidate fits a different connector.'} for i in range(2)]}
    candidate['offer']={'item_id':item,'variant_id':'fixture-blue-usb','ship_to':'IL','currency':'USD','item_price':15,'shipping_cost':0,'minimum_order':0,'first_order_only':False,'membership_required':False,'conditional_bundle':False,'free_shipping':True,'checked_at':date,'source_url':f'https://www.aliexpress.com/item/{item}.html','in_stock':True,'seller_positive_pct':96,'rating':4.7,'review_count':100,'shipping_days_max':14,'reviewed':True,'evidence_text':'Synthetic fixture: exact variant, destination and shipping terms observed.'}
    candidate['ad_review']={'country':'IL','checked_at':date,'source_url':'https://adstransparency.google.com/','saturation':'low','reviewed':True,'query':'fixture product','notes':'Synthetic fixture only; no actual advertising claim.'}
    candidate['editorial']={k:{lang:'Synthetic test editorial text' for lang in ('en','ru','he','es')} for k in ('use_i18n','check_i18n')}
    snapshot={'id':'fixture','country':'IL','source':'google_trends','search_type':'shopping','observed_at':date,'source_url':'https://trends.google.com/trends/explore','terms':[{'term':'fixture','need_id':'test-need'}],'weeks':[{'week':(now-timedelta(days=7*(i+2))).date().isoformat(),'values':[10]} for i in range(30)]}
    return candidate,[snapshot]
