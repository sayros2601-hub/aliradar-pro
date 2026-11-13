// Yandex Metrika, counter 114240176. Loaded on the Russian pages only (see page() in build_redesign.py).
// It lives in a file because the site's Content-Security-Policy forbids inline scripts; the policy in dist/_headers
// lists the Metrika hosts this needs.
(function (m, e, t, r, i, k, a) {
  m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
  m[i].l = 1 * new Date();
  k = e.createElement(t); a = e.getElementsByTagName(t)[0]; k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
})(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js?id=114240176', 'ym');

ym(114240176, 'init', { ssr: true, webvisor: true, clickmap: true, referrer: document.referrer, url: location.href, accurateTrackBounce: true, trackLinks: true });

// A click through to the seller is the one action that matters on this site: count it as a goal.
document.addEventListener('click', function (event) {
  var link = event.target.closest && event.target.closest('a[rel~="sponsored"]');
  if (link) ym(114240176, 'reachGoal', 'go_aliexpress');
}, true);
