/* DealVault browser preferences and sharing. Original partner URLs stay unchanged. */
(() => {
  'use strict';
  const store = {get(key) {try {return sessionStorage.getItem(key);} catch {return null;}},set(key,value) {try {sessionStorage.setItem(key,value);} catch {}}};
  const campaign = {};
  const incoming = new URLSearchParams(location.search);
  for (const key of ['utm_source','utm_medium','utm_campaign','utm_content','utm_term']) {
    const value = incoming.get(key) || store.get('dv_' + key);
    if (value) {campaign[key] = value.slice(0,128); store.set('dv_' + key, campaign[key]);}
  }
  window.DealVaultCampaign = campaign;
  // Do not append undocumented affiliate parameters or rewrite account attribution.
  window.decorateAffiliateUrl = raw => raw;
  window.trackAffiliateClick = () => {};
  window.showShareToast = message => window.DealVaultToast?.(message);
})();
