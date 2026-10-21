"""
CYBERPICK 2077 // STATIC SITE GENERATOR
Compiles the high-tech Cyberpunk AI Deal Matrix into:
- index.html (Main 3D Matrix with HUD, dynamic filter matrix, and hologram modal)
- deals/*.html (Standalone Cyberpunk deal pages for search crawlers and deep links)

Strict compliance with AliExpress Affiliate Rules (August 2025):
- No unauthorized trademark claims or logos on CTA buttons
- Compliant action-oriented CTA: 'למעבר לדיל ↗' / 'View Deal ↗'
- Transparent affiliate disclosure and seller attribution
- 0 to 300 ₪ threshold with Free Shipping and Duty-Free under $75
"""
import os
import json
import html
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
DEALS_DIR = os.path.join(BASE_DIR, "deals")
RATE_ILS = 3.7
VER = "2077.1"

e = lambda s: html.escape(str(s or ""), quote=True)


def tr(p, key, lang="he"):
    d = p.get(key + "_i18n") or {}
    return d.get(lang) or p.get(key) or d.get("en") or ""


def orders_num(p):
    n = re.sub(r"[^0-9]", "", str(p.get("orders_count") or ""))
    return int(n) if n else int(p.get("reviews_count") or 0)


def compact_product(p):
    keep = [
        "id", "slug", "category", "price_usd", "old_price_usd", "discount_pct",
        "rating", "reviews_count", "affiliate_url", "image", "gallery",
        "highlights", "specs"
    ]
    obj = {k: p.get(k) for k in keep if p.get(k) is not None}
    for k in ["title", "short_desc"]:
        obj[k] = p.get(k + "_i18n") or {"he": p.get(k, "")}
    obj["pop"] = orders_num(p)
    return obj


def render_card_html(p, idx, prefix=""):
    title = tr(p, "title")
    pr_ils = round(p["price_usd"] * RATE_ILS)
    old_ils = round((p.get("old_price_usd") or 0) * RATE_ILS)
    disc = p.get("discount_pct") or 0
    eager = 'loading="eager" fetchpriority="high"' if idx < 6 else 'loading="lazy"'
    img_src = prefix + p["image"]

    return f'''<div class="cyber-card" data-id="{e(p['id'])}" tabindex="0" role="button" aria-label="{e(title)}">
  <div class="card-visual">
    <img src="{e(img_src)}" alt="{e(title)}" width="400" height="400" {eager} decoding="async">
    {f'<span class="cyber-tag-off">-{disc}%</span>' if disc else ''}
    <span class="cyber-hud-rating">★ {p.get('rating', '')}</span>
  </div>
  <div class="card-content">
    <h3 class="card-headline">{e(title)}</h3>
    <div class="price-box">
      <span class="cyber-price">₪{pr_ils}</span>
      {f'<span class="cyber-old-price">₪{old_ils}</span>' if old_ils > pr_ils else ''}
    </div>
    <div class="card-footer-meta">
      <span class="ship-badge">🚚 משלוח חינם*</span>
      <span class="action-arrow">פרטים ורכישה ❯</span>
    </div>
  </div>
</div>'''


