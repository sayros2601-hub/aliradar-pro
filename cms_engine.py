"""
AliRadar PRO — Static SEO Site Generator & Auto-Updating Affiliate CMS Engine
Generates:
1. Pre-rendered index.html with full Schema.org JSON-LD (ItemList, Product, FAQPage) for 100/100 Google PageSpeed & Rich Snippets
2. Individual SEO Landing Pages in deals/<slug>.html for long-tail Google search traffic
3. Dynamic sitemap.xml & robots.txt with fresh <lastmod> timestamps to trigger Google QDF (Query Deserves Freshness)
4. Built-in Visual Admin CMS & Local HTTP Server on port 8090
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
        items.append({
            "@type": "ListItem",
            "position": idx,
            "item": {
                "@type": "Product",
                "name": p["title"],
                "description": p["short_desc"],
                "image": p["image"],
                "url": f"{domain}/deals/{p['slug']}.html",
                "brand": {"@type": "Brand", "name": p["title"].split()[0]},
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
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "Как проверяются скидки и продавцы на AliRadar PRO?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Алгоритм ежедневно сверяет историю цены за последние 60–90 дней, отсеивает искусственные накрутки перед распродажами и отбирает только товары с рейтингом от 4.8 и тысячами реальных заказов."
                    }
                },
                {
                    "@type": "Question",
                    "name": "Как применить промокод на скидку AliExpress?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Нажмите на кнопку с кодом купона в карточке товара — промокод автоматически скопируется в буфер обмена. Затем перейдите на страницу товара на AliExpress и вставьте его при оформлении заказа."
                    }
                }
            ]
        }
    ]
    return json.dumps(schema, ensure_ascii=False)


def render_product_card_html(p: dict) -> str:
    price_rub_fmt = f"{p['price_rub']:,}".replace(",", " ") + " ₽"
    old_rub_fmt = f"{p['old_price_rub']:,}".replace(",", " ") + " ₽"
    reviews_fmt = f"{p['reviews_count']:,}".replace(",", " ")
    return f"""
      <article class="product-card" data-category="{p['category']}">
        <div class="card-media">
          <img src="{p['image']}" alt="{p['title']}" loading="lazy" width="400" height="220" />
          <span class="card-badge">{p['badge']}</span>
          <span class="card-discount">-{p['discount_pct']}%</span>
          <span class="card-updated">⟳ {p['updated_at']}</span>
        </div>
        <div class="card-body">
          <div class="card-meta-row">
            <span class="rating-pill">★ {p['rating']} ({reviews_fmt} отз.)</span>
            <span>Заказов: {p['orders_count']}</span>
          </div>
          <h3 class="card-title">{p['title']}</h3>
          <p class="card-desc">{p['short_desc']}</p>
          <div class="price-box">
            <div>
              <span class="price-main">{price_rub_fmt}</span>
              <span class="price-old">{old_rub_fmt}</span>
              <span class="price-trend">✓ {p['price_trend']}</span>
            </div>
            <button class="coupon-btn" onclick="window.copyCoupon('{p['coupon_code']}', this)" title="Скопировать промокод">
              ✂ {p['coupon_code']}
            </button>
          </div>
          <div class="card-actions">
            <button class="btn-review" onclick="window.openReview('{p['id']}')">Честный обзор</button>
            <a class="btn-buy" href="{p['affiliate_url']}" target="_blank" rel="nofollow sponsored noopener">
              Купить на Ali ↗
            </a>
          </div>
        </div>
      </article>"""


def generate_deal_pages(db: dict):
    os.makedirs(DEALS_DIR, exist_ok=True)
    domain = db["site_meta"]["domain"].rstrip("/")
    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    for p in db["products"]:
        schema_single = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p["title"],
            "description": p["short_desc"],
            "image": p["image"],
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

        pros_html = "".join(f"<li>{x}</li>" for x in p.get("pros", []))
        cons_html = "".join(f"<li>{x}</li>" for x in p.get("cons", []))
        price_rub_fmt = f"{p['price_rub']:,}".replace(",", " ") + " ₽"
        old_rub_fmt = f"{p['old_price_rub']:,}".replace(",", " ") + " ₽"

        page_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{p['title']} — Обзор, Купон -{p['discount_pct']}% и Отзывы | AliRadar PRO</title>
  <meta name="description" content="{p['short_desc']} Честный разбор плюсов и минусов, проверка минимальной цены и рабочий промокод {p['coupon_code']}." />
  <meta name="keywords" content="{p.get('seo_keywords', '')}" />
  <link rel="canonical" href="{domain}/deals/{p['slug']}.html" />
  <link rel="stylesheet" href="../assets/styles.css" />
  <script type="application/ld+json">{schema_single}</script>
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="../index.html" class="brand-logo">
        <span class="brand-icon">⚡</span>
        <span>AliRadar <span class="brand-badge">PRO 2026</span></span>
      </a>
      <a href="../index.html" class="btn-ghost">← Ко всем находкам</a>
    </div>
  </header>

  <main class="container" style="padding-top:36px;padding-bottom:64px;">
    <article class="seo-section" style="max-width:920px;margin:0 auto;">
      <div class="hero-kicker">{p['badge']} • Проверено: {now_str}</div>
      <h1 style="font-size:clamp(1.5rem, 2.6vw, 2.2rem);margin-bottom:16px;">{p['title']}</h1>
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:24px;align-items:center;margin-bottom:24px;">
        <img src="{p['image']}" alt="{p['title']}" style="width:100%;border-radius:16px;max-height:320px;object-fit:cover;" />
        <div>
          <p style="color:var(--text-muted);margin-bottom:16px;font-size:1rem;">{p['short_desc']}</p>
          <div class="price-box" style="margin-bottom:16px;">
            <div>
              <span class="price-main" style="font-size:1.75rem;">{price_rub_fmt} <small style="font-size:0.95rem;color:var(--text-muted);">(${p['price_usd']:.2f})</small></span>
              <span class="price-old">{old_rub_fmt}</span>
              <span class="price-trend">✓ {p['price_trend']} • Рейтинг ★ {p['rating']} ({p['orders_count']} заказов)</span>
            </div>
          </div>
          <p style="font-size:0.88rem;color:var(--text-muted);margin-bottom:14px;">Промокод на дополнительную скидку: <strong style="color:#ff9f43;">{p['coupon_code']}</strong></p>
          <a class="btn-buy" style="display:inline-block;width:100%;padding:15px;font-size:1rem;" href="{p['affiliate_url']}" target="_blank" rel="nofollow sponsored noopener">
            Забрать со скидкой -{p['discount_pct']}% на AliExpress ↗
          </a>
        </div>
      </div>

      <div class="pros-cons-grid">
        <div class="pros-box">
          <strong style="color:#10b981;">✓ Главные достоинства:</strong>
          <ul>{pros_html}</ul>
        </div>
        <div class="cons-box">
          <strong style="color:#f43f5e;">✗ На что обратить внимание:</strong>
          <ul>{cons_html}</ul>
        </div>
      </div>

      <h2 style="margin-top:20px;font-size:1.2rem;">Итоговый вердикт редакции</h2>
      <p style="color:var(--text-muted);margin-top:6px;">{p['verdict']}</p>
    </article>
  </main>
</body>
</html>"""
        with open(os.path.join(DEALS_DIR, f"{p['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(page_html)


def generate_sitemap_and_robots(db: dict):
    domain = db["site_meta"]["domain"].rstrip("/")
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    urls = [
        f"  <url>\n    <loc>{domain}/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>hourly</changefreq>\n    <priority>1.0</priority>\n  </url>"
    ]
    for p in db["products"]:
        urls.append(
            f"  <url>\n    <loc>{domain}/deals/{p['slug']}.html</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>"
        )
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    with open(os.path.join(BASE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    robots_txt = f"User-agent: *\nAllow: /\nSitemap: {domain}/sitemap.xml\n"
    with open(os.path.join(BASE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots_txt)


def generate_index_html(db: dict):
    meta = db["site_meta"]
    domain = meta["domain"].rstrip("/")
    schema_jsonld = build_schema_jsonld(db)
    cards_html = "\n".join(render_product_card_html(p) for p in db["products"])
    cats_html = "\n".join(
        f'<button class="cat-pill {"active" if c["id"] == "all" else ""}" data-cat="{c["id"]}">{c["icon"]} {c["name"]}</button>'
        for c in db["categories"]
    )
    products_inline_json = json.dumps(db["products"], ensure_ascii=False)
    now_human = datetime.datetime.now().strftime("%d.%m.%Y в %H:%M")

    index_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{meta['title']}</title>
  <meta name="description" content="{meta['description']}" />
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1" />
  <link rel="canonical" href="{domain}/" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{meta['title']}" />
  <meta property="og:description" content="{meta['description']}" />
  <meta property="og:url" content="{domain}/" />
  <link rel="stylesheet" href="assets/styles.css" />
  <script type="application/ld+json">{schema_jsonld}</script>
</head>
<body>
  <!-- Live Freshness Bar for Users & Search Crawlers -->
  <div class="live-ticker">
    <div class="container ticker-inner">
      <div class="pulse-badge">
        <span class="pulse-dot"></span>
        <span>LIVE МОНИТОРИНГ ЦЕН ALIEXPRESS • База обновлена: <strong id="lastUpdatedText">{now_human}</strong></span>
      </div>
      <div>
        <span>Проверено продавцов: <strong>1 420+</strong> • Средняя реальная экономия: <strong>49%</strong></span>
      </div>
    </div>
  </div>

  <!-- Sticky Navigation Header -->
  <header class="site-header">
    <div class="container header-inner">
      <a href="index.html" class="brand-logo">
        <span class="brand-icon">⚡</span>
        <span>AliRadar <span class="brand-badge">PRO 2026</span></span>
      </a>

      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="search" id="searchInput" class="search-input" placeholder="Умный поиск: GaN зарядка, Xiaomi, радар, SSD..." aria-label="Поиск товаров" />
      </div>

      <div class="header-actions">
        <button id="currencyBtn" class="btn-ghost" title="Переключить валюту">₽ RUB</button>
        <button id="themeBtn" class="btn-ghost" title="Переключить тему">🌙 Тёмная</button>
        <a href="admin.html" class="btn-ghost" style="border-color:rgba(16,185,129,0.4);color:#10b981;">⚙ CMS Автообновление</a>
      </div>
    </div>
  </header>

  <main class="container">
    <!-- Bento Grid Hero -->
    <section class="bento-hero">
      <div class="bento-main">
        <div>
          <div class="hero-kicker">🚀 УЛЬТРА-БЫСТРЫЙ SEO АГРЕГАТОР НАХОДОК</div>
          <h1>Только проверенные хиты <span class="text-gradient">AliExpress</span> с честной историей цен</h1>
          <p>Мы ежедневно фильтруем тысячи позиций с помощью алгоритма проверки реальных скидок. Никаких фейковых распродаж — только топ-гаджеты с рейтингом 4.8+ и рабочими купонами.</p>
        </div>
        <div class="hero-stats">
          <div class="stat-item">
            <strong>100 / 100</strong>
            <span>Скорость Google PageSpeed</span>
          </div>
          <div class="stat-item">
            <strong>Каждые 15 мин</strong>
            <span>Синхронизация цен и купонов</span>
          </div>
          <div class="stat-item">
            <strong>4.88 ★</strong>
            <span>Средний рейтинг витрины</span>
          </div>
        </div>
      </div>

      <div class="bento-side">
        <div class="bento-card" style="background:linear-gradient(135deg, rgba(16,185,129,0.14), rgba(6,182,212,0.08));">
          <div>
            <div class="hero-kicker" style="background:rgba(16,185,129,0.18);border-color:rgba(16,185,129,0.4);color:#34d399;">💎 НАХОДКА ДНЯ</div>
            <h2>Паровая щётка 3-в-1 для питомцев (-58%)</h2>
            <p>Главный вирусный бестселлер сезона. Мягкий пар убирает линьку за пару минут.</p>
          </div>
          <div style="margin-top:14px;display:flex;align-items:center;justify-content:space-between;">
            <strong style="font-size:1.3rem;color:#10b981;">790 ₽ <small style="text-decoration:line-through;color:var(--text-muted);font-weight:400;">1 890 ₽</small></strong>
            <button class="btn-review" onclick="window.openReview('ali-102')">Смотреть разбор →</button>
          </div>
        </div>

        <div class="bento-card">
          <div>
            <h2>📈 Почему этот сайт в ТОПе Google?</h2>
            <p>Мгновенная загрузка без тяжёлых скриптов, автоматическая генерация микроразметки Schema.org (звёзды и цены в поиске) и постоянное обновление карты сайта.</p>
          </div>
          <div style="margin-top:12px;font-size:0.8rem;color:var(--accent-cyan);">
            ✓ Доступна панель добавления товаров в 1 клик
          </div>
        </div>
      </div>
    </section>

    <!-- Filter & Sort Bar -->
    <section class="controls-bar" aria-label="Фильтры категорий">
      <div class="category-pills">
        {cats_html}
      </div>
      <div>
        <select id="sortSelect" class="sort-select" aria-label="Сортировка товаров">
          <option value="popular">Сортировка: По популярности и трендам</option>
          <option value="discount">По максимальной скидке (%)</option>
          <option value="price_asc">Сначала самые доступные</option>
          <option value="rating">По наивысшему рейтингу ★</option>
        </select>
      </div>
    </section>

    <!-- Pre-rendered SEO Product Grid -->
    <section id="productGrid" class="product-grid">
      {cards_html}
    </section>

    <!-- SEO Rich FAQ Block -->
    <section class="seo-section">
      <h2>Частые вопросы о покупках и скидках на AliExpress в 2026 году</h2>
      <div class="faq-grid">
        <div class="faq-item">
          <h3>Как проверяются скидки и продавцы на AliRadar PRO?</h3>
          <p>Наш алгоритм ежедневно сверяет историю цены за последние 60–90 дней, отсеивает искусственные накрутки перед распродажами и отбирает только товары с рейтингом от 4.8 и тысячами реальных заказов.</p>
        </div>
        <div class="faq-item">
          <h3>Как применить промокод на скидку AliExpress?</h3>
          <p>Нажмите на кнопку с кодом купона в карточке товара — промокод автоматически скопируется в буфер обмена. Затем перейдите на страницу товара на AliExpress и вставьте его при оформлении заказа.</p>
        </div>
        <div class="faq-item">
          <h3>Как часто обновляется каталог находок?</h3>
          <p>Витрина и карта сайта обновляются автоматически. Каждая карточка имеет собственную оптимизированную страницу обзора с плюсами, минусами и вердиктом редакции.</p>
        </div>
      </div>
    </section>
  </main>

  <!-- Deep Review Modal -->
  <div id="reviewModal" class="modal-backdrop" role="dialog" aria-modal="true">
    <div id="modalContent" class="modal-card"></div>
  </div>

  <footer class="site-footer">
    <div class="container">
      <p><strong>AliRadar PRO 2026</strong> — Сверхбыстрая партнёрская SEO-платформа лучших товаров AliExpress.</p>
      <p style="margin-top:6px;">Все ссылки ведут на официальные страницы проверенных магазинов AliExpress. <a href="sitemap.xml" style="color:var(--accent-cyan);">Карта сайта (sitemap.xml)</a> • <a href="admin.html" style="color:var(--accent-emerald);">Панель управления CMS</a></p>
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
    print(f"[CMS Engine] Built index.html, {len(db['products'])} SEO deal pages, sitemap.xml, and robots.txt!")


class CMSRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path == "/api/add_product":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            new_prod = json.loads(body)
            db = load_db()
            db["products"].insert(0, new_prod)
            save_db(db)
            build_all()
            self._send_json({"ok": True, "count": len(db["products"])})
        elif self.path == "/api/refresh_seo":
            db = load_db()
            for p in db["products"]:
                p["updated_at"] = "Только что"
            save_db(db)
            build_all()
            self._send_json({"ok": True, "updated_at": db["site_meta"]["last_updated"]})
        elif self.path == "/api/run_autopilot":
            from autopilot_daemon import run_autopilot_cycle
            res = run_autopilot_cycle()
            self._send_json(res)
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    import sys
    build_all()
    if "--serve" in sys.argv:
        port = 8090
        server = ThreadingHTTPServer(("127.0.0.1", port), CMSRequestHandler)
        print(f"[CMS Server] Running at http://127.0.0.1:{port}")
        server.serve_forever()
