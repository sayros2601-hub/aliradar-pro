import json
import time
import os
from playwright.sync_api import sync_playwright

USER_DATA_DIR = r"C:\Users\Nika\Desktop\PAWSVAULT_STUDIO\chrome_affiliate_profile"
OUT_FILE = r"C:\Users\Nika\.gemini\antigravity\scratch\aliexpress_seo_hub\data\new_portals_batch.json"

QUERIES = [
    ("gadgets", "mini thermal printer portable", "mini-pocket-thermal-label-printer"),
    ("gadgets", "magnetic 3 in 1 foldable wireless charger", "magnetic-3in1-foldable-magsafe-charger"),
    ("gadgets", "ultrasonic cleaner jewelry glasses portable", "ultrasonic-cleaner-tank-glasses-jewelry"),
    ("gadgets", "electric fabric shaver lint remover", "rechargeable-fabric-shaver-lint-remover"),
    ("gadgets", "smart tracker tag find my", "apple-find-my-smart-gps-tag-tracker"),
    ("auto", "solar tpms tire pressure monitor", "solar-wireless-tpms-tire-pressure-monitor"),
    ("auto", "2 in 1 car vacuum cleaner cordless air duster", "2in1-cordless-car-vacuum-turbo-blower"),
    ("auto", "telescopic car rearview mirror phone holder", "telescopic-rearview-mirror-car-phone-mount"),
    ("auto", "retractable car charger usb c lightning", "retractable-fast-car-charger-dual-cable"),
    ("auto", "solar car aroma diffuser rotating", "solar-rotating-car-perfume-diffuser"),
    ("smarthome", "motion sensor led light cabinet ultra thin", "magnetic-motion-sensor-led-cabinet-light"),
    ("smarthome", "electric wine opener automatic corkscrew", "automatic-electric-wine-corkscrew-opener"),
    ("smarthome", "digital measuring spoon scale 0.1g", "digital-lcd-measuring-spoon-scale"),
    ("smarthome", "automatic foam soap dispenser touchless", "automatic-touchless-foaming-soap-dispenser"),
    ("smarthome", "smart coffee mug warmer coaster", "smart-coffee-mug-warmer-coaster"),
    ("smarthome", "electric gravity salt pepper grinder", "electric-gravity-salt-pepper-grinder"),
    ("pets", "dog paw cleaner cup silicone", "soft-silicone-dog-paw-cleaner-cup"),
    ("pets", "ultrasonic dog bark deterrent device", "automatic-ultrasonic-dog-barking-deterrent"),
    ("tools", "laser measure distance meter 40m", "digital-laser-measure-distance-meter-40m"),
    ("tools", "18 in 1 snowflake tool stainless steel", "18in1-snowflake-edc-pocket-multi-tool"),
    ("under10", "cob keychain flashlight mini rechargeable", "rechargeable-mini-cob-keychain-flashlight"),
    ("under10", "rfid blocking card holder pop up", "anti-theft-rfid-blocking-pop-up-cardholder"),
    ("under10", "mini bag sealer heat cutter portable", "mini-portable-heat-bag-sealer-cutter"),
    ("under10", "360 splash filter faucet aerator nozzle", "360-splash-proof-kitchen-faucet-aerator"),
]

def harvest():
    results = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        print("Opening Portals Ad Center...", flush=True)
        page.goto("https://portals.aliexpress.com/affiportals/web/ad_center.htm", timeout=45000)
        page.wait_for_timeout(3500)

        search_tab = page.get_by_text("Search", exact=True)
        if search_tab.count() > 0:
            search_tab.first.click()
            page.wait_for_timeout(1500)

        for cat, query, slug in QUERIES:
            print(f"[{cat}] Searching: {query}...", flush=True)
            try:
                page.keyboard.press("Escape")
                time.sleep(0.3)

                # Ensure dialogs are closed
                page.evaluate('''() => {
                    const closeBtns = Array.from(document.querySelectorAll('button, a, span')).filter(el => el.innerText.trim() === 'Close');
                    if (closeBtns.length) closeBtns[closeBtns.length - 1].click();
                }''')
                time.sleep(0.3)

                inp = page.locator("input[placeholder*='keyword'], input[placeholder*='Search'], input[type='text']").first
                inp.fill(query)
                page.keyboard.press("Enter")
                page.wait_for_timeout(2500)

                btn = page.locator("text='Promote now'").first
                if btn.count() == 0:
                    print(f"  No promote button for {query}", flush=True)
                    continue

                btn.click()
                page.wait_for_timeout(2000)

                data = page.evaluate('''() => {
                    const ta = document.querySelector('textarea');
                    const text = ta ? ta.value : '';
                    const imgs = Array.from(document.querySelectorAll('img'))
                        .map(i => i.src)
                        .filter(s => s && s.includes('aliexpress-media.com') && s.includes('/kf/'));
                    return { text: text, imgs: Array.from(new Set(imgs)) };
                }''')

                text = data.get("text", "")
                link_match = None
                lines = text.split("\n")
                for line in lines:
                    if "s.click.aliexpress.com" in line:
                        parts = line.split()
                        for pt in parts:
                            if "s.click.aliexpress.com" in pt:
                                link_match = pt.strip()
                                break
                
                # title is usually the line before link
                raw_title = lines[0].replace("Top On Sale Product Recommendations!", "").strip() if lines else query

                imgs = data.get("imgs", [])
                print(f"  Found: {raw_title[:45]} | Link: {link_match} | Imgs: {len(imgs)}", flush=True)

                results.append({
                    "category": cat,
                    "query": query,
                    "slug": slug,
                    "raw_title": raw_title,
                    "affiliate_url": link_match or "https://s.click.aliexpress.com/e/_c4XMCrnL",
                    "images": imgs[:6]
                })

                # Close modal
                page.evaluate('''() => {
                    const closeBtns = Array.from(document.querySelectorAll('button, a, span')).filter(el => el.innerText.trim() === 'Close');
                    if (closeBtns.length) closeBtns[closeBtns.length - 1].click();
                }''')
                page.wait_for_timeout(1000)

            except Exception as e:
                print(f"  Error on {query}: {e}", flush=True)

        context.close()

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nSuccessfully harvested {len(results)} new products into {OUT_FILE}!", flush=True)

if __name__ == "__main__":
    harvest()
