(() => {
  const root = document.documentElement;
  const lang = root.lang || 'en';
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.add('js');

  // Sections fade up once.
  const seen = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('in'); seen.unobserve(entry.target); }
  }), { rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.rv').forEach(el => seen.observe(el));

  // The section in the middle of the screen decides the page colour.
  const paint = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) document.body.style.setProperty('--page', entry.target.dataset.page);
  }), { rootMargin: '-50% 0px -50% 0px' });
  document.querySelectorAll('[data-page]').forEach(el => paint.observe(el));

  // Date and countdown to the next drop (the daily job runs at 08:00 UTC).
  document.querySelectorAll('[data-today]').forEach(el => {
    el.textContent = new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'long' }).format(new Date());
  });
  const clocks = document.querySelectorAll('[data-countdown]');
  if (clocks.length) {
    const pad = n => String(n).padStart(2, '0');
    const update = () => {
      const now = new Date();
      const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 8));
      if (next <= now) next.setUTCDate(next.getUTCDate() + 1);
      const s = Math.floor((next - now) / 1000);
      const text = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
      clocks.forEach(el => { el.textContent = text; });
    };
    update(); setInterval(update, 1000);
  }

  // One loop: scroll speed swings the hanging products and softens the grid; scroll position drives the pinned scene.
  const hangs = [...document.querySelectorAll('.hang')].map((el, i) => ({ el, a: 0, v: 0, phase: i * 1.7, shown: 0 }));
  hangs.forEach(h => h.el.addEventListener('pointerenter', e => { h.v += (e.movementX || 6) > 0 ? 3 : -3; }));
  const day = document.querySelector('.day');
  let last = scrollY, speed = 0, blur = 0;
  const frame = time => {
    const dy = scrollY - last; last = scrollY;
    speed += (dy - speed) * 0.12;
    if (!calm) {
      for (const h of hangs) {
        h.v += -h.a * 0.035 - h.v * 0.045 + Math.max(-3, Math.min(3, dy * 0.02));
        h.a = Math.max(-16, Math.min(16, h.a + h.v));
        const angle = h.a + Math.sin(time / 1300 + h.phase) * 1.4;
        if (Math.abs(angle - h.shown) > 0.02) { h.shown = angle; h.el.style.setProperty('--a', angle.toFixed(2)); }
      }
      const b = Math.min(Math.abs(speed) / 45, 1);
      if (Math.abs(b - blur) > 0.02) { blur = b < 0.03 ? 0 : b; root.style.setProperty('--blur', blur.toFixed(2)); }
    }
    if (day) {
      const rect = day.getBoundingClientRect();
      const p = Math.max(0, Math.min(1, -rect.top / (rect.height - innerHeight)));
      day.style.setProperty('--p', calm ? 1 : p.toFixed(4));
      day.classList.toggle('live', calm || p > 0.6);
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);

  // Seller photo: tap the polaroid to enlarge it.
  document.querySelectorAll('.pola').forEach(card => card.addEventListener('click', () => card.classList.toggle('big')));

  // Filter the full grid by world.
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    const world = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    document.querySelectorAll('.grid [data-w]').forEach(card => { card.hidden = world !== '*' && card.dataset.w !== world; });
  }));

  // The clicked product image morphs into the hero of its page.
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-go]');
    const image = link && link.querySelector('img');
    if (image) image.style.viewTransitionName = 'hero-p';
  }, true);

  // Phone: the buy button follows whenever the main one is off screen.
  const main = document.querySelector('[data-main-cta]');
  const sticky = document.querySelector('.sticky');
  if (main && sticky) new IntersectionObserver(([entry]) => sticky.classList.toggle('show', !entry.isIntersecting)).observe(main);

  // Product pages: swipe sideways for the previous or next find.
  const hero = document.querySelector('[data-swipe]');
  if (hero) {
    let x0 = 0, y0 = 0;
    hero.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    hero.addEventListener('touchend', e => {
      const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
      if (Math.abs(dx) > 80 && Math.abs(dy) < 50) {
        const target = hero.dataset[dx < 0 ? 'next' : 'prev'];
        if (target) location.href = target;
      }
    }, { passive: true });
  }
})();
