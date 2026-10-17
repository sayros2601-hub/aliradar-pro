// AliRadar PRO — Zero-Dependency Interactive Client Engine
(function () {
  let products = window.__INITIAL_PRODUCTS__ || [];
  let currentCategory = 'all';
  let currentSearch = '';
  let currentSort = 'popular';
  let currency = 'RUB'; // 'RUB' or 'USD'

  const gridEl = document.getElementById('productGrid');
  const searchInput = document.getElementById('searchInput');
  const sortSelect = document.getElementById('sortSelect');
  const currencyBtn = document.getElementById('currencyBtn');
  const themeBtn = document.getElementById('themeBtn');
  const modalBackdrop = document.getElementById('reviewModal');
  const modalContent = document.getElementById('modalContent');

  function formatPrice(p) {
    if (currency === 'RUB') {
      return p.price_rub.toLocaleString('ru-RU') + ' ₽';
    }
    return '$' + p.price_usd.toFixed(2);
  }

  function formatOldPrice(p) {
    if (currency === 'RUB') {
      return p.old_price_rub.toLocaleString('ru-RU') + ' ₽';
    }
    return '$' + p.old_price_usd.toFixed(2);
  }

  function renderProducts() {
    if (!gridEl) return;
    let filtered = products.filter((p) => {
      const matchCat = currentCategory === 'all' || p.category === currentCategory;
      const q = currentSearch.trim().toLowerCase();
      const matchSearch =
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.short_desc.toLowerCase().includes(q) ||
        (p.seo_keywords && p.seo_keywords.toLowerCase().includes(q));
      return matchCat && matchSearch;
    });

    if (currentSort === 'price_asc') {
      filtered.sort((a, b) => a.price_usd - b.price_usd);
    } else if (currentSort === 'discount') {
      filtered.sort((a, b) => b.discount_pct - a.discount_pct);
    } else if (currentSort === 'rating') {
      filtered.sort((a, b) => b.rating - a.rating);
    }

    if (filtered.length === 0) {
      gridEl.innerHTML =
        '<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);">Ничего не найдено по вашему запросу. Попробуйте выбрать другую категорию.</div>';
      return;
    }

    gridEl.innerHTML = filtered
      .map(
        (p) => `
      <article class="product-card" data-category="${p.category}">
        <div class="card-media">
          <img src="${p.image}" alt="${p.title}" loading="lazy" width="400" height="220" />
          <span class="card-badge">${p.badge}</span>
          <span class="card-discount">-${p.discount_pct}%</span>
          <span class="card-updated">⟳ ${p.updated_at}</span>
        </div>
        <div class="card-body">
          <div class="card-meta-row">
            <span class="rating-pill">★ ${p.rating} (${p.reviews_count.toLocaleString('ru-RU')} отз.)</span>
            <span>Заказов: ${p.orders_count}</span>
          </div>
          <h3 class="card-title">${p.title}</h3>
          <p class="card-desc">${p.short_desc}</p>
          <div class="price-box">
            <div>
              <span class="price-main">${formatPrice(p)}</span>
              <span class="price-old">${formatOldPrice(p)}</span>
              <span class="price-trend">✓ ${p.price_trend}</span>
            </div>
            <button class="coupon-btn" onclick="window.copyCoupon('${p.coupon_code}', this)" title="Скопировать промокод">
              ✂ ${p.coupon_code}
            </button>
          </div>
          <div class="card-actions">
            <button class="btn-review" onclick="window.openReview('${p.id}')">Честный обзор</button>
            <a class="btn-buy" href="${p.affiliate_url}" target="_blank" rel="nofollow sponsored noopener">
              Купить на Ali ↗
            </a>
          </div>
        </div>
      </article>
    `
      )
      .join('');
  }

  window.copyCoupon = function (code, btnEl) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(code);
    }
    const orig = btnEl.innerHTML;
    btnEl.innerHTML = '✓ Скопировано!';
    btnEl.style.borderColor = '#10b981';
    btnEl.style.color = '#10b981';
    setTimeout(() => {
      btnEl.innerHTML = orig;
      btnEl.style.borderColor = '';
      btnEl.style.color = '';
    }, 1800);
  };

  window.openReview = function (id) {
    const p = products.find((item) => item.id === id);
    if (!p || !modalBackdrop || !modalContent) return;
    modalContent.innerHTML = `
      <button class="modal-close" onclick="window.closeReview()">✕</button>
      <div class="hero-kicker" style="margin-bottom:10px;">${p.badge} • Скидка ${p.discount_pct}%</div>
      <h2 style="font-size:1.4rem;margin-bottom:10px;">${p.title}</h2>
      <p style="color:var(--text-muted);font-size:0.94rem;margin-bottom:16px;">${p.short_desc}</p>
      <div class="pros-cons-grid">
        <div class="pros-box">
          <strong style="color:#10b981;">✓ Плюсы по отзывам покупателей:</strong>
          <ul>${(p.pros || []).map((x) => `<li>${x}</li>`).join('')}</ul>
        </div>
        <div class="cons-box">
          <strong style="color:#f43f5e;">✗ Нюансы и минусы:</strong>
          <ul>${(p.cons || []).map((x) => `<li>${x}</li>`).join('')}</ul>
        </div>
      </div>
      <div style="padding:14px;border-radius:12px;background:rgba(255,255,255,0.04);border:1px solid var(--border-subtle);margin-bottom:18px;">
        <strong>Вердикт AliRadar PRO:</strong>
        <p style="color:var(--text-muted);font-size:0.9rem;margin-top:4px;">${p.verdict}</p>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;">
        <div>
          <span class="price-main" style="font-size:1.6rem;">${formatPrice(p)}</span>
          <span class="price-old">${formatOldPrice(p)}</span>
          <span class="price-trend">Купон продавца: <strong>${p.coupon_code}</strong></span>
        </div>
        <div style="display:flex;gap:10px;">
          <a class="btn-ghost" href="deals/${p.slug}.html">Открыть SEO-страницу</a>
          <a class="btn-buy" style="padding:13px 24px;font-size:0.95rem;" href="${p.affiliate_url}" target="_blank" rel="nofollow sponsored noopener">
            Перейти на AliExpress ↗
          </a>
        </div>
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

  document.querySelectorAll('.cat-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.getAttribute('data-cat') || 'all';
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

  if (currencyBtn) {
    currencyBtn.addEventListener('click', () => {
      currency = currency === 'RUB' ? 'USD' : 'RUB';
      currencyBtn.textContent = currency === 'RUB' ? '₽ RUB' : '$ USD';
      renderProducts();
    });
  }

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const root = document.documentElement;
      const isLight = root.getAttribute('data-theme') === 'light';
      root.setAttribute('data-theme', isLight ? 'dark' : 'light');
      themeBtn.textContent = isLight ? '🌙 Тёмная' : '☀️ Светлая';
    });
  }
})();
