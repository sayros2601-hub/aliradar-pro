"""Rotate only real, reviewed Portals candidates. Empty reserve is a safe no-op."""
import argparse
from datetime import datetime, timezone
from dealvault_core import DATA_DIR, read_json, write_json, affiliate_key, validate_catalog, utc_now
from link_health_guard import check_single_link
from product_selection import rank_candidates


PRODUCTS_FILE=DATA_DIR/'products.json'
RESERVE_FILE=DATA_DIR/'reserve_pool.json'
LOG_FILE=DATA_DIR/'rotation_log.json'
JOURNAL=DATA_DIR/'rotation_pending.json'


def recover_transaction():
    if JOURNAL.exists():
        pending=read_json(JOURNAL)
        write_json(PRODUCTS_FILE,pending['catalog'])
        write_json(RESERVE_FILE,pending['reserve'])
        write_json(LOG_FILE,pending['log'])
        JOURNAL.unlink()


def rotate_deals(count=7,dry_run=False,checker=check_single_link):
    if not 1 <= count <= 35:
        raise ValueError('Rotation count must be between 1 and 35')
    if dry_run and JOURNAL.exists():
        raise RuntimeError('A previous rotation needs recovery; dry-run made no changes')
    if not dry_run:
        recover_transaction()
    db=read_json(PRODUCTS_FILE)
    reserve=read_json(RESERVE_FILE,[])
    history=read_json(LOG_FILE,[])
    day=datetime.now(timezone.utc).date().isoformat()
    if any(entry.get('date') == day for entry in history):
        print('[Rotation] Already processed this UTC date; unchanged.')
        return []
    ids={p['id'] for p in db['products']}
    slugs={p['slug'] for p in db['products']}
    links={affiliate_key(p['affiliate_url']) for p in db['products']}
    item_ids={str(p['item_id']) for p in db['products'] if p.get('item_id')}
    incoming=[]
    category_counts={}; needs={}
    policy=read_json(DATA_DIR/'selection_policy.json')
    for decision,candidate in rank_candidates(reserve):
        if not decision['eligible']:
            continue
        need = decision.get('need_id') or candidate.get('category')
        category = candidate.get('category')
        max_need = policy.get('max_per_need', 1)
        max_cat = policy.get('max_per_category', 2)
        if (need and needs.get(need, 0) >= max_need) or (category and category_counts.get(category, 0) >= max_cat):
            continue
        if len(incoming) >= count:
            break
        # A working shortlink alone cannot establish title, image or product identity.
        if candidate.get('source') != 'portals' or candidate.get('reviewed') is not True or not candidate.get('item_id') or not candidate.get('source_evidence'):
            continue
        if str(candidate.get('item_id')) in item_ids:
            continue
        if candidate.get('id') in ids or candidate.get('slug') in slugs or affiliate_key(candidate.get('affiliate_url')) in links:
            continue
        try:
            validate_catalog({**db,'products':[candidate]})
        except ValueError:
            continue
        if checker(candidate)['status'] != 'RESOLVED':
            continue
        item={**candidate,'added_at':utc_now(),'is_new':True}
        incoming.append(item)
        needs[need]=needs.get(need,0)+1; category_counts[category]=category_counts.get(category,0)+1
        item_ids.add(str(item['item_id']))
        ids.add(item['id']); slugs.add(item['slug']); links.add(affiliate_key(item['affiliate_url']))
    if not incoming:
        print('[Rotation] No candidates passed current demand, delivery, quality and editorial checks. Catalog unchanged.')
        return []
    # Rotation replaces admitted items; resizing is a separate editorial operation.
    limit=len(db['products'])
    existing=[{**p,'is_new':False} for p in db['products']]
    combined=incoming+existing
    retired=combined[limit:]
    db['products']=combined[:limit]
    new_ids={p['id'] for p in incoming}
    next_reserve=[p for p in reserve if p.get('id') not in new_ids]+retired
    validate_catalog(db)
    if dry_run:
        print(f'[Rotation] Dry-run: {len(incoming)} candidates; no files written.')
        return incoming
    entry={'date':day,'timestamp':utc_now(),'rotated_in':[p['id'] for p in incoming],
           'rotated_out':[p['id'] for p in retired],'total_active':len(db['products'])}
    pending={'catalog':db,'reserve':next_reserve,'log':(history+[entry])[-90:]}
    write_json(JOURNAL,pending)
    recover_transaction()
    print(f'[Rotation] Published {len(incoming)} reviewed candidates; catalog size {len(db["products"])}.')
    return incoming


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count',type=int,default=7)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    # The pipeline owns locking, validation and building for production.
    from dealvault_pipeline import pipeline_lock
    with pipeline_lock():
        rotate_deals(args.count,args.dry_run)
