# -*- coding: utf-8 -*-
"""
VKONTAKTE (VK) MASS POSTER // BATCH 100 DEALS DISPATCHER
--------------------------------------------------------
Automates posting 100 deals to VK wall or public communities via wall.post API.
Supports simulation mode (--simulate) and live mode with safe rate-limiting delays.
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
RATE_RUB = 95.0

def load_products():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("products", [])

def format_vk_post(p, domain="https://dealvault.surge.sh"):
    slug = p["slug"]
    pr_usd = p["price_usd"]
    old_usd = p.get("old_price_usd", round(pr_usd * 1.8, 2))
    pr_rub = round(pr_usd * RATE_RUB)
    old_rub = round(old_usd * RATE_RUB)
    disc = p.get("discount_pct", 50)
    title = p.get("title_i18n", {}).get("ru") or p.get("title", "")
    desc = p.get("short_desc_i18n", {}).get("ru") or ""
    rating = p.get("rating", 4.9)
    orders = p.get("orders_count", 3500)
    deal_url = f"{domain}/deals/{slug}.html?utm_source=vk_mass&utm_medium=wall&utm_campaign=batch100"
    aff_url = p.get("affiliate_url", deal_url)

    text = (
        f"🔥 {title}\n\n"
        f"💬 {desc}\n\n"
        f"💰 Цена по акции: {pr_rub} ₽ (старая цена: {old_rub} ₽)\n"
        f"🏷️ Выгода: -{disc}% | ⭐ Рейтинг: {rating} ({orders} заказов)\n"
        f"🚚 Бесплатная доставка Choice в РФ\n"
        f"✂️ Промокод: AEIL02 ($2 скидка от $15)\n\n"
        f"👉 Заказать на AliExpress: {aff_url}\n"
        f"🌐 Подробный обзор и характеристики: {deal_url}\n\n"
        f"#aliexpress #скидки #акции #гаджеты #находки"
    )
    return text, aff_url

def send_vk_wall_post(token, owner_id, message, attachments=None, simulate=False):
    if simulate:
        print("[VK SIMULATE POST]")
        print(message[:140] + "...")
        print("-" * 50)
        return True

    api_url = "https://api.vk.com/method/wall.post"
    params = {
        "access_token": token,
        "owner_id": owner_id,
        "from_group": 1,
        "message": message,
        "v": "5.199"
    }
    if attachments:
        params["attachments"] = attachments

    req = urllib.request.Request(
        api_url,
        data=urllib.parse.urlencode(params).encode("utf-8"),
        headers={"User-Agent": "SmartPickVKPoster/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "response" in data:
                return True
            else:
                print("VK Error:", data.get("error", {}).get("error_msg"))
                return False
    except Exception as ex:
        print(f"Network error: {ex}")
        return False

def main():
    parser = argparse.ArgumentParser(description="SmartPick VK Mass Poster (100 Deals)")
    parser.add_argument("--token", help="VK User or Community Access Token")
    parser.add_argument("--owner_id", help="Owner ID (for groups prefix with minus, e.g. -12345678)")
    parser.add_argument("--count", type=int, default=100, help="Number of deals to post (default: 100)")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between posts in seconds (default: 3.0s)")
    parser.add_argument("--simulate", action="store_true", help="Simulate posting without live API requests")

    args = parser.parse_args()
    products = load_products()[:args.count]

    print(f"==================================================")
    print(f"SMARTPICK VK MASS POSTER")
    print(f"Target count: {len(products)} deals | Simulation: {args.simulate}")
    print(f"==================================================")

    if not args.simulate and (not args.token or not args.owner_id):
        print("Error: Live mode requires --token <VK_TOKEN> and --owner_id <ID>.")
        print("Tip: Run with --simulate to preview 100 posts locally without a token!")
        sys.exit(1)

    success_count = 0
    for idx, p in enumerate(products, 1):
        msg, aff_url = format_vk_post(p)
        print(f"[{idx}/{len(products)}] Posting: {p['slug']}...")
        ok = send_vk_wall_post(args.token, args.owner_id, msg, attachments=aff_url, simulate=args.simulate)
        if ok:
            success_count += 1
        if idx < len(products) and not args.simulate:
            time.sleep(args.delay)

    print(f"\nVK Mass posting finished! Successfully processed: {success_count}/{len(products)} deals.")

if __name__ == "__main__":
    main()
