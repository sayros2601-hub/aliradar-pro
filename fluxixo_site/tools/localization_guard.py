#!/usr/bin/env python3
"""Read-only FLUXIXO content guard and conservative staged translation merger.

No network, deployment, source rewriting, credentials or third-party packages.
This validates structure/coverage, NOT native fluency or product specifications.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

LOCALES = ('en', 'pt', 'es', 'fr', 'he')
SAFE_ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
CYRILLIC = re.compile(r'[\u0400-\u04ff]')
MIXED_HEBREW_ARABIC = re.compile(r'[\u0590-\u05ff][\u0600-\u06ff]|[\u0600-\u06ff][\u0590-\u05ff]')


def load_json(text: str) -> Any:
    """Reject duplicate keys instead of silently discarding editorial content."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f'Invalid JSON number: {value}')))


def read_text(path: Path) -> str:
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError(f'Refusing oversized input: {path}')
    return path.read_text(encoding='utf-8-sig')


def parse_catalog(text: str) -> dict:
    match = re.fullmatch(r'\s*(?:/\*.*?\*/\s*)?window\.MIRA_CATALOG\s*=\s*(\{.*\})\s*;?\s*', text, re.S)
    if not match:
        raise ValueError('Unsupported catalog format: expected a JSON-only MIRA_CATALOG assignment')
    value = load_json(match.group(1))
    if not isinstance(value, dict):
        raise ValueError('Catalog must be a JSON object')
    return value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def inspect_catalog(catalog: Any, data: Any, assets_root: Path | None = None) -> list[dict]:
    """Basic readiness only. Deliberately does not certify language quality."""
    issues: list[dict] = []
    def report(code, path, message, severity='error'):
        issues.append({'severity': severity, 'code': code, 'path': path, 'message': message})
    if not isinstance(catalog, dict) or not isinstance(catalog.get('products'), list):
        report('invalid_catalog', 'products', 'Expected a products array')
        return issues
    if not isinstance(data, dict):
        report('invalid_localization', 'i18n_data', 'Expected an object')
        return issues
    tr = data.get('products')
    if not isinstance(tr, dict):
        report('invalid_translations', 'products', 'Expected translations indexed by exact product ID')
        tr = {}
    ui = data.get('ui', {})
    if not isinstance(ui, dict):
        report('invalid_ui', 'ui', 'Expected an object'); ui = {}
    ru_ui = ui.get('ru', {})
    if not isinstance(ru_ui, dict) or not ru_ui:
        report('invalid_ui', 'ui.ru', 'Russian reference UI must be a nonempty object'); ru_ui = {}
    for lang in LOCALES:
        target = ui.get(lang, {})
        if not isinstance(target, dict):
            report('invalid_ui', f'ui.{lang}', 'Expected an object'); target = {}
        for key in ru_ui:
            if not nonempty(target.get(key)):
                report('missing_ui_key', f'ui.{lang}.{key}', 'Missing or empty UI string')
    cats = data.get('cats', {})
    if not isinstance(cats, dict):
        report('invalid_categories', 'cats', 'Expected an object'); cats = {}
    seen: set[str] = set()
    for idx, product in enumerate(catalog['products']):
        path = f'catalog.products[{idx}]'
        if not isinstance(product, dict):
            report('invalid_product', path, 'Expected an object'); continue
        pid = product.get('id')
        if not isinstance(pid, str) or not SAFE_ID.fullmatch(pid):
            report('invalid_product_id', path, 'ID is not a safe stable slug'); continue
        if pid in seen:
            report('duplicate_product_id', pid, 'ID occurs more than once')
        seen.add(pid)
        if product.get('demo'):
            continue
        for field in ('name', 'description'):
            if not nonempty(product.get(field)):
                report('invalid_source_field', f'{pid}.{field}', 'Empty source field')
        per_product = tr.get(pid, {})
        if not isinstance(per_product, dict):
            per_product = {}
        for lang in LOCALES:
            fields = per_product.get(lang)
            prefix = f'products.{pid}.{lang}'
            if not isinstance(fields, dict) or not fields:
                report('missing_translation', prefix, 'Missing target-language product')
                continue
            for key in ('name', 'description'):
                if not nonempty(fields.get(key)):
                    report('invalid_'+key, prefix+'.'+key, 'Expected nonempty text')
            headline = fields.get('headline')
            if not isinstance(headline, list) or not headline or not all(nonempty(v) for v in headline):
                report('invalid_headline', prefix+'.headline', 'Expected a nonempty list of nonempty strings')
            texts = [fields.get('name'), fields.get('description')]
            texts += headline if isinstance(headline, list) else []
            for text in filter(lambda t: isinstance(t, str), texts):
                if CYRILLIC.search(text):
                    report('russian_in_translation', prefix, 'Cyrillic in a non-Russian core field: review before release')
                if lang == 'he' and MIXED_HEBREW_ARABIC.search(text):
                    report('mixed_hebrew_arabic_word', prefix, 'Hebrew and Arabic characters joined inside a word')
            category = product.get('category')
            translated_cat = cats.get(category, {}) if isinstance(category, str) else {}
            if not isinstance(translated_cat, dict) or not nonempty(translated_cat.get(lang)):
                report('missing_category_translation', f'cats.{category}.{lang}', 'Missing category text')
        if assets_root is not None:
            root = Path(assets_root).resolve()
            for field in ('image', 'original'):
                value = product.get(field)
                if field == 'original' and not value:
                    report('no_original_photo', pid, 'No original seller photo supplied', 'warning'); continue
                if not isinstance(value, str) or not value or '\\' in value:
                    report('unsafe_asset_path', f'{pid}.{field}', 'Invalid local asset path'); continue
                relative = PurePosixPath(value)
                if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'assets':
                    report('unsafe_asset_path', f'{pid}.{field}', 'Asset must be a relative path under assets/'); continue
                resolved = (root / value).resolve()
                if not resolved.is_relative_to(root):
                    report('unsafe_asset_path', f'{pid}.{field}', 'Asset symlink escapes the site root'); continue
                if not resolved.is_file() or resolved.stat().st_size == 0:
                    report('missing_asset', f'{pid}.{field}', 'Missing or empty image file')
    for pid in tr:
        if pid not in seen:
            report('orphan_translation', f'products.{pid}', 'Retained: no matching current catalog ID; never remap by numeric prefix', 'warning')
    return issues


