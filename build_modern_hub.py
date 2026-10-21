# -*- coding: utf-8 -*-
"""
BUILD MODERN HUB // 105 VIRAL PRODUCTS STATIC GENERATOR
Generates modern, clean, user-friendly Deal Hub:
- index.html (Main 105-product catalog with instant 4-language switcher)
- deals/*.html (105 standalone SEO-optimized deal pages)
"""
import os
import json
import html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "products.json")
DEALS_DIR = os.path.join(BASE_DIR, "deals")
os.makedirs(DEALS_DIR, exist_ok=True)

e = lambda s: html.escape(str(s or ""), quote=True)
RATE_ILS = 3.7

def render_precard(p, idx):
    title = p.get("title_i18n", {}).get("en") or p.get("title") or ""
    pr_usd = p["price_usd"]
    old_usd = p.get("old_price_usd") or round(pr_usd * 1.8, 2)
    disc = p.get("discount_pct", 0)
    rating = p.get("rating", 4.9)
    img = p["image"]
    eager = 'loading="eager" fetchpriority="high"' if idx < 8 else 'loading="lazy"'
    is_new = p.get("is_new", False)
    card_cls = "product-card is-new-card" if is_new else "product-card"
    new_badge = '<span class="badge-new-drop"><span class="pulse-dot"></span> ✨ NEW TODAY</span>' if is_new else ''
    disc_badge = f'<span class="discount-badge">-{disc}%</span>' if (disc and not is_new) else ''
    perk_html = '<span style="color:#34d399;font-weight:700;">✨ Added Today</span>' if is_new else '<span>🚚 Free Shipping*</span>'

    return f'''<div class="{card_cls}" data-id="{e(p['id'])}" tabindex="0" role="button" aria-label="{e(title)}">
  <div class="card-img-wrap">
    <img src="{e(img)}" alt="{e(title)}" width="400" height="400" {eager} decoding="async">
    {new_badge}
    {disc_badge}
    <span class="rating-badge">★ {rating}</span>
  </div>
  <div class="card-body">
    <h3 class="card-title">{e(title)}</h3>
    <div class="card-price-row">
      <span class="current-price">${pr_usd}</span>
      {f'<span class="old-price">${old_usd}</span>' if old_usd > pr_usd else ''}
    </div>
    <div class="card-perks">
      {perk_html}
      <span>⚡ Choice</span>
    </div>
    <div class="card-actions">
      <button type="button" class="btn-quick-view" data-modal-id="{e(p['id'])}">Quick View</button>
      <a href="{e(p['affiliate_url'])}" target="_blank" rel="nofollow sponsored noopener" class="btn-buy-deal" data-aff-id="{e(p['id'])}">Get Deal ↗</a>
    </div>
  </div>
</div>'''


