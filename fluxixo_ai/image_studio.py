"""Pure-Pillow perceptual image uniqueness (dHash/aHash) & FLUXIXO studio mastering.

Zero external runtime dependencies beyond Pillow + Python standard library so
lightweight CI jobs and offline tests import cleanly without rembg or numpy.
"""
from __future__ import annotations

import base64
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ALPHA_FLOOR = 24
TIGHT_BBOX_ALPHA = 20
DEFAULT_CLOUDFLARE_ACCOUNT_ID = 'a4be28e05f73ad2b3939d364ea8b2817'
DEFAULT_CLOUDFLARE_AUTOPILOT_URL = 'https://fluxixo-autopilot.sayros2601.workers.dev'
WRANGLER_OAUTH_USER_AGENT = 'wrangler/4.151.3'
DEFAULT_IMAGE_MODEL = '@cf/black-forest-labs/flux-2-klein-9b'
FALLBACK_IMAGE_MODEL = '@cf/black-forest-labs/flux-2-klein-4b'
CF_IMAGE_FALLBACK_MODELS = (
    '@cf/black-forest-labs/flux-2-klein-9b',
    '@cf/black-forest-labs/flux-2-klein-4b',
)
DEFAULT_VISION_MODEL = '@cf/meta/llama-4-scout-17b-16e-instruct'
CF_VISION_FALLBACK_MODELS = (
    '@cf/meta/llama-4-scout-17b-16e-instruct',
    '@cf/mistralai/mistral-small-3.1-24b-instruct',
    '@cf/qwen/qwen3.8-27b',
)
GITHUB_MODELS_URL = 'https://models.github.ai/inference/chat/completions'
GITHUB_VISION_MODELS = (
    'openai/gpt-4o-mini',
    'openai/gpt-4o',
)


def compute_dhash(image: Image.Image, *, size: int = 8) -> str:
    """Compute horizontal-gradient difference hash formatted as lowercase hex."""
    grey = image.convert('L').resize((size + 1, size), Image.Resampling.LANCZOS)
    px = grey.tobytes()
    bits = 0
    total = size * size
    stride = size + 1
    for i in range(total):
        row, col = divmod(i, size)
        if px[row * stride + col] > px[row * stride + col + 1]:
            bits |= 1 << i
    return f'{bits:0{total // 4}x}'


def compute_ahash(image: Image.Image, *, size: int = 8) -> str:
    """Compute mean-luminance average hash formatted as lowercase hex."""
    grey = image.convert('L').resize((size, size), Image.Resampling.LANCZOS)
    px = grey.tobytes()
    total = size * size
    mean = sum(px) / total if total else 0.0
    bits = 0
    for i, val in enumerate(px):
        if val >= mean:
            bits |= 1 << i
    return f'{bits:0{total // 4}x}'


def hamming_distance(hex_a: str, hex_b: str) -> int:
    """Compute bitwise Hamming distance between two equal-length hex digests."""
    if not isinstance(hex_a, str) or not isinstance(hex_b, str) or len(hex_a) != len(hex_b) or not hex_a:
        raise ValueError('hash digests must be non-empty equal-length hex strings')
    return (int(hex_a, 16) ^ int(hex_b, 16)).bit_count()


def tight_alpha_bbox(cutout: Image.Image, *, alpha_floor: int = TIGHT_BBOX_ALPHA) -> tuple[int, int, int, int] | None:
    """Compute tight bounding box ignoring stray ultra-faint edge noise below alpha_floor."""
    rgba = cutout if cutout.mode == 'RGBA' else cutout.convert('RGBA')
    mask = rgba.getchannel('A').point(lambda a: 255 if a >= alpha_floor else 0)
    return mask.getbbox() or rgba.getbbox()


def _content_aspect(image: Image.Image, *, alpha_floor: int = ALPHA_FLOOR) -> str:
    if 'A' in image.getbands():
        bbox = tight_alpha_bbox(image, alpha_floor=alpha_floor)
        if bbox:
            w = max(1, bbox[2] - bbox[0])
            h = max(1, bbox[3] - bbox[1])
            return f'{w / h:.2f}'
    w, h = max(1, image.width), max(1, image.height)
    return f'{w / h:.2f}'


def compute_rgb_dhash(image: Image.Image, *, size: int = 8) -> str:
    """Compute concatenated horizontal-gradient dHash for R, G, and B channels."""
    rgb = image.convert('RGB')
    return ''.join(compute_dhash(ch, size=size) for ch in rgb.split())


def canonical_rgb_for_hash(
    image: Image.Image,
    *,
    alpha_floor: int = ALPHA_FLOOR,
    out_size: int = 128,
) -> Image.Image:
    """Trim transparent margin if present and normalize content via crop-fill RGB."""
    if 'A' in image.getbands():
        rgba = image.convert('RGBA')
        alpha = rgba.getchannel('A')
        extrema = alpha.getextrema()
        if extrema and extrema[0] < 250:
            bbox = tight_alpha_bbox(rgba, alpha_floor=alpha_floor)
            if bbox:
                rgba = rgba.crop(bbox)
            rgba_small = rgba.resize((out_size, out_size), Image.Resampling.LANCZOS)
            white_bg = Image.new('RGBA', (out_size, out_size), (255, 255, 255, 255))
            return Image.alpha_composite(white_bg, rgba_small).convert('RGB')
        work = rgba.convert('RGB')
    else:
        work = image.convert('RGB')

    return work.resize((out_size, out_size), Image.Resampling.LANCZOS)


def compute_perceptual_hashes(image: Image.Image, *, alpha_floor: int = ALPHA_FLOOR) -> dict[str, str]:
    """Compute canonical and mirrored dHash/aHash/RGB-dHash descriptors plus trimmed aspect ratio."""
    aspect = _content_aspect(image, alpha_floor=alpha_floor)
    canon = canonical_rgb_for_hash(image, alpha_floor=alpha_floor, out_size=128)
    mirror = ImageOps.mirror(canon)
    return {
        'dhash': compute_dhash(canon),
        'ahash': compute_ahash(canon),
        'rgb_dhash': compute_rgb_dhash(canon),
        'dhash_mirror': compute_dhash(mirror),
        'ahash_mirror': compute_ahash(mirror),
        'rgb_dhash_mirror': compute_rgb_dhash(mirror),
        'aspect': aspect,
    }


def _file_perceptual_hashes(path: Path, rel: str, cache: dict[str, Any]) -> tuple[dict[str, str] | None, bool]:
    try:
        st = path.stat()
    except OSError:
        return None, False
    if st.st_size > 12_000_000 or st.st_size == 0:
        return None, False
    cached = cache.get(rel)
    if (
        isinstance(cached, dict)
        and cached.get('size') == st.st_size
        and cached.get('mtime_ns') == st.st_mtime_ns
        and isinstance(cached.get('hashes'), dict)
        and cached['hashes'].get('dhash')
        and cached['hashes'].get('ahash')
        and cached['hashes'].get('rgb_dhash')
    ):
        return cached['hashes'], False
    try:
        with Image.open(path) as img:
            if img.width < 1 or img.height < 1 or img.width * img.height > 25_000_000:
                return None, False
            img.load()
            hashes = compute_perceptual_hashes(img)
        cache[rel] = {
            'size': st.st_size,
            'mtime_ns': st.st_mtime_ns,
            'hashes': hashes,
        }
        return hashes, True
    except Exception:
        return None, False


def load_catalog_perceptual_index(
    products: list[dict[str, Any]],
    dist: Path,
    *,
    cache_path: Path | None = None,
    include_originals: bool = True,
) -> list[dict[str, Any]]:
    """Index perceptual hashes for all catalog assets, top-level dist/assets/images, and originals."""
    dist_resolved = Path(dist).resolve()
    cache: dict[str, Any] = {}
    cache_dirty = False
    if cache_path is not None and cache_path.is_file():
        try:
            raw_cache = json.loads(cache_path.read_text(encoding='utf-8'))
            if isinstance(raw_cache, dict):
                cache = raw_cache
        except Exception:
            cache = {}

    entries: list[dict[str, Any]] = []
    seen_rels: set[str] = set()
    rel_to_pid: dict[str, str] = {}

    for product in products or ():
        pid = str(product.get('id') or '')
        if not pid:
            continue
        if isinstance(product.get('imageDhash'), str) and isinstance(product.get('imageAhash'), str):
            entries.append({
                'id': pid,
                'path': str(product.get('image') or ''),
                'kind': 'catalog_image',
                'dhash': product['imageDhash'],
                'ahash': product['imageAhash'],
                **({'aspect': str(product['imageAspect'])} if product.get('imageAspect') else {}),
            })
        if (
            include_originals
            and isinstance(product.get('sourceImageDhash'), str)
            and isinstance(product.get('sourceImageAhash'), str)
        ):
            entries.append({
                'id': pid,
                'path': str(product.get('original') or ''),
                'kind': 'catalog_original',
                'dhash': product['sourceImageDhash'],
                'ahash': product['sourceImageAhash'],
                **({'aspect': str(product['sourceAspect'])} if product.get('sourceAspect') else {}),
            })
        for field_rel in ([product.get('image')] + list(product.get('views') or [])):
            if isinstance(field_rel, str) and field_rel:
                rel_to_pid[field_rel.replace('\\', '/')] = pid
        if include_originals and isinstance(product.get('original'), str) and product['original']:
            rel_to_pid[product['original'].replace('\\', '/')] = pid

    candidate_files: list[tuple[str, str, Path]] = []
    for rel, pid in rel_to_pid.items():
        if rel.startswith('assets/images/watch-layers/'):
            continue
        p = (dist_resolved / rel).resolve()
        if p.is_relative_to(dist_resolved) and p.is_file():
            candidate_files.append((rel, pid, p))

    images_dir = dist_resolved / 'assets' / 'images'
    if images_dir.is_dir():
        for p in sorted(images_dir.glob('*.webp')):
            rel = f'assets/images/{p.name}'
            pid = rel_to_pid.get(rel, f'file:{p.stem}')
            candidate_files.append((rel, pid, p))

    if include_originals:
        orig_dir = dist_resolved / 'assets' / 'originals'
        if orig_dir.is_dir():
            for p in sorted(orig_dir.iterdir()):
                if p.suffix.lower() not in ('.webp', '.jpg', '.jpeg', '.png'):
                    continue
                rel = f'assets/originals/{p.name}'
                pid = rel_to_pid.get(rel, f'file:{p.stem}')
                candidate_files.append((rel, pid, p))

    for rel, pid, path in candidate_files:
        if rel in seen_rels:
            continue
        seen_rels.add(rel)
        hashes, updated = _file_perceptual_hashes(path, rel, cache)
        if updated:
            cache_dirty = True
        if hashes:
            entries.append({
                'id': pid,
                'path': rel,
                'kind': 'original' if '/originals/' in rel else 'cutout',
                **hashes,
            })

    if cache_dirty and cache_path is not None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
        except OSError:
            pass

    return entries


