(() => {
  const dataElem = document.getElementById('cyber-data');
  if (!dataElem) return;

  const DB = JSON.parse(dataElem.textContent);
  const P = DB.products;
  const $ = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  const RATE = { ILS: 3.7, USD: 1.0, EUR: 0.92 };
  const SYM = { ILS: '₪', USD: '$', EUR: '€' };

  const LANGS = {
    he: 'עברית',
    en: 'English',
    ru: 'Русский',
    ar: 'العربية',
    es: 'Español',
    fr: 'Français',
    de: 'Deutsch'
  };

  const I18N = {
    he: {
      heroTag: 'מטריקס מבצעים // 2077',
      h1: 'גאדג\'טים ופטנטים מהעתיד במחירי השקה',
      sub: 'סריקת מוצרים שימושיים ממיטב היצרנים ברשת. פטור מלא ממכס עד $75 ומשלוח חינם לישראל.',
      badge1: '🚚 משלוח חינם לישראל*',
      badge2: '💸 פטור מלא ממע"מ ומכס (<$75)',
      badge3: '⚡ דילים מאומתים 100%',
      pAll: 'הכל',
      p1: 'עד ₪25',
      p2: '₪25 - ₪50',
      p3: '₪50 - ₪100',
      p4: '₪100 - ₪200',
      chipRate: '⭐ דירוג 4.8+ בלבד',
      chipDisc: '🔥 הנחה 50% ומעלה',
      chipFree: '🚚 משלוח חינם',
      sortAi: '🧠 דירוג AI חכם',
      sortDisc: '🔥 הנחה הגבוהה ביותר',
      sortAsc: '💵 מחיר: מהזול ליקר',
      sortDesc: '💎 מחיר: מהיקר לזול',
      sortRate: '⭐ דירוג קונים',
      searchPlh: 'חיפוש במטריקס: גאדג\'ט, רכב, בית, כלים...',
      itemsFound: 'פריטים פעילים במטריקס',
      noItems: 'לא אותרו פריטים תואמים בסריקה 🛑',
      cta: 'למעבר לדיל ↗',
      viewAction: 'פרטים ורכישה ❯',
      specsHeader: 'מפרט טכני מאומת',
      whyHeader: 'יתרונות בולטים',
      estPrice: 'משוער באתר המוכר',
      directLink: 'קישור ישיר למבצע',
      prefTitleLang: 'שפת ממשק',
      prefTitleCur: 'מטבע תצוגה',
      footerDisc: 'הבהרה משפטית: אתר SmartPick Matrix הינו אתר סקירות והמלצות עצמאי. הקישורים באתר הינם קישורי שותפים (Affiliate Links) — ברכישת מוצר ייתכן שנקבל עמלה ללא כל עלות נוספת עבורכם. המחירים, המשלוח והזמינות נקבעים ומוצגים במלואם באתר המוכר ב-AliExpress. *משלוח חינם בכפוף לתנאי המוכר וליעד המשלוח.',
      cats: {
        all: 'כל המציאות',
        gadgets: 'גאדג׳טים והמצאות כיס',
        auto: 'שדרוגים חכמים לרכב',
        smarthome: 'בית, מטבח ומיקרו-המצאות',
        pets: 'המצאות לחיות מחמד',
        tools: 'כלי עבודה ותיקונים',
        under10: 'מציאות גאוניות עד ₪50'
      }
    },
    en: {
      heroTag: 'DEAL MATRIX // 2077',
      h1: 'Next-Gen Utility Gadgets & Life Innovations',
      sub: 'AI-curated non-saturated problem solvers and smart upgrades with free shipping worldwide.',
      badge1: '🚚 Free Shipping Available*',
      badge2: '💸 Duty-Free under $75',
      badge3: '⚡ 100% Verified Deals',
      pAll: 'All',
      p1: 'Under $8',
      p2: '$8 - $15',
      p3: '$15 - $30',
      p4: '$30 - $60',
      chipRate: '⭐ 4.8+ Rating Only',
      chipDisc: '🔥 50%+ Discount',
      chipFree: '🚚 Free Shipping',
      sortAi: '🧠 AI Cyber Score',
      sortDisc: '🔥 Biggest Discount %',
      sortAsc: '💵 Price: Low to High',
      sortDesc: '💎 Price: High to Low',
      sortRate: '⭐ Customer Rating',
      searchPlh: 'Search Matrix: gadgets, tools, auto, home...',
      itemsFound: 'nodes active in matrix',
      noItems: 'No matching nodes found in scan 🛑',
      cta: 'View Deal ↗',
      viewAction: 'Details & Buy ❯',
      specsHeader: 'Verified Technical Specs',
      whyHeader: 'Key Features',
      estPrice: 'Estimated on seller site',
      directLink: 'Direct seller link',
      prefTitleLang: 'Interface Language',
      prefTitleCur: 'Currency',
      footerDisc: 'Disclosure: SmartPick Matrix is an independent deal curation and review portal. Links are affiliate links — we may earn a commission with zero additional cost to you. Final price, shipping and customs terms are shown on the seller’s site.',
      cats: {
        all: 'All Nodes',
        gadgets: 'Pocket Inventions & EDC',
        auto: 'Smart Car Tech',
        smarthome: 'Smart Home & Kitchen',
        pets: 'Clever Pet Tech',
        tools: 'Precision Tools & Repair',
        under10: 'Sub-$15 Genius Bargains'
      }
    },
    ru: {
      heroTag: 'МАТРИЦА НАХОДОК // 2077',
      h1: 'Гаджеты будущего и умные изобретения',
      sub: 'Отобранные инновации и полезные устройства без таможенных пошлин до $75 с бесплатной доставкой.',
      badge1: '🚚 Бесплатная доставка*',
      badge2: '💸 Без пошлины до $75',
      badge3: '⚡ 100% проверенные сделки',
      pAll: 'Все',
      p1: 'До $8 (~₪25)',
      p2: '$8 - $15 (~₪50)',
      p3: '$15 - $30 (~₪100)',
      p4: '$30 - $60 (~₪200)',
      chipRate: '⭐ Рейтинг 4.8+',
      chipDisc: '🔥 Скидка от 50%',
      chipFree: '🚚 Бесплатная доставка',
      sortAi: '🧠 Рейтинг AI',
      sortDisc: '🔥 Максимальная скидка',
      sortAsc: '💵 Сначала дешевые',
      sortDesc: '💎 Сначала дорогие',
      sortRate: '⭐ По оценкам покупателей',
      searchPlh: 'Поиск: гаджеты, инструменты, авто, дом...',
      itemsFound: 'активных товаров в матрице',
      noItems: 'По вашему запросу ничего не найдено 🛑',
      cta: 'Перейти к сделке ↗',
      viewAction: 'Обзор и заказ ❯',
      specsHeader: 'Технические характеристики',
      whyHeader: 'Главные преимущества',
      estPrice: 'Ориентировочно на сайте продавца',
      directLink: 'Прямая ссылка на товар',
      prefTitleLang: 'Язык интерфейса',
      prefTitleCur: 'Валюта',
      footerDisc: 'Уведомление: SmartPick Matrix — независимый обзорный каталог. Ссылки являются партнерскими — мы можем получать комиссию без переплат с вашей стороны. Итоговая цена, доставка и налоги подтверждаются на сайте продавца в AliExpress.',
      cats: {
        all: 'Все находки',
        gadgets: 'Карманные гаджеты и EDC',
        auto: 'Умные автотовары',
        smarthome: 'Дом, кухня и новинки',
        pets: 'Изобретения для питомцев',
        tools: 'Точный инструмент и ремонт',
        under10: 'Гениальные находки до $15'
      }
    }
  };

  const defCur = l => (l === 'he' ? 'ILS' : ['de', 'fr', 'es'].includes(l) ? 'EUR' : 'USD');
  const S = {
    lang: localStorage.cyber_lang || 'he',
    cur: localStorage.cyber_cur || '',
    cat: 'all',
    price: 'all',
    sort: 'ai',
    q: '',
    minRating48: false,
    minDisc50: false
  };
  if (!S.cur) S.cur = defCur(S.lang);
  window.SmartPickCurrentCurrency = S.cur;

  const t = k => I18N[S.lang]?.[k] ?? I18N.en[k] ?? '';
  const tx = o => (o ? (o[S.lang] || o.en || o.he || '') : '');
  const money = u => {
    const v = u * RATE[S.cur];
    return S.cur === 'ILS' ? '₪' + Math.round(v) : SYM[S.cur] + v.toFixed(2);
  };
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  const PRICE_RANGES = {
    'all': [0, 9999],
    'p1': [0, 25],
    'p2': [25, 50],
    'p3': [50, 100],
    'p4': [100, 300]
  };

  // Card HTML template
  function renderCard(p, idx) {
    const title = esc(tx(p.title));
    const disc = p.discount_pct ? `<span class="cyber-tag-off">-${p.discount_pct}%</span>` : '';
    const rating = `<span class="cyber-hud-rating">★ ${p.rating}</span>`;
    const oldPrice = p.old_price_usd > p.price_usd ? `<span class="cyber-old-price">${money(p.old_price_usd)}</span>` : '';

    return `
      <div class="cyber-card" data-id="${p.id}" tabindex="0" role="button" aria-label="${title}">
        <div class="card-visual">
          <img src="${p.image}" alt="${title}" width="400" height="400" loading="${idx < 6 ? 'eager' : 'lazy'}" decoding="async">
          ${disc}
          ${rating}
        </div>
        <div class="card-content">
          <h3 class="card-headline">${title}</h3>
          <div class="price-box">
            <span class="cyber-price">${money(p.price_usd)}</span>
            ${oldPrice}
          </div>
          <div class="card-footer-meta">
            <span class="ship-badge">🚚 משלוח חינם*</span>
            <span class="action-arrow">${t('viewAction')}</span>
          </div>
        </div>
      </div>
    `;
  }

  // Filter & sort logic
  function filterProducts() {
    const q = S.q.trim().toLowerCase();
    const [minIls, maxIls] = PRICE_RANGES[S.price] || [0, 9999];

    let result = P.filter(p => {
      // Category
      if (S.cat !== 'all' && p.category !== S.cat) return false;
      // Price
      const ils = p.price_usd * 3.7;
      if (ils < minIls || ils >= maxIls) return false;
      // Rating filter
      if (S.minRating48 && Number(p.rating) < 4.8) return false;
      // Discount filter
      if (S.minDisc50 && Number(p.discount_pct || 0) < 50) return false;
      // Search keyword
      if (q) {
        const fullText = [Object.values(p.title || {}), p.highlights || []].flat().join(' ').toLowerCase();
        if (!fullText.includes(q)) return false;
      }
      return true;
    });

    // Sorting
    const sortFn = {
      ai: (a, b) => (b.pop * (b.rating / 5)) - (a.pop * (a.rating / 5)),
      disc: (a, b) => (b.discount_pct || 0) - (a.discount_pct || 0),
      asc: (a, b) => a.price_usd - b.price_usd,
      desc: (a, b) => b.price_usd - a.price_usd,
      rate: (a, b) => b.rating - a.rating || b.reviews_count - a.reviews_count
    }[S.sort] || ((a, b) => b.pop - a.pop);

    return result.sort(sortFn);
  }

  function renderGrid() {
    const list = filterProducts();
    const grid = $('#cyber-grid');
    if (!grid) return;

    if (list.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; font-size: 16px; color: var(--cyan);">${t('noItems')}</div>`;
    } else {
      grid.innerHTML = list.map((p, i) => renderCard(p, i)).join('');
    }

    const counter = $('#matrix-count');
    if (counter) {
      counter.innerHTML = `<span class="hud-pulse"></span> <b>${list.length}</b> ${t('itemsFound')}`;
    }

    attachCardTilt();
  }

  // 3D Parallax Tilt with Holographic Glare
  function attachCardTilt() {
    if (!window.matchMedia('(hover: hover)').matches) return;

    $$('.cyber-card').forEach(card => {
      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = ((y - centerY) / centerY) * -9;
        const rotateY = ((x - centerX) / centerX) * 9;

        card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.02, 1.02, 1.02)`;
        card.style.setProperty('--mouse-x', `${(x / rect.width * 100).toFixed(1)}%`);
        card.style.setProperty('--mouse-y', `${(y / rect.height * 100).toFixed(1)}%`);
      }, { passive: true });

      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
      }, { passive: true });
    });
  }

  // Interactive Cursor Aura
  function initCursorAura() {
    if (!window.matchMedia('(hover: hover)').matches) return;
    const cursor = document.createElement('div');
    cursor.className = 'cyber-glow-cursor';
    document.body.appendChild(cursor);

    let mouseX = -1000, mouseY = -1000;
    let curX = -1000, curY = -1000;

    window.addEventListener('mousemove', e => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    }, { passive: true });

    function animateCursor() {
      curX += (mouseX - curX) * 0.15;
      curY += (mouseY - curY) * 0.15;
      cursor.style.left = `${curX}px`;
      cursor.style.top = `${curY}px`;
      requestAnimationFrame(animateCursor);
    }
    requestAnimationFrame(animateCursor);
  }

  // Open Hologram Modal Dossier
  function openModal(id, push = true) {
    const p = P.find(x => x.id === id);
    if (!p) return;

    const modal = $('#cyber-modal');
    const body = $('#modal-dossier-body');
    if (!modal || !body) return;

    const gallery = p.gallery && p.gallery.length ? p.gallery : [p.image];
    const specsEntries = p.specs ? Object.entries(p.specs) : [];

    const specsTable = specsEntries.length ? `
      <div class="specs-terminal">
        <h4 style="color: var(--cyan); margin-bottom: 8px; font-size: 13px;">// ${t('specsHeader')}</h4>
        <table class="specs-table">
          <tbody>
            ${specsEntries.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}
          </tbody>
        </table>
      </div>
    ` : '';

    const highlightsList = (p.highlights && S.lang === 'he') ? `
      <div style="margin: 16px 0;">
        <h4 style="color: #fff; margin-bottom: 10px; font-size: 14px;">⚡ ${t('whyHeader')}</h4>
        <ul style="list-style: none; display: grid; gap: 8px;">
          ${p.highlights.map(h => `<li style="font-size: 13.5px; color: #cbd5e1; display: flex; gap: 8px;"><span style="color: var(--green); font-weight: bold;">✔</span> ${esc(h)}</li>`).join('')}
        </ul>
      </div>
    ` : `<p style="color: var(--text-muted); font-size: 14px; margin: 12px 0;">${esc(tx(p.short_desc))}</p>`;

    body.innerHTML = `
      <div class="modal-content-grid">
        <div class="modal-gallery">
          <div class="modal-slider" id="modal-slider">
            ${gallery.map(img => `<img src="${img}" alt="" width="600" height="600" decoding="async">`).join('')}
          </div>
          <div class="modal-dots" id="modal-dots">
            ${gallery.map((_, i) => `<i class="${i === 0 ? 'active' : ''}"></i>`).join('')}
          </div>
        </div>
        <div class="modal-details">
          ${p.discount_pct ? `<span class="cyber-tag-off" style="position: static; display: inline-block; margin-bottom: 8px;">-${p.discount_pct}% OFF</span>` : ''}
          <h2 class="modal-h3">${esc(tx(p.title))}</h2>
          <div class="modal-price-row">
            <span class="modal-price">${money(p.price_usd)}</span>
            ${p.old_price_usd > p.price_usd ? `<s class="cyber-old-price" style="font-size: 16px;">${money(p.old_price_usd)}</s>` : ''}
            <span style="color: var(--gold); font-size: 14px; font-weight: bold; margin-inline-start: auto;">★ ${p.rating}</span>
          </div>
          <div class="modal-perks">
            <span class="modal-perk-tag">🚚 משלוח חינם לישראל*</span>
            <span class="modal-perk-tag" style="color: var(--cyan); border-color: rgba(0, 240, 255, 0.3);">💸 פטור ממע"מ (<$75)</span>
            <span class="modal-perk-tag" style="color: var(--gold); border-color: rgba(255, 210, 0, 0.3);">⚡ דיל אונליין מאומת</span>
          </div>
          ${highlightsList}
          ${specsTable}

          <div class="modal-share-row">
            <span class="share-label">${S.lang === 'he' ? 'שיתוף מהיר:' : (S.lang === 'ru' ? 'Поделиться:' : 'Share:')}</span>
            <button type="button" class="share-btn share-btn-wa" data-share="whatsapp" aria-label="Share on WhatsApp">
              <span>💬 WhatsApp</span>
            </button>
            <button type="button" class="share-btn share-btn-tg" data-share="telegram" aria-label="Share on Telegram">
              <span>✈️ Telegram</span>
            </button>
            <button type="button" class="share-btn share-btn-copy" data-share="copy" aria-label="Copy Link">
              <span>🔗 ${S.lang === 'he' ? 'העתקת קישור' : (S.lang === 'ru' ? 'Копировать' : 'Copy Link')}</span>
            </button>
          </div>
        </div>
      </div>
      <div class="modal-bottom-bar">
        <div>
          <b style="font-family: var(--font-mono); font-size: 22px; color: var(--cyan);">${money(p.price_usd)}</b>
          <small style="display: block; font-size: 11px; color: var(--text-muted);">${t('estPrice')}</small>
        </div>
        <a class="cta-cyber-button" data-aff-id="${p.id}" href="${esc(window.decorateAffiliateUrl ? window.decorateAffiliateUrl(p.affiliate_url, p.id) : p.affiliate_url)}" target="_blank" rel="nofollow sponsored noopener">
          <span>${t('cta')}</span>
        </a>
      </div>
    `;

    // Slider sync
    const slider = $('#modal-slider');
    const dots = $$('#modal-dots i');
    slider.addEventListener('scroll', () => {
      const idx = Math.round(Math.abs(slider.scrollLeft) / slider.clientWidth);
      dots.forEach((dot, j) => dot.classList.toggle('active', j === idx));
    }, { passive: true });

    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    if (push) history.pushState({ p: id }, '', '#' + p.slug);
  }

  function closeModal() {
    const modal = $('#cyber-modal');
    if (modal) modal.hidden = true;
    const prefModal = $('#cyber-pref-modal');
    if (prefModal) prefModal.hidden = true;
    document.body.style.overflow = '';
  }

  // Language & Currency Sheet
  function openPrefsModal() {
    const modal = $('#cyber-pref-modal');
    const body = $('#pref-modal-body');
    if (!modal || !body) return;

    body.innerHTML = `
      <div style="padding: 24px;">
        <h4 style="color: var(--cyan); margin-bottom: 12px; font-family: var(--font-mono); font-size: 13px;">// ${t('prefTitleLang')}</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 22px;">
          ${Object.entries(LANGS).map(([k, v]) => `
            <button class="price-btn ${k === S.lang ? 'active' : ''}" data-lang="${k}" style="height: 42px; border: 1px solid var(--border-neon);">
              ${v}
            </button>
          `).join('')}
        </div>
        <h4 style="color: var(--cyan); margin-bottom: 12px; font-family: var(--font-mono); font-size: 13px;">// ${t('prefTitleCur')}</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
          ${Object.keys(RATE).map(c => `
            <button class="price-btn ${c === S.cur ? 'active' : ''}" data-cur="${c}" style="height: 42px; border: 1px solid var(--border-neon);">
              ${SYM[c]} ${c}
            </button>
          `).join('')}
        </div>
      </div>
    `;

    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  // Update i18n text everywhere
  function applyI18n() {
    const h = document.documentElement;
    h.lang = S.lang;
    h.dir = (S.lang === 'he' || S.lang === 'ar') ? 'rtl' : 'ltr';

    $$('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      const text = t(key);
      if (text) el.textContent = text;
    });

    const searchInput = $('#cyber-search-input');
    if (searchInput) searchInput.placeholder = t('searchPlh');

    const prefLbl = $('#pref-btn-label');
    if (prefLbl) prefLbl.textContent = `${S.lang.toUpperCase()} · ${SYM[S.cur]}`;

    // Update Category Pills
    $$('.cyber-cat-pill').forEach(btn => {
      const id = btn.dataset.cat;
      const count = id === 'all' ? P.length : P.filter(x => x.category === id).length;
      const catName = t('cats')?.[id] || id;
      const nameSpan = btn.querySelector('.cat-label');
      const countSpan = btn.querySelector('.cat-badge');
      if (nameSpan) nameSpan.textContent = catName;
      if (countSpan) countSpan.textContent = count;
    });
  }

  // Global Event Listeners
  function attachEvents() {
    // Card clicks
    $('#cyber-grid')?.addEventListener('click', e => {
      const card = e.target.closest('.cyber-card');
      if (!card || e.metaKey || e.ctrlKey) return;
      openModal(card.dataset.id);
    });

    // Enter key on card
    $('#cyber-grid')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const card = e.target.closest('.cyber-card');
        if (card) openModal(card.dataset.id);
      }
    });

    // Category navigation
    $('#cyber-nav')?.addEventListener('click', e => {
      const pill = e.target.closest('.cyber-cat-pill');
      if (!pill) return;
      $$('.cyber-cat-pill').forEach(b => b.classList.toggle('active', b === pill));
      pill.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' });
      S.cat = pill.dataset.cat;
      renderGrid();
    });

    // Price segment buttons
    $('#price-segment')?.addEventListener('click', e => {
      const btn = e.target.closest('.price-btn');
      if (!btn) return;
      $$('#price-segment .price-btn').forEach(b => b.classList.toggle('active', b === btn));
      S.price = btn.dataset.price;
      renderGrid();
    });

    // Toggle chips (Rating 4.8+, Discount 50%+)
    $('#toggle-chips')?.addEventListener('click', e => {
      const chip = e.target.closest('.toggle-chip');
      if (!chip) return;
      chip.classList.toggle('active');
      if (chip.dataset.toggle === 'rate48') S.minRating48 = chip.classList.contains('active');
      if (chip.dataset.toggle === 'disc50') S.minDisc50 = chip.classList.contains('active');
      renderGrid();
    });

    // Sort select
    $('#matrix-sort-select')?.addEventListener('change', e => {
      S.sort = e.target.value;
      renderGrid();
    });

    // Search input
    let searchDebounce;
    $('#cyber-search-input')?.addEventListener('input', e => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        S.q = e.target.value;
        renderGrid();
      }, 140);
    });

    // Prefs button
    $('#cyber-pref-btn')?.addEventListener('click', openPrefsModal);
    $('#pref-modal-body')?.addEventListener('click', e => {
      const btn = e.target.closest('button');
      if (!btn) return;
      if (btn.dataset.lang) {
        S.lang = localStorage.cyber_lang = btn.dataset.lang;
        if (!localStorage.cyber_cur) S.cur = defCur(S.lang);
      }
      if (btn.dataset.cur) {
        S.cur = localStorage.cyber_cur = btn.dataset.cur;
        window.SmartPickCurrentCurrency = S.cur;
      }
      applyI18n();
      renderGrid();
      openPrefsModal();
    });

    // Affiliate outbound click attribution
    document.addEventListener('click', e => {
      const cta = e.target.closest('.cta-cyber-button');
      if (cta) {
        const pId = cta.dataset.affId;
        const prod = P.find(x => x.id === pId);
        if (prod && typeof window.trackAffiliateClick === 'function') {
          window.trackAffiliateClick(prod);
        }
      }
    });

    // Modal quick share actions
    document.addEventListener('click', e => {
      const shareBtn = e.target.closest('[data-share]');
      if (shareBtn) {
        const platform = shareBtn.dataset.share;
        const hash = location.hash.slice(1);
        const prod = P.find(x => x.slug === hash) || P[0];
        if (prod && typeof window.shareDeal === 'function') {
          window.shareDeal(platform, prod, S.lang);
        }
      }
    });

    // Copy coupon code HUD action
    document.addEventListener('click', e => {
      const cBtn = e.target.closest('[data-copy-coupon]');
      if (!cBtn) return;
      const code = cBtn.dataset.copyCoupon || 'AEIL02';
      navigator.clipboard.writeText(code).then(() => {
        if (typeof window.showShareToast === 'function') {
          const msg = S.lang === 'he' ? `קוד קופון ${code} הועתק! ✂️` : (S.lang === 'ru' ? `Купон ${code} скопирован! ✂️` : `Coupon ${code} copied! ✂️`);
          window.showShareToast(msg);
        }
      });
    });

    // Modal Close
    document.addEventListener('click', e => {
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
  initCursorAura();
  applyI18n();
  renderGrid();
  attachEvents();

  // Check URL hash on load
  const initHash = location.hash.slice(1);
  if (initHash) {
    const item = P.find(x => x.slug === initHash);
    if (item) openModal(item.id, false);
  }
})();
