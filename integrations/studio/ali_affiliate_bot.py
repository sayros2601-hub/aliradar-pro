"""
PAWSVAULT STUDIO - AliExpress Affiliate Automation Engine
Autonomous tool for searching viral products, generating monetized affiliate links,
extracting product media, and monitoring commissions without user intervention.
"""

import os
import time
import json
import re
from playwright.sync_api import sync_playwright

USER_DATA_DIR = r"C:\Users\Nika\Desktop\PAWSVAULT_STUDIO\chrome_affiliate_profile"
SCREENSHOTS_DIR = r"C:\Users\Nika\Desktop\PAWSVAULT_STUDIO\ALIEXPRESS_EXPLORATION"

class AliAffiliateEngine:
    def __init__(self, headless=True):
        self.headless = headless
        self.user_data_dir = USER_DATA_DIR

    def _get_context(self, playwright):
        return playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            channel="chrome",
            headless=self.headless,
            viewport={"width": 1920, "height": 1080},
            args=[]
        )

    def get_account_overview(self):
        """Fetches current balance, account name, and unread notifications."""
        with sync_playwright() as p:
            context = self._get_context(p)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://portals.aliexpress.com/affiportals/web/home.htm", timeout=45000)
            page.wait_for_timeout(3000)

            account_name = page.locator(".user-name, [class*='userName'], [class*='user-info']").first.inner_text().strip() if page.locator(".user-name, [class*='userName'], [class*='user-info']").count() > 0 else None

            # A generic first USD element is not evidence of account balance.
            # Until the account widget is verified, report no financial value.
            balance_text = None

            data = {
                "account_name": account_name,
                "balance": balance_text,
                "balance_status": "not_verified",
                "url": page.url
            }
            context.close()
            return data

    def search_products(self, keyword, max_results=10):
        """Searches Ad Center for products matching keyword and extracts details."""
        products = []
        with sync_playwright() as p:
            context = self._get_context(p)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://portals.aliexpress.com/affiportals/web/ad_center.htm", timeout=45000)
            page.wait_for_timeout(3000)

            # Click Search tab
            search_tab = page.get_by_text("Search", exact=True)
            if search_tab.count() > 0:
                search_tab.first.click()
                page.wait_for_timeout(2000)

            # Enter keyword
            search_input = page.locator("input[placeholder*='keyword'], input[placeholder*='Search'], input[type='text']").first
            search_input.fill(keyword)
            page.keyboard.press("Enter")
            page.wait_for_timeout(4000)

            # Parse product cards
            cards = page.locator(".card-view, [class*='product-card'], [class*='goods-item']").all()
            if not cards:
                # Fallback to items containing 'USD'
                cards = page.locator("div:has-text('USD')").all()

            # Direct extraction via JavaScript evaluation for ultra-fast, robust scraping
            results = page.evaluate("""() => {
                const items = [];
                const buttons = Array.from(document.querySelectorAll('button, a')).filter(el => el.innerText.trim() === 'Promote now');
                buttons.forEach(btn => {
                    const card = btn.closest('div[class*="item"], div[class*="card"]') || btn.parentElement.parentElement;
                    if (card) {
                        const text = card.innerText;
                        const img = card.querySelector('img');
                        items.push({
                            text: text,
                            img_src: img ? img.src : null
                        });
                    }
                });
                return items;
            }""")

            for idx, r in enumerate(results[:max_results]):
                lines = [l.strip() for l in r["text"].split("\n") if l.strip()]
                products.append({
                    "id": idx + 1,
                    "title": lines[0] if lines else "Product",
                    "details": lines,
                    "image": r.get("img_src")
                })

            context.close()
        return products

    def get_promo_material_and_link(self, keyword_or_index, tracking_id="default", result_index=0):
        """Clicks 'Promote now' on the chosen item and extracts the affiliate link + clean promo photos."""
        if tracking_id != "default":
            raise ValueError("Tracking-id changes are not supported; original Portals attribution is preserved.")
        if not isinstance(keyword_or_index,str) or not keyword_or_index.strip():
            raise ValueError("An explicit search query is required; no default product.")
        if type(result_index) is not int or result_index < 0:
            raise ValueError("A non-negative candidate index is required.")
        with sync_playwright() as p:
            context = self._get_context(p)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://portals.aliexpress.com/affiportals/web/ad_center.htm", timeout=45000)
            page.wait_for_timeout(3000)

            search_tab = page.get_by_text("Search", exact=True)
            if search_tab.count() > 0:
                search_tab.first.click()
                page.wait_for_timeout(2000)

            search_input = page.locator("input[placeholder*='keyword'], input[placeholder*='Search'], input[type='text']").first
            search_input.fill(keyword_or_index.strip())
            page.keyboard.press("Enter")
            page.wait_for_timeout(4000)

            # Click Promote now
            promote_btns = page.get_by_text("Promote now", exact=True).all()
            if result_index >= len(promote_btns):
                context.close()
                return None

            promote_btns[result_index].click()
            page.wait_for_timeout(2500)

            # Extract modal info
            modal_data = page.evaluate("""() => {
                const modal = document.querySelector('.ant-modal, [role="dialog"], .next-dialog');
                if (!modal) return null;
                const linkElem = Array.from(modal.querySelectorAll('a, span, div')).find(el => el.innerText && el.innerText.includes('s.click.aliexpress.com'));
                const images = Array.from(modal.querySelectorAll('img')).map(img => img.src);
                return {
                    full_text: modal.innerText,
                    affiliate_link: linkElem ? linkElem.innerText : null,
                    images: images
                };
            }""")

            context.close()
            return modal_data

if __name__ == "__main__":
    engine = AliAffiliateEngine(headless=True)
    status = engine.get_account_overview()
    print("Account Overview:", status)
