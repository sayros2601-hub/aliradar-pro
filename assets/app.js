// SmartChoice / SmartPick — Multilingual E-Commerce Deal Catalog Engine
// Default Language: Hebrew (עברית, RTL) + Global Languages (EN, RU, ES, FR, DE, AR)
// Currencies: ₪ ILS, $ USD, € EUR (Rubles removed)
// Features: 100% Real Factory Images, Interactive Multi-Angle Gallery, Curiosity Hooks, Full Specs Modal

(function () {
  const I18N = {
    he: {
      dir: 'rtl',
      langName: '🇮🇱 עברית',
      brandSub: 'קטלוג מציאות עולמי',
      topBadge1: '✓ <strong>חנויות רשמיות</strong> בלבד',
      topBadge2: '📦 משלוח מהיר לישראל ואירופה (עד <strong>$75</strong> פטור מלא ממס בישראל)',
      topBadge3: '🔒 רכישה בטוחה ישירות מהיצרן',
      searchPlaceholder: 'חיפוש מציאות: מטען GaN, מצלמת דרך 2K, גאדג׳טים, חיות מחמד...',
      searchBtn: 'חיפוש',
      heroTitle: 'מציאות Choice וגאדג׳טים מובחרים — במחירים ישירים מהיצרן',
      heroSub: 'כל המוצרים נבחרו בקפידה עם תמונות מפעל אמיתיות, דירוג קונים מאומת (4.8★–5.0★) ומשלוח מהיר.',
      pill1: '⭐ דירוג 4.8+ מוכח',
      pill2: '📸 תמונות מוצר אמיתיות (לחצו להחלפת זווית)',
      pill3: '✈️ משלוח מהיר לכל העולם',
      sortPopular: 'מיון: הכי פופולריים',
      sortDiscount: 'לפי גובה ההנחה (%)',
      sortPriceAsc: 'מחיר: מהנמוך לגבוה',
      sortRating: 'לפי דירוג קונים ★',
      cats: {
        all: '🔥 כל המציאות',
        gadgets: '⚡ גאדג׳טים ואלקטרוניקה',
        auto: '🚗 לרכב ולנהג',
        pets: '🐾 חיות מחמד',
        smarthome: '🏠 בית חכם וכלים',
        under10: '💎 מציאות עד $15'
      },
      ordersLabel: 'נמכרו:',
      reviewsLabel: 'ביקורות',
      choiceTag: 'Choice',
      shippingTag: '🚚 משלוח חינם ומהיר',
      btnDetails: '🔍 תמונות ומפרט',
      btnBuy: 'לרכישה בחנות הרשמית ←',
      modalHighlights: '⭐ למה המוצר מומלץ:',
      modalSpecs: '📋 מפרט טכני מלא:',
      modalTrust: '🛡️ אחריות קונים מלאה, משלוח בינלאומי מהיר ופטור מלא ממס בישראל עד $75.',
      noResults: 'לא נמצאו מוצרים התואמים לחיפוש. נסה לבחור קטגוריה אחרת.',
      footerTitle: 'SmartPick Global — קטלוג עצמאי למציאות וגאדג׳טים מובילים',
      disclosure: 'גילוי נאות: SmartPick הוא קטלוג המלצות עצמאי ואינו בבעלות AliExpress או קבוצת Alibaba. כל הקישורים באתר הם קישורי שותפים רשמיים המובילים ישירות לחנויות המקוריות במחיר המבצע ללא תוספת תשלום.'
    },
    en: {
      dir: 'ltr',
      langName: '🇺🇸 English',
      brandSub: 'Global Choice Deals',
      topBadge1: '✓ <strong>Official Stores</strong> Only',
      topBadge2: '📦 Fast Shipping to US, Europe & Israel (Tax-Free under $75 in IL)',
      topBadge3: '🔒 100% Safe Direct Factory Links',
      searchPlaceholder: 'Search deals: GaN charger, 2K dash cam, smart home, pets...',
      searchBtn: 'Search',
      heroTitle: 'Top-Rated Choice Deals & Gadgets — Direct Factory Prices',
      heroSub: 'Handpicked items with 100% real factory photos, verified 4.8★–5.0★ buyer ratings, and rapid delivery.',
      pill1: '⭐ 4.8+ Verified Ratings',
      pill2: '📸 Real Multi-Angle Photos (Click to preview)',
      pill3: '✈️ Worldwide Fast Shipping',
      sortPopular: 'Sort: Most Popular',
      sortDiscount: 'Highest Discount (%)',
      sortPriceAsc: 'Price: Low to High',
      sortRating: 'Highest Rating ★',
      cats: {
        all: '🔥 All Deals',
        gadgets: '⚡ Smart Gadgets',
        auto: '🚗 Auto & Car Gear',
        pets: '🐾 Pet Favorites',
        smarthome: '🏠 Smart Home & Tools',
        under10: '💎 Under $15 Finds'
      },
      ordersLabel: 'Sold:',
      reviewsLabel: 'reviews',
      choiceTag: 'Choice',
      shippingTag: '🚚 Free Fast Shipping',
      btnDetails: '🔍 Photos & Specs',
      btnBuy: 'Get Deal on Store →',
      modalHighlights: '⭐ Key Highlights:',
      modalSpecs: '📋 Full Specifications:',
      modalTrust: '🛡️ Official buyer protection, hassle-free returns, and fast international shipping.',
      noResults: 'No products matched your search. Try another category.',
      footerTitle: 'SmartPick Global — Independent Curated Product & Deal Catalog',
      disclosure: 'Affiliate Disclosure: SmartPick is an independent curated discovery portal and is not owned or operated by AliExpress or Alibaba Group. When you buy through official links, we may earn a referral fee at zero extra cost to you.'
    },
    ru: {
      dir: 'ltr',
      langName: '🇷🇺 Русский',
      brandSub: 'Каталог проверенных находок',
      topBadge1: '✓ Только <strong>официальные магазины</strong>',
      topBadge2: '📦 Быстрая доставка в Израиль, ЕС и США (до $75 без пошлины в Израиле)',
      topBadge3: '🔒 Прямые безопасные ссылки со скидкой',
      searchPlaceholder: 'Поиск: зарядка GaN 100W, видеорегистратор 2K, товары для животных...',
      searchBtn: 'Найти',
      heroTitle: 'Хиты Choice и лучшие гаджеты по прямым ценам фабрик',
      heroSub: 'Только реальные заводские фотографии со всех ракурсов, честный рейтинг 4.8★–5.0★ и быстрая отправка.',
      pill1: '⭐ Рейтинг 4.8+ звёзд',
      pill2: '📸 Настоящие фото товара (нажимайте на миниатюры)',
      pill3: '✈️ Быстрая международная доставка',
      sortPopular: 'По популярности',
      sortDiscount: 'По размеру скидки (%)',
      sortPriceAsc: 'Сначала недорогие',
      sortRating: 'По рейтингу ★',
      cats: {
        all: '🔥 Все находки',
        gadgets: '⚡ Умные гаджеты',
        auto: '🚗 Автотовары',
        pets: '🐾 Хиты для питомцев',
        smarthome: '🏠 Дом и Инструмент',
        under10: '💎 Находки до $15'
      },
      ordersLabel: 'Купили:',
      reviewsLabel: 'отзывов',
      choiceTag: 'Choice',
      shippingTag: '🚚 Быстрая доставка',
      btnDetails: '🔍 Фото и Обзор',
      btnBuy: 'В магазин со скидкой →',
      modalHighlights: '⭐ Главные преимущества:',
      modalSpecs: '📋 Технические характеристики:',
      modalTrust: '🛡️ Защита покупателя, возврат без проблем и прямая цена без посредников.',
      noResults: 'По вашему запросу ничего не найдено. Попробуйте выбрать другую категорию.',
      footerTitle: 'SmartPick Global — Независимый каталог лучших находок и скидок',
      disclosure: 'Партнёрское уведомление: SmartPick является независимым каталогом обзоров и не принадлежит корпорации Alibaba Group / AliExpress. Покупая по прямым ссылкам, вы получаете лучшую цену без каких-либо наценок.'
    },
    es: {
      dir: 'ltr',
      langName: '🇪🇸 Español',
      brandSub: 'Catálogo de Ofertas Choice',
      topBadge1: '✓ Solo <strong>Tiendas Oficiales</strong>',
      topBadge2: '📦 Envío rápido a Europa, EE.UU. e Israel',
      topBadge3: '🔒 Enlaces oficiales directos',
      searchPlaceholder: 'Buscar: cargador GaN, cámara coche 2K, mascotas, hogar...',
      searchBtn: 'Buscar',
      heroTitle: 'Los Mejores Chollos Choice y Gadgets a Precio de Fábrica',
      heroSub: 'Fotos reales de fábrica desde todos los ángulos, valoración de 4.8★–5.0★ y envío rápido.',
      pill1: '⭐ Valoración 4.8+',
      pill2: '📸 Fotos Reales (Haz clic para ver)',
      pill3: '✈️ Envío Rápido Mundial',
      sortPopular: 'Más Populares',
      sortDiscount: 'Mayor Descuento (%)',
      sortPriceAsc: 'Precio: Menor a Mayor',
      sortRating: 'Mejor Valorados ★',
      cats: {
        all: '🔥 Todas las Ofertas',
        gadgets: '⚡ Gadgets Inteligentes',
        auto: '🚗 Accesorios de Coche',
        pets: '🐾 Para Mascotas',
        smarthome: '🏠 Hogar y Herramientas',
        under10: '💎 Menos de $15'
      },
      ordersLabel: 'Vendidos:',
      reviewsLabel: 'opiniones',
      choiceTag: 'Choice',
      shippingTag: '🚚 Envío Gratis Rápido',
      btnDetails: '🔍 Fotos y Ficha',
      btnBuy: 'Ver Oferta en Tienda →',
      modalHighlights: '⭐ Ventajas Destacadas:',
      modalSpecs: '📋 Especificaciones Técnicas:',
      modalTrust: '🛡️ Protección del comprador y garantía de devolución.',
      noResults: 'No se encontraron productos. Prueba otra categoría.',
      footerTitle: 'SmartPick Global — Catálogo Independiente de Ofertas',
      disclosure: 'Aviso de afiliado: SmartPick es un catálogo independiente no afiliado a Alibaba Group. Al comprar a través de nuestros enlaces oficiales, podemos recibir una comisión sin coste adicional.'
    },
    fr: {
      dir: 'ltr',
      langName: '🇫🇷 Français',
      brandSub: 'Sélection Bons Plans Choice',
      topBadge1: '✓ <strong>Boutiques Officielles</strong>',
      topBadge2: '📦 Livraison rapide Europe & International',
      topBadge3: '🔒 Liens officiels vérifiés',
      searchPlaceholder: 'Rechercher : chargeur GaN, caméra voiture, animaux...',
      searchBtn: 'Chercher',
      heroTitle: 'Meilleurs Gadgets & Bons Plans Choice — Prix Direct Fabricant',
      heroSub: 'Photos d\'usine réelles sous tous les angles, avis clients 4.8★–5.0★ et livraison express.',
      pill1: '⭐ Avis 4.8+ Vérifiés',
      pill2: '📸 Vraies Photos Produit',
      pill3: '✈️ Livraison Rapide',
      sortPopular: 'Les Plus Populaires',
      sortDiscount: 'Plus Grosse Réduction (%)',
      sortPriceAsc: 'Prix : Croissant',
      sortRating: 'Mieux Notés ★',
      cats: {
        all: '🔥 Tous les Bons Plans',
        gadgets: '⚡ Gadgets Tech',
        auto: '🚗 Auto & Accessoires',
        pets: '🐾 Chiens & Chats',
        smarthome: '🏠 Maison Connectée',
        under10: '💎 Moins de 15$'
      },
      ordersLabel: 'Commandes :',
      reviewsLabel: 'avis',
      choiceTag: 'Choice',
      shippingTag: '🚚 Livraison Gratuite',
      btnDetails: '🔍 Photos & Détails',
      btnBuy: 'Acheter en Boutique →',
      modalHighlights: '⭐ Points Forts :',
      modalSpecs: '📋 Fiche Technique :',
      modalTrust: '🛡️ Protection de l\'acheteur et retours faciles.',
      noResults: 'Aucun produit trouvé. Essayez une autre catégorie.',
      footerTitle: 'SmartPick Global — Guide d\'Achat Indépendant',
      disclosure: 'Transparence : SmartPick est un catalogue indépendant non affilié à Alibaba Group.'
    },
    de: {
      dir: 'ltr',
      langName: '🇩🇪 Deutsch',
      brandSub: 'Choice Schnäppchen-Katalog',
      topBadge1: '✓ Nur <strong>Offizielle Shops</strong>',
      topBadge2: '📦 Schneller Versand EU, USA & Weltweit',
      topBadge3: '🔒 Sichere Direktlinks zum Hersteller',
      searchPlaceholder: 'Suche: GaN Ladegerät, 2K Dashcam, Haustiere...',
      searchBtn: 'Suchen',
      heroTitle: 'Top Choice Deals & Gadgets — Direktpreise vom Hersteller',
      heroSub: 'Echte Fabrikfotos aus allen Blickwinkeln, 4.8★–5.0★ Kundenbewertungen und schneller Versand.',
      pill1: '⭐ 4.8+ Top-Bewertung',
      pill2: '📸 Echte Produktfotos',
      pill3: '✈️ Schnelle Lieferung',
      sortPopular: 'Beliebteste zuerst',
      sortDiscount: 'Höchster Rabatt (%)',
      sortPriceAsc: 'Preis: Aufsteigend',
      sortRating: 'Beste Bewertung ★',
      cats: {
        all: '🔥 Alle Schnäppchen',
        gadgets: '⚡ Smart Gadgets',
        auto: '🚗 Auto & Zubehör',
        pets: '🐾 Für Haustiere',
        smarthome: '🏠 Smart Home & Werkzeug',
        under10: '💎 Unter 15$'
      },
      ordersLabel: 'Verkauft:',
      reviewsLabel: 'Bewertungen',
      choiceTag: 'Choice',
      shippingTag: '🚚 Schneller Gratisversand',
      btnDetails: '🔍 Fotos & Details',
      btnBuy: 'Zum offiziellen Shop →',
      modalHighlights: '⭐ Produkthighlights:',
      modalSpecs: '📋 Technische Daten:',
      modalTrust: '🛡️ Offizieller Käuferschutz und unkomplizierte Rückgabe.',
      noResults: 'Keine passenden Produkte gefunden.',
      footerTitle: 'SmartPick Global — Unabhängiger Schnäppchenführer',
      disclosure: 'Transparenz: SmartPick ist ein unabhängiges Entdeckungsportal.'
    },
    ar: {
      dir: 'rtl',
      langName: '🇦🇪 العربية',
      brandSub: 'كتالوج صفقات تشويس العالمية',
      topBadge1: '✓ <strong>متاجر رسمية</strong> ومضمونة فقط',
      topBadge2: '📦 شحن سريع ومباشر مع حماية كاملة للمشتري',
      topBadge3: '🔒 روابط مباشرة معتمدة بأسعار المصنع',
      searchPlaceholder: 'بحث: شاحن GaN سريع، كاميرا سيارة 2K، مستلزمات قطط...',
      searchBtn: 'بحث',
      heroTitle: 'أفضل صفقات Choice والأجهزة الذكية — بأسعار المصنع المباشرة',
      heroSub: 'صور حقيقية مباشرة من خط الإنتاج بزوايا متعددة، تقييمات موثوقة (4.8★–5.0★) وشحن سريع.',
      pill1: '⭐ تقييم 4.8+ مؤكد',
      pill2: '📸 صور حقيقية للمنتج (انقر للتبديل)',
      pill3: '✈️ شحن سريع لجميع الدول',
      sortPopular: 'الأكثر شعبية',
      sortDiscount: 'أعلى نسبة خصم (%)',
      sortPriceAsc: 'السعر: من الأقل للأعلى',
      sortRating: 'الأعلى تقييماً ★',
      cats: {
        all: '🔥 جميع العروض',
        gadgets: '⚡ أجهزة ذكية',
        auto: '🚗 للسيارات والقيادة',
        pets: '🐾 مستلزمات الحيوانات',
        smarthome: '🏠 المنزل الذكي',
        under10: '💎 صفقات أقل من 15$'
      },
      ordersLabel: 'المبيعات:',
      reviewsLabel: 'تقييم',
      choiceTag: 'Choice',
      shippingTag: '🚚 شحن سريع ومجاني',
      btnDetails: '🔍 الصور والمواصفات',
      btnBuy: 'شراء من المتجر الرسمي ←',
      modalHighlights: '⭐ أبرز مميزات المنتج:',
      modalSpecs: '📋 المواصفات الفنية الكاملة:',
      modalTrust: '🛡️ حماية كاملة للمشتري، ضمان استرجاع وشحن سريع مباشر.',
      noResults: 'لم يتم العثور على منتجات مطابقة.',
      footerTitle: 'SmartPick Global — كتالوج المنتجات والعروض المستقل',
      disclosure: 'إخلاء مسؤولية: SmartPick هو دليل تسوق مستقل وغير تابع لشركة Alibaba أو AliExpress.'
    }
  };

  let currentLang = 'he';
  let currency = 'ILS';
  let currentCategory = 'all';
  let currentSort = 'popular';
  let currentSearch = '';

  const RATES = {
    ILS: 3.65,
    USD: 1.0,
    EUR: 0.92
  };

  const SYMBOLS = {
    ILS: '₪',
    USD: '$',
    EUR: '€'
  };

  const products = window.__INITIAL_PRODUCTS__ || [];

  const langSelect = document.getElementById('langSelect');
  const searchInput = document.getElementById('searchInput');
  const searchBtn = document.getElementById('searchBtn');
  const sortSelect = document.getElementById('sortSelect');
  const gridEl = document.getElementById('productGrid');
  const modalBackdrop = document.getElementById('reviewModal');
  const modalContent = document.getElementById('modalContent');

  function getLocalizedField(item, field) {
    if (!item) return '';
    const i18nField = field + '_i18n';
    if (item[i18nField] && item[i18nField][currentLang]) {
      return item[i18nField][currentLang];
    }
    return item[field] || (item[i18nField] && item[i18nField]['he']) || (item[i18nField] && item[i18nField]['en']) || '';
  }

  function formatPrice(usd) {
    const rate = RATES[currency] || 1;
    const sym = SYMBOLS[currency] || '$';
    const val = usd * rate;
    if (currency === 'ILS') {
      return `${sym}${Math.round(val)}`;
    }
    return `${sym}${val.toFixed(2)}`;
  }

  function formatOldPrice(usd) {
    const rate = RATES[currency] || 1;
    const sym = SYMBOLS[currency] || '$';
    const val = usd * rate;
    if (currency === 'ILS') {
      return `${sym}${Math.round(val)}`;
    }
    return `${sym}${val.toFixed(2)}`;
  }

  function applyLanguageUI() {
    const t = I18N[currentLang] || I18N.he;
    document.documentElement.lang = currentLang;
    document.documentElement.dir = t.dir;

    if (langSelect) langSelect.value = currentLang;

    const brandSub = document.querySelector('.brand-sub');
    if (brandSub) brandSub.textContent = t.brandSub;

    const badge1 = document.getElementById('topBadge1');
    const badge2 = document.getElementById('topBadge2');
    const badge3 = document.getElementById('topBadge3');
    if (badge1) badge1.innerHTML = t.topBadge1;
    if (badge2) badge2.innerHTML = t.topBadge2;
    if (badge3) badge3.innerHTML = t.topBadge3;

    if (searchInput) searchInput.placeholder = t.searchPlaceholder;
    if (searchBtn) searchBtn.textContent = t.searchBtn;

    const heroTitle = document.getElementById('heroTitle');
    const heroSub = document.getElementById('heroSub');
    if (heroTitle) heroTitle.textContent = t.heroTitle;
    if (heroSub) heroSub.textContent = t.heroSub;

    const pill1 = document.getElementById('pill1');
    const pill2 = document.getElementById('pill2');
    const pill3 = document.getElementById('pill3');
    if (pill1) pill1.textContent = t.pill1;
    if (pill2) pill2.textContent = t.pill2;
    if (pill3) pill3.textContent = t.pill3;

    if (sortSelect) {
      sortSelect.options[0].textContent = t.sortPopular;
      sortSelect.options[1].textContent = t.sortDiscount;
      sortSelect.options[2].textContent = t.sortPriceAsc;
      sortSelect.options[3].textContent = t.sortRating;
    }

    document.querySelectorAll('.cat-pill').forEach((btn) => {
      const catKey = btn.getAttribute('data-cat');
      if (t.cats && t.cats[catKey]) {
        btn.textContent = t.cats[catKey];
      }
    });

    const footerTitle = document.getElementById('footerTitle');
    const disclosureBox = document.getElementById('disclosureBox');
    if (footerTitle) footerTitle.textContent = t.footerTitle;
    if (disclosureBox) disclosureBox.textContent = t.disclosure;

    renderProducts();
  }

  window.switchCardPhoto = function (cardId, imgUrl, thumbEl) {
    const mainImg = document.getElementById('main-img-' + cardId);
    if (mainImg) {
      mainImg.src = imgUrl;
    }
    if (thumbEl && thumbEl.parentElement) {
      thumbEl.parentElement.querySelectorAll('.thumb-item').forEach((el) => el.classList.remove('active'));
      thumbEl.classList.add('active');
    }
  };

  function renderProducts() {
    if (!gridEl) return;
    const t = I18N[currentLang] || I18N.he;

    let filtered = products.filter((p) => {
      const matchCat = currentCategory === 'all' || p.category === currentCategory;
      const q = currentSearch.trim().toLowerCase();
      if (!q) return matchCat;
      const hay = [
        p.title,
        getLocalizedField(p, 'title'),
        getLocalizedField(p, 'card_hook'),
        getLocalizedField(p, 'short_desc'),
        p.slug
      ]
        .join(' ')
        .toLowerCase();
      return matchCat && hay.includes(q);
    });

    if (currentSort === 'discount') {
      filtered.sort((a, b) => b.discount_pct - a.discount_pct);
    } else if (currentSort === 'price_asc') {
      filtered.sort((a, b) => a.price_usd - b.price_usd);
    } else if (currentSort === 'rating') {
      filtered.sort((a, b) => b.rating - a.rating);
    }

    if (filtered.length === 0) {
      gridEl.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:#64748b;background:#fff;border-radius:14px;border:1px solid #e2e8f0;">${t.noResults}</div>`;
      return;
    }

    gridEl.innerHTML = filtered
      .map((p) => {
        const title = getLocalizedField(p, 'title');
        const hook = getLocalizedField(p, 'card_hook') || getLocalizedField(p, 'short_desc');
        const gallery = (p.gallery && p.gallery.length ? p.gallery : [p.image]).slice(0, 5);
        
        const thumbsHtml =
          gallery.length > 1
            ? `<div class="thumb-strip">
                ${gallery
                  .map(
                    (gUrl, idx) => `
                  <button type="button" class="thumb-item ${idx === 0 ? 'active' : ''}" onclick="window.switchCardPhoto('${p.id}', '${gUrl}', this)" aria-label="Photo ${idx + 1}">
                    <img src="${gUrl}" alt="" loading="lazy" width="40" height="40" />
                  </button>`
                  )
                  .join('')}
               </div>`
            : '';

        return `
      <article class="product-card" data-category="${p.category}">
        <div class="card-media-wrap">
          <a href="${p.affiliate_url}" target="_blank" rel="nofollow sponsored noopener" class="card-media">
            <img id="main-img-${p.id}" src="${gallery[0]}" alt="${title}" loading="lazy" width="300" height="300" />
            <span class="choice-tag">★ ${t.choiceTag}</span>
            <span class="card-discount">-${p.discount_pct}%</span>
          </a>
          ${thumbsHtml}
        </div>
        <div class="card-body">
          <div class="card-meta-row">
            <span class="rating-pill">★ ${p.rating} (${p.reviews_count.toLocaleString()})</span>
            <span class="orders-pill">${t.ordersLabel} ${p.orders_count}</span>
          </div>
          <h3 class="card-title" title="${title}">${title}</h3>
          <div class="card-hook" onclick="window.openReview('${p.id}')" title="לחצו לסקירה מלאה ומפרט">
            ${hook}
          </div>
          <div class="price-box">
            <div>
              <span class="price-main">${formatPrice(p.price_usd)}</span>
              <span class="price-old">${formatOldPrice(p.old_price_usd)}</span>
            </div>
            <span class="shipping-tag">${t.shippingTag}</span>
          </div>
          <div class="card-actions">
            <button type="button" class="btn-review" onclick="window.openReview('${p.id}')">
              ${t.btnDetails}
            </button>
            <a class="btn-buy" href="${p.affiliate_url}" target="_blank" rel="nofollow sponsored noopener">
              ${t.btnBuy}
            </a>
          </div>
        </div>
      </article>
    `;
      })
      .join('');
  }

  window.openReview = function (id) {
    const p = products.find((item) => item.id === id);
    if (!p || !modalBackdrop || !modalContent) return;
    const t = I18N[currentLang] || I18N.he;
    const title = getLocalizedField(p, 'title');
    const hook = getLocalizedField(p, 'card_hook') || getLocalizedField(p, 'short_desc');
    const gallery = (p.gallery && p.gallery.length ? p.gallery : [p.image]);

    let highlightsHtml = '';
    if (p.highlights && p.highlights.length) {
      highlightsHtml = `
        <h4 style="font-size:0.95rem;font-weight:800;color:#191919;margin-top:14px;margin-bottom:6px;">${t.modalHighlights}</h4>
        <ul class="highlights-list">
          ${p.highlights.map((h) => `<li>${h}</li>`).join('')}
        </ul>
      `;
    }

    let specsHtml = '';
    if (p.specs && Object.keys(p.specs).length) {
      specsHtml = `
        <h4 style="font-size:0.95rem;font-weight:800;color:#191919;margin-top:12px;margin-bottom:6px;">${t.modalSpecs}</h4>
        <table class="specs-table">
          <tbody>
            ${Object.entries(p.specs)
              .map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`)
              .join('')}
          </tbody>
        </table>
      `;
    }

    modalContent.innerHTML = `
      <button type="button" class="modal-close" onclick="window.closeReview()" aria-label="Close">✕</button>
      
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span class="choice-tag" style="position:static;">★ ${t.choiceTag}</span>
        <span style="font-size:0.84rem;font-weight:800;color:#fd384f;">-${p.discount_pct}% הנחה</span>
        <span style="color:#ff9800;font-weight:800;font-size:0.84rem;">★ ${p.rating}</span>
        <span style="color:#64748b;font-size:0.82rem;">(${t.ordersLabel} ${p.orders_count})</span>
      </div>

      <h2 style="font-size:1.18rem;margin-bottom:12px;color:#191919;padding-inline-end:32px;line-height:1.4;">${title}</h2>
      
      <!-- Interactive Main Photo with Full Angles -->
      <div class="modal-hero-wrap">
        <img id="modal-hero-img" src="${gallery[0]}" alt="${title}" />
      </div>

      <div class="modal-thumbs-row">
        ${gallery
          .map(
            (imgUrl, idx) => `
          <button type="button" class="modal-thumb ${idx === 0 ? 'active' : ''}" onclick="document.getElementById('modal-hero-img').src='${imgUrl}'; this.parentElement.querySelectorAll('.modal-thumb').forEach(b => b.classList.remove('active')); this.classList.add('active');">
            <img src="${imgUrl}" alt="Photo ${idx + 1}" />
          </button>`
          )
          .join('')}
      </div>

      <div class="card-hook" style="cursor:default;font-size:0.88rem;margin-bottom:12px;">
        ${hook}
      </div>

      ${highlightsHtml}
      ${specsHtml}

      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 14px;font-size:0.82rem;color:#166534;margin-top:12px;margin-bottom:18px;">
        ${t.modalTrust}
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;padding-top:14px;border-top:1px solid #e5e7eb;position:sticky;bottom:0;background:#ffffff;margin-top:auto;">
        <div>
          <span class="price-main" style="font-size:1.6rem;">${formatPrice(p.price_usd)}</span>
          <span class="price-old" style="font-size:0.95rem;">${formatOldPrice(p.old_price_usd)}</span>
        </div>
        <a class="btn-buy" style="padding:12px 26px;font-size:1rem;" href="${p.affiliate_url}" target="_blank" rel="nofollow sponsored noopener">
          ${t.btnBuy}
        </a>
      </div>
    `;
    modalBackdrop.classList.add('open');
  };

  window.closeReview = function () {
    if (modalBackdrop) modalBackdrop.classList.remove('open');
  };

  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) window.closeReview();
    });
  }

  if (langSelect) {
    langSelect.addEventListener('change', (e) => {
      currentLang = e.target.value || 'he';
      applyLanguageUI();
    });
  }

  document.querySelectorAll('.cat-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.getAttribute('data-cat') || 'all';
      renderProducts();
    });
  });

  document.querySelectorAll('.curr-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.curr-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currency = btn.getAttribute('data-curr') || 'ILS';
      renderProducts();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearch = e.target.value || '';
      renderProducts();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      currentSort = e.target.value;
      renderProducts();
    });
  }

  // Initialize in Hebrew (RTL) by default
  applyLanguageUI();
})();
