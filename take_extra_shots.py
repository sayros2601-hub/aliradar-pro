from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 960})
    page.goto('http://127.0.0.1:8090/index.html')
    time.sleep(1.5)

    # 1. Open modal for second card
    btns = page.locator('.btn-review')
    if btns.count() > 1:
        btns.nth(1).click()
        time.sleep(1)
        page.screenshot(path='screenshot_gem_modal.png')
        page.locator('.modal-close').click()
        time.sleep(0.5)

    # 2. Filter under 50 ILS
    page.locator('[data-price="under50"]').click()
    time.sleep(1)
    page.screenshot(path='screenshot_under50_filter.png')

    # 3. Mobile final
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('[data-price="all"]').click()
    time.sleep(1)
    page.screenshot(path='screenshot_36_mobile.png')

    browser.close()

print('Extra shots taken successfully!')
