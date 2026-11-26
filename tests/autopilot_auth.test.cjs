const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');

const workerPath = path.join(__dirname, '../cloudflare_autopilot/src/index.js');
const workerSource = fs.readFileSync(workerPath, 'utf8').replace('export default {', 'globalThis.worker = {');
const syncToken = 'worker-unit-test-token';
const publishedDay = '2026-11-20';
const protectedPosts = [
  '/api/generate-cutout',
  '/api/describe-product',
  '/api/generate-copy',
  '/api/dispatch',
  '/api/seo-sync',
  '/api/catalog-sync',
  '/api/review-media',
];

function loadWorker(mockFetch = () => assert.fail('unexpected network call'), Clock = Date) {
  const context = {
    AbortSignal, Blob, FormData, Headers, ReadableStream, Request, Response,
    TextEncoder, URL, Uint8Array, atob, btoa, crypto: webcrypto,
    Date: Clock, fetch: mockFetch,
  };
  vm.runInNewContext(workerSource, context, { filename: workerPath });
  return context.worker;
}

function request(pathname, { method = 'GET', auth, body, headers } = {}) {
  const requestHeaders = new Headers(headers);
  if (auth) requestHeaders.set('Authorization', auth);
  if (body !== undefined) requestHeaders.set('Content-Type', 'application/json');
  return new Request(`https://worker.invalid${pathname}`, {
    method, headers: requestHeaders, body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function post(pathname, body) {
  return request(pathname, { method: 'POST', auth: `Bearer ${syncToken}`, body });
}

function forbidBindings(token) {
  return {
    AUTOPILOT_SYNC_TOKEN: token,
    get DB() { return assert.fail('database accessed before authorization'); },
    get AI() { return assert.fail('AI accessed before authorization'); },
    get MEDIA_BUCKET() { return assert.fail('media accessed before authorization'); },
    get GITHUB_DISPATCH_TOKEN() { return assert.fail('dispatch credential accessed before authorization'); },
  };
}

function publicPublishingDatabase() {
  let queries = 0;
  return {
    get queries() { return queries; },
    prepare(sql) {
      queries++;
      assert.match(sql, /^SELECT COALESCE\(published_day, day\) AS published_day FROM daily_publish_state /);
      assert.match(sql, /WHERE status = 'published' ORDER BY day DESC LIMIT 1$/);
      return { async first() { return { published_day: publishedDay, reserved_count: 12 }; } };
    },
    batch() { assert.fail('public status must not batch private telemetry queries'); },
  };
}

function statements() {
  return {
    prepare(sql) {
      return { sql, bind(...args) { return { sql, args }; } };
    },
  };
}

const worker = loadWorker();

for (const pathname of protectedPosts) {
  test(`${pathname} requires configured bearer auth before body or service access`, async () => {
    const cases = [
      { binding: syncToken, headers: { 'X-Fluxixo-Source': 'github-actions' } },
      { binding: syncToken, auth: `Bearer x${syncToken.slice(1)}` },
      { binding: syncToken, auth: `Bearer ${syncToken}-extra` },
      { binding: syncToken, auth: `Basic ${syncToken}` },
      { binding: undefined, auth: `Bearer ${syncToken}` },
      { binding: ' ', auth: `Bearer ${syncToken}` },
    ];
    for (const { binding, auth, headers } of cases) {
      const incoming = request(pathname, { method: 'POST', auth, headers, body: { fixture: true } });
      for (const method of ['text', 'json', 'formData', 'arrayBuffer']) {
        incoming[method] = () => assert.fail('request parsed before authorization');
      }
      const response = await worker.fetch(incoming, forbidBindings(binding));
      assert.equal(response.status, 401);
      assert.equal(response.headers.get('WWW-Authenticate'), 'Bearer');
      assert.equal(response.headers.get('Cache-Control'), 'no-store');
      assert.deepEqual(await response.json(), { ok: false, error: 'Unauthorized' });
      assert.equal(incoming.bodyUsed, false);
    }
  });
}

test('liveness, preflight and unknown routes need no private services', async () => {
  const env = forbidBindings(undefined);
  const health = await worker.fetch(request('/healthz'), env);
  assert.equal(health.status, 200);
  assert.equal(health.headers.get('Cache-Control'), 'no-store');
  assert.deepEqual(await health.json(), { ok: true, service: 'fluxixo-autopilot' });

  const preflight = await worker.fetch(request('/api/catalog-sync', { method: 'OPTIONS' }), env);
  assert.equal(preflight.status, 204);
  assert.equal(await preflight.text(), '');
  assert.match(preflight.headers.get('Access-Control-Allow-Headers'), /\bAuthorization\b/);

  for (const [pathname, method] of [['/unknown', 'GET'], ['/unknown', 'POST'], ['/api/dispatch', 'GET']]) {
    const missing = await worker.fetch(request(pathname, { method }), env);
    assert.equal(missing.status, 404);
    assert.deepEqual(await missing.json(), { ok: false, error: 'Not Found' });
  }
});

test('public status reads only the publication date and allowlists its JSON', async () => {
  for (const pathname of ['/', '/api/status']) {
    for (const auth of [undefined, 'Bearer wrong-unit-test-token']) {
      const db = publicPublishingDatabase();
      const response = await worker.fetch(request(pathname, { auth }), { AUTOPILOT_SYNC_TOKEN: syncToken, DB: db });
      assert.equal(response.status, 200);
      assert.equal(response.headers.get('Cache-Control'), 'no-store');
      assert.equal(response.headers.get('Vary'), 'Authorization');
      const result = await response.json();
      assert.deepEqual(Object.keys(result).sort(), ['countdown', 'ok', 'published_day', 'service']);
      assert.equal(result.ok, true);
      assert.equal(result.service, 'fluxixo-autopilot');
      assert.equal(result.published_day, publishedDay);
      assert.equal(result.countdown.due_day, '2026-11-21');
      assert.equal(db.queries, 1);
    }
  }
});

test('an authenticated operator can still read detailed status on both entry points', async () => {
  const syntheticState = { day: publishedDay, status: 'published', reserved_count: 5 };
  const db = {
    ...statements(),
    async batch(queries) {
      assert.equal(queries.length, 12);
      return queries.map(({ sql }) => {
        if (sql.startsWith('SELECT COALESCE')) return { results: [{ published_day: publishedDay }] };
        if (sql.startsWith('SELECT day, status')) return { results: [syntheticState] };
        return { results: sql.includes('COUNT(*)') ? [{ count: 4 }] : [] };
      });
    },
  };
  for (const pathname of ['/', '/api/status']) {
    const response = await worker.fetch(request(pathname, { auth: `bearer ${syncToken}` }), {
      AUTOPILOT_SYNC_TOKEN: syncToken, DB: db,
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.equal(response.headers.get('Vary'), 'Authorization');
    const result = await response.json();
    assert.equal(result.published_day, publishedDay);
    assert.deepEqual(result.publish_state, [syntheticState]);
    assert.equal(result.configured_secrets.autopilot_sync_token, true);
    assert.equal(result.d1_counts.daily_ledger, 4);
    for (const key of ['countdown', 'ledger_recent', 'seo_recent', 'studio_recent', 'cron_recent']) {
      assert.ok(Object.hasOwn(result, key));
    }
    assert.equal(JSON.stringify(result).includes(syncToken), false);
  }
});

test('drop countdown has the same public fields even with an operator token', async () => {
  for (const auth of [undefined, `Bearer ${syncToken}`]) {
    const db = publicPublishingDatabase();
    const response = await worker.fetch(request('/drop-status.json', { auth }), { AUTOPILOT_SYNC_TOKEN: syncToken, DB: db });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    const result = await response.json();
    assert.deepEqual(Object.keys(result).sort(), [
      'countdown', 'due_day', 'israel_day', 'published_day', 'seconds_remaining', 'status', 'utc_day',
    ]);
    assert.equal(result.published_day, publishedDay);
    assert.equal(result.due_day, result.countdown.due_day);
    assert.equal(result.status, result.countdown.status);
    assert.equal(result.seconds_remaining, result.countdown.seconds);
    assert.equal(db.queries, 1);
  }
});

test('public redirects keep both rule listing and single-path resolution', async () => {
  const rule = { source_path: '/sitemap', target_path: '/sitemap.xml', status_code: 301 };
  const env = {
    AUTOPILOT_SYNC_TOKEN: syncToken,
    SITE_ORIGIN: 'https://store.invalid',
    DB: {
      prepare(sql) {
        return {
          sql,
          bind(...args) {
            return {
              sql, args,
              async first() {
                assert.match(sql, /FROM redirects WHERE source_path = \?/);
                assert.deepEqual(args, [rule.source_path]);
                return rule;
              },
            };
          },
        };
      },
      async batch([count, listing]) {
        assert.match(count.sql, /^SELECT COUNT\(\*\) AS total FROM redirects/);
        assert.deepEqual(listing.args, [2, 0]);
        return [{ results: [{ total: 1 }] }, { results: [rule] }];
      },
    },
  };
  const listing = await worker.fetch(request('/api/redirects?limit=2'), env);
  assert.equal(listing.status, 200);
  assert.deepEqual(await listing.json(), { ok: true, total: 1, count: 1, limit: 2, offset: 0, rules: [rule] });
  const lookup = await worker.fetch(request('/api/redirects?path=/sitemap'), env);
  assert.equal(lookup.status, 200);
  assert.equal((await lookup.json()).location, 'https://store.invalid/sitemap.xml');
  const redirect = await worker.fetch(request('/api/redirects?path=/sitemap&resolve=1'), env);
  assert.equal(redirect.status, 301);
  assert.equal(redirect.headers.get('Location'), 'https://store.invalid/sitemap.xml');
});

test('authorized AI requests preserve existing response contracts with mocked model outputs', async () => {
  const modelOutputs = ['synthetic copy', 'synthetic visual description'];
  const cloudflareAi = {
    async run(model, input) {
      assert.match(model, /^@cf\//);
      assert.ok(input.messages?.length);
      return { response: modelOutputs.shift() };
    },
  };
  const env = { AUTOPILOT_SYNC_TOKEN: syncToken, AI: cloudflareAi };
  const copy = await worker.fetch(post('/api/generate-copy', {
    messages: [{ role: 'user', content: 'unit-test copy' }], response_format: { type: 'text' },
  }), env);
  assert.equal(copy.status, 200);
  assert.equal((await copy.json()).choices[0].message.content, 'synthetic copy');
  const reference = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).toString('base64');
  const vision = await worker.fetch(post('/api/describe-product', { image_base64: reference }), env);
  assert.equal(vision.status, 200);
  assert.equal((await vision.json()).visual_spec, 'synthetic visual description');
  assert.deepEqual(modelOutputs, []);

  const image = Buffer.alloc(128);
  image.set([137, 80, 78, 71, 13, 10, 26, 10]);
  const recorded = [];
  const cutout = await worker.fetch(post('/api/generate-cutout?meta=1', { prompt: 'test fixture' }), {
    AUTOPILOT_SYNC_TOKEN: syncToken,
    AI: {
      async run(model, input) {
        assert.match(model, /^@cf\//);
        assert.match(input.multipart.contentType, /^multipart\/form-data\b/);
        return { image: image.toString('base64') };
      },
    },
    DB: {
      prepare(sql) {
        assert.match(sql, /^INSERT INTO studio_generations /);
        return {
          bind(...args) {
            return {
              async run() {
                recorded.push(args);
                return { meta: { last_row_id: 7 } };
              },
            };
          },
        };
      },
    },
  });
  assert.equal(cutout.status, 200);
  const result = await cutout.json();
  assert.equal(result.id, 7);
  assert.equal(result.mime_type, 'image/png');
  assert.equal(result.bytes, 128);
  assert.equal(recorded.length, 1);
  assert.equal(recorded[0][3], 'completed');
});

test('authorized catalog sync writes its existing audit, publication and ledger records', async () => {
  const db = {
    ...statements(),
    async batch(queries) {
      assert.equal(queries.length, 3);
      const [audit, state, ledger] = queries;
      assert.match(audit.sql, /INSERT INTO cron_runs /);
      assert.equal(audit.args[1], 'fixture');
      assert.match(state.sql, /INSERT OR REPLACE INTO daily_publish_state /);
      assert.equal(state.args[0], publishedDay);
      assert.match(ledger.sql, /INSERT OR IGNORE INTO daily_ledger /);
      assert.equal(ledger.args[1], 'fixture-product');
    },
  };
  const result = await worker.fetch(post('/api/catalog-sync', {
    event: 'fixture',
    publish_state: { days: { [publishedDay]: { status: 'published', published_day: publishedDay } } },
    ledger_days: { [publishedDay]: [{ catalog_id: 'fixture-product' }] },
  }), { AUTOPILOT_SYNC_TOKEN: syncToken, DB: db });
  assert.equal(result.status, 200);
  assert.equal((await result.json()).synced, true);
});

test('authorized workflow dispatch is constrained to the established workflow and inputs', async () => {
  let dispatched = 0;
  const mockWorker = loadWorker(async (url, init) => {
    dispatched++;
    assert.match(url, /\/actions\/workflows\/fluxixo_daily_rotate\.yml\/dispatches$/);
    assert.equal(init.method, 'POST');
    assert.deepEqual(JSON.parse(init.body), { ref: 'main', inputs: { add_count: '0' } });
    return new Response(null, { status: 204 });
  });
  const response = await mockWorker.fetch(post('/api/dispatch', { workflow: 'daily_rotate', add_count: 0 }), {
    AUTOPILOT_SYNC_TOKEN: syncToken,
    GITHUB_DISPATCH_TOKEN: 'github-unit-test-token',
    GITHUB_REPO: 'fixture/fixture',
    DB: {
      prepare(sql) {
        assert.match(sql, /INSERT INTO cron_runs /);
        return {
          bind(source) {
            assert.equal(source, 'api-dispatch');
            return { async run() {} };
          },
        };
      },
    },
  });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).http_status, 204);
  assert.equal(dispatched, 1);
});

test('authorized SEO telemetry can run without submitting URLs', async () => {
  const calls = [];
  const mockWorker = loadWorker(async (url, init) => {
    assert.equal(init.method, undefined);
    calls.push(url);
    assert.ok(url.startsWith('https://store.invalid/'));
    return new Response(url.endsWith('.txt') ? 'fixture-key' : '<urlset><url><loc>https://store.invalid/</loc></url></urlset>');
  });
  const db = {
    prepare(sql) {
      return { bind(...args) { return { sql, args, async first() { return null; } }; } };
    },
    async batch(queries) {
      assert.equal(queries.length, 1);
      for (const { sql, args } of queries) {
        assert.match(sql, /^INSERT INTO seo_telemetry /);
        assert.equal(args[4], 'telemetry_only');
      }
    },
  };
  const response = await mockWorker.fetch(post('/api/seo-sync', {}), {
    AUTOPILOT_SYNC_TOKEN: syncToken, SITE_ORIGIN: 'https://store.invalid', INDEXNOW_KEY: 'fixture-key', DB: db,
  });
  assert.equal(response.status, 200);
  const result = await response.json();
  assert.equal(result.engines.indexnow_global.submitted_count, 0);
  assert.equal(result.engines.indexnow_global.status, 'telemetry_only');
  assert.equal(result.engines.indexnow_yandex, undefined);
  assert.deepEqual(calls.sort(), [
    'https://store.invalid/fixture-key.txt', 'https://store.invalid/sitemap.xml',
  ]);
});

test('the scheduled callback still runs inside the Worker without HTTP credentials', async () => {
  const scheduledTime = '2026-11-20T12:00:00Z';
  class FixedClock extends Date {
    constructor(...args) {
      super(...(args.length ? args : [scheduledTime]));
    }
  }

  let dispatched = 0;
  const mockWorker = loadWorker(async (url, init) => {
    dispatched++;
    assert.match(url, /\/actions\/workflows\/fluxixo_daily_rotate\.yml\/dispatches$/);
    assert.deepEqual(JSON.parse(init.body), { ref: 'main', inputs: { add_count: 'auto' } });
    return new Response(null, { status: 204 });
  }, FixedClock);
  let recorded;
  const db = {
    prepare(sql) {
      return {
        sql,
        bind(...args) {
          return { sql, args, async run() { recorded = { sql, args }; } };
        },
      };
    },
    async batch(queries) {
      assert.equal(queries.length, 3);
      assert.match(queries[0].sql, /FROM daily_publish_state WHERE day = \?/);
      assert.match(queries[1].sql, /FROM daily_ledger WHERE day = \?/);
      assert.match(queries[2].sql, /AS published_day FROM daily_publish_state/);
      return [{ results: [] }, { results: [{ count: 0 }] }, { results: [] }];
    },
  };
  let pending;
  await mockWorker.scheduled({ cron: '30 10-18 * * *' }, {
    GITHUB_DISPATCH_TOKEN: 'github-unit-test-token', GITHUB_REPO: 'fixture/fixture', DB: db,
  }, { waitUntil(operation) { pending = operation; } });
  assert.ok(pending);
  await pending;
  assert.equal(dispatched, 1);
  assert.match(recorded.sql, /^INSERT INTO cron_runs /);
  assert.equal(recorded.args[1], 'prepare_window_check');
  assert.equal(recorded.args[2], 'ok');
});

test('click tracking endpoint enforces allowed origins and records D1 rows while summary/r2 require auth', async () => {
  const deniedSummary = await worker.fetch(request('/api/clicks-summary'), forbidBindings(syncToken));
  assert.equal(deniedSummary.status, 401);

  const deniedR2 = await worker.fetch(request('/api/r2-media/assets/images/test.webp', { method: 'PUT', body: { bad: 1 } }), forbidBindings(syncToken));
  assert.equal(deniedR2.status, 401);

  const badOrigin = await worker.fetch(
    request('/api/click', { method: 'POST', headers: { Origin: 'https://evil.invalid' }, body: { product_id: 'p1' } }),
    forbidBindings(syncToken)
  );
  assert.equal(badOrigin.status, 403);

  const inserted = [];
  const clickDb = {
    prepare(sql) {
      assert.match(sql, /^INSERT INTO affiliate_clicks /);
      return {
        bind(...args) {
          return {
            async run() {
              inserted.push(args);
              return { success: true };
            },
          };
        },
      };
    },
  };
  const okClick = await worker.fetch(
    new Request('https://worker.invalid/api/click', {
      method: 'POST',
      headers: { Origin: 'https://www.fluxixo.shop', 'Content-Type': 'text/plain', 'CF-IPCountry': 'IL' },
      body: JSON.stringify({ product_id: 'auto-123', lang: 'he', world: 'tech', page_path: '/he/products/auto-123/' }),
    }),
    { AUTOPILOT_SYNC_TOKEN: syncToken, DB: clickDb }
  );
  assert.equal(okClick.status, 204);
  assert.equal(inserted.length, 1);
  assert.equal(inserted[0][0], 'auto-123');
  assert.equal(inserted[0][1], 'he');
});

test('flux-1-schnell fallback, review-media and R2 upload handlers behave safely', async () => {
  const reviewRes = await worker.fetch(post('/api/review-media', {
    system: 'Review studio image',
    payload: { id: 'p1' },
    images: ['data:image/jpeg;base64,/9j/4AAQ'],
  }), {
    AUTOPILOT_SYNC_TOKEN: syncToken,
    AI: {
      async run(model) {
        assert.match(model, /^@cf\//);
        return { response: JSON.stringify({ accepted: true, reasons: [], material_defects: [] }) };
      },
    },
  });
  assert.equal(reviewRes.status, 200);
  const reviewJson = await reviewRes.json();
  assert.equal(reviewJson.ok, true);
  assert.equal(reviewJson.result.accepted, true);

  const tgRemoved = await worker.fetch(post('/api/telegram-digest', { text: 'Daily drop live' }), {
    AUTOPILOT_SYNC_TOKEN: syncToken,
  });
  assert.equal(tgRemoved.status, 404);

  const storedR2 = [];
  const r2Res = await worker.fetch(
    new Request('https://worker.invalid/api/r2-media/assets/images/sample.webp', {
      method: 'PUT',
      headers: { Authorization: `Bearer ${syncToken}`, 'Content-Type': 'image/webp' },
      body: new Uint8Array([82, 73, 70, 70]),
    }),
    {
      AUTOPILOT_SYNC_TOKEN: syncToken,
      MEDIA_BUCKET: {
        async put(key, bytes, opts) {
          storedR2.push({ key, len: bytes.byteLength, opts });
        },
      },
    }
  );
  assert.equal(r2Res.status, 200);
  assert.equal(storedR2[0].key, 'assets/images/sample.webp');
  assert.equal(storedR2[0].opts.httpMetadata.contentType, 'image/webp');
});
