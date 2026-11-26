"""Conservative six-language text-only refresh for existing FLUXIXO product pages.

Each accepted product is identified using the signed official AliExpress DETAIL API,
written only after source-claim, language, internal-overlap and independent
six-locale public-snippet checks. No images, links, prices or site logic change.
A failed check leaves the published card untouched.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "fluxixo_site"
TOOLS = SITE / "tools"
sys.path.insert(0, str(TOOLS))

import ai_seo
import check_texts
import copy_originality
from fluxixo_ai.gemini_client import GeminiDeferred
from fluxixo_ai.policy import DETAIL, normalize_product
from fluxixo_ai.search import AliClient, ApiError, _rows

CATALOG_PATH = SITE / "dist/js/catalog.js"
I18N_PATH = TOOLS / "i18n_data.json"
FIXES_PATH = TOOLS / "text_fixes.json"
STATE_PATH = ROOT / "data/fluxixo_existing_copy_state.json"
LANGS = ("ru", "en", "pt", "es", "fr", "he")


def read_catalog():
    raw = CATALOG_PATH.read_text(encoding="utf-8")
    prefix, data = raw.split("=", 1)
    return prefix, json.loads(data.strip().rstrip(";"))


def save_catalog(prefix, catalog):
    CATALOG_PATH.write_text(prefix + "= " + json.dumps(catalog, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_state():
    if not STATE_PATH.exists():
        return {"version": 1, "products": {}}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("products"), dict):
        raise ValueError("copy_refresh_state_invalid")
    return state


def checkpoint(state):
    """Persist draft reservations before calls; fail closed if the GitHub push fails."""
    write_json(STATE_PATH, state)
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("copy_checkpoint_requires_main")
    subprocess.run(["git", "add", "-f", "--", "data/fluxixo_existing_copy_state.json"], cwd=ROOT, check=True)
    dirty = subprocess.run(["git", "diff", "--cached", "--quiet", "--", "data/fluxixo_existing_copy_state.json"], cwd=ROOT).returncode
    if dirty:
        subprocess.run(["git", "commit", "--only", "-m", "chore(fluxixo): checkpoint existing-copy validation [skip ci]", "--", "data/fluxixo_existing_copy_state.json"], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)


def source_title(client, product):
    pid = str(product.get("sourceProductId") or "")
    if not re.fullmatch(r"[1-9][0-9]{0,31}", pid):
        raise ValueError("product_id_not_verified")
    expected = "https://www.aliexpress.com/item/" + pid + ".html"
    if product.get("sourceDetailUrl", expected) != expected:
        raise ValueError("source_link_mismatch")
    response = client(DETAIL, {
        "product_ids": pid, "country": "US", "target_currency": "USD",
        "target_language": "EN", "tracking_id": "default",
    })
    rows = _rows(response, DETAIL)
    matches = [row for row in rows if isinstance(row, dict) and str(row.get("product_id")) == pid]
    if len(matches) != 1:
        raise ValueError("api_detail_missing_or_ambiguous")
    verified = normalize_product(matches[0], "US", DETAIL, datetime.now(timezone.utc).isoformat())
    if verified["product_id"] != pid or verified["detail_url"] != expected:
        raise ValueError("api_identity_mismatch")
    title = verified["title"].strip()
    if len(title) < 8:
        raise ValueError("api_title_too_short")
    return title


def current_bundle(item, i18n):
    pid = item["id"]
    localizations = i18n["products"].get(pid, {})
    bundle = {"ru": {field: item[field] for field in ("name", "headline", "description")}}
    for language in LANGS[1:]:
        loc = localizations.get(language)
        if not isinstance(loc, dict):
            raise ValueError("translation_missing_" + language)
        bundle[language] = {field: loc[field] for field in ("name", "headline", "description")}
    return bundle


def seller_identity_compatible(title, bundle):
    """An ID match alone is insufficient if a seller repurposed a listing."""
    original = str(bundle["en"]["name"])
    old = set(copy_originality.tokenize_meaningful(original, "en"))
    new = set(copy_originality.tokenize_meaningful(title, "en"))
    meaningful = {x for x in old & new if len(x) >= 4 and not x.isdigit()}
    # Conservative requirement: at least one meaningful English product word.
    return bool(meaningful)


def remove_old_text_overrides(fixes, pid):
    for language in LANGS[1:]:
        rows = fixes.get(language, {})
        if not isinstance(rows, dict):
            continue
        for prefix in list(rows):
            if pid == prefix or pid.startswith(prefix + "-"):
                del rows[prefix]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-products", type=int, default=2)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--force-curated", action="store_true",
                        help="Allow rewriting items that already have curated 6-language editorial copy.")
    args = parser.parse_args()
    if not 1 <= args.max_products <= 4:
        parser.error("--max-products must be 1..4")
    if os.environ.get("FLUXIXO_TEXT_PROVIDER") != "gemini":
        raise SystemExit("Existing-copy rewrite requires the fact-reviewing Gemini provider")
    if os.environ.get("FLUXIXO_WEB_CHECK") != "1" or not ai_seo.free_web_check_enabled():
        raise SystemExit("External originality search must be enabled")
    if not os.environ.get("ALI_APP_KEY") or not os.environ.get("ALI_APP_SECRET"):
        raise SystemExit("AliExpress credentials unavailable")
    if not os.environ.get("FLUXIXO_TEXT_GEMINI_API_KEY"):
        raise SystemExit("Dedicated text review credential unavailable")
    prefix, catalog = read_catalog()
    i18n = json.loads(I18N_PATH.read_text(encoding="utf-8"))
    fixes = json.loads(FIXES_PATH.read_text(encoding="utf-8"))
    editorial_path = I18N_PATH.parent / "product_editorial.json"
    curated_ids = set(json.loads(editorial_path.read_text(encoding="utf-8")).keys()) if editorial_path.exists() else set()
    state = load_state()
    client = AliClient()
    report = {"attempted": [], "updated": [], "deferred": [], "already_done": 0}
    processed = 0
    # Retry unsuccessful items in later runs; a bounded selection avoids quota storms.
    for item in catalog["products"]:
        if item.get("demo"):
            continue
        pid = item.get("id")
        history = state["products"].setdefault(pid, {})
        if history.get("completed") or (pid in curated_ids and not args.force_curated):
            report["already_done"] += 1
            continue
        # Do not retry the same missing/incorrect seller source every day.
        # Scan past blocked items and continue through the rest of the catalog.
        last_attempt = history.get("last_attempt")
        if isinstance(last_attempt, str):
            try:
                if datetime.now(timezone.utc) - datetime.fromisoformat(last_attempt) < timedelta(days=7):
                    continue
            except ValueError:
                pass
        if processed >= args.max_products:
            break
        processed += 1
        history["last_attempt"] = datetime.now(timezone.utc).isoformat()
        try:
            baseline = current_bundle(item, i18n)
            title = source_title(client, item)
            if not seller_identity_compatible(title, baseline):
                raise ValueError("seller_title_does_not_match_existing_product")
            corpus = copy_originality.build_catalog_copy_corpus(
                catalog["products"], i18n, exclude_ids={pid},
            )
            journal = history.setdefault("copy_journal", {})
            product_context = {
                "source_title": title, "category": item.get("category", ""),
                "market": "RU,US,BR,MX,FR,IL",
            }
            proposal, provider = ai_seo.enrich_product_copy(
                product_context, baseline, catalog_corpus=corpus, copy_state=journal,
                checkpoint=lambda: checkpoint(state),
            )
            problems = ai_seo.validate_product_bundle(
                proposal, source_text=title, source_title=title, catalog_corpus=corpus,
            )
            if problems:
                raise ValueError("final_bundle_validation_failed")
            originality_receipt = {}
            problems = ai_seo.external_copy_problems(proposal, receipt=originality_receipt)
            if problems or set(originality_receipt) != set(LANGS):
                raise ValueError("external_originality_not_confirmed")
            proposed_item = {**item, **proposal["ru"], "details": proposal["ru"]["description"]}
            issues = check_texts.lint_product_bundle(pid, proposed_item,
                {lang: proposal[lang] for lang in LANGS[1:]}, i18n)
            if issues:
                raise ValueError("localization_lint_failed")
            # Only user-facing copy changes. Existing product identity, URLs,
            # media, pricing and auxiliary catalog attributes remain untouched.
            item.update({field: proposal["ru"][field] for field in ("name", "headline", "description")})
            item["details"] = proposal["ru"]["description"]
            for lang in LANGS[1:]:
                i18n["products"][pid][lang].update({
                    field: proposal[lang][field] for field in ("name", "headline", "description")
                })
            remove_old_text_overrides(fixes, pid)
            history["completed"] = datetime.now(timezone.utc).isoformat()
            history["provider"] = provider
            history["source_version"] = __import__("fluxixo_ai.copy_revisions", fromlist=["copy_source_version"]).copy_source_version(title)
            history["originality_sha256"] = {lang: originality_receipt[lang]["sha256"] for lang in LANGS}
            report["updated"].append(pid)
        except (ApiError, GeminiDeferred, ValueError, KeyError, TypeError) as exc:
            reason = getattr(exc, "code", None) or str(exc)
            reason = re.sub(r"[^a-zA-Z0-9_:-]", "_", str(reason))[:100]
            report["deferred"].append({"id": pid, "reason": reason})
            history["last_deferred"] = reason
        report["attempted"].append(pid)
        # Accept copy only once in memory; commit and publish occur after full
        # site build/verification in the protected GitHub Actions workflow.
    if report["updated"]:
        save_catalog(prefix, catalog)
        write_json(I18N_PATH, i18n)
        write_json(FIXES_PATH, fixes)
    write_json(STATE_PATH, state)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.report, report)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("changed=" + ("true" if report["updated"] else "false") + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "attempted"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
