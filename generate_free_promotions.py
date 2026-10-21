# -*- coding: utf-8 -*-
"""
FREE PROMOTION & BROADCAST GENERATOR ACROSS 4 LANGUAGES:
1. Hebrew (HE) -> Telegram channels & WhatsApp deal broadcasts
2. Russian (RU) -> Telegram deal channels & VKontakte communities
3. Spanish (ES) -> Telegram Chollos channels & Chollometro forum style
4. English (EN) -> Reddit (r/Aliexpress, r/gadgets, r/EDC), Pinterest & Twitter/X threads
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
OUT_DIR = os.path.join(BASE_DIR, "broadcasts")
os.makedirs(OUT_DIR, exist_ok=True)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

products = db["products"]
dom = db.get("site_meta", {}).get("domain", "https://smartpick-deals.com").rstrip("/")
RATE_ILS = 3.7
RATE_EUR = 0.92
RATE_RUB = 96.0

# 1. HEBREW (WhatsApp & Telegram)
he_lines = [
    "=" * 60,
    "📢 ערוצי טלגרם וקבוצות וואטסאפ בישראל // פוסטים מוכנים להפצה חינמית",
    "=" * 60 + "\n"
]

for i, p in enumerate(products, 1):
    title = p.get("title_i18n", {}).get("he") or p.get("title", "")
    pr_ils = round(p["price_usd"] * RATE_ILS)
    old_ils = round((p.get("old_price_usd") or 0) * RATE_ILS)
    disc = p.get("discount_pct", 0)
    rating = p.get("rating", 4.9)
    aff_link = f"{p['affiliate_url']}?aff_sub=tg_he&aff_sub2=free_deal_{p['id']}"
    hub_link = f"{dom}/deals/{p['slug']}.html?utm_source=telegram&utm_medium=channel_he"

    hl_text = "\n".join(f"  🔹 {h}" for h in (p.get("highlights") or [])[:3])

    post = f"""🔥 דיל שווה #{i} // {title}
