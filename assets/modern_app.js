/* Static content first. Filtering, currency estimates and accessible quick views. */
(() => {
  'use strict';
  const data = document.getElementById('products-db');
  if (!data) return;
  const DB = JSON.parse(data.textContent);
  const C = DB.copy;
  const lang = DB.lang;
  const script = document.currentScript;
  const root = new URL('../', script.src);
  const asset = path => new URL(path, root).href;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const storage = {
    get(key) {try {return localStorage.getItem(key);} catch {return null;}},
    set(key,value) {try {localStorage.setItem(key,value);} catch {}}
  };
  const rates = Object.fromEntries(Object.entries(DB.rates.rates || {USD:1}).filter(([,n]) => typeof n === 'number' && Number.isFinite(n) && n > 0));
  rates.USD = 1;
  let currency = Object.hasOwn(rates,storage.get('sp_cur')) ? storage.get('sp_cur') : 'USD';
  const currencySelect = document.getElementById('currency-select');
  if (currencySelect) currencySelect.value = currency;
  const money = usd => new Intl.NumberFormat(lang === 'he' ? 'he-IL' : lang, {style:'currency',currency,maximumFractionDigits:currency === 'RUB' ? 0 : 2}).format(Number(usd) * rates[currency]);
  function renderMoney() {
    document.querySelectorAll('[data-money]').forEach(el => {el.textContent = money(el.dataset.money);});
    const priceSelect = document.getElementById('price-select');
    if (priceSelect) for (const option of priceSelect.options) {
      if (option.value === 'all') continue;
      option.textContent = C[option.value === 'over50' ? 'over' : 'under'].replace('{price}',money(option.value === 'over50' ? 50 : Number(option.value)));
    }
    const ratesNote = document.getElementById('rates-note');
    if (ratesNote && currency !== 'USD') {
      let date = DB.rates.observed_at;
      try {date = new Intl.DateTimeFormat(lang,{dateStyle:'medium',timeZone:'UTC'}).format(new Date(date));} catch {date = '';}
      ratesNote.textContent = date ? `${C.rates}: ${date} · ExchangeRate-API` : '';
    } else if (ratesNote) ratesNote.textContent = '';
  }
  let toastTimer;
  window.DealVaultToast = text => {
    const el = document.getElementById('toast');
    el.textContent = text; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => {el.hidden = true;},3500);
  };
  currencySelect?.addEventListener('change', () => {
    if (Object.hasOwn(rates,currencySelect.value)) {currency = currencySelect.value; storage.set('sp_cur',currency); renderMoney();}
  });
  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme; storage.set('sp_theme',theme);
  });
  document.getElementById('clear-preferences')?.addEventListener('click', () => {
    try {for (const key of Object.keys(localStorage)) if (/^(sp_|dv_)/.test(key)) localStorage.removeItem(key);} catch {}
    try {for (const key of Object.keys(sessionStorage)) if (/^(sp_|dv_)/.test(key)) sessionStorage.removeItem(key);} catch {}
    location.reload();
  });
  const normalise = value => String(value).normalize('NFKD').replace(/[\u0300-\u036f\u0591-\u05c7]/g,'').toLocaleLowerCase();
  const grid = document.getElementById('product-grid');
  const cards = grid ? [...grid.querySelectorAll('.product-card')] : [];
  const input = document.getElementById('global-search-input');
  const budget = document.getElementById('price-select');
  const sort = document.getElementById('sort-select');
  const query = new URLSearchParams(location.search);
  let category = query.get('cat') || 'all';
  if (![...document.querySelectorAll('[data-cat]')].some(el => el.dataset.cat === category)) category = 'all';
  if (input) input.value = (query.get('q') || '').slice(0,200);
  if (budget && [...budget.options].some(o => o.value === query.get('budget'))) budget.value = query.get('budget');
  if (sort && [...sort.options].some(o => o.value === query.get('sort'))) sort.value = query.get('sort');
  function filter(updateUrl = true) {
    if (!grid) return;
    const words = normalise(input.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    const ordered = [...cards].sort((a,b) => sort.value === 'price_asc' ? Number(a.dataset.price)-Number(b.dataset.price) : sort.value === 'price_desc' ? Number(b.dataset.price)-Number(a.dataset.price) : Number(a.dataset.order)-Number(b.dataset.order));
    for (const card of ordered) {
      const price = Number(card.dataset.price);
      card.hidden = !((category === 'all' || card.dataset.category === category) &&
        (budget.value === 'all' || (budget.value === 'over50' ? price >= 50 : price < Number(budget.value))) &&
        words.every(word => normalise(card.dataset.search).includes(word)));
      if (!card.hidden) count++;
      grid.appendChild(card);
    }
    document.getElementById('items-counter').textContent = `${count} ${C.found}`;
    document.getElementById('empty-state').hidden = count !== 0;
    document.querySelectorAll('[data-cat]').forEach(el => {const selected = el.dataset.cat === category; el.classList.toggle('active',selected); el.setAttribute('aria-pressed',String(selected));});
    if (updateUrl) {
      const url = new URL(location.href);
      for (const [key,value] of Object.entries({q:input.value.trim(),cat:category === 'all' ? '' : category,budget:budget.value === 'all' ? '' : budget.value,sort:sort.value === 'curated' ? '' : sort.value})) {
        if (value) url.searchParams.set(key,value); else url.searchParams.delete(key);
      }
      history.replaceState(history.state,'',url);
    }
  }
  document.getElementById('category-nav')?.addEventListener('click', event => {const pill = event.target.closest('[data-cat]'); if (pill) {category = pill.dataset.cat; filter();}});
  input?.addEventListener('input', () => filter());
  budget?.addEventListener('change', () => filter());
  sort?.addEventListener('change', () => filter());
  document.getElementById('clear-filters')?.addEventListener('click', () => {category = 'all'; input.value = ''; budget.value = 'all'; sort.value = 'curated'; filter(); input.focus();});
  const dialog = document.getElementById('product-modal');
  let modalProduct = null;
  let returnFocus = null;
  function openModal(id, push = true) {
    const product = DB.products.find(p => p.id === id);
    if (!product || !dialog) return;
    if (!dialog.open) returnFocus = document.activeElement;
    modalProduct = product;
    const title = product.title_i18n[lang];
    document.getElementById('modal-content-area').innerHTML = `<div class="modal-layout"><a class="modal-photo" href="${esc(DB.paths[id])}"><img src="${esc(asset(product.image))}" width="600" height="600" alt="${esc(title)}"></a><div class="modal-details"><p class="eyebrow">DEALVAULT</p><h2 id="modal-title">${esc(title)}</h2><div class="deal-price"><span>${esc(C.reference)}</span><strong data-money="${product.price_usd}"></strong></div><p class="muted">${esc(C.price_note)}</p><a class="button primary" href="${esc(product.affiliate_url)}" target="_blank" rel="sponsored nofollow noopener" data-aff-id="${esc(id)}">${esc(C.shop)} ↗</a><p class="affiliate-note">${esc(C.affiliate)}</p><a class="detail-link" href="${esc(DB.paths[id])}">${esc(C.details)} ↗</a><div class="share-row" data-product-id="${esc(id)}"><button type="button" data-share="copy">${esc(C.copy)}</button><button type="button" data-share="whatsapp">WhatsApp</button><button type="button" data-share="telegram">Telegram</button></div></div></div>`;
    renderMoney();
    if (!dialog.open) dialog.showModal();
    document.body.style.overflow = 'hidden';
    if (push && location.hash !== '#' + product.slug) {const url = new URL(location.href); url.hash = product.slug; history.pushState({deal:product.slug},'',url);}
  }
  function clearModalHash() {
    if (DB.products.some(p => '#' + p.slug === location.hash)) {const url = new URL(location.href); url.hash = ''; history.replaceState(null,'',url);}
  }
  function closeModal(clearHash = true) {
    if (dialog?.open) dialog.close();
    document.body.style.overflow = '';
    modalProduct = null;
    if (clearHash) clearModalHash();
    if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
  }
  dialog?.addEventListener('cancel', event => {event.preventDefault(); closeModal();});
  dialog?.addEventListener('click', event => {if (event.target === dialog) {const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) closeModal();}});
  function syncHash() {let slug; try {slug = decodeURIComponent(location.hash.slice(1));} catch {return;} const p = DB.products.find(p => p.slug === slug); if (p && grid) openModal(p.id,false); else if (dialog?.open) closeModal(false);}
  window.addEventListener('popstate',syncHash);
  window.addEventListener('hashchange',syncHash);
  function canonicalProduct(product) {
    return `${DB.domain}/${lang === 'en' ? '' : lang + '/'}deals/${product.slug}`;
  }
  async function share(platform, product) {
    const url = canonicalProduct(product);
    const title = product.title_i18n[lang];
    if (platform === 'copy') {
      try {await navigator.clipboard.writeText(url); window.DealVaultToast(C.copied);} catch {window.DealVaultToast(`${C.copy_failed} ${url}`);}
    } else {
      const endpoint = platform === 'whatsapp' ? `https://api.whatsapp.com/send?text=${encodeURIComponent(title + '\n' + url)}` : `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;
      window.open(endpoint,'_blank','noopener,noreferrer');
    }
  }
  document.addEventListener('click', event => {
    const close = event.target.closest('[data-close-modal]');
    if (close) {closeModal(); return;}
    const quick = event.target.closest('[data-modal-id]');
    if (quick) {openModal(quick.dataset.modalId); return;}
    const shareButton = event.target.closest('[data-share]');
    if (shareButton) {const id = shareButton.closest('[data-product-id]')?.dataset.productId; const p = DB.products.find(x => x.id === id) || modalProduct; if (p) share(shareButton.dataset.share,p); return;}
    const link = event.target.closest('a[href]');
    if (link && !link.hasAttribute('data-aff-id')) {
      const url = new URL(link.href);
      if (url.origin === location.origin && !link.getAttribute('href').startsWith('#') && !url.pathname.startsWith('/assets/')) {
        for (const [key,value] of Object.entries(window.DealVaultCampaign || {})) if (!url.searchParams.has(key)) url.searchParams.set(key,value);
        link.href = url.href;
      }
    }
  });
  renderMoney(); filter(false); syncHash();
})();
