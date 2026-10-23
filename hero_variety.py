"""Editorial hero shortlist: real catalog photos, never synthetic products."""
import hashlib
from dealvault_core import BASE_DIR, LANGUAGES, page_path, product_title, public_path

# Reviewed together for distinct subjects: travel, repair, pets and home.
# Missing/withdrawn products are omitted, rather than resurrected from this list.
HERO_IDS = (
    'real-109', 'real-111', 'real-123', 'real-125', 'real-106', 'real-113',
    'real-116', 'real-126', 'real-128', 'real-131', 'real-102', 'real-103',
)


def hero_products(products):
    by_id = {p['id']: p for p in products}
    selected, photos = [], set()
    for pid in HERO_IDS:
        p = by_id.get(pid)
        if not p or not all(p.get('title_i18n', {}).get(lang) for lang in LANGUAGES):
            continue
        fingerprint = hashlib.sha256((BASE_DIR / p['image']).read_bytes()).hexdigest()
        if fingerprint not in photos:
            selected.append((p, fingerprint))
            photos.add(fingerprint)
    if not selected:
        p = products[0]
        selected = [(p, hashlib.sha256((BASE_DIR / p['image']).read_bytes()).hexdigest())]
    return selected


def hero_payload(selected, images, lang):
    return [{'id': p['id'], 'key': fingerprint, 'image': public_path(images[p['image']]),
             'href': public_path(page_path(lang, p['slug'])), 'title': product_title(p, lang)}
            for p, fingerprint in selected]
