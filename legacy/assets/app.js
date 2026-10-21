// SmartChoice / SmartPick — Multilingual E-Commerce Deal Catalog Engine
// Default Language: Hebrew (עברית, RTL) + Global Languages (EN, RU, ES, FR, DE, AR)
// Currencies: ₪ ILS, $ USD, € EUR (Rubles removed)
// Features: 36+ Curated Hidden Gem Products across 6 AliExpress Departments
// Real Factory Images (0-latency local cache), Multi-Angle Gallery, Curiosity Hooks, Full Specs Modal

(function () {
  const I18N = {
    he: {
      dir: 'rtl',
      langName: '🇮🇱 עברית',
      brandSub: 'קטלוג מציאות עולמי',
      topBadge1: '✓ <strong>חנויות רשמיות</strong> בלבד',
      topBadge2: '📦 משלוח מהיר לישראל (עד <strong>$75</strong> פטור מלא ממס בישראל)',
      topBadge3: '🔒 רכישה בטוחה ישירות מהיצרן',
      searchPlaceholder: 'חיפוש מציאות: מדפסת כיס, מטען GaN, ניטור צמיגים, שואב אבק לרכב, משקל דיגיטלי...',
      searchBtn: 'חיפוש',
      heroTitle: 'מציאות Choice והמצאות שלא ראיתם — במחירים ישירים מהיצרן',
      heroSub: 'קטלוג עצמאי של גאדג׳טים מבריקים, שדרוגים לרכב, פטנטים לבית ולחיות מחמד שחוסכים כסף. כולם מתחת לרף המס ($75) ועם משלוח חינם לישראל.',
      pill1: '⭐ דירוג 4.8+ מוכח',
      pill2: '📸 תמונות מוצר אמיתיות (לחצו להחלפת זווית)',
      pill3: '✈️ משלוח חינם לישראל',
      sortPopular: 'מיון: הכי פופולריים',
      sortDiscount: 'לפי גובה ההנחה (%)',
      sortPriceAsc: 'מחיר: מהנמוך לגבוה',
      sortRating: 'לפי דירוג קונים ★',
      cats: {
        all: '🔥 כל המציאות',
        gadgets: '⚡ גאדג׳טים והמצאות כיס',
        auto: '🚗 שדרוגים חכמים לרכב',
        smarthome: '🏠 בית, מטבח ומיקרו-המצאות',
        pets: '🐾 המצאות לחיות מחמד',
        tools: '🔧 כלי עבודה ותיקונים',
        under10: '💎 מציאות גאוניות עד ₪50'
      },
      priceFilterLabel: 'סינון לפי מחיר:',
      priceAll: 'הכל',
      priceUnder50: 'עד ₪50',
      price50_100: '₪50 - ₪100',
      price100_280: '₪100 - ₪280',
      ordersLabel: 'נמכרו:',
      reviewsLabel: 'ביקורות',
      choiceTag: 'Choice',
      shippingTag: '🚚 משלוח חינם לישראל',
      btnDetails: '🔍 תמונות ומפרט',
      btnBuy: 'לרכישה בחנות הרשמית ←',
      modalHighlights: '⭐ למה המוצר מומלץ:',
      modalSpecs: '📋 מפרט טכני מלא:',
      modalTrust: '🛡️ אחריות קונים מלאה, משלוח מהיר לישראל ופטור מלא ממס בישראל עד $75.',
      noResults: 'לא נמצאו מוצרים התואמים לחיפוש. נסה לשנות קטגוריה או טווח מחירים.',
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
      searchPlaceholder: 'Search hidden gems: pocket printer, GaN charger, TPMS, car vacuum, digital spoon...',
      searchBtn: 'Search',
      heroTitle: 'Undiscovered Choice Deals & Inventions — Direct Factory Prices',
      heroSub: 'Curated breakthroughs, clever car upgrades, smart home inventions, and pet gadgets that solve daily problems. All under $75 customs limit.',
      pill1: '⭐ 4.8+ Verified Ratings',
      pill2: '📸 Real Multi-Angle Photos (Click to preview)',
      pill3: '✈️ Free Shipping Included',
      sortPopular: 'Sort: Most Popular',
      sortDiscount: 'Highest Discount (%)',
      sortPriceAsc: 'Price: Low to High',
      sortRating: 'Highest Rating ★',
      cats: {
        all: '🔥 All Deals',
        gadgets: '⚡ Smart Inventions & EDC',
        auto: '🚗 Car Gear & Auto Tech',
        smarthome: '🏠 Smart Home & Kitchen',
        pets: '🐾 Clever Pet Tech',
        tools: '🔧 Precision Tools & Repair',
        under10: '💎 Under $15 Brilliant Bargains'
      },
      priceFilterLabel: 'Filter by Price:',
      priceAll: 'All Prices',
      priceUnder50: 'Under $15',
      price50_100: '$15 - $30',
      price100_280: '$30 - $75',
      ordersLabel: 'Sold:',
      reviewsLabel: 'reviews',
      choiceTag: 'Choice',
      shippingTag: '🚚 Free Fast Shipping',
      btnDetails: '🔍 Photos & Specs',
      btnBuy: 'Get Deal on Store →',
      modalHighlights: '⭐ Key Highlights:',
      modalSpecs: '📋 Full Specifications:',
      modalTrust: '🛡️ Official buyer protection, hassle-free returns, and fast international shipping.',
      noResults: 'No products matched your search. Try adjusting filters.',
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
      searchPlaceholder: 'Поиск редких находок: карманный принтер, автосканер, датчик шин, весы-ложка...',
      searchBtn: 'Найти',
      heroTitle: 'Редкие находки Choice и изобретения, которых нет в обычном топе',
      heroSub: 'Гениальные полезные гаджеты, автотовары, умные мелочи для дома и питомцев по прямым ценам фабрик. Все товары до $75 без пошлины в Израиле и с бесплатной доставкой.',
      pill1: '⭐ Рейтинг 4.8+ звёзд',
      pill2: '📸 Настоящие фото товара (нажимайте на миниатюры)',
      pill3: '✈️ Бесплатная доставка в Израиль',
      sortPopular: 'По популярности',
      sortDiscount: 'По размеру скидки (%)',
      sortPriceAsc: 'Сначала недорогие',
      sortRating: 'По рейтингу ★',
      cats: {
        all: '🔥 Все находки',
        gadgets: '⚡ Гаджеты и EDC',
        auto: '🚗 Автотовары и апгрейд',
        smarthome: '🏠 Дом, кухня и лайфхаки',
        pets: '🐾 Инновации для питомцев',
        tools: '🔧 Точный инструмент',
        under10: '💎 Находки до 50 шекелей'
      },
      priceFilterLabel: 'Цена:',
      priceAll: 'Все',
      priceUnder50: 'До 50 ₪',
      price50_100: '50 - 100 ₪',
      price100_280: '100 - 280 ₪',
      ordersLabel: 'Купили:',
      reviewsLabel: 'отзывов',
      choiceTag: 'Choice',
      shippingTag: '🚚 Бесплатная доставка',
      btnDetails: '🔍 Фото и Обзор',
      btnBuy: 'В магазин со скидкой →',
      modalHighlights: '⭐ Главные преимущества:',
      modalSpecs: '📋 Технические характеристики:',
      modalTrust: '🛡️ Защита покупателя, возврат без проблем и прямая цена без посредников.',
      noResults: 'По вашему запросу ничего не найдено. Попробуйте сбросить фильтры.',
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
      searchPlaceholder: 'Buscar chollos: mini impresora, TPMS solar, aspirador coche, hogar...',
      searchBtn: 'Buscar',
      heroTitle: 'Inventos y Chollos Ocultos Choice a Precio de Fábrica',
      heroSub: 'Artículos ingeniosos para coche, hogar y mascotas sin intermediarios.',
      pill1: '⭐ Valoración 4.8+',
      pill2: '📸 Fotos Reales',
      pill3: '✈️ Envío Gratis',
      sortPopular: 'Más Populares',
      sortDiscount: 'Mayor Descuento (%)',
      sortPriceAsc: 'Precio: Menor a Mayor',
      sortRating: 'Mejor Valorados ★',
      cats: {
        all: '🔥 Todas las Ofertas',
        gadgets: '⚡ Inventos y EDC',
        auto: '🚗 Accesorios de Coche',
        smarthome: '🏠 Hogar y Cocina',
        pets: '🐾 Para Mascotas',
        tools: '🔧 Herramientas',
        under10: '💎 Menos de $15'
      },
      priceFilterLabel: 'Precio:',
      priceAll: 'Todos',
      priceUnder50: '< $15',
      price50_100: '$15 - $30',
      price100_280: '$30 - $75',
      ordersLabel: 'Vendidos:',
      reviewsLabel: 'opiniones',
      choiceTag: 'Choice',
      shippingTag: '🚚 Envío Gratis',
      btnDetails: '🔍 Fotos y Ficha',
      btnBuy: 'Ver Oferta en Tienda →',
      modalHighlights: '⭐ Ventajas Destacadas:',
      modalSpecs: '📋 Especificaciones Técnicas:',
      modalTrust: '🛡️ Protección del comprador y garantía de devolución.',
      noResults: 'No se encontraron productos.',
      footerTitle: 'SmartPick Global — Catálogo Independiente de Ofertas',
      disclosure: 'Aviso de afiliado: SmartPick es un catálogo independiente.'
    },
    fr: {
      dir: 'ltr',
      langName: '🇫🇷 Français',
      brandSub: 'Sélection Bons Plans Choice',
      topBadge1: '✓ <strong>Boutiques Officielles</strong>',
      topBadge2: '📦 Livraison rapide Europe & International',
      topBadge3: '🔒 Liens officiels vérifiés',
      searchPlaceholder: 'Rechercher : mini imprimante, TPMS, aspirateur sans fil...',
      searchBtn: 'Chercher',
      heroTitle: 'Pépites et Inventions Choice — Prix Direct Fabricant',
      heroSub: 'Gadgets utiles pour la voiture, la maison et vos animaux sans intermédiaires.',
      pill1: '⭐ Avis 4.8+ Vérifiés',
      pill2: '📸 Vraies Photos Produit',
      pill3: '✈️ Livraison Gratuite',
      sortPopular: 'Les Plus Populaires',
      sortDiscount: 'Plus Grosse Réduction (%)',
      sortPriceAsc: 'Prix : Croissant',
      sortRating: 'Mieux Notés ★',
      cats: {
        all: '🔥 Tous les Bons Plans',
        gadgets: '⚡ Gadgets EDC',
        auto: '🚗 Auto & Conduite',
        smarthome: '🏠 Maison & Cuisine',
        pets: '🐾 Animaux',
        tools: '🔧 Outils Précision',
        under10: '💎 Moins de 15$'
      },
      priceFilterLabel: 'Prix :',
      priceAll: 'Tous',
      priceUnder50: '< 15$',
      price50_100: '15$ - 30$',
      price100_280: '30$ - 75$',
      ordersLabel: 'Commandes :',
      reviewsLabel: 'avis',
      choiceTag: 'Choice',
      shippingTag: '🚚 Livraison Gratuite',
      btnDetails: '🔍 Photos & Détails',
      btnBuy: 'Acheter en Boutique →',
      modalHighlights: '⭐ Points Forts :',
      modalSpecs: '📋 Fiche Technique :',
      modalTrust: '🛡️ Protection de l\'acheteur et retours faciles.',
      noResults: 'Aucun produit trouvé.',
      footerTitle: 'SmartPick Global — Guide d\'Achat Indépendant',
      disclosure: 'Transparence : SmartPick est un catalogue indépendant.'
    },
    de: {
      dir: 'ltr',
      langName: '🇩🇪 Deutsch',
      brandSub: 'Choice Schnäppchen-Katalog',
      topBadge1: '✓ Nur <strong>Offizielle Shops</strong>',
      topBadge2: '📦 Schneller Versand EU, USA & Weltweit',
      topBadge3: '🔒 Sichere Direktlinks zum Hersteller',
      searchPlaceholder: 'Suche: Minidrucker, Reifendruck, Akkusauger...',
      searchBtn: 'Suchen',
      heroTitle: 'Geheime Choice Deals & Erfindungen — Direktpreise',
      heroSub: 'Nützliche Problemlöser für Auto, Küche, Haustiere und EDC.',
      pill1: '⭐ 4.8+ Top-Bewertung',
      pill2: '📸 Echte Produktfotos',
      pill3: '✈️ Gratisversand',
      sortPopular: 'Beliebteste zuerst',
      sortDiscount: 'Höchster Rabatt (%)',
      sortPriceAsc: 'Preis: Aufsteigend',
      sortRating: 'Beste Bewertung ★',
      cats: {
        all: '🔥 Alle Schnäppchen',
        gadgets: '⚡ EDC Gadgets',
        auto: '🚗 Auto & Zubehör',
        smarthome: '🏠 Heim & Küche',
        pets: '🐾 Haustier-Gadgets',
        tools: '🔧 Werkzeuge',
        under10: '💎 Unter 15$'
      },
      priceFilterLabel: 'Preis:',
      priceAll: 'Alle',
      priceUnder50: '< 15$',
      price50_100: '15$ - 30$',
      price100_280: '30$ - 75$',
      ordersLabel: 'Verkauft:',
      reviewsLabel: 'Bewertungen',
      choiceTag: 'Choice',
      shippingTag: '🚚 Gratisversand',
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
      searchPlaceholder: 'بحث: طابعة جيب، حساس إطارات، مكنسة سيارة، ملعقة ميزان...',
      searchBtn: 'بحث',
      heroTitle: 'ابتكارات وصفقات Choice نادرة — بأسعار المصنع المباشرة',
      heroSub: 'أجهزة ذكية غير تقليدية للسيارة والمنزل والحيوانات الأليفة بأفضل الأسعار المباشرة.',
      pill1: '⭐ تقييم 4.8+ مؤكد',
      pill2: '📸 صور حقيقية للمنتج (انقر للتبديل)',
      pill3: '✈️ شحن مجاني متاح',
      sortPopular: 'الأكثر شعبية',
      sortDiscount: 'أعلى نسبة خصم (%)',
      sortPriceAsc: 'السعر: من الأقل للأعلى',
      sortRating: 'الأعلى تقييماً ★',
      cats: {
        all: '🔥 جميع العروض',
        gadgets: '⚡ أجهزة ذكية محمولة',
        auto: '🚗 مستلزمات السيارات',
        smarthome: '🏠 المنزل والمطبخ',
        pets: '🐾 مستلزمات الحيوانات',
        tools: '🔧 أدوات الصيانة',
        under10: '💎 صفقات أقل من 50 شيكل'
      },
      priceFilterLabel: 'تصفية حسب السعر:',
      priceAll: 'الكل',
      priceUnder50: 'أقل من 50 ₪',
      price50_100: '50 - 100 ₪',
      price100_280: '100 - 280 ₪',
      ordersLabel: 'المبيعات:',
      reviewsLabel: 'تقييم',
      choiceTag: 'Choice',
      shippingTag: '🚚 شحن مجاني سريع',
      btnDetails: '🔍 الصور والمواصفات',
      btnBuy: 'شراء من المتجر الرسمي ←',
      modalHighlights: '⭐ أبرز مميزات المنتج:',
      modalSpecs: '📋 المواصفات الفنية الكاملة:',
      modalTrust: '🛡️ حماية كاملة للمشتري، ضمان استرجاع وشحن مباشر.',
      noResults: 'لم يتم العثور على منتجات مطابقة.',
      footerTitle: 'SmartPick Global — كتالوج المنتجات والعروض المستقل',
      disclosure: 'إخلاء مسؤولية: SmartPick هو دليل تسوق مستقل.'
    }
  };

  let currentLang = 'he';
  let currency = 'ILS';
  let currentCategory = 'all';
  let currentPriceFilter = 'all';
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
  const priceFilterLabel = document.getElementById('priceFilterLabel');

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

  function updateCategoryCounts() {
    const counts = { all: products.length };
    products.forEach((p) => {
      counts[p.category] = (counts[p.category] || 0) + 1;
    });

    const t = I18N[currentLang] || I18N.he;
    document.querySelectorAll('.cat-pill').forEach((btn) => {
      const catKey = btn.getAttribute('data-cat');
      const baseName = t.cats && t.cats[catKey] ? t.cats[catKey] : catKey;
      const count = counts[catKey] || 0;
      btn.innerHTML = `${baseName} <span class="cat-count">(${count})</span>`;
    });
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

    if (priceFilterLabel) priceFilterLabel.textContent = t.priceFilterLabel;
    const btnAllPrice = document.querySelector('[data-price="all"]');
    const btnUnder50 = document.querySelector('[data-price="under50"]');
    const btn50_100 = document.querySelector('[data-price="50_100"]');
    const btn100_280 = document.querySelector('[data-price="100_280"]');
    if (btnAllPrice) btnAllPrice.textContent = t.priceAll;
    if (btnUnder50) btnUnder50.textContent = t.priceUnder50;
    if (btn50_100) btn50_100.textContent = t.price50_100;
    if (btn100_280) btn100_280.textContent = t.price100_280;

    const footerTitle = document.getElementById('footerTitle');
    const disclosureBox = document.getElementById('disclosureBox');
    if (footerTitle) footerTitle.textContent = t.footerTitle;
    if (disclosureBox) disclosureBox.textContent = t.disclosure;

    updateCategoryCounts();
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

      // Price filter (based on ILS price)
      const ilsPrice = Math.round(p.price_usd * 3.65);
      let matchPrice = true;
      if (currentPriceFilter === 'under50') {
        matchPrice = ilsPrice <= 50;
      } else if (currentPriceFilter === '50_100') {
        matchPrice = ilsPrice > 50 && ilsPrice <= 100;
      } else if (currentPriceFilter === '100_280') {
        matchPrice = ilsPrice > 100 && ilsPrice <= 300;
      }

      const q = currentSearch.trim().toLowerCase();
      if (!q) return matchCat && matchPrice;

      const hay = [
        p.title,
        getLocalizedField(p, 'title'),
        getLocalizedField(p, 'card_hook'),
        getLocalizedField(p, 'short_desc'),
        p.slug
      ]
        .join(' ')
        .toLowerCase();

      return matchCat && matchPrice && hay.includes(q);
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
          <div class="card-hook" onclick="window.openReview('${p.id}')" title="לחצו לצפייה בכל התמונות והמפרט">
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
    const gallery = p.gallery && p.gallery.length ? p.gallery : [p.image];

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

  document.querySelectorAll('.price-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.price-pill').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentPriceFilter = btn.getAttribute('data-price') || 'all';
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
