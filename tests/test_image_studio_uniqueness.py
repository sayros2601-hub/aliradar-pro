"""Tests for perceptual image uniqueness (dHash/aHash/RGB-dHash) & pure-Pillow studio mastering."""
from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw, ImageOps

from fluxixo_ai import autonomous, image_studio as ims

NOW = datetime(2026, 11, 12, 8, tzinfo=timezone.utc)


def _draw_cutout_a(canvas_size: tuple[int, int] = (720, 720)) -> Image.Image:
    img = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = canvas_size[0] // 2, canvas_size[1] // 2
    d.rounded_rectangle((cx - 180, cy - 190, cx + 160, cy + 190), radius=34, fill=(44, 58, 86, 255))
    # Strongly asymmetric left handle + bright copper accent on upper-left quadrant
    d.rounded_rectangle((cx - 245, cy - 120, cx - 155, cy + 95), radius=24, fill=(214, 138, 62, 255))
    # Bright lens/dial offset into right half for clear L-R chirality
    d.ellipse((cx + 10, cy - 115, cx + 135, cy + 10), fill=(235, 238, 244, 255))
    d.ellipse((cx + 35, cy - 90, cx + 110, cy - 15), fill=(22, 28, 42, 255))
    d.rectangle((cx - 130, cy + 75, cx + 25, cy + 150), fill=(195, 72, 66, 255))
    return img


