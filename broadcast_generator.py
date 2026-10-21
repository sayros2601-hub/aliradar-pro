"""
BROADCAST & AD CREATIVES GENERATOR
Generates ready-to-use promotional posts and advertising copies for:
1. Telegram Channels & Groups (Hebrew & Russian)
2. WhatsApp Broadcast Channels (Hebrew)
3. Meta Ads (Facebook & Instagram Feed/Stories) Ad Copy Sets
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
OUT_DIR = os.path.join(BASE_DIR, "broadcasts")
RATE_ILS = 3.7


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_telegram_he(products, domain):
    lines = []
    lines.append("=" * 60)
    lines.append("📢 TELEGRAM BROADCAST FEED // HEBREW (עברית)")
    lines.append("=" * 60 + "\n")

    for i, p in enumerate(products, 1):
        title = p.get("title_i18n", {}).get("he") or p.get("title", "")
        pr_ils = round(p["price_usd"] * RATE_ILS)
        old_ils = round((p.get("old_price_usd") or 0) * RATE_ILS)
        disc = p.get("discount_pct", 0)
        rating = p.get("rating", "4.8")
        aff_url = f"{p['affiliate_url']}?aff_sub=tg_he&aff_sub2=deal_{p['id']}"
        hub_url = f"{domain}/deals/{p['slug']}.html?utm_source=telegram&utm_medium=channel&utm_campaign=he_daily"

        highlights = p.get("highlights", [])
        hl_txt = "\n".join(f"  🔹 {h}" for h in highlights[:3]) if highlights else ""

        post = f"""🔥 דיל #{i} // {title}
⭐ דירוג קונים מאומת: {rating} מתוך 5.0
💵 מחיר מבצע: ₪{pr_ils} בלבד! {f'(במקום ₪{old_ils} | {disc}% הנחה)' if old_ils > pr_ils else ''}
🚚 משלוח: חינם לישראל (פטור מלא ממכס ומע"מ עד $75!)

{hl_txt}

🔗 קישור ישיר לרכישה ב-AliExpress:
👉 {aff_url}

📑 עמוד המפרט המלא והסקירה:
👉 {hub_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        lines.append(post)
    return "\n\n".join(lines)


def generate_telegram_ru(products, domain):
    lines = []
    lines.append("=" * 60)
    lines.append("📢 TELEGRAM BROADCAST FEED // RUSSIAN (РУССКИЙ)")
    lines.append("=" * 60 + "\n")

    for i, p in enumerate(products, 1):
        title = p.get("title_i18n", {}).get("ru") or p.get("title_i18n", {}).get("en") or p.get("title", "")
        pr_usd = p["price_usd"]
        pr_ils = round(pr_usd * RATE_ILS)
        disc = p.get("discount_pct", 0)
        rating = p.get("rating", "4.8")
        aff_url = f"{p['affiliate_url']}?aff_sub=tg_ru&aff_sub2=deal_{p['id']}"
        hub_url = f"{domain}/deals/{p['slug']}.html?utm_source=telegram&utm_medium=channel_ru&utm_campaign=ru_daily"

        post = f"""⚡ НАХОДКА #{i} // {title}
⭐ Рейтинг качества: {rating}/5.0 (Проверенный продавец)
💵 Цена со скидкой: ${pr_usd:.2f} (~₪{pr_ils}) {f'[-{disc}% OFF]' if disc else ''}
🚚 Доставка: Бесплатно! Без пошлин до $75

🛒 Заказать на AliExpress:
👉 {aff_url}

🔎 Полный обзор и характеристики:
👉 {hub_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        lines.append(post)
    return "\n\n".join(lines)


def generate_meta_ads(products, domain):
    ads = []
    # General Matrix Ad
    ads.append({
        "campaign_type": "Matrix Hub Traffic / Catalog Sales",
        "target_audience": "Israel, 22-55, Tech & Gadgets, Online Shopping, AliExpress enthusiasts",
        "primary_text": "גאדג'טים ופטנטים מהעתיד שלא הכרתם במחירי השקה מטורפים! ⚡\nכל הפריטים מתחת ל-₪300, עם משלוח חינם לישראל ופטור מלא ממכס ומע\"מ עד $75.\nסריקת AI בלייב של המציאות החזקות ביותר ברשת. גלו את המטריקס עכשיו!",
        "headline": "SmartPick Matrix 2077 | מציאות וגאדג'טים חכמים",
        "description": "🚚 משלוח חינם • ⭐ דירוג 4.8+ • 💸 פטור ממע\"מ",
        "destination_url": f"{domain}/index.html?utm_source=facebook&utm_medium=cpc&utm_campaign=matrix_launch",
        "call_to_action": "Shop Now / קניה עכשיו"
    })

    # Individual Product Creatives for Top 8 Gems
    for p in products[:8]:
        title = p.get("title_i18n", {}).get("he") or p.get("title", "")
        pr_ils = round(p["price_usd"] * RATE_ILS)
        disc = p.get("discount_pct", 0)
        ads.append({
            "product_id": p["id"],
            "campaign_type": f"Single Product Conversion - {p['id']}",
            "primary_text": f"מצאנו את הלהיט הבא: {title} במחיר שאי אפשר להתחרות בו!\nרק ₪{pr_ils} עם משלוח חינם עד הבית. דירוג קונים מאומת {p.get('rating')}/5.0.\nכמות מוגבלת במחיר ההשקה, אל תפספסו!",
            "headline": f"{title[:45]}... | ₪{pr_ils}",
            "description": f"🔥 {disc}% הנחה • משלוח חינם לישראל",
            "destination_url": f"{domain}/deals/{p['slug']}.html?utm_source=facebook&utm_medium=cpc&utm_campaign=prod_{p['id']}",
            "call_to_action": "Get Offer / קבלת ההצעה"
        })

    return ads


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    db = load_data()
    products = db["products"]
    domain = db.get("site_meta", {}).get("domain", "https://smartpick.co.il").rstrip("/")

    tg_he = generate_telegram_he(products, domain)
    with open(os.path.join(OUT_DIR, "broadcast_telegram_he.txt"), "w", encoding="utf-8") as f:
        f.write(tg_he)

    tg_ru = generate_telegram_ru(products, domain)
    with open(os.path.join(OUT_DIR, "broadcast_telegram_ru.txt"), "w", encoding="utf-8") as f:
        f.write(tg_ru)

    meta_ads = generate_meta_ads(products, domain)
    with open(os.path.join(OUT_DIR, "ad_creatives_facebook.json"), "w", encoding="utf-8") as f:
        json.dump(meta_ads, f, ensure_ascii=False, indent=2)

    print(f"[Broadcast Generator] Successfully generated:")
    print(f" - {os.path.join(OUT_DIR, 'broadcast_telegram_he.txt')}")
    print(f" - {os.path.join(OUT_DIR, 'broadcast_telegram_ru.txt')}")
    print(f" - {os.path.join(OUT_DIR, 'ad_creatives_facebook.json')}")


if __name__ == "__main__":
    main()
