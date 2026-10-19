"""
SmartChoice / SmartPick Global — Curated Marketplace Discovery & Affiliate SEO Engine
- Default Language: Hebrew (עברית, RTL)
- 7 Instant Languages: Hebrew (HE), English (EN), Russian (RU), Spanish (ES), French (FR), German (DE), Arabic (AR)
- Currencies: ₪ ILS, $ USD, € EUR (Rubles completely removed)
- 100% Trademark-Compliant Independent Branding with official FTC/Affiliate Disclosures
- 100% Real Factory Images (Cached locally in assets/img/ for 0-latency, 0-rate-limit reliability)
- Curiosity Benefit Hooks on Cards + Interactive Full Specs & Multi-Angle Modals
"""

import os
import json
import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
DEALS_DIR = os.path.join(BASE_DIR, "deals")


def load_db() -> dict:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db: dict):
    db["site_meta"]["last_updated"] = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def build_schema_jsonld(db: dict) -> str:
    domain = db["site_meta"]["domain"].rstrip("/")
    items = []
    for idx, p in enumerate(db["products"], 1):
        gallery = p.get("gallery") or [p["image"]]
        full_imgs = [g if g.startswith("http") else f"{domain}/{g}" for g in gallery]
        items.append({
            "@type": "ListItem",
            "position": idx,
            "item": {
                "@type": "Product",
                "name": p["title"],
                "description": p.get("card_hook") or p.get("short_desc", ""),
                "image": full_imgs,
                "url": f"{domain}/deals/{p['slug']}.html",
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": str(p["rating"]),
                    "reviewCount": str(p["reviews_count"])
                },
                "offers": {
                    "@type": "Offer",
                    "url": p["affiliate_url"],
                    "priceCurrency": "USD",
                    "price": str(p["price_usd"]),
                    "availability": "https://schema.org/InStock"
                }
            }
        })

    schema = [
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": db["site_meta"]["title"],
            "description": db["site_meta"]["description"],
            "numberOfItems": len(items),
            "itemListElement": items
        }
    ]
    return json.dumps(schema, ensure_ascii=False)


def render_product_card_html(p: dict) -> str:
    ils_price = int(round(p["price_usd"] * 3.65))
    ils_old = int(round(p["old_price_usd"] * 3.65))
    gallery = (p.get("gallery") or [p["image"]])[:5]
    hook = p.get("card_hook") or p.get("short_desc", "")

    thumbs_html = ""
    if len(gallery) > 1:
        thumbs_items = "".join(
            f'<button type="button" class="thumb-item {"active" if i == 0 else ""}" onclick="window.switchCardPhoto(\'{p["id"]}\', \'{g_url}\', this)" aria-label="Photo {i+1}"><img src="{g_url}" alt="" loading="lazy" width="40" height="40" /></button>'
            for i, g_url in enumerate(gallery)
        )
        thumbs_html = f'<div class="thumb-strip">{thumbs_items}</div>'

    return f"""
      <article class="product-card" data-category="{p['category']}">
        <div class="card-media-wrap">
          <a href="{p['affiliate_url']}" target="_blank" rel="nofollow sponsored noopener" class="card-media">
            <img id="main-img-{p['id']}" src="{gallery[0]}" alt="{p['title']}" loading="lazy" width="300" height="300" />
            <span class="choice-tag">★ Choice</span>
            <span class="card-discount">-{p['discount_pct']}%</span>
          </a>
          {thumbs_html}
        </div>
        <div class="card-body">
          <div class="card-meta-row">
            <span class="rating-pill">★ {p['rating']} ({p['reviews_count']:,})</span>
            <span class="orders-pill">נמכרו: {p['orders_count']}</span>
          </div>
          <h3 class="card-title" title="{p['title']}">{p['title']}</h3>
          <div class="card-hook" onclick="window.openReview('{p['id']}')" title="לחצו לצפייה בכל התמונות והמפרט">
            {hook}
          </div>
          <div class="price-box">
            <div>
              <span class="price-main">₪{ils_price}</span>
              <span class="price-old">₪{ils_old}</span>
            </div>
            <span class="shipping-tag">🚚 משלוח חינם ומהיר</span>
          </div>
          <div class="card-actions">
            <button type="button" class="btn-review" onclick="window.openReview('{p['id']}')">
              🔍 תמונות ומפרט
            </button>
            <a class="btn-buy" href="{p['affiliate_url']}" target="_blank" rel="nofollow sponsored noopener">
              לרכישה בחנות הרשמית ←
            </a>
          </div>
        </div>
      </article>"""