def _aspect_compatible(aspect_a: Any, aspect_b: Any, *, max_log_diff: float = 0.35) -> bool:
    try:
        a = float(aspect_a)
        b = float(aspect_b)
    except (TypeError, ValueError):
        return True
    if a <= 0 or b <= 0:
        return True
    return abs(math.log(a / b)) <= max_log_diff


def is_perceptually_duplicate(
    candidate_hashes: dict[str, Any],
    index: list[dict[str, Any]] | None,
    *,
    dhash_threshold: int = 10,
    ahash_threshold: int = 8,
    strong_dhash_threshold: int = 6,
    rgb_dhash_threshold: int = 30,
) -> tuple[bool, dict[str, Any] | None]:
    """Compare candidate dHash/aHash/RGB-dHash (direct and mirror) against catalog index."""
    if not index or not isinstance(candidate_hashes, dict):
        return False, None
    c_dhash = candidate_hashes.get('dhash')
    c_ahash = candidate_hashes.get('ahash')
    if not c_dhash or not c_ahash:
        return False, None
    c_rgb = candidate_hashes.get('rgb_dhash')
    c_dmirror = candidate_hashes.get('dhash_mirror')
    c_amirror = candidate_hashes.get('ahash_mirror')
    c_rgb_mirror = candidate_hashes.get('rgb_dhash_mirror')
    c_aspect = candidate_hashes.get('aspect')

    for entry in index:
        e_dhash = entry.get('dhash')
        e_ahash = entry.get('ahash')
        if not e_dhash or not e_ahash or len(e_dhash) != len(c_dhash) or len(e_ahash) != len(c_ahash):
            continue
        if not _aspect_compatible(c_aspect, entry.get('aspect')):
            continue
        e_rgb = entry.get('rgb_dhash')

        pairs: list[tuple[str, str, str, str | None]] = [('direct', c_dhash, c_ahash, c_rgb)]
        if c_dmirror and c_amirror:
            pairs.append(('mirror', c_dmirror, c_amirror, c_rgb_mirror))

        for mode, d_cmp, a_cmp, rgb_cmp in pairs:
            d_dist = hamming_distance(d_cmp, e_dhash)
            a_dist = hamming_distance(a_cmp, e_ahash)
            rgb_dist: int | None = None
            if rgb_cmp and e_rgb and len(rgb_cmp) == len(e_rgb):
                rgb_dist = hamming_distance(rgb_cmp, e_rgb)
            if rgb_dist is not None and rgb_dist > rgb_dhash_threshold:
                continue
            if (d_dist <= dhash_threshold and a_dist <= ahash_threshold) or d_dist <= strong_dhash_threshold:
                return True, {
                    'id': entry.get('id', ''),
                    'path': entry.get('path', ''),
                    'kind': entry.get('kind', ''),
                    'mode': mode,
                    'dhash_dist': d_dist,
                    'ahash_dist': a_dist,
                    **({'rgb_dhash_dist': rgb_dist} if rgb_dist is not None else {}),
                }
    return False, None


def _bleed_interior_rgb(rgba: Image.Image, solid_mask: Image.Image, blur_radius: int = 3) -> Image.Image:
    """Propagate solid foreground colors outward over transparent edge halo without background bleed."""
    w, h = rgba.size
    fg = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    fg.paste(rgba.convert('RGB'), (0, 0), mask=solid_mask)

    base = fg
    for denom in (8, 4, 2):
        sw, sh = max(4, w // denom), max(4, h // denom)
        layer = fg.resize((sw, sh), Image.Resampling.BILINEAR).resize((w, h), Image.Resampling.BILINEAR)
        base = Image.alpha_composite(layer, base)

    out_rgb = base.convert('RGB')
    if blur_radius > 0:
        out_rgb = out_rgb.filter(ImageFilter.GaussianBlur(max(0.8, blur_radius * 0.6)))
    return out_rgb


def clean_cutout_alpha(
    cutout: Image.Image,
    *,
    alpha_floor: int = ALPHA_FLOOR,
    solid_alpha: int = 215,
    feather_radius: float = 0.55,
    dehalo_radius: int = 3,
) -> Image.Image:
    """Clean residual background haze, feather outer silhouette, and decontaminate edge halos."""
    rgba = cutout.convert('RGBA')
    alpha = rgba.getchannel('A')

    ramp_span = max(1, solid_alpha - alpha_floor)
    lut = [
        0 if v < alpha_floor else (v if v >= solid_alpha else min(255, round((v - alpha_floor) * solid_alpha / ramp_span)))
        for v in range(256)
    ]
    cleaned_a = alpha.point(lut)
    if feather_radius > 0:
        soft = cleaned_a.filter(ImageFilter.GaussianBlur(feather_radius))
        # Preserve completely solid interior opacity and keep background pixels strictly zero.
        support = cleaned_a.point(lambda v: 255 if v > 0 else 0)
        soft = ImageChops.multiply(soft, support)
        interior_preserve = cleaned_a.point(lambda v: v if v >= solid_alpha else 0)
        cleaned_a = ImageChops.lighter(soft, interior_preserve)

    solid_mask = alpha.point(lambda v: 255 if v >= solid_alpha else 0)
    if solid_mask.getbbox() is None:
        out = rgba.copy()
        out.putalpha(cleaned_a)
        return out

    dehalo_rgb = _bleed_interior_rgb(rgba, solid_mask, blur_radius=dehalo_radius)
    orig_rgb = rgba.convert('RGB')
    merged_rgb = Image.composite(orig_rgb, dehalo_rgb, solid_mask)
    result = merged_rgb.convert('RGBA')
    result.putalpha(cleaned_a)
    return result


def _hist_percentile(hist: list[int], pct: float) -> int:
    total = sum(hist)
    if total <= 0:
        return 0
    target = total * pct
    acc = 0
    for idx, count in enumerate(hist):
        acc += count
        if acc >= target:
            return idx
    return 255


def normalize_studio_contrast(
    cutout: Image.Image,
    *,
    low_pct: float = 0.015,
    high_pct: float = 0.988,
    max_gain: float = 1.22,
    black_floor: int = 6,
    white_ceiling: int = 250,
    saturation_boost: float = 1.04,
) -> Image.Image:
    """Apply bounded foreground-only tonal normalization; preserves alpha channel verbatim."""
    rgba = cutout.convert('RGBA')
    alpha = rgba.getchannel('A')
    mask = alpha.point(lambda a: 255 if a >= 128 else 0)
    if mask.getbbox() is None:
        return rgba

    luma = rgba.convert('L')
    hist = luma.histogram(mask=mask)
    total = sum(hist)
    if total < 32:
        return rgba

    p_low = _hist_percentile(hist, low_pct)
    p_high = _hist_percentile(hist, high_pct)
    span = max(24, p_high - p_low)

    # Gentle haze lift only when darks sit elevated, without crushing genuinely dark products.
    shift_low = max(0, min(p_low - black_floor, round(p_low * 0.45))) if p_low > 18 else 0
    target_span = max(24, white_ceiling - max(black_floor, p_low - shift_low))
    gain = min(max_gain, max(1.0, target_span / span))

    rgb = rgba.convert('RGB')
    if gain > 1.015 or shift_low > 0:
        lut = [
            max(0, min(255, round((v - shift_low) * gain + (black_floor * 0.35 if shift_low else 0))))
            for v in range(256)
        ]
        rgb = rgb.point(lut * 3)

    if saturation_boost != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(saturation_boost)

    out = rgb.convert('RGBA')
    out.putalpha(alpha)
    return out


def apply_studio_contact_shadow(
    canvas: Image.Image,
    placed_cutout: Image.Image,
    paste_box: tuple[int, int, int, int],
    *,
    max_opacity: float = 0.14,
    blur_radius: float = 15.0,
    shadow_height_ratio: float = 0.032,
) -> Image.Image:
    """Render an adaptive subtle contact-shadow ellipse beneath the object's resting foot."""
    base_rgba = canvas.convert('RGBA')
    fg_rgba = placed_cutout.convert('RGBA')
    fg_w, fg_h = fg_rgba.size
    if fg_w < 4 or fg_h < 4:
        return base_rgba

    # Inspect bottom 8% strip to track actual object foot span rather than full canvas width.
    strip_h = max(2, round(fg_h * 0.08))
    bottom_alpha = fg_rgba.crop((0, fg_h - strip_h, fg_w, fg_h)).getchannel('A')
    foot_bbox = bottom_alpha.point(lambda a: 255 if a >= 160 else 0).getbbox()
    if foot_bbox and (foot_bbox[2] - foot_bbox[0]) >= 6:
        fx0, fx1 = foot_bbox[0], foot_bbox[2]
    else:
        inset = round(fg_w * 0.2)
        fx0, fx1 = inset, max(inset + 6, fg_w - inset)

    px0, py0, _, _ = paste_box
    pad_margin = round(blur_radius * 2.2) + 2
    foot_span = max(12, fx1 - fx0)
    sx0 = max(pad_margin, px0 + fx0 - round(foot_span * 0.03))
    sx1 = min(base_rgba.width - pad_margin, px0 + fx1 + round(foot_span * 0.03))
    if sx1 - sx0 < 10:
        return base_rgba

    shadow_h = max(8, round(fg_h * shadow_height_ratio))
    cy = py0 + fg_h - max(1, round(fg_h * 0.01))
    sy0 = max(pad_margin, cy - shadow_h // 2)
    sy1 = min(base_rgba.height - pad_margin, sy0 + shadow_h)
    if sy1 - sy0 < 4:
        return base_rgba

    shadow = Image.new('RGBA', base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    peak_alpha = max(1, min(60, round(255 * max_opacity)))
    draw.ellipse((sx0, sy0, sx1, sy1), fill=(20, 18, 24, peak_alpha))
    if blur_radius > 0:
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))

    return Image.alpha_composite(shadow, base_rgba)


def _alpha_center_x(rgba: Image.Image) -> float:
    """Weighted horizontal alpha mass center scaled to [0..width]."""
    small = rgba.getchannel('A')
    sw, sh = min(128, small.width), min(128, small.height)
    if sw < 2 or sh < 2:
        return rgba.width / 2.0
    grid = small.resize((sw, sh), Image.Resampling.BOX)
    px = grid.tobytes()
    total = 0
    wx = 0
    for idx, val in enumerate(px):
        if val >= 48:
            total += val
            wx += (idx % sw) * val
    if total == 0:
        return rgba.width / 2.0
    return ((wx / total) + 0.5) * (rgba.width / sw)


def apply_foreground_clarity(cutout: Image.Image, *, upscale_ratio: float = 1.0) -> Image.Image:
    """Apply bounded UnsharpMask clarity strictly inside solid opaque foreground pixels."""
    rgba = cutout.convert('RGBA')
    alpha = rgba.getchannel('A')
    solid_mask = alpha.point(lambda a: 255 if a >= 210 else 0)
    if solid_mask.getbbox() is None:
        return rgba

    # Mild clarity at native/downscale; stronger micro-detail recovery on mild upscale, never magnifying noise.
    clamped_ratio = max(1.0, min(2.6, float(upscale_ratio)))
    percent = round(36 + (clamped_ratio - 1.0) * 26)
    sharpened_rgb = rgba.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1.05, percent=percent, threshold=4))
    merged_rgb = Image.composite(sharpened_rgb, rgba.convert('RGB'), solid_mask)
    out = merged_rgb.convert('RGBA')
    out.putalpha(alpha)
    return out