def build_index(db):
    meta = db["site_meta"]
    prods = db["products"]
    cats = db["categories"]
    dom = meta["domain"].rstrip("/")

    cards_html = "\n".join(render_card_html(p, i) for i, p in enumerate(prods))

    payload_json = json.dumps(
        {"cats": cats, "products": [compact_product(p) for p in prods]},
        ensure_ascii=False,
        separators=(",", ":")
    ).replace("</", "<\\/")

    schema_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": meta["title"],
        "description": meta["description"],
        "numberOfItems": len(prods),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": f"{dom}/deals/{p['slug']}.html",
                "name": tr(p, "title")
            }
            for i, p in enumerate(prods)
        ]
    }, ensure_ascii=False)

    cat_pills_html = "".join(
        f'''<button class="cyber-cat-pill{' active' if c['id'] == 'all' else ''}" data-cat="{e(c['id'])}">
  <span class="cat-icon">{c.get('icon', '⚡')}</span>
  <span class="cat-label">{e(c['name'])}</span>
  <span class="cat-badge">{len(prods) if c['id'] == 'all' else len([x for x in prods if x.get('category') == c['id']])}</span>
</button>'''
        for c in cats
    )

    out = f'''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>SmartPick // מטריקס מציאות וגאדג׳טים חכמים מהעתיד</title>
  <meta name="description" content="מטריקס דילים עתידני מבוסס AI: גאדג'טים מהפכניים, פטנטים לרכב, לבית ולחיים. 100% קישורים מאומתים, פטור מלא ממכס עד $75 ומשלוח חינם לישראל.">
  <link rel="canonical" href="{dom}/index.html">
  <meta property="og:type" content="website">
  <meta property="og:title" content="SmartPick // מטריקס מציאות וגאדג׳טים חכמים מהעתיד">
  <meta property="og:description" content="מטריקס דילים עתידני מבוסס AI: גאדג'טים מהפכניים, פטנטים לרכב, לבית ולחיים. 100% קישורים מאומתים, פטור מלא ממכס עד $75 ומשלוח חינם לישראל.">
  <meta property="og:image" content="{dom}/{e(prods[0]['image'])}">
  <meta property="og:url" content="{dom}/index.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="SmartPick // מטריקס מציאות וגאדג׳טים חכמים מהעתיד">
  <meta name="twitter:description" content="מטריקס דילים עתידני מבוסס AI: גאדג'טים מהפכניים, פטנטים לרכב, לבית ולחיים.">
  <meta name="twitter:image" content="{dom}/{e(prods[0]['image'])}">
  <meta name="theme-color" content="#05070f">
  <link rel="icon" href="assets/icon.svg" type="image/svg+xml">
  <link rel="manifest" href="manifest.json">
  <link rel="apple-touch-icon" href="assets/icon.svg">
  <link rel="preload" as="image" href="{e(prods[0]['image'])}" fetchpriority="high">
  <link rel="stylesheet" href="assets/cyber.css?v={VER}">
  <script type="application/ld+json">{schema_ld}</script>
  <script src="assets/tracking.js"></script>
</head>
<body>

  <!-- Cyber Background Perspective Grid & Floating Auroras -->
  <div class="cyber-canvas-wrap" aria-hidden="true">
    <div class="cyber-grid-floor"></div>
    <div class="cyber-aurora aurora-1"></div>
    <div class="cyber-aurora aurora-2"></div>
    <div class="cyber-aurora aurora-3"></div>
  </div>

  <!-- Cyber Header & HUD -->
  <header class="cyber-header">
    <div class="header-meta-bar">
      <div class="hud-badge"><span class="hud-pulse"></span> <span data-i18n="badge3">⚡ דילים מאומתים 100%</span></div>
      <div class="hud-badge"><span data-i18n="badge1">🚚 משלוח חינם לישראל*</span></div>
      <div class="hud-badge"><span data-i18n="badge2">💸 פטור מלא ממע"מ ומכס (&lt;$75)</span></div>
    </div>
    
    <div class="header-main">
      <a href="index.html" class="cyber-logo" aria-label="SmartPick Matrix">
        <div class="logo-badge"><span>SP</span></div>
        <div class="logo-title">SMART<b>PICK</b> <span class="logo-sub">MATRIX // 2077</span></div>
      </a>

      <div class="cyber-search-box">
        <div class="cyber-search-wrap">
          <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
          <input type="search" id="cyber-search-input" placeholder="חיפוש במטריקס: גאדג'ט, רכב, בית, כלים..." autocomplete="off" enterkeyhint="search">
        </div>
      </div>

      <button class="cyber-pref-btn" id="cyber-pref-btn" aria-label="Interface settings">
        <span id="pref-btn-label">HE · ₪</span>
      </button>
    </div>

    <!-- Category Pills Navigation -->
    <nav class="cyber-nav" id="cyber-nav" aria-label="קטגוריות">
      {cat_pills_html}
    </nav>
  </header>

  <!-- Main Cyber Matrix Display -->
  <main class="wrap">
    
    <!-- Hero HUD Banner -->
    <section class="cyber-hero">
      <span class="hero-tag" data-i18n="heroTag">מטריקס מבצעים // 2077</span>
      <h1 data-i18n="h1">גאדג'טים ופטנטים מהעתיד במחירי השקה</h1>
      <p data-i18n="sub">סריקת מוצרים שימושיים ממיטב היצרנים ברשת. פטור מלא ממכס עד $75 ומשלוח חינם לישראל.</p>
      <div class="cyber-badges-row">
        <span class="cyber-chip" data-i18n="badge1">🚚 משלוח חינם לישראל*</span>
        <span class="cyber-chip" data-i18n="badge2">💸 פטור מלא ממע"מ ומכס (&lt;$75)</span>
        <span class="cyber-chip" data-i18n="badge3">⚡ דילים מאומתים 100%</span>
      </div>
    </section>

    <!-- Cyber Coupon HUD Banner -->
    <aside class="cyber-coupon-hud" aria-label="פרומו קופונים פעילים">
      <div class="coupon-content">
        <span class="coupon-badge-tag">קוד קופון פעיל</span>
        <span>קבל הנחה נוספת של $2 בקנייה מעל $15 באמצעות קוד מיוחד:</span>
      </div>
      <button type="button" class="coupon-pill" data-copy-coupon="AEIL02" aria-label="העתק קופון AEIL02">
        <code>AEIL02</code>
        <span>✂️ העתק קופון</span>
      </button>
    </aside>

    <!-- Expanded Filter & Sorting Matrix -->
    <section class="filter-matrix" aria-label="מסנן ומיונים">
      <div class="matrix-row-1">
        <div class="price-segment" id="price-segment" role="group" aria-label="טווח מחירים">
          <button class="price-btn active" data-price="all" data-i18n="pAll">הכל</button>
          <button class="price-btn" data-price="p1" data-i18n="p1">עד ₪25</button>
          <button class="price-btn" data-price="p2" data-i18n="p2">₪25 - ₪50</button>
          <button class="price-btn" data-price="p3" data-i18n="p3">₪50 - ₪100</button>
          <button class="price-btn" data-price="p4" data-i18n="p4">₪100 - ₪200</button>
        </div>
        <div class="matrix-sort">
          <select id="matrix-sort-select" aria-label="אפשרויות מיון">
            <option value="ai" data-i18n="sortAi">🧠 דירוג AI חכם</option>
            <option value="disc" data-i18n="sortDisc">🔥 הנחה הגבוהה ביותר</option>
            <option value="asc" data-i18n="sortAsc">💵 מחיר: מהזול ליקר</option>
            <option value="desc" data-i18n="sortDesc">💎 מחיר: מהיקר לזול</option>
            <option value="rate" data-i18n="sortRate">⭐ דירוג קונים</option>
          </select>
        </div>
      </div>

      <div class="feature-toggles" id="toggle-chips">
        <button class="toggle-chip" data-toggle="rate48" data-i18n="chipRate">⭐ דירוג 4.8+ בלבד</button>
        <button class="toggle-chip" data-toggle="disc50" data-i18n="chipDisc">🔥 הנחה 50% ומעלה</button>
        <button class="toggle-chip active" data-toggle="freeShip" data-i18n="chipFree">🚚 משלוח חינם</button>
      </div>

      <div class="matrix-counter" id="matrix-count">
        <span class="hud-pulse"></span> <b>{len(prods)}</b> <span data-i18n="itemsFound">פריטים פעילים במטריקס</span>
      </div>
    </section>

    <!-- Interactive 3D Product Matrix Grid -->
    <section class="cyber-grid" id="cyber-grid" aria-label="מטריקס מוצרים">
      {cards_html}
    </section>

  </main>

  <!-- Legal & FTC Compliant Terminal Footer -->
  <footer class="cyber-footer">
    <div class="terminal-box">
      <h4 style="color: var(--cyan); font-family: var(--font-mono); font-size: 13px; margin-bottom: 8px;">// SMARTPICK MATRIX LEGAL DISCLOSURE</h4>
      <p data-i18n="footerDisc">הבהרה משפטית: אתר SmartPick Matrix הינו אתר סקירות והמלצות עצמאי. הקישורים באתר הינם קישורי שותפים (Affiliate Links) — ברכישת מוצר ייתכן שנקבל עמלה ללא כל עלות נוספת עבורכם. המחירים, המשלוח והזמינות נקבעים ומוצגים במלואם באתר המוכר ב-AliExpress. *משלוח חינם בכפוף לתנאי המוכר וליעד המשלוח.</p>
      
      <nav class="footer-nav-links" aria-label="ניווט משפטי ומדיניות">
        <a href="privacy.html">מדיניות פרטיות (Privacy)</a>
        <span>•</span>
        <a href="terms.html">תנאי שימוש (Terms)</a>
        <span>•</span>
        <a href="disclosure.html">גילוי נאות שותפים (Disclosure)</a>
        <span>•</span>
        <a href="contact.html">יצירת קשר ושירות (Contact)</a>
      </nav>

      <p style="margin-top: 12px; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">© 2077 SMARTPICK SYSTEM. ALL RIGHTS RESERVED.</p>
    </div>
  </footer>

  <!-- Holographic Product Dossier Modal -->
  <div class="cyber-modal" id="cyber-modal" hidden role="dialog" aria-modal="true" aria-labelledby="modal-dossier-body">
    <div class="modal-backdrop" data-close-modal></div>
    <div class="modal-dossier">
      <button class="modal-close-x" data-close-modal aria-label="סגירה">✕</button>
      <div id="modal-dossier-body"></div>
    </div>
  </div>

  <!-- Language & Currency Preferences Modal -->
  <div class="cyber-modal" id="cyber-pref-modal" hidden role="dialog" aria-modal="true">
    <div class="modal-backdrop" data-close-modal></div>
    <div class="modal-dossier" style="max-width: 480px;">
      <button class="modal-close-x" data-close-modal aria-label="סגירה">✕</button>
      <div id="pref-modal-body"></div>
    </div>
  </div>

  <!-- Inline Encrypted Database & Dynamic Engine -->
  <script id="cyber-data" type="application/json">{payload_json}</script>
  <script src="assets/cyber_app.js?v={VER}" defer></script>
</body>
</html>'''

    target = os.path.join(BASE_DIR, "index.html")
    with open(target, "w", encoding="utf-8") as f:
        f.write(out)