def build_index(db):
    prods = db["products"]
    cats = db["categories"]
    meta = db["site_meta"]
    dom = meta["domain"].rstrip("/")

    cards_html = "\n".join(render_precard(p, i) for i, p in enumerate(prods))

    new_drops_count = len([x for x in prods if x.get("is_new")])
    cat_pills_list = []
    for c in cats:
        cat_pills_list.append(f'''<button type="button" class="cat-pill{' active' if c['id'] == 'all' else ''}" data-cat="{e(c['id'])}">
  <span>{c.get('icon', '⚡')}</span>
  <span class="cat-label">{e(c.get('name_i18n', {}).get('en', c['name']))}</span>
  <span class="cat-count">{len(prods) if c['id'] == 'all' else len([x for x in prods if x.get('category') == c['id']])}</span>
</button>''')
        if c['id'] == 'all':
            cat_pills_list.append(f'''<button type="button" class="cat-pill pill-new" data-cat="new_today">
  <span class="pulse-dot"></span>
  <span class="cat-label">New Today</span>
  <span class="cat-count">{new_drops_count}</span>
</button>''')
    cat_pills_html = "".join(cat_pills_list)

    schema_ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{dom}/#website",
                "url": dom,
                "name": "DealVault",
                "description": meta["description"],
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": f"{dom}/index.html?q={{search_term_string}}",
                    "query-input": "required name=search_term_string"
                }
            },
            {
                "@type": "ItemList",
                "@id": f"{dom}/#itemlist",
                "name": meta["title"],
                "description": meta["description"],
                "numberOfItems": len(prods),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "url": f"{dom}/deals/{p['slug']}.html",
                        "name": p.get("title_i18n", {}).get("en") or p.get("title")
                    }
                    for i, p in enumerate(prods[:50])
                ]
            }
        ]
    }, ensure_ascii=False)

    payload_json = json.dumps(
        {"categories": cats, "products": prods},
        ensure_ascii=False,
        separators=(",", ":")
    ).replace("</", "<\\/")

    out = f'''<!DOCTYPE html>
<html lang="en" dir="ltr" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>DealVault // Verified Smart Gadgets & Bargain Vault</title>
  <meta name="description" content="Discover problem-solving smart gadgets, auto upgrades, home tech and verified AliExpress bargains with free shipping and duty-free under $75.">
  <link rel="canonical" href="{dom}/index.html">
  <link rel="alternate" hreflang="x-default" href="{dom}/index.html">
  <link rel="alternate" hreflang="en" href="{dom}/index.html?lang=en">
  <link rel="alternate" hreflang="ru" href="{dom}/index.html?lang=ru">
  <link rel="alternate" hreflang="he" href="{dom}/index.html?lang=he">
  <link rel="alternate" hreflang="es" href="{dom}/index.html?lang=es">
  <meta property="og:type" content="website">
  <meta property="og:title" content="DealVault // Verified Smart Gadgets & Bargain Vault">
  <meta property="og:description" content="Handpicked viral innovations, car upgrades and everyday problem-solvers with direct factory pricing and free worldwide shipping.">
  <meta property="og:image" content="{dom}/{e(prods[0]['image'])}">
  <meta property="og:url" content="{dom}/index.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="DealVault // Curated Smart Gadgets & Vault">
  <meta name="twitter:description" content="Discover problem-solving smart gadgets and verified AliExpress bargains with free shipping.">
  <meta name="twitter:image" content="{dom}/{e(prods[0]['image'])}">
  <meta name="theme-color" content="#0284c7">
  <link rel="icon" href="assets/icon.svg" type="image/svg+xml">
  <link rel="manifest" href="manifest.json">
  <link rel="stylesheet" href="assets/modern.css?v=2026.3">
  <script>
    (function(){{
      var t = localStorage.getItem('sp_theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', t);
      var l = localStorage.getItem('sp_lang') || 'en';
      document.documentElement.setAttribute('lang', l);
      document.documentElement.setAttribute('dir', l === 'he' ? 'rtl' : 'ltr');
    }})();
  </script>
  <script type="application/ld+json">{schema_ld}</script>
  <script src="assets/tracking.js"></script>
</head>
<body>

  <!-- Sticky Modern Header -->
  <header class="modern-header">
    <div class="wrap">
      <div class="header-inner">
        <a href="index.html" class="brand-logo" aria-label="DealVault Home">
          <div class="brand-icon">⬡</div>
          <div>
            <div class="brand-text">Deal<span>Vault</span></div>
            <span class="brand-sub">Curated Deals & Tech Vault</span>
          </div>
        </a>

        <div class="header-search">
          <input type="search" id="global-search-input" placeholder="Search 100+ gadgets: car, edc, tools, home, charging..." autocomplete="off">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        </div>

        <div class="header-controls">
          <!-- 4 Language Switcher -->
          <div class="segmented-pill" aria-label="Language">
            <button type="button" class="seg-btn active" data-set-lang="en">EN</button>
            <button type="button" class="seg-btn" data-set-lang="he">עב</button>
            <button type="button" class="seg-btn" data-set-lang="es">ES</button>
            <button type="button" class="seg-btn" data-set-lang="ru">RU</button>
          </div>

          <!-- Currency Switcher -->
          <div class="segmented-pill" aria-label="Currency">
            <button type="button" class="seg-btn" data-set-cur="ILS">₪</button>
            <button type="button" class="seg-btn active" data-set-cur="USD">$</button>
            <button type="button" class="seg-btn" data-set-cur="EUR">€</button>
            <button type="button" class="seg-btn" data-set-cur="RUB">₽</button>
          </div>

          <!-- Theme Switcher -->
          <button type="button" class="theme-toggle-btn" id="theme-toggle" aria-label="Toggle Theme" title="Toggle Light / Dark Theme">🌓</button>
        </div>
      </div>
    </div>
  </header>

  <main class="wrap">
    
    <!-- Hero Banner (Compact & High-Impact) -->
    <section class="modern-hero">
      <span class="hero-pill" data-i18n="heroBadge">CURATED DEALS // 2026</span>
      <h1 data-i18n="heroH1">Smart Gadgets That Actually Solve Daily Problems</h1>
      <p data-i18n="heroSub">Handpicked viral innovations, car upgrades and everyday problem-solvers with free worldwide shipping and duty-free under $75.</p>
      
      <div class="hero-trust-badges">
        <span class="trust-badge" data-i18n="badgeFreeShip">🚚 Free Worldwide Shipping*</span>
        <span class="trust-badge" data-i18n="badgeDutyFree">💸 Duty-Free Guaranteed (&lt;$75)</span>
        <span class="trust-badge" data-i18n="badgeRating">⭐ 4.8+ Verified Buyer Ratings</span>
        <span class="trust-badge" data-i18n="badgeChoice">⚡ Direct Factory Pricing</span>
      </div>
    </section>

    <!-- Coupon HUD -->
    <aside class="modern-coupon-banner">
      <div class="coupon-info">
        <span class="coupon-tag">Active Coupon</span>
        <span data-i18n="couponText">Active AliExpress Coupon: Code [ AEIL02 ] — $2 OFF orders over $15!</span>
      </div>
      <button type="button" class="coupon-copy-btn" data-copy-coupon="AEIL02" aria-label="Copy Coupon AEIL02">
        <code>AEIL02</code>
        <span data-i18n="couponCopy">✂️ Copy Code</span>
      </button>
    </aside>

    <!-- Category Nav Tabs -->
    <nav class="category-nav" id="category-nav" aria-label="Categories">
      {cat_pills_html}
    </nav>

    <!-- Filter & Sort Bar -->
    <section class="filter-bar" aria-label="Filters">
      <div class="price-filters" id="price-filters">
        <button type="button" class="price-chip active" data-price="all" data-i18n="pAll">All Prices</button>
        <button type="button" class="price-chip" data-price="p1" data-i18n="p1">Under $10</button>
        <button type="button" class="price-chip" data-price="p2" data-i18n="p2">$10 - $25</button>
        <button type="button" class="price-chip" data-price="p3" data-i18n="p3">$25 - $50</button>
        <button type="button" class="price-chip" data-price="p4" data-i18n="p4">$50+</button>
      </div>

      <div class="filter-actions">
        <select class="sort-select" id="sort-select" aria-label="Sort">
          <option value="trending" data-i18n="sortTrending">🔥 Trending & AI Picks</option>
          <option value="discount" data-i18n="sortDiscount">🏷️ Biggest Discount %</option>
          <option value="price_asc" data-i18n="sortAsc">💵 Price: Low to High</option>
          <option value="price_desc" data-i18n="sortDesc">💎 Price: High to Low</option>
          <option value="rating" data-i18n="sortRating">⭐ Highest Rated</option>
        </select>
        <span class="items-counter" id="items-counter">{len(prods)} deals available</span>
      </div>
    </section>

    <!-- Products Grid -->
    <section class="product-grid" id="product-grid" aria-label="Products">
      {cards_html}
    </section>

  </main>

  <!-- Legal & FTC Compliant Footer -->
  <footer class="modern-footer">
    <div class="footer-inner">
      <nav class="footer-nav" aria-label="Legal">
        <a href="privacy.html" data-i18n="legalPrivacy">Privacy Policy</a>
        <span>•</span>
        <a href="terms.html" data-i18n="legalTerms">Terms of Service</a>
        <span>•</span>
        <a href="disclosure.html" data-i18n="legalDisclosure">Affiliate Disclosure</a>
        <span>•</span>
        <a href="contact.html" data-i18n="legalContact">Contact Support</a>
      </nav>
      <p data-i18n="footerLegal">Disclosure: DealVault is an independent deal review and curation hub. Links on this site are affiliate links — we may earn a small commission with zero additional cost to you. Final price, shipping and customs terms are confirmed on AliExpress.</p>
      <p class="footer-copy">© 2026 DEALVAULT. ALL RIGHTS RESERVED.</p>
    </div>
  </footer>

  <!-- Modal Dossier -->
  <div class="modern-modal" id="product-modal" hidden role="dialog" aria-modal="true">
    <div class="modal-backdrop" data-close-modal></div>
    <div class="modal-window">
      <button type="button" class="modal-close-btn" data-close-modal aria-label="סגירה">✕</button>
      <div id="modal-content-area"></div>
    </div>
  </div>

  <!-- Embedded Database & App Engine -->
  <script id="products-db" type="application/json">{payload_json}</script>
  <script src="assets/modern_app.js?v=2026.2" defer></script>
</body>
</html>'''

    target = os.path.join(BASE_DIR, "index.html")
    with open(target, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"[Hub Builder] index.html successfully compiled with {len(prods)} products.")


