// Redirect *.pages.dev to official domain & retire deleted endpoints
const retired = new Set(['/editor', '/editor/', '/editor.html', '/js/editor.js', '/css/editor.css', '/telegram-digest.json']);
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname.includes('pages.dev')) {
      url.hostname = 'www.fluxixo.shop';
      url.protocol = 'https:';
      return Response.redirect(url.toString(), 301);
    }
    if (!retired.has(url.pathname)) return env.ASSETS.fetch(request);
    const msg = url.pathname === '/telegram-digest.json' ? 'This feed is no longer available.\n' : 'This editor is no longer publicly available.\n';
    return new Response(request.method === 'HEAD' ? null : msg, {
      status: 410,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex, nofollow',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
      }
    });
  }
};