def measure_image_quality(
    cutout: Image.Image,
    *,
    raw_fg_size: tuple[int, int] | None = None,
    composed: Image.Image | None = None,
    target_box: int = 890,
) -> dict[str, Any]:
    """Compute foreground resolution, upscale ratio, sharpness, exposure, border clipping, and halo metrics."""
    raw_rgba = cutout.convert('RGBA')
    bbox = tight_alpha_bbox(raw_rgba, alpha_floor=TIGHT_BBOX_ALPHA)
    if raw_fg_size is not None:
        fg_w, fg_h = int(raw_fg_size[0]), int(raw_fg_size[1])
    elif bbox:
        fg_w, fg_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        fg_w, fg_h = 0, 0
    fg_max_side = max(fg_w, fg_h)
    fg_min_side = min(fg_w, fg_h)
    upscale_ratio = round(target_box / max(1, fg_max_side), 3) if fg_max_side > 0 else 999.0

    # Measure border contact on raw seller cutout (detects cropped-off edges before studio padding).
    rw, rh = raw_rgba.size
    raw_alpha = raw_rgba.getchannel('A')
    border_hits: list[float] = []
    if rw >= 8 and rh >= 8:
        edges = [
            raw_alpha.crop((0, 0, rw, 2)),
            raw_alpha.crop((0, rh - 2, rw, rh)),
            raw_alpha.crop((0, 0, 2, rh)),
            raw_alpha.crop((rw - 2, 0, rw, rh)),
        ]
        for strip in edges:
            vals = strip.tobytes()
            border_hits.append(sum(1 for v in vals if v >= 180) / max(1, len(vals)))
    max_border_clip = round(max(border_hits) if border_hits else 0.0, 3)
    clipped_edges = sum(1 for r in border_hits if r > 0.35)

    # Measure interior sharpness, luma dynamic range, and semi-transparent white fringe on composed/cutout.
    target = (composed or raw_rgba).convert('RGBA')
    tb = tight_alpha_bbox(target, alpha_floor=TIGHT_BBOX_ALPHA)
    roi = target.crop(tb) if tb else target
    roi.thumbnail((256, 256), Image.Resampling.LANCZOS)
    rw2, rh2 = roi.size
    r_px = roi.convert('RGB').tobytes()
    a_px = roi.getchannel('A').tobytes()
    l_px = roi.convert('L').tobytes()

    grad_sum = 0.0
    grad_cnt = 0
    luma_vals: list[int] = []
    rim_total = 0
    rim_white = 0

    for y in range(rh2):
        row_off = y * rw2
        for x in range(rw2):
            idx = row_off + x
            a = a_px[idx]
            if a >= 180:
                luma_vals.append(l_px[idx])
                if x + 1 < rw2 and y + 1 < rh2 and a_px[idx + 1] >= 180 and a_px[idx + rw2] >= 180:
                    gx = abs(l_px[idx + 1] - l_px[idx])
                    gy = abs(l_px[idx + rw2] - l_px[idx])
                    grad_sum += gx + gy
                    grad_cnt += 1
            elif 24 <= a < 160:
                rim_total += 1
                rgb_i = idx * 3
                r_c, g_c, b_c = r_px[rgb_i], r_px[rgb_i + 1], r_px[rgb_i + 2]
                if min(r_c, g_c, b_c) >= 235 and max(r_c, g_c, b_c) - min(r_c, g_c, b_c) <= 14:
                    rim_white += 1

    sharpness = round(grad_sum / grad_cnt, 3) if grad_cnt else 0.0
    if luma_vals:
        mean_luma = sum(luma_vals) / len(luma_vals)
        var = sum((v - mean_luma) ** 2 for v in luma_vals) / len(luma_vals)
        luma_std = math.sqrt(var)
    else:
        mean_luma, luma_std = 0.0, 0.0
    halo_fringe = round(rim_white / rim_total, 3) if rim_total >= 12 and mean_luma < 215 else 0.0

    return {
        'fg_width': fg_w,
        'fg_height': fg_h,
        'fg_max_side': fg_max_side,
        'fg_min_side': fg_min_side,
        'upscale_ratio': upscale_ratio,
        'sharpness': sharpness,
        'fg_mean_luma': round(mean_luma, 2),
        'fg_luma_std': round(luma_std, 2),
        'max_border_clip': max_border_clip,
        'clipped_edges': clipped_edges,
        'halo_fringe_ratio': halo_fringe,
    }


def verify_studio_image(
    cutout: Image.Image,
    *,
    raw_fg_size: tuple[int, int] | None = None,
    composed: Image.Image | None = None,
    min_fg_side: int = 360,
    max_upscale: float = 2.6,
    min_sharpness: float = 4.2,
    max_border_clip: float = 0.65,
    max_halo_fringe: float = 0.48,
) -> tuple[bool, dict[str, Any]]:
    """Verify foreground sharpness, resolution, framing, exposure, and halo freedom before publication."""
    metrics = measure_image_quality(cutout, raw_fg_size=raw_fg_size, composed=composed)
    reasons: list[str] = []
    if metrics['fg_max_side'] < min_fg_side:
        reasons.append('low_foreground_resolution')
    if metrics['upscale_ratio'] > max_upscale:
        reasons.append('excessive_upscale')
    if metrics['sharpness'] < min_sharpness:
        reasons.append('blurry_foreground')
    if metrics['fg_mean_luma'] > 246 and metrics['fg_luma_std'] < 8.0:
        reasons.append('washed_out')
    if metrics['fg_mean_luma'] < 14 and metrics['fg_luma_std'] < 6.0:
        reasons.append('crushed_dark')
    if metrics['max_border_clip'] > max_border_clip or metrics['clipped_edges'] >= 2:
        reasons.append('cropped_subject')
    if metrics['halo_fringe_ratio'] > max_halo_fringe:
        reasons.append('halo_fringe')
    return not reasons, {**metrics, 'reasons': reasons}


