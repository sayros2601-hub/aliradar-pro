const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const script = fs.readFileSync(path.join(__dirname, '../fluxixo_site/redesign/static/app.js'), 'utf8');

function loadLocaleExports({ withUrl = true } = {}) {
  const ctx = { module: { exports: {} }, Intl, Date, URLSearchParams };
  if (withUrl) ctx.URL = URL;
  vm.runInNewContext(script, ctx);
  return ctx.module.exports;
}

const fx = loadLocaleExports();

test('ordinary visits keep the English homepage for every browser language', () => {
  for (const language of ['en-US', 'ru-RU', 'es-MX', 'pt-BR', 'fr-FR', 'he-IL', 'iw', 'ja-JP']) {
    assert.equal(fx.resolveVisitorPath({ pathname: '/', languages: [language, 'ru-RU'] }), null, language);
  }
});

test('old saved preferences and inbound referrers leave the homepage URL intact', () => {
  assert.equal(
    fx.resolveVisitorPath({
      pathname: '/',
      search: '?utm_source=tt',
      hash: '#drop',
      savedLang: 'pt-BR',
      referrer: 'https://www.google.com/',
      origin: 'https://www.fluxixo.shop',
      languages: ['ru-RU'],
    }),
    null,
  );
});

test('normal storefront and deep links keep their selected locale', () => {
  for (const pathname of ['/en/', '/catalog/', '/es/', '/pt/', '/fr/', '/he/', '/en/journal/wifi-repeater-buying-guide/', '/products/katord-wifi-repeater/']) {
    assert.equal(fx.resolveVisitorPath({ pathname, search: '?lang=es&category=tech', hash: '#todo' }), null, pathname);
  }
});

test('explicit legacy language links preserve catalog sections and other query parameters', () => {
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=ru&utm_source=share', hash: '#drop' }), '/catalog/?utm_source=share#drop');
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=es&tag=a&tag=b', hash: '#mundos' }), '/es/?tag=a&tag=b#mundos');
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=pt-BR&category=tech', hash: '#todo' }), '/pt/?category=tech#todo');
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?LANG=iw_IL', hash: '#find' }), '/he/#find');
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=en', hash: '#find' }), '/en/#find');
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=en&category=tech', hash: '#todo' }), '/en/?category=tech#todo');
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=en', hash: '#drop' }), null);
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=ja', hash: '#find-063-cable-tester' }), null);
  assert.equal(fx.resolveVisitorPath({ pathname: '/', search: '?lang=fr', hash: '#spotlight-title-1' }), '/fr/#spotlight-title-1');
});

test('legacy showroom product links open the same item in its requested locale', () => {
  const examples = [
    ['en', 'find-063-cable-tester', '/en'],
    ['ru', 'auto-1005013194588661', ''],
    ['es-MX', 'import-0042', '/es'],
    ['pt', 'find-064-book-light', '/pt'],
    ['fr', 'find-063-cable-tester', '/fr'],
    ['he', 'katord-wifi-repeater', '/he'],
  ];
  for (const [language, id, prefix] of examples) {
    assert.equal(fx.resolveVisitorPath({
      pathname: '/index.html',
      search: `?utm_source=share&lang=${language}`,
      hash: `#${id}`,
    }), `${prefix}/products/${id}/?utm_source=share`);
  }
  assert.equal(fx.resolveVisitorPath({
    pathname: '/',
    search: '?utm_source=share',
    hash: '#find-063-cable-tester',
  }), '/en/products/find-063-cable-tester/?utm_source=share');
});

test('decorateAffiliateUrl appends AliExpress storefront _lang and afSmartRedirect idempotently', () => {
  const base = 'https://s.click.aliexpress.com/e/_c32Y13sN';
  assert.equal(fx.decorateAffiliateUrl(base, 'en'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=en_US&afSmartRedirect=y');
  assert.equal(fx.decorateAffiliateUrl(base, 'ru'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=ru_RU&afSmartRedirect=y');
  assert.equal(fx.decorateAffiliateUrl(base, 'pt-BR'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=pt_BR&afSmartRedirect=y');
  assert.equal(fx.decorateAffiliateUrl(base, 'es-MX'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=es_ES&afSmartRedirect=y');
  assert.equal(fx.decorateAffiliateUrl(base, 'fr'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=fr_FR&afSmartRedirect=y');
  assert.equal(fx.decorateAffiliateUrl(base, 'he-IL'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=iw_IL&afSmartRedirect=y');

  const once = fx.decorateAffiliateUrl(base, 'ru');
  assert.equal(fx.decorateAffiliateUrl(once, 'ru'), once);
  assert.equal(fx.decorateAffiliateUrl('https://www.fluxixo.shop/products/demo/', 'ru'), 'https://www.fluxixo.shop/products/demo/');

  const fxNoUrl = loadLocaleExports({ withUrl: false });
  assert.equal(fxNoUrl.decorateAffiliateUrl(base, 'pt-BR'), 'https://s.click.aliexpress.com/e/_c32Y13sN?_lang=pt_BR&afSmartRedirect=y');
});
