/* Runs immediately after the hero markup, before first paint. No slideshow. */
(() => {
  'use strict';
  const link = document.querySelector('[data-hero-id]');
  const source = document.getElementById('hero-candidates');
  if (!link || !source) return;
  const candidates = JSON.parse(source.textContent);
  if (!candidates.length) return;
  const key = 'dv_hero_history_v1';
  // Persist across visits; fall back to this tab if persistent storage is blocked.
  const stores = [];
  for (const name of ['localStorage', 'sessionStorage']) {
    try {
      const store = window[name];
      store.setItem(key + '_probe', '1');
      store.removeItem(key + '_probe');
      stores.push(store);
    } catch {}
  }
  const valid = new Set(candidates.map(p => p.key));
  let seen, last;
  function readHistory() {
    let state = {};
    for (const store of stores) {
      try {
        const parsed = JSON.parse(store.getItem(key) || 'null');
        if (parsed && Array.isArray(parsed.seen)) { state = parsed; break; }
      } catch {}
    }
    seen = new Set((state.seen || []).filter(x => valid.has(x)));
    last = valid.has(state.last) ? state.last : null;
  }
  const attempted = new Set();
  const photo = link.querySelector('img');
  const title = link.querySelector('.spotlight-bottom > span');
  function choose() {
    let remaining = candidates.filter(p => !seen.has(p.key) && !attempted.has(p.key));
    if (!remaining.length) {
      seen = new Set();
      remaining = candidates.filter(p => !attempted.has(p.key));
    }
    if (!remaining.length) return; // Keep the meaningful product title/link on failure.
    const different = remaining.filter(p => p.key !== last);
    if (different.length) remaining = different;
    const next = remaining[Math.floor(Math.random() * remaining.length)];
    attempted.add(next.key);
    seen.add(next.key);
    last = next.key;
    const value = JSON.stringify({seen: [...seen], last});
    for (const store of stores) { try { store.setItem(key, value); } catch {} }
    // Update the whole product together; never put another photo on an old link.
    link.href = next.href;
    link.dataset.heroId = next.id;
    title.textContent = next.title;
    title.title = next.title;
    photo.alt = next.title;
    photo.src = next.image;
  }
  photo.addEventListener('error', choose);
  window.addEventListener('pageshow', event => {
    if (event.persisted) { readHistory(); attempted.clear(); choose(); }
  });
  readHistory();
  choose();
})();