def generate_deal_pages(db: dict):
    os.makedirs(DEALS_DIR, exist_ok=True)
    domain = db["site_meta"]["domain"].rstrip("/")
    now_str = datetime.datetime.now().strftime("%d.%m.%Y")

    for p in db["products"]:
        gallery = (p.get("gallery") or [p["image"]])[:6]
        full_imgs = [g if g.startswith("http") else f"{domain}/{g}" for g in gallery]
        local_imgs_for_deal = [g if g.startswith("http") else f"../{g}" for g in gallery]

        schema_single = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p["title"],
            "description": p.get("card_hook") or p.get("short_desc", ""),
            "image": full_imgs,
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": str(p["rating"]),
                "reviewCount": str(p["reviews_count"])
            },
            "offers": {
                "@type": "Offer",
                "url": p["affiliate_url"],
                "priceCurrency": "USD",
                "price": str(p["price_usd"]),
                "availability": "https://schema.org/InStock"
            }
        }, ensure_ascii=False)

        ils_price = int(round(p["price_usd"] * 3.65))
        ils_old = int(round(p["old_price_usd"] * 3.65))

        thumbs_html = "".join(
            f'<button type="button" class="modal-thumb {"active" if i == 0 else ""}" onclick="document.getElementById(\'deal-hero-img\').src=\'{img_url}\'; this.parentElement.querySelectorAll(\'.modal-thumb\').forEach(b => b.classList.remove(\'active\')); this.classList.add(\'active\');"><img src="{img_url}" alt="Photo {i+1}" /></button>'
            for i, img_url in enumerate(local_imgs_for_deal)
        )

        highlights_html = ""
        if p.get("highlights"):
            highlights_html = f"""
            <h3 style="font-size:1.05rem;font-weight:800;color:#191919;margin-top:20px;margin-bottom:8px;">⭐ יתרונות בולטים של המוצר:</h3>
            <ul class="highlights-list">
              {''.join(f'<li>{h}</li>' for h in p['highlights'])}
            </ul>
            """

        specs_html = ""
        if p.get("specs"):
            specs_html = f"""
            <h3 style="font-size:1.05rem;font-weight:800;color:#191919;margin-top:16px;margin-bottom:8px;">📋 מפרט טכני מלא:</h3>
            <table class="specs-table">
              <tbody>
                {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in p['specs'].items())}
              </tbody>
            </table>
            """

        en_title = p.get("title_i18n", {}).get("en", p["title"])
        ru_title = p.get("title_i18n", {}).get("ru", "")
        hook = p.get("card_hook") or p.get("short_desc", "")

        page_html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#fd384f" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <title>{p['title']} | Choice Deal — SmartPick</title>
  <meta name="description" content="{hook} {en_title} {ru_title}" />
  <link rel="canonical" href="{domain}/deals/{p['slug']}.html" />
  <link rel="icon" href="../assets/icon.svg" type="image/svg+xml" />
  <link rel="apple-touch-icon" href="../assets/icon.svg" />
  <link rel="stylesheet" href="../assets/styles.css" />
  <script type="application/ld+json">{schema_single}</script>
