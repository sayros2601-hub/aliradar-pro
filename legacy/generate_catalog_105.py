# -*- coding: utf-8 -*-
import os
import json
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
IMG_DIR = os.path.join(BASE_DIR, "assets", "img")
os.makedirs(IMG_DIR, exist_ok=True)

# Helper to generate professional gadget visual if local file doesn't exist
def ensure_image(filename, title_short, cat, icon="⚡"):
    filepath = os.path.join(IMG_DIR, filename)
    if os.path.exists(filepath):
        return f"assets/img/{filename}"

    img = Image.new("RGB", (600, 600), color=(14, 18, 30))
    draw = ImageDraw.Draw(img)

    # Clean borders & layered cards
    draw.rounded_rectangle([(20, 20), (580, 580)], radius=20, fill=(20, 26, 42), outline=(38, 52, 82), width=2)
    draw.rounded_rectangle([(40, 40), (560, 560)], radius=16, fill=(13, 17, 28))

    # Header branding
    draw.text((60, 65), f"SMARTPICK // {cat.upper()}", fill=(0, 210, 255))
    draw.text((540, 65), "VERIFIED ★ 4.9", fill=(255, 198, 0), anchor="ra")

    # Product visual box
    draw.rounded_rectangle([(100, 130), (500, 440)], radius=16, fill=(25, 33, 54), outline=(0, 210, 255), width=1)
    draw.text((300, 240), icon, fill=(255, 255, 255), anchor="mm")
    draw.text((300, 340), title_short[:28], fill=(255, 255, 255), anchor="mm")

    # Bottom badge
    draw.rounded_rectangle([(180, 485), (420, 525)], radius=10, fill=(0, 210, 255))
    draw.text((300, 505), "FREE SHIPPING // $75 DUTY-FREE", fill=(10, 14, 26), anchor="mm")

    img.save(filepath, "JPEG", quality=92)
    return f"assets/img/{filename}"


# Load existing 36 items
with open(DATA_FILE, "r", encoding="utf-8") as f:
    existing_db = json.load(f)

products = existing_db.get("products", [])
print(f"Starting with {len(products)} base products.")

# Normalize existing 36 items for all 4 languages (EN, HE, ES, RU)
for p in products:
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

    # Re-categorize tech accessories
    if p["id"] in ["real-101", "real-109", "real-113", "real-121"]:
        p["category"] = "tech"

print("Base products normalized.")
