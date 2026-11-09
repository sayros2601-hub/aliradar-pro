(function () {
  'use strict';
  // Language switcher for catalog, categories, and product pages
  document.addEventListener('change', function (e) {
    var el = e.target;
    if (el && (el.classList.contains('lang-select') || el.id === 'lang-select')) {
      var opt = el.options && el.options[el.selectedIndex];
      if (opt) {
        var targetLang = opt.getAttribute('data-lang') || el.value;
        try {
          localStorage.setItem('fluxixo.lang.v2', targetLang);
        } catch (_) {}
        var url = el.value;
        if (url && (url.startsWith('/') || url.startsWith('http') || url.indexOf('.html') !== -1)) {
          window.location.href = url;
        }
      }
    }
  }, true);

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest('a');
    if (a && a.closest('.locale-links')) {
      var langAttr = a.getAttribute('lang');
      if (langAttr) {
        var code = langAttr.split('-')[0].toLowerCase();
        try {
          localStorage.setItem('fluxixo.lang.v2', code);
        } catch (_) {}
      }
    }
  }, true);
})();
