// Yandex Metrika, counter 114240176. Loaded on the Russian pages only (see page() in build_redesign.py).
// It lives in a file because the site's Content-Security-Policy forbids inline scripts; the policy in dist/_headers
// lists the Metrika hosts this needs.
//
// The counter queue is set up at once, so the visit, its source and every goal are recorded from the first moment,
// but tag.js with its session recorder (Webvisor) starts only after the page has loaded and the phone is idle.
// Measured on 2026-11-14 (Lighthouse, mobile): with Metrika starting during load the Russian catalog blocked the
// page for 2.5 s (Total Blocking Time), without it 0.17 s — exactly when people first look and tap.
(function (m, e, t, r, i) {
  m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
  m[i].l = 1 * new Date();
  var started = false;
  function start() {
    if (started) return;
    started = true;
    var k = e.createElement(t), a = e.getElementsByTagName(t)[0];
    k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
  }
  function later() {
    m.setTimeout(function () {
      if ('requestIdleCallback' in m) m.requestIdleCallback(start, { timeout: 2000 });
      else start();
    }, 1500);
  }
  if (e.readyState === 'complete') later();
  else m.addEventListener('load', later, { once: true });
  // Someone who goes to the seller before that still counts: the seller opens in a new tab, so the tag loads now.
  e.addEventListener('click', function (event) {
    if (event.target.closest && event.target.closest('a[rel~="sponsored"]')) start();
  }, true);
})(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js?id=114240176', 'ym');

ym(114240176, 'init', { ssr: true, webvisor: true, clickmap: true, referrer: document.referrer, url: location.href, accurateTrackBounce: true, trackLinks: true });

// A click through to the seller is the one action that matters on this site: count it as a goal.
document.addEventListener('click', function (event) {
  var link = event.target.closest && event.target.closest('a[rel~="sponsored"]');
  if (link) ym(114240176, 'reachGoal', 'go_aliexpress');
}, true);
