# -*- coding: utf-8 -*-
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

dom = "https://smartpick-deals.com"
lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    f'  <url><loc>{dom}/index.html</loc><priority>1.0</priority><changefreq>daily</changefreq></url>'
]

for leg in ["privacy.html", "terms.html", "disclosure.html", "contact.html"]:
    lines.append(f'  <url><loc>{dom}/{leg}</loc><priority>0.5</priority><changefreq>monthly</changefreq></url>')

for p in db["products"]:
    lines.append(f'  <url><loc>{dom}/deals/{p["slug"]}.html</loc><priority>0.8</priority><changefreq>weekly</changefreq></url>')

lines.append('</urlset>')

sitemap_path = os.path.join(BASE_DIR, "sitemap.xml")
with open(sitemap_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Sitemap successfully generated with {len(db['products']) + 5} URLs at {sitemap_path}")
