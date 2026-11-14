"""Reusable Search Engine, Cloudflare & Live Technical SEO Health Audit Utility for FLUXIXO.

Checks:
1. DPAPI-encrypted credential store in `.local/` (`CryptProtectData` / `CryptUnprotectData`).
2. Cloudflare API (token status, Pages project `dealvault`, latest deployment, custom domains,
   apex redirect `fluxixo.shop -> www.fluxixo.shop`, SSL/security/cache headers, Web Analytics beacon).
3. Google Search integration (`google-site-verification` meta tag, `sitemap.xml`, `robots.txt`,
   `rss.xml`, WebSub hub reachability, and optional `gsc-service-account.dpapi` API query).
4. Microsoft Bing integration (`msvalidate.01` meta tag, `BingSiteAuth.xml`, IndexNow key files,
   `indexnow-submitted.json` coverage, and optional `bing-api-key.dpapi` Webmaster API query).
5. Yandex Webmaster integration (`yandex-verification` meta tag, `User-agent: Yandex` & `Clean-param`
   in `robots.txt`, `sitemap-ru.xml` 103 RU URLs coverage, `yandex-indexnow-state.json` acknowledged
   vs pending count, and optional `yandex-oauth-token.dpapi` Webmaster API v4 query).
6. Full Live Technical SEO, Link, Reciprocal Hreflang & JSON-LD Schema Audit across all 6 languages
   (`ru`, `en`, `es`, `pt`, `fr`, `he`).
"""
from __future__ import annotations

import argparse
import collections
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import ctypes.wintypes
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import statistics
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener, urlopen
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOOLS_DIR = Path(__file__).resolve().parent
SITE_ROOT = TOOLS_DIR.parent
HUB_ROOT = SITE_ROOT.parent
LOCAL_DIR = HUB_ROOT / ".local"

ORIGIN = "https://www.fluxixo.shop"
APEX_ORIGIN = "https://fluxixo.shop"
CF_ACCOUNT_ID = "a4be28e05f73ad2b3939d364ea8b2817"
CF_PROJECT_NAME = "dealvault"

EXPECTED_GOOGLE_VERIFY = "BUSamFSGELSfaWQEaVVj2QzUgKQvWovtg-ZaHCfKNb0"
EXPECTED_BING_VERIFY = "49287D3DFF71EA9430905E14A0A426F2"
EXPECTED_YANDEX_VERIFY = "deee62492f76cf5b"
EXPECTED_INDEXNOW_KEY = "ededa82eb5716fb9ef71632b519559cb"

LANGUAGES = ("ru", "en", "es", "pt", "fr", "he")
HTML_LANG_TAGS = {
    "ru": "ru",
    "en": "en",
    "pt": "pt-BR",
    "es": "es-MX",
    "fr": "fr",
    "he": "he-IL",
}
EXPECTED_HREFLANG_KEYS = {"ru", "ru-RU", "en", "en-US", "es", "es-MX", "pt", "pt-BR", "fr", "fr-FR", "he", "he-IL", "x-default"}
FOREIGN_LOCALE_RE = re.compile(r"^/(en|pt|es|fr|he)(/|$)")
FORBIDDEN_SCHEMA_TOKENS = ('"Product"', '"Offer"', "priceCurrency", "InStock", "Подборка")
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