def _draw_tall_cylinder_a() -> Image.Image:
    img = Image.new('RGBA', (800, 800), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((330, 60, 470, 740), radius=28, fill=(28, 38, 58, 255))
    d.rectangle((330, 60, 470, 175), fill=(218, 122, 54, 255))
    for y in range(210, 460, 55):
        d.rectangle((348, y, 452, y + 20), fill=(225, 228, 236, 255))
    d.ellipse((365, 555, 435, 625), fill=(72, 165, 210, 255))
    return img


def _draw_tall_cylinder_b() -> Image.Image:
    img = Image.new('RGBA', (800, 800), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((335, 70, 465, 730), radius=24, fill=(238, 230, 212, 255))
    d.ellipse((355, 130, 445, 220), fill=(36, 138, 92, 255))
    d.rectangle((335, 580, 465, 730), fill=(42, 40, 38, 255))
    d.line((365, 280, 365, 540), fill=(182, 58, 52, 255), width=14)
    return img


class ImageStudioUniquenessTests(unittest.TestCase):
    def test_perceptual_dedup_catches_reencode_rescale_padded_backdrop_and_mirror(self):
        base = _draw_cutout_a()
        base_hashes = ims.compute_perceptual_hashes(base)
        entry = {'id': 'prod-a', 'path': 'assets/images/prod-a.webp', 'kind': 'cutout', **base_hashes}

        buf_webp = io.BytesIO()
        base.save(buf_webp, format='WEBP', quality=70)
        buf_webp.seek(0)
        reencoded = Image.open(buf_webp).convert('RGBA')

        rescaled = base.resize((360, 360), Image.Resampling.LANCZOS)

        padded = Image.new('RGBA', (1100, 960), (0, 0, 0, 0))
        padded.paste(base, (190, 120))

        # Flatten onto different backdrops with cropped foreground region -> perceptual hash still matches
        bbox = ims.tight_alpha_bbox(base)
        cropped_fg = base.crop(bbox)
        on_cream = Image.alpha_composite(
            Image.new('RGBA', cropped_fg.size, (248, 244, 236, 255)),
            cropped_fg,
        ).convert('RGB')
        on_slate = Image.alpha_composite(
            Image.new('RGBA', cropped_fg.size, (236, 240, 246, 255)),
            cropped_fg,
        ).convert('RGB')

        for label, variant in (
            ('reencoded_webp70', reencoded),
            ('rescaled_360', rescaled),
            ('padded_canvas', padded),
            ('backdrop_cream', on_cream),
            ('backdrop_slate', on_slate),
        ):
            dup, hit = ims.is_perceptually_duplicate(ims.compute_perceptual_hashes(variant), [entry])
            self.assertTrue(dup, f'{label} was not caught as perceptual duplicate')
            self.assertEqual('prod-a', hit['id'])

        mirrored = ImageOps.mirror(base)
        dup_m, hit_m = ims.is_perceptually_duplicate(ims.compute_perceptual_hashes(mirrored), [entry])
        self.assertTrue(dup_m, 'horizontal mirror must be detected')
        self.assertEqual('mirror', hit_m['mode'])

    def test_distinct_tall_vertical_products_do_not_false_collide(self):
        cyl_a = _draw_tall_cylinder_a()
        cyl_b = _draw_tall_cylinder_b()
        h_a = ims.compute_perceptual_hashes(cyl_a)
        h_b = ims.compute_perceptual_hashes(cyl_b)

        dup, hit = ims.is_perceptually_duplicate(
            h_a,
            [{'id': 'cyl-b', 'path': 'assets/images/cyl-b.webp', 'kind': 'cutout', **h_b}],
        )
        self.assertFalse(dup, f'Distinct tall vertical silhouettes false-collided: {hit}')

    def test_clean_cutout_alpha_removes_faint_halo_and_decontaminates_edge(self):
        img = Image.new('RGBA', (120, 120), (0, 255, 0, 10))
        d = ImageDraw.Draw(img)
        # Semitransparent ring with green seller backdrop spill
        d.rectangle((26, 26, 94, 94), fill=(0, 220, 0, 170))
        # Solid red product interior
        d.rectangle((32, 32, 88, 88), fill=(210, 30, 30, 255))

        cleaned = ims.clean_cutout_alpha(img, alpha_floor=24, solid_alpha=215, feather_radius=0.5)
        self.assertEqual(0, cleaned.getpixel((5, 5))[3], 'faint alpha<24 noise must become 0')
        interior = cleaned.getpixel((60, 60))
        self.assertGreaterEqual(interior[3], 250)
        self.assertGreater(interior[0], interior[1])
        edge = cleaned.getpixel((28, 60))
        self.assertGreater(edge[0], edge[1], f'edge halo RGB must bleed interior red over green spill, got {edge}')

    def test_normalize_studio_contrast_preserves_alpha_and_enhances_washed_foreground(self):
        img = Image.new('RGBA', (160, 160), (15, 240, 30, 0))  # poison RGB in transparent pixels
        d = ImageDraw.Draw(img)
        for offset, shade in ((0, 70), (12, 115), (24, 155), (36, 185)):
            d.rectangle((30 + offset, 30 + offset, 130 - offset, 130 - offset), fill=(shade, shade + 4, shade - 4, 255))

        out = ims.normalize_studio_contrast(img)
        self.assertEqual(img.getchannel('A').tobytes(), out.getchannel('A').tobytes())
        dark_px = out.getpixel((34, 34))
        bright_px = out.getpixel((80, 80))
        self.assertLess(dark_px[0], 70, 'washed dark tone should deepen safely')
        self.assertGreater(bright_px[0], 185, 'washed highlight should lift without blowout')
        self.assertGreater(bright_px[0] - dark_px[0], 185 - 70, 'foreground tonal contrast span should widen')

    def test_compose_studio_frame_and_contact_shadow_bounds(self):
        cutout = _draw_cutout_a((600, 900))
        framed = ims.compose_studio_frame(cutout, canvas_size=1254, max_box=890)
        self.assertEqual('RGBA', framed.mode)
        self.assertEqual((1254, 1254), framed.size)
        for corner in ((0, 0), (1253, 0), (0, 1253), (1253, 1253)):
            self.assertEqual(0, framed.getpixel(corner)[3], f'corner {corner} must remain transparent')

        # Contact shadow below object foot stays subtle (<= 14% opacity)
        bottom_band = framed.crop((200, 900, 1054, 1200)).getchannel('A')
        pixels = bottom_band.get_flattened_data() if hasattr(bottom_band, 'get_flattened_data') else bottom_band.getdata()
        low_alphas = [a for a in pixels if 0 < a < 55]
        self.assertTrue(low_alphas, 'expected subtle soft contact shadow under product foot')
        self.assertLessEqual(max(low_alphas), 54)

    def test_accumulate_supports_byte_stub_and_rejects_perceptual_image_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / 'fluxixo_site'
            dist = site / 'dist'
            reserve = site / 'reserve'
            for p in (dist / 'js', dist / 'assets' / 'images', site / 'tools', reserve, root / 'data'):
                p.mkdir(parents=True)

            # Seed catalog matching the 2026-11-10 ledger row with a real cutout image on disk
            existing_img = _draw_cutout_a((640, 640))
            (dist / 'assets' / 'images' / 'find-064-book-light.webp').parent.mkdir(parents=True, exist_ok=True)
            existing_img.save(dist / 'assets' / 'images' / 'find-064-book-light.webp', format='WEBP', quality=90)
            old_products = [
                {
                    'id': pid,
                    'name': f'Предмет {pid}',
                    'headline': ['Свет,', 'который с тобой.'],
                    'description': 'Компактный практичный аксессуар.',
                    'image': f'assets/images/{pid}.webp',
                    'affiliateUrl': f'https://s.click.aliexpress.com/e/{pid}',
                }
                for pid in ('find-064-book-light', 'find-065-spice-grinder', 'find-067-pill-organizer')
            ]
            (dist / 'js' / 'catalog.js').write_text(
                'window.MIRA_CATALOG = ' + json.dumps({'products': old_products}, ensure_ascii=False) + ';',
                encoding='utf-8',
            )
            (site / 'tools' / 'i18n_data.json').write_text(json.dumps({'products': {}}), encoding='utf-8')
            (reserve / 'reserve_pool.json').write_text('[]', encoding='utf-8')
            live_ledger_path = Path(autonomous.__file__).resolve().parent.parent / 'data' / 'fluxixo_daily_ledger.json'
            live_ledger = json.loads(live_ledger_path.read_text(encoding='utf-8'))
            ledger = root / 'data' / 'ledger.json'
            ledger.write_text(
                json.dumps(
                    {
                        'version': live_ledger['version'],
                        'days': {'2026-11-10': live_ledger['days']['2026-11-10']},
                        'validation_runs': {},
                    },
                    ensure_ascii=False,
                ),
                encoding='utf-8',
            )

            seed = next(s for s in autonomous.SEEDS if s['key'] == 'inspection_mirror')
            cand = {
                'product_id': '999001',
                'title': 'Inspection mirror tool',
                'detail_url': 'https://www.aliexpress.com/item/999001.html',
                'image_url': 'https://ae01.alicdn.com/kf/999001.jpg',
                'affiliate_url': 'https://s.click.aliexpress.com/e/999001',
                'model_key': None,
                'task': seed,
            }

            # Real perceptual clone cutout must be rejected during accumulate()
            def clone_media(item, internal_id, stage):
                img_path = stage / f'{internal_id}-prepared.webp'
                orig_path = stage / f'{internal_id}-original.webp'
                ImageOps.mirror(existing_img).save(img_path, format='WEBP', quality=75)
                orig_path.write_bytes(b'orig-bytes-unique')
                return {
                    'image': img_path,
                    'original': orig_path,
                    'source_sha256': 'a' * 64,
                    'pixel_sha256': 'b' * 64,
                }

            with self.assertRaises(autonomous.DailyError):
                autonomous.accumulate(
                    count=1,
                    site_root=site,
                    dist=dist,
                    reserve_dir=reserve,
                    ledger_path=ledger,
                    now=NOW,
                    discover_fn=lambda *_: [cand],
                    media_fn=clone_media,
                )

            # Byte stub fixture media_fn remains backward compatible
            def byte_stub_media(item, internal_id, stage):
                img_path = stage / f'{internal_id}-prepared.webp'
                orig_path = stage / f'{internal_id}-original.webp'
                img_path.write_bytes(b'stub-prepared-' + internal_id.encode())
                orig_path.write_bytes(b'stub-original-' + internal_id.encode())
                return {
                    'image': img_path,
                    'original': orig_path,
                    'source_sha256': 'c' * 64,
                    'pixel_sha256': 'd' * 64,
                }

            res = autonomous.accumulate(
                count=1,
                site_root=site,
                dist=dist,
                reserve_dir=reserve,
                ledger_path=ledger,
                now=NOW,
                discover_fn=lambda *_: [cand],
                media_fn=byte_stub_media,
            )
            self.assertEqual(1, res['added'])


if __name__ == '__main__':
    unittest.main()