def build_deal_page(db, p):
    dom = db["site_meta"]["domain"].rstrip("/")
    title_en = p.get("title_i18n", {}).get("en") or p.get("title")
    title_he = p.get("title_i18n", {}).get("he") or p.get("title")
    desc = p.get("short_desc_i18n", {}).get("en") or p.get("short_desc")
    pr_usd = p["price_usd"]
    old_usd = p.get("old_price_usd") or round(pr_usd * 1.8, 2)
    disc = p.get("discount_pct", 0)
    is_new = p.get("is_new", False)
    gallery = p.get("gallery") or [p["image"]]

    slides_html = "".join(f'<img src="../{e(img)}" alt="{e(title_en)}">' for img in gallery)
    specs_rows = "".join(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed rgba(255,255,255,0.06);"><span style="color:var(--text-muted);">{e(k)}</span><b>{e(v)}</b></div>' for k, v in (p.get("specs") or {}).items())
    highlights_html = "".join(f'<li><span>✔</span> {e(h)}</li>' for h in (p.get("highlights") or []))

    new_badge_deal = '<span class="badge-new-drop" style="position:static;display:inline-flex;margin-bottom:8px;"><span class="pulse-dot"></span> ✨ NEW TODAY</span>' if is_new else ''
    disc_badge_deal = f'<span class="discount-badge" style="position:static;display:inline-block;margin-bottom:8px;">-{disc}% OFF</span>' if (disc and not is_new) else ''

    brand_name = (p.get("specs") or {}).get("Brand") or (p.get("specs") or {}).get("Manufacturer") or "DealVault Verified"
    schema_prod = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Product",
                "name": title_en,
                "image": [f"{dom}/{x}" for x in gallery],
                "description": desc,
                "brand": {"@type": "Brand", "name": brand_name},
                "sku": p["id"],
                "aggregateRating": {
                    "@type": "AggregateRating",
                    "ratingValue": str(p.get("rating", 4.9)),
                    "reviewCount": str(p.get("reviews_count", 150)),
                    "bestRating": "5"
                },
                "offers": {
                    "@type": "Offer",
                    "priceCurrency": "USD",
                    "price": str(p["price_usd"]),
                    "priceValidUntil": "2027-12-31",
                    "availability": "https://schema.org/InStock",
                    "url": p["affiliate_url"]
                }
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": dom},
                    {"@type": "ListItem", "position": 2, "name": p.get("category", "gadgets").capitalize(), "item": f"{dom}/index.html"},
                    {"@type": "ListItem", "position": 3, "name": title_en, "item": f"{dom}/deals/{p['slug']}.html"}
                ]
            }
        ]
    }, ensure_ascii=False)

    out = f'''<!DOCTYPE html>
<html lang="en" dir="ltr" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{e(title_en)} | DealVault</title>
  <meta name="description" content="{e(desc)}">
  <link rel="canonical" href="{dom}/deals/{e(p['slug'])}.html">
  <meta property="og:type" content="product">
  <meta property="og:title" content="{e(title_en)} | DealVault">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:image" content="{dom}/{e(p['image'])}">
  <meta property="og:url" content="{dom}/deals/{e(p['slug'])}.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{e(title_en)}">
  <meta name="twitter:description" content="{e(desc)}">
  <meta name="twitter:image" content="{dom}/{e(p['image'])}">
  <meta name="theme-color" content="#0284c7">
  <link rel="icon" href="../assets/icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../assets/modern.css?v=2026.3">
  <script>
    (function(){{
      var t = localStorage.getItem('sp_theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', t);
    }})();
  </script>
  <script type="application/ld+json">{schema_prod}</script>
  <script src="../assets/tracking.js"></script>
  <style>
    .deal-wrap {{ max-width: 820px; margin: 30px auto 60px; padding: 0 16px; }}
    .back-btn {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent-cyan); font-weight: 600; margin-bottom: 20px; font-size: 14px; }}
    .deal-card {{ background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); overflow: hidden; padding: 24px; box-shadow: var(--shadow-card); }}
  </style>
</head>
<body>

  <header class="modern-header">
    <div class="wrap">
      <div class="header-inner">
        <a href="../index.html" class="brand-logo" aria-label="DealVault Home">
          <div class="brand-icon">⬡</div>
          <div class="brand-text">Deal<span>Vault</span></div>
        </a>
        <div style="display:flex;align-items:center;gap:12px;">
          <a href="../index.html" class="back-btn" style="margin-bottom:0;">➔ Back to Catalog</a>
          <button type="button" class="theme-toggle-btn" id="theme-toggle" aria-label="Toggle Theme" title="Toggle Light / Dark Theme">🌓</button>
        </div>
      </div>
    </div>
  </header>

  <main class="deal-wrap">
    <a href="../index.html" class="back-btn">➔ Back to All Deals</a>
    <div class="deal-card">
      <div class="modal-grid-layout" style="padding:0;">
        <div class="modal-gallery-view">
          <div class="modal-slider">
            {slides_html}
          </div>
        </div>
        <div>
          {new_badge_deal}
          {disc_badge_deal}
          <h1 style="font-size:20px;font-weight:800;color:var(--text-primary);line-height:1.4;margin-bottom:12px;">{e(title_en)}</h1>
          
          <div class="modal-price-box">
            <span class="modal-current-price">${pr_usd}</span>
            {f'<span class="modal-old-price">${old_usd}</span>' if old_usd > pr_usd else ''}
            <span style="color:var(--accent-amber);font-weight:bold;margin-inline-start:auto;">★ {p.get("rating", 4.9)}</span>
          </div>

          <div class="modal-share-bar">
            <span class="share-title">Quick Share:</span>
            <button type="button" class="btn-share btn-share-wa" onclick="window.shareDeal && window.shareDeal('whatsapp', {{title:'{e(title_en)}', price_usd:{p['price_usd']}, slug:'{e(p['slug'])}'}}, 'en')">
              💬 WhatsApp
            </button>
            <button type="button" class="btn-share btn-share-tg" onclick="window.shareDeal && window.shareDeal('telegram', {{title:'{e(title_en)}', price_usd:{p['price_usd']}, slug:'{e(p['slug'])}'}}, 'en')">
              ✈️ Telegram
            </button>
            <button type="button" class="btn-share btn-share-copy" onclick="window.shareDeal && window.shareDeal('copy', {{title:'{e(title_en)}', price_usd:{p['price_usd']}, slug:'{e(p['slug'])}'}}, 'en')">
              🔗 Copy Link
            </button>
          </div>

          {f'<div style="margin:14px 0;"><h4 style="font-size:13.5px;color:var(--accent-cyan);margin-bottom:8px;">⚡ Key Advantages</h4><ul class="modal-bullets">{highlights_html}</ul></div>' if highlights_html else ''}

          {f'<div style="margin:14px 0;background:var(--bg-surface-hover);padding:12px;border-radius:8px;border:1px solid var(--border-subtle);"><h4 style="font-size:12.5px;color:var(--text-muted);text-transform:uppercase;margin-bottom:8px;">SPECIFICATIONS</h4>{specs_rows}</div>' if specs_rows else ''}

          <a href="{e(p['affiliate_url'])}" target="_blank" rel="nofollow sponsored noopener" class="modal-cta-btn" id="deal-cta-btn">
            Check Deal on AliExpress ↗
          </a>
        </div>
      </div>
    </div>
  </main>

  <footer class="modern-footer">
    <div class="footer-inner">
      <nav class="footer-nav">
        <a href="../privacy.html">Privacy Policy</a>
        <span>•</span>
        <a href="../terms.html">Terms of Service</a>
        <span>•</span>
        <a href="../disclosure.html">Affiliate Disclosure</a>
        <span>•</span>
        <a href="../contact.html">Contact Support</a>
      </nav>
      <p>© 2026 DEALVAULT. ALL RIGHTS RESERVED.</p>
    </div>
  </footer>

  <script>
    const cta = document.getElementById('deal-cta-btn');
    if (cta && window.decorateAffiliateUrl) {{
      cta.href = window.decorateAffiliateUrl(cta.href, "{e(p['id'])}");
      cta.addEventListener('click', () => {{
        if (window.trackAffiliateClick) {{
          window.trackAffiliateClick({{
            id: "{e(p['id'])}",
            title: "{e(title_en)}",
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


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    build_index(db)
    for p in db["products"]:
        build_deal_page(db, p)
    print(f"[Hub Builder] Generated index.html + {len(db['products'])} individual deal pages.")


if __name__ == "__main__":
    main()
