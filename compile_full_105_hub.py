# -*- coding: utf-8 -*-
"""
COMPILER SCRIPT: Merges base products with Expansion Part 1 & 2 into data/products.json
Total target: 105 products.
"""
import os
import json
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
IMG_DIR = os.path.join(BASE_DIR, "assets", "img")
os.makedirs(IMG_DIR, exist_ok=True)

from catalog_expansion_batch import EXPANSION_PRODUCTS
from catalog_expansion_part2 import EXPANSION_PART2

# Ensure image exists or generate clean preview
def ensure_img(filename, label, cat, icon="⚡"):
    path = os.path.join(IMG_DIR, filename)
    if not os.path.exists(path):
        img = Image.new("RGB", (600, 600), color=(14, 18, 30))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(20, 20), (580, 580)], radius=20, fill=(20, 26, 42), outline=(38, 52, 82), width=2)
        draw.rounded_rectangle([(40, 40), (560, 560)], radius=16, fill=(13, 17, 28))
        draw.text((60, 65), f"SMARTPICK // {cat.upper()}", fill=(0, 210, 255))
        draw.text((540, 65), "VERIFIED ★ 4.9", fill=(255, 198, 0), anchor="ra")
        draw.rounded_rectangle([(90, 130), (510, 440)], radius=16, fill=(24, 32, 52), outline=(0, 210, 255), width=1)
        draw.text((300, 240), icon, fill=(255, 255, 255), anchor="mm")
        draw.text((300, 340), label[:28], fill=(255, 255, 255), anchor="mm")
        draw.rounded_rectangle([(180, 485), (420, 525)], radius=10, fill=(0, 210, 255))
        draw.text((300, 505), "FREE SHIPPING // $75 DUTY-FREE", fill=(10, 14, 26), anchor="mm")
        img.save(path, "JPEG", quality=92)
    return f"assets/img/{filename}"

# 1. Load existing
with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

base_prods = db.get("products", [])
print(f"Loaded {len(base_prods)} base products.")

# Normalize base products
for p in base_prods:
    t = p.get("title_i18n", {})
    he_t = t.get("he") or p.get("title", "")
    en_t = t.get("en") or he_t
    t["en"] = en_t
    t["he"] = he_t
    t["es"] = t.get("es") or en_t
    t["ru"] = t.get("ru") or en_t
    p["title_i18n"] = t

    d = p.get("short_desc_i18n", {})
    he_d = d.get("he") or p.get("short_desc", "")
    en_d = d.get("en") or he_d
    d["en"] = en_d
    d["he"] = he_d
    d["es"] = d.get("es") or en_d
    d["ru"] = d.get("ru") or en_d
    p["short_desc_i18n"] = d

    if p["id"] in ["real-101", "real-109", "real-113", "real-121"]:
        p["category"] = "tech"

# 2. Convert and merge new products
all_new = EXPANSION_PRODUCTS + EXPANSION_PART2
print(f"Preparing {len(all_new)} expansion products...")

converted_new = []
for item in all_new:
    t_dict = item.get("title_i18n") or item.get("title") or {}
    if isinstance(t_dict, str):
        t_dict = {"en": t_dict, "he": t_dict, "es": t_dict, "ru": t_dict}
    d_dict = item.get("short_desc_i18n") or item.get("desc") or item.get("short_desc") or {}
    if isinstance(d_dict, str):
        d_dict = {"en": d_dict, "he": d_dict, "es": d_dict, "ru": d_dict}

    img_path = ensure_img(item.get("img") or item.get("img_file"), t_dict.get("en", "Gadget"), item["category"], item.get("icon", "⚡"))
    p_obj = {
        "id": item["id"],
        "slug": item["slug"],
        "category": item["category"],
        "badge": "⚡ POPULAR",
        "badge_i18n": {
            "en": "🔥 POPULAR",
            "he": "🔥 נבחר הקונים",
            "es": "🔥 POPULAR",
            "ru": "🔥 ХИТ ПРОДАЖ"
        },
        "title": t_dict.get("en", ""),
        "title_i18n": t_dict,
        "short_desc": d_dict.get("en", ""),
        "short_desc_i18n": d_dict,
        "price_usd": item["price_usd"],
        "old_price_usd": item["old_price_usd"],
        "discount_pct": item["discount_pct"],
        "rating": item["rating"],
        "reviews_count": item["reviews_count"],
        "orders_count": item["orders_count"],
        "affiliate_url": item["affiliate_url"],
        "image": img_path,
        "gallery": [img_path],
        "highlights": item["highlights"],
        "specs": item["specs"]
    }
    converted_new.append(p_obj)

