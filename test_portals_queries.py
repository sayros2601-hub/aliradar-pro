from playwright.sync_api import sync_playwright
import time
import re

USER_DATA_DIR = r"C:\Users\Nika\Desktop\PAWSVAULT_STUDIO\chrome_affiliate_profile"

TEST_QUERIES = [
    "mini thermal printer portable",
    "solar tpms tire pressure monitor",
    "motion sensor led light cabinet",
    "ultrasonic cleaner portable jewelry"
]

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        channel="chrome",
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://portals.aliexpress.com/affiportals/web/ad_center.htm", timeout=45000)
    page.wait_for_timeout(3500)
    
    search_tab = page.get_by_text("Search", exact=True)
    if search_tab.count() > 0:
        search_tab.first.click()
        page.wait_for_timeout(1500)
    
    for q in TEST_QUERIES:
        print(f"Testing query: {q}")
        # close any lingering modal
        page.keyboard.press("Escape")
        time.sleep(0.5)

        inp = page.locator("input[placeholder*='keyword'], input[placeholder*='Search'], input[type='text']").first
        inp.fill(q)
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        
        btn = page.locator("text='Promote now'").first
        if btn.count() > 0:
            print("  Found Promote button!")
            btn.click()
            page.wait_for_timeout(2000)
            
            data = page.evaluate('''() => {
                const ta = document.querySelector('textarea');
                const text = ta ? ta.value : '';
                const imgs = Array.from(document.querySelectorAll('img'))
                    .map(i => i.src)
                    .filter(s => s && s.includes('aliexpress-media.com') && s.includes('/kf/'));
                return { text: text, imgs: imgs };
            }''')
            print("  Text:", data.get("text", "")[:120].replace("\n", " "))
            print("  Images found:", len(data.get("imgs", [])))
            for im in data.get("imgs", [])[:3]:
                print("    ", im)

            # Close dialog cleanly
            page.evaluate('''() => {
                const closeBtns = Array.from(document.querySelectorAll('button, a, span')).filter(el => el.innerText.trim() === 'Close');
                if (closeBtns.length) closeBtns[closeBtns.length - 1].click();
            }''')
            time.sleep(1)
        else:
            print("  No promote button found.")

    context.close()
