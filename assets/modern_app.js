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
  let saved;
  try {const raw=JSON.parse(storage.get('dv_saved') || '[]'); saved=new Set(Array.isArray(raw)?raw.filter(x=>typeof x==='string' && x.length<100).slice(0,5000):[]);} catch {saved=new Set();}
  const savedFilter=document.getElementById('saved-filter');
  let onlySaved=false;
  function paintSaved() {
    document.querySelectorAll('[data-save-id]').forEach(button=>{const active=saved.has(button.dataset.saveId);button.setAttribute('aria-pressed',String(active));button.textContent=active?'♥':'♡';});
    const counter=document.getElementById('saved-count');if(counter)counter.textContent=String(saved.size);
  }
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const motionButton=document.getElementById('motion-toggle');
  function paintMotion() {
    if(!motionButton)return;
    const paused=document.documentElement.dataset.motion==='off';
    motionButton.hidden=reduced.matches;
    motionButton.setAttribute('aria-pressed',String(paused));
    motionButton.setAttribute('aria-label',paused?C.motion_resume:C.motion);
    motionButton.title=paused?C.motion_resume:C.motion;
    motionButton.textContent=paused?'▷':'Ⅱ';
  }
  motionButton?.addEventListener('click',()=>{const next=document.documentElement.dataset.motion==='off'?'on':'off';document.documentElement.dataset.motion=next;storage.set('dv_motion',next);paintMotion();});
  reduced.addEventListener('change',paintMotion);
  document.addEventListener('visibilitychange',()=>{document.documentElement.dataset.pageHidden=String(document.hidden);});
  const stage=document.querySelector('.orbit-stage');
  if(stage && 'IntersectionObserver' in window)new IntersectionObserver(entries=>{document.documentElement.dataset.heroVisible=String(entries[0].isIntersecting);},{rootMargin:'30px'}).observe(stage);
  paintMotion();paintSaved();
  const countrySelect=document.getElementById('country-select');
  if(countrySelect) {
    const valid=[...countrySelect.options].some(o=>o.value===storage.get('dv_country'));
    countrySelect.value=valid?storage.get('dv_country'):'';
    const updateCountry=()=>{const name=countrySelect.selectedOptions[0].textContent;document.getElementById('market-note').textContent=countrySelect.value?C.market_selected.replace('{country}',name):C.market_note;};
    countrySelect.addEventListener('change',()=>{storage.set('dv_country',countrySelect.value);updateCountry();});updateCountry();
  }
  let toastTimer;
  window.DealVaultToast = text => {
    const el = document.getElementById('toast');
    el.textContent = text; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => {el.hidden = true;},3500);
  };
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
  const query = new URLSearchParams(location.search);
  let category = query.get('cat') || 'all';
  if (![...document.querySelectorAll('[data-cat]')].some(el => el.dataset.cat === category)) category = 'all';
  onlySaved=query.get('saved')==='1';
  if(savedFilter)savedFilter.setAttribute('aria-pressed',String(onlySaved));
  if (input) input.value = (query.get('q') || '').slice(0,200);
  const searchText=new Map(cards.map(card=>[card,normalise(card.dataset.search)]));
  function filter(updateUrl = true) {
    if (!grid) return;
    const words = normalise(input.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const card of cards) {
      card.hidden = !((!onlySaved || saved.has(card.dataset.id)) && (category === 'all' || card.dataset.category === category) &&
        words.every(word => searchText.get(card).includes(word)));
      if (!card.hidden) count++;
    }
    document.querySelector('#empty-state h3').textContent=onlySaved?C.saved_empty:C.empty;
    document.getElementById('items-counter').textContent = `${count} ${C.found}`;
    document.getElementById('empty-state').hidden = count !== 0;
    document.querySelectorAll('[data-cat]').forEach(el => {const selected = el.dataset.cat === category; el.classList.toggle('active',selected); el.setAttribute('aria-pressed',String(selected));});
    if (updateUrl) {
      const url = new URL(location.href);
      for (const [key,value] of Object.entries({saved:onlySaved?'1':'',q:input.value.trim(),cat:category === 'all' ? '' : category,budget:'',sort:''})) {
        if (value) url.searchParams.set(key,value); else url.searchParams.delete(key);
      }
      history.replaceState(history.state,'',url);
    }
  }
  document.getElementById('category-nav')?.addEventListener('click', event => {const pill = event.target.closest('[data-cat]'); if (pill) {category = pill.dataset.cat; filter();}});
  savedFilter?.addEventListener('click',()=>{onlySaved=!onlySaved;savedFilter.setAttribute('aria-pressed',String(onlySaved));filter();});
  input?.addEventListener('input', () => filter());
  document.getElementById('clear-filters')?.addEventListener('click', () => {category = 'all'; onlySaved=false; savedFilter?.setAttribute('aria-pressed','false'); input.value = ''; filter(); input.focus();});
  const dialog = document.getElementById('product-modal');
  let modalProduct = null;
  let returnFocus = null;
  function openModal(id, push = true) {
    const product = DB.products.find(p => p.id === id);
    if (!product || !dialog) return;
    if (!dialog.open) returnFocus = document.activeElement;
    modalProduct = product;
    const title = product.title_i18n[lang];
    document.getElementById('modal-content-area').innerHTML = `<div class="modal-layout"><a class="modal-photo" href="${esc(DB.paths[id])}"><img src="${esc(asset(product.image))}" width="600" height="600" alt="${esc(title)}"></a><div class="modal-details"><p class="eyebrow">DEALVAULT${product.is_new ? ' · <span class="deal-badge-new">✦ ' + esc(C.new_badge || 'NEW') + '</span>' : ''}</p><h2 id="modal-title">${esc(title)}</h2><p class="muted">${esc(product.use_i18n?.[lang] || '')}</p><p class="price-unavailable price-unavailable-detail">${esc(C.price_status)}</p><p class="muted">${esc(C.price_note)}</p><a class="button primary" href="${esc(product.affiliate_url)}" target="_blank" rel="sponsored nofollow noopener" data-aff-id="${esc(id)}">${esc(C.shop)} ↗</a><p class="affiliate-note">${esc(C.affiliate)}</p><a class="detail-link" href="${esc(DB.paths[id])}">${esc(C.details)} ↗</a><div class="share-row" data-product-id="${esc(id)}"><button type="button" data-share="copy">${esc(C.copy)}</button><button type="button" data-share="whatsapp">WhatsApp</button><button type="button" data-share="telegram">Telegram</button></div></div></div>`;
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
    const saveButton=event.target.closest('[data-save-id]');
    if(saveButton){const id=saveButton.dataset.saveId;if(saved.has(id))saved.delete(id);else saved.add(id);storage.set('dv_saved',JSON.stringify([...saved]));paintSaved();if(onlySaved)filter();return;}
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
 filter(false); syncHash();
})();
