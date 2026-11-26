// Redirect *.pages.dev to official domain & retire deleted endpoints
const retired = new Set(['/editor', '/editor/', '/editor.html', '/js/editor.js', '/css/editor.css', '/telegram-digest.json']);
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname.includes('pages.dev')) {
      url.hostname = 'www.fluxixo.shop';
      url.protocol = 'https:';
      return new Response(null, {
        status: 301,
        headers: {
          'Location': url.toString(),
          'X-Robots-Tag': 'noindex, nofollow',
          'Cache-Control': 'public, max-age=3600'
        }
      });
    }
    const isGoneAsset = url.pathname.startsWith('/assets/img/');
    if (!retired.has(url.pathname) && !isGoneAsset) return env.ASSETS.fetch(request);
    const msg = isGoneAsset
      ? 'This legacy image resource has been permanently removed.\n'
      : (url.pathname === '/telegram-digest.json' ? 'This feed is no longer available.\n' : 'This editor is no longer publicly available.\n');
    return new Response(request.method === 'HEAD' ? null : msg, {
      status: 410,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': isGoneAsset ? 'public, max-age=86400' : 'no-store',
        'X-Robots-Tag': 'noindex, nofollow',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
      }
    });
  }
};
