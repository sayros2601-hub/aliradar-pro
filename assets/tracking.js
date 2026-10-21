/**
 * SMARTPICK MATRIX // AD TRACKING & ATTRIBUTION ENGINE
 * Supports:
 * - Google Analytics 4 (GA4)
 * - Meta Pixel (Facebook Pixel)
 * - TikTok Pixel
 * - UTM Parameter persistence & passthrough
 * - Outbound Affiliate Click telemetry
 */
(() => {
  'use strict';

  // 1. UTM Parameter Capture & Persistence
  const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'subid'];
  const params = new URLSearchParams(window.location.search);
  const utmObj = {};

  UTM_KEYS.forEach(k => {
    const val = params.get(k);
    if (val) {
      utmObj[k] = val;
      try { sessionStorage.setItem('sp_' + k, val); } catch (e) {}
    } else {
      try {
        const stored = sessionStorage.getItem('sp_' + k);
        if (stored) utmObj[k] = stored;
      } catch (e) {}
    }
  });

  window.SmartPickUTM = utmObj;

  // 2. Outbound Link Decorator: Appends subids to affiliate clicks
  window.decorateAffiliateUrl = function(rawUrl, prodId) {
    if (!rawUrl) return rawUrl;
    try {
      const u = new URL(rawUrl);
      if (utmObj.utm_source) u.searchParams.set('aff_sub', utmObj.utm_source);
      if (utmObj.utm_campaign) u.searchParams.set('aff_sub2', utmObj.utm_campaign);
      if (prodId) u.searchParams.set('aff_sub3', prodId);
      return u.toString();
    } catch (e) {
      return rawUrl;
    }
  };

  // 3. Track Outbound Affiliate Click Event
  window.trackAffiliateClick = function(product) {
    const payload = {
      product_id: product.id || 'unknown',
      product_name: typeof product.title === 'string' ? product.title : (product.title?.he || product.title?.en || 'product'),
      price_usd: product.price_usd || 0,
      category: product.category || 'all',
      currency: window.SmartPickCurrentCurrency || 'ILS',
      utm_source: utmObj.utm_source || 'direct',
      utm_campaign: utmObj.utm_campaign || 'none',
      timestamp: new Date().toISOString()
    };

    // Google Analytics 4
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'affiliate_click', {
        item_id: payload.product_id,
        item_name: payload.product_name,
        value: payload.price_usd,
        currency: 'USD',
        item_category: payload.category
      });
      window.gtag('event', 'conversion', {
        send_to: 'affiliate_outbound'
      });
    }

    // Meta Pixel (Facebook)
    if (typeof window.fbq === 'function') {
      window.fbq('trackCustom', 'AffiliateClick', {
        content_name: payload.product_name,
        content_category: payload.category,
        content_ids: [payload.product_id],
        value: payload.price_usd,
        currency: 'USD'
      });
    }

    // TikTok Pixel
    if (typeof window.ttq === 'function' && window.ttq.track) {
      window.ttq.track('ClickButton', {
        content_id: payload.product_id,
        content_name: payload.product_name,
        value: payload.price_usd,
        currency: 'USD'
      });
    }

    // Local Telemetry / Debug Log
    try {
      const clicks = JSON.parse(localStorage.getItem('sp_click_log') || '[]');
      clicks.unshift(payload);
      if (clicks.length > 50) clicks.pop();
      localStorage.setItem('sp_click_log', JSON.stringify(clicks));
    } catch (e) {}

    console.log('[SmartPick Tracker] Affiliate Click Tracked:', payload);
  };

  // 4. Quick Share Helpers (WhatsApp, Telegram, WebShare)
  window.shareDeal = function(platform, prod, lang) {
    const title = typeof prod.title === 'string' ? prod.title : (prod.title?.[lang] || prod.title?.he || prod.title?.en || '');
    const priceStr = prod.price_ils ? `₪${prod.price_ils}` : `$${prod.price_usd}`;
    const url = window.location.origin + window.location.pathname.replace(/\/deals\/.*$/, '') + '/#' + prod.slug;

    let text = '';
    if (lang === 'he') {
      text = `🔥 מצאתי דיל מטורף ב-DealVault:\n*${title}*\n💵 מחיר: ${priceStr} בלבד (משלוח חינם!)\n👉 לצפייה בדיל: ${url}`;
    } else if (lang === 'ru') {
      text = `🔥 Отличная находка в DealVault:\n*${title}*\n💵 Цена: ${priceStr} (Бесплатная доставка!)\n👉 Смотреть дил: ${url}`;
    } else {
      text = `🔥 Check out this verified deal on DealVault:\n*${title}*\n💵 Only ${priceStr} with Free Shipping!\n👉 View deal: ${url}`;
    }

    if (platform === 'whatsapp') {
      window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`, '_blank');
    } else if (platform === 'telegram') {
      window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`, '_blank');
    } else if (platform === 'native' && navigator.share) {
      navigator.share({ title: title, text: text, url: url }).catch(() => {});
    } else if (platform === 'copy') {
      navigator.clipboard.writeText(url).then(() => {
        showShareToast(lang === 'he' ? 'הקישור הועתק בהצלחה! 📋' : (lang === 'ru' ? 'Ссылка скопирована! 📋' : 'Link copied! 📋'));
      }).catch(() => {});
    }
  };

  function showShareToast(msg) {
    let toast = document.getElementById('sp-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'sp-toast';
      toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#00f0ff;color:#05070f;font-weight:bold;padding:10px 24px;border-radius:30px;box-shadow:0 0 20px rgba(0,240,255,0.6);z-index:99999;font-family:sans-serif;font-size:14px;transition:opacity 0.3s;';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 2200);
  }

  window.showShareToast = showShareToast;
})();