⭐ דירוג קונים מאומת: {rating} מתוך 5.0
💵 מחיר מבצע: ₪{pr_ils} בלבד! {f'(במקום ₪{old_ils} | {disc}% הנחה)' if old_ils > pr_ils else ''}
🚚 משלוח: חינם לישראל (פטור מלא ממע"מ ומכס עד $75!)

{hl_text}

🛒 קישור ישיר לרכישה ב-AliExpress:
👉 {aff_link}

📑 עמוד המפרט המלא והסקירה:
👉 {hub_link}
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    he_lines.append(post)

with open(os.path.join(OUT_DIR, "free_promo_telegram_he.txt"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(he_lines))


# 2. RUSSIAN (Telegram & VK & Forums)
ru_lines = [
    "=" * 60,
    "📢 TELEGRAM КАНАЛЫ И VK ГРУППЫ // ГОТОВЫЕ ПОСТЫ ДЛЯ БЕСПЛАТНОГО ТРАФИКА",
    "=" * 60 + "\n"
]

for i, p in enumerate(products, 1):
    title = p.get("title_i18n", {}).get("ru") or p.get("title_i18n", {}).get("en") or p.get("title", "")
    pr_usd = p["price_usd"]
    pr_rub = round(pr_usd * RATE_RUB)
    pr_ils = round(pr_usd * RATE_ILS)
    disc = p.get("discount_pct", 0)
    rating = p.get("rating", 4.9)
    aff_link = f"{p['affiliate_url']}?aff_sub=tg_ru&aff_sub2=free_deal_{p['id']}"
    hub_link = f"{dom}/deals/{p['slug']}.html?utm_source=telegram&utm_medium=channel_ru"

    post = f"""⚡ ТОП НАХОДКА #{i} // {title}
⭐ Рейтинг продавца: {rating} / 5.0 (Проверенное качество)
💵 Цена со скидкой: ${pr_usd:.2f} (~{pr_rub} ₽ / ₪{pr_ils}) {f'[-{disc}%]' if disc else ''}
🚚 Доставка: Бесплатно! (Без таможенных пошлин до $75)

🛒 Заказать на AliExpress:
👉 {aff_link}

🔎 Подробный обзор и характеристики:
👉 {hub_link}
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    ru_lines.append(post)

with open(os.path.join(OUT_DIR, "free_promo_telegram_ru.txt"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(ru_lines))


# 3. SPANISH (Telegram Chollos & Chollometro)
es_lines = [
    "=" * 60,
    "📢 CANALES TELEGRAM CHOLLOS Y COMUNIDADES EN ESPAÑA // POSTS LISTOS",
    "=" * 60 + "\n"
]

for i, p in enumerate(products, 1):
    title = p.get("title_i18n", {}).get("es") or p.get("title_i18n", {}).get("en") or p.get("title", "")
    pr_eur = p["price_usd"] * RATE_EUR
    old_eur = (p.get("old_price_usd") or 0) * RATE_EUR
    disc = p.get("discount_pct", 0)
    rating = p.get("rating", 4.9)
    aff_link = f"{p['affiliate_url']}?aff_sub=tg_es&aff_sub2=free_chollo_{p['id']}"
    hub_link = f"{dom}/deals/{p['slug']}.html?utm_source=telegram&utm_medium=channel_es"

    post = f"""🔥 CHOLLAZO #{i} // {title}
⭐ Valoración: {rating}/5.0 (Compradores verificados)
💵 Precio Mínimo: {pr_eur:.2f}€ {f'(Antes {old_eur:.2f}€ | -{disc}% DTO)' if old_eur > pr_eur else ''}
🚚 Envío: Gratis a España (Sin aduanas)

🛒 Ver oferta en AliExpress:
👉 {aff_link}

📑 Ficha técnica y detalles:
👉 {hub_link}
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    es_lines.append(post)

with open(os.path.join(OUT_DIR, "free_promo_telegram_es.txt"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(es_lines))


# 4. ENGLISH (Reddit r/gadgets & r/BuyItForLife / Pinterest / X)
en_lines = [
    "=" * 60,
    "📢 GLOBAL ENGLISH PROMOTIONAL COPIES (REDDIT, PINTEREST, X THREADS)",
    "=" * 60 + "\n"
]

for i, p in enumerate(products, 1):
    title = p.get("title_i18n", {}).get("en") or p.get("title", "")
    pr_usd = p["price_usd"]
    old_usd = p.get("old_price_usd") or 0
    disc = p.get("discount_pct", 0)
    rating = p.get("rating", 4.9)
    aff_link = f"{p['affiliate_url']}?aff_sub=social_en&aff_sub2=deal_{p['id']}"
    hub_link = f"{dom}/deals/{p['slug']}.html?utm_source=reddit&utm_medium=post"

    post = f"""💡 Viral Smart Gadget #{i}: {title}
⭐ 4.8+ Rating ({p.get('orders_count', 1000)}+ verified orders)
💵 Sale Price: ${pr_usd:.2f} {f'(was ${old_usd:.2f} | {disc}% OFF)' if old_usd > pr_usd else ''}
🚚 Free Worldwide Shipping Available

Why it's awesome:
- Compact, durable, problem-solving daily utility
- Direct manufacturer price without brand markup

👉 Check AliExpress Deal: {aff_link}
📑 Full specs & specs review: {hub_link}
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    en_lines.append(post)

with open(os.path.join(OUT_DIR, "free_promo_reddit_pinterest_en.txt"), "w", encoding="utf-8") as f:
    f.write("\n\n".join(en_lines))

print(f"[Promotions Generator] Successfully generated 4 language packages in {OUT_DIR}:")
print(f" - free_promo_telegram_he.txt ({len(products)} deals)")
print(f" - free_promo_telegram_ru.txt ({len(products)} deals)")
print(f" - free_promo_telegram_es.txt ({len(products)} deals)")
print(f" - free_promo_reddit_pinterest_en.txt ({len(products)} deals)")
