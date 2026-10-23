"""Shared paths, validation and atomic storage for the DealVault pipeline."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LANGUAGES = ("en", "ru", "he", "es")
DOMAIN = "https://dealvault.pages.dev"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path, default=None):
    path = Path(path)
    if not path.exists() and default is not None:
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def affiliate_key(url):
    """Validate shortlink shape; preserve all original tracking parameters."""
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        return None
    try:
        parsed = urlparse(url)
        if (parsed.scheme == "https" and parsed.hostname == "s.click.aliexpress.com"
                and not parsed.username and not parsed.password and parsed.port in (None, 443)
                and re.fullmatch(r"/e/_[A-Za-z0-9_-]+", parsed.path)):
            return parsed.netloc.lower() + parsed.path
    except (TypeError, ValueError):
        pass
    return None


def page_path(lang="en", slug=None, legal=None):
    prefix = "" if lang == "en" else f"{lang}/"
    if slug:
        return f"{prefix}deals/{slug}.html"
    return prefix + (f"{legal}.html" if legal else "index.html")


def public_path(path):
    """Cloudflare Pages' canonical route for a generated file."""
    path=str(path).replace('\\','/').lstrip('/')
    if path.endswith('index.html'):
        path=path[:-len('index.html')]
    elif path.endswith('.html'):
        path=path[:-5]
    return '/'+path


def product_title(product, lang="en"):
    return product.get("title_i18n", {}).get(lang) or product.get("title_i18n", {}).get("en") or product.get("title", "")


def recently_added(product, now=None):
    """New means added within seven days, never a permanent imported flag."""
    if product.get('is_new') is not True:
        return False
    try:
        added = datetime.fromisoformat(product['added_at'].replace('Z', '+00:00'))
        return added.tzinfo is not None and timedelta(0) <= (now or datetime.now(timezone.utc)) - added <= timedelta(days=7)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def validate_catalog(db, root=BASE_DIR):
    errors = []
    products = db.get("products", [])
    if not products:
        errors.append("Refusing to build an empty catalog")
    ids, slugs, links, item_ids = set(), set(), set(), set()
    cats = {c["id"] for c in db.get("categories", [])}
    for p in products:
        pid, slug = p.get("id"), p.get("slug", "")
        key = affiliate_key(p.get("affiliate_url"))
        item = p.get('item_id')
        if p.get('source') == 'curated_ai_studio' or (item and not str(item).isdigit()):
            errors.append(f'{pid}: marketplace identity must come from an actual product')
        if item:
            if str(item) in item_ids:
                errors.append(f'{pid}: duplicate marketplace item ID')
            item_ids.add(str(item))
        for value, seen, label in [(pid, ids, "id"), (slug, slugs, "slug"), (key, links, "affiliate destination")]:
            if not value or value in seen:
                errors.append(f"{pid}: missing/duplicate {label}")
            seen.add(value)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            errors.append(f"{pid}: unsafe slug")
        if not key:
            errors.append(f"{pid}: expected an original AliExpress Portals HTTPS shortlink")
        price = p.get("price_usd")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            errors.append(f"{pid}: invalid reference price")
        if p.get("category") not in cats:
            errors.append(f"{pid}: unknown category")
        if any(not p.get("title_i18n", {}).get(lang) for lang in LANGUAGES):
            errors.append(f"{pid}: missing translated title")
        for asset in [p.get("image", ""), *p.get("gallery", [])]:
            target = (root / asset).resolve()
            if not asset.startswith("assets/img/") or root.resolve() not in target.parents or not target.is_file():
                errors.append(f"{pid}: missing or unsafe local image {asset}")
    if errors:
        raise ValueError("Catalog validation failed:\n" + "\n".join(errors))
    return products
