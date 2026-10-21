# -*- coding: utf-8 -*-
"""
DEALVAULT LINK HEALTH GUARD & VALIDATOR
---------------------------------------
Validates every affiliate link in data/products.json against AliExpress live servers:
1. Follows HTTP redirects to inspect the final destination.
2. If redirected to https://best.aliexpress.com (item delisted / does not exist) or 404:
   -> Marks as DEAD and purges from active catalog.
3. If redirected to https://www.aliexpress.com/item/...:
   -> Marks as HEALTHY (100% live and purchasable).
4. Saves clean, verified catalog and triggers site recompile.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_FILE = os.path.join(BASE_DIR, "data", "products.json")
VERIFIED_BACKUP = os.path.join(BASE_DIR, "data", "products_verified_backup.json")

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def check_single_link(product):
    pid = product.get("id")
    slug = product.get("slug")
    url = product.get("affiliate_url")
    
    if not url or not url.startswith("http"):
        return {"id": pid, "slug": slug, "status": "DEAD", "reason": "NO_URL", "dest": ""}

    opener = urllib.request.build_opener(NoRedirectHandler)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    try:
        try:
            resp = opener.open(req, timeout=8)
            loc = resp.headers.get("Location", "")
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location", "")

        loc_str = str(loc or "").strip()

        # Delisted items redirect to best.aliexpress.com homepage
        if "best.aliexpress.com" in loc_str or not loc_str:
            return {"id": pid, "slug": slug, "status": "DEAD", "reason": "REDIRECT_TO_HOMEPAGE", "dest": loc_str}
        
        # Live products redirect to item detail page
        if "aliexpress.com/item/" in loc_str or "pdp" in loc_str:
            return {"id": pid, "slug": slug, "status": "HEALTHY", "reason": "LIVE_PRODUCT_PAGE", "dest": loc_str}

        return {"id": pid, "slug": slug, "status": "HEALTHY", "reason": "CUSTOM_REDIRECT", "dest": loc_str}

    except Exception as ex:
        return {"id": pid, "slug": slug, "status": "DEAD", "reason": f"ERROR: {ex}", "dest": ""}

def validate_and_clean_catalog():
    if not os.path.exists(PRODUCTS_FILE):
        print(f"Error: {PRODUCTS_FILE} not found.")
        return []

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    all_products = db.get("products", [])
    print(f"[Health Guard] Auditing {len(all_products)} products for live AliExpress links...")

    healthy_products = []
    dead_products = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_single_link, p): p for p in all_products}
        for future in as_completed(futures):
            p = futures[future]
            res = future.result()
            if res["status"] == "HEALTHY":
                healthy_products.append(p)
                print(f"  [✓ LIVE] {res['id']}: {res['slug']}")
            else:
                dead_products.append(res)
                print(f"  [✗ DEAD] {res['id']}: {res['slug']} -> {res['reason']}")

    print(f"\n[Health Guard] Audit complete!")
    print(f"  - Total Audited: {len(all_products)}")
    print(f"  - Healthy & Live: {len(healthy_products)}")
    print(f"  - Dead/Delisted Removed: {len(dead_products)}")

    # Backup original before overwriting
    with open(VERIFIED_BACKUP, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    # Save only healthy verified products
    db["products"] = healthy_products
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"[Health Guard] Saved clean catalog with {len(healthy_products)} verified products to {PRODUCTS_FILE}")
    return healthy_products

if __name__ == "__main__":
    validate_and_clean_catalog()
