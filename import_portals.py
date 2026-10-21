"""Stage genuine captured Portals records for editorial review, never auto-invent products."""
import argparse
import hashlib
import re
from pathlib import Path
from dealvault_core import DATA_DIR, affiliate_key, read_json, write_json, utc_now
from link_health_guard import check_single_link


def stage_records(records):
    db=read_json(DATA_DIR/'products.json')
    inbox=read_json(DATA_DIR/'portals_inbox.json',[])
    existing={affiliate_key(p['affiliate_url']) for p in db['products']} | {affiliate_key(p['affiliate_url']) for p in inbox}
    added=[]
    for raw in records:
        text=raw.get('modal',{}).get('text') or raw.get('text','')
        match=re.search(r'https://s\.click\.aliexpress\.com/e/_[A-Za-z0-9_-]+',text)
        url=raw.get('affiliate_url') or (match.group(0) if match else '')
        key=affiliate_key(url)
        if not key or key in existing:continue
        lines=[line.strip() for line in text.splitlines() if line.strip()]
        title=raw.get('raw_title') or (lines[1] if len(lines)>1 else '')
        # Query terms are search intent, not the title of the actual promoted product.
        if not title:continue
        candidate={'id':'portals-'+hashlib.sha256(key.encode()).hexdigest()[:12],
                   'affiliate_url':url,'raw_title':title,'source':'portals','source_evidence':text,
                   'category':raw.get('category'),'images':raw.get('images') or raw.get('modal',{}).get('images',[]),
                   'captured_at':utc_now(),'reviewed':False,
                   'query':raw.get('query'),'target_country':raw.get('target_country'),
                   'selection':raw.get('selection',{}),'offer':raw.get('offer',{}),
                   'ad_review':raw.get('ad_review',{}),'editorial':raw.get('editorial',{})}
        check=check_single_link(candidate)
        candidate['destination_check']=check
        candidate['item_id']=check.get('item_id')
        inbox.append(candidate); added.append(candidate); existing.add(key)
    if added:write_json(DATA_DIR/'portals_inbox.json',inbox)
    print(f'[Portals] Staged {len(added)} real records for review. Live catalog unchanged.')
    return added


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    stage_records(read_json(parser.parse_args().capture))