def compose_studio_frame(
    cutout: Image.Image,
    *,
    canvas_size: int = 1254,
    max_box: int = 890,
    normalize_tonality: bool = True,
    add_contact_shadow: bool = True,
    apply_clarity: bool = True,
) -> Image.Image:
    """Clean, trim, contrast-balance, micro-sharpen, frame, and ground a transparent cutout."""
    cleaned = clean_cutout_alpha(cutout)
    bbox = tight_alpha_bbox(cleaned, alpha_floor=TIGHT_BBOX_ALPHA)
    if bbox:
        cleaned = cleaned.crop(bbox)

    scale = min(max_box / max(1, cleaned.width), max_box / max(1, cleaned.height))
    fit = (max(1, round(cleaned.width * scale)), max(1, round(cleaned.height * scale)))
    placed = cleaned.resize(fit, Image.Resampling.LANCZOS)
    if normalize_tonality:
        placed = normalize_studio_contrast(placed)
    if apply_clarity:
        placed = apply_foreground_clarity(placed, upscale_ratio=scale)

    # Blend optical mass center with geometric center (clamped to +-4% of canvas width).
    geo_x = (canvas_size - fit[0]) / 2.0
    mass_shift = (fit[0] / 2.0) - _alpha_center_x(placed)
    max_shift = canvas_size * 0.04
    mass_shift = max(-max_shift, min(max_shift, mass_shift * 0.35))
    x = max(0, min(canvas_size - fit[0], round(geo_x + mass_shift)))
    y = max(0, min(canvas_size - fit[1], round((canvas_size - fit[1]) * 0.48)))

    canvas = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.alpha_composite(placed, (x, y))
    if add_contact_shadow:
        canvas = apply_studio_contact_shadow(
            canvas,
            placed,
            (x, y, x + fit[0], y + fit[1]),
        )
    return canvas


WORLD_BACKGROUNDS: dict[str, str] = {
    'Техника': '#DFE5FB',
    'Дом': '#F1E3CF',
    'Кухня': '#D9EEDE',
    'В дороге': '#FBE7A6',
    'Инструменты': '#FDD8C4',
    'Уход': '#F8D9E6',
    'Спорт': '#D3EDF5',
    'На природе': '#DFEAC4',
    'Питомцы': '#E9DCF8',
    'tech': '#DFE5FB',
    'home': '#F1E3CF',
    'kitchen': '#D9EEDE',
    'auto-travel': '#FBE7A6',
    'tools': '#FDD8C4',
    'beauty-care': '#F8D9E6',
    'sports': '#D3EDF5',
    'outdoors': '#DFEAC4',
    'pets': '#E9DCF8',
}


def compose_direct_studio_frame(
    image: Image.Image,
    *,
    background_hex: str | None = None,
    canvas_size: int = 1254,
    apply_clarity: bool = True,
) -> Image.Image:
    """Master a studio render directly on its world background without cutting or punching holes."""
    target_rgb = parse_hex_color(background_hex) or (243, 240, 233)
    rgb = image.convert('RGB')
    w, h = rgb.size
    if w >= 8 and h >= 8:
        px = bytearray(rgb.tobytes())
        corners = [
            rgb.getpixel((4, 4)),
            rgb.getpixel((w - 5, 4)),
            rgb.getpixel((4, h - 5)),
            rgb.getpixel((w - 5, h - 5)),
        ]
        cur_r = sum(c[0] for c in corners) / 4.0
        cur_g = sum(c[1] for c in corners) / 4.0
        cur_b = sum(c[2] for c in corners) / 4.0
        tr, tg, tb = target_rgb
        tol = 44.0
        for i in range(0, len(px), 3):
            r, g, b = px[i], px[i + 1], px[i + 2]
            dist = ((r - cur_r) ** 2 + (g - cur_g) ** 2 + (b - cur_b) ** 2) ** 0.5
            if dist < tol:
                w_blend = 1.0 if dist <= tol * 0.45 else max(0.0, 1.0 - (dist - tol * 0.45) / (tol * 0.55))
                px[i] = max(0, min(255, round(r + (tr - cur_r) * w_blend)))
                px[i + 1] = max(0, min(255, round(g + (tg - cur_g) * w_blend)))
                px[i + 2] = max(0, min(255, round(b + (tb - cur_b) * w_blend)))
        rgb = Image.frombytes('RGB', (w, h), bytes(px))

    if rgb.size != (canvas_size, canvas_size):
        rgb = rgb.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
    if apply_clarity:
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.0, percent=32, threshold=4))
    return rgb.convert('RGBA')


def verify_direct_studio_image(
    image: Image.Image,
    *,
    min_side: int = 640,
    min_sharpness: float = 2.2,
) -> tuple[bool, dict[str, Any]]:
    """Verify resolution, dynamic range, and sharpness of a direct studio background render (no cutout)."""
    w, h = image.size
    small = image.convert('L').resize((256, 256), Image.Resampling.LANCZOS)
    l_px = small.tobytes()
    grad_sum = 0.0
    grad_cnt = 0
    for y in range(255):
        row = y * 256
        for x in range(255):
            idx = row + x
            grad_sum += abs(l_px[idx + 1] - l_px[idx]) + abs(l_px[idx + 256] - l_px[idx])
            grad_cnt += 1
    sharpness = round(grad_sum / max(1, grad_cnt), 3)
    mean_luma = sum(l_px) / len(l_px)
    luma_std = math.sqrt(sum((v - mean_luma) ** 2 for v in l_px) / len(l_px))
    reasons: list[str] = []
    if min(w, h) < min_side:
        reasons.append('low_foreground_resolution')
    if sharpness < min_sharpness:
        reasons.append('blurry_foreground')
    if luma_std < 6.0:
        reasons.append('flat_blank_render')
    metrics = {
        'fg_width': w,
        'fg_height': h,
        'fg_max_side': max(w, h),
        'fg_min_side': min(w, h),
        'upscale_ratio': 1.0,
        'sharpness': sharpness,
        'fg_mean_luma': round(mean_luma, 2),
        'fg_luma_std': round(luma_std, 2),
        'max_border_clip': 0.0,
        'clipped_edges': 0,
        'halo_fringe_ratio': 0.0,
        'reasons': reasons,
    }
    return not reasons, metrics


def normalize_hex_color(raw_hex: str | None) -> str:
    """Return normalized '#RRGGBB' hex string or '' when invalid."""
    cleaned = str(raw_hex or '').strip().lstrip('#')
    if len(cleaned) == 6 and all(ch in '0123456789abcdefABCDEF' for ch in cleaned):
        return f'#{cleaned.upper()}'
    return ''


def parse_hex_color(raw_hex: str | None) -> tuple[int, int, int] | None:
    """Parse '#RRGGBB' hex color into an (R, G, B) tuple, or None when invalid."""
    hx = normalize_hex_color(raw_hex)
    if not hx:
        return None
    return (int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16))


def resolve_world_background(category: str | None = None, background_hex: str | None = None) -> str | None:
    """Resolve explicit hex color or FLUXIXO site category pastel color, returning None if unmapped."""
    explicit = normalize_hex_color(background_hex)
    if explicit:
        return explicit
    cat = str(category or '').strip()
    return WORLD_BACKGROUNDS.get(cat)


def _is_colored_backdrop(bg_rgb: tuple[int, int, int]) -> bool:
    return min(bg_rgb) < 238 or (max(bg_rgb) - min(bg_rgb)) >= 14


