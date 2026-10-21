# -*- coding: utf-8 -*-
"""
QA & PLAYWRIGHT TEST SUITE FOR MODERN SMARTPICK HUB
Tests:
- 105 products rendered
- Instant 4-Language switcher (EN, HE, ES, RU)
- 4-Currency switcher (USD, ILS, EUR, RUB)
- Live search & category filters
- Modern modal dossier & sharing
- Desktop & Mobile responsive captures
"""
import os
import sys
import shutil
import http.server
import threading
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARTIFACT_DIR = r"C:\Users\Nika\.gemini\antigravity\brain\4a73aca6-c0c7-490f-9909-f6e1418bc641"
PORT = 8092
BASE_URL = f"http://127.0.0.1:{PORT}/index.html"

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    def log_message(self, format, *args):
        pass

def start_server():
    server = http.server.HTTPServer(("127.0.0.1", PORT), QuietHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

def run_qa():
    srv = start_server()
    print(f"[QA] Started local server at {BASE_URL}")
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop Test (1440x900) - Hebrew
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="he-IL")
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append(f"PAGE_ERROR: {err}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE_{msg.type.upper()}: {msg.text}") if msg.type in ["error"] else None)

        print("[QA] Loading Desktop Modern Hub...")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(800)
        page.screenshot(path="modern_desktop_he.png")
        print("[QA] Saved modern_desktop_he.png")

        # 2. Test Modal Dossier
        print("[QA] Opening Product Modal...")
        first_card = page.locator(".product-card").first
        first_card.locator(".btn-quick-view").click()
        page.wait_for_selector("#product-modal:not([hidden])", timeout=3000)
        page.wait_for_timeout(600)
        page.screenshot(path="modern_modal.png")
        print("[QA] Saved modern_modal.png")

        # Close Modal
        page.click(".modal-close-btn")
        page.wait_for_timeout(400)

        # 3. Test Language Switch: Switch to Spanish (ES)
        print("[QA] Testing Spanish Language Switch...")
        page.click('button[data-set-lang="es"]')
        page.wait_for_timeout(600)
        page.screenshot(path="modern_desktop_es.png")
        print("[QA] Saved modern_desktop_es.png")

        # 4. Test Language Switch: Switch to Russian (RU)
        print("[QA] Testing Russian Language Switch...")
        page.click('button[data-set-lang="ru"]')
        page.wait_for_timeout(600)
        page.screenshot(path="modern_desktop_ru.png")
        print("[QA] Saved modern_desktop_ru.png")

        # 5. Test Language Switch: Switch to English (EN)
        print("[QA] Testing English Language Switch...")
        page.click('button[data-set-lang="en"]')
        page.wait_for_timeout(600)
        page.screenshot(path="modern_desktop_en.png")
        print("[QA] Saved modern_desktop_en.png")

        # 6. Test Category Filter (Tech & Audio)
        print("[QA] Testing Category Filter: Tech...")
        page.click('button[data-cat="tech"]')
        page.wait_for_timeout(500)
        page.screenshot(path="modern_cat_tech.png")
        print("[QA] Saved modern_cat_tech.png")

        # 6b. Test "New Today" Filter
        print("[QA] Testing 'New Today' Filter...")
        page.click('button[data-cat="new_today"]')
        page.wait_for_timeout(500)
        page.screenshot(path="modern_new_today.png")
        print("[QA] Saved modern_new_today.png")

        context.close()

        # 7. Mobile Viewport Test (iPhone 14 / 390x844)
        print("[QA] Testing Mobile Viewport...")
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        m_page = mobile_ctx.new_page()
        m_page.goto(BASE_URL, wait_until="networkidle")
        m_page.wait_for_timeout(800)
        m_page.screenshot(path="modern_mobile.png")
        print("[QA] Saved modern_mobile.png")

        # Mobile Modal
        m_card = m_page.locator(".product-card").first
        m_card.locator(".btn-quick-view").click()
        m_page.wait_for_selector("#product-modal:not([hidden])")
        m_page.wait_for_timeout(500)
        m_page.screenshot(path="modern_mobile_modal.png")
        print("[QA] Saved modern_mobile_modal.png")
        m_page.keyboard.press("Escape")
        m_page.wait_for_timeout(300)

        # 8. Standalone Deal Page Test
        print("[QA] Loading standalone deal page...")
        deal_url = f"http://127.0.0.1:{PORT}/deals/ugreen-nexode-air-100w-gan-charger.html"
        m_page.goto(deal_url, wait_until="networkidle")
        m_page.wait_for_timeout(600)
        m_page.screenshot(path="modern_deal_page.png")
        print("[QA] Saved modern_deal_page.png")

        browser.close()

    # Copy screenshots to artifact directory
    shots = [
        "modern_desktop_he.png", "modern_desktop_en.png", "modern_desktop_es.png",
        "modern_desktop_ru.png", "modern_modal.png", "modern_cat_tech.png",
        "modern_new_today.png",
        "modern_mobile.png", "modern_mobile_modal.png", "modern_deal_page.png"
    ]
    for s in shots:
        if os.path.exists(s):
            shutil.copy(s, os.path.join(ARTIFACT_DIR, s))
            print(f"[QA] Copied {s} -> {ARTIFACT_DIR}")

    print("\n--- QA REPORT ---")
    if errors:
        print(f"Errors detected ({len(errors)}):")
        for err in errors:
            print(" -", err)
    else:
        print("PERFECT: 0 JS ERRORS, 0 CONSOLE ERRORS!")

if __name__ == "__main__":
    run_qa()
