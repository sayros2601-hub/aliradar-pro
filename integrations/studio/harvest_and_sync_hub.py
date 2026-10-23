# -*- coding: utf-8 -*-
"""
PAWSVAULT STUDIO // AUTO-HARVEST & SYNC ENGINE FOR DEALVAULT
------------------------------------------------------------
1. Connects to user's AliExpress Portals session.
2. Captures candidates from Ad Center; conversion is not established.
3. Automatically validates each link via HTTP redirect to check product destinations.
4. Stages captured records in DealVault inbox for editorial review.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = (r"C:\Users\Nika\Desktop\Antigravity_Projects\PAWSVAULT_STUDIO"
        if os.path.exists(r"C:\Users\Nika\Desktop\Antigravity_Projects\PAWSVAULT_STUDIO")
        else r"C:\Users\Nika\Desktop\PAWSVAULT_STUDIO")
PROFILE_DIR = os.path.join(ROOT, "chrome_affiliate_profile")
HUB_DIR = r"C:\Users\Nika\.gemini\antigravity\scratch\aliexpress_seo_hub"
PRODUCTS_FILE = os.path.join(HUB_DIR, "data", "products.json")

# Queries come from recent regional evidence, not advertiser order.
if HUB_DIR not in sys.path:
    sys.path.insert(0,HUB_DIR)
from product_selection import research_plan


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def verify_link_is_alive(url):
    if HUB_DIR not in sys.path:
        sys.path.insert(0, HUB_DIR)
    from link_health_guard import check_single_link
    return check_single_link({"id": "candidate", "affiliate_url": url})["status"] == "RESOLVED"


def harvest_and_sync():
    print("=====================================================")
    print("ALIEXPRESS PORTALS -> DEALVAULT AUTO-SYNC HARVESTER")
    print("=====================================================")

    if not os.path.exists(PROFILE_DIR):
        print(f"Error: Profile dir {PROFILE_DIR} does not exist.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=True,
            viewport={"width": 1920, "height": 1080},
            args=[]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        print("Checking AliExpress Portals session...")
        page.goto("https://portals.aliexpress.com/affiportals/web/ad_center.htm", timeout=45000)
        page.wait_for_timeout(3500)

        if "login" in page.url.lower():
            print("\n[!] Внимание: Сессия в AliExpress Portals требует входа.")
            print("Пожалуйста, запустите на рабочем столе 'AliExpress_Partner_Bot.bat' и авторизуйтесь.")
            browser.close()
            return

        print("[✓] Сессия активна! Переход в Ad Center...")

        search_tab = page.get_by_text("Search", exact=True)
        if search_tab.count() > 0:
            search_tab.first.click()
            page.wait_for_timeout(1500)

        # Existing products
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
        existing_urls = {p.get("affiliate_url") for p in db.get("products", [])}
        new_items = []
        next_result = {}

        for lead in [lead for lead in research_plan() for _ in range(3)]:
            cat,kw,country=lead["category"],lead["query"],lead["country"]
            print(f"Searching Ad Center: '{kw}' ({cat})...")
            try:
                # Close any modals
                page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, a, span')).filter(el => el.innerText.trim() === 'Close');
                    if (btns.length) btns[btns.length - 1].click();
                }""")
                page.wait_for_timeout(400)

                input_box = page.locator("input[placeholder*='keyword'], input[placeholder*='Search'], input[type='text']").first
                input_box.fill(kw)
                page.keyboard.press("Enter")
                page.wait_for_timeout(3500)

                buttons=page.get_by_text("Promote now",exact=True)
                result_index=next_result.get((country,kw),0)
                next_result[(country,kw)]=result_index+1
                if result_index >= buttons.count():
                    continue
                buttons.nth(result_index).click()

                page.wait_for_timeout(2500)

                data = page.evaluate("""() => {
                    const modal = document.querySelector('.next-dialog, .ant-modal, [role="dialog"]');
                    if (!modal) return null;
                    const ta = modal.querySelector('textarea');
                    const text = ta ? ta.value : modal.innerText;
                    const imgs = Array.from(modal.querySelectorAll('img')).map(img => img.src || '').filter(s => s.includes('alicdn') || s.includes('aliexpress-media'));
                    return { text: text, images: imgs };
                }""")

                if not data or not data.get("text"):
                    continue

                # Parse link
                match = re.search(r'https://s\.click\.aliexpress\.com/e/[a-zA-Z0-9_\-]+', data["text"])
                if not match:
                    continue
                aff_url = match.group(0)

                if aff_url in existing_urls:
                    print(f"  Already in catalog: {aff_url}")
                    continue

                # Resolve destination before staging; this does not verify stock.
                print(f"  Testing link health for {aff_url}...")
                if not verify_link_is_alive(aff_url):
                    print(f"  [!] Destination not conclusively resolved; record not staged.")
                    continue

                print("  [Destination resolved; stock not independently verified]")
                existing_urls.add(aff_url)
                new_items.append({"affiliate_url": aff_url, "text": data["text"], "images": data.get("images", []), "category": cat, "query": kw, "result_index": result_index, "target_country": country, "selection": {"country": country, "need_id": lead["need_id"], "demand_snapshot_id": lead["demand_snapshot_id"]}})

            except Exception as e:
                print(f"  Error on {kw}: {e}")

        browser.close()
        if HUB_DIR not in sys.path:
            sys.path.insert(0, HUB_DIR)
        from import_portals import stage_records
        stage_records(new_items)

if __name__ == "__main__":
    harvest_and_sync()