def _estimate_studio_backdrop(
    rgb: Image.Image,
    *,
    target_bg_rgb: tuple[int, int, int] | None = None,
) -> tuple[int, int, int]:
    """Estimate studio backdrop RGB from border pixels, supporting white or site-colored studio sweeps."""
    w, h = rgb.size
    raw = rgb.tobytes()
    samples: list[tuple[int, int, int]] = []
    bright_rs: list[int] = []
    bright_gs: list[int] = []
    bright_bs: list[int] = []

    def _collect(idx: int) -> None:
        off = idx * 3
        r, g, b = raw[off], raw[off + 1], raw[off + 2]
        samples.append((r, g, b))
        if min(r, g, b) >= 215 and max(r, g, b) - min(r, g, b) <= 22:
            bright_rs.append(r)
            bright_gs.append(g)
            bright_bs.append(b)

    for x in range(w):
        _collect(x)
        if h > 1:
            _collect((h - 1) * w + x)
    for y in range(1, h - 1):
        _collect(y * w)
        if w > 1:
            _collect(y * w + w - 1)

    if target_bg_rgb is not None and _is_colored_backdrop(target_bg_rgb):
        tr, tg, tb = target_bg_rgb
        near = [c for c in samples if (c[0] - tr) ** 2 + (c[1] - tg) ** 2 + (c[2] - tb) ** 2 <= 62 * 62]
        pool = near or samples
        rs = sorted(c[0] for c in pool)
        gs = sorted(c[1] for c in pool)
        bs = sorted(c[2] for c in pool)
        mid = len(pool) // 2
        return (rs[mid], gs[mid], bs[mid]) if pool else target_bg_rgb

    if bright_rs and len(bright_rs) >= len(samples) * 0.45:
        bright_rs.sort()
        bright_gs.sort()
        bright_bs.sort()
        mid = len(bright_rs) // 2
        return (bright_rs[mid], bright_gs[mid], bright_bs[mid])

    # Auto-detect colored pastel studio sweeps by sampling corner consensus.
    corners = [
        rgb.getpixel((x, y))
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
    ]
    if corners and min(min(c) for c in corners) >= 150:
        cr = sorted(c[0] for c in corners)[len(corners) // 2]
        cg = sorted(c[1] for c in corners)[len(corners) // 2]
        cb = sorted(c[2] for c in corners)[len(corners) // 2]
        matching = sum(
            1 for c in samples
            if (c[0] - cr) ** 2 + (c[1] - cg) ** 2 + (c[2] - cb) ** 2 <= 32 * 32
        )
        if matching >= len(samples) * 0.45:
            return (cr, cg, cb)

    return (255, 255, 255)


def _flood_fill_background(cand_bytes: bytes, w: int, h: int) -> bytearray:
    """4-connected flood-fill from image borders; returns fg mask (0=background, 255=foreground)."""
    total = w * h
    fg = bytearray(b'\xff' * total)
    stack: list[int] = []

    def _seed(idx: int) -> None:
        if cand_bytes[idx] and fg[idx]:
            fg[idx] = 0
            stack.append(idx)

    for x in range(w):
        _seed(x)
        _seed((h - 1) * w + x)
    for y in range(1, h - 1):
        _seed(y * w)
        _seed(y * w + w - 1)

    while stack:
        idx = stack.pop()
        x = idx % w
        if x > 0:
            n = idx - 1
            if cand_bytes[n] and fg[n]:
                fg[n] = 0
                stack.append(n)
        if x + 1 < w:
            n = idx + 1
            if cand_bytes[n] and fg[n]:
                fg[n] = 0
                stack.append(n)
        if idx >= w:
            n = idx - w
            if cand_bytes[n] and fg[n]:
                fg[n] = 0
                stack.append(n)
        if idx + w < total:
            n = idx + w
            if cand_bytes[n] and fg[n]:
                fg[n] = 0
                stack.append(n)
    return fg


def _decontaminate_rim_pixel(
    rgb_out: bytearray,
    idx: int,
    alpha_val: int,
    bg_rgb: tuple[int, int, int],
) -> None:
    """Recover true edge foreground color by unmixing studio backdrop from partial alpha."""
    af = alpha_val / 255.0
    if af < 0.15 or af >= 1.0:
        return
    off = idx * 3
    inv = 1.0 - af
    rgb_out[off] = max(0, min(255, round((rgb_out[off] - inv * bg_rgb[0]) / af)))
    rgb_out[off + 1] = max(0, min(255, round((rgb_out[off + 1] - inv * bg_rgb[1]) / af)))
    rgb_out[off + 2] = max(0, min(255, round((rgb_out[off + 2] - inv * bg_rgb[2]) / af)))


def _build_colored_bg_candidates(raw_rgb: bytes, total: int, bg_rgb: tuple[int, int, int]) -> tuple[bytes, bytes]:
    """Return (flood_candidates, euclidean_dist_u8) for a colored pastel studio backdrop and its soft shadows."""
    bg_r, bg_g, bg_b = bg_rgb
    bg_sum = max(1, bg_r + bg_g + bg_b)
    bg_rn, bg_gn, bg_bn = bg_r / bg_sum, bg_g / bg_sum, bg_b / bg_sum
    bg_sat = max(bg_r, bg_g, bg_b) - min(bg_r, bg_g, bg_b)
    min_shadow_sum = max(320, round(bg_sum * 0.62))
    max_shadow_sum = bg_sum + 28
    cand = bytearray(total)
    dist_u8 = bytearray(total)

    for i in range(total):
        off = i * 3
        r, g, b = raw_rgb[off], raw_rgb[off + 1], raw_rgb[off + 2]
        dr, dg, db = r - bg_r, g - bg_g, b - bg_b
        d2 = dr * dr + dg * dg + db * db
        dist_u8[i] = min(255, round(math.sqrt(d2)))
        if d2 <= 28 * 28:
            cand[i] = 255
            continue
        if bg_sat >= 16:
            s = r + g + b
            if min_shadow_sum <= s <= max_shadow_sum:
                rn, gn, bn = r / s, g / s, b / s
                if abs(rn - bg_rn) + abs(gn - bg_gn) + abs(bn - bg_bn) <= 0.030:
                    cand[i] = 255
    return bytes(cand), bytes(dist_u8)


def _clear_enclosed_bg_holes(
    fg: bytearray,
    raw_rgb: bytes,
    w: int,
    h: int,
    bg_rgb: tuple[int, int, int],
    *,
    hole_dist_sq: int = 24 * 24,
    min_hole_pixels: int = 36,
) -> None:
    """Clear enclosed background pockets (e.g., handle or strap loops) that match a colored studio backdrop."""
    bg_r, bg_g, bg_b = bg_rgb
    total = w * h
    visited = bytearray(total)
    for start in range(total):
        if fg[start] == 0 or visited[start]:
            continue
        off = start * 3
        dr, dg, db = raw_rgb[off] - bg_r, raw_rgb[off + 1] - bg_g, raw_rgb[off + 2] - bg_b
        if dr * dr + dg * dg + db * db > hole_dist_sq:
            continue
        comp = [start]
        visited[start] = 1
        stack = [start]
        while stack:
            idx = stack.pop()
            x = idx % w
            neighbors = []
            if x > 0:
                neighbors.append(idx - 1)
            if x + 1 < w:
                neighbors.append(idx + 1)
            if idx >= w:
                neighbors.append(idx - w)
            if idx + w < total:
                neighbors.append(idx + w)
            for ni in neighbors:
                if fg[ni] and not visited[ni]:
                    noff = ni * 3
                    ndr, ndg, ndb = raw_rgb[noff] - bg_r, raw_rgb[noff + 1] - bg_g, raw_rgb[noff + 2] - bg_b
                    if ndr * ndr + ndg * ndg + ndb * ndb <= hole_dist_sq:
                        visited[ni] = 1
                        comp.append(ni)
                        stack.append(ni)
        if len(comp) >= min_hole_pixels:
            for ci in comp:
                fg[ci] = 0


def extract_isolated_studio_alpha(
    image: Image.Image,
    *,
    background_hex: str | None = None,
) -> Image.Image:
    """Extract crisp RGBA cutout from a white OR colored-world studio image without rembg or numpy."""
    target_bg_rgb = parse_hex_color(background_hex)
    if 'A' in image.getbands():
        rgba_in = image.convert('RGBA')
        fill_rgb = target_bg_rgb or (255, 255, 255)
        solid_bg = Image.new('RGBA', rgba_in.size, (*fill_rgb, 255))
        rgb = Image.alpha_composite(solid_bg, rgba_in).convert('RGB')
    else:
        rgb = image.convert('RGB')

    w, h = rgb.size
    if w < 2 or h < 2:
        return rgb.convert('RGBA')

    total = w * h
    bg_rgb = _estimate_studio_backdrop(rgb, target_bg_rgb=target_bg_rgb)
    bg_r, bg_g, bg_b = bg_rgb
    bg_colored = _is_colored_backdrop(bg_rgb)
    raw_rgb = rgb.tobytes()

    r_ch, g_ch, b_ch = rgb.split()
    mn_ch = ImageChops.darker(ImageChops.darker(r_ch, g_ch), b_ch)
    mx_ch = ImageChops.lighter(ImageChops.lighter(r_ch, g_ch), b_ch)
    chroma_ch = ImageChops.subtract(mx_ch, mn_ch)
    bg_dist_ch = ImageChops.lighter(
        ImageChops.lighter(
            ImageChops.difference(r_ch, Image.new('L', (w, h), bg_r)),
            ImageChops.difference(g_ch, Image.new('L', (w, h), bg_g)),
        ),
        ImageChops.difference(b_ch, Image.new('L', (w, h), bg_b)),
    )

    if bg_colored:
        cand_bytes, euc_dist_bytes = _build_colored_bg_candidates(raw_rgb, total, bg_rgb)
        alpha_out = bytearray(cand_bytes)
        # Seed border ring (outer 4px collar) so 1px JPEG/border edge lines cannot seal off flood fill.
        seeded = bytearray(b'\xff' * total)
        stack: list[int] = []
        for y in range(h):
            is_top_bot = y < 4 or y >= h - 4
            row_off = y * w
            for x in range(w):
                if is_top_bot or x < 4 or x >= w - 4:
                    idx = row_off + x
                    if euc_dist_bytes[idx] <= 34:
                        seeded[idx] = 0
                        stack.append(idx)
        while stack:
            idx = stack.pop()
            x = idx % w
            if x > 0 and seeded[idx - 1] and alpha_out[idx - 1]:
                seeded[idx - 1] = 0
                stack.append(idx - 1)
            if x + 1 < w and seeded[idx + 1] and alpha_out[idx + 1]:
                seeded[idx + 1] = 0
                stack.append(idx + 1)
            if idx >= w and seeded[idx - w] and alpha_out[idx - w]:
                seeded[idx - w] = 0
                stack.append(idx - w)
            if idx + w < total and seeded[idx + w] and alpha_out[idx + w]:
                seeded[idx + w] = 0
                stack.append(idx + w)
        alpha_out = seeded
        _clear_enclosed_bg_holes(alpha_out, raw_rgb, w, h, bg_rgb)
        # Clear isolated tiny perimeter slivers (e.g. 1-2px AI border lines < 180px touching frame edges).
        visited_s = bytearray(total)
        for y in range(h):
            is_edge_y = y < 6 or y >= h - 6
            row_off = y * w
            for x in range(w):
                if not (is_edge_y or x < 6 or x >= w - 6):
                    continue
                s_idx = row_off + x
                if not alpha_out[s_idx] or visited_s[s_idx]:
                    continue
                comp = [s_idx]
                visited_s[s_idx] = 1
                stk = [s_idx]
                while stk:
                    ci = stk.pop()
                    cx = ci % w
                    for ni in (
                        (ci - 1 if cx > 0 else -1),
                        (ci + 1 if cx + 1 < w else -1),
                        (ci - w if ci >= w else -1),
                        (ci + w if ci + w < total else -1),
                    ):
                        if ni >= 0 and alpha_out[ni] and not visited_s[ni]:
                            visited_s[ni] = 1
                            comp.append(ni)
                            stk.append(ni)
                            if len(comp) > 220:
                                stk.clear()
                                break
                if len(comp) <= 220:
                    for ci in comp:
                        alpha_out[ci] = 0
        pure_white_bg = b'\x00' * total
    else:
        cand_mask = ImageChops.darker(
            mn_ch.point(lambda v: 255 if v >= 236 else 0),
            ImageChops.darker(
                chroma_ch.point(lambda v: 255 if v <= 12 else 0),
                bg_dist_ch.point(lambda v: 255 if v <= 20 else 0),
            ),
        )
        pure_white_bg = cand_mask.tobytes()
        alpha_out = _flood_fill_background(pure_white_bg, w, h)
        euc_dist_bytes = bg_dist_ch.tobytes()

    # When neural salient segmentation (rembg) is available on full-resolution (>=960px) studio renders,
    # use U2Net as outer shadow cleaner on white backdrops, and intersect cleanly with colored-hole masks.
    import sys as _sys
    used_rembg = False
    if min(w, h) >= 960 and _sys.modules.get('rembg', True) is not None and os.environ.get('FLUXIXO_DISABLE_REMBG_REFINE') != '1':
        try:
            from rembg import remove as _rembg_remove, new_session as _new_session
            global _STUDIO_REMBG_SESSION
            if '_STUDIO_REMBG_SESSION' not in globals() or _STUDIO_REMBG_SESSION is None:
                _STUDIO_REMBG_SESSION = _new_session('u2net')
            rem_a = _rembg_remove(rgb, session=_STUDIO_REMBG_SESSION).convert('RGBA').getchannel('A').tobytes()
            fg_pixels = sum(1 for v in rem_a if v >= 128)
            if fg_pixels >= total * 0.04:
                if bg_colored:
                    alpha_out = bytearray(
                        0 if (
                            alpha_out[i] == 0
                            or (rem_a[i] < 24 and euc_dist_bytes[i] <= 98 and (raw_rgb[i * 3] + raw_rgb[i * 3 + 1] + raw_rgb[i * 3 + 2]) >= 280)
                        ) else alpha_out[i]
                        for i in range(total)
                    )
                else:
                    alpha_out = bytearray(
                        0 if (
                            alpha_out[i] == 0
                            or rem_a[i] < 24
                            or (rem_a[i] < 210 and pure_white_bg[i])
                        ) else (255 if rem_a[i] >= 96 and not pure_white_bg[i] else rem_a[i])
                        for i in range(total)
                    )
                used_rembg = True
        except Exception:
            pass

    chroma_bytes = chroma_ch.tobytes()
    dist_bytes = euc_dist_bytes if bg_colored else bg_dist_ch.tobytes()
    rgb_out = bytearray(raw_rgb)

    # Exterior boundary passes smooth AA edges and strip background halos without piercing closed outlines.
    soft_lo, soft_hi = (16.0, 44.0) if bg_colored else ((12.0, 48.0) if not used_rembg else (16.0, 52.0))
    span = soft_hi - soft_lo
    decontam_indices: set[int] = set()
    for _ in range(2):
        hard_bin = Image.frombytes('L', (w, h), bytes(255 if a > 0 else 0 for a in alpha_out))
        ring = ImageChops.subtract(hard_bin, hard_bin.filter(ImageFilter.MinFilter(3)))
        bbox = ring.getbbox()
        if not bbox:
            break
        ring_bytes = ring.tobytes()
        changed = False
        for y in range(bbox[1], bbox[3]):
            row_start = y * w
            for idx in range(row_start + bbox[0], row_start + bbox[2]):
                if not ring_bytes[idx]:
                    continue
                strength = float(dist_bytes[idx]) if bg_colored else max(float(dist_bytes[idx]), float(chroma_bytes[idx]) * 2.4)
                if strength <= soft_lo:
                    if alpha_out[idx] != 0:
                        alpha_out[idx] = 0
                        decontam_indices.discard(idx)
                        changed = True
                elif strength < soft_hi:
                    a = round(255.0 * (strength - soft_lo) / span)
                    if a < alpha_out[idx]:
                        alpha_out[idx] = a
                    decontam_indices.add(idx)
        if not changed:
            break

    for idx in decontam_indices:
        _decontaminate_rim_pixel(rgb_out, idx, alpha_out[idx], bg_rgb)

    out = Image.frombytes('RGB', (w, h), bytes(rgb_out)).convert('RGBA')
    out.putalpha(Image.frombytes('L', (w, h), bytes(alpha_out)))
    return out


def resolve_cloudflare_ai_token(explicit_token: str | None = None) -> tuple[str, str]:
    """Resolve Cloudflare Workers AI bearer token & User-Agent, or ('', '') if unavailable."""
    if isinstance(explicit_token, str) and explicit_token.strip():
        tok = explicit_token.strip()
        ua = WRANGLER_OAUTH_USER_AGENT if tok.startswith('cfoat_') else 'fluxixo-image-studio/1.0'
        return tok, ua

    for env_name in ('CLOUDFLARE_AI_TOKEN', 'CLOUDFLARE_API_TOKEN'):
        env_val = os.environ.get(env_name)
        if isinstance(env_val, str) and env_val.strip():
            tok = env_val.strip()
            ua = WRANGLER_OAUTH_USER_AGENT if tok.startswith('cfoat_') else 'fluxixo-image-studio/1.0'
            return tok, ua

    candidates: list[Path] = []
    appdata = (os.environ.get('APPDATA') or '').strip()
    if appdata:
        candidates.append(Path(appdata) / 'xdg.config' / '.wrangler' / 'config' / 'default.toml')
    xdg_home = (os.environ.get('XDG_CONFIG_HOME') or '').strip()
    if xdg_home:
        candidates.append(Path(xdg_home) / '.wrangler' / 'config' / 'default.toml')

    for cfg_path in candidates:
        try:
            if not cfg_path.is_file():
                continue
            raw_text = cfg_path.read_text(encoding='utf-8')
        except OSError:
            continue
        oauth_token = ''
        exp_str = ''
        if tomllib is not None:
            try:
                parsed = tomllib.loads(raw_text)
                val = parsed.get('oauth_token')
                if isinstance(val, str):
                    oauth_token = val.strip()
                exp_val = parsed.get('expiration_time')
                if isinstance(exp_val, str):
                    exp_str = exp_val.strip()
            except Exception:
                oauth_token = ''
        if not oauth_token:
            match = re.search(r"""^\s*oauth_token\s*=\s*(['"])(.+?)\1""", raw_text, re.MULTILINE)
            if match:
                oauth_token = match.group(2).strip()
        if not exp_str:
            exp_match = re.search(r"""^\s*expiration_time\s*=\s*(['"])(.+?)\1""", raw_text, re.MULTILINE)
            if exp_match:
                exp_str = exp_match.group(2).strip()
        if exp_str:
            try:
                from datetime import datetime, timedelta, timezone
                exp_dt = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                if exp_dt <= datetime.now(timezone.utc) + timedelta(minutes=2):
                    import subprocess
                    subprocess.run(
                        ['npx', 'wrangler', 'whoami'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=15,
                        shell=(os.name == 'nt'),
                    )
                    raw_text = cfg_path.read_text(encoding='utf-8')
                    match = re.search(r"""^\s*oauth_token\s*=\s*(['"])(.+?)\1""", raw_text, re.MULTILINE)
                    if match:
                        oauth_token = match.group(2).strip()
            except Exception:
                pass
        if oauth_token:
            return oauth_token, WRANGLER_OAUTH_USER_AGENT

    return '', ''


def _encode_reference_image(reference_image: Image.Image | bytes, *, max_side: int = 448) -> bytes:
    """Normalize PIL Image or image bytes to PNG bytes (<512x512 required by Cloudflare FLUX.2 input_image_0)."""
    if isinstance(reference_image, Image.Image):
        img = reference_image
        if 'A' in img.getbands():
            rgba = img.convert('RGBA')
            rgb = Image.alpha_composite(Image.new('RGBA', rgba.size, (255, 255, 255, 255)), rgba).convert('RGB')
        else:
            rgb = img.convert('RGB')
        if max(rgb.size) > max_side:
            rgb = rgb.copy()
            rgb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        buf = BytesIO()
        rgb.save(buf, format='PNG')
        return buf.getvalue()

    if isinstance(reference_image, (bytes, bytearray)):
        raw = bytes(reference_image)
        try:
            with Image.open(BytesIO(raw)) as img:
                img.load()
                return _encode_reference_image(img, max_side=max_side)
        except Exception:
            return raw

    raise TypeError('reference_image must be PIL.Image.Image, bytes, or None')


def _encode_reference_jpeg_base64(
    reference_image: Image.Image | bytes,
    *,
    max_side: int = 448,
    quality: int = 86,
) -> str:
    """Normalize PIL Image or bytes to base64 JPEG suitable for Gemini Multimodal Vision."""
    if isinstance(reference_image, Image.Image):
        img = reference_image
        if 'A' in img.getbands():
            rgba = img.convert('RGBA')
            rgb = Image.alpha_composite(Image.new('RGBA', rgba.size, (255, 255, 255, 255)), rgba).convert('RGB')
        else:
            rgb = img.convert('RGB')
    elif isinstance(reference_image, (bytes, bytearray)):
        with Image.open(BytesIO(bytes(reference_image))) as opened:
            opened.load()
            return _encode_reference_jpeg_base64(opened, max_side=max_side, quality=quality)
    else:
        raise TypeError('reference_image must be PIL.Image.Image, bytes, or None')

    rgb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = BytesIO()
    rgb.save(buf, format='JPEG', quality=quality)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def _encode_multipart_form(
    fields: dict[str, str],
    files: dict[str, tuple[str, str, bytes]] | None = None,
) -> tuple[bytes, str]:
    boundary = f'----FluxixoBoundary{uuid.uuid4().hex}'
    body = bytearray()
    for name, value in fields.items():
        body.extend(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('utf-8')
        )
    for name, (filename, content_type, data) in (files or {}).items():
        body.extend(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f'Content-Type: {content_type}\r\n\r\n'.encode('utf-8')
        )
        body.extend(data)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    return bytes(body), f'multipart/form-data; boundary={boundary}'


def _append_query_param(url: str, key: str, value: str) -> str:
    parts = urllib.parse.urlsplit(url)
    pairs = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if k != key]
    pairs.append((key, value))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(pairs), parts.fragment))


def _resolve_worker_transport_url() -> str:
    """Return Cloudflare Worker URL when configured via env URL or worker transport."""
    transport = os.environ.get('FLUXIXO_AI_TRANSPORT', '').strip().lower()
    if transport in ('direct', 'none', 'disabled', 'off'):
        return ''
    explicit_url = os.environ.get('CLOUDFLARE_AUTOPILOT_URL')
    if explicit_url is not None:
        cleaned = explicit_url.strip().rstrip('/')
        if cleaned:
            return cleaned
        if not transport:
            return ''
    if transport in ('worker', 'cloudflare_worker', 'autopilot'):
        return DEFAULT_CLOUDFLARE_AUTOPILOT_URL.rstrip('/')
    return ''


def _decode_worker_image(raw_bytes: bytes, content_type: str) -> Image.Image:
    ct = (content_type or '').lower()
    if 'json' in ct or raw_bytes.lstrip().startswith(b'{'):
        payload = json.loads(raw_bytes.decode('utf-8'))
        if isinstance(payload, dict) and (payload.get('success') is False or payload.get('ok') is False):
            raise RuntimeError(f'worker_ai_error:{payload.get("error") or payload.get("errors")}')
        result = payload.get('result') if isinstance(payload, dict) else None
        b64 = result.get('image') if isinstance(result, dict) else (payload.get('image') if isinstance(payload, dict) else None)
        if not isinstance(b64, str) or not b64.strip():
            raise RuntimeError('worker_ai_missing_image')
        text = b64.strip()
        if text.startswith('data:') and ',' in text:
            text = text.split(',', 1)[1]
        img_bytes = base64.b64decode(text)
    else:
        img_bytes = raw_bytes

    with Image.open(BytesIO(img_bytes)) as img:
        img.load()
        return img.copy()


def _post_autopilot_cutout(
    autopilot_url: str,
    mp_body: bytes,
    mp_ct: str,
    timeout: float,
    *,
    provider: str = 'cloudflare',
) -> Image.Image:
    base = autopilot_url.rstrip('/')
    endpoint = base if base.endswith('/api/generate-cutout') else f'{base}/api/generate-cutout'
    if provider:
        endpoint = _append_query_param(endpoint, 'provider', provider)
    headers = {
        'User-Agent': 'fluxixo-image-studio/1.0',
        'Content-Type': mp_ct,
    }
    sync_token = os.environ.get('AUTOPILOT_SYNC_TOKEN', '').strip()
    if sync_token:
        headers['Authorization'] = f'Bearer {sync_token}'
    req = urllib.request.Request(endpoint, data=mp_body, method='POST', headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        resp_ct = resp.headers.get('Content-Type', '') if resp.headers else ''
    return _decode_worker_image(raw, resp_ct)


def _post_json_request(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    req_headers = {
        'User-Agent': 'fluxixo-image-studio/1.0',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        **headers,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
        headers=req_headers,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8', 'replace'))


def _resolve_cf_models(
    requested: str | None,
    env_var: str,
    fallback_models: tuple[str, ...],
) -> list[str]:
    candidates: list[str] = []
    for raw_source in (requested, os.environ.get(env_var, '')):
        text = str(raw_source or '').strip()
        if not text:
            continue
        for part in text.split(','):
            name = part.strip().lstrip('/')
            if name and name.startswith('@cf/') and name not in candidates:
                candidates.append(name)
    for fb in fallback_models:
        if fb not in candidates:
            candidates.append(fb)
    return candidates


def _extract_cf_text_response(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ''
    result = payload.get('result') if isinstance(payload.get('result'), dict) else payload
    raw_resp = result.get('response') if isinstance(result, dict) else None
    if isinstance(raw_resp, str) and raw_resp.strip():
        return re.sub(r'<think>[\s\S]*?</think>', '', raw_resp, flags=re.IGNORECASE).strip()
    choices = (result.get('choices') if isinstance(result, dict) else None) or payload.get('choices')
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        msg = choices[0].get('message') or {}
        content = msg.get('content', '') if isinstance(msg, dict) else ''
        if isinstance(content, str) and content.strip():
            return re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.IGNORECASE).strip()
    return ''


def _prefer_worker_transport(worker_url: str) -> bool:
    """Return True when Cloudflare Worker transport should be tried first."""
    return bool(worker_url) and os.environ.get('FLUXIXO_AI_TRANSPORT', '').strip().lower() in (
        '', 'autopilot', 'cloudflare_worker', 'worker',
    )


def describe_product_from_reference(
    reference_image: Image.Image | bytes | None,
    *,
    product_title: str = '',
    api_key: str | None = None,
    vision_model: str | None = None,
    timeout: float = 45.0,
    account_id: str = DEFAULT_CLOUDFLARE_ACCOUNT_ID,
    token: str | None = None,
) -> str:
    """Inspect product via Cloudflare Workers AI Vision (Worker first, direct CF/GitHub Models fallback) — never Google/Gemini."""
    del api_key
    if reference_image is None:
        return ''

    worker_url = _resolve_worker_transport_url()
    cf_token, cf_ua = resolve_cloudflare_ai_token(token)
    gh_token = resolve_github_models_token()
    if not worker_url and not cf_token and not gh_token:
        return ''

    try:
        b64_jpg = _encode_reference_jpeg_base64(reference_image)
    except Exception:
        return ''

    hint = ' '.join(str(product_title or '').split())[:160]
    vision_prompt = (
        f'Describe ONLY the standalone physical product in this AliExpress image{f" ({hint})" if hint else ""} '
        'in 2-3 concise visual sentences for a studio product photographer: overall silhouette, carry handle/strap or antenna if present, casing materials, colors, screen/controls, '
        'and what its active powered-on working effect looks like when switched on (such as LED light mask glow, beam, mist, spray, rotor spin, or glowing readout). '
        'CRITICAL: Describe ONLY the isolated object floating alone; NEVER mention rocks, tables, surfaces, backgrounds, '
        'inset thumbnails, collage boxes, overlaid promotional text, digits, price tags, or hands.'
    )

    def _describe_worker() -> str:
        if not worker_url:
            return ''
        endpoint = worker_url if worker_url.endswith('/api/describe-product') else f'{worker_url}/api/describe-product'
        endpoint = _append_query_param(endpoint, 'provider', 'cloudflare')
        sync_token = os.environ.get('AUTOPILOT_SYNC_TOKEN', '').strip()
        headers = {'Authorization': f'Bearer {sync_token}'} if sync_token else {}
        worker_payload: dict[str, Any] = {
            'prompt': hint,
            'title': hint,
            'image_base64': b64_jpg,
            'provider': 'cloudflare-workers-ai',
        }
        if vision_model and str(vision_model).strip().startswith('@cf/'):
            worker_payload['model'] = str(vision_model).strip()
        try:
            resp = _post_json_request(endpoint, worker_payload, headers, timeout)
        except Exception:
            return ''
        if not isinstance(resp, dict) or resp.get('ok') is False:
            return ''
        text = resp.get('visual_spec') or _extract_cf_text_response(resp)
        return ' '.join(str(text).split())[:550]

    def _describe_cf_direct() -> str:
        if not cf_token:
            return ''
        candidates = _resolve_cf_models(vision_model, 'FLUXIXO_CF_VISION_MODEL', CF_VISION_FALLBACK_MODELS)
        headers = {'Authorization': f'Bearer {cf_token}', 'User-Agent': cf_ua or 'fluxixo-image-studio/1.0'}
        data_uri = f'data:image/jpeg;base64,{b64_jpg}'
        payload = {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': vision_prompt},
                        {'type': 'image_url', 'image_url': {'url': data_uri}},
                    ],
                }
            ],
            'temperature': 0.15,
            'max_tokens': 400,
        }
        for cand_model in candidates:
            url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{cand_model}'
            try:
                resp = _post_json_request(url, payload, headers, timeout)
                text = _extract_cf_text_response(resp)
                if text.strip():
                    return ' '.join(text.split())[:550]
            except Exception:
                continue
        return ''

    def _describe_github() -> str:
        if not gh_token:
            return ''
        headers = {
            'Authorization': f'Bearer {gh_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        data_uri = f'data:image/jpeg;base64,{b64_jpg}'
        for cand_model in GITHUB_VISION_MODELS:
            payload = {
                'model': cand_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': vision_prompt},
                            {'type': 'image_url', 'image_url': {'url': data_uri}},
                        ],
                    }
                ],
                'temperature': 0.15,
                'max_tokens': 350,
            }
            try:
                resp = _post_json_request(GITHUB_MODELS_URL, payload, headers, timeout)
                text = _extract_cf_text_response(resp)
                if text.strip():
                    return ' '.join(text.split())[:550]
            except Exception:
                continue
        return ''

    for fn in (_describe_worker, _describe_cf_direct, _describe_github):
        out = fn()
        if out:
            return out
    return ''