def prepare_patch(catalog: dict, original: dict, patch: dict) -> tuple[dict, dict]:
    """Pure transform: exact-ID/source guards, no silent conflict resolution."""
    products = catalog.get('products')
    if not isinstance(products, list) or any(not isinstance(p, dict) for p in products):
        raise ValueError('Catalog products must be objects')
    indexed = {}
    for p in products:
        pid = p.get('id')
        if not isinstance(pid, str) or not SAFE_ID.fullmatch(pid) or pid in indexed:
            raise ValueError('Invalid or duplicate catalog ID')
        indexed[pid] = p
    if not isinstance(original, dict) or not isinstance(original.get('products'), dict):
        raise ValueError('Translation products object required')
    merged = copy.deepcopy(original)
    changed = 0
    for pid, entry in patch['products'].items():
        if pid not in indexed:
            raise ValueError(f'{pid}: not in catalog; no automatic ID remapping allowed')
        for key, value in entry['expected_source'].items():
            if indexed[pid].get(key) != value:
                raise ValueError(f'Source changed: {pid}.{key}')
        target = merged['products'].setdefault(pid, {})
        if not isinstance(target, dict):
            raise ValueError(f'Conflict: malformed translation record {pid}')
        if set(entry['translations']) != set(LOCALES):
            raise ValueError(f'Patch must cover exactly five target locales: {pid}')
        for lang, values in entry['translations'].items():
            current = target.setdefault(lang, {})
            if not isinstance(current, dict):
                raise ValueError(f'Conflict: malformed locale {pid}.{lang}')
            for key, value in values.items():
                if current.get(key) == value:
                    continue
                if current.get(key) not in (None, '', []):
                    raise ValueError(f'Conflict: existing editorial value {pid}.{lang}.{key}')
                current[key] = copy.deepcopy(value)
                changed += 1
    for fix in patch.get('corrections', []):
        try:
            current = merged['products'][fix['id']][fix['locale']]
            value = current[fix['field']]
        except (KeyError, TypeError) as exc:
            raise ValueError(f'Conflict: correction target missing {fix["id"]}') from exc
        if value == fix['replacement']:
            continue
        if value != fix['expected']:
            raise ValueError(f'Conflict: correction source changed {fix["id"]}.{fix["field"]}')
        current[fix['field']] = fix['replacement']
        changed += 1
    return merged, {'changed_fields': changed, 'locales': list(LOCALES),
                    'product_ids': list(patch['products']),
                    'native_speaker_verified': False, 'source_files_modified': False,
                    'production_deployed': False}


def write_staged(site: Path, output: Path, data: dict, summary: dict) -> None:
    site, output = Path(site).resolve(), Path(output).resolve()
    if output.is_relative_to(site):
        raise ValueError('Staged output must be outside the source site directory')
    if not site.is_dir():
        raise ValueError('Source site directory does not exist')
    output.mkdir(parents=True, exist_ok=False)
    content = (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    (output/'i18n_data.json').write_bytes(content)
    final = {**summary, 'output_sha256': hashlib.sha256(content).hexdigest()}
    (output/'preparation.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'STAGING_COMPLETE.txt').write_text('Prepared only. No source files changed. No deployment performed.\n',encoding='utf-8')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'prepare'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--site-root', required=True, type=Path, help='Existing fluxixo_site directory')
        cmd.add_argument('--content-only', action='store_true', help='Skip filesystem image checks; not a full release gate')
        if name == 'prepare':
            cmd.add_argument('--patch', type=Path, default=Path(__file__).parent/'translations/missing-products.json')
            cmd.add_argument('--output', type=Path, required=True, help='New staging directory outside source')
    args = parser.parse_args(argv)
    try:
        site = args.site_root.resolve()
        catalog = parse_catalog(read_text(site/'dist/js/catalog.js'))
        original = load_json(read_text(site/'tools/i18n_data.json'))
        summary = None
        if args.command == 'prepare':
            data, summary = prepare_patch(catalog, original, load_json(read_text(args.patch)))
        else:
            data = original
        issues = inspect_catalog(catalog, data, None if args.content_only else site/'dist')
        errors = [i for i in issues if i['severity'] == 'error']
        report = {'passed_basic_content_checks': not errors,
                  'image_files_checked': not args.content_only,
                  'language_quality_certified': False, 'production_deployed': False,
                  'issues': issues}
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if errors:
            return 1
        if summary is not None:
            write_staged(site,args.output,data,summary)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'error':str(exc),'production_deployed':False},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
