import json
import os
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / 'campaigns' / 'pinterest_us_bulk_scheduled.csv'
SCREENSHOT_DIR = BASE_DIR / 'campaigns'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_URL = "http://127.0.0.1:9222"

def ensure_chrome_with_cdp():
    raise RuntimeError('Unsafe legacy launcher retired: it terminated every Chrome window and enabled broad remote access. Use the connected browser and verified RSS settings; no browser was stopped.')


def run_pinterest_automation():
    print("=" * 60)
    print("AUTONOMOUS PINTEREST BULK BOT")
    print("=" * 60)

    if not ensure_chrome_with_cdp():
        print("Cannot attach to Chrome.")
        return

    with sync_playwright() as p:
        print("Connecting to live Chrome session via CDP...")
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]

        # Find existing Pinterest tab or open a new one
        target_page = None
        for page in context.pages:
            if 'pinterest.com' in page.url:
                target_page = page
                print(f"✓ Found existing Pinterest tab: {page.url}")
                break

        if not target_page:
            print("Opening new tab for Pinterest Bulk Pin Creation...")
            target_page = context.new_page()
            target_page.goto("https://www.pinterest.com/pin-creation-tool/bulk-pins/", wait_until="domcontentloaded")
        else:
            if "bulk-pins" not in target_page.url:
                print("Navigating existing Pinterest tab to Bulk Pins tool...")
                target_page.goto("https://www.pinterest.com/pin-creation-tool/bulk-pins/", wait_until="domcontentloaded")

        time.sleep(3)
        print(f"Current page URL: {target_page.url}")
        print(f"Page title: {target_page.title()}")

        # Check if redirected to login or business convert
        if "login" in target_page.url:
            print("Notice: Pinterest is asking for login. Please check the browser.")
            target_page.screenshot(path=str(SCREENSHOT_DIR / "pinterest_login_required.png"))
            return

        target_page.screenshot(path=str(SCREENSHOT_DIR / "pinterest_landing.png"))
        print(f"✓ Saved landing screenshot: {SCREENSHOT_DIR / 'pinterest_landing.png'}")

        # Look for file upload input
        file_input = target_page.query_selector('input[type="file"]')
        if file_input:
            print(f"✓ Found file input element. Attaching {CSV_PATH.name}...")
            file_input.set_input_files(str(CSV_PATH))
            print("✓ File uploaded to Pinterest! Waiting for validation...")
            time.sleep(5)
            
            target_page.screenshot(path=str(SCREENSHOT_DIR / "pinterest_after_upload.png"))
            print(f"✓ Saved post-upload screenshot: {SCREENSHOT_DIR / 'pinterest_after_upload.png'}")
            
            # Look for publish or submit buttons
            buttons = target_page.query_selector_all('button')
            for b in buttons:
                txt = b.inner_text().strip().lower()
                if any(k in txt for k in ['create', 'publish', 'save', 'submit', 'запланировать', 'опубликовать', 'создать']):
                    print(f"Found submit button: '{b.inner_text()}'. Clicking...")
                    try:
                        b.click()
                        time.sleep(4)
                        target_page.screenshot(path=str(SCREENSHOT_DIR / "pinterest_published.png"))
                        print("✓ Pins successfully submitted to Pinterest schedule!")
                        break
                    except Exception as e:
                        print(f"Click failed: {e}")
        else:
            print("File input not found directly. Checking dropzone or UI elements...")
            # Print page buttons and inputs for diagnostic
            inputs = target_page.query_selector_all('input')
            print(f"Found {len(inputs)} inputs on page.")

        print("Automation task complete.")

if __name__ == '__main__':
    run_pinterest_automation()