</head>
<body>
  <!-- Top Trust Bar -->
  <div class="top-bar">
    <div class="container top-bar-inner">
      <div class="top-bar-badges">
        <span>✓ <strong>חנויות רשמיות</strong> בלבד</span>
        <span>📦 משלוח מהיר לישראל (עד <strong>$75</strong> פטור ממס)</span>
        <span>🔒 רכישה ישירה ובטוחה</span>
      </div>
      <div>
        <a href="../index.html" style="color:#ffd000;text-decoration:none;font-weight:700;">← חזרה לקטלוג הראשי</a>
      </div>
    </div>
  </div>

  <header class="site-header">
    <div class="container header-inner">
      <a href="../index.html" class="brand-logo">
        <span class="brand-icon">✓</span>
        <span>SmartPick <span class="brand-sub">Choice Deals</span></span>
      </a>
      <a href="../index.html" class="lang-select" style="display:inline-flex;align-items:center;text-decoration:none;">לכל המציאות בקטלוג →</a>
    </div>
  </header>

  <main class="container" style="max-width:860px;margin-top:20px;margin-bottom:60px;">
    <article style="background:#fff;border:1px solid #eaebed;border-radius:14px;padding:24px;box-shadow:var(--shadow-card);">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span class="choice-tag" style="position:static;">★ Choice</span>
        <span style="color:#fd384f;font-weight:900;font-size:0.9rem;">-{p['discount_pct']}% הנחה פעילה</span>
        <span style="color:#ff9800;font-weight:800;font-size:0.86rem;">★ {p['rating']} ({p['reviews_count']:,} ביקורות)</span>
        <span style="color:#64748b;font-size:0.84rem;">נמכרו: {p['orders_count']}</span>
      </div>

      <h1 style="font-size:1.35rem;font-weight:800;line-height:1.4;margin-bottom:14px;color:#191919;">{p['title']}</h1>

      <!-- Main Photo Preview with Thumbnail Strip -->
      <div class="modal-hero-wrap" style="max-height:420px;">
        <img id="deal-hero-img" src="{local_imgs_for_deal[0]}" alt="{p['title']}" />
      </div>

      <div class="modal-thumbs-row">
        {thumbs_html}
      </div>

      <div class="card-hook" style="cursor:default;font-size:0.92rem;margin-bottom:16px;">
        {hook}
      </div>

      {highlights_html}
      {specs_html}

      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px 16px;font-size:0.86rem;color:#166534;margin-top:16px;margin-bottom:24px;">
        🛡️ <strong>רכישה בטוחה:</strong> קישור ישיר לחנות הרשמית. פטור מלא ממס בישראל בהזמנות עד $75, הגנת קונים מלאה ומשלוח מהיר.
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;padding-top:16px;border-top:1px solid #eaebed;">
        <div>
          <span class="price-main" style="font-size:1.75rem;">₪{ils_price}</span>
          <span class="price-old" style="font-size:1.05rem;">₪{ils_old}</span>
          <span style="font-size:0.85rem;color:#64748b;margin-inline-start:6px;">(${p['price_usd']:.2f})</span>
        </div>
        <a class="btn-buy" style="padding:12px 28px;font-size:1.02rem;" href="{p['affiliate_url']}" target="_blank" rel="nofollow sponsored noopener">
          לרכישה בחנות הרשמית במחיר המבצע ←
        </a>
      </div>
    </article>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p><strong>SmartPick Global — קטלוג עצמאי למציאות וגאדג׳טים מובילים</strong></p>
      <div class="disclaimer-box">
        גילוי נאות: SmartPick הוא קטלוג המלצות עצמאי ואינו בבעלות AliExpress או קבוצת Alibaba. כל הקישורים באתר הם קישורי שותפים רשמיים המובילים ישירות לחנויות המקוריות במחיר המבצע ללא תוספת תשלום.
      </div>
    </div>
  </footer>
