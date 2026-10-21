"""
Fetches real, high-converting products directly from AliExpress Portals (Ad Center)
for Israel, USA, and Europe buyers, with real square AliExpress CDN photos (ae-pic-a1.aliexpress-media.com)
and real s.click.aliexpress.com tracking links!
"""

import os
import re
import json
import time
from playwright.sync_api import sync_playwright

USER_DATA_DIR = r"C:\Users\Nika\Desktop\PAWSVAULT_STUDIO\chrome_affiliate_profile"

QUERIES = [
    ("gadgets", "ugreen gan charger type c"),
    ("gadgets", "baseus power bank fast charge"),
    ("auto", "70mai dash cam car dvr"),
    ("auto", "wireless car air compressor pump"),
    ("smarthome", "tuya zigbee smart sensor"),
    ("smarthome", "electric precision screwdriver set"),
    ("under10", "240w usb type c cable fast charge"),
    ("under10", "magnetic phone holder car mount"),
]


def grab_portals():
    results = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=True,
            viewport={"width": 1920, "height": 1080},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        print("Opening Ad Center...", flush=True)
        page.goto("https://portals.aliexpress.com/affiportals/web/ad_center.htm", timeout=45000)
        page.wait_for_timeout(3500)

        search_tab = page.get_by_text("Search", exact=True)
        if search_tab.count() > 0:
            search_tab.first.click()
            page.wait_for_timeout(1500)

        for cat, q in QUERIES:
            print(f"Searching: {q}...", flush=True)
            try:
                # Ensure any open modal is closed first
                page.evaluate(
                    """() => {
                        const closeBtns = Array.from(document.querySelectorAll('button, a, span')).filter(el => el.innerText.trim() === 'Close');
                        if (closeBtns.length) closeBtns[closeBtns.length - 1].click();
                        const xBtns = document.querySelectorAll('.next-dialog-close, .ant-modal-close');
                        xBtns.forEach(b => b.click());
                    }"""
                )
                page.wait_for_timeout(500)

                search_input = page.locator(
                    "input[placeholder*='keyword'], input[placeholder*='Search'], input[type='text']"
                ).first
                search_input.fill(q)
                page.keyboard.press("Enter")
                page.wait_for_timeout(3500)

                # Click first Promote now button via JS to avoid overlay interception
                clicked = page.evaluate(
                    """() => {
                        const btns = Array.from(document.querySelectorAll('.material-card-promot-button, button, div'))
                            .filter(el => el.innerText && el.innerText.trim() === 'Promote now');
                        if (!btns.length) return false;
                        btns[0].click();
                        return true;
                    }"""
                )
                if not clicked:
                    print(f"  No buttons for {q}", flush=True)
                    continue

                page.wait_for_timeout(2400)

                data = page.evaluate(
                    """() => {
                        const modal = document.querySelector('.next-dialog, .ant-modal, [role="dialog"]');
                        if (!modal) return null;
                        const ta = modal.querySelector('textarea');
                        const text = ta ? ta.value : modal.innerText;
                        const imgs = Array.from(modal.querySelectorAll('img'))
                            .map(img => img.src || '')
                            .filter(src => src.includes('aliexpress-media.com') || src.includes('alicdn.com'));
                        return { text: text, images: imgs };
                    }"""
                )

                # Close modal cleanly
                page.evaluate(
                    """() => {
                        const closeBtns = Array.from(document.querySelectorAll('button, a, span')).filter(el => el.innerText.trim() === 'Close');
                        if (closeBtns.length) closeBtns[closeBtns.length - 1].click();
                        const xBtns = document.querySelectorAll('.next-dialog-close, .ant-modal-close');
                        xBtns.forEach(b => b.click());
                    }"""
                )
                page.wait_for_timeout(800)

                if data and data.get("text"):
                    print(f"  [+] Got modal for {q}: {len(data.get('images', []))} images", flush=True)
                    results.append({"category": cat, "query": q, "modal": data})
            except Exception as e:
                print(f"  [!] Error on {q}: {str(e)[:80].encode('ascii', 'ignore').decode()}", flush=True)

        context.close()

    out_file = r"C:\Users\Nika\.gemini\antigravity\scratch\aliexpress_seo_hub\data\raw_portals_batch.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(results)} items to {out_file}", flush=True)


if __name__ == "__main__":
    grab_portals()