def build_deal(db, p):
    dom = db["site_meta"]["domain"].rstrip("/")
    gallery = p.get("gallery") or [p["image"]]
    pr_ils = round(p["price_usd"] * RATE_ILS)
    old_ils = round((p.get("old_price_usd") or 0) * RATE_ILS)
    title = tr(p, "title")
    desc = tr(p, "short_desc")

    slides_html = "".join(
        f'<img src="../{e(img)}" alt="{e(title)} {i+1}" width="600" height="600" {"fetchpriority=high" if i==0 else "loading=lazy"} decoding="async">'
        for i, img in enumerate(gallery)
    )
    dots_html = "".join(f'<i class="{"active" if i == 0 else ""}"></i>' for i in range(len(gallery)))

    specs_rows = "".join(
        f'<tr><th>{e(k)}</th><td>{e(v)}</td></tr>'
        for k, v in (p.get("specs") or {}).items()
    )

    highlights_html = "".join(
        f'<li style="font-size: 13.5px; color: #cbd5e1; display: flex; gap: 8px;"><span style="color: var(--green); font-weight: bold;">✔</span> {e(h)}</li>'
        for h in (p.get("highlights") or [])
    )

    others = [x for x in db["products"] if x.get("category") == p.get("category") and x["id"] != p["id"]][:3]
    related_cards = "\n".join(
        render_card_html(x, i, prefix="../").replace('data-id="', f'onclick="location.href=\'{e(x["slug"])}.html\'" data-id="')
        for i, x in enumerate(others)
    )

    schema_prod = json.dumps({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "image": [f"{dom}/{x}" for x in gallery],
        "description": desc,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": str(p.get("rating", "4.8")),
            "reviewCount": str(p.get("reviews_count", "100"))
        },
        "offers": {
            "@type": "Offer",
            "priceCurrency": "USD",
            "price": str(p["price_usd"]),
            "availability": "https://schema.org/InStock",
            "url": p["affiliate_url"]
        }
    }, ensure_ascii=False)

    out = f'''<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{e(title)} | SmartPick Matrix // 2077</title>
  <meta name="description" content="{e(desc)}">
  <link rel="canonical" href="{dom}/deals/{e(p['slug'])}.html">
  <meta property="og:type" content="product">
  <meta property="og:title" content="{e(title)} | SmartPick Matrix">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:image" content="{dom}/{e(p['image'])}">
  <meta property="og:url" content="{dom}/deals/{e(p['slug'])}.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{e(title)}">
  <meta name="twitter:description" content="{e(desc)}">
  <meta name="twitter:image" content="{dom}/{e(p['image'])}">
  <meta name="theme-color" content="#05070f">
  <link rel="icon" href="../assets/icon.svg" type="image/svg+xml">
  <link rel="manifest" href="../manifest.json">
  <link rel="apple-touch-icon" href="../assets/icon.svg">
  <link rel="stylesheet" href="../assets/cyber.css?v={VER}">
  <script type="application/ld+json">{schema_prod}</script>
  <script src="../assets/tracking.js"></script>
  <style>
    .deal-container {{ max-width: 800px; margin: 30px auto 60px; padding: 0 16px; }}
    .back-nav {{ display: inline-flex; align-items: center; gap: 8px; color: var(--cyan); text-decoration: none; font-family: var(--font-mono); font-size: 14px; margin-bottom: 20px; padding: 8px 16px; background: rgba(0,240,255,0.06); border: 1px solid var(--border-neon); border-radius: 8px; }}
    .back-nav:hover {{ background: rgba(0,240,255,0.15); box-shadow: 0 0 16px var(--cyan-glow); }}
    .standalone-dossier {{ background: var(--bg-panel); border: 1px solid var(--border-neon); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.8), 0 0 30px rgba(0,240,255,0.1); }}
    .rel-title {{ font-size: 20px; color: #fff; margin: 40px 0 20px; font-family: var(--font-mono); }}
  </style>
</head>
<body>

  <!-- Cyber Background Perspective Grid & Floating Auroras -->
  <div class="cyber-canvas-wrap" aria-hidden="true">
    <div class="cyber-grid-floor"></div>
    <div class="cyber-aurora aurora-1"></div>
    <div class="cyber-aurora aurora-2"></div>
  </div>

  <header class="cyber-header">
    <div class="header-main" style="padding: 12px 20px;">
      <a href="../index.html" class="cyber-logo">
        <div class="logo-badge"><span>SP</span></div>
        <div class="logo-title">SMART<b>PICK</b> <span class="logo-sub">MATRIX // 2077</span></div>
      </a>
      <a href="../index.html" class="back-nav" style="margin-bottom: 0;">➔ חזרה למטריקס</a>
    </div>
  </header>

  <main class="deal-container">
    <div class="standalone-dossier">
      <div class="modal-gallery">
        <div class="modal-slider" id="deal-slider">
          {slides_html}
        </div>
        <div class="modal-dots" id="deal-dots">
          {dots_html}
        </div>
      </div>

      <div class="modal-details">
        {f'<span class="cyber-tag-off" style="position: static; display: inline-block; margin-bottom: 8px;">-{p.get("discount_pct")}% OFF</span>' if p.get("discount_pct") else ''}
        <h1 class="modal-h3" style="font-size: 22px;">{e(title)}</h1>
        <div class="modal-price-row">
          <span class="modal-price">₪{pr_ils}</span>
          {f'<s class="cyber-old-price" style="font-size: 16px;">₪{old_ils}</s>' if old_ils > pr_ils else ''}
          <span style="color: var(--gold); font-size: 14px; font-weight: bold; margin-inline-start: auto;">★ {p.get("rating")}</span>
        </div>
        <div class="modal-perks">
          <span class="modal-perk-tag">🚚 משלוח חינם לישראל*</span>
          <span class="modal-perk-tag" style="color: var(--cyan); border-color: rgba(0, 240, 255, 0.3);">💸 פטור ממע"מ (&lt;$75)</span>
          <span class="modal-perk-tag" style="color: var(--gold); border-color: rgba(255, 210, 0, 0.3);">⚡ דיל אונליין מאומת</span>
        </div>

        {f'<div style="margin: 16px 0;"><h4 style="color: #fff; margin-bottom: 10px; font-size: 14px;">⚡ יתרונות בולטים</h4><ul style="list-style: none; display: grid; gap: 8px;">{highlights_html}</ul></div>' if highlights_html else ''}

        {f'<div class="specs-terminal"><h4 style="color: var(--cyan); margin-bottom: 8px; font-size: 13px;">// מפרט טכני מאומת</h4><table class="specs-table"><tbody>{specs_rows}</tbody></table></div>' if specs_rows else ''}

        <div class="modal-share-row">
          <span class="share-label">שיתוף מהיר:</span>
          <button type="button" class="share-btn share-btn-wa" onclick="window.shareDeal && window.shareDeal('whatsapp', {{title:'{e(title)}', price_ils:{pr_ils}, price_usd:{p['price_usd']}, slug:'{e(p['slug'])}'}}, 'he')" aria-label="Share WhatsApp">
            <span>💬 WhatsApp</span>
          </button>
          <button type="button" class="share-btn share-btn-tg" onclick="window.shareDeal && window.shareDeal('telegram', {{title:'{e(title)}', price_ils:{pr_ils}, price_usd:{p['price_usd']}, slug:'{e(p['slug'])}'}}, 'he')" aria-label="Share Telegram">
            <span>✈️ Telegram</span>
          </button>
          <button type="button" class="share-btn share-btn-copy" onclick="window.shareDeal && window.shareDeal('copy', {{title:'{e(title)}', price_ils:{pr_ils}, price_usd:{p['price_usd']}, slug:'{e(p['slug'])}'}}, 'he')" aria-label="Copy Link">
            <span>🔗 העתקת קישור</span>
          </button>
        </div>
      </div>

      <div class="modal-bottom-bar" style="position: static; border-radius: 0 0 16px 16px;">
        <div>
          <b style="font-family: var(--font-mono); font-size: 22px; color: var(--cyan);">₪{pr_ils}</b>
          <small style="display: block; font-size: 11px; color: var(--text-muted);">משוער באתר המוכר</small>
        </div>
        <a class="cta-cyber-button" id="deal-cta-btn" href="{e(p['affiliate_url'])}" target="_blank" rel="nofollow sponsored noopener">
          <span>למעבר לדיל ↗</span>
        </a>
      </div>
    </div>

    {f'<h3 class="rel-title">// פריטים קשורים במטריקס</h3><div class="cyber-grid">{related_cards}</div>' if related_cards else ''}
  </main>

  <footer class="cyber-footer">
    <div class="terminal-box">
      <h4 style="color: var(--cyan); font-family: var(--font-mono); font-size: 13px; margin-bottom: 8px;">// SMARTPICK MATRIX LEGAL DISCLOSURE</h4>
      <p>הבהרה: אתר SmartPick הינו אתר סקירות והמלצות עצמאי. הקישורים הינם קישורי שותפים (Affiliate Links). המחירים, המשלוח והזמינות מוצגים במלואם באתר המוכר ב-AliExpress.</p>
      
      <nav class="footer-nav-links" aria-label="ניווט משפטי ומדיניות">
        <a href="../privacy.html">מדיניות פרטיות</a>
        <span>•</span>
        <a href="../terms.html">תנאי שימוש</a>
        <span>•</span>
        <a href="../disclosure.html">גילוי נאות שותפים</a>
        <span>•</span>
        <a href="../contact.html">יצירת קשר ושירות</a>
      </nav>

      <p style="margin-top: 12px; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">© 2077 SMARTPICK SYSTEM. ALL RIGHTS RESERVED.</p>
    </div>
  </footer>

  <script>
    const slider = document.getElementById('deal-slider');
    const dots = [...document.querySelectorAll('#deal-dots i')];
    if (slider) {{
      slider.addEventListener('scroll', () => {{
        const idx = Math.round(Math.abs(slider.scrollLeft) / slider.clientWidth);
        dots.forEach((dot, j) => dot.classList.toggle('active', j === idx));
      }}, {{ passive: true }});
    }}
    const cta = document.getElementById('deal-cta-btn');
    if (cta && window.decorateAffiliateUrl) {{
      cta.href = window.decorateAffiliateUrl(cta.href, "{e(p['id'])}");
      cta.addEventListener('click', () => {{
        if (window.trackAffiliateClick) {{
          window.trackAffiliateClick({{
            id: "{e(p['id'])}",
            title: "{e(title)}",
            price_usd: {p['price_usd']},
            category: "{e(p.get('category',''))}"
          }});
        }}
      }});
    }}
  </script>
</body>
</html>'''

    target = os.path.join(DEALS_DIR, f"{p['slug']}.html")
    with open(target, "w", encoding="utf-8") as f:
        f.write(out)


def build():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    os.makedirs(DEALS_DIR, exist_ok=True)
    build_index(db)
    for p in db["products"]:
        build_deal(db, p)
    print(f"[Cyber Builder] Successfully generated index.html + {len(db['products'])} deal nodes in Cyberpunk 2077 aesthetic!")


if __name__ == "__main__":
    build()
