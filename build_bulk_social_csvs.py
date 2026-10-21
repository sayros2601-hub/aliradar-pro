# -*- coding: utf-8 -*-
"""
Generates Bulk CSV files for social media autoposters (Buffer, Metricool, Publer, Hootsuite, dlvr.it).
Accepts 100 posts at once with scheduled times, viral text, clean links, and images.
"""
import os
import json
import csv
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
BROADCASTS_DIR = os.path.join(BASE_DIR, "broadcasts")
os.makedirs(BROADCASTS_DIR, exist_ok=True)

RATE_ILS = 3.7
RATE_EUR = 0.92
RATE_RUB = 95.0

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    prods = db.get("products", [])[:100]
    dom = db.get("site_meta", {}).get("domain", "https://dealvault.pages.dev").rstrip("/")

    # Generate 4 language CSVs
    langs = [
        ("ru", "bulk_100_buffer_ru.csv"),
        ("he", "bulk_100_buffer_he.csv"),
        ("es", "bulk_100_buffer_es.csv"),
        ("en", "bulk_100_buffer_en.csv")
    ]

    base_time = datetime.now() + timedelta(minutes=10)

    for lang_code, filename in langs:
        filepath = os.path.join(BROADCASTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8-sig", newline="") as csvfile:
            writer = csv.writer(csvfile)
            # Buffer / Metricool format: Date, Text, Link, ImageURL
            writer.writerow(["Date", "Text", "Link", "ImageURL"])

            for idx, p in enumerate(prods):
                # Spread posts every 30 minutes
                post_time = (base_time + timedelta(minutes=idx * 30)).strftime("%Y-%m-%d %H:%M")
                pr_usd = p["price_usd"]
                old_usd = p.get("old_price_usd", round(pr_usd * 1.8, 2))
                disc = p.get("discount_pct", 50)
                slug = p["slug"]
                deal_url = f"{dom}/deals/{slug}.html?utm_source=social_bulk&utm_medium={lang_code}&utm_campaign=batch100"
                img_url = f"{dom}/{p['image']}"

                if lang_code == "ru":
                    t = p.get("title_i18n", {}).get("ru") or p.get("title", "")
                    pr_local = round(pr_usd * RATE_RUB)
                    old_local = round(old_usd * RATE_RUB)
                    desc = p.get("short_desc_i18n", {}).get("ru") or ""
                    post_text = f"🔥 {t}\n💰 Цена: {pr_local} ₽ (вместо {old_local} ₽) - Скидка -{disc}%\n🚚 Бесплатная доставка | Рейтинг ★ 4.8+\n✂️ Промокод: AEIL02\n\n👉 {deal_url}"
                elif lang_code == "he":
                    t = p.get("title_i18n", {}).get("he") or p.get("title", "")
                    pr_local = round(pr_usd * RATE_ILS)
                    old_local = round(old_usd * RATE_ILS)
                    post_text = f"✨ {t}\n💰 מחיר מבצע: ₪{pr_local} (במקום ₪{old_local}) | הנחה -{disc}%\n🚚 משלוח חינם | פטור ממע\"מ עד $75\n✂️ קוד קופון: AEIL02\n\n👉 {deal_url}"
                elif lang_code == "es":
                    t = p.get("title_i18n", {}).get("es") or p.get("title", "")
                    pr_local = round(pr_usd * RATE_EUR, 2)
                    old_local = round(old_usd * RATE_EUR, 2)
                    post_text = f"🏷️ {t}\n💰 Chollo: {pr_local}€ (PVP {old_local}€) | -{disc}% Dto\n🚚 Envío Gratis | Valoración ★ 4.8+\n✂️ Cupón: AEIL02\n\n👉 {deal_url}"
                else:
                    t = p.get("title_i18n", {}).get("en") or p.get("title", "")
                    post_text = f"⚡ {t}\n💰 Deal Price: ${pr_usd} (was ${old_usd}) | {disc}% OFF\n🚚 Free Worldwide Shipping | ★ 4.8+ Verified\n✂️ Promo Code: AEIL02\n\n👉 {deal_url}"

                writer.writerow([post_time, post_text, deal_url, img_url])

        print(f"[Bulk CSV] Generated {filepath} (100 scheduled posts)")

if __name__ == "__main__":
    main()
