"""Local preview with the clean routes used by Cloudflare Pages."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from dealvault_core import BASE_DIR


class PagesHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        translated=Path(super().translate_path(path))
        if not translated.exists() and not Path(urlsplit(path).path).suffix:
            html=translated.with_suffix('.html')
            if html.is_file(): return str(html)
        return str(translated)


if __name__ == '__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8080),partial(PagesHandler,directory=str(BASE_DIR/'dist')))
    print('Preview: http://127.0.0.1:8080')
    server.serve_forever()