# 3. Combine
full_products = base_prods + converted_new

# Categories with all 4 languages
categories = [
    {
        "id": "all",
        "icon": "⚡",
        "name": "כל המציאות",
        "name_i18n": {
            "en": "All Gadgets",
            "he": "כל המציאות",
            "es": "Todos los Chollos",
            "ru": "Все находки"
        }
    },
    {
        "id": "gadgets",
        "icon": "🚀",
        "name": "גאדג׳טים וכיס",
        "name_i18n": {
            "en": "EDC & Pocket Tech",
            "he": "גאדג׳טים וכיס",
            "es": "Gadgets y EDC",
            "ru": "Карманные гаджеты и EDC"
        }
    },
    {
        "id": "auto",
        "icon": "🚗",
        "name": "שדרוגים לרכב",
        "name_i18n": {
            "en": "Smart Car Tech",
            "he": "שדרוגים לרכב",
            "es": "Accesorios Coche",
            "ru": "Умные автотовары"
        }
    },
    {
        "id": "smarthome",
        "icon": "🏠",
        "name": "בית ומטבח",
        "name_i18n": {
            "en": "Smart Home & Kitchen",
            "he": "בית ומטבח",
            "es": "Hogar y Cocina",
            "ru": "Дом, кухня и уборка"
        }
    },
    {
        "id": "tech",
        "icon": "🎧",
        "name": "אודיו, מטענים וציוד",
        "name_i18n": {
            "en": "Audio & Fast GaN",
            "he": "אודיו, מטענים וציוד",
            "es": "Sonido y Carga",
            "ru": "Аудио, GaN и сетапы"
        }
    },
    {
        "id": "pets",
        "icon": "🐾",
        "name": "חיות מחמד",
        "name_i18n": {
            "en": "Clever Pet Tech",
            "he": "חיות מחמד",
            "es": "Mascotas Listas",
            "ru": "Товары для питомцев"
        }
    },
    {
        "id": "tools",
        "icon": "🔧",
        "name": "כלי עבודה ותיקונים",
        "name_i18n": {
            "en": "Precision Tools",
            "he": "כלי עבודה ותיקונים",
            "es": "Herramientas",
            "ru": "Точный инструмент"
        }
    },
    {
        "id": "under10",
        "icon": "💰",
        "name": "מציאות עד ₪35",
        "name_i18n": {
            "en": "Under $10 Bargains",
            "he": "מציאות עד ₪35",
            "es": "Menos de 10$",
            "ru": "Находки до $10"
        }
    }
]

db["products"] = full_products
db["categories"] = categories
db["site_meta"] = {
    "title": "SmartPick // Curated Smart Gadgets & Trending Life Hacks",
    "description": "Discover problem-solving smart gadgets, auto upgrades, home tech and verified AliExpress bargains with free shipping and duty-free under $75.",
    "domain": "https://smartpick-deals.com",
    "supported_languages": ["en", "he", "es", "ru"],
    "supported_currencies": ["USD", "ILS", "EUR", "RUB"]
}

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"\n[SUCCESS] Successfully compiled {len(full_products)} products into {DATA_FILE}!")
