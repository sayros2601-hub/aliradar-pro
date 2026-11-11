(() => {
  const root = document.documentElement;
  const lang = root.lang || 'en';
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Phones and small tablets get the app layout: no pinned scene, no swinging, no repainting.
  const phone = matchMedia('(max-width: 860px)');
  root.classList.add('js');

  // Sections fade up once.
  const seen = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('in'); seen.unobserve(entry.target); }
  }), { rootMargin: '0px 0px -4% 0px' });
  document.querySelectorAll('.rv').forEach(el => seen.observe(el));

  // Wide screens: the section in the middle of the screen decides the page colour.
  const paint = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting && !phone.matches) document.body.style.setProperty('--page', entry.target.dataset.page);
  }), { rootMargin: '-50% 0px -50% 0px' });
  document.querySelectorAll('[data-page]').forEach(el => paint.observe(el));

  // The date of the latest real drop (a UTC day from the daily job's ledger), in the visitor's language.
  document.querySelectorAll('[data-day]').forEach(el => {
    const day = new Date(el.getAttribute('datetime') + 'T12:00:00Z');
    if (!isNaN(day)) el.textContent = new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(day);
  });
  // Next drop: "today" while today's has not landed yet, otherwise "tomorrow".
  document.querySelectorAll('[data-next]').forEach(el => {
    const [today, tomorrow] = el.dataset.when.split('|');
    el.textContent = el.dataset.next >= new Date().toISOString().slice(0, 10) ? tomorrow : today;
  });

  // Wide screens, one loop: scroll speed swings the hanging products; scroll position drives the pinned scene.
  const hangs = [...document.querySelectorAll('.hang')].map((el, i) => ({ el, a: 0, v: 0, phase: i * 1.7, shown: 0 }));
  hangs.forEach(h => h.el.addEventListener('pointerenter', e => { h.v += (e.movementX || 6) > 0 ? 3 : -3; }));
  const day = document.querySelector('.day');
  let last = scrollY, running = false;
  const frame = time => {
    if (phone.matches) { running = false; return; }
    const dy = scrollY - last; last = scrollY;
    if (!calm) {
      for (const h of hangs) {
        h.v += -h.a * 0.035 - h.v * 0.045 + Math.max(-3, Math.min(3, dy * 0.02));
        h.a = Math.max(-16, Math.min(16, h.a + h.v));
        const angle = h.a + Math.sin(time / 1300 + h.phase) * 1.4;
        if (Math.abs(angle - h.shown) > 0.02) { h.shown = angle; h.el.style.setProperty('--a', angle.toFixed(2)); }
      }
    }
    if (day) {
      const rect = day.getBoundingClientRect();
      const p = Math.max(0, Math.min(1, -rect.top / (rect.height - innerHeight)));
      day.style.setProperty('--p', calm ? 1 : p.toFixed(4));
      day.classList.toggle('live', calm || p > 0.6);
    }
    requestAnimationFrame(frame);
  };
  const loop = () => {
    if (!phone.matches && !running && (hangs.length || day)) { running = true; last = scrollY; requestAnimationFrame(frame); }
  };
  phone.addEventListener('change', loop);
  loop();

  // Swipe rows: dots show which card is in view and jump to it; product galleries also get arrows.
  document.querySelectorAll('[data-dots]').forEach(row => {
    const cards = [...row.children].filter(el => el.tagName !== 'svg');
    if (cards.length < 2) return;
    const dots = document.createElement('div');
    dots.className = 'dots';
    dots.setAttribute('aria-hidden', 'true');
    dots.innerHTML = cards.map((_, i) => `<i${i ? '' : ' class="on"'}></i>`).join('');
    row.after(dots);
    let current = 0;
    const go = i => {
      const card = cards[Math.max(0, Math.min(cards.length - 1, i))];
      row.scrollTo({ left: row.scrollLeft + card.getBoundingClientRect().left - row.getBoundingClientRect().left
        - (row.clientWidth - card.offsetWidth) / 2, behavior: calm ? 'auto' : 'smooth' });
    };
    [...dots.children].forEach((dot, i) => dot.addEventListener('click', () => go(i)));
    const frame = row.parentElement.matches('.p-gallery') ? row.parentElement : null;
    const arrows = [];
    if (frame) {
      ['prev', 'next'].forEach((name, k) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'arrow ' + name;
        button.setAttribute('aria-label', frame.dataset[name === 'prev' ? 'labelPrev' : 'labelNext'] || name);
        button.textContent = (k ? 1 : -1) * (root.dir === 'rtl' ? -1 : 1) > 0 ? '→' : '←';
        button.addEventListener('click', () => go(current + (k ? 1 : -1)));
        frame.append(button);
        arrows.push(button);
      });
      arrows[0].disabled = true;
    }
    let queued = false;
    row.addEventListener('scroll', () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        const middle = row.getBoundingClientRect().left + row.clientWidth / 2;
        let best = 0, gap = Infinity;
        cards.forEach((card, i) => {
          const box = card.getBoundingClientRect();
          const d = Math.abs(box.left + box.width / 2 - middle);
          if (d < gap) { gap = d; best = i; }
        });
        // The first and last cards never reach the middle of a row that shows a peek of the next one.
        const end = Math.abs(row.scrollLeft);
        if (end < 8) best = 0;
        else if (end > row.scrollWidth - row.clientWidth - 8) best = cards.length - 1;
        current = best;
        [...dots.children].forEach((dot, i) => dot.classList.toggle('on', i === best));
        if (arrows.length) { arrows[0].disabled = best === 0; arrows[1].disabled = best === cards.length - 1; }
      });
    }, { passive: true });
  });

  // Phone: the language list is a sheet that slides up.
  const langButton = document.querySelector('.lang-btn');
  const sheet = document.querySelector('.langs');
  if (langButton && sheet) {
    const toggle = open => { sheet.classList.toggle('open', open); langButton.setAttribute('aria-expanded', String(open)); };
    langButton.addEventListener('click', event => { event.stopPropagation(); toggle(!sheet.classList.contains('open')); });
    document.addEventListener('click', event => { if (!sheet.contains(event.target)) toggle(false); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') toggle(false); });
  }

  // Catalog: filter by world and by words in the name.
  const cards = [...document.querySelectorAll('.grid [data-w]')];
  const find = document.querySelector('.find');
  const none = document.querySelector('.none');
  const plain = text => text.toLowerCase().normalize('NFD').replace(/[̀-֑ͯ-ׇ]/g, '');
  let world = '*';
  const names = cards.map(card => plain(card.textContent));
  const apply = () => {
    const words = find ? plain(find.value).split(/\s+/).filter(Boolean) : [];
    let shown = 0;
    cards.forEach((card, i) => {
      const ok = (world === '*' || card.dataset.w === world) && words.every(word => names[i].includes(word));
      card.hidden = !ok;
      shown += ok;
    });
    if (none) none.hidden = shown > 0;
  };
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    world = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    apply();
  }));
  if (find) find.addEventListener('input', apply);

  // Bottom bar: same-page tabs act at once, and the bar shows where you are.
  const tabs = [...document.querySelectorAll('.tabs [data-tab]')];
  const here = name => tabs.forEach(tab => tab.dataset.tab === name ? tab.setAttribute('aria-current', 'page') : tab.removeAttribute('aria-current'));
  const openSearch = () => { find.scrollIntoView({ block: 'center' }); find.focus({ preventScroll: true }); };
  tabs.forEach(tab => tab.addEventListener('click', event => {
    const url = new URL(tab.href);
    if (url.pathname !== location.pathname) return;
    if (tab.dataset.tab === 'home') { event.preventDefault(); scrollTo(0, 0); }
    if (tab.dataset.tab === 'find' && find) { event.preventDefault(); openSearch(); }
  }));
  if (find && location.hash === '#find') openSearch();
  const catalog = document.getElementById('todo');
  const worlds = document.getElementById('cats');
  if (tabs.length && catalog && worlds) {
    let queued = false;
    const where = () => {
      queued = false;
      const line = innerHeight * 0.45;
      here(catalog.getBoundingClientRect().top < line ? 'all' : worlds.getBoundingClientRect().top < line ? 'cats' : 'home');
    };
    addEventListener('scroll', () => { if (!queued && phone.matches) { queued = true; requestAnimationFrame(where); } }, { passive: true });
  }

  // Product clip: the photo stays a while, the real clip slowly dissolves in over it, plays, and dissolves back
  // into the photo while still moving (no frozen last frame); repeats while on screen.
  const clip = document.querySelector('.demo video');
  if (clip && !calm && !(navigator.connection && navigator.connection.saveData)) {
    const frame = clip.parentElement;
    const PHOTO = 3000;  // how long the photo is shown before each play
    const FADE = 1.5;    // seconds; matches the CSS transition
    let visible = false, timer = 0;
    const start = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (!visible) return;
        clip.currentTime = 0;
        clip.play().then(() => frame.classList.add('playing')).catch(() => {});
      }, PHOTO);
    };
    clip.addEventListener('timeupdate', () => {
      if (frame.classList.contains('playing') && clip.duration && clip.currentTime > clip.duration - FADE) frame.classList.remove('playing');
    });
    clip.addEventListener('ended', () => { frame.classList.remove('playing'); if (visible) start(); });
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) { if (clip.preload !== 'auto') { clip.preload = 'auto'; clip.load(); } if (clip.paused) start(); }
      else { clearTimeout(timer); clip.pause(); frame.classList.remove('playing'); }
    }, { threshold: 0.4 }).observe(frame);
  }

  // The clicked product image morphs into the hero of its page.
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-go]');
    const image = link && link.querySelector('img');
    if (image) image.style.viewTransitionName = 'hero-p';
  }, true);
})();
