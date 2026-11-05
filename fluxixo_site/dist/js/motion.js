/* MIRA — compositor-friendly perspective stage. Classic script; works with file://. */
(function () {
  'use strict';

  var PERSPECTIVE = 1100;
  var TRANSITION_MS = 760;
  var FADE_MS = 160;
  var MIDPOINT = 0.38;
  var IMAGE_TIMEOUT_MS = 6500;
  var CACHE_LIMIT = 8;
  var RING_DEPTHS = [-1500, -800, -100];
  // Equal-time sine samples soften the reversals and match the loop boundary.
  // Linear timing preserves the wave instead of applying a second global easing.
  var IDLE_FRAMES = [];
  for (var idleStep = 0; idleStep <= 32; idleStep += 1) {
    var idleWave = idleStep === 32 ? 0 : Math.sin(idleStep / 32 * Math.PI * 2);
    IDLE_FRAMES.push({
      transform: 'translate3d(0,' + (-4 * idleWave).toFixed(3) + 'px,0) rotateZ(' +
        (.55 * idleWave).toFixed(3) + 'deg)',
      offset: idleStep / 32
    });
  }
  var FALLBACK_IMAGE = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">' +
    '<rect x="150" y="150" width="340" height="340" rx="72" fill="#e4e4f0" fill-opacity=".16" stroke="#e4e4f0" stroke-opacity=".35" stroke-width="2"/>' +
    '<path d="M220 390l75-85 55 58 37-41 53 68H220z" fill="#e4e4f0" fill-opacity=".5"/>' +
    '<circle cx="382" cy="258" r="24" fill="#e4e4f0" fill-opacity=".65"/>' +
    '</svg>'
  );

  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }
  function number(value, fallback) {
    var result = Number(value);
    return Number.isFinite(result) ? result : fallback;
  }
  function smooth(start, end, value) {
    var t = clamp((value - start) / (end - start), 0, 1);
    return t * t * (3 - 2 * t);
  }
  function easeOut(value) {
    var t = 1 - clamp(value, 0, 1);
    return 1 - t * t * t;
  }
  function safeProduct(product) {
    product = product || {};
    return {
      image: typeof product.image === 'string' ? product.image : '',
      alt: typeof product.alt === 'string' ? product.alt : '',
      scale: clamp(number(product.scale, 1), 0.45, 1.8),
      rotation: clamp(number(product.rotation, 0), -30, 30)
    };
  }
  function transform(x, y, z, rx, ry, rz, scale) {
    return 'translate(-50%, -50%) translate3d(' + x.toFixed(2) + 'px,' +
      y.toFixed(2) + 'px,' + z.toFixed(2) + 'px) rotateX(' + rx.toFixed(2) +
      'deg) rotateY(' + ry.toFixed(2) + 'deg) rotateZ(' + rz.toFixed(2) +
      'deg) scale(' + scale.toFixed(4) + ')';
  }
  function ringTransform(index, travel) {
    return 'translate(-50%, -50%) translateZ(' + (RING_DEPTHS[index] + travel) +
      'px) rotateZ(-14deg) scale(1.04)';
  }

  class MiraStage {
    constructor(options) {
      options = options || {};
      this.stage = options.stage;
      this.canvas = options.canvas || null;
      this.planes = Array.from(options.planes || []).slice(0, 2);
      this.rings = Array.from(options.rings || []).slice(0, 3);
      if (!this.stage || this.planes.length !== 2) {
        throw new Error('MiraStage needs a stage and two product planes.');
      }
      this.images = this.planes.map(function (plane) {
        var image = plane.querySelector('img');
        if (!image) throw new Error('Each product plane needs an img element.');
        return image;
      });
      this.context = this.canvas ? this.canvas.getContext('2d', { alpha: true }) : null;
      this.reducedMotion = Boolean(options.reducedMotion);
      this.paused = false;
      this.disposed = false;
      this._native = typeof this.planes[0].animate === 'function';
      this._hidden = Boolean(window.document.hidden);
      this._busy = false;
      this._epoch = 0;
      this._active = 0;
      this._products = [null, null];
      this._transition = null;
      this._cancelImageWait = null;
      this._imageCache = new Map();
      this._raf = null;
      this._resizeRaf = null;
      this._lastTime = 0;
      this._idleAnimation = null;
      this._idleIndex = -1;
      this._pointer = { x: 0, y: 0 };
      this._tilt = { x: 0, y: 0 };
      this._viewport = { width: 1, height: 1, dpr: 1 };
      this._bounds = { left: 0, top: 0, width: 1, height: 1 };
      this._origin = { x: 0, y: 0 };
      this._tickBound = this._tick.bind(this);
      this._resizeBound = () => {
        if (this._resizeRaf !== null || this.disposed) return;
        this._resizeRaf = window.requestAnimationFrame(() => {
          this._resizeRaf = null;
          this._resize();
        });
      };
      this._pointerBound = this._onPointerMove.bind(this);
      this._leaveBound = this._onPointerLeave.bind(this);
      this._visibilityBound = this._onVisibilityChange.bind(this);

      this.planes.forEach(function (plane) {
        plane.style.opacity = '0';
        plane.style.visibility = 'hidden';
        plane.style.pointerEvents = 'none';
        plane.style.willChange = '';
      });
      this.images.forEach(function (image) {
        image.draggable = false;
        image.decoding = 'async';
        image.style.backfaceVisibility = 'hidden';
      });
      this.rings.forEach(function (ring) {
        ring.style.pointerEvents = 'none';
        ring.style.willChange = '';
      });
      this.stage.addEventListener('pointermove', this._pointerBound, { passive: true });
      this.stage.addEventListener('pointerleave', this._leaveBound, { passive: true });
      window.addEventListener('resize', this._resizeBound, { passive: true });
      window.document.addEventListener('visibilitychange', this._visibilityBound);
      this._resize();
    }

    get isTransitioning() { return this._busy; }
    get transitionDuration() { return this.reducedMotion ? FADE_MS : TRANSITION_MS; }
    get copyChangeDelay() { return Math.round(this.transitionDuration * MIDPOINT); }

    // The strong Image references retain a small decoded neighborhood, not the whole catalog.
    preload(products) {
      if (this.disposed) return Promise.resolve([]);
      var sources = Array.from(products || []).slice(0, 3).map(function (item) {
        return typeof item === 'string' ? item : item && item.image;
      }).filter(Boolean);
      return Promise.all(sources.map(src => this._loadImage(src)));
    }

    setInitial(product) {
      if (this.disposed) return;
      this._abort();
      this._active = 0;
      this._products = [safeProduct(product), null];
      this._applyProduct(0, this._products[0], this._products[0].image || FALLBACK_IMAGE);
      this.planes[1].style.visibility = 'hidden';
      this.planes[1].style.opacity = '0';
      this._resetPointer();
      this._renderStable();
      this._startIdle();
      this.preload([this._products[0]]);
    }

    async transitionTo(product, direction, onHalfway) {
      if (this.disposed || this._busy) return false;
      var next = safeProduct(product);
      if (!this._products[this._active]) {
        this.setInitial(next);
        if (typeof onHalfway === 'function') onHalfway();
        return true;
      }
      this._busy = true;
      var epoch = ++this._epoch;
      var prepared = await this._waitForImage(next.image);
      if (this.disposed || epoch !== this._epoch) return false;
      if (prepared.cancelled) { this._busy = false; return false; }

      var incoming = 1 - this._active;
      this._products[incoming] = next;
      this._stopLoop();
      this._pauseIdle();
      this._applyProduct(incoming, next, prepared.src);
      this.planes[incoming].style.opacity = '0';
      this._resetPointer();

      return new Promise((resolve) => {
        var transition = this._transition = {
          started: window.performance.now(),
          duration: this.transitionDuration,
          reduced: this.reducedMotion,
          direction: number(direction, 1) < 0 ? -1 : 1,
          outgoing: this._active,
          incoming: incoming,
          notified: false,
          animations: [],
          midpointTimer: null,
          finishTimer: null,
          onHalfway: typeof onHalfway === 'function' ? onHalfway : function () {},
          resolve: resolve
        };
        if (this.paused || this._hidden) {
          this._completeTransition();
          return;
        }
        this.planes.forEach(function (plane) { plane.style.willChange = 'transform, opacity'; });
        if (this._native) {
          try {
            this._animateTransition(transition);
            return;
          } catch (_) {
            this._clearTransitionAnimation(transition);
            this._native = false;
          }
        }
        // Older browsers keep the same depth path; only transitions need a JS frame loop.
        this._renderFallback(transition.started);
        this._requestTick();
      });
    }

    setReducedMotion(value) {
      if (this.disposed) return;
      var changed = this.reducedMotion !== Boolean(value);
      this.reducedMotion = Boolean(value);
      if (this._transition) this._completeTransition();
      this._stopLoop();
      this._cancelIdle();
      this._resetPointer();
      this._renderStable();
      if (changed || this.reducedMotion) this._drawDust();
      this._startIdle();
    }

    setPaused(value) {
      if (this.disposed) return;
      this.paused = Boolean(value);
      if (this.paused) {
        if (this._transition) this._completeTransition();
        this._stopLoop();
        this._pauseIdle();
        this._resetPointer();
        this._renderStable();
      } else {
        this._startIdle();
      }
    }

    dispose() {
      if (this.disposed) return;
      this.disposed = true;
      this._abort();
      if (this._resizeRaf !== null) window.cancelAnimationFrame(this._resizeRaf);
      this._resizeRaf = null;
      this._imageCache.forEach(function (entry) { entry.cancel(); });
      this._imageCache.clear();
      this.stage.removeEventListener('pointermove', this._pointerBound);
      this.stage.removeEventListener('pointerleave', this._leaveBound);
      window.removeEventListener('resize', this._resizeBound);
      window.document.removeEventListener('visibilitychange', this._visibilityBound);
      this.images.forEach(function (image) { image.onerror = null; });
      this.planes.concat(this.rings).forEach(function (element) { element.style.willChange = ''; });
      this._clearCanvas();
    }

    _applyProduct(index, product, src) {
      var image = this.images[index];
      var plane = this.planes[index];
      image.alt = product.alt;
      image.onerror = function () {
        image.onerror = null;
        image.src = FALLBACK_IMAGE;
        plane.dataset.imageError = 'true';
      };
      plane.dataset.imageError = src === FALLBACK_IMAGE ? 'true' : 'false';
      if (image.getAttribute('src') !== src) image.src = src;
      plane.style.visibility = 'visible';
    }

    _loadImage(src) {
      if (!src) return Promise.resolve({ src: FALLBACK_IMAGE });
      var cached = this._imageCache.get(src);
      if (cached) {
        this._imageCache.delete(src);
        this._imageCache.set(src, cached);
        return cached.promise;
      }
      var entry = { loader: new window.Image(), cancel: function () {} };
      entry.promise = new Promise((resolve) => {
        var settled = false;
        var timeout;
        var finish = function (result) {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          entry.loader.onload = entry.loader.onerror = null;
          resolve(result);
        };
        entry.cancel = function () { finish({ src: FALLBACK_IMAGE, cancelled: true }); };
        timeout = window.setTimeout(function () { finish({ src: FALLBACK_IMAGE }); }, IMAGE_TIMEOUT_MS);
        entry.loader.onerror = function () { finish({ src: FALLBACK_IMAGE }); };
        entry.loader.onload = function () {
          if (!entry.loader.naturalWidth) { finish({ src: FALLBACK_IMAGE }); return; }
          if (typeof entry.loader.decode === 'function') {
            entry.loader.decode().then(function () { finish({ src: src }); }, function () {
              finish({ src: entry.loader.naturalWidth ? src : FALLBACK_IMAGE });
            });
          } else {
            finish({ src: src });
          }
        };
        entry.loader.decoding = 'async';
        entry.loader.src = src;
      });
      this._imageCache.set(src, entry);
      while (this._imageCache.size > CACHE_LIMIT) {
        var oldest = this._imageCache.keys().next().value;
        this._imageCache.get(oldest).cancel();
        this._imageCache.delete(oldest);
      }
      return entry.promise;
    }

    _waitForImage(src) {
      return new Promise((resolve) => {
        var settled = false;
        var finish = result => {
          if (settled) return;
          settled = true;
          if (this._cancelImageWait === cancel) this._cancelImageWait = null;
          resolve(result);
        };
        var cancel = function () { finish({ cancelled: true }); };
        this._cancelImageWait = cancel;
        this._loadImage(src).then(finish);
      });
    }

    _abort() {
      this._epoch += 1;
      if (this._cancelImageWait) this._cancelImageWait();
      var transition = this._transition;
      this._transition = null;
      if (transition) this._clearTransitionAnimation(transition);
      this.planes.forEach(function (plane) { plane.style.willChange = ''; });
      this._busy = false;
      this._stopLoop();
      this._cancelIdle();
      if (transition) transition.resolve(false);
    }

    _notifyHalfway(transition) {
      if (transition.notified) return;
      transition.notified = true;
      try { transition.onHalfway(); } catch (error) {
        window.console.warn('MiraStage onHalfway callback failed:', error);
      }
    }

    _completeTransition() {
      var transition = this._transition;
      if (!transition) return;
      this._notifyHalfway(transition);
      if (this.disposed || this._transition !== transition) return;
      this._clearTransitionAnimation(transition);
      this._cancelIdle();
      this._stopLoop();
      this._active = transition.incoming;
      this.planes[transition.outgoing].style.opacity = '0';
      this.planes[transition.outgoing].style.visibility = 'hidden';
      this.planes[transition.outgoing].style.willChange = '';
      this._transition = null;
      this._busy = false;
      this._resetPointer();
      this._renderStable();
      this._startIdle();
      transition.resolve(true);
    }

    _clearTransitionAnimation(transition) {
      window.clearTimeout(transition.midpointTimer);
      window.clearTimeout(transition.finishTimer);
      transition.animations.forEach(function (animation) {
        animation.onfinish = null;
        animation.cancel();
      });
      transition.animations = [];
      this.rings.forEach(function (ring) { ring.style.willChange = ''; });
      if (this.canvas) this.canvas.style.willChange = '';
    }

    _frame(transition, p, incoming) {
      var product = this._products[incoming ? transition.incoming : transition.outgoing];
      if (transition.reduced) {
        return { transform: transform(0, 0, 0, 0, 0, product.rotation, product.scale), opacity: incoming ? p : 1 - p };
      }
      var departure = smooth(0, 0.76, p);
      var remainder = 1 - easeOut((p - 0.045) / 0.955);
      var amount = incoming ? remainder : departure;
      var forward = transition.direction > 0;
      var opacity = incoming ? smooth(0.04, 0.4, p) : 1 - smooth(0.14, 0.66, p);
      var x, y, z, rx, ry, rz;
      if (forward && !incoming) {
        x = this._bounds.width * 0.48 * amount; y = -14 * amount;
        z = PERSPECTIVE * 0.39 * amount; rx = 2 * amount; ry = 6 * amount;
        rz = product.rotation - 7 * amount;
      } else if (forward) {
        x = -this._bounds.width * 0.04 * amount; y = 20 * amount;
        z = -1350 * amount; rx = -2 * amount; ry = -5 * amount;
        rz = product.rotation + 4 * amount;
      } else if (!incoming) {
        x = this._bounds.width * 0.04 * amount; y = 20 * amount;
        z = -1350 * amount; rx = -2 * amount; ry = 5 * amount;
        rz = product.rotation + 4 * amount;
      } else {
        x = -this._bounds.width * 0.48 * amount; y = -14 * amount;
        z = PERSPECTIVE * 0.39 * amount; rx = 2 * amount; ry = -6 * amount;
        rz = product.rotation + 7 * amount;
      }
      return { transform: transform(x, y, z, rx, ry, rz, product.scale), opacity: opacity };
    }

    _animateTransition(transition) {
      var count = transition.reduced ? 1 : 28;
      var outgoing = [], incoming = [];
      for (var i = 0; i <= count; i += 1) {
        var p = i / count;
        outgoing.push(Object.assign({ offset: p }, this._frame(transition, p, false)));
        incoming.push(Object.assign({ offset: p }, this._frame(transition, p, true)));
      }
      var timing = { duration: transition.duration, easing: 'linear', fill: 'both' };
      transition.animations.push(this.planes[transition.outgoing].animate(outgoing, timing));
      var lead = this.planes[transition.incoming].animate(incoming, timing);
      transition.animations.push(lead);
      if (!transition.reduced) {
        this.rings.forEach(function (ring, index) {
          ring.style.willChange = 'transform, opacity';
          transition.animations.push(ring.animate([
            { transform: ringTransform(index, 0), opacity: 0.10 },
            { transform: ringTransform(index, transition.direction * 190), opacity: 0.18, offset: 0.44 },
            { transform: ringTransform(index, 0), opacity: 0.10 }
          ], { duration: transition.duration, easing: 'cubic-bezier(.22,.6,.25,1)', fill: 'both' }));
        });
        if (this.canvas && this.context) {
          this.canvas.style.willChange = 'transform, opacity';
          transition.animations.push(this.canvas.animate([
            { transform: 'scale(1)', opacity: 1 },
            { transform: 'scale(' + (transition.direction > 0 ? '1.065' : '.95') + ')', opacity: .6, offset: .45 },
            { transform: 'scale(1)', opacity: 1 }
          ], { duration: transition.duration, easing: 'ease-in-out', fill: 'both' }));
        }
      }
      transition.midpointTimer = window.setTimeout(() => {
        if (this._transition === transition) this._notifyHalfway(transition);
      }, Math.round(transition.duration * MIDPOINT));
      lead.onfinish = () => { if (this._transition === transition) this._completeTransition(); };
      // A bounded guard also releases navigation if a browser drops an animation finish event.
      transition.finishTimer = window.setTimeout(() => {
        if (this._transition === transition) this._completeTransition();
      }, transition.duration + 120);
    }

    _renderFallback(now) {
      var transition = this._transition;
      if (!transition) return;
      var p = clamp((now - transition.started) / transition.duration, 0, 1);
      Object.assign(this.planes[transition.outgoing].style, this._frame(transition, p, false));
      Object.assign(this.planes[transition.incoming].style, this._frame(transition, p, true));
      if (p >= MIDPOINT) this._notifyHalfway(transition);
      if (this._transition === transition && p >= 1) this._completeTransition();
    }

    _renderStable() {
      var product = this._products[this._active];
      if (!product) return;
      var plane = this.planes[this._active];
      plane.style.transform = transform(0, 0, 0, -this._tilt.y * 2.6, this._tilt.x * 4,
        product.rotation, product.scale);
      plane.style.opacity = '1';
      plane.style.visibility = 'visible';
      plane.style.willChange = '';
      this.rings.forEach(function (ring, index) {
        ring.style.transform = ringTransform(index, 0);
        ring.style.opacity = '0.10';
      });
    }

    _startIdle() {
      if (this.disposed || this.paused || this._hidden || this.reducedMotion || this._transition || !this._products[this._active] || !this._native) return;
      if (this._idleAnimation && this._idleIndex === this._active) {
        this._idleAnimation.play();
        return;
      }
      this._cancelIdle();
      this._idleIndex = this._active;
      // Native transform-only drift stays smooth without a permanent JS/canvas frame loop.
      try {
        this._idleAnimation = this.images[this._active].animate(IDLE_FRAMES,
          { duration: 7200, iterations: Infinity, easing: 'linear' });
      } catch (_) {
        this._native = false;
        this._idleAnimation = null;
        this._idleIndex = -1;
      }
    }

    _pauseIdle() { if (this._idleAnimation) this._idleAnimation.pause(); }
    _cancelIdle() {
      if (this._idleAnimation) this._idleAnimation.cancel();
      this._idleAnimation = null;
      this._idleIndex = -1;
    }
    _resetPointer() {
      this._pointer.x = this._pointer.y = this._tilt.x = this._tilt.y = 0;
      this._lastTime = 0;
    }
    _requestTick() {
      if (this._raf !== null || this.disposed || this.paused || this._hidden) return;
      this._raf = window.requestAnimationFrame(this._tickBound);
    }
    _stopLoop() {
      if (this._raf !== null) window.cancelAnimationFrame(this._raf);
      this._raf = null;
      this._lastTime = 0;
    }
    _tick(now) {
      this._raf = null;
      if (this.disposed || this.paused || this._hidden) return;
      if (this._transition) {
        if (!this._native) {
          this._renderFallback(now);
          if (this._transition) this._requestTick();
        }
        return;
      }
      if (this.reducedMotion || this._busy || !this._products[this._active]) return;
      var dt = this._lastTime ? clamp((now - this._lastTime) / 1000, 0, .05) : 1 / 60;
      this._lastTime = now;
      var tracking = 1 - Math.exp(-dt * 13);
      this._tilt.x += (this._pointer.x - this._tilt.x) * tracking;
      this._tilt.y += (this._pointer.y - this._tilt.y) * tracking;
      var settled = Math.abs(this._pointer.x - this._tilt.x) < .002 && Math.abs(this._pointer.y - this._tilt.y) < .002;
      if (settled) { this._tilt.x = this._pointer.x; this._tilt.y = this._pointer.y; }
      var product = this._products[this._active];
      var plane = this.planes[this._active];
      plane.style.transform = transform(0, 0, 0, -this._tilt.y * 2.6, this._tilt.x * 4,
        product.rotation, product.scale);
      plane.style.willChange = settled ? '' : 'transform';
      if (!settled) this._requestTick();
      else this._lastTime = 0;
    }

    _resize() {
      if (this.disposed) return;
      if (this._transition) this._completeTransition();
      var stageRect = this.stage.getBoundingClientRect();
      this._bounds = {
        left: stageRect.left, top: stageRect.top,
        width: Math.max(1, stageRect.width), height: Math.max(1, stageRect.height)
      };
      var canvasRect = this.canvas ? this.canvas.getBoundingClientRect() : null;
      var width = Math.max(1, (canvasRect && canvasRect.width) || window.innerWidth);
      var height = Math.max(1, (canvasRect && canvasRect.height) || window.innerHeight);
      // Dust is tiny and soft: 1x already preserves its appearance and limits layer memory.
      this._viewport = { width: width, height: height, dpr: 1 };
      this._origin = {
        x: stageRect.left + stageRect.width / 2 - (canvasRect ? canvasRect.left : 0),
        y: stageRect.top + stageRect.height / 2 - (canvasRect ? canvasRect.top : 0)
      };
      if (this.canvas && this.context) {
        this.canvas.width = Math.round(width);
        this.canvas.height = Math.round(height);
        this.canvas.style.transformOrigin = this._origin.x + 'px ' + this._origin.y + 'px';
      }
      this._drawDust();
      this._renderStable();
    }

    _drawDust() {
      var context = this.context;
      if (!context) return;
      this._clearCanvas();
      if (this.reducedMotion) return;
      var width = this._viewport.width, height = this._viewport.height;
      var count = width < 700 ? 24 : 42;
      context.fillStyle = '#efe9e3';
      // Deterministic positions avoid a new glitter pattern whenever the address bar resizes.
      for (var i = 0; i < count; i += 1) {
        var a = (i * .61803398875 + .17) % 1;
        var b = (i * .41421356237 + .29) % 1;
        var radius = .55 + (i % 5) * .17;
        context.globalAlpha = .10 + (i % 7) * .035;
        context.beginPath();
        context.arc(a * width, b * height, radius, 0, Math.PI * 2);
        context.fill();
      }
      context.globalAlpha = 1;
    }
    _clearCanvas() {
      if (this.context) this.context.clearRect(0, 0, this._viewport.width, this._viewport.height);
    }
    _onPointerMove(event) {
      if (this.reducedMotion || this.paused || this._hidden || this._busy || event.pointerType === 'touch') return;
      this._pointer.x = clamp((event.clientX - this._bounds.left) / this._bounds.width * 2 - 1, -1, 1);
      this._pointer.y = clamp((event.clientY - this._bounds.top) / this._bounds.height * 2 - 1, -1, 1);
      this._requestTick();
    }
    _onPointerLeave() {
      this._pointer.x = this._pointer.y = 0;
      if (!this.reducedMotion && !this.paused && !this._hidden && !this._busy) this._requestTick();
    }
    _onVisibilityChange() {
      this._hidden = Boolean(window.document.hidden);
      if (this._hidden) {
        if (this._transition) this._completeTransition();
        this._stopLoop();
        this._pauseIdle();
        this._resetPointer();
        this._renderStable();
      } else {
        this._startIdle();
      }
    }
  }
  window.MiraStage = MiraStage;
}());
