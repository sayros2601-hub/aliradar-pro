from __future__ import annotations

import json
import unittest
from pathlib import Path

from fluxixo_site.redesign.build_redesign import (
    CATEGORY_LONG_FILE,
    EDITORIAL_FILE,
    HOME_EDITORIAL_FILE,
    LANGS,
    LONG_RU_FILE,
    Site,
    category_long_map,
    home_editorial,
    load,
    product_editorial,
    proofread,
)
from fluxixo_site.redesign.ui_text import MORE_HEADINGS
from fluxixo_site.tools import check_texts, verify_release
from fluxixo_site.tools.journal_pages import (
    EXTRA_MULTILINGUAL_FILE,
    JOURNAL_RELATED_HEADING,
    all_articles,
)


class EditorialSeoOverhaulTests(unittest.TestCase):
    @staticmethod
    def _check(where: str, text: str, lang: str) -> list[str]:
        probs: list[str] = []
        check_texts.check_string(text, lang, where, probs)
        return probs

    def test_all_114_products_have_6_language_4_block_editorial_copy(self) -> None:
        raw_items, _ = load()
        products = [p for p in raw_items if not p.get("demo")]
        self.assertGreaterEqual(len(products), 114)

        ed = product_editorial()
        ru_long = json.loads(LONG_RU_FILE.read_text(encoding="utf-8"))

        for p in products:
            pid = p["id"]
            self.assertIn(pid, ed, f"Missing product_editorial entry for {pid}")
            self.assertIn(pid, ru_long, f"Missing ru_long_copy entry for {pid}")
            self.assertTrue(ru_long[pid].get("who"))
            self.assertGreaterEqual(len(ru_long[pid].get("check", [])), 3)

            for lang in LANGS:
                self.assertIn(lang, ed[pid], f"Missing {lang} in product_editorial[{pid}]")
                block = ed[pid][lang]
                for key in ("who", "skip", "compare"):
                    val = (block.get(key) or "").strip()
                    self.assertGreaterEqual(
                        len(val.split()),
                        14,
                        f"{pid}.{lang}.{key} is too short: {val!r}",
                    )
                    errs = self._check(f"editorial.{pid}.{lang}.{key}", val, lang)
                    self.assertEqual(errs, [], f"{pid}.{lang}.{key} failed check_texts: {errs}")
                checks = block.get("check") or []
                self.assertGreaterEqual(len(checks), 3, f"{pid}.{lang}.check has <3 bullets")
                for idx, bullet in enumerate(checks):
                    self.assertGreaterEqual(len(bullet.split()), 6)
                    errs = self._check(f"editorial.{pid}.{lang}.check.{idx}", bullet, lang)
                    self.assertEqual(errs, [], f"{pid}.{lang}.check.{idx} failed check_texts: {errs}")

    def test_all_9_categories_have_6_language_long_copy(self) -> None:
        cats = category_long_map()
        expected_categories = (
            "Техника",
            "Дом",
            "Кухня",
            "В дороге",
            "Инструменты",
            "Уход",
            "Спорт",
            "На природе",
            "Питомцы",
        )
        for cat in expected_categories:
            self.assertIn(cat, cats, f"Missing category {cat}")
            for lang in LANGS:
                text = (cats[cat].get(lang) or "").strip()
                self.assertGreaterEqual(
                    len(text.split()),
                    50,
                    f"Category {cat} [{lang}] buying guide too short ({len(text.split())} words)",
                )
                errs = self._check(f"cat.{cat}.{lang}", text, lang)
                self.assertEqual(errs, [], f"Category {cat} [{lang}] failed check_texts: {errs}")

    def test_eight_new_multilingual_journal_guides_and_bidirectional_product_links(self) -> None:
        self.assertTrue(EXTRA_MULTILINGUAL_FILE.is_file())
        extra_articles = json.loads(EXTRA_MULTILINGUAL_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(extra_articles), 8)

        raw_items, _ = load()
        valid_ids = {p["id"] for p in raw_items if not p.get("demo")}

        for art in extra_articles:
            slug = art["slug"]
            self.assertIn(art["preferred_product"], valid_ids, f"{slug} preferred_product invalid")
            related = art.get("related_products") or []
            self.assertGreaterEqual(len(related), 3, f"{slug} must link >=3 related_products")
            for pid in related:
                self.assertIn(pid, valid_ids, f"{slug} related_product {pid} not in catalog")

            for lang in LANGS:
                self.assertIn(lang, art["translations"], f"{slug} missing {lang}")
                title, desc, h1, sections = art["translations"][lang]
                self.assertEqual(len(sections), 6, f"{slug}.{lang} must have 6 sections")
                total_words = sum(len(h2.split()) + len(body.split()) for h2, body in sections)
                self.assertGreaterEqual(
                    total_words,
                    480,
                    f"{slug}.{lang} has only {total_words} words",
                )
                for field_name, val in (("title", title), ("desc", desc), ("h1", h1)):
                    errs = self._check(f"journal.{slug}.{lang}.{field_name}", val, lang)
                    self.assertEqual(errs, [], errs)
                for idx, (h2, body) in enumerate(sections):
                    self.assertEqual(
                        self._check(f"journal.{slug}.{lang}.h2.{idx}", h2, lang),
                        [],
                    )
                    self.assertEqual(
                        self._check(f"journal.{slug}.{lang}.body.{idx}", body, lang),
                        [],
                    )

        # Total Journal guides across the site should now be 15 (7 original + 8 new)
        self.assertEqual(len(all_articles()), 15)

        # Site.guides(p) should link products in related_products back to their Journal guide
        raw_items, data = load()
        site = Site(raw_items, data, "en")
        linked_products = sum(1 for p in site.items if site.guides(p))
        self.assertGreaterEqual(linked_products, 29)

    def test_all_6_homepages_and_en_catalog_have_rich_editorial_copy(self) -> None:
        self.assertTrue(HOME_EDITORIAL_FILE.is_file())
        raw_json = HOME_EDITORIAL_FILE.read_text(encoding="utf-8")
        for forbidden in verify_release.FORBIDDEN:
            self.assertNotIn(forbidden, raw_json)

        he_data = home_editorial()
        raw_items, data = load()
        entry_pages = {
            "en": "/",
            "ru": "/catalog/",
            "pt": "/pt/",
            "es": "/es/",
            "fr": "/fr/",
            "he": "/he/",
        }

        for lang in LANGS:
            self.assertIn(lang, he_data, f"Missing {lang} in home_editorial.json")
            entry = he_data[lang]
            total_words = 0
            for key in ("about_h", "pillars_h", "guides_h", "guides_intro", "guides_cta", "qa_h", "langs_h"):
                val = (entry.get(key) or "").strip()
                self.assertTrue(val, f"{lang}.{key} missing")
                self.assertEqual(self._check(f"home.{lang}.{key}", val, lang), [])
                total_words += len(val.split())
            self.assertEqual(len(entry.get("about", [])), 2)
            for idx, para in enumerate(entry["about"]):
                self.assertGreaterEqual(len(para.split()), 45)
                self.assertEqual(self._check(f"home.{lang}.about.{idx}", para, lang), [])
                total_words += len(para.split())
            self.assertEqual(len(entry.get("pillars", [])), 4)
            for idx, pillar in enumerate(entry["pillars"]):
                self.assertEqual(self._check(f"home.{lang}.pillar.{idx}.h", pillar["h"], lang), [])
                self.assertEqual(self._check(f"home.{lang}.pillar.{idx}.p", pillar["p"], lang), [])
                total_words += len(pillar["h"].split()) + len(pillar["p"].split())
            self.assertEqual(len(entry.get("qa", [])), 4)
            for idx, qa in enumerate(entry["qa"]):
                self.assertEqual(self._check(f"home.{lang}.qa.{idx}.q", qa["q"], lang), [])
                self.assertEqual(self._check(f"home.{lang}.qa.{idx}.a", qa["a"], lang), [])
                total_words += len(qa["q"].split()) + len(qa["a"].split())
            self.assertGreaterEqual(total_words, 360, f"Homepage {lang} editorial copy too short: {total_words}")

            html = Site(raw_items, data, lang).home_editorial_html(entry_pages)
            self.assertIn('<section class="home-editorial"', html)
            self.assertEqual(html.count('class="home-pillar"'), 4)
            self.assertEqual(html.count('<details class="faq-item">'), 4)
            self.assertIn('<ul class="home-guides-grid">', html)
            self.assertNotIn('<section class="product-faq"', html)

        cat_en = he_data.get("catalog_en", {})
        cat_words = sum(len(str(v).split()) for v in cat_en.values())
        self.assertGreaterEqual(cat_words, 110)
        for key, text in cat_en.items():
            self.assertEqual(self._check(f"home.catalog_en.{key}", text, "en"), [])

    def test_proofread_passes_with_zero_errors(self) -> None:
        for lang in LANGS:
            self.assertIn(lang, MORE_HEADINGS)
            self.assertIn(lang, JOURNAL_RELATED_HEADING)
        proofread()


if __name__ == "__main__":
    unittest.main()