def build_studio_prompt(
    prompt: str,
    *,
    angle: str = 'hero front three-quarter studio view',
    background_hex: str | None = None,
    visual_spec: str = '',
) -> str:
    """Compose a reference-guided, text-free, zero-shadow Google AI Studio prompt for the target site backdrop."""
    subject = ' '.join(str(prompt or '').split())[:220] or 'compact precision product'
    view_angle = ' '.join(str(angle or 'hero front three-quarter studio view').split())[:140]
    spec = ' '.join(str(visual_spec or '').split())[:460]
    item_clause = f'{subject} ({spec})' if spec else subject
    lower_angle = view_angle.lower()
    is_effect_slot = any(k in lower_angle for k in ('close-up', 'detail', 'effect', 'action'))
    is_secondary_slot = ('45-degree' in lower_angle or 'isometric' in lower_angle or 'side' in lower_angle or 'rear' in lower_angle)

    target_hex = normalize_hex_color(background_hex)
    if target_hex:
        bg_clause = (
            f'floating weightless in mid-air centered against a completely flat uniform seamless solid pastel color void matching hex {target_hex} '
            'with generous clean border on all sides'
        )
    else:
        bg_clause = 'floating in mid-air centered on a pure flat #FFFFFF solid white background with generous white margin on all sides'

    if is_effect_slot:
        angle_directive = (
            f'{view_angle}, active powered-on functional demonstration macro showcasing the working effect in operation '
            '(vibrant illuminated LED/light/mask glow, laser beam, indicator readout, steam/airflow blades, or active working mechanism clearly visible and turned ON, '
            'noticeably different from the static turned-off front hero shot)'
        )
        lighting_clause = 'crisp dimensional studio rim lighting that accentuates active glowing lights, optical effects, and micro-details cleanly'
    elif is_secondary_slot:
        angle_directive = (
            f'{view_angle}, rotated 60-to-120 degrees to reveal the side profile, rear controls, charging port, straps, or underside mechanics rather than repeating the front view'
        )
        lighting_clause = 'even shadowless studio lighting'
    else:
        angle_directive = view_angle
        lighting_clause = 'even shadowless studio lighting'

    return (
        f'Ultra-clean commercial industrial design studio product photograph of ONLY the exact single standalone {item_clause} from the reference photo, '
        f'{angle_directive}, {bg_clause}, faithfully keeping its true real silhouette, carry strap/handle, knobs, and proportions without distortion, '
        'zero floor plane, zero tabletop, zero floor shadow, zero drop shadow, zero ground reflection, zero surface, zero pedestal, zero vignette, no frame borders, no edge lines, '
        f'{lighting_clause}, full uncropped object, crisp edge separation, '
        'strictly remove all external collage boxes, inset cards, promotional banners, seller badges, overlaid marketing text, Chinese characters, watermarks, hands, people, and pets'
    )