CREDENTIAL_SPECS = {
    "cloudflare": ("cloudflare-token.dpapi", "Cloudflare API Token"),
    "bing": ("bing-api-key.dpapi", "Bing Webmaster API Key"),
    "yandex": ("yandex-oauth-token.dpapi", "Yandex Webmaster OAuth Token"),
    "gsc": ("gsc-service-account.dpapi", "Google Search Console Service Account / Token"),
}


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def dpapi_protect(raw_bytes: bytes) -> bytes:
    """Encrypt bytes using Windows DPAPI CryptProtectData bound to the current user."""
    buf = ctypes.create_string_buffer(raw_bytes, len(raw_bytes))
    blob_in = DATA_BLOB(len(raw_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    ):
        raise OSError("CryptProtectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def dpapi_unprotect(enc_bytes: bytes) -> bytes | None:
    """Decrypt bytes using Windows DPAPI CryptUnprotectData."""
    buf = ctypes.create_string_buffer(enc_bytes, len(enc_bytes))
    blob_in = DATA_BLOB(len(enc_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    ):
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return None


def load_credential(name: str) -> str | None:
    filename = CREDENTIAL_SPECS[name][0] if name in CREDENTIAL_SPECS else name
    path = LOCAL_DIR / filename
    if not path.exists():
        return None
    raw = dpapi_unprotect(path.read_bytes())
    if raw is None:
        return None
    return raw.decode("utf-8", errors="replace").strip()


def save_credential(name: str, secret_text: str) -> Path:
    filename = CREDENTIAL_SPECS[name][0] if name in CREDENTIAL_SPECS else name
    if not filename.endswith(".dpapi"):
        filename += ".dpapi"
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCAL_DIR / filename
    encrypted = dpapi_protect(secret_text.strip().encode("utf-8"))
    path.write_bytes(encrypted)
    return path


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    follow_redirects: bool = True,
    method: str = "GET",
    data: bytes | None = None,
    retries: int = 3,
) -> tuple[int, bytes, dict[str, str], float, str | None]:
    """Perform HTTP request returning (status, body, lower_headers, elapsed_ms, error)."""
    req_headers = {
        "User-Agent": "FLUXIXO-SEO-Health-Auditor/2.0 (+https://www.fluxixo.shop)",
        "Accept": "*/*",
    }
    if headers:
        req_headers.update(headers)
    last_err = None
    for attempt in range(retries):
        req = Request(url, data=data, headers=req_headers, method=method)
        start = time.perf_counter()
        try:
            if follow_redirects:
                with urlopen(req, timeout=timeout) as resp:
                    body = resp.read() if method != "HEAD" else b""
                    elapsed = (time.perf_counter() - start) * 1000.0
                    hdrs = {k.lower(): v for k, v in resp.headers.items()}
                    return resp.status, body, hdrs, elapsed, None
            else:
                opener = build_opener(_NoRedirect, HTTPSHandler(context=ssl.create_default_context()))
                with opener.open(req, timeout=timeout) as resp:
                    body = resp.read() if method != "HEAD" else b""
                    elapsed = (time.perf_counter() - start) * 1000.0
                    hdrs = {k.lower(): v for k, v in resp.headers.items()}
                    return resp.status, body, hdrs, elapsed, None
        except HTTPError as err:
            elapsed = (time.perf_counter() - start) * 1000.0
            body = err.read() if method != "HEAD" and err.fp else b""
            hdrs = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
            if err.code >= 500 and attempt + 1 < retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            return err.code, body, hdrs, elapsed, None
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000.0
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < retries:
                time.sleep(0.4 * (attempt + 1))
    return 0, b"", {}, elapsed, last_err


class LiveHTMLInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_lang = None
        self.html_dir = None
        self.title = ""
        self.description = None
        self.robots = ""
        self.canonical = None
        self.meta_verify = {}
        self.hreflang = {}
        self.h1_count = 0
        self.links = []
        self.assets = []
        self.jsonld_raw = []
        self.has_cf_beacon = False
        self._capture_tag = None
        self._buf = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.html_lang = a.get("lang")
            self.html_dir = a.get("dir", "ltr")
        elif tag == "meta":
            name = a.get("name", "").lower()
            content = a.get("content", "")
            if name == "description":
                self.description = content
            elif name == "robots":
                self.robots = content
            elif name in ("google-site-verification", "msvalidate.01", "yandex-verification"):
                self.meta_verify[name] = content
        elif tag == "link":
            rel_tokens = set(a.get("rel", "").lower().split())
            href = a.get("href", "")
            if "canonical" in rel_tokens:
                self.canonical = href
            if "alternate" in rel_tokens and a.get("hreflang"):
                self.hreflang[a["hreflang"]] = href
            if href and any(r in rel_tokens for r in ("icon", "apple-touch-icon", "manifest", "preload", "stylesheet")):
                self.assets.append(href)
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag in ("img", "script", "source", "video"):
            src = a.get("src", "")
            if src:
                if "static.cloudflareinsights.com/beacon.min.js" in src:
                    self.has_cf_beacon = True
                else:
                    self.assets.append(src)
            for part in a.get("srcset", "").split(","):
                if part.strip():
                    self.assets.append(part.strip().split()[0])
        if tag == "title" or (tag == "script" and a.get("type", "").lower() == "application/ld+json"):
            self._capture_tag = tag
            self._buf = []

    def handle_data(self, data: str):
        if self._capture_tag:
            self._buf.append(data)

    def handle_endtag(self, tag: str):
        if self._capture_tag == tag:
            text = "".join(self._buf)
            if tag == "title":
                self.title = " ".join(text.split())
            else:
                self.jsonld_raw.append(text)
            self._capture_tag = None


def check_credentials_store() -> dict:
    report = {}
    for key, (filename, label) in CREDENTIAL_SPECS.items():
        path = LOCAL_DIR / filename
        if not path.exists():
            report[key] = {"file": filename, "label": label, "present": False, "decrypted": False}
        else:
            val = load_credential(key)
            report[key] = {
                "file": filename,
                "label": label,
                "present": True,
                "decrypted": bool(val),
                "bytes": path.stat().st_size,
            }
    return report


def check_cloudflare() -> dict:
    result = {
        "token_status": "missing",
        "project": None,
        "latest_deployment": None,
        "domains": [],
        "apex_redirect": {},
        "ssl_and_headers": {},
        "web_analytics_beacon": {},
        "issues": [],
    }
    token = load_credential("cloudflare")
    if not token:
        result["issues"].append("Missing or undecryptable .local/cloudflare-token.dpapi")
    else:
        auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        st, body, _, _, err = http_get(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/tokens/verify",
            headers=auth_headers,
        )
        if st != 200:
            st, body, _, _, err = http_get(
                "https://api.cloudflare.com/client/v4/user/tokens/verify",
                headers=auth_headers,
            )
        if st == 200 and not err:
            data = json.loads(body.decode("utf-8"))
            result["token_status"] = data.get("result", {}).get("status", "unknown")

        proj_url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects/{CF_PROJECT_NAME}"
        st, body, _, _, err = http_get(proj_url, headers=auth_headers)
        if st == 200 and not err:
            if result["token_status"] == "missing":
                result["token_status"] = "active (scoped to Cloudflare Pages)"
            proj = json.loads(body.decode("utf-8")).get("result", {})
            result["project"] = {
                "name": proj.get("name"),
                "subdomain": proj.get("subdomain"),
                "production_branch": proj.get("production_branch"),
                "domains": proj.get("domains", []),
            }
            latest = proj.get("canonical_deployment") or proj.get("latest_deployment") or {}
            stage = latest.get("latest_stage") or {}
            result["latest_deployment"] = {
                "id": latest.get("id"),
                "url": latest.get("url"),
                "environment": latest.get("environment"),
                "created_on": latest.get("created_on"),
                "stage_name": stage.get("name"),
                "stage_status": stage.get("status"),
            }
            if stage.get("status") != "success":
                result["issues"].append(f"Latest Pages deployment stage status is {stage.get('status')}")
        else:
            result["issues"].append(f"Failed to query Cloudflare Pages project {CF_PROJECT_NAME}: HTTP {st}")

        dom_url = f"{proj_url}/domains"
        st, body, _, _, err = http_get(dom_url, headers=auth_headers)
        if st == 200 and not err:
            doms = json.loads(body.decode("utf-8")).get("result", [])
            for d in doms:
                result["domains"].append({
                    "name": d.get("name"),
                    "status": d.get("status"),
                    "ssl_status": (d.get("validation_data") or {}).get("status"),
                })
            www_dom = next((d for d in result["domains"] if d["name"] == "www.fluxixo.shop"), None)
            if not www_dom or www_dom.get("status") != "active":
                result["issues"].append("Custom domain www.fluxixo.shop is not active in Cloudflare Pages")

    # Apex redirect check: fluxixo.shop -> www.fluxixo.shop
    st, _, hdrs, ms, err = http_get(f"{APEX_ORIGIN}/", follow_redirects=False)
    loc = hdrs.get("location", "")
    redirect_ok = st in (301, 302, 308) and loc.startswith(ORIGIN)
    result["apex_redirect"] = {
        "status": st,
        "location": loc,
        "response_ms": round(ms, 1),
        "valid": redirect_ok,
        "error": err,
    }
    if not redirect_ok:
        result["issues"].append(f"Apex redirect {APEX_ORIGIN}/ -> {ORIGIN}/ failed (HTTP {st} -> {loc})")

    # SSL, headers & Web Analytics beacon check on www.fluxixo.shop
    st, body, hdrs, ms, err = http_get(f"{ORIGIN}/")
    html_text = body.decode("utf-8", errors="replace")
    has_beacon = "static.cloudflareinsights.com/beacon.min.js" in html_text
    result["ssl_and_headers"] = {
        "status": st,
        "response_ms": round(ms, 1),
        "server": hdrs.get("server"),
        "cf_ray": hdrs.get("cf-ray"),
        "cache_control": hdrs.get("cache-control"),
        "x_content_type_options": hdrs.get("x-content-type-options"),
        "referrer_policy": hdrs.get("referrer-policy"),
        "permissions_policy": hdrs.get("permissions-policy"),
        "content_security_policy_present": bool(hdrs.get("content-security-policy")),
    }
    result["web_analytics_beacon"] = {
        "injected_on_root": has_beacon,
    }
    if st != 200:
        result["issues"].append(f"Root page {ORIGIN}/ returned HTTP {st}")
    if hdrs.get("x-content-type-options") != "nosniff":
        result["issues"].append("Missing X-Content-Type-Options: nosniff header")
    if not hdrs.get("content-security-policy"):
        result["issues"].append("Missing Content-Security-Policy header")

    return result


def check_google() -> dict:
    result = {
        "verification_meta": {},
        "sitemap_xml": {},
        "robots_txt": {},
        "rss_and_websub": {},
        "gsc_api": {},
        "issues": [],
    }
    # Check verification meta tag on root and locale homepages
    locale_Verify = {}
    for lang, path in (("root_en", "/"), ("ru", "/catalog/"), ("en", "/en/"), ("es", "/es/"), ("pt", "/pt/"), ("fr", "/fr/"), ("he", "/he/")):
        st, body, _, _, _ = http_get(ORIGIN + path)
        parser = LiveHTMLInspector()
        if st == 200:
            parser.feed(body.decode("utf-8", errors="replace"))
        token = parser.meta_verify.get("google-site-verification")
        locale_Verify[lang] = {
            "path": path,
            "present": token == EXPECTED_GOOGLE_VERIFY,
            "value": token,
        }
    result["verification_meta"] = {
        "expected": EXPECTED_GOOGLE_VERIFY,
        "root_verified": locale_Verify["root_en"]["present"],
        "by_entrypoint": locale_Verify,
    }
    if not locale_Verify["root_en"]["present"]:
        result["issues"].append("Missing or mismatched google-site-verification meta tag on root '/'")

    # Check live sitemap.xml
    st, body, hdrs, ms, err = http_get(f"{ORIGIN}/sitemap.xml")
    if st != 200 or err:
        result["sitemap_xml"] = {"status": st, "valid_xml": False, "error": err}
        result["issues"].append(f"sitemap.xml unreachable: HTTP {st}")
    else:
        try:
            root = ET.fromstring(body.decode("utf-8"))
            locs = []
            lastmods = []
            for url_node in root.findall(f"{SITEMAP_NS}url"):
                loc = (url_node.findtext(f"{SITEMAP_NS}loc") or "").strip()
                lastmod = (url_node.findtext(f"{SITEMAP_NS}lastmod") or "").strip()
                if loc:
                    locs.append(loc)
                if lastmod:
                    lastmods.append(lastmod)
            by_lang = collections.Counter()
            for u in locs:
                p = urlsplit(u).path
                m = re.match(r"^/(en|es|pt|fr|he)/", p)
                by_lang[m.group(1) if m else "ru_or_root"] += 1
            result["sitemap_xml"] = {
                "status": st,
                "response_ms": round(ms, 1),
                "cache_control": hdrs.get("cache-control"),
                "valid_xml": True,
                "url_count": len(locs),
                "unique_url_count": len(set(locs)),
                "lastmod_count": len(lastmods),
                "counts_by_locale": dict(by_lang),
                "urls": locs,
            }
            if len(locs) < 100 or len(locs) != len(set(locs)):
                result["issues"].append(f"sitemap.xml anomaly: {len(locs)} total vs {len(set(locs))} unique")
        except ET.ParseError as exc:
            result["sitemap_xml"] = {"status": st, "valid_xml": False, "error": str(exc)}
            result["issues"].append(f"sitemap.xml XML parse error: {exc}")

    # Check live robots.txt for Google (*)
    st, body, _, _, err = http_get(f"{ORIGIN}/robots.txt")
    txt = body.decode("utf-8", errors="replace") if st == 200 else ""
    has_wildcard = "User-agent: *" in txt and "Allow: /" in txt
    has_sitemap = f"Sitemap: {ORIGIN}/sitemap.xml" in txt
    result["robots_txt"] = {
        "status": st,
        "wildcard_allow_root": has_wildcard,
        "declares_sitemap_xml": has_sitemap,
    }
    if st != 200 or not has_wildcard or not has_sitemap:
        result["issues"].append("robots.txt missing User-agent: * Allow: / or Sitemap declaration")

    # Check RSS feed & Google WebSub hub reachability
    rss_st, rss_body, _, _, _ = http_get(f"{ORIGIN}/rss.xml")
    rss_items = 0
    if rss_st == 200:
        try:
            rss_root = ET.fromstring(rss_body.decode("utf-8"))
            rss_items = len(rss_root.findall("./channel/item"))
        except ET.ParseError:
            rss_items = -1
    hub_st, _, _, hub_ms, hub_err = http_get("https://pubsubhubbub.appspot.com/", method="GET")
    result["rss_and_websub"] = {
        "rss_status": rss_st,
        "rss_items": rss_items,
        "websub_hub_url": "https://pubsubhubbub.appspot.com/",
        "websub_hub_status": hub_st,
        "websub_hub_ms": round(hub_ms, 1),
        "websub_reachable": hub_st in (200, 204, 400, 405) and not hub_err,
    }

    # Check optional GSC service account / token in .local/gsc-service-account.dpapi
    gsc_raw = load_credential("gsc")
    if not gsc_raw:
        result["gsc_api"] = {
            "configured": False,
            "status": "skipped (no .local/gsc-service-account.dpapi configured; public HTML meta + sitemap.xml active)",
        }
    else:
        try:
            parsed = json.loads(gsc_raw)
            if "access_token" in parsed:
                st, b, _, _, e = http_get(
                    "https://www.googleapis.com/webmasters/v3/sites",
                    headers={"Authorization": f"Bearer {parsed['access_token']}"},
                )
                result["gsc_api"] = {"configured": True, "http_status": st, "response": json.loads(b.decode("utf-8")) if st == 200 else e}
            else:
                result["gsc_api"] = {
                    "configured": True,
                    "client_email": parsed.get("client_email"),
                    "project_id": parsed.get("project_id"),
                    "status": "service_account_json_loaded",
                }
        except Exception as exc:
            result["gsc_api"] = {"configured": True, "error": str(exc)}

    return result


def check_bing(sitemap_urls: list[str]) -> dict:
    result = {
        "verification_meta": {},
        "bing_site_auth_xml": {},
        "indexnow_key_files": {},
        "indexnow_submission_ledger": {},
        "bing_webmaster_api": {},
        "issues": [],
    }
    st, body, _, _, _ = http_get(f"{ORIGIN}/")
    parser = LiveHTMLInspector()
    if st == 200:
        parser.feed(body.decode("utf-8", errors="replace"))
    msval = parser.meta_verify.get("msvalidate.01")
    result["verification_meta"] = {
        "expected": EXPECTED_BING_VERIFY,
        "present_on_root": msval == EXPECTED_BING_VERIFY,
        "value": msval,
    }
    if msval != EXPECTED_BING_VERIFY:
        result["issues"].append("Missing or mismatched msvalidate.01 meta tag on '/'")

    # BingSiteAuth.xml
    st, body, _, _, err = http_get(f"{ORIGIN}/BingSiteAuth.xml")
    xml_user = None
    if st == 200:
        try:
            xml_user = (ET.fromstring(body.decode("utf-8")).findtext("./user") or "").strip()
        except ET.ParseError:
            xml_user = "PARSE_ERROR"
    result["bing_site_auth_xml"] = {
        "status": st,
        "user": xml_user,
        "valid": st == 200 and xml_user == EXPECTED_BING_VERIFY,
    }
    if st != 200 or xml_user != EXPECTED_BING_VERIFY:
        result["issues"].append(f"BingSiteAuth.xml invalid (HTTP {st}, user={xml_user})")

    # IndexNow key files
    for path in (f"/{EXPECTED_INDEXNOW_KEY}.txt", "/indexnow.txt", "/indexnow-key.txt"):
        kst, kbody, _, _, _ = http_get(ORIGIN + path)
        ktext = kbody.decode("utf-8", errors="replace").strip() if kst == 200 else ""
        ok = kst == 200 and ktext == EXPECTED_INDEXNOW_KEY
        result["indexnow_key_files"][path] = {"status": kst, "matches_key": ok}
        if not ok:
            result["issues"].append(f"IndexNow key file {path} failed verification (HTTP {kst})")

    # indexnow-submitted.json coverage
    submitted_path = TOOLS_DIR / "indexnow-submitted.json"
    build_state_path = TOOLS_DIR / "search-build-state.json"
    if submitted_path.exists():
        submitted = json.loads(submitted_path.read_text(encoding="utf-8"))
        build_state = json.loads(build_state_path.read_text(encoding="utf-8")) if build_state_path.exists() else {}
        sitemap_set = set(sitemap_urls)
        covered = sitemap_set & set(submitted.keys())
        up_to_date = 0
        for u in covered:
            rel_path = urlsplit(u).path
            if submitted.get(u) == build_state.get(rel_path, {}).get("sha256"):
                up_to_date += 1
        result["indexnow_submission_ledger"] = {
            "total_submitted_records": len(submitted),
            "sitemap_urls_total": len(sitemap_set),
            "sitemap_urls_covered": len(covered),
            "matching_current_build_sha256": up_to_date,
            "coverage_pct": round(len(covered) * 100.0 / max(1, len(sitemap_set)), 2),
        }
        if len(covered) < len(sitemap_set):
            result["issues"].append(
                f"indexnow-submitted.json covers {len(covered)}/{len(sitemap_set)} sitemap URLs"
            )
    else:
        result["indexnow_submission_ledger"] = {"present": False}
        result["issues"].append("Missing tools/indexnow-submitted.json")

    # Optional Bing Webmaster API check via .local/bing-api-key.dpapi
    bing_key = load_credential("bing")
    if not bing_key:
        result["bing_webmaster_api"] = {
            "configured": False,
            "status": "skipped (no .local/bing-api-key.dpapi configured; IndexNow + BingSiteAuth.xml active)",
        }
    else:
        q_sites = f"https://ssl.bing.com/webmaster/api.svc/json/GetUserSites?apikey={urlencode({'k': bing_key})[2:]}"
        q_quota = (
            f"https://ssl.bing.com/webmaster/api.svc/json/GetUrlSubmissionQuota"
            f"?siteUrl={urlencode({'u': ORIGIN})[2:]}&apikey={urlencode({'k': bing_key})[2:]}"
        )
        st_s, body_s, _, _, err_s = http_get(q_sites)
        st_q, body_q, _, _, err_q = http_get(q_quota)
        result["bing_webmaster_api"] = {
            "configured": True,
            "get_user_sites_status": st_s,
            "get_user_sites": json.loads(body_s.decode("utf-8")) if st_s == 200 else err_s,
            "get_quota_status": st_q,
            "get_quota": json.loads(body_q.decode("utf-8")) if st_q == 200 else err_q,
        }
        if st_s != 200:
            result["issues"].append(f"Bing Webmaster API GetUserSites returned HTTP {st_s}")

    return result


def check_yandex(sitemap_urls: list[str]) -> dict:
    result = {
        "verification_meta": {},
        "robots_txt_yandex": {},
        "sitemap_ru_xml": {},
        "yandex_indexnow_state": {},
        "yandex_webmaster_api": {},
        "issues": [],
    }
    st, body, _, _, _ = http_get(f"{ORIGIN}/")
    parser = LiveHTMLInspector()
    if st == 200:
        parser.feed(body.decode("utf-8", errors="replace"))
    yval = parser.meta_verify.get("yandex-verification")
    result["verification_meta"] = {
        "expected": EXPECTED_YANDEX_VERIFY,
        "present_on_root": yval == EXPECTED_YANDEX_VERIFY,
        "value": yval,
    }
    if yval != EXPECTED_YANDEX_VERIFY:
        result["issues"].append("Missing or mismatched yandex-verification meta tag on '/'")

    # Check robots.txt Yandex block & Clean-param
    st, body, _, _, _ = http_get(f"{ORIGIN}/robots.txt")
    txt = body.decode("utf-8", errors="replace") if st == 200 else ""
    expected_disallows = [f"Disallow: /{loc}/" for loc in ("en", "pt", "es", "fr", "he")]
    missing_disallows = [d for d in expected_disallows if d not in txt]
    has_clean_utm = "Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term" in txt
    has_clean_lang = "Clean-param: lang /" in txt
    has_ru_sitemap = f"Sitemap: {ORIGIN}/sitemap-ru.xml" in txt
    result["robots_txt_yandex"] = {
        "has_yandex_user_agent": "User-agent: Yandex" in txt,
        "missing_foreign_disallows": missing_disallows,
        "has_clean_param_utm": has_clean_utm,
        "has_clean_param_lang": has_clean_lang,
        "declares_sitemap_ru": has_ru_sitemap,
    }
    if "User-agent: Yandex" not in txt or missing_disallows or not has_clean_utm or not has_clean_lang or not has_ru_sitemap:
        result["issues"].append("robots.txt Yandex directives or Clean-param rules incomplete")

    # Check live sitemap-ru.xml (Russian routes excluding English root '/')
    expected_ru = {
        u for u in sitemap_urls
        if u.startswith(ORIGIN + "/")
        and urlsplit(u).path != "/"
        and not FOREIGN_LOCALE_RE.match(urlsplit(u).path)
    }
    st, body, hdrs, ms, err = http_get(f"{ORIGIN}/sitemap-ru.xml")
    if st != 200 or err:
        result["sitemap_ru_xml"] = {"status": st, "valid_xml": False, "error": err}
        result["issues"].append(f"sitemap-ru.xml unreachable: HTTP {st}")
    else:
        try:
            root = ET.fromstring(body.decode("utf-8"))
            ru_urls = [
                (n.findtext(f"{SITEMAP_NS}loc") or "").strip()
                for n in root.findall(f"{SITEMAP_NS}url")
            ]
            foreign_leaks = [u for u in ru_urls if FOREIGN_LOCALE_RE.match(urlsplit(u).path)]
            missing_ru = sorted(expected_ru - set(ru_urls))
            unexpected_ru = sorted(set(ru_urls) - expected_ru)
            result["sitemap_ru_xml"] = {
                "status": st,
                "response_ms": round(ms, 1),
                "valid_xml": True,
                "url_count": len(ru_urls),
                "unique_url_count": len(set(ru_urls)),
                "expected_ru_count": len(expected_ru),
                "foreign_locale_leaks": len(foreign_leaks),
                "missing_ru_urls": missing_ru[:5],
                "unexpected_ru_urls": unexpected_ru[:5],
                "exact_103_ru_match": len(ru_urls) == len(expected_ru) and not missing_ru and not unexpected_ru,
            }
            if missing_ru or unexpected_ru or foreign_leaks or len(ru_urls) != len(set(ru_urls)):
                result["issues"].append(
                    f"sitemap-ru.xml mismatch: count={len(ru_urls)}, missing={len(missing_ru)}, unexpected={len(unexpected_ru)}"
                )
        except ET.ParseError as exc:
            result["sitemap_ru_xml"] = {"status": st, "valid_xml": False, "error": str(exc)}
            result["issues"].append(f"sitemap-ru.xml XML parse error: {exc}")

    # Check yandex-indexnow-state.json
    state_path = TOOLS_DIR / "yandex-indexnow-state.json"
    build_state_path = TOOLS_DIR / "search-build-state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        build_state = json.loads(build_state_path.read_text(encoding="utf-8")) if build_state_path.exists() else {}
        ack = state.get("acknowledged", {})
        pending = state.get("pending", {})
        legacy = state.get("legacy_shared", {})
        ack_current = sum(
            1 for u in expected_ru
            if ack.get(u) == build_state.get(urlsplit(u).path, {}).get("sha256")
        )
        result["yandex_indexnow_state"] = {
            "schema_version": state.get("schema_version"),
            "acknowledged_count": len(ack),
            "pending_count": len(pending),
            "legacy_shared_count": len(legacy),
            "acknowledged_matching_current_build": ack_current,
            "expected_ru_urls": len(expected_ru),
        }
        if pending:
            result["issues"].append(f"Yandex IndexNow has {len(pending)} pending unacknowledged RU URLs")
    else:
        result["yandex_indexnow_state"] = {"present": False}
        result["issues"].append("Missing tools/yandex-indexnow-state.json")

    # Optional Yandex Webmaster API v4 check via .local/yandex-oauth-token.dpapi
    yandex_token = load_credential("yandex")
    if not yandex_token:
        result["yandex_webmaster_api"] = {
            "configured": False,
            "status": "skipped (no .local/yandex-oauth-token.dpapi configured; Yandex IndexNow + sitemap-ru.xml active)",
        }
    else:
        headers = {"Authorization": f"OAuth {yandex_token}"}
        st_u, body_u, _, _, err_u = http_get("https://api.webmaster.yandex.net/v4/user", headers=headers)
        api_info = {"configured": True, "user_http_status": st_u}
        if st_u == 200:
            user_data = json.loads(body_u.decode("utf-8"))
            user_id = user_data.get("user_id")
            api_info["user_id"] = user_id
            if user_id:
                st_h, body_h, _, _, _ = http_get(
                    f"https://api.webmaster.yandex.net/v4/user/{user_id}/hosts", headers=headers
                )
                api_info["hosts_http_status"] = st_h
                if st_h == 200:
                    hosts = json.loads(body_h.decode("utf-8")).get("hosts", [])
                    api_info["hosts"] = [
                        {"host_id": h.get("host_id"), "verified": h.get("verified")}
                        for h in hosts
                    ]
        else:
            api_info["error"] = err_u or body_u.decode("utf-8", errors="replace")[:200]
            result["issues"].append(f"Yandex Webmaster API /v4/user returned HTTP {st_u}")
        result["yandex_webmaster_api"] = api_info

    return result


def audit_live_seo(sitemap_urls: list[str], max_workers: int = 24) -> dict:
    """Audit all live URLs in sitemap.xml across all 6 languages (`ru`, `en`, `es`, `pt`, `fr`, `he`)."""
    pages_data: dict[str, dict] = {}
    problems: dict[str, list[str]] = collections.defaultdict(list)
    by_lang_times: dict[str, list[float]] = collections.defaultdict(list)
    by_lang_counts: dict[str, int] = collections.defaultdict(int)
    internal_assets_to_check: set[str] = set()
    internal_links_to_check: set[str] = set()

    def classify_lang(url: str) -> str:
        path = urlsplit(url).path
        m = re.match(r"^/(en|es|pt|fr|he)(/|$)", path)
        if m:
            return m.group(1)
        return "en" if path == "/" else "ru"

    def fetch_and_parse(url: str):
        st, body, hdrs, ms, err = http_get(url)
        return url, st, body, hdrs, ms, err

    start_all = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fetch_and_parse, u) for u in sitemap_urls]
        for fut in as_completed(futures):
            url, st, body, hdrs, ms, err = fut.result()
            lang = classify_lang(url)
            by_lang_counts[lang] += 1
            by_lang_times[lang].append(ms)
            if st != 200 or err:
                problems["http_error"].append(f"{url} (HTTP {st}, {err})")
                continue
            text = body.decode("utf-8", errors="replace")
            inspector = LiveHTMLInspector()
            inspector.feed(text)
            path = urlsplit(url).path
            is_home = path == "/"

            # Check Cache-Control header
            cc = hdrs.get("cache-control", "")
            if "must-revalidate" not in cc:
                problems["cache_control"].append(f"{url} -> {cc!r}")

            # Check HTML lang & dir
            expected_lang_tag = HTML_LANG_TAGS.get(lang, lang)
            if inspector.html_lang != expected_lang_tag:
                problems["html_lang"].append(
                    f"{url} expected lang={expected_lang_tag}, got {inspector.html_lang}"
                )
            expected_dir = "rtl" if lang == "he" else "ltr"
            if inspector.html_dir != expected_dir:
                problems["html_dir"].append(f"{url} expected dir={expected_dir}, got {inspector.html_dir}")

            # Check canonical
            if inspector.canonical != url:
                problems["canonical_mismatch"].append(f"{url} -> {inspector.canonical}")

            # Check H1 count
            if inspector.h1_count != 1:
                problems["h1_count"].append(f"{url} (h1={inspector.h1_count})")

            # Check title & description bounds
            if not inspector.title or len(inspector.title) > 70:
                problems["title_bounds"].append(f"{url} ({len(inspector.title)} chars)")
            if not inspector.description or not (50 <= len(inspector.description) <= 170):
                desc_len = len(inspector.description or "")
                problems["description_bounds"].append(f"{url} ({desc_len} chars)")

            # Check robots meta
            if "noindex" in inspector.robots.lower():
                problems["noindex_in_sitemap"].append(url)

            # Check forbidden tokens
            for tok in FORBIDDEN_SCHEMA_TOKENS:
                if tok in text:
                    problems[f"forbidden_token_{tok}"].append(url)

            # Check JSON-LD validity (required on root/catalog/locale homes and all product pages)
            requires_jsonld = is_home or path in ("/catalog/", "/en/", "/es/", "/pt/", "/fr/", "/he/") or "/products/" in path
            if requires_jsonld and not inspector.jsonld_raw:
                problems["missing_jsonld"].append(url)
            for block in inspector.jsonld_raw:
                try:
                    parsed_ld = json.loads(block)
                    if not isinstance(parsed_ld, dict) or "schema.org" not in str(parsed_ld.get("@context", "")):
                        problems["invalid_jsonld_context"].append(url)
                except ValueError as exc:
                    problems["invalid_jsonld_syntax"].append(f"{url}: {exc}")

            # Check hreflang presence: standalone /en/ catalog has none; root '/' and all other pages match the cluster
            keys = set(inspector.hreflang.keys())
            if path == "/en/":
                if keys:
                    problems["standalone_en_has_hreflang"].append(f"{url} has {sorted(keys)}")
            else:
                ru_only_journal = path.startswith("/journal/") and keys == {"ru", "ru-RU", "x-default"}
                if keys != EXPECTED_HREFLANG_KEYS and not ru_only_journal:
                    problems["hreflang_incomplete"].append(
                        f"{url} has {sorted(keys)}"
                    )

            # Collect internal links & assets
            for asset in inspector.assets:
                ap = urlsplit(asset)
                if not ap.scheme and ap.path.startswith("/"):
                    internal_assets_to_check.add(ORIGIN + ap.path)
                elif ap.netloc == "www.fluxixo.shop":
                    internal_assets_to_check.add(ORIGIN + ap.path)

            for link in inspector.links:
                lp = urlsplit(link)
                if lp.scheme in ("mailto", "tel", "javascript"):
                    continue
                if lp.scheme in ("http", "https") and lp.netloc != "www.fluxixo.shop":
                    continue
                if lp.path:
                    target_path = lp.path if lp.path.startswith("/") else "/" + lp.path
                    internal_links_to_check.add(ORIGIN + target_path)

            pages_data[url] = {
                "lang": lang,
                "title": inspector.title,
                "description": inspector.description,
                "hreflang": inspector.hreflang,
                "has_cf_beacon": inspector.has_cf_beacon,
            }

    # Verify reciprocal hreflang links across all audited pages
    for url, pdata in pages_data.items():
        for hlang, target_url in pdata["hreflang"].items():
            target_page = pages_data.get(target_url)
            if target_page is None:
                problems["hreflang_target_missing"].append(f"{url} [{hlang}] -> {target_url}")
            elif url not in target_page["hreflang"].values():
                problems["hreflang_not_reciprocal"].append(f"{url} [{hlang}] -> {target_url}")

    # Check title and description uniqueness across all pages
    for field in ("title", "description"):
        counts = collections.Counter(p[field] for p in pages_data.values() if p.get(field))
        dups = [val for val, cnt in counts.items() if cnt > 1]
        if dups:
            problems[f"duplicate_{field}"].extend(dups[:5])

    # Verify internal links not already in pages_data
    unchecked_links = sorted(internal_links_to_check - set(pages_data.keys()))
    # Sample/verify all unique internal assets & non-sitemap internal links
    targets_to_probe = unchecked_links + sorted(internal_assets_to_check)

    def probe_asset(target_url: str):
        st, _, hdrs, _, err = http_get(target_url, method="HEAD")
        if st in (403, 405) or err:
            st, _, hdrs, _, err = http_get(target_url, method="GET")
        return target_url, st, hdrs, err

    asset_headers_sample = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for target_url, st, hdrs, err in pool.map(probe_asset, targets_to_probe):
            if st != 200 or err:
                problems["broken_internal_link_or_asset"].append(f"{target_url} (HTTP {st})")
            elif re.search(r"\.[0-9a-f]{12}\.(js|css|svg)$", target_url) and not asset_headers_sample:
                asset_headers_sample = {
                    "asset": target_url,
                    "cache_control": hdrs.get("cache-control"),
                }

    total_elapsed_s = round(time.perf_counter() - start_all, 2)

    locale_summary = {}
    for lang in LANGUAGES:
        times = by_lang_times.get(lang, [])
        locale_summary[lang] = {
            "pages_audited": by_lang_counts.get(lang, 0),
            "avg_response_ms": round(statistics.mean(times), 1) if times else 0.0,
            "median_response_ms": round(statistics.median(times), 1) if times else 0.0,
            "p95_response_ms": round(sorted(times)[int(0.95 * (len(times) - 1))], 1) if times else 0.0,
        }

    return {
        "total_sitemap_urls": len(sitemap_urls),
        "pages_successfully_audited": len(pages_data),
        "unique_internal_assets_verified": len(internal_assets_to_check),
        "extra_internal_links_verified": len(unchecked_links),
        "hashed_asset_cache_sample": asset_headers_sample,
        "audit_duration_seconds": total_elapsed_s,
        "by_language": locale_summary,
        "problems_count": sum(len(v) for v in problems.values()),
        "problems": dict(problems),
    }


