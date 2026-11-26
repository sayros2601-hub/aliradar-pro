"""Non-destructive affiliate destination checks. A redirect is not proof of stock."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
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


def load_catalog_products(catalog_path=None):
    """Load non-demo products from products.json or catalog.js cleanly."""
    path = Path(catalog_path) if catalog_path else PRODUCTS_FILE
    if not catalog_path or path == PRODUCTS_FILE:
        return read_json(PRODUCTS_FILE)["products"]
    raw = path.read_text(encoding="utf-8").strip()
    if path.suffix == ".js" and "=" in raw:
        raw = raw.split("=", 1)[1].strip().rstrip(";")
    data = json.loads(raw)
    items = data["products"] if isinstance(data, dict) else data
    out = []
    for item in items:
        if not isinstance(item, dict) or item.get("demo"):
            continue
        out.append({
            "id": item.get("id"),
            "slug": item.get("slug") or item.get("id"),
            "affiliate_url": item.get("affiliate_url") or item.get("affiliateUrl") or "",
            "item_id": item.get("item_id") or item.get("sourceProductId"),
        })
    return out


def _write_markdown_summary(summary_path, report):
    if not summary_path:
        return
    counts = report.get("summary") or {}
    results = report.get("results") or []
    broken = [r for r in results if r.get("status") != "RESOLVED"]
    lines = [
        "## AliExpress Affiliate Link Health Audit",
        f"- Checked links: **{len(results)}**",
        f"- Summary: `{json.dumps(counts, ensure_ascii=False)}`",
    ]
    if broken:
        lines.append(f"- Non-resolved links ({len(broken)}):")
        for row in broken[:30]:
            lines.append(f"  - `{row.get('id')}`: {row.get('status')} ({row.get('reason')})")
    Path(summary_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(summary_path).open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="", help="Path to products.json or catalog.js")
    parser.add_argument("--dry-run", action="store_true", help="Check links without writing even the report")
    parser.add_argument("--summary", default="", help="Optional markdown summary file (e.g. $GITHUB_STEP_SUMMARY)")
    args = parser.parse_args()
    products = load_catalog_products(args.catalog or None)
    report = audit_catalog(products, write=not args.dry_run)
    _write_markdown_summary(args.summary, report)
