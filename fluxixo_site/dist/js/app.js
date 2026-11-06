(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const catalog = window.MiraCatalog.defaults();
  const products = catalog.products;
  const i18n = window.FluxixoI18n || {
    getLang: () => 'ru',
    setLang: l => l,
    t: k => '',
    localizeProduct: p => p,
    applyStaticUI: () => {},
    applyDocumentDirection: () => {}
  };
  const loc = p => i18n.localizeProduct(p, i18n.getLang());
  const mobileLayout = window.matchMedia('(max-width: 1100px), (max-height: 480px) and (pointer: coarse)');
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let motionPreference = '';
  try { motionPreference = localStorage.getItem('mira.motion.v1') || ''; } catch (_) {}
  let reduced = motionPreference ? motionPreference === 'quiet' : prefersReduced.matches;
  let active = Math.max(0, products.findIndex(p => '#' + p.id === location.hash));
  let targetIndex = active;
  let pending = null;
  let busy = false;
  let toastTimer;
  const dialogs = Array.from(document.querySelectorAll('dialog'));
  const stage = new window.MiraStage({
    stage: $('product-stage'), canvas: $('depth-dust'),
    planes: document.querySelectorAll('.product-plane'),
    rings: document.querySelectorAll('.depth-ring'), reducedMotion: reduced
  });
  const count = n => String(n).padStart(2, '0');
  const normalize = n => (n % products.length + products.length) % products.length;
  const current = () => loc(products[active]);
  const dialogOpen = () => dialogs.some(d => d.open);
  const forStage = product => {
    const lp = loc(product);
    return {image: lp.image, alt: lp.name, scale: lp.scale, rotation: lp.rotation};
  };
  const atmospheres = Array.from(document.querySelectorAll('.ambient-scene'));
  let atmosphereIndex = 0, atmosphereTheme = '', atmosphereAnimations = [], copyAnimation = null;

  function setAtmosphere(theme, animate) {
    if (!atmospheres.length || atmosphereTheme === theme) return;
    atmosphereAnimations.forEach(animation => animation.cancel());
    atmosphereAnimations = [];
    const previous = atmospheres[atmosphereIndex];
    const nextIndex = 1 - atmosphereIndex;
    const next = atmospheres[nextIndex];
    next.dataset.palette = theme;
    next.style.opacity = '1';
    previous.style.opacity = '0';
    if (animate && !reduced && next.animate) {
      atmosphereAnimations = [
        previous.animate([{opacity: 1}, {opacity: 0}], {duration: 500, easing: 'ease-out'}),
        next.animate([{opacity: 0}, {opacity: 1}], {duration: 500, easing: 'ease-out'})
      ];
    }
    atmosphereIndex = nextIndex;
    atmosphereTheme = theme;
  }

  function announce(message) { $('product-announcement').textContent = message; }
  function toast(message) {
    clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false;
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 5500);
  }
  function updateTitle(product) {
    const heading = $('product-heading'); heading.replaceChildren();
    product.headline.forEach(line => {
      const span = document.createElement('span');
      if (line.endsWith('.')) {
        span.append(document.createTextNode(line.slice(0, -1)));
        const dot = document.createElement('span'); dot.className = 'accent-dot'; dot.textContent = '.'; span.append(dot);
      } else span.textContent = line;
      heading.append(span);
    });
    heading.dataset.long = product.headline.some(s => s.length > 19) ? 'true' : 'false';
  }
  function updateCopy(index, announceChange = false) {
    active = index;
    const product = current();
    setAtmosphere(product.theme, announceChange);
    document.body.dataset.theme = product.theme;
    $('product-category').textContent = product.category;
    $('object-category').textContent = product.category;
    $('product-name').textContent = product.name;
    $('watch-explode-button').hidden = product.id !== 'import-0024';
    $('product-description').textContent = product.description;
    $('demo-label').hidden = !product.demo;
    updateTitle(product);
    const isAffiliate = !product.demo && Boolean(product.affiliateUrl);
    $('product-cta').hidden = !isAffiliate;
    $('demo-cta').hidden = isAffiliate;
    $('details-button').hidden = !isAffiliate;
    if (isAffiliate) $('product-cta').setAttribute('href', product.affiliateUrl);
    else $('product-cta').removeAttribute('href');
    $('affiliate-note').textContent = isAffiliate
      ? (i18n.t('affiliateNote') || 'Партнёрская ссылка. Мы можем получить комиссию за покупку.')
      : product.pendingLink ? (i18n.t('ctaPending') || 'Ссылка на продавца уточняется.') : 'Демонстрационный предмет.';
    $('large-index').textContent = count(index + 1);
    $('large-total').textContent = count(products.length);
    $('collection-count').textContent = count(products.length);
    renderRail(index);
    document.title = 'FLUXIXO — ' + product.name;
    try {
      const address = new URL(location.href);
      if (i18n.getLang() !== 'en' || address.searchParams.has('lang')) address.searchParams.set('lang', i18n.getLang());
      address.hash = product.id;
      history.replaceState(null, '', address);
    } catch (_) {}
    if (announceChange) announce(product.name + ' (' + (index + 1) + '/' + products.length + ')');
    stage.preload([products[normalize(index + 1)], products[normalize(index - 1)]]);
  }
  async function navigate(index, direction) {
    index = normalize(index);
    if (busy) { pending = {index, direction}; return; }
    if (index === active) return;
    window.MiraWatch.reset();
    busy = true; targetIndex = index;
    $('showroom').setAttribute('aria-busy', 'true');
    $('watch-explode-button').disabled = true;
    $('details-button').disabled = $('demo-cta').disabled = true;
    $('product-cta').setAttribute('aria-disabled', 'true');
    try {
      await stage.transitionTo(forStage(products[index]), direction || 1, () => {
        if (copyAnimation) copyAnimation.cancel();
        updateCopy(index, true);
        if ($('product-copy').animate) copyAnimation = $('product-copy').animate(
          reduced ? [{opacity: 0}, {opacity: 1}] : [{opacity: 0, transform: 'translateY(7px)'}, {opacity: 1, transform: 'translateY(0)'}],
          {duration: reduced ? 100 : 240, easing: 'cubic-bezier(.2,.7,.2,1)'}
        );
      });
    } catch (_) {
      stage.setInitial(forStage(products[index])); updateCopy(index, true);
      toast('Предмет открыт без анимации.');
    } finally {
      if (copyAnimation) { copyAnimation.cancel(); copyAnimation = null; }
      $('showroom').removeAttribute('aria-busy');
      $('watch-explode-button').disabled = false;
      $('details-button').disabled = $('demo-cta').disabled = false;
      $('product-cta').removeAttribute('aria-disabled');
      busy = false; targetIndex = active;
      if (pending) { const next = pending; pending = null; navigate(next.index, next.direction); }
    }
  }
  function step(direction) {
    if (products.length < 2 || dialogOpen()) return;
    const base = pending ? pending.index : busy ? targetIndex : active;
    navigate(base + direction, direction);
  }
  function direct(index) {
    const forward = (index - active + products.length) % products.length;
    navigate(index, forward <= products.length / 2 ? 1 : -1);
  }
  function renderRail(index) {
    const rail = $('product-rail');
    const focusedIndex = document.activeElement?.dataset?.productIndex;
    rail.replaceChildren();
    const indices = products.length <= 3 ? products.map((_, i) => i) : [normalize(index - 1), index, normalize(index + 1)];
    indices.forEach(i => {
      const product = loc(products[i]);
      const button = document.createElement('button');
      button.className = 'rail-item';
      button.dataset.productIndex = String(i);
      button.setAttribute('aria-label', product.name);
      button.setAttribute('aria-current', i === index ? 'true' : 'false');
      button.title = product.name;
      const image = document.createElement('img');
      image.src = product.image; image.alt = ''; image.draggable = false;
      button.append(image);
      button.addEventListener('click', () => direct(i));
      rail.append(button);
    });
    if (focusedIndex !== undefined) {
      const target = Array.from(rail.children).find(b => b.dataset.productIndex === focusedIndex) || rail.querySelector('[aria-current="true"]');
      target?.focus({preventScroll: true});
    }
  }
  function createNav() {
    renderRail(active);
    $('collection-grid').replaceChildren();
    products.forEach((rawProduct, i) => {
      const product = loc(rawProduct);
      const card = document.createElement('button'); card.className = 'collection-card';
      const number = document.createElement('span'); number.className = 'card-number'; number.textContent = count(i + 1);
      const picture = document.createElement('img'); picture.loading = 'lazy'; picture.decoding = 'async'; picture.src = product.image; picture.alt = '';
      const name = document.createElement('strong'); name.textContent = product.name;
      const category = document.createElement('span'); category.className = 'card-category'; category.textContent = product.category;
      const status = document.createElement('span'); status.className = 'card-status'; status.textContent = product.pendingLink ? (i18n.t('ctaPending') || 'Ссылка уточняется') : product.demo ? 'Demo' : 'AliExpress';
      card.append(number, picture, name, category, status);
      card.addEventListener('click', () => { $('collection-dialog').close(); direct(i); });
      $('collection-grid').append(card);
    });
    $('previous-button').disabled = $('next-button').disabled = products.length < 2;
  }
  function openDialog(dialog) {
    stage.setPaused(true);
    dialog.showModal();
    dialog.scrollTop = 0;
  }
  function openDetails() {
    const product = current();
    $('details-title').textContent = product.name;
    $('details-category').textContent = product.category;
    $('details-status').textContent = product.pendingLink ? (i18n.t('ctaPending') || 'Ссылка уточняется') : 'FLUXIXO · AliExpress';
    $('details-image').src = product.image; $('details-image').alt = product.name;
    $('details-image-label').textContent = i18n.t('sceneCaption') || product.imageNote;
    $('details-description').textContent = product.description || product.details;
    $('details-facts').replaceChildren();
    product.facts.forEach(f => {
      const dt = document.createElement('dt'); dt.textContent = f.label;
      const dd = document.createElement('dd'); dd.textContent = f.value;
      $('details-facts').append(dt, dd);
    });
    $('details-cta').hidden = product.demo || !product.affiliateUrl;
    if (!product.demo && product.affiliateUrl) $('details-cta').setAttribute('href', product.affiliateUrl);
    else $('details-cta').removeAttribute('href');
    $('details-disclosure').textContent = i18n.t('affiliateNote') || 'Партнёрская ссылка AliExpress.';
    $('source-details').hidden = !product.original;
    $('source-details').open = false;
    if (product.original) $('source-image').src = product.original;
    else $('source-image').removeAttribute('src');
    openDialog($('details-dialog'));
  }
  dialogs.forEach(dialog => {
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
      if (!dialogOpen()) {
        stage.setPaused(window.MiraWatch.active);
      }
    });
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
  });
  $('collection-button').addEventListener('click', () => openDialog($('collection-dialog')));
  $('about-button').addEventListener('click', () => openDialog($('about-dialog')));
  $('details-button').addEventListener('click', openDetails);
  $('watch-explode-button').addEventListener('click', () => {
    if (busy || current().id !== 'import-0024') return;
    window.MiraWatch.toggle(stage);
  });
  $('product-cta').addEventListener('click', event => { if (busy) event.preventDefault(); });
  $('demo-cta').addEventListener('click', openDetails);
  $('home-button').addEventListener('click', () => direct(0));
  $('next-button').addEventListener('click', () => step(1));
  $('previous-button').addEventListener('click', () => step(-1));

  function applyMotion() {
    if (reduced) {
      atmosphereAnimations.forEach(animation => animation.cancel());
      atmosphereAnimations = [];
    }
    document.body.classList.toggle('is-reduced', reduced);
    $('motion-button').setAttribute('aria-pressed', String(reduced));
    $('motion-button').querySelector('span').textContent = reduced ? (i18n.t('motionMore') || 'Включить движение') : (i18n.t('motionLess') || 'Меньше движения');
    $('motion-button').title = reduced ? (i18n.t('motionMore') || 'Включить движение') : (i18n.t('motionLess') || 'Меньше движения');
    $('stage-hint').lastChild.textContent = ' ' + (reduced ? (i18n.t('stageHintQuiet') || 'Спокойный режим') : window.matchMedia('(pointer: coarse)').matches ? (i18n.t('stageHintTouch') || 'Свайпни влево или вправо') : (i18n.t('stageHintMouse') || 'Наведи, чтобы изменить ракурс'));
    stage.setReducedMotion(reduced);
  }
  $('motion-button').addEventListener('click', () => {
    reduced = !reduced; motionPreference = reduced ? 'quiet' : 'full';
    try { localStorage.setItem('mira.motion.v1', motionPreference); } catch (_) {}
    applyMotion();
  });
  prefersReduced.addEventListener('change', event => { if (!motionPreference) { reduced = event.matches; applyMotion(); } });

  const langSelect = $('lang-select');
  if (langSelect) {
    langSelect.value = i18n.getLang();
    langSelect.addEventListener('change', event => {
      i18n.setLang(event.target.value);
      createNav();
      updateCopy(active, false);
      applyMotion();
      if ($('details-dialog').open) openDetails();
    });
  }

  let wheelSum = 0, wheelLatched = false, wheelReset;
  $('showroom').addEventListener('wheel', event => {
    if (mobileLayout.matches || event.ctrlKey || event.metaKey || dialogOpen() || event.target.closest('a,button,input,textarea,select')) return;
    if (Math.abs(event.deltaY) < Math.abs(event.deltaX)) return;
    event.preventDefault();
    clearTimeout(wheelReset);
    wheelReset = setTimeout(() => { wheelSum = 0; wheelLatched = false; }, 220);
    if (wheelLatched || busy) return;
    const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? innerHeight : 1);
    wheelSum += Math.max(-150, Math.min(150, delta));
    if (Math.abs(wheelSum) > 48) { wheelLatched = true; step(wheelSum > 0 ? 1 : -1); wheelSum = 0; }
  }, {passive: false});
  window.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || dialogOpen() || event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
    if (mobileLayout.matches && ['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End'].includes(event.key)) return;
    const keys = {ArrowRight: 1, ArrowDown: 1, PageDown: 1, ArrowLeft: -1, ArrowUp: -1, PageUp: -1};
    if (keys[event.key]) { event.preventDefault(); if (!event.repeat) step(keys[event.key]); }
    else if (event.key === 'Home') { event.preventDefault(); direct(0); }
    else if (event.key === 'End') { event.preventDefault(); direct(products.length - 1); }
  });
  let touchStart = null;
  $('showroom').addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' || !event.isPrimary || dialogOpen() || event.target.closest('a,button,input,textarea,select,summary')) return;
    touchStart = {x: event.clientX, y: event.clientY, id: event.pointerId};
    try { $('showroom').setPointerCapture(event.pointerId); } catch (_) {}
  });
  $('showroom').addEventListener('pointerup', event => {
    if (!touchStart || touchStart.id !== event.pointerId) return;
    const dx = event.clientX - touchStart.x, dy = event.clientY - touchStart.y; touchStart = null;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.2) step(dx < 0 ? 1 : -1);
  });
  $('showroom').addEventListener('pointercancel', () => { touchStart = null; });
  window.addEventListener('hashchange', () => {
    const found = products.findIndex(p => '#' + p.id === location.hash);
    if (found >= 0 && found !== active) direct(found);
  });
  window.addEventListener('pagehide', () => stage.setPaused(true));
  window.addEventListener('pageshow', () => { if (!dialogOpen()) stage.setPaused(window.MiraWatch.active); });
  i18n.applyDocumentDirection(i18n.getLang());
  i18n.applyStaticUI(i18n.getLang());
  createNav(); updateCopy(active); stage.setInitial(forStage(products[active])); applyMotion();
})();
