"""Non-destructive affiliate destination checks. A redirect is not proof of stock."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse
from dealvault_core import DATA_DIR, affiliate_key, read_json, utc_now, write_json

PRODUCTS_FILE = DATA_DIR / "products.json"
REPORT_FILE = DATA_DIR / "link_health_report.json"


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def allowed_destination(url):
    try:
        p = urlparse(url)
        host = p.hostname or ""
        return (p.scheme == "https" and not p.username and not p.password and p.port in (None, 443)
                and any(host == d or host.endswith("." + d) for d in ("aliexpress.com", "aliexpress.us", "aliexpress.ru")))
    except ValueError:
        return False


def item_id(url):
    match = re.search(r"/(?:item|i)/(\d{10,})\.html", urlparse(url).path)
    return match.group(1) if match else None


def check_single_link(product, opener=None, timeout=7):
    result = {"id": product.get("id"), "slug": product.get("slug"), "checked_at": utc_now(),
              "status": "UNKNOWN", "reason": "UNRESOLVED", "dest": "", "item_id": None,
              "affiliate_url": product.get("affiliate_url", "")}
    url = product.get("affiliate_url", "")
    if not affiliate_key(url):
        return {**result, "status": "INVALID", "reason": "INVALID_AFFILIATE_URL"}
    opener = opener or urllib.request.build_opener(NoRedirectHandler)
    visited = set()
    started = time.monotonic()
    for _ in range(8):
        if not allowed_destination(url):
            return {**result, "reason": "UNEXPECTED_REDIRECT_HOST"}
        if url in visited or time.monotonic() - started > 25:
            return {**result, "reason": "REDIRECT_LIMIT"}
        visited.add(url)
        result["dest"] = url
        expected, actual = product.get("item_id"), item_id(url)
        if actual:
            if expected and str(expected) != actual:
                return {**result, "status": "MISMATCH", "reason": "WRONG_PRODUCT_ID", "item_id": actual}
            return {**result, "status": "RESOLVED", "reason": "PRODUCT_DESTINATION_ONLY", "item_id": actual}
        parsed = urlparse(url)
        if parsed.hostname == "best.aliexpress.com" and parsed.path in ("", "/"):
            return {**result, "status": "UNAVAILABLE", "reason": "FALLBACK_HOMEPAGE"}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
            try:
                response = opener.open(req, timeout=timeout)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                code, location = response.code, response.headers.get("Location")
                if code in (301, 302, 303, 307, 308) and location:
                    url = urljoin(url, location)
                    continue
                if code in (404, 410):
                    return {**result, "status": "UNAVAILABLE", "reason": f"HTTP_{code}"}
                return {**result, "reason": f"HTTP_{code}_WITHOUT_PRODUCT_DESTINATION"}
        except (urllib.error.URLError, TimeoutError, OSError):
            return {**result, "reason": "NETWORK_OR_TIMEOUT"}
    return {**result, "reason": "REDIRECT_LIMIT"}


def audit_catalog(products=None, report_path=REPORT_FILE, write=True, workers=4):
    products = products if products is not None else read_json(PRODUCTS_FILE)["products"]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(check_single_link, products))
    report = {"checked_at": utc_now(), "scope": "affiliate_destination_only", "stock_verified": False,
              "summary": dict(Counter(r["status"] for r in results)), "results": results}
    if write:
        write_json(report_path, report)
    print(f"[Link audit] {report['summary']}; catalog unchanged.")
    return report


def validate_and_clean_catalog():
    """Compatibility: auditing never deletes products on network errors."""
    db = read_json(PRODUCTS_FILE)
    audit_catalog(db["products"])
    return db["products"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Check links without writing even the report")
    args = parser.parse_args()
    audit_catalog(write=not args.dry_run)