def _load_dpapi_secret(filename: str) -> str:
    try:
        from dpapi_store import load_credential
    except ImportError:
        tools_dir = str(Path(__file__).resolve().parents[1] / 'fluxixo_site' / 'tools')
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        try:
            from dpapi_store import load_credential
        except ImportError:
            return ''
    try:
        return (load_credential(filename) or '').strip()
    except Exception:
        return ''


def resolve_cloudflare_ai_token(explicit_token: str | None = None, *, local: bool = True) -> tuple[str, str]:
    """Resolve Cloudflare Workers AI bearer token & User-Agent from arg, env, DPAPI, or Wrangler OAuth."""
    if isinstance(explicit_token, str) and explicit_token.strip():
        tok = explicit_token.strip()
        ua = WRANGLER_OAUTH_USER_AGENT if tok.startswith('cfoat_') else 'fluxixo-image-studio/1.0'
        return tok, ua
    for env_name in ('CLOUDFLARE_AI_TOKEN', 'CLOUDFLARE_API_TOKEN'):
        env_val = os.environ.get(env_name, '').strip()
        if env_val:
            ua = WRANGLER_OAUTH_USER_AGENT if env_val.startswith('cfoat_') else 'fluxixo-image-studio/1.0'
            return env_val, ua
    if local:
        val = _load_dpapi_secret('cloudflare-token.dpapi')
        if val:
            ua = WRANGLER_OAUTH_USER_AGENT if val.startswith('cfoat_') else 'fluxixo-image-studio/1.0'
            return val, ua
    return '', ''