def print_human_summary(report: dict) -> None:
    print("=" * 78)
    print("FLUXIXO SEARCH CONNECTIONS & LIVE TECHNICAL SEO AUDIT")
    print("=" * 78)

    print("\n[1] DPAPI Credential Store (.local/)")
    for k, info in report["credentials"].items():
        status = "ENCRYPTED & READY" if info["decrypted"] else ("MISSING (Optional)" if k != "cloudflare" else "MISSING (Required)")
        print(f"  - {info['file']:28s} : {status} ({info['label']})")

    cf = report["cloudflare"]
    print("\n[2] Cloudflare API & Edge Delivery")
    print(f"  - Token Status                 : {cf['token_status']}")
    if cf["project"]:
        print(f"  - Pages Project                : {cf['project']['name']} ({cf['project']['subdomain']})")
    if cf["latest_deployment"]:
        ld = cf["latest_deployment"]
        print(f"  - Latest Deployment            : {ld['id']} | {ld['stage_name']}={ld['stage_status']} | {ld['created_on']}")
    print(f"  - Custom Domains               : {', '.join(d['name'] + '=' + str(d['status']) for d in cf['domains'])}")
    ar = cf["apex_redirect"]
    print(f"  - Apex Redirect (fluxixo.shop) : HTTP {ar.get('status')} -> {ar.get('location')} ({ar.get('response_ms')} ms)")
    sh = cf["ssl_and_headers"]
    print(f"  - Live Edge Headers            : HTTP {sh.get('status')} | CF-Ray={sh.get('cf_ray')} | Cache-Control={sh.get('cache_control')}")
    print(f"  - Security Headers             : X-Content-Type-Options={sh.get('x_content_type_options')} | CSP={sh.get('content_security_policy_present')}")
    print(f"  - Cloudflare Web Analytics     : Beacon injected={cf['web_analytics_beacon'].get('injected_on_root')}")

    gg = report["google"]
    print("\n[3] Google Search Integration")
    print(f"  - google-site-verification     : Root '/'={gg['verification_meta']['root_verified']} ({gg['verification_meta']['expected']})")
    sm = gg["sitemap_xml"]
    print(f"  - Live sitemap.xml             : HTTP {sm.get('status')} | {sm.get('url_count')} URLs ({sm.get('unique_url_count')} unique) | Valid XML={sm.get('valid_xml')}")
    print(f"  - Sitemap Breakdown by Locale  : {sm.get('counts_by_locale')}")
    print(f"  - robots.txt (*)               : Wildcard Allow={gg['robots_txt']['wildcard_allow_root']} | Sitemap Declared={gg['robots_txt']['declares_sitemap_xml']}")
    ws = gg["rss_and_websub"]
    print(f"  - RSS & Google WebSub Hub      : rss.xml HTTP {ws['rss_status']} ({ws['rss_items']} items) | WebSub Hub HTTP {ws['websub_hub_status']} ({ws['websub_hub_ms']} ms)")
    print(f"  - Search Console API           : {gg['gsc_api'].get('status', gg['gsc_api'])}")

    bg = report["bing"]
    print("\n[4] Microsoft Bing & IndexNow Integration")
    print(f"  - msvalidate.01 Meta Tag       : Root '/'={bg['verification_meta']['present_on_root']} ({bg['verification_meta']['expected']})")
    print(f"  - Live BingSiteAuth.xml        : HTTP {bg['bing_site_auth_xml']['status']} | Valid={bg['bing_site_auth_xml']['valid']}")
    in_files = ", ".join(f"{p}={v['matches_key']}" for p, v in bg["indexnow_key_files"].items())
    print(f"  - Live IndexNow Key Files      : {in_files}")
    led = bg["indexnow_submission_ledger"]
    if led.get("sitemap_urls_total"):
        print(f"  - indexnow-submitted.json      : {led['sitemap_urls_covered']}/{led['sitemap_urls_total']} URLs covered ({led['coverage_pct']}%), {led['matching_current_build_sha256']} matching current build SHA256")
    print(f"  - Bing Webmaster API           : {bg['bing_webmaster_api'].get('status', bg['bing_webmaster_api'])}")

    yx = report["yandex"]
    print("\n[5] Yandex Webmaster Integration")
    print(f"  - yandex-verification Meta Tag : Root '/'={yx['verification_meta']['present_on_root']} ({yx['verification_meta']['expected']})")
    ry = yx["robots_txt_yandex"]
    print(f"  - robots.txt (Yandex)          : User-agent={ry['has_yandex_user_agent']} | Clean-param UTM={ry['has_clean_param_utm']} | Clean-param lang={ry['has_clean_param_lang']} | Foreign Disallows OK={len(ry['missing_foreign_disallows']) == 0}")
    sru = yx["sitemap_ru_xml"]
    print(f"  - Live sitemap-ru.xml          : HTTP {sru.get('status')} | {sru.get('url_count')} RU URLs (expected {sru.get('expected_ru_count')}) | Exact Match={sru.get('exact_103_ru_match')} | Foreign Leaks={sru.get('foreign_locale_leaks')}")
    ys = yx["yandex_indexnow_state"]
    if "acknowledged_count" in ys:
        print(f"  - yandex-indexnow-state.json   : Acknowledged={ys['acknowledged_count']} | Pending={ys['pending_count']} | Matching Current Build={ys['acknowledged_matching_current_build']}/{ys['expected_ru_urls']}")
    print(f"  - Yandex Webmaster API v4      : {yx['yandex_webmaster_api'].get('status', yx['yandex_webmaster_api'])}")

    seo = report["live_seo_audit"]
    print("\n[6] Live Technical SEO, Hreflang & Schema Audit (6 Languages)")
    print(f"  - Sitemap Pages Audited        : {seo['pages_successfully_audited']}/{seo['total_sitemap_urls']} in {seo['audit_duration_seconds']}s")
    print(f"  - Internal Assets Verified     : {seo['unique_internal_assets_verified']} assets + {seo['extra_internal_links_verified']} non-sitemap routes")
    if seo.get("hashed_asset_cache_sample"):
        hs = seo["hashed_asset_cache_sample"]
        print(f"  - Immutable Asset Cache Header : {hs['asset']} -> {hs['cache_control']}")
    print("  - Per-Language Response Times  :")
    for lang, stats in seo["by_language"].items():
        print(f"      [{lang.upper()}] {stats['pages_audited']:3d} pages | avg={stats['avg_response_ms']:6.1f} ms | median={stats['median_response_ms']:6.1f} ms | p95={stats['p95_response_ms']:6.1f} ms")
    print(f"  - Total SEO/Schema/Link Issues : {seo['problems_count']}")
    if seo["problems"]:
        for k, items in seo["problems"].items():
            print(f"      ! {k}: {len(items)} e.g. {items[:3]}")

    all_issues = (
        cf["issues"] + gg["issues"] + bg["issues"] + yx["issues"]
        + [f"SEO:{k}={len(v)}" for k, v in seo["problems"].items()]
    )
    print("\n" + "=" * 78)
    if all_issues:
        print(f"OVERALL STATUS: WARNINGS/ISSUES FOUND ({len(all_issues)})")
        for issue in all_issues:
            print(f"  * {issue}")
    else:
        print("OVERALL STATUS: ALL CLOUDFLARE, SEARCH ENGINE & LIVE SEO CHECKS PASSED")
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output full report as JSON")
    parser.add_argument("--save-out", type=Path, help="Save JSON report to file path")
    parser.add_argument("--set-credential", nargs=2, metavar=("NAME", "SECRET"), help="Encrypt and save a credential into .local/<name>.dpapi")
    parser.add_argument("--set-credential-file", nargs=2, metavar=("NAME", "FILEPATH"), help="Encrypt and save a credential file into .local/<name>.dpapi")
    args = parser.parse_args()

    if args.set_credential:
        name, val = args.set_credential
        saved = save_credential(name, val)
        print(f"Saved DPAPI-encrypted credential to {saved}")
        return 0

    if args.set_credential_file:
        name, fpath = args.set_credential_file
        saved = save_credential(name, Path(fpath).read_text(encoding="utf-8"))
        print(f"Saved DPAPI-encrypted credential from file to {saved}")
        return 0

    creds = check_credentials_store()
    cf = check_cloudflare()
    gg = check_google()
    sitemap_urls = gg.get("sitemap_xml", {}).get("urls", [])
    bg = check_bing(sitemap_urls)
    yx = check_yandex(sitemap_urls)
    seo = audit_live_seo(sitemap_urls)

    # Strip raw URL list from sitemap_xml summary before serializing
    if "urls" in gg.get("sitemap_xml", {}):
        del gg["sitemap_xml"]["urls"]

    report = {
        "checked_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "origin": ORIGIN,
        "credentials": creds,
        "cloudflare": cf,
        "google": gg,
        "bing": bg,
        "yandex": yx,
        "live_seo_audit": seo,
    }

    if args.save_out:
        args.save_out.parent.mkdir(parents=True, exist_ok=True)
        args.save_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human_summary(report)

    has_failures = bool(cf["issues"] or gg["issues"] or bg["issues"] or yx["issues"] or seo["problems_count"])
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
