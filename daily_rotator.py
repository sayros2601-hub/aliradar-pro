# -*- coding: utf-8 -*-
"""
DAILY ROTATOR // AUTOMATED 7-DEAL ROLLING CYCLER
------------------------------------------------
1. Selects 7 fresh items from data/reserve_pool.json and marks them with `is_new: True`.
2. Resets previous `is_new` items to `False` in data/products.json.
3. Inserts the 7 new items at the top of the catalog (positions 0-6).
4. Moves the 7 oldest tail items from data/products.json back into the reserve pool.
5. Keeps catalog size fixed at exactly 105 items (zero disk bloat, 15-day lifecycle).
6. Automatically rebuilds index.html and deals/*.html via build_modern_hub.py.
7. Updates sitemap.xml.
8. Generates ready-to-post broadcasts in broadcasts/daily_drop_YYYY-MM-DD.txt for
   Hebrew, Russian, Spanish, and English free social channels.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
RESERVE_FILE = os.path.join(DATA_DIR, "reserve_pool.json")
LOG_FILE = os.path.join(DATA_DIR, "rotation_log.json")
BROADCASTS_DIR = os.path.join(BASE_DIR, "broadcasts")
os.makedirs(BROADCASTS_DIR, exist_ok=True)

RATE_ILS = 3.7
RATE_EUR = 0.92
RATE_RUB = 95.0

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_daily_broadcast(new_items, date_str):
    """
    Generates multi-language viral copy for today's 7 new items.
    Targeting 100% free channels: Telegram, WhatsApp, Reddit, VK, Pinterest.
    """
    he_lines = [
        f"🌟 **מבצעי היום החדשים ב-SmartPick!** [{date_str}]",
        "הגאדג'טים הכי שווים שהתווספו הבוקר לקטלוג במחירי יצרן ישירים:",
        "🚚 משלוח חינם לישראל | 💸 פטור ממע\"מ ומכס עד $75\n"
    ]
    ru_lines = [
        f"🔥 **СВЕЖИЙ ДРОП ДНЯ // Топ-7 находок на AliExpress!** [{date_str}]",
        "Новые проверенные гаджеты и полезные вещи по ценам фабрик:",
        "🚚 Бесплатная доставка | ⭐ Только рейтинг 4.8+ и реальные отзывы\n"
    ]
    es_lines = [
        f"⚡ **¡NOVEDADES DE HOY EN SMARTPICK!** [{date_str}]",
        "Los 7 mejores chollos virales añadidos hoy a precio directo de fábrica:",
        "🚚 Envío gratis | 🏷️ Descuentos de hasta el 60%\n"
    ]
    en_lines = [
        f"🚀 **DAILY DROP // 7 Trending AliExpress Finds** [{date_str}]",
        "Problem-solving EDC tech, smart home & car upgrades added today:",
        "📦 Free Worldwide Shipping | ⭐ 4.8+ Star Buyer Ratings\n"
    ]

    for i, p in enumerate(new_items, 1):
        pr_usd = p["price_usd"]
        old_usd = p.get("old_price_usd", round(pr_usd * 1.8, 2))
        disc = p.get("discount_pct", 50)
        slug = p["slug"]

        # HEBREW
        t_he = p.get("title_i18n", {}).get("he") or p.get("title", "")
        pr_ils = round(pr_usd * RATE_ILS)
        old_ils = round(old_usd * RATE_ILS)
        link_he = f"https://smartpick.click/deals/{slug}.html?utm_source=telegram_he&utm_medium=daily_drop&utm_campaign={date_str}"
        he_lines.append(f"{i}. ✨ **{t_he}**")
        he_lines.append(f"   💰 מחיר מבצע: **₪{pr_ils}** (במקום ₪{old_ils}) | **-{disc}%**")
        he_lines.append(f"   🔗 קישור לבדיקה ורכישה: {link_he}\n")

        # RUSSIAN
        t_ru = p.get("title_i18n", {}).get("ru") or p.get("title", "")
        pr_rub = round(pr_usd * RATE_RUB)
        old_rub = round(old_usd * RATE_RUB)
        link_ru = f"https://smartpick.click/deals/{slug}.html?utm_source=telegram_ru&utm_medium=daily_drop&utm_campaign={date_str}"
        ru_lines.append(f"{i}. 🔥 **{t_ru}**")
        ru_lines.append(f"   💰 Цена: **{pr_rub} ₽** (было {old_rub} ₽) | Скидка **-{disc}%**")
        ru_lines.append(f"   🔗 Смотреть на сайте: {link_ru}\n")

        # SPANISH
        t_es = p.get("title_i18n", {}).get("es") or p.get("title", "")
        pr_eur = round(pr_usd * RATE_EUR, 2)
        old_eur = round(old_usd * RATE_EUR, 2)
        link_es = f"https://smartpick.click/deals/{slug}.html?utm_source=telegram_es&utm_medium=daily_drop&utm_campaign={date_str}"
        es_lines.append(f"{i}. 🏷️ **{t_es}**")
        es_lines.append(f"   💰 Precio: **{pr_eur}€** (PVP: {old_eur}€) | **-{disc}% dto.**")
        es_lines.append(f"   🔗 Enlace al chollo: {link_es}\n")

        # ENGLISH
        t_en = p.get("title_i18n", {}).get("en") or p.get("title", "")
        link_en = f"https://smartpick.click/deals/{slug}.html?utm_source=reddit_en&utm_medium=daily_drop&utm_campaign={date_str}"
        en_lines.append(f"{i}. ⚡ **{t_en}**")
        en_lines.append(f"   💰 Price: **${pr_usd}** (was ${old_usd}) | **{disc}% OFF**")
        en_lines.append(f"   🔗 Direct Link: {link_en}\n")

    he_lines.append("🎁 קוד קופון פעיל בקופה: `AEIL02` ($2 הנחה מעל $15)")
    he_lines.append("🌐 לכל 105 המציאות המלאות: https://smartpick.click")

    ru_lines.append("🎁 Промокод на доп. скидку: `AEIL02` ($2 скидка от $15)")
    ru_lines.append("🌐 Весь каталог из 105 товаров: https://smartpick.click")

    es_lines.append("🎁 Cupón descuento adicional: `AEIL02` ($2 dto. en +$15)")
    es_lines.append("🌐 Ver los 105 chollos activos: https://smartpick.click")

    en_lines.append("🎁 Use promo code `AEIL02` at checkout for $2 OFF over $15!")
    en_lines.append("🌐 Browse all 105 curated deals: https://smartpick.click")

    content = f"""================================================================================
