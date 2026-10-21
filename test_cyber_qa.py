import os
import sys
import shutil
import http.server
import threading
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARTIFACT_DIR = r"C:\Users\Nika\.gemini\antigravity\brain\4a73aca6-c0c7-490f-9909-f6e1418bc641"
PORT = 8090
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
    print(f"[QA] Started local server at http://127.0.0.1:{PORT}")
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Desktop Test (1440x900)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="he-IL")
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append(f"PAGE_ERROR: {err}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE_{msg.type.upper()}: {msg.text}") if msg.type in ["error"] else None)

        print("[QA] Loading Desktop index.html...")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Trigger mouse move over the first card to verify tilt
        card = page.locator(".cyber-card").first
        box = card.bounding_box()
        if box:
            page.mouse.move(box["x"] + box["width"] * 0.75, box["y"] + box["height"] * 0.25)
            page.wait_for_timeout(500)

        page.screenshot(path="cyber_desktop.png")
        print("[QA] Saved cyber_desktop.png")

        # 2. Click card to open Holographic Modal Dossier
        print("[QA] Opening Modal Dossier...")
        card.click()
        page.wait_for_selector("#cyber-modal:not([hidden])", timeout=3000)
        page.wait_for_timeout(600)
        page.screenshot(path="cyber_modal.png")
        print("[QA] Saved cyber_modal.png")

        # Close modal
        page.click("#cyber-modal .modal-close-x")
        page.wait_for_timeout(400)

        # 3. Test Filter Matrix: Click price filter 'p2' (25 - 50 ₪)
        print("[QA] Testing Price Filter ₪25 - ₪50...")
        page.click('button[data-price="p2"]')
        page.wait_for_timeout(500)
        page.screenshot(path="cyber_filtered_price.png")
        print("[QA] Saved cyber_filtered_price.png")

        # 4. Test Rating filter
        print("[QA] Testing Rating 4.8+ filter...")
        page.click('button[data-toggle="rate48"]')
        page.wait_for_timeout(500)

        # 5. Switch to Russian language
        print("[QA] Testing Language Switch to Russian...")
        page.click("#cyber-pref-btn")
        page.wait_for_selector("#cyber-pref-modal:not([hidden])")
        page.wait_for_timeout(400)
        page.click('button[data-lang="ru"]')
        page.wait_for_timeout(600)
        page.click("#cyber-pref-modal .modal-close-x")
        page.wait_for_timeout(400)
        page.screenshot(path="cyber_russian.png")
        print("[QA] Saved cyber_russian.png")

        # Reset language to Hebrew
        page.click("#cyber-pref-btn")
        page.wait_for_timeout(400)
        page.click('button[data-lang="he"]')
        page.wait_for_timeout(500)
        page.click("#cyber-pref-modal .modal-close-x")
        page.wait_for_timeout(400)

        context.close()

        # 6. Mobile Test (iPhone 14 / 390x844)
        print("[QA] Loading Mobile viewport...")
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        m_page = mobile_ctx.new_page()
        m_page.on("pageerror", lambda err: errors.append(f"M_PAGE_ERROR: {err}"))
        m_page.on("console", lambda msg: errors.append(f"M_CONSOLE_ERR: {msg.text}") if msg.type in ["error"] else None)

        m_page.goto(BASE_URL, wait_until="networkidle")
        m_page.wait_for_timeout(800)
        m_page.screenshot(path="cyber_mobile.png")
        print("[QA] Saved cyber_mobile.png")

        # Mobile Modal
        m_card = m_page.locator(".cyber-card").first
        m_card.click()
        m_page.wait_for_selector("#cyber-modal:not([hidden])")
        m_page.wait_for_timeout(600)
        m_page.screenshot(path="cyber_mobile_modal.png")
        print("[QA] Saved cyber_mobile_modal.png")

        # Close mobile modal
        m_page.click("#cyber-modal .modal-close-x")
        m_page.wait_for_timeout(400)

        # 7. Standalone Deal Page Test
        print("[QA] Loading standalone deal page...")
        deal_url = f"http://127.0.0.1:{PORT}/deals/ugreen-nexode-air-100w-gan-charger.html"
        m_page.goto(deal_url, wait_until="networkidle")
        m_page.wait_for_timeout(800)
        m_page.screenshot(path="cyber_deal_mobile.png")

        # Desktop deal page
        d_deal_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        d_deal_page = d_deal_ctx.new_page()
        d_deal_page.goto(deal_url, wait_until="networkidle")
        d_deal_page.wait_for_timeout(800)
        d_deal_page.screenshot(path="cyber_deal_desktop.png")
        print("[QA] Saved cyber_deal_desktop.png")

        browser.close()

    # Copy screenshots to artifact dir
    shots = [
        "cyber_desktop.png", "cyber_modal.png", "cyber_filtered_price.png",
        "cyber_russian.png", "cyber_mobile.png", "cyber_mobile_modal.png",
        "cyber_deal_desktop.png", "cyber_deal_mobile.png"
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
