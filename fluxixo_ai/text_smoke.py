"""One-card copy and exact-image review smoke. Never generates images or publishes."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import hashlib
import os
from pathlib import Path
import re
import time

from . import autonomous
from .gemini_client import GeminiDeferred, TEXT_MODEL, REVIEW_MODEL
from . import reviewed_media

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_POLICY = 'fluxixo-card-smoke-v1'


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _save_state(path, state, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)
    try:
        from .state_checkpoint import checkpoint
        checkpoint(root=root)
    except Exception:
        raise GeminiDeferred('checkpoint_unavailable') from None


def _existing_assets(record, site):
    outputs = [record.get('image'), *(record.get('views') or [])]
    if len(outputs) != 3:
        raise ValueError('three_existing_images_required')
    sources = [record.get('original')] * 3
    identity_asset = record.get('original')
    metadata = record.get('mediaReview')
    if (isinstance(metadata, dict) and metadata.get('product_id') == str(record.get('sourceProductId', ''))
            and metadata.get('source_title_sha256') == _hash(record['sourceTitle'].encode())
            and isinstance(metadata.get('frames'), list) and len(metadata['frames']) == 3
            and [frame.get('role') for frame in metadata['frames']] == list(reviewed_media.ROLES)):
        sources = [frame.get('source_asset') for frame in metadata['frames']]
        identity_asset = metadata.get('identity_source_asset') or identity_asset
    identity = reviewed_media._safe_asset(site / 'dist', identity_asset)
    if identity is None or not identity.is_file():
        raise ValueError('canonical_seller_reference_required')
    identity_bytes = identity.read_bytes()
    result = []
    for role, source, output in zip(reviewed_media.ROLES, sources, outputs):
        paths = [reviewed_media._safe_asset(site / 'dist', relative) for relative in (source, output)]
        if any(path is None or not path.is_file() for path in paths):
            raise ValueError('existing_public_asset_required')
        result.append({'role': role, 'source_asset': source, 'output_asset': output,
                       'identity_source_asset': identity_asset, 'identity_source_bytes': identity_bytes,
                       'source_bytes': paths[0].read_bytes(), 'output_bytes': paths[1].read_bytes()})
    return result


def _review_frames(record, assets, state, state_path, root):
    prior = []
    frames = []
    overall = 'accepted'
    requested = 0
    cached = state.setdefault('reviews', {})
    for asset in assets:
        binding = {
            'policy': reviewed_media.POLICY_VERSION, 'model': REVIEW_MODEL, 'thinking_level': 'HIGH',
            'product_id': str(record.get('sourceProductId', '')), 'catalog_id': record['id'],
            'source_title_sha256': _hash(record['sourceTitle'].encode()),
            'identity_source_asset': asset['identity_source_asset'],
            'identity_source_sha256': _hash(asset['identity_source_bytes']),
            'role': asset['role'], 'source_asset': asset['source_asset'], 'output_asset': asset['output_asset'],
            'source_sha256': _hash(asset['source_bytes']), 'image_sha256': _hash(asset['output_bytes']),
            'prior_image_sha256': [_hash(value) for value in prior],
        }
        if overall != 'accepted':
            frames.append({**binding, 'status': 'not_reviewed', 'reason': 'prior_frame_not_accepted', 'reused': False})
            continue
        key = _hash(json.dumps(binding, sort_keys=True).encode())
        previous = cached.get(asset['role']) or {}
        reused = previous.get('input_key') == key and (
            previous.get('status') in ('accepted', 'rejected', 'uncertain')
            or previous.get('status') == 'deferred' and previous.get('retry_at', 0) > time.time())
        if reused:
            outcome = dict(previous)
            if outcome['status'] == 'accepted' and not reviewed_media._valid_review(outcome.get('assessment')):
                reused = False
        if not reused:
            try:
                requested += 1
                assessment = reviewed_media._default_reviewer(
                    asset['source_bytes'], asset['output_bytes'], title=record['sourceTitle'],
                    role=asset['role'], identity_source=asset['identity_source_bytes'], prior_outputs=tuple(prior),
                )
                if reviewed_media._valid_review(assessment):
                    status = 'accepted'
                elif (isinstance(assessment, dict)
                      and all(type(assessment.get(key)) is bool for key in ('accepted', *reviewed_media.CHECKS))):
                    status = 'rejected'
                else:
                    status = 'uncertain'
                outcome = {'input_key': key, 'status': status, 'assessment': assessment, 'reviewed_at': time.time()}
            except GeminiDeferred as error:
                outcome = {'input_key': key, 'status': 'deferred', 'reason': error.code, 'retry_at': error.retry_at}
            except Exception:
                outcome = {'input_key': key, 'status': 'deferred', 'reason': 'review_unavailable', 'retry_at': time.time() + 300}
            cached[asset['role']] = outcome
            _save_state(state_path, state, root)
        frame = {**binding, **outcome, 'reused': reused}
        frames.append(frame)
        if outcome['status'] == 'accepted':
            prior.append(asset['output_bytes'])
        else:
            overall = outcome['status']
    return frames, overall, requested


def run_smoke(catalog_id, *, repo_root=REPO_ROOT):
    """Exercise the daily text enrichment path on copies of one existing record."""
    if not isinstance(catalog_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', catalog_id):
        raise ValueError('invalid_catalog_id')
    root = Path(repo_root).resolve()
    site = root / 'fluxixo_site'
    raw = (site / 'dist/js/catalog.js').read_text(encoding='utf-8')
    catalog = json.loads(raw.split('=', 1)[1].strip().removesuffix(';'))
    i18n = json.loads((site / 'tools/i18n_data.json').read_text(encoding='utf-8'))
    matches = [p for p in catalog.get('products', []) if p.get('id') == catalog_id]
    if len(matches) != 1 or matches[0].get('demo'):
        raise ValueError('existing_catalog_item_required')
    record = deepcopy(matches[0])
    translated = deepcopy(i18n.get('products', {}).get(catalog_id))
    if not isinstance(translated, dict) or set(autonomous.LANGS) - {'ru'} - set(translated):
        raise ValueError('existing_six_language_copy_required')
    source = str(record.get('sourceTitle') or '').strip()
    if not source:
        raise ValueError('source_title_required')
    if os.environ.get('FLUXIXO_TEXT_PROVIDER', '').lower() != 'gemini':
        raise ValueError('explicit_gemini_provider_required')
    if not os.environ.get('FLUXIXO_TEXT_GEMINI_API_KEY', '').strip():
        raise GeminiDeferred('gemini_key_missing')
    # Load only existing public files before any paid/free inference attempt.
    assets = _existing_assets(record, site)
    state_path = site / 'reserve/reviewed-media/smoke' / catalog_id / 'state.json'
    try:
        state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    except (OSError, ValueError):
        raise GeminiDeferred('smoke_state_unavailable') from None
    if not isinstance(state, dict):
        raise GeminiDeferred('smoke_state_unavailable')

    ai_seo, originality = autonomous._import_tools_modules(site)
    overrides_file = site / 'tools/seo_overrides.json'
    overrides = json.loads(overrides_file.read_text(encoding='utf-8')).get('routes', {}) if overrides_file.exists() else {}
    overrides = {route: value for route, value in overrides.items()
                 if f'/products/{catalog_id}/' not in route}
    corpus = originality.build_catalog_copy_corpus(catalog['products'], i18n,
                                                  extra_routes=overrides, exclude_ids={catalog_id})
    text_key = _hash(json.dumps([SMOKE_POLICY, TEXT_MODEL, 'HIGH', catalog, i18n, overrides],
                                sort_keys=True, ensure_ascii=False).encode())
    text_state = state.get('text') or {}
    text_reused = text_state.get('input_key') == text_key and isinstance(text_state.get('copy'), dict)
    if text_reused:
        saved = text_state['copy']
        updated = {**record, **saved['ru']}
        locales = {lang: saved[lang] for lang in autonomous.LANGS if lang != 'ru'}
    else:
        updated, locales = autonomous._maybe_ai_enrich(
            record, translated, {'title': source}, site, catalog_corpus=corpus,
        )
    # Apply both daily and detailed field validators. No baseline fallback can masquerade as success.
    bundle = {'ru': {key: updated[key] for key in ('name', 'headline', 'description')},
              **{lang: locales[lang] for lang in autonomous.LANGS if lang != 'ru'}}
    errors = autonomous._copy_validation_problems(updated, locales, site, catalog_corpus=corpus)
    errors += ai_seo.validate_product_bundle(
        bundle, source_text=f'{source} {json.dumps({"ru": record, **translated}, ensure_ascii=False)}',
        source_title=source, catalog_corpus=corpus, min_desc_len=160,
    )
    if errors:
        state.pop('text', None)
        _save_state(state_path, state, root)
        raise GeminiDeferred('smoke_copy_validation_failed')
    state['text'] = {'input_key': text_key, 'copy': bundle, 'model': TEXT_MODEL, 'thinking_level': 'HIGH'}
    _save_state(state_path, state, root)
    frames, status, requested = _review_frames(record, assets, state, state_path, root)
    return {
        'success': status == 'accepted', 'status': status, 'catalog_id': catalog_id, 'provider': 'gemini', 'model': TEXT_MODEL,
        'thinking_level': 'HIGH', 'validated_locales': len(bundle), 'published': False,
        'all_frames_accepted': status == 'accepted', 'photo_review_model': REVIEW_MODEL,
        'text_reused': text_reused, 'reviews_requested': requested, 'frames': frames,
        'validation': 'daily copy, six-language field, source-title and catalog originality checks passed',
        'external_snippet_check_enabled': os.environ.get('FLUXIXO_WEB_CHECK', '') == '1',
        'copy': bundle,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog-id', required=True)
    parser.add_argument('--output', help='Optional JSON artifact path outside the repository')
    args = parser.parse_args(argv)
    target = Path(args.output).resolve() if args.output else None
    if target is not None and target.is_relative_to(REPO_ROOT):
        parser.error('output must be outside the repository; site writes are forbidden')
    try:
        report = run_smoke(args.catalog_id)
        exit_code = 0 if report['success'] else (2 if report['status'] == 'deferred' else 3)
    except GeminiDeferred as error:
        report = {'success': False, 'published': False, 'reason': error.code, 'retry_at': error.retry_at}
        exit_code = 2
    except (ValueError, KeyError, OSError):
        report = {'success': False, 'published': False, 'reason': 'invalid_smoke_input_or_catalog'}
        exit_code = 2
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {key: value for key, value in report.items() if key not in ('copy', 'frames')}
    if 'frames' in report:
        summary['frames'] = [{key: frame[key] for key in ('role', 'status', 'reused')} for frame in report['frames']]
    print(json.dumps(summary, ensure_ascii=True))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
