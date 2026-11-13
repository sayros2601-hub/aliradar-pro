const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

// Run the real shipped script without browser globals. Its pure scheduler is
// also used by the visible counter, so these cases catch timezone/rollover bugs.
const script = fs.readFileSync(path.join(__dirname, '../fluxixo_site/redesign/static/app.js'), 'utf8');
const sandbox = { module: { exports: {} }, Intl, Date };
vm.runInNewContext(script, sandbox);
const state = (...args) => {
  assert.equal(typeof sandbox.module.exports.getCountdownState, 'function', 'the storefront must expose its real countdown calculation');
  return sandbox.module.exports.getCountdownState(...args);
};

test('winter countdown targets 19:00 Israel, independent of visitor timezone', () => {
  const result = state('2026-11-13T15:30:00Z', { publishedDay: '2026-11-12' });
  assert.equal(result.status, 'countdown');
  assert.equal(result.seconds, 5400);
});

test('summer countdown uses daylight-saving offset', () => {
  const result = state('2026-07-13T15:30:00Z', { publishedDay: '2026-07-12' });
  assert.equal(result.status, 'countdown');
  assert.equal(result.seconds, 1800);
});

test('reaching the scheduled start does not pretend publication succeeded', () => {
  const result = state('2026-11-13T17:00:00Z', { publishedDay: '2026-11-12' });
  assert.equal(result.status, 'awaiting');
  assert.equal(result.seconds, 0);
});

test('new publication metadata advances to the next day', () => {
  const result = state('2026-11-13T17:10:00Z', { publishedDay: '2026-11-13' });
  assert.equal(result.status, 'countdown');
  assert.equal(result.seconds, 85800);
});

test('stale cached page stays awaiting across midnight instead of resetting', () => {
  const result = state('2026-11-14T08:00:00Z', { publishedDay: '2026-11-12' });
  assert.equal(result.status, 'awaiting');
  assert.equal(result.seconds, 0);
});

test('first scheduled day without published metadata also stays awaiting when stale', () => {
  const result = state('2026-11-14T08:00:00Z', { dueDay: '2026-11-13' });
  assert.equal(result.status, 'awaiting');
});

test('next publication crosses spring clock change in 23 hours', () => {
  const result = state('2026-03-26T17:00:00Z', { publishedDay: '2026-03-26' });
  assert.equal(result.seconds, 23 * 3600);
});

test('next publication crosses autumn clock change in 25 hours', () => {
  const result = state('2026-10-24T16:00:00Z', { publishedDay: '2026-10-24' });
  assert.equal(result.seconds, 25 * 3600);
});

test('publication checks are limited to once a minute and accept new live metadata', async () => {
  assert.equal(typeof sandbox.module.exports.createPublicationPoller, 'function');
  let requests = 0;
  const poll = sandbox.module.exports.createPublicationPoller(async () => {
    requests++;
    return { published_day: '2026-11-13' };
  });
  assert.equal(await poll(new Date('2026-11-13T17:01:00Z'), '2026-11-12'), '2026-11-13');
  assert.equal(await poll(new Date('2026-11-13T17:01:01Z'), '2026-11-13'), '2026-11-13');
  assert.equal(requests, 1);
  await poll(new Date('2026-11-13T17:02:00Z'), '2026-11-13');
  assert.equal(requests, 2);
});

test('unavailable or invalid status never invents publication or moves it backwards', async () => {
  assert.equal(typeof sandbox.module.exports.createPublicationPoller, 'function');
  for (const payload of [{published_day:'2026-11-14'}, {published_day:'2026-11-11'}, {published_day:'invalid'}, {}]) {
    const poll = sandbox.module.exports.createPublicationPoller(async () => payload);
    assert.equal(await poll(new Date('2026-11-13T17:01:00Z'), '2026-11-12'), '2026-11-12');
  }
  const poll = sandbox.module.exports.createPublicationPoller(async () => { throw new Error('offline'); });
  assert.equal(await poll(new Date('2026-11-13T17:01:00Z'), '2026-11-12'), '2026-11-12');
});
