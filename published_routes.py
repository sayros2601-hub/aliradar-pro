"""Remember published product URLs without retaining stale offers or affiliate buttons."""
import re
from dealvault_core import DATA_DIR, LANGUAGES, read_json, write_json

ROUTES_FILE = DATA_DIR / 'published_routes.json'


def known_routes(products, path=None):
    records = read_json(path or ROUTES_FILE, [])
    merged = {}
    for item in [*records, *products]:
        slug = item.get('slug') if isinstance(item, dict) else None
        titles = item.get('title_i18n', {}) if isinstance(item, dict) else {}
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            raise ValueError('Unsafe published route')
        if not isinstance(titles, dict) or any(not isinstance(titles.get(l), str) or not titles[l].strip() for l in LANGUAGES):
            raise ValueError('Published route needs translated titles')
        merged[slug] = {'slug': slug, 'title_i18n': {l: titles[l] for l in LANGUAGES}}
    return list(merged.values())


def save_routes(products):
    write_json(ROUTES_FILE, known_routes(products))
