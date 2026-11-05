(function () {
  'use strict';
  const KEY = 'mira.catalog.unique.v2';
  const THEMES = ['blue', 'coral', 'sand', 'lavender', 'rose'];
  const clone = value => JSON.parse(JSON.stringify(value));
  const str = (v, max, label, optional = false) => {
    if (typeof v !== 'string' || v.length > max || (!optional && !v.trim())) throw new Error('Проверьте поле «' + label + '».');
    return v;
  };
  function affiliateUrl(value, optional = false) {
    if (!value && optional) return '';
    str(value, 10000, 'Партнёрская ссылка');
    let url;
    try { url = new URL(value); } catch (_) { throw new Error('Нужна полная ссылка https://… на AliExpress.'); }
    const host = url.hostname.toLowerCase();
    if (url.protocol !== 'https:' || url.username || url.password || !(host === 'aliexpress.com' || host.endsWith('.aliexpress.com') || host === 'aliexpress.ru' || host.endsWith('.aliexpress.ru'))) {
      throw new Error('Разрешены только HTTPS-ссылки AliExpress.');
    }
    // Keep the original string, including every tracking parameter and its order.
    return value;
  }
  function imageUrl(value, optional = false) {
    if (!value && optional) return '';
    str(value, 4500000, 'Изображение');
    if (/^assets\/[a-zA-Z0-9_./-]+\.(?:webp|png|jpe?g|avif)$/i.test(value) && !value.includes('..')) return value;
    if (/^data:image\/(?:png|webp|jpeg|avif);base64,[A-Za-z0-9+/=]+$/.test(value)) return value;
    throw new Error('Выберите PNG, WebP, JPEG или AVIF либо локальный путь assets/…');
  }
  function validate(input) {
    if (!input || typeof input !== 'object' || input.version !== 1 || !Array.isArray(input.products) || input.products.length < 1 || input.products.length > 1000) {
      throw new Error('Нужен каталог MIRA версии 1, от 1 до 1000 товаров.');
    }
    const ids = new Set();
    const products = input.products.map((p, i) => {
      if (!p || typeof p !== 'object') throw new Error('Некорректный товар №' + (i + 1));
      const id = str(p.id, 64, 'ID товара');
      if (!/^[a-z0-9][a-z0-9_-]*$/i.test(id) || ids.has(id)) throw new Error('ID товаров должны быть разными: латинские буквы, цифры, - и _.');
      ids.add(id);
      if (!Array.isArray(p.headline) || p.headline.length !== 2) throw new Error('У заголовка должны быть две строки.');
      if (typeof p.demo !== 'boolean') throw new Error('Укажите статус товара: демо или партнёрский.');
      if (!THEMES.includes(p.theme)) throw new Error('Выберите одну из пяти палитр MIRA.');
      if (!Array.isArray(p.facts) || p.facts.length > 8) throw new Error('Для товара можно добавить не более 8 фактов.');
      return {
        id, name: str(p.name, 90, 'Название'), category: str(p.category, 50, 'Категория'),
        headline: p.headline.map(x => str(x, 32, 'Строка заголовка')),
        description: str(p.description, 240, 'Краткое описание', true),
        image: imageUrl(p.image), original: imageUrl(p.original || '', true),
        imageNote: str(p.imageNote || '', 600, 'Источник изображения', true),
        pendingLink: p.pendingLink === true,
        affiliateUrl: affiliateUrl(p.affiliateUrl || '', p.demo || p.pendingLink === true),
        sourceUrl: affiliateUrl(p.sourceUrl || '', true), demo: p.demo, theme: p.theme,
        scale: Number.isFinite(p.scale) ? Math.min(1.4, Math.max(.65, p.scale)) : 1,
        rotation: Number.isFinite(p.rotation) ? Math.min(15, Math.max(-15, p.rotation)) : 0,
        details: str(p.details || '', 4000, 'Подробное описание', true),
        facts: p.facts.map(f => ({label: str(f.label, 90, 'Название характеристики'), value: str(f.value, 240, 'Значение характеристики')}))
      };
    });
    return {version: 1, brand: 'MIRA', tagline: 'Находки с другой стороны', products};
  }
  function defaults() { return validate(clone(window.MIRA_CATALOG)); }
  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) return {catalog: validate(JSON.parse(raw)), custom: true, warning: ''};
    } catch (_) {
      return {catalog: defaults(), custom: false, warning: 'Локальные изменения не удалось прочитать. Открыта исходная коллекция.'};
    }
    return {catalog: defaults(), custom: false, warning: ''};
  }
  function save(input) {
    const valid = validate(input);
    const json = JSON.stringify(valid);
    if (json.length > 16000000) throw new Error('Каталог слишком большой. Уменьшите изображения или число товаров.');
    try { localStorage.setItem(KEY, json); } catch (_) { throw new Error('Браузер не сохранил каталог: память заполнена или хранение отключено. Скачайте catalog.js, чтобы не потерять изменения.'); }
    return valid;
  }
  function reset() { try { localStorage.removeItem(KEY); } catch (_) {} return defaults(); }
  function download(name, body, type = 'application/json') {
    const url = URL.createObjectURL(new Blob([body], {type}));
    const a = document.createElement('a'); a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }
  function serialize(input) {
    return '/* MIRA portable catalog. Replace dist/js/catalog.js with this file. */\nwindow.MIRA_CATALOG = ' + JSON.stringify(validate(input), null, 2).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029') + ';\n';
  }
  window.MiraCatalog = Object.freeze({KEY, THEMES, clone, validate, defaults, load, save, reset, download, serialize, affiliateUrl, imageUrl});
})();
