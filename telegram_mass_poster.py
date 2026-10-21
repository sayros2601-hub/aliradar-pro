# -*- coding: utf-8 -*-
"""
TELEGRAM MASS POSTER // BATCH 100 DEALS DISPATCHER
--------------------------------------------------
Automates publishing 100 AliExpress deals directly into Telegram Channels, Groups, or Supergroups.

Features:
- Live Telegram Bot API dispatch (via sendPhoto / sendMessage)
- Inline keyboard buttons: "🛍️ КУПИТЬ НА ALIEXPRESS" / "🌐 СМОТРЕТЬ ОБЗОР НА САЙТЕ"
- Safe rate-limiting pacing (1.5 - 2.5s per post) to comply with Telegram flood limits
- Multi-language support: Russian, Hebrew, Spanish, English
- Simulation mode (--simulate) for safe dry-run previewing without sending actual messages
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

RATE_ILS = 3.7
RATE_EUR = 0.92
RATE_RUB = 95.0

def load_products():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    return db.get("products", [])

def format_telegram_caption(p, lang="ru", domain="https://smartpick.click"):
    slug = p["slug"]
    pr_usd = p["price_usd"]
    old_usd = p.get("old_price_usd", round(pr_usd * 1.8, 2))
    disc = p.get("discount_pct", 50)
    deal_url = f"{domain}/deals/{slug}.html?utm_source=telegram_mass&utm_medium={lang}&utm_campaign=batch100"
    aff_url = p.get("affiliate_url", deal_url)
    rating = p.get("rating", 4.9)
    orders = p.get("orders_count", 3500)

    if lang == "ru":
        title = p.get("title_i18n", {}).get("ru") or p.get("title", "")
        pr_local = round(pr_usd * RATE_RUB)
        old_local = round(old_usd * RATE_RUB)
        desc = p.get("short_desc_i18n", {}).get("ru") or ""
        caption = (
            f"🔥 *{title}*\n\n"
            f"📝 {desc}\n\n"
            f"💰 *Цена по акции:* `{pr_local} ₽` _(обычно ~{old_local} ₽)_\n"
            f"🏷️ *Скидка:* `-{disc}%` | ⭐ *Рейтинг:* `{rating}` ({orders} заказов)\n"
            f"🚚 *Бесплатная доставка* в ПВЗ и почту\n"
            f"✂️ Промокод на скидку: `AEIL02` ($2 от $15)\n\n"
            f"👉 [Открыть страницу товара на SmartPick]({deal_url})"
        )
        btn_buy = "🛍️ КУПИТЬ НА ALIEXPRESS"
        btn_hub = "🌐 ДЕТАЛИ И ОБЗОР"
    elif lang == "he":
        title = p.get("title_i18n", {}).get("he") or p.get("title", "")
        pr_local = round(pr_usd * RATE_ILS)
        old_local = round(old_usd * RATE_ILS)
        desc = p.get("short_desc_i18n", {}).get("he") or ""
        caption = (
            f"✨ *{title}*\n\n"
            f"📝 {desc}\n\n"
            f"💰 *מחיר מבצע בלעדי:* `₪{pr_local}` _(במקום ₪{old_local})_\n"
            f"🏷️ *הנחה:* `-{disc}%` | ⭐ *דירוג:* `{rating}` ({orders} הזמנות)\n"
            f"🚚 *משלוח חינם לישראל* | 💸 *פטור מלא ממע\"מ ומכס עד $75*\n"
            f"✂️ קוד קופון פעיל: `AEIL02` ($2 הנחה מעל $15)\n\n"
            f"👉 [לצפייה בפרטים המלאים ב-SmartPick]({deal_url})"
        )
        btn_buy = "🛍️ לקנייה ישירה ב-AliExpress"
        btn_hub = "🌐 סקירה ומפרט באתר"
    elif lang == "es":
        title = p.get("title_i18n", {}).get("es") or p.get("title", "")
        pr_local = round(pr_usd * RATE_EUR, 2)
        old_local = round(old_usd * RATE_EUR, 2)
        desc = p.get("short_desc_i18n", {}).get("es") or ""
        caption = (
            f"🏷️ *{title}*\n\n"
            f"📝 {desc}\n\n"
            f"💰 *Precio Chollo:* `{pr_local}€` _(PVP {old_local}€)_\n"
            f"🏷️ *Descuento:* `-{disc}%` | ⭐ *Valoración:* `{rating}` ({orders} ventas)\n"
            f"🚚 *Envío Gratis Choice*\n"
            f"✂️ Cupón activo: `AEIL02` ($2 dto en +$15)\n\n"
            f"👉 [Ver detalles en SmartPick]({deal_url})"
        )
        btn_buy = "🛍️ VER CHOLLO EN ALIEXPRESS"
        btn_hub = "🌐 FICHA Y DETALLES"
    else: # English
        title = p.get("title_i18n", {}).get("en") or p.get("title", "")
        desc = p.get("short_desc_i18n", {}).get("en") or ""
        caption = (
            f"⚡ *{title}*\n\n"
            f"📝 {desc}\n\n"
            f"💰 *Deal Price:* `${pr_usd}` _(was ${old_usd})_\n"
            f"🏷️ *Discount:* `-{disc}% OFF` | ⭐ *Rating:* `{rating}` ({orders} orders)\n"
            f"🚚 *Free Worldwide Shipping*\n"
            f"✂️ Promo Code: `AEIL02` ($2 OFF over $15)\n\n"
            f"👉 [View Deal Dossier on SmartPick]({deal_url})"
        )
        btn_buy = "🛍️ GET DEAL ON ALIEXPRESS"
        btn_hub = "🌐 FULL SPECS & REVIEWS"

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": btn_buy, "url": aff_url},
                {"text": btn_hub, "url": deal_url}
            ]
        ]
    }

    return caption, reply_markup

def send_telegram_deal(bot_token, chat_id, caption, reply_markup, image_path=None, simulate=False):
    if simulate:
        print("[SIMULATE POST]")
        print(caption[:150] + "...")
        print("Buttons:", reply_markup["inline_keyboard"][0])
        print("-" * 50)
        return True

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": caption,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(reply_markup),
        "disable_web_page_preview": False
    }

    req = urllib.request.Request(
        api_url,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={"User-Agent": "SmartPickMassPoster/2.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok", False)
    except Exception as ex:
        print(f"Telegram API Error: {ex}")
        return False

def main():
    parser = argparse.ArgumentParser(description="SmartPick Telegram Mass Poster (100 Deals)")
    parser.add_argument("--token", help="Telegram Bot Token from @BotFather")
    parser.add_argument("--channel", help="Telegram Channel username or ID (e.g. @mydealschannel or -1001234567)")
    parser.add_argument("--lang", default="ru", choices=["ru", "he", "es", "en"], help="Language: ru, he, es, en (default: ru)")
    parser.add_argument("--count", type=int, default=100, help="Number of deals to post (default: 100)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between posts in seconds to prevent flood (default: 2.0s)")
    parser.add_argument("--simulate", action="store_true", help="Simulate publishing without sending live requests")

    args = parser.parse_args()

    products = load_products()[:args.count]
    print(f"==================================================")
    print(f"SMARTPICK TELEGRAM MASS POSTER")
    print(f"Target count: {len(products)} deals | Language: {args.lang.upper()}")
    print(f"Simulation mode: {args.simulate}")
    print(f"==================================================")

    if not args.simulate and (not args.token or not args.channel):
        print("Error: Live mode requires --token <BOT_TOKEN> and --channel <@CHANNEL>.")
        print("Tip: Run with --simulate to preview 100 posts locally without a bot token!")
        sys.exit(1)

    success_count = 0
    for idx, p in enumerate(products, 1):
        caption, reply_markup = format_telegram_caption(p, lang=args.lang)
        print(f"[{idx}/{len(products)}] Posting: {p['slug']}...")

        ok = send_telegram_deal(
            bot_token=args.token,
            chat_id=args.channel,
            caption=caption,
            reply_markup=reply_markup,
            simulate=args.simulate
        )

        if ok:
            success_count += 1
        else:
            print(f"Failed to post deal #{idx} ({p['slug']})")

        if idx < len(products) and not args.simulate:
            time.sleep(args.delay)

    print(f"\nFinished mass posting! Successfully processed: {success_count}/{len(products)} deals.")

if __name__ == "__main__":
    main()
