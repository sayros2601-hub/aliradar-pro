# -*- coding: utf-8 -*-
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")

# Load existing 36 products
with open(DATA_FILE, "r", encoding="utf-8") as f:
    existing_db = json.load(f)

existing_products = existing_db.get("products", [])
print(f"Loaded {len(existing_products)} existing products.")

# Update existing products with missing ES or RU translations if any
for p in existing_products:
    # Ensure title_i18n has all 4 languages
    t = p.get("title_i18n", {})
    he_title = t.get("he") or p.get("title", "")
    en_title = t.get("en") or he_title
    if "es" not in t or not t["es"]:
        t["es"] = en_title
    if "ru" not in t or not t["ru"]:
        t["ru"] = en_title
    p["title_i18n"] = t

    # Ensure short_desc_i18n
    d = p.get("short_desc_i18n", {})
    he_desc = d.get("he") or p.get("short_desc", "")
    en_desc = d.get("en") or he_desc
    if "es" not in d or not d["es"]:
        d["es"] = en_desc
    if "ru" not in d or not d["ru"]:
        d["ru"] = en_desc
    p["short_desc_i18n"] = d

    # Move chargers and audio to 'tech' category
    if p["id"] in ["real-101", "real-109", "real-113", "real-121"]:
        p["category"] = "tech"

print("Enriched existing products.")