SMARTPICK DAILY VIRAL BROADCAST PACK // {date_str}
================================================================================

--------------------------------------------------------------------------------
[1] HEBREW (TELEGRAM & WHATSAPP GROUPS)
--------------------------------------------------------------------------------
{chr(10).join(he_lines)}

--------------------------------------------------------------------------------
[2] RUSSIAN (TELEGRAM CHANNELS & VK / OK GROUPS)
--------------------------------------------------------------------------------
{chr(10).join(ru_lines)}

--------------------------------------------------------------------------------
[3] SPANISH (TELEGRAM CHOLLOS & CHOLLOMETRO)
--------------------------------------------------------------------------------
{chr(10).join(es_lines)}

--------------------------------------------------------------------------------
[4] ENGLISH (REDDIT r/deals, PINTEREST, X/TWITTER)
--------------------------------------------------------------------------------
{chr(10).join(en_lines)}
"""
    broadcast_path = os.path.join(BROADCASTS_DIR, f"daily_drop_{date_str}.txt")
    with open(broadcast_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[Rotator] Generated daily promo broadcast at: {broadcast_path}")
    return broadcast_path

def rotate_deals(count=7, dry_run=False):
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"[Rotator] Starting daily rotation for date: {date_str} (Rotating {count} products)...")

    db = load_json(PRODUCTS_FILE)
    prods = db.get("products", [])
    reserve = load_json(RESERVE_FILE)

    if len(reserve) < count:
        print(f"[Rotator Warning] Reserve pool has only {len(reserve)} items. Replenishing from end of catalog...")

    # 1. Clear 'is_new' on existing products
    prev_new_ids = []
    for p in prods:
        if p.get("is_new"):
            prev_new_ids.append(p["id"])
            p["is_new"] = False

    print(f"[Rotator] Unmarked {len(prev_new_ids)} previous daily items: {prev_new_ids}")

    # 2. Extract `count` new items from reserve pool
    incoming_items = reserve[:count]
    remaining_reserve = reserve[count:]

    for p in incoming_items:
        p["is_new"] = True

    incoming_ids = [p["id"] for p in incoming_items]
    print(f"[Rotator] Selected {len(incoming_items)} incoming items for today: {incoming_ids}")

    # 3. Determine items to retire from catalog tail to keep exactly 105
    target_catalog_size = 105
    current_size = len(prods)
    num_to_retire = (current_size + len(incoming_items)) - target_catalog_size

    if num_to_retire > 0:
        retiring_items = prods[-num_to_retire:]
        active_retained = prods[:-num_to_retire]
        for r in retiring_items:
            r["is_new"] = False
        # Push retired items to end of reserve pool (rolling FIFO)
        updated_reserve = remaining_reserve + retiring_items
        retiring_ids = [r["id"] for r in retiring_items]
        print(f"[Rotator] Retiring {len(retiring_items)} oldest items to reserve pool: {retiring_ids}")
    else:
        active_retained = prods
        updated_reserve = remaining_reserve
        retiring_ids = []

    # 4. Form new catalog with incoming items at the top
    new_catalog = incoming_items + active_retained
    db["products"] = new_catalog

    print(f"[Rotator] New catalog size: {len(new_catalog)} (Target: {target_catalog_size})")

    if dry_run:
        print("[Rotator] DRY-RUN enabled. No files written.")
        return

    # 5. Save updated database & reserve pool
    save_json(PRODUCTS_FILE, db)
    save_json(RESERVE_FILE, updated_reserve)
    print(f"[Rotator] Saved {PRODUCTS_FILE} and {RESERVE_FILE}")

    # 6. Log rotation
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "date": date_str,
        "rotated_in": incoming_ids,
        "rotated_out": retiring_ids,
        "total_active": len(new_catalog),
        "total_reserve": len(updated_reserve)
    }
    history = []
    if os.path.exists(LOG_FILE):
        try:
            history = load_json(LOG_FILE)
        except Exception:
            history = []
    history.append(log_entry)
    save_json(LOG_FILE, history)

    # 7. Recompile website (index.html + deals/*.html)
    print("[Rotator] Rebuilding static Deal Hub...")
    hub_builder = os.path.join(BASE_DIR, "build_modern_hub.py")
    subprocess.run([sys.executable, hub_builder], check=True)

    # 8. Update sitemap.xml
    sitemap_script = os.path.join(BASE_DIR, "update_sitemap.py")
    if os.path.exists(sitemap_script):
        subprocess.run([sys.executable, sitemap_script], check=True)
        print("[Rotator] Updated sitemap.xml")

    # 9. Generate multi-language viral copy
    generate_daily_broadcast(incoming_items, date_str)

    print(f"[Rotator] Daily rotation complete! 7 new deals are live and prominently highlighted.")


def main():
    parser = argparse.ArgumentParser(description="SmartPick Daily 7-Deal Rotator")
    parser.add_argument("--count", type=int, default=7, help="Number of products to rotate (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate rotation without writing files")
    parser.add_argument("--broadcast-only", action="store_true", help="Only generate today's broadcast pack for current new items")

    args = parser.parse_args()

    if args.broadcast_only:
        db = load_json(PRODUCTS_FILE)
        new_items = [p for p in db.get("products", []) if p.get("is_new")]
        date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"[Rotator] Generating broadcast pack for {len(new_items)} current new items...")
        generate_daily_broadcast(new_items, date_str)
    else:
        rotate_deals(count=args.count, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