def resolve_github_models_token(explicit_token: str | None = None) -> str:
    """Resolve GitHub Models token (GITHUB_TOKEN / GH_TOKEN) when running in GitHub Actions or local CLI."""
    if isinstance(explicit_token, str) and explicit_token.strip():
        return explicit_token.strip()
    for env_name in ('GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_MODELS_TOKEN'):
        val = os.environ.get(env_name, '').strip()
        if val:
            return val
    return ''


def resolve_image_provider(
    provider: str | None = None,
    *,
    gemini_key: str = '',
    cf_token: str = '',
    autopilot_url: str = '',
) -> str:
    """Route studio image generation through Cloudflare Workers AI (never Google/Gemini)."""
    del provider, gemini_key, cf_token, autopilot_url
    return 'cloudflare'


def _post_cloudflare_direct_cutout(
    full_prompt: str,
    cf_token: str,
    cf_ua: str,
    *,
    account_id: str = DEFAULT_CLOUDFLARE_ACCOUNT_ID,
    ref_bytes: bytes | None = None,
    model: str | None = None,
    width: int = 1024,
    height: int = 1024,
    timeout: float = 60.0,
) -> Image.Image:
    candidates = _resolve_cf_models(model, 'FLUXIXO_CF_IMAGE_MODEL', CF_IMAGE_FALLBACK_MODELS)
    fields = {
        'prompt': full_prompt,
        'width': str(int(width)),
        'height': str(int(height)),
    }
    files = {'input_image_0': ('reference.png', 'image/png', ref_bytes)} if ref_bytes else None
    mp_body, mp_ct = _encode_multipart_form(fields, files)
    headers = {
        'Authorization': f'Bearer {cf_token}',
        'User-Agent': cf_ua or 'fluxixo-image-studio/1.0',
        'Content-Type': mp_ct,
    }
    last_exc: Exception | None = None
    for cand_model in candidates:
        url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{cand_model}'
        try:
            req = urllib.request.Request(url, data=mp_body, method='POST', headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                resp_ct = resp.headers.get('Content-Type', '') if resp.headers else ''
            return _decode_worker_image(raw, resp_ct)
        except Exception as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError('cloudflare_image_generation_failed')


def generate_studio_cutout(
    prompt: str,
    reference_image: Image.Image | bytes | None = None,
    *,
    angle: str = 'hero front three-quarter studio view',
    model: str | None = None,
    account_id: str = DEFAULT_CLOUDFLARE_ACCOUNT_ID,
    token: str | None = None,
    width: int = 1024,
    height: int = 1024,
    timeout: float = 45.0,
    background_hex: str | None = None,
    category: str | None = None,
    visual_spec: str | None = None,
    use_vision: bool = False,
    provider: str | None = None,
    gemini_api_key: str | None = None,
    aspect_ratio: str = '1:1',
    image_size: str | None = None,
    cutout_alpha: bool | None = None,
) -> Image.Image:
    """Generate a studio product image via Cloudflare Workers AI (FLUX.2 Klein 9B/4B) and master to 1254x1254."""
    del provider, gemini_api_key, aspect_ratio, image_size
    ref_bytes = _encode_reference_image(reference_image, max_side=448) if reference_image is not None else None
    target_hex = resolve_world_background(category, background_hex)
    resolved_spec = (visual_spec or '').strip()

    worker_url = _resolve_worker_transport_url()
    cf_token, cf_ua = resolve_cloudflare_ai_token(token, local=not bool(worker_url))
    if not worker_url and not cf_token:
        raise RuntimeError('cloudflare_ai_unavailable')

    if use_vision and not resolved_spec and reference_image is not None:
        resolved_spec = describe_product_from_reference(
            reference_image,
            product_title=prompt,
            account_id=account_id,
            token=token,
            timeout=min(25.0, float(timeout)),
        )

    full_prompt = build_studio_prompt(
        prompt,
        angle=angle,
        background_hex=target_hex,
        visual_spec=resolved_spec,
    )

    def _cutout_worker() -> Image.Image:
        attach_ref = ref_bytes is not None and os.environ.get('FLUXIXO_SEND_RAW_REF', '1') != '0'
        fields = {
            'prompt': full_prompt,
            'provider': 'cloudflare-workers-ai',
            'width': str(int(width)),
            'height': str(int(height)),
        }
        if target_hex:
            fields['background_hex'] = target_hex
        if category:
            fields['category'] = str(category).strip()
        if resolved_spec:
            fields['visual_spec'] = resolved_spec
        safe_model = str(model or os.environ.get('FLUXIXO_CF_IMAGE_MODEL', '') or '').strip().lstrip('/')
        if safe_model.startswith('@cf/'):
            fields['model'] = safe_model
        files = {'input_image_0': ('reference.png', 'image/png', ref_bytes)} if attach_ref else None
        mp_body, mp_ct = _encode_multipart_form(fields, files)
        return _post_autopilot_cutout(
            worker_url,
            mp_body,
            mp_ct,
            max(float(timeout), 60.0),
            provider='cloudflare',
        )

    def _cutout_direct() -> Image.Image:
        return _post_cloudflare_direct_cutout(
            full_prompt,
            cf_token,
            cf_ua,
            account_id=account_id,
            ref_bytes=ref_bytes,
            model=model,
            width=width,
            height=height,
            timeout=max(float(timeout), 60.0),
        )

    attempts = [(_cutout_worker, bool(worker_url)), (_cutout_direct, bool(cf_token))] if _prefer_worker_transport(worker_url) else [(_cutout_direct, bool(cf_token)), (_cutout_worker, bool(worker_url))]
    raw_img: Image.Image | None = None
    last_err: Exception | None = None
    for fn, enabled in attempts:
        if not enabled:
            continue
        try:
            raw_img = fn()
            break
        except Exception as exc:
            last_err = exc
    if raw_img is None:
        assert last_err is not None
        raise last_err

    if cutout_alpha is False:
        return compose_direct_studio_frame(
            raw_img,
            background_hex=target_hex or '#F3F0E9',
            canvas_size=1254,
            apply_clarity=True,
        )

    cutout = extract_isolated_studio_alpha(raw_img, background_hex=target_hex)
    if tight_alpha_bbox(cutout) is None:
        raise RuntimeError('generated_cutout_empty')

    return compose_studio_frame(
        cutout,
        canvas_size=1254,
        max_box=890,
        normalize_tonality=True,
        add_contact_shadow=False,
        apply_clarity=True,
    )