</body>
</html>"""

        with open(os.path.join(DEALS_DIR, f"{p['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(page_html)


def generate_sitemap_and_robots(db: dict):
    domain = db["site_meta"]["domain"].rstrip("/")
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d")

    urls = [
        f"""  <url>
    <loc>{domain}/index.html</loc>
    <lastmod>{now_iso}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""
    ]

    for p in db["products"]:
        urls.append(f"""  <url>
    <loc>{domain}/deals/{p['slug']}.html</loc>
    <lastmod>{now_iso}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>""")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    with open(os.path.join(BASE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    robots_txt = f"""User-agent: *
Allow: /
Sitemap: {domain}/sitemap.xml
"""
    with open(os.path.join(BASE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots_txt)


def generate_index_html(db: dict):
    schema_jsonld = build_schema_jsonld(db)
    cards_html = "\n".join(render_product_card_html(p) for p in db["products"])
    domain = db["site_meta"]["domain"].rstrip("/")

    cats_html = "\n".join(
        f'<button type="button" class="cat-pill {"active" if c["id"] == "all" else ""}" data-cat="{c["id"]}">{c["icon"]} {c["name"]}</button>'
        for c in db["categories"]
    )

    products_inline_json = json.dumps(db["products"], ensure_ascii=False)

    index_html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#fd384f" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <meta name="apple-mobile-web-app-title" content="SmartPick" />
  <title>{db['site_meta']['title']}</title>
  <meta name="description" content="{db['site_meta']['description']}" />
  <link rel="canonical" href="{domain}/index.html" />
  <link rel="manifest" href="manifest.json" />
  <link rel="icon" href="assets/icon.svg" type="image/svg+xml" />
  <link rel="apple-touch-icon" href="assets/icon.svg" />
  <link rel="stylesheet" href="assets/styles.css" />
  <script type="application/ld+json">{schema_jsonld}</script>
</head>
<body>
  <!-- Top Trust Bar -->
  <div class="top-bar">
    <div class="container top-bar-inner">
      <div class="top-bar-badges">
        <span id="topBadge1">✓ <strong>חנויות רשמיות</strong> בלבד</span>
        <span id="topBadge2">📦 משלוח מהיר לישראל ואירופה (עד <strong>$75</strong> פטור מלא ממס בישראל)</span>
        <span id="topBadge3">🔒 רכישה בטוחה ישירות מהיצרן</span>
      </div>
      <div class="top-bar-controls">
        <div class="currency-switch" role="group" aria-label="Currency">
          <button type="button" class="curr-btn active" data-curr="ILS">₪ ILS</button>
          <button type="button" class="curr-btn" data-curr="USD">$ USD</button>
          <button type="button" class="curr-btn" data-curr="EUR">€ EUR</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Main Header with Search and Language -->
  <header class="site-header">
    <div class="container header-inner">
      <a href="index.html" class="brand-logo">
        <span class="brand-icon">✓</span>
        <span>SmartPick <span class="brand-sub">Choice Deals</span></span>
      </a>

      <div class="search-box">
        <input type="search" id="searchInput" placeholder="חיפוש מציאות: מטען GaN, מצלמת דרך 2K, גאדג׳טים, חיות מחמד..." aria-label="Search" />
        <button type="button" id="searchBtn" class="search-btn">חיפוש</button>
      </div>

      <div class="header-actions">
        <select id="langSelect" class="lang-select" aria-label="Language">
          <option value="he" selected>🇮🇱 עברית (HE)</option>
          <option value="en">🇺🇸 English (EN)</option>
          <option value="ru">🇷🇺 Русский (RU)</option>
          <option value="es">🇪🇸 Español (ES)</option>
          <option value="fr">🇫🇷 Français (FR)</option>
          <option value="de">🇩🇪 Deutsch (DE)</option>
          <option value="ar">🇸🇦 العربية (AR)</option>
        </select>
      </div>
    </div>
  </header>

  <main class="container">
    <!-- Hero Banner -->
    <section class="store-banner">
      <div class="store-banner-left">
        <h1 id="heroTitle">מציאות Choice וגאדג׳טים מובחרים — במחירים ישירים מהיצרן</h1>
        <p id="heroSub">כל המוצרים נבחרו בקפידה עם תמונות מפעל אמיתיות, דירוג קונים מאומת (4.8★–5.0★) ומשלוח מהיר.</p>
      </div>
      <div class="trust-pills">
        <div id="pill1" class="trust-pill">⭐ דירוג 4.8+ מוכח</div>
        <div id="pill2" class="trust-pill">📸 תמונות מוצר אמיתיות (לחצו להחלפה)</div>
        <div id="pill3" class="trust-pill">✈️ משלוח מהיר לכל העולם</div>
      </div>
    </section>

    <!-- Categories & Sort -->
    <section class="controls-bar" aria-label="Categories">
      <div class="category-pills">
        {cats_html}
      </div>
      <div>
        <select id="sortSelect" class="sort-select" aria-label="Sort">
          <option value="popular">מיון: הכי פופולריים</option>
          <option value="discount">לפי גובה ההנחה (%)</option>
          <option value="price_asc">מחיר: מהנמוך לגבוה</option>
          <option value="rating">לפי דירוג קונים ★</option>
        </select>
      </div>
    </section>

    <!-- 1:1 Real Square Product Grid with 5-Photo Gallery Strip -->
    <section id="productGrid" class="product-grid">
      {cards_html}
    </section>
  </main>

  <!-- Product Gallery & Details Modal -->
  <div id="reviewModal" class="modal-backdrop" role="dialog" aria-modal="true">
    <div id="modalContent" class="modal-card"></div>
  </div>

  <footer class="site-footer">
    <div class="container">
      <p><strong id="footerTitle">SmartPick Global — קטלוג עצמאי למציאות וגאדג׳טים מובילים</strong></p>
      <div id="disclosureBox" class="disclaimer-box">
        גילוי נאות: SmartPick הוא קטלוג המלצות עצמאי ואינו בבעלות AliExpress או קבוצת Alibaba. כל הקישורים באתר הם קישורי שותפים רשמיים המובילים ישירות לחנויות המקוריות במחיר המבצע ללא תוספת תשלום.
      </div>
    </div>
  </footer>

  <script>window.__INITIAL_PRODUCTS__ = {products_inline_json};</script>
  <script src="assets/app.js"></script>
</body>
</html>"""

    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)


def build_all():
    db = load_db()
    generate_index_html(db)
    generate_deal_pages(db)
    generate_sitemap_and_robots(db)
    print(f"[SmartPick Engine] Successfully built index.html, {len(db['products'])} deal pages, sitemap.xml and robots.txt!")


class CMSRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    import sys
    build_all()
    if "--serve" in sys.argv:
        port = 8090
        server = ThreadingHTTPServer(("127.0.0.1", port), CMSRequestHandler)
        print(f"[SmartPick Server] Running at http://127.0.0.1:{port}")
        server.serve_forever()
