(() => {
  const D = JSON.parse(document.getElementById('data').textContent);
  const P = D.products;
  const $ = s => document.querySelector(s);
  document.documentElement.classList.add('js');

  const RATE = { ILS: 3.7, USD: 1, EUR: 0.92 };
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

  const T = {
    he: {
      kicker: '✨ מבחר מוצרים מומלצים',
      h1: 'מציאות שימושיות במחירים משתלמים',
      sub: 'סקירת גאדג\'טים וחידושים לבית, לרכב ולחיים עם קישור ישיר לעמוד המוצר',
      t1: '🚚 משלוח חינם לישראל*',
      t2: '💸 פטור ממע"מ בהזמנות עד $75',
      t3: '🔗 קישור ישיר לעמוד המוכר',
      pAll: 'הכל',
      upTo: 'עד',
      sort: 'מיון',
      sPop: 'פופולרי',
      sDisc: 'הנחה גבוהה',
      sAsc: 'מחיר: נמוך לגבוה',
      sDesc: 'מחיר: גבוה לנמוך',
      sRate: 'דירוג',
      empty: 'לא נמצאו מוצרים 🙈',
      q: 'חיפוש מוצרים...',
      sold: 'נמכרו',
      ship: 'משלוח חינם*',
      items: 'מוצרים',
      why: 'מאפיינים עיקריים',
      spec: 'מפרט טכני',
      cta: 'למעבר לדיל ↗',
      reviews: 'ביקורות',
      lang: 'שפה',
      cur: 'מטבע',
      vat: '💸 פטור ממע"מ (מתחת ל-$75)',
      direct: '🔗 קישור ישיר למוכר',
      shipIL: '🚚 משלוח חינם לישראל*',
      disc: 'SmartPick הינו אתר סקירות והמלצות עצמאי ואינו קשור לחברת AliExpress. הקישורים באתר הם קישורי שותפים — ייתכן שנקבל עמלה ללא עלות נוספת עבורכם. המחירים המוצגים משוערים ועשויים להשתנות; המחיר, המשלוח והמס הסופיים מוצגים באתר המוכר ב-AliExpress. *משלוח חינם בכפוף לתנאי המוכר וכתובת המשלוח.',
      cats: {
        all: 'הכל',
        gadgets: 'גאדג׳טים',
        auto: 'לרכב',
        smarthome: 'בית ומטבח',
        pets: 'חיות מחמד',
        tools: 'כלי עבודה',
        under10: 'עד ₪50'
      }
    },
    en: {
      kicker: '✨ Recommended Picks',
      h1: 'Smart Products at Friendly Prices',
      sub: 'Curated useful gadgets, car upgrades and home innovations with direct seller links',
      t1: '🚚 Free Shipping*',
      t2: '💸 Duty-Free under $75',
      t3: '🔗 Direct Seller Link',
      pAll: 'All',
      upTo: 'Up to',
      sort: 'Sort',
      sPop: 'Popular',
      sDisc: 'Biggest Discount',
      sAsc: 'Price: Low to High',
      sDesc: 'Price: High to Low',
      sRate: 'Rating',
      empty: 'No products found 🙈',
      q: 'Search products...',
      sold: 'sold',
      ship: 'Free shipping*',
      items: 'items',
      why: 'Key Features',
      spec: 'Specifications',
      cta: 'View Deal ↗',
      reviews: 'reviews',
      lang: 'Language',
      cur: 'Currency',
      vat: '💸 VAT-Free (under $75)',
      direct: '🔗 Direct link to seller',
      shipIL: '🚚 Free Shipping*',
      disc: 'SmartPick is an independent review site and is not affiliated with AliExpress. Links are affiliate links — we may earn a commission at no additional cost to you. Displayed prices are approximate and subject to change; final price, shipping and taxes are displayed on the seller’s site.',
      cats: {
        all: 'All',
        gadgets: 'Gadgets',
        auto: 'Car Tech',
        smarthome: 'Home & Kitchen',
        pets: 'Pet Care',
        tools: 'Tools & Fix',
        under10: 'Under $15'
      }
    },
    ru: {
      kicker: '✨ Рекомендуемая подборка',
      h1: 'Умные товары по доступным ценам',
      sub: 'Полезные гаджеты и новинки для дома и авто с прямыми ссылками на товар',
      t1: '🚚 Бесплатная доставка*',
      t2: '💸 Без пошлины до $75',
      t3: '🔗 Прямая ссылка на продавца',
      pAll: 'Все',
      upTo: 'До',
      sort: 'Сортировка',
      sPop: 'Популярные',
      sDisc: 'Большая скидка',
      sAsc: 'Сначала дешёвые',
      sDesc: 'Сначала дорогие',
      sRate: 'Рейтинг',
      empty: 'Ничего не найдено 🙈',
      q: 'Поиск товаров...',
      sold: 'продано',
      ship: 'Бесплатная доставка*',
      items: 'товаров',
      why: 'Главные особенности',
      spec: 'Характеристики',
      cta: 'Перейти к сделке ↗',
      reviews: 'отзывов',
      lang: 'Язык',
      cur: 'Валюта',
      vat: '💸 Без пошлины (до $75)',
      direct: '🔗 Прямая ссылка на товар',
      shipIL: '🚚 Бесплатная доставка*',
      disc: 'SmartPick — независимый обзорный сайт, не связанный с AliExpress. Ссылки являются партнёрскими — мы можем получать комиссию без доплаты с вашей стороны. Цены ориентировочные; итоговая стоимость, доставка и налоги отображаются на сайте продавца.',
      cats: {
        all: 'Все',
        gadgets: 'Гаджеты',
        auto: 'Для авто',
        smarthome: 'Дом и кухня',
        pets: 'Питомцы',
        tools: 'Инструменты',
        under10: 'До $15'
      }
    },
    ar: {
      kicker: '✨ اختيارات موصى بها',
      h1: 'منتجات ذكية بأسعار مناسبة',
      sub: 'أحدث الابتكارات المفيدة للمنزل والسيارة مع رابط مباشر لصفحة البائع',
      t1: '🚚 شحن مجاني*',
      t2: '💸 معفى من الجمارك حتى $75',
      t3: '🔗 رابط مباشر للبائع',
      pAll: 'الكل',
      upTo: 'حتى',
      sort: 'ترتيب',
      sPop: 'الأكثر شعبية',
      sDisc: 'أكبر خصم',
      sAsc: 'السعر: من الأقل',
      sDesc: 'السعر: من الأعلى',
      sRate: 'التقييم',
      empty: 'لا توجد منتجات 🙈',
      q: 'ابحث عن منتجات...',
      sold: 'مباع',
      ship: 'شحن مجاني*',
      items: 'منتج',
      why: 'أهم الميزات',
      spec: 'المواصفات',
      cta: 'عرض الصفقة ↗',
      reviews: 'تقييم',
      lang: 'اللغة',
      cur: 'العملة',
      vat: '💸 بدون ضرائب (حتى $75)',
      direct: '🔗 رابط مباشر للبائع',
      shipIL: '🚚 شحن مجاني*',
      disc: 'SmartPick موقع مستقل للمراجعات والتوصيات. الروابط تابعة وقد نحصل على عمولة دون أي تكلفة إضافية عليك. الأسعار تقريبية ويتم تحديد السعر والشحن النهائي على موقع البائع.',
      cats: {
        all: 'الكل',
        gadgets: 'أدوات ذكية',
        auto: 'للسيارة',
        smarthome: 'المنزل والمطبخ',
        pets: 'الحيوانات الأليفة',
        tools: 'عدد',
        under10: 'أقل من $15'
      }
    },
    es: {
      kicker: '✨ Selección recomendada',
      h1: 'Productos ingeniosos a buen precio',
      sub: 'Gadgets prácticos para el hogar y el coche con enlace directo al vendedor',
      t1: '🚚 Envío gratis*',
      t2: '💸 Sin aduanas hasta $75',
      t3: '🔗 Enlace directo al vendedor',
      pAll: 'Todo',
      upTo: 'Hasta',
      sort: 'Ordenar',
      sPop: 'Popular',
      sDisc: 'Mayor descuento',
      sAsc: 'Precio: menor a mayor',
      sDesc: 'Precio: mayor a menor',
      sRate: 'Valoración',
      empty: 'Sin resultados 🙈',
      q: 'Buscar productos...',
      sold: 'vendidos',
      ship: 'Envío gratis*',
      items: 'productos',
      why: 'Características destacadas',
      spec: 'Especificaciones',
      cta: 'Ver oferta ↗',
      reviews: 'reseñas',
      lang: 'Idioma',
      cur: 'Moneda',
      vat: '💸 Sin impuestos (<$75)',
      direct: '🔗 Enlace directo al vendedor',
      shipIL: '🚚 Envío gratis*',
      disc: 'SmartPick es un sitio independiente no afiliado a AliExpress. Los enlaces son de afiliado: podemos recibir una comisión sin coste adicional para ti. Los precios finales se confirman en el sitio del vendedor.',
      cats: {
        all: 'Todo',
        gadgets: 'Gadgets',
        auto: 'Coche',
        smarthome: 'Hogar y cocina',
        pets: 'Mascotas',
        tools: 'Herramientas',
        under10: 'Menos de 15€'
      }
    },
    fr: {
      kicker: '✨ Sélection recommandée',
      h1: 'Produits malins à prix doux',
      sub: 'Innovations utiles pour la maison et l\'auto avec lien direct vers le vendeur',
      t1: '🚚 Livraison gratuite*',
      t2: '💸 Sans douane jusqu\'à 75$',
      t3: '🔗 Lien direct vendeur',
      pAll: 'Tout',
      upTo: 'Jusqu’à',
      sort: 'Trier',
      sPop: 'Populaire',
      sDisc: 'Plus grosse remise',
      sAsc: 'Prix croissant',
      sDesc: 'Prix décroissant',
      sRate: 'Note',
      empty: 'Aucun produit 🙈',
      q: 'Rechercher...',
      sold: 'vendus',
      ship: 'Livraison gratuite*',
      items: 'produits',
      why: 'Points forts',
      spec: 'Caractéristiques',
      cta: 'Voir l\'offre ↗',
      reviews: 'avis',
      lang: 'Langue',
      cur: 'Devise',
      vat: '💸 Sans taxe (<75$)',
      direct: '🔗 Lien direct vendeur',
      shipIL: '🚚 Livraison gratuite*',
      disc: 'SmartPick est un site de recommandations indépendant. Liens affiliés : nous pouvons percevoir une commission sans surcoût pour vous. Les prix finaux sont affichés sur le site du vendeur.',
      cats: {
        all: 'Tout',
        gadgets: 'Gadgets',
        auto: 'Auto',
        smarthome: 'Maison & cuisine',
        pets: 'Animaux',
        tools: 'Outils',
        under10: 'Moins de 15€'
      }
    },
    de: {
      kicker: '✨ Empfohlene Auswahl',
      h1: 'Clevere Produkte zu fairen Preisen',
      sub: 'Nützliche Gadgets für Haushalt und Auto mit direktem Link zur Artikelseite',
      t1: '🚚 Gratis Versand*',
      t2: '💸 Zollfrei bis $75',
      t3: '🔗 Direkter Händler-Link',
      pAll: 'Alle',
      upTo: 'Bis',
      sort: 'Sortieren',
      sPop: 'Beliebt',
      sDisc: 'Größter Rabatt',
      sAsc: 'Preis aufsteigend',
      sDesc: 'Preis absteigend',
      sRate: 'Bewertung',
      empty: 'Keine Produkte 🙈',
      q: 'Produkte suchen...',
      sold: 'verkauft',
      ship: 'Gratis Versand*',
      items: 'Produkte',
      why: 'Hauptmerkmale',
      spec: 'Technische Daten',
      cta: 'Zum Angebot ↗',
      reviews: 'Bewertungen',
      lang: 'Sprache',
      cur: 'Währung',
      vat: '💸 Zollfrei (<$75)',
      direct: '🔗 Direkter Händler-Link',
      shipIL: '🚚 Gratis Versand*',
      disc: 'SmartPick ist eine unabhängige Empfehlungsseite. Affiliate-Links: Wir erhalten ggf. eine Provision ohne Mehrkosten für dich. Endpreise und Versandbedingungen werden auf der Händlerseite angezeigt.',
      cats: {
        all: 'Alle',
        gadgets: 'Gadgets',
        auto: 'Auto',
        smarthome: 'Haus & Küche',
        pets: 'Haustiere',
        tools: 'Werkzeug',
        under10: 'Unter 15€'
      }
    }
  };

  const defCur = l => (l === 'he' ? 'ILS' : ['de', 'fr', 'es'].includes(l) ? 'EUR' : 'USD');
  const S = {
    lang: localStorage.lang || 'he',
    cur: localStorage.cur || '',
    cat: 'all',
    price: 'all',
    sort: 'pop',
    q: ''
  };
  if (!S.cur) S.cur = defCur(S.lang);

  const t = k => T[S.lang]?.[k] ?? T.en[k] ?? '';
  const tx = o => (o ? (o[S.lang] || o.en || o.he || '') : '');
  const money = u => {
    const v = u * RATE[S.cur];
    return S.cur === 'ILS' ? '₪' + Math.round(v) : SYM[S.cur] + v.toFixed(2);
  };
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const BANDS = { '0-50': [0, 50], '50-100': [50, 100], '100-300': [100, 300] };

  function card(p, i) {
    return `<a class="card" href="deals/${p.slug}.html" data-id="${p.id}" style="--i:${i % 8}">
      <div class="card-media">
        <img src="${p.image}" alt="${esc(tx(p.title))}" width="400" height="400" ${i < 4 ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async">
        ${p.discount_pct ? `<span class="tag-off">-${p.discount_pct}%</span>` : ''}
      </div>
      <div class="card-body">
        <h3 class="card-title">${esc(tx(p.title))}</h3>
        <div class="price-row">
          <b class="price">${money(p.price_usd)}</b>
          ${p.old_price_usd > p.price_usd ? `<s class="old">${money(p.old_price_usd)}</s>` : ''}
        </div>
        <div class="meta">
          <span class="star">★ ${p.rating}</span>
          <span class="ship">${t('ship')}</span>
        </div>
      </div>
    </a>`;
  }

  function list() {
    const q = S.q.trim().toLowerCase();
    let r = P.filter(p => {
      const matchCat = S.cat === 'all' || p.category === S.cat;
      const ils = p.price_usd * 3.7;
      const matchPrice = S.price === 'all' || (ils >= BANDS[S.price][0] && ils < BANDS[S.price][1]);
      const matchQ = !q || [Object.values(p.title || {}), p.highlights || []].flat().join(' ').toLowerCase().includes(q);
      return matchCat && matchPrice && matchQ;
    });

    const f = {
      pop: (a, b) => b.pop - a.pop,
      disc: (a, b) => (b.discount_pct || 0) - (a.discount_pct || 0),
      asc: (a, b) => a.price_usd - b.price_usd,
      desc: (a, b) => b.price_usd - a.price_usd,
      rate: (a, b) => b.rating - a.rating || b.reviews_count - a.reviews_count
    }[S.sort];
    return r.sort(f);
  }

  function render() {
    const r = list(), g = $('#grid');
    g.innerHTML = r.map(card).join('');
    $('#empty').hidden = r.length > 0;
    $('#count').textContent = `${r.length} ${t('items')}`;
  }

  function i18n() {
    const h = document.documentElement;
    h.lang = S.lang;
    h.dir = (S.lang === 'he' || S.lang === 'ar') ? 'rtl' : 'ltr';
    document.querySelectorAll('[data-t]').forEach(n => {
      const val = t(n.dataset.t);
      if (val) n.textContent = val;
    });
    $('#q').placeholder = t('q');
    $('#prefLbl').textContent = `${S.lang.toUpperCase()} · ${SYM[S.cur]}`;
    document.querySelectorAll('.cat').forEach(b => {
      const id = b.dataset.cat;
      const n = id === 'all' ? P.length : P.filter(p => p.category === id).length;
      b.querySelector('.cat-name').innerHTML = `${esc(t('cats')[id] || id)} <span class="n">${n}</span>`;
    });
    document.querySelectorAll('#price [data-p]').forEach(b => {
      if (b.dataset.p === 'all') return;
      const [a, z] = BANDS[b.dataset.p];
      const m = v => money(v / 3.7).replace(/\.\d+$/, '');
      b.textContent = a === 0 ? `${t('upTo')} ${m(z)}` : `${m(a)}–${m(z)}`;
    });
  }

  function open(id, push = true) {
    const p = P.find(x => x.id === id);
    if (!p) return;
    const g = p.gallery && p.gallery.length ? p.gallery : [p.image];
    const sp = p.specs
      ? Object.entries(p.specs).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')
      : '';

    $('#sheetBody').innerHTML = `
      <div class="gal">
        <div class="gal-track">${g.map((s, i) => `<img src="${s}" alt="" width="600" height="600" ${i ? 'loading="lazy"' : ''} decoding="async">`).join('')}</div>
        <div class="dots">${g.map((_, i) => `<i${i ? '' : ' class="on"'}></i>`).join('')}</div>
      </div>
      <div class="pd-info">
        ${p.discount_pct ? `<span class="pill-off">-${p.discount_pct}%</span>` : ''}
        <h3>${esc(tx(p.title))}</h3>
        <div class="price-row big">
          <b class="price">${money(p.price_usd)}</b>
          ${p.old_price_usd > p.price_usd ? `<s class="old">${money(p.old_price_usd)}</s>` : ''}
        </div>
        <div class="meta" style="margin: 8px 0 12px;">
          <span class="star">★ ${p.rating}</span>
          <span class="ship">${t('shipIL')}</span>
        </div>
        <div class="perks">
          <span>${t('shipIL')}</span>
          <span>${t('vat')}</span>
          <span>${t('direct')}</span>
        </div>
        ${p.highlights && S.lang === 'he' ? `<h2>${t('why')}</h2><ul class="hl">${p.highlights.map(h => `<li>${esc(h)}</li>`).join('')}</ul>` : `<p style="margin-top:12px">${esc(tx(p.short_desc))}</p>`}
        ${sp ? `<h2>${t('spec')}</h2><table class="specs">${sp}</table>` : ''}
      </div>
      <div class="buybar">
        <div>
          <b>${money(p.price_usd)}</b>
          <small>משוער באתר המוכר</small>
        </div>
        <a class="cta" href="${esc(p.affiliate_url)}" target="_blank" rel="nofollow sponsored noopener">
          ${t('cta')}
        </a>
      </div>
    `;

    const tr = $('#sheetBody .gal-track');
    const d = [...document.querySelectorAll('#sheetBody .dots i')];
    tr.addEventListener('scroll', () => {
      const i = Math.round(Math.abs(tr.scrollLeft) / tr.clientWidth);
      d.forEach((x, j) => x.classList.toggle('on', j === i));
    }, { passive: true });

    show('#sheet');
    $('#sheet .sheet-card').scrollTop = 0;
    if (push) history.pushState({ p: id }, '', '#' + p.slug);
  }

  function show(s) {
    $(s).hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function hide() {
    document.querySelectorAll('.sheet').forEach(s => (s.hidden = true));
    document.body.style.overflow = '';
  }

  function prefs() {
    $('#prefsBody').innerHTML = `
      <div class="prefs">
        <h4>${t('lang')}</h4>
        <div class="opts">
          ${Object.entries(LANGS).map(([k, v]) => `<button data-l="${k}" class="${k === S.lang ? 'on' : ''}">${v}</button>`).join('')}
        </div>
        <h4>${t('cur')}</h4>
        <div class="opts">
          ${Object.keys(RATE).map(c => `<button data-c="${c}" class="${c === S.cur ? 'on' : ''}">${SYM[c]} ${c}</button>`).join('')}
        </div>
      </div>
    `;
    show('#prefs');
  }

  // Events
  $('#grid').addEventListener('click', e => {
    const c = e.target.closest('.card');
    if (!c || e.metaKey || e.ctrlKey) return;
    e.preventDefault();
    open(c.dataset.id);
  });

  $('#cats').addEventListener('click', e => {
    const b = e.target.closest('.cat');
    if (!b) return;
    document.querySelectorAll('.cat').forEach(x => x.classList.toggle('on', x === b));
    b.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' });
    S.cat = b.dataset.cat;
    render();
  });

  $('#price').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    document.querySelectorAll('#price button').forEach(x => x.classList.toggle('on', x === b));
    S.price = b.dataset.p;
    render();
  });

  $('#sort').addEventListener('change', e => {
    S.sort = e.target.value;
    render();
  });

  let qt;
  $('#q').addEventListener('input', e => {
    clearTimeout(qt);
    qt = setTimeout(() => {
      S.q = e.target.value;
      render();
    }, 120);
  });

  $('#prefBtn').addEventListener('click', prefs);
  $('#prefsBody').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.l) {
      S.lang = localStorage.lang = b.dataset.l;
      if (!localStorage.cur) S.cur = defCur(S.lang);
    }
    if (b.dataset.c) S.cur = localStorage.cur = b.dataset.c;
    i18n();
    render();
    prefs();
  });

  document.addEventListener('click', e => {
    if (e.target.closest('[data-close]')) {
      const sh = !$('#sheet').hidden;
      hide();
      if (sh && location.hash) history.back();
    }
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') hide();
  });

  addEventListener('popstate', () => {
    const s = location.hash.slice(1);
    const p = P.find(x => x.slug === s);
    p ? open(p.id, false) : hide();
  });

  i18n();
  render();
  const h = location.hash.slice(1);
  const hp = P.find(x => x.slug === h);
  if (hp) open(hp.id, false);
})();
