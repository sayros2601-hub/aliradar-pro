"""Pure-Pillow perceptual image uniqueness (dHash/aHash) & FLUXIXO studio mastering.

Zero external runtime dependencies beyond Pillow + Python standard library so
lightweight CI jobs and offline tests import cleanly without rembg or numpy.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ALPHA_FLOOR = 24
TIGHT_BBOX_ALPHA = 20


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


def compose_studio_frame(
    cutout: Image.Image,
    *,
    canvas_size: int = 1254,
    max_box: int = 890,
    normalize_tonality: bool = True,
    add_contact_shadow: bool = True,
) -> Image.Image:
    """Clean, trim, contrast-balance, frame, and ground a transparent cutout on a 1254px canvas."""
    cleaned = clean_cutout_alpha(cutout)
    bbox = tight_alpha_bbox(cleaned, alpha_floor=TIGHT_BBOX_ALPHA)
    if bbox:
        cleaned = cleaned.crop(bbox)

    scale = min(max_box / max(1, cleaned.width), max_box / max(1, cleaned.height))
    fit = (max(1, round(cleaned.width * scale)), max(1, round(cleaned.height * scale)))
    placed = cleaned.resize(fit, Image.Resampling.LANCZOS)
    if normalize_tonality:
        placed = normalize_studio_contrast(placed)

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
