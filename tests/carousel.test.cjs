const assert = require('node:assert/strict');
const test = require('node:test');
const storefront = require('../fluxixo_site/redesign/static/app.js');

function clock() {
  let now = 0, id = 0;
  const timers = new Map();
  return {
    setTimeout(fn, delay) { timers.set(++id, { at: now + delay, fn }); return id; },
    clearTimeout(key) { timers.delete(key); },
    count() { return timers.size; },
    advance(ms) {
      const end = now + ms;
      for (;;) {
        const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > end) break;
        now = next[1].at;
        timers.delete(next[0]);
        next[1].fn();
      }
      now = end;
    }
  };
}

function fixture(extra = {}) {
  assert.equal(typeof storefront.createCarouselController, 'function', 'the actual carousel controller must be exported');
  const time = clock(), changes = [];
  const controller = storefront.createCarouselController({
    count: 7, setTimeout: time.setTimeout, clearTimeout: time.clearTimeout,
    onChange: (index, meta) => { changes.push({ index, ...meta }); }, ...extra
  });
  return { time, changes, controller };
}

test('autoplay shows exactly seven slides in order, every eight seconds, with one timer', () => {
  const { time, changes } = fixture();
  assert.equal(changes[0].index, 0);
  time.advance(7999);
  assert.equal(changes.length, 1);
  time.advance(1);
  assert.equal(changes[1].index, 1);
  for (let i = 0; i < 6; i++) { assert.equal(time.count(), 1); time.advance(8000); }
  assert.deepEqual(changes.map(x => x.index), [0, 1, 2, 3, 4, 5, 6, 0]);
  assert.equal(time.count(), 1);
});

test('hover, hidden document and offscreen pauses compose without restarting early', () => {
  const { controller: c, time, changes } = fixture();
  time.advance(3000);
  c.pause('hover', true);
  c.pause('hidden', true);
  c.pause('offscreen', true);
  c.pause('hover', false);
  c.pause('hidden', false);
  time.advance(50000);
  assert.equal(changes.length, 1);
  assert.equal(time.count(), 0);
  c.pause('offscreen', false);
  c.pause('offscreen', false);
  assert.equal(time.count(), 1);
  time.advance(8000);
  assert.equal(changes.at(-1).index, 1);
});

test('keyboard focus pauses the slide until focus leaves, independent of image hover', () => {
  const { controller: c, time, changes } = fixture();
  c.pause('focus', true);
  c.pause('hover', true);
  c.pause('hover', false);
  c.move(1);
  time.advance(50000);
  assert.equal(changes.at(-1).index, 1);
  assert.equal(changes.length, 2);
  assert.equal(time.count(), 0);
  c.pause('focus', false);
  time.advance(8000);
  assert.equal(changes.at(-1).index, 2);
});

test('manual previous/next wrap and reset a single full interval', () => {
  const { controller: c, time, changes } = fixture();
  time.advance(7000);
  c.move(-1);
  assert.equal(changes.at(-1).index, 6);
  assert.equal(changes.at(-1).manual, true);
  time.advance(7999);
  assert.equal(changes.at(-1).index, 6);
  c.move(1);
  assert.equal(changes.at(-1).index, 0);
  assert.equal(time.count(), 1);
  time.advance(8000);
  assert.equal(changes.at(-1).index, 1);
});

test('reduced motion forbids autoplay including explicit Start but keeps manual navigation', () => {
  const { controller: c, time, changes } = fixture({ reducedMotion: true });
  c.start();
  time.advance(100000);
  assert.equal(changes.length, 1);
  assert.equal(time.count(), 0);
  c.move(1);
  assert.equal(changes.at(-1).index, 1);
  c.setReducedMotion(false);
  assert.equal(time.count(), 1);
  c.setReducedMotion(true);
  assert.equal(time.count(), 0);
});

test('image readiness delays autoplay; paused and superseded changes cannot resurrect it', async () => {
  let finish;
  const { controller: c, time } = fixture({ onChange(index) {
    if (index === 1) return new Promise(resolve => { finish = resolve; });
  } });
  time.advance(8000);
  assert.equal(c.state().index, 1);
  assert.equal(time.count(), 0);
  time.advance(40000);
  assert.equal(c.state().index, 1);
  c.move(1);
  c.stop();
  finish();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(c.state().index, 2);
  assert.equal(time.count(), 0);
  c.start();
  time.advance(7999);
  assert.equal(c.state().index, 2);
  time.advance(1);
  assert.equal(c.state().index, 3);
});

test('destroy cancels the active timer and rejects later interaction', () => {
  const { controller: c, time, changes } = fixture();
  c.destroy(); c.start(); c.move(1); c.pause('hidden', false);
  time.advance(100000);
  assert.equal(changes.length, 1);
  assert.equal(time.count(), 0);
});

test('pausing during automatic image loading cancels the visual change and retains the displayed slide', async () => {
  for (const pause of [c => c.pause('hover', true), c => c.stop(), c => c.pause('hidden', true), c => c.setReducedMotion(true)]) {
    let visible = 0, finish;
    const { controller: c, time } = fixture({ onChange(index, meta) {
      if (meta.initial || meta.manual) { visible = index; return; }
      return new Promise(resolve => { finish = () => {
        if (!meta.canCommit || meta.canCommit()) visible = index;
        resolve();
      }; });
    } });
    time.advance(8000);
    assert.equal(visible, 0);
    pause(c);
    finish();
    await Promise.resolve();
    await Promise.resolve();
    assert.equal(visible, 0, 'a late image must not switch the product after Pause');
    assert.equal(c.state().index, 0);
    assert.equal(time.count(), 0);
    c.move(1);
    assert.equal(visible, 1, 'manual navigation remains available while paused');
    c.destroy();
  }
});

test('swiping follows reading direction and ignores taps or vertical page scrolling', () => {
  assert.equal(typeof storefront.carouselSwipeStep, 'function');
  const swipe = storefront.carouselSwipeStep;
  assert.equal(swipe(-100, 10, false), 1);
  assert.equal(swipe(100, 10, false), -1);
  assert.equal(swipe(-100, 10, true), -1);
  assert.equal(swipe(100, 10, true), 1);
  assert.equal(swipe(20, 2, false), 0);
  assert.equal(swipe(90, 100, false), 0);
  assert.equal(swipe(70, 60, false), 0);
});
