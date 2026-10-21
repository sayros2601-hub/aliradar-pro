/**
 * SMARTPICK // MODERN DEAL HUB ENGINE
 * 4 Languages: EN, HE, ES, RU
 * 4 Currencies: USD, ILS, EUR, RUB
 * Fast live search, instant category filters, modal dossier & 1-click sharing
 */
(() => {
  'use strict';

  const dataScript = document.getElementById('products-db');
  if (!dataScript) return;

  const DB = JSON.parse(dataScript.textContent);
  const P = DB.products;
  const CATS = DB.categories;

  // Currency Rates relative to 1 USD
  const RATES = { USD: 1.0, ILS: 3.7, EUR: 0.92, RUB: 96.0 };
  const SYMS = { USD: '$', ILS: '₪', EUR: '€', RUB: '₽' };

  // Localization Dictionary (EN, HE, ES, RU)
  const I18N = {
    en: {
      siteTitle: "SmartPick // Curated Smart Gadgets & Trending Life Hacks",
      heroBadge: "CURATED DEALS // 2026",
      heroH1: "Smart Gadgets That Actually Solve Daily Problems",
      heroSub: "Handpicked viral innovations, car upgrades and everyday problem-solvers with free worldwide shipping and duty-free under $75.",
      badgeFreeShip: "🚚 Free Worldwide Shipping*",
      badgeDutyFree: "💸 Duty-Free Guaranteed (<$75)",
      badgeRating: "⭐ 4.8+ Verified Buyer Ratings",
      badgeChoice: "⚡ Direct Factory Pricing",
      badgeNewDrop: "✨ NEW TODAY",
      freshToday: "Fresh Daily Drop",
      newToday: "New Today",
      couponText: "Active AliExpress Coupon: Code [ AEIL02 ] — $2 OFF orders over $15!",
      couponCopy: "✂️ Copy Code",
      couponCopied: "Coupon AEIL02 Copied to Clipboard! ✂️",
      searchPlaceholder: "Search 100+ gadgets: car, edc, tools, home, charging...",
      pAll: "All Prices",
      p1: "Under $10",
      p2: "$10 - $25",
      p3: "$25 - $50",
      p4: "$50+",
      sortTrending: "🔥 Trending & AI Picks",
      sortDiscount: "🏷️ Biggest Discount %",
      sortAsc: "💵 Price: Low to High",
      sortDesc: "💎 Price: High to Low",
      sortRating: "⭐ Highest Rated",
      itemsFound: "deals available",
      noResults: "No matching gadgets found. Try another search term! 🔍",
      quickView: "Quick View",
      getDeal: "Get Deal ↗",
      specsHeader: "Verified Specifications",
      whyHeader: "Why It's Genius",
      shareHeader: "Share Deal:",
      copyLink: "Copy Link",
      linkCopied: "Link copied to clipboard! 📋",
      modalCta: "Check Deal on AliExpress ↗",
      footerLegal: "Disclosure: SmartPick is an independent deal review and curation hub. Links on this site are affiliate links — we may earn a small commission with zero additional cost to you. Final price, shipping and customs terms are confirmed on AliExpress.",
      legalPrivacy: "Privacy Policy",
      legalTerms: "Terms of Service",
      legalDisclosure: "Affiliate Disclosure",
      legalContact: "Contact Support"
    },
    he: {
      siteTitle: "SmartPick // מציאות שוות וגאדג'טים חכמים לחיים",
      heroBadge: "מבצעים מאומתים // 2026",
      heroH1: "גאדג'טים ופטנטים שבאמת פותרים בעיות ביומיום",
      heroSub: "מציאות ויראליות מאומתות, שדרוגים לרכב ולבית במחירי יצרן ישירים. פטור מלא ממע\"מ ומכס עד $75 ומשלוח חינם לישראל.",
      badgeFreeShip: "🚚 משלוח חינם לישראל*",
      badgeDutyFree: "💸 פטור מלא ממע\"מ ומכס (<$75)",
      badgeRating: "⭐ דירוג 4.8+ בלבד",
      badgeChoice: "⚡ מחירי יצרן ישירים",
      badgeNewDrop: "✨ חדש מהיום",
      freshToday: "נוסף היום",
      newToday: "חדש היום",
      couponText: "קוד קופון פעיל: AEIL02 — הנחה של $2 בקנייה מעל $15!",
      couponCopy: "✂️ העתק קופון",
      couponCopied: "הקופון AEIL02 הועתק בהצלחה! ✂️",
      searchPlaceholder: "חיפוש בין 100+ גאדג'טים: רכב, בית, כלים, מטען...",
      pAll: "כל המחירים",
      p1: "עד ₪35",
      p2: "₪35 - ₪90",
      p3: "₪90 - ₪185",
      p4: "מעל ₪185",
      sortTrending: "🔥 הכי פופולרי ונבחר",
      sortDiscount: "🏷️ הנחה הגבוהה ביותר",
      sortAsc: "💵 מחיר: מהזול ליקר",
      sortDesc: "💎 מחיר: מהיקר לזול",
      sortRating: "⭐ דירוג קונים גבוה",
      itemsFound: "מציאות פעילות",
      noResults: "לא אותרו פריטים תואמים. נסו חיפוש אחר! 🔍",
      quickView: "פרטים מהירים",
      getDeal: "לדיל ↗",
      specsHeader: "מפרט טכני מאומת",
      whyHeader: "יתרונות בולטים",
      shareHeader: "שיתוף מהיר:",
      copyLink: "העתקת קישור",
      linkCopied: "הקישור הועתק בהצלחה! 📋",
      modalCta: "למעבר לדיל ב-AliExpress ↗",
      footerLegal: "גילוי נאות: אתר SmartPick הינו אתר סקירות והמלצות עצמאי. הקישורים הינם קישורי שותפים — ברכישת מוצר ייתכן שנקבל עמלה ללא כל עלות נוספת עבורכם. המחירים, המשלוח והזמינות מוצגים במלואם באתר AliExpress. *משלוח חינם בכפוף לתנאי המוכר.",
      legalPrivacy: "מדיניות פרטיות",
      legalTerms: "תנאי שימוש",
      legalDisclosure: "גילוי נאות שותפים",
      legalContact: "יצירת קשר ושירות"
    },
    es: {
      siteTitle: "SmartPick // Chollos y Gadgets Inteligentes del Momento",
      heroBadge: "CHOLLOS VERIFICADOS // 2026",
      heroH1: "Gadgets Útiles que Solucionan Problemas Reales",
      heroSub: "Innovaciones virales para el coche, hogar y día a día con precios directos de fábrica. Envío gratis a España y libre de aduanas.",
      badgeFreeShip: "🚚 Envío Gratis Disponible*",
      badgeDutyFree: "💸 Sin Aduanas (<75$)",
      badgeRating: "⭐ Valoración Media 4.8+",
      badgeChoice: "⚡ Precios Directos de Fábrica",
      badgeNewDrop: "✨ NOVEDAD HOY",
      freshToday: "Novedad Hoy",
      newToday: "Novedades",
      couponText: "Cupón Activo AliExpress: Código [ AEIL02 ] — 2$ de descuento en compras >15$!",
      couponCopy: "✂️ Copiar Cupón",
      couponCopied: "¡Cupón AEIL02 Copiado! ✂️",
      searchPlaceholder: "Buscar entre más de 100 chollos: coche, herramientas, hogar...",
      pAll: "Todos los Precios",
      p1: "Menos de 10€",
      p2: "10€ - 25€",
      p3: "25€ - 50€",
      p4: "Más de 50€",
      sortTrending: "🔥 Más Populares",
      sortDiscount: "🏷️ Mayor Descuento %",
      sortAsc: "💵 Precio: Menor a Mayor",
      sortDesc: "💎 Precio: Mayor a Menor",
      sortRating: "⭐ Mejor Valorados",
      itemsFound: "chollos activos",
      noResults: "No se encontraron gadgets. ¡Prueba con otra búsqueda! 🔍",
      quickView: "Vista Rápida",
      getDeal: "Ver Chollo ↗",
      specsHeader: "Especificaciones Técnicas",
      whyHeader: "Por Qué es Genial",
      shareHeader: "Compartir:",
      copyLink: "Copiar Enlace",
      linkCopied: "¡Enlace copiado al portapapeles! 📋",
      modalCta: "Comprobar Chollo en AliExpress ↗",
      footerLegal: "Aviso Legal: SmartPick es un portal independiente de recomendaciones y chollos. Los enlaces son de afiliados — podemos recibir una comisión sin coste extra para ti. Los precios y disponibilidad final se confirman en AliExpress.",
      legalPrivacy: "Política de Privacidad",
      legalTerms: "Términos de Servicio",
      legalDisclosure: "Aviso de Afiliados",
      legalContact: "Contacto y Soporte"
    },
    ru: {
      siteTitle: "SmartPick // Умные находки, полезные гаджеты и топ-скидки",
      heroBadge: "ПРОВЕРЕННЫЕ НАХОДКИ // 2026",
      heroH1: "Умные гаджеты и новинки, которые реально полезны",
      heroSub: "Отобранные вирусные изобретения для авто, дома, мастерской и повседневной жизни по прямым ценам AliExpress с бесплатной доставкой.",
      badgeFreeShip: "🚚 Бесплатная доставка*",
      badgeDutyFree: "💸 Без пошлин до $75",
      badgeRating: "⭐ Рейтинг 4.8+ у всех товаров",
      badgeChoice: "⚡ Прямые цены производителей",
      badgeNewDrop: "✨ НОВИНКА ДНЯ",
      freshToday: "Свежая новинка",
      newToday: "Новинки дня",
      couponText: "Активный промокод AliExpress: Код [ AEIL02 ] — скидка $2 при заказе от $15!",
      couponCopy: "✂️ Скопировать",
      couponCopied: "Промокод AEIL02 скопирован! ✂️",
      searchPlaceholder: "Поиск среди 100+ товаров: авто, дом, инструменты, зарядки...",
      pAll: "Все цены",
      p1: "До 1 000 ₽ ($10)",
      p2: "1 000 - 2 500 ₽",
      p3: "2 500 - 5 000 ₽",
      p4: "От 5 000 ₽",
      sortTrending: "🔥 В тренде и популярные",
      sortDiscount: "🏷️ Максимальная скидка %",
      sortAsc: "💵 Сначала недорогие",
      sortDesc: "💎 Сначала премиум",
      sortRating: "⭐ По оценкам покупателей",
      itemsFound: "активных находок",
      noResults: "По вашему запросу ничего не найдено. Попробуйте другие слова! 🔍",
      quickView: "Быстрый обзор",
      getDeal: "К товару ↗",
      specsHeader: "Технические характеристики",
      whyHeader: "Главные фишки и плюсы",
      shareHeader: "Поделиться:",
      copyLink: "Скопировать ссылку",
      linkCopied: "Ссылка скопирована в буфер! 📋",
      modalCta: "Смотреть сделку на AliExpress ↗",
      footerLegal: "Уведомление: SmartPick — независимый обзорный портал полезных товаров. Ссылки являются партнерскими — мы можем получать вознаграждение без переплат с вашей стороны. Финальная цена и условия доставки подтверждаются на AliExpress.",
      legalPrivacy: "Конфиденциальность",
      legalTerms: "Условия использования",
      legalDisclosure: "Партнерское раскрытие",
      legalContact: "Связаться с нами"
    }
  };

  // State
  const defaultLang = () => {
    const nav = (navigator.language || '').toLowerCase();
    if (nav.startsWith('he')) return 'he';
    if (nav.startsWith('es')) return 'es';
    if (nav.startsWith('ru')) return 'ru';
    return 'en';
  };

  const defaultCur = (l) => {
    if (l === 'he') return 'ILS';
    if (l === 'es') return 'EUR';
    if (l === 'ru') return 'RUB';
    return 'USD';
  };

  const STATE = {
    lang: localStorage.getItem('sp_lang') || defaultLang(),
    cur: localStorage.getItem('sp_cur') || '',
    theme: localStorage.getItem('sp_theme') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
    cat: 'all',
    price: 'all',
    sort: 'trending',
    search: ''
  };

  if (!STATE.cur) STATE.cur = defaultCur(STATE.lang);
  window.SmartPickCurrentCurrency = STATE.cur;

  const applyTheme = () => {
    document.documentElement.setAttribute('data-theme', STATE.theme);
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
      themeBtn.textContent = STATE.theme === 'dark' ? '☀️' : '🌙';
      themeBtn.setAttribute('title', STATE.theme === 'dark' ? 'Светлая тема' : 'Темная тема');
    }
  };

  // Helpers
  const t = (k) => I18N[STATE.lang]?.[k] || I18N.en[k] || '';
  const tx = (obj) => {
    if (!obj) return '';
    if (typeof obj === 'string') return obj;
    return obj[STATE.lang] || obj.en || obj.he || obj.ru || obj.es || '';
  };

  const formatMoney = (usdVal) => {
    const rate = RATES[STATE.cur] || 1.0;
    const sym = SYMS[STATE.cur] || '$';
    const val = usdVal * rate;

    if (STATE.cur === 'ILS') return `₪${Math.round(val)}`;
    if (STATE.cur === 'RUB') return `${Math.round(val).toLocaleString()} ₽`;
    if (STATE.cur === 'EUR') return `${val.toFixed(2)} €`;
    return `$${val.toFixed(2)}`;
  };

  // Filter & Sort
  const PRICE_LIMITS_USD = {
    all: [0, 99999],
    p1: [0, 10],
    p2: [10, 25],
    p3: [25, 50],
    p4: [50, 99999]
  };

  function getFilteredProducts() {
    const q = STATE.search.trim().toLowerCase();
    const [minPr, maxPr] = PRICE_LIMITS_USD[STATE.price] || [0, 99999];

    let list = P.filter(p => {
      // Category filter (support special 'new_today' category)
      if (STATE.cat === 'new_today') {
        if (!p.is_new) return false;
      } else if (STATE.cat !== 'all' && p.category !== STATE.cat) {
        return false;
      }
      // Price
      if (p.price_usd < minPr || p.price_usd >= maxPr) return false;
      // Search
      if (q) {
        const full = [
          Object.values(p.title_i18n || {}),
          Object.values(p.short_desc_i18n || {}),
          p.highlights || []
        ].flat().join(' ').toLowerCase();
        if (!full.includes(q)) return false;
      }
      return true;
    });

    // Sort
    const sorters = {
      trending: (a, b) => (b.orders_count || 0) * (b.rating || 4.8) - (a.orders_count || 0) * (a.rating || 4.8),
      discount: (a, b) => (b.discount_pct || 0) - (a.discount_pct || 0),
      price_asc: (a, b) => a.price_usd - b.price_usd,
      price_desc: (a, b) => b.price_usd - a.price_usd,
      rating: (a, b) => (b.rating || 0) - (a.rating || 0) || (b.reviews_count || 0) - (a.reviews_count || 0)
    };

    return list.sort(sorters[STATE.sort] || sorters.trending);
  }

  // Render Card HTML
  function renderCard(p, idx) {
    const title = tx(p.title_i18n);
    const priceStr = formatMoney(p.price_usd);
    const oldStr = p.old_price_usd > p.price_usd ? formatMoney(p.old_price_usd) : '';
    const isNewClass = p.is_new ? ' is-new-card' : '';
    const newDropBadge = p.is_new ? `<span class="badge-new-drop"><span class="pulse-dot"></span> ${t('badgeNewDrop')}</span>` : '';
    const discBadge = p.discount_pct && !p.is_new ? `<span class="discount-badge">-${p.discount_pct}%</span>` : '';
    const ratingBadge = `<span class="rating-badge">★ ${p.rating}</span>`;
    const affUrl = window.decorateAffiliateUrl ? window.decorateAffiliateUrl(p.affiliate_url, p.id) : p.affiliate_url;

    return `
      <div class="product-card${isNewClass}" data-id="${p.id}" tabindex="0" role="button" aria-label="${title}">
        <div class="card-img-wrap">
          <img src="${p.image}" alt="${title}" width="400" height="400" loading="${idx < 8 ? 'eager' : 'lazy'}" decoding="async">
          ${newDropBadge}
          ${discBadge}
          ${ratingBadge}
        </div>
        <div class="card-body">
          <h3 class="card-title">${title}</h3>
          <div class="card-price-row">
            <span class="current-price">${priceStr}</span>
            ${oldStr ? `<span class="old-price">${oldStr}</span>` : ''}
          </div>
          <div class="card-perks">
            ${p.is_new ? `<span style="color:#34d399;font-weight:700;">✨ ${t('freshToday')}</span>` : `<span>🚚 ${t('badgeFreeShip').split(' ')[1] || 'Free'}</span>`}
            <span>⚡ Choice</span>
          </div>
          <div class="card-actions">
            <button type="button" class="btn-quick-view" data-modal-id="${p.id}">
              ${t('quickView')}
            </button>
            <a href="${affUrl}" target="_blank" rel="nofollow sponsored noopener" class="btn-buy-deal" data-aff-id="${p.id}">
              ${t('getDeal')}
            </a>
          </div>
        </div>
      </div>
    `;
  }

  // Render Grid
  function renderGrid() {
    const grid = document.getElementById('product-grid');
    if (!grid) return;

    const list = getFilteredProducts();
    if (list.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--accent-cyan); font-size: 16px;">${t('noResults')}</div>`;
    } else {
      grid.innerHTML = list.map((p, i) => renderCard(p, i)).join('');
    }

    const counter = document.getElementById('items-counter');
    if (counter) {
      counter.textContent = `${list.length} ${t('itemsFound')}`;
    }
  }

  // Open Product Modal
  function openModal(id, pushHash = true) {
    const p = P.find(x => x.id === id);
    if (!p) return;

    const modal = document.getElementById('product-modal');
    const body = document.getElementById('modal-content-area');
    if (!modal || !body) return;

    const title = tx(p.title_i18n);
    const desc = tx(p.short_desc_i18n);
    const priceStr = formatMoney(p.price_usd);
    const oldStr = p.old_price_usd > p.price_usd ? formatMoney(p.old_price_usd) : '';
    const gallery = p.gallery && p.gallery.length ? p.gallery : [p.image];
    const affUrl = window.decorateAffiliateUrl ? window.decorateAffiliateUrl(p.affiliate_url, p.id) : p.affiliate_url;

    const highlightsHtml = (p.highlights && p.highlights.length) ? `
      <div style="margin: 14px 0;">
        <h4 style="font-size: 13.5px; color: var(--accent-cyan); margin-bottom: 8px;">⚡ ${t('whyHeader')}</h4>
        <ul class="modal-bullets">
          ${p.highlights.map(h => `<li><span>✔</span> ${h}</li>`).join('')}
        </ul>
      </div>
    ` : `<p style="color: var(--text-secondary); font-size: 14px; margin: 12px 0;">${desc}</p>`;

    const specsHtml = (p.specs && Object.keys(p.specs).length) ? `
      <div style="margin: 14px 0; background: rgba(0,0,0,0.25); padding: 12px; border-radius: 8px; border: 1px solid var(--border-subtle);">
        <h4 style="font-size: 12.5px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">${t('specsHeader')}</h4>
        <div style="display: grid; gap: 6px; font-size: 12.5px;">
          ${Object.entries(p.specs).map(([k, v]) => `
            <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(255,255,255,0.06); padding-bottom: 4px;">
              <span style="color: var(--text-muted);">${k}</span>
              <b style="color: #cbd5e1;">${v}</b>
            </div>
          `).join('')}
        </div>
      </div>
    ` : '';

    body.innerHTML = `
      <div class="modal-grid-layout">
        <div class="modal-gallery-view">
          <div class="modal-slider" id="modal-slider">
            ${gallery.map(img => `<img src="${img}" alt="" width="600" height="600">`).join('')}
          </div>
        </div>
        <div class="modal-details-view">
          ${p.is_new ? `<span class="badge-new-drop" style="position:static;display:inline-flex;margin-bottom:8px;"><span class="pulse-dot"></span> ${t('badgeNewDrop')}</span>` : (p.discount_pct ? `<span class="discount-badge" style="position: static; display: inline-block; margin-bottom: 8px;">-${p.discount_pct}% OFF</span>` : '')}
          <h2>${title}</h2>
          <div class="modal-price-box">
            <span class="modal-current-price">${priceStr}</span>
            ${oldStr ? `<span class="modal-old-price">${oldStr}</span>` : ''}
            <span style="color: var(--accent-amber); font-weight: bold; margin-inline-start: auto;">★ ${p.rating}</span>
          </div>

          <div class="modal-share-bar">
            <span class="share-title">${t('shareHeader')}</span>
            <button type="button" class="btn-share btn-share-wa" data-share="whatsapp" aria-label="Share WhatsApp">
              💬 WhatsApp
            </button>
            <button type="button" class="btn-share btn-share-tg" data-share="telegram" aria-label="Share Telegram">
              ✈️ Telegram
            </button>
            <button type="button" class="btn-share btn-share-copy" data-share="copy" aria-label="Copy Link">
              🔗 ${t('copyLink')}
            </button>
          </div>

          ${highlightsHtml}
          ${specsHtml}

          <a href="${affUrl}" target="_blank" rel="nofollow sponsored noopener" class="modal-cta-btn" data-aff-id="${p.id}">
            ${t('modalCta')}
          </a>
        </div>
      </div>
    `;

    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    if (pushHash) history.pushState({ p: id }, '', '#' + p.slug);
  }

  function closeModal() {
    const modal = document.getElementById('product-modal');
    if (modal) modal.hidden = true;
    document.body.style.overflow = '';
  }

  // Toast Notification
  function showToast(msg) {
    let toast = document.getElementById('modern-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'modern-toast';
      toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#06b6d4;color:#0b0f19;font-weight:700;padding:10px 24px;border-radius:30px;box-shadow:0 10px 25px rgba(6,182,212,0.4);z-index:99999;font-size:13.5px;transition:opacity 0.25s;';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 2400);
  }

  // Update UI Elements with current language strings
  function applyLanguage() {
    const html = document.documentElement;
    html.lang = STATE.lang;
    html.dir = (STATE.lang === 'he') ? 'rtl' : 'ltr';

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      const text = t(key);
      if (text) el.textContent = text;
    });

    const searchInput = document.getElementById('global-search-input');
    if (searchInput) searchInput.placeholder = t('searchPlaceholder');

    // Update active state on language pills
    document.querySelectorAll('[data-set-lang]').forEach(b => {
      b.classList.toggle('active', b.dataset.setLang === STATE.lang);
    });

    // Update active state on currency pills
    document.querySelectorAll('[data-set-cur]').forEach(b => {
      b.classList.toggle('active', b.dataset.setCur === STATE.cur);
    });

    // Update category pills names
    document.querySelectorAll('.cat-pill').forEach(btn => {
      const catId = btn.dataset.cat;
      if (catId === 'new_today') {
        const nameSpan = btn.querySelector('.cat-label');
        if (nameSpan) nameSpan.textContent = t('newToday');
        return;
      }
      const catObj = CATS.find(c => c.id === catId);
      if (catObj) {
        const nameSpan = btn.querySelector('.cat-label');
        if (nameSpan) nameSpan.textContent = tx(catObj.name_i18n) || catObj.name;
      }
    });

    // Update price segment filter names
    const priceMap = {
      all: 'pAll',
      p1: 'p1',
      p2: 'p2',
      p3: 'p3',
      p4: 'p4'
    };
    document.querySelectorAll('.price-chip').forEach(btn => {
      const code = btn.dataset.price;
      const textKey = priceMap[code];
      if (textKey) btn.textContent = t(textKey);
    });
  }

  // Event Listeners
  function attachListeners() {
    // Language Switcher
    document.addEventListener('click', e => {
      const btn = e.target.closest('[data-set-lang]');
      if (!btn) return;
      STATE.lang = btn.dataset.setLang;
      localStorage.setItem('sp_lang', STATE.lang);
      if (!localStorage.getItem('sp_cur')) {
        STATE.cur = defaultCur(STATE.lang);
        window.SmartPickCurrentCurrency = STATE.cur;
      }
      applyLanguage();
      renderGrid();
    });

    // Currency Switcher
    document.addEventListener('click', e => {
      const btn = e.target.closest('[data-set-cur]');
      if (!btn) return;
      STATE.cur = btn.dataset.setCur;
      localStorage.setItem('sp_cur', STATE.cur);
      window.SmartPickCurrentCurrency = STATE.cur;
      applyLanguage();
      renderGrid();
    });

    // Category Tabs
    const catNav = document.getElementById('category-nav');
    if (catNav) {
      catNav.addEventListener('click', e => {
        const pill = e.target.closest('.cat-pill');
        if (!pill) return;
        document.querySelectorAll('.cat-pill').forEach(b => b.classList.toggle('active', b === pill));
        STATE.cat = pill.dataset.cat;
        renderGrid();
      });
    }

    // Price Segment Chips
    const priceNav = document.getElementById('price-filters');
    if (priceNav) {
      priceNav.addEventListener('click', e => {
        const chip = e.target.closest('.price-chip');
        if (!chip) return;
        document.querySelectorAll('.price-chip').forEach(c => c.classList.toggle('active', c === chip));
        STATE.price = chip.dataset.price;
        renderGrid();
      });
    }

    // Sort Dropdown
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
      sortSelect.addEventListener('change', e => {
        STATE.sort = e.target.value;
        renderGrid();
      });
    }

    // Theme Switcher Button
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        STATE.theme = STATE.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('sp_theme', STATE.theme);
        applyTheme();
      });
    }

    // Search Input
    let searchDebounce;
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', e => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
          STATE.search = e.target.value;
          renderGrid();
        }, 120);
      });
    }

    // Card Click -> Open Modal
    document.addEventListener('click', e => {
      const card = e.target.closest('.product-card');
      if (card && !e.target.closest('.btn-buy-deal')) {
        openModal(card.dataset.id);
        return;
      }

      // Quick View button
      const qv = e.target.closest('[data-modal-id]');
      if (qv) {
        openModal(qv.dataset.modalId);
        return;
      }

      // Outbound affiliate link tracking
      const cta = e.target.closest('[data-aff-id]');
      if (cta) {
        const pId = cta.dataset.affId;
        const prod = P.find(x => x.id === pId);
        if (prod && typeof window.trackAffiliateClick === 'function') {
          window.trackAffiliateClick(prod);
        }
      }

      // Coupon Copy
      const copyBtn = e.target.closest('[data-copy-coupon]');
      if (copyBtn) {
        const code = copyBtn.dataset.copyCoupon || 'AEIL02';
        navigator.clipboard.writeText(code).then(() => {
          showToast(t('couponCopied'));
        });
        return;
      }

      // Modal Share Row Buttons
      const shareBtn = e.target.closest('[data-share]');
      if (shareBtn) {
        const platform = shareBtn.dataset.share;
        const hash = location.hash.slice(1);
        const prod = P.find(x => x.slug === hash) || P[0];
        if (prod && typeof window.shareDeal === 'function') {
          window.shareDeal(platform, prod, STATE.lang);
        }
        return;
      }

      // Modal Close Backdrop or Close Button
      if (e.target.closest('[data-close-modal]')) {
        closeModal();
        if (location.hash) history.back();
      }
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') closeModal();
    });

    window.addEventListener('popstate', () => {
      const hash = location.hash.slice(1);
      const found = P.find(x => x.slug === hash);
      if (found) {
        openModal(found.id, false);
      } else {
        closeModal();
      }
    });
  }

  // Initialize
  applyTheme();
  applyLanguage();
  renderGrid();
  attachListeners();

  // Check URL hash on initial load
  const initHash = location.hash.slice(1);
  if (initHash) {
    const item = P.find(x => x.slug === initHash);
    if (item) openModal(item.id, false);
  }
})();
