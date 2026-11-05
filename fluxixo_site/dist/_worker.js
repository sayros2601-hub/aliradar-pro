// Only the retired editor routes in _routes.json invoke this function.
const retired = new Set(['/editor', '/editor/', '/editor.html', '/js/editor.js', '/css/editor.css']);
export default {
  async fetch(request, env) {
    if (!retired.has(new URL(request.url).pathname)) return env.ASSETS.fetch(request);
    return new Response(request.method === 'HEAD' ? null : 'This editor is no longer publicly available.\n', {
      status: 410,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Robots-Tag': 'noindex, nofollow',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        'Strict-Transport-Security': 'max-age=2592000'
      }
    });
  }
};
