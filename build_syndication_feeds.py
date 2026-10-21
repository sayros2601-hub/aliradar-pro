# -*- coding: utf-8 -*-
"""
SYNDICATION FEED GENERATOR
Generates rss.xml and feed.json for all 105 products so external automation
tools (IFTTT, Zapier, dlvr.it, Telegram RSS Bot) can auto-post all 100 deals.
"""
import os
import json
import html
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
RSS_FILE = os.path.join(BASE_DIR, "rss.xml")
FEED_JSON_FILE = os.path.join(BASE_DIR, "feed.json")

def escape_xml(s):
    return html.escape(str(s or ""), quote=True)

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    
    prods = db.get("products", [])
    dom = db.get("site_meta", {}).get("domain", "https://dealvault.pages.dev").rstrip("/")
    now_rfc822 = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # RSS 2.0
    items_xml = []
    feed_items_json = []

    for p in prods:
        slug = p["slug"]
        link = f"{dom}/deals/{slug}.html"
        t_en = p.get("title_i18n", {}).get("en") or p.get("title", "")
        t_he = p.get("title_i18n", {}).get("he", "")
        t_ru = p.get("title_i18n", {}).get("ru", "")
        t_es = p.get("title_i18n", {}).get("es", "")
        desc = p.get("short_desc_i18n", {}).get("en") or p.get("short_desc", "")
        img = f"{dom}/{p['image']}"
        price = p["price_usd"]
        old_price = p.get("old_price_usd", round(price * 1.8, 2))
        disc = p.get("discount_pct", 50)

        item_str = f"""    <item>
      <title>{escape_xml(f"[{disc}% OFF] {t_en} - ${price}")}</title>
      <link>{escape_xml(link)}</link>
      <guid isPermaLink="true">{escape_xml(link)}</guid>
      <description>{escape_xml(f"{desc} | Now ${price} (was ${old_price}). Free Worldwide Shipping!")}</description>
      <pubDate>{now_rfc822}</pubDate>
      <enclosure url="{escape_xml(img)}" type="image/jpeg" length="102400"/>
      <category>{escape_xml(p.get("category", "gadgets"))}</category>
    </item>"""
        items_xml.append(item_str)

        feed_items_json.append({
            "id": p["id"],
            "url": link,
            "title": t_en,
            "title_he": t_he,
            "title_ru": t_ru,
            "title_es": t_es,
            "image": img,
            "price_usd": price,
            "discount_pct": disc,
            "affiliate_url": p["affiliate_url"],
            "category": p.get("category", "gadgets")
        })

    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DealVault Deals 24/7 Feed</title>
    <link>{dom}</link>
    <description>Daily Curated AliExpress Deals and Viral Problem-Solving Gadgets</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{dom}/rss.xml" rel="self" type="application/rss+xml" />
{"".join(chr(10) + x for x in items_xml)}
  </channel>
</rss>"""

    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(rss_content)

    with open(FEED_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "version": "https://jsonfeed.org/version/1.1",
            "title": "DealVault Deals JSON Feed",
            "home_page_url": dom,
            "feed_url": f"{dom}/feed.json",
            "items": feed_items_json
        }, f, ensure_ascii=False, indent=2)

    print(f"[Syndication] Generated rss.xml ({len(prods)} items) and feed.json")

if __name__ == "__main__":
    main()
