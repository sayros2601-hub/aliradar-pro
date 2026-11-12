"""Tests for anti-mirroring, catalog copy uniqueness, AI retry loop, and snippet verification."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / 'fluxixo_site' / 'tools'
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import ai_seo  # noqa: E402
import copy_originality as co  # noqa: E402


def _clean_bundle() -> dict[str, dict]:
    return {
        'ru': {
            'name': 'Складное зеркало осмотра',
            'headline': ['Видно', 'за углом.'],
            'description': 'Компактное зеркало помогает проверить крепёж за шкафом и под капотом без демонтажа.',
        },
        'en': {
            'name': 'Compact Inspection Mirror',
            'headline': ['See around', 'tight bends.'],
            'description': 'Slim pocket mirror for checking hidden fasteners behind cabinets or under cramped engine bays.',
        },
        'pt': {
            'name': 'Espelho de Inspeção Compacto',
            'headline': ['Veja o que', 'fica oculto.'],
            'description': 'Espelho fino para conferir parafusos atrás de móveis e dentro do cofre do motor.',
        },
        'es': {
            'name': 'Espejo de Inspección Compacto',
            'headline': ['Mira detrás', 'sin desmontar.'],
            'description': 'Espejo delgado para revisar tornillos ocultos detrás de muebles o dentro del motor.',
        },
        'fr': {
            'name': 'Miroir d’Inspection Compact',
            'headline': ['Voyez dans', 'les recoins.'],
            'description': 'Miroir fin pour contrôler les fixations cachées derrière un meuble ou sous le capot.',
        },
        'he': {
            'name': 'מראת ביקורת מתקפלת',
            'headline': ['רואים מעבר', 'לפינה צרה.'],
            'description': 'מראה דקה לבדיקת חיבורים נסתרים מאחורי ארון או בתא מנוע צפוף בלי פירוק.',
        },
    }


class CopyOriginalityTests(unittest.TestCase):
    def test_source_title_mirroring_blocks_english_mirror_and_latin_leak_in_ru_he(self):
        src_title = 'New Telescoping Magnetic Inspection Mirror Tool 360 Swivel Mechanic'
        bundle = _clean_bundle()
        self.assertEqual([], co.check_source_title_mirroring(bundle, src_title))

        # Mirroring in English
        mirrored = _clean_bundle()
        mirrored['en']['name'] = 'Telescoping Magnetic Inspection Mirror Tool'
        probs = co.check_source_title_mirroring(mirrored, src_title)
        self.assertTrue(any('en.name' in p for p in probs), probs)

        # Leaking 4+ English source words into Russian/Hebrew
        ru_leak = _clean_bundle()
        ru_leak['ru']['description'] = (
            'Удобный инструмент Magnetic Inspection Mirror Tool Swivel для проверки крепежа дома и в гараже.'
        )
        probs_ru = co.check_source_title_mirroring(ru_leak, src_title)
        self.assertTrue(any('ru.description' in p for p in probs_ru), probs_ru)

        he_leak = _clean_bundle()
        he_leak['he']['name'] = 'מראה Telescoping Magnetic Inspection Mirror Tool'
        probs_he = co.check_source_title_mirroring(he_leak, src_title)
        self.assertTrue(any('he.name' in p for p in probs_he), probs_he)

    def test_catalog_similarity_blocks_near_duplicate_and_allows_distinct(self):
        existing_products = [
            {
                'id': 'p-1',
                'name': 'Настольный таймер фокуса',
                'headline': ['Управляйте', 'каждым блоком.'],
                'description': 'Скрытая шкала отсчёта помогает держать рабочий ритм дома без лишних уведомлений телефона.',
            }
        ]
        existing_i18n = {
            'products': {
                'p-1': {
                    k: v for k, v in _clean_bundle().items() if k != 'ru'
                }
            }
        }
        corpus = co.build_catalog_copy_corpus(
            existing_products,
            existing_i18n,
            extra_routes={'/en/': {'title': 'Everyday Curated Tools', 'description': 'Quiet practical picks tested for daily desks.'}},
        )

        dup = _clean_bundle()  # matches en/pt/es/fr/he of p-1
        probs_dup = co.check_catalog_similarity(dup, corpus)
        self.assertTrue(probs_dup, 'expected near-duplicate catalog rejection')

        distinct = {
            'ru': {
                'name': 'Керамический дозатор масла',
                'headline': ['Ровная струя', 'без капель.'],
                'description': 'Тёмный кувшин защищает оливковое масло от света на кухне и дозирует порцию аккуратно.',
            },
            'en': {
                'name': 'Ceramic Olive Oil Pourer',
                'headline': ['Clean pour', 'every meal.'],
                'description': 'Opaque stoneware bottle shields extra virgin oil from kitchen daylight while pouring neatly.',
            },
            'pt': {
                'name': 'Galheteiro de Cerâmica Escura',
                'headline': ['Dose exata', 'sem pingos.'],
                'description': 'Garrafa opaca protege o azeite da luz direta na bancada e controla o fio ao servir.',
            },
            'es': {
                'name': 'Aceitera Opaca de Cerámica',
                'headline': ['Vierte limpio', 'sin goteos.'],
                'description': 'Botella cerámica opaca resguarda el aceite de la luz en la encimera con caño preciso.',
            },
            'fr': {
                'name': 'Huilier Opaque en Grès',
                'headline': ['Versez juste', 'sans goutte.'],
                'description': 'Flacon en céramique opaque qui préserve l’huile d’olive de la lumière sur le plan.',
            },
            'he': {
                'name': 'בקבוק קרמיקה אטום לשמן',
                'headline': ['מזיגה נקייה', 'בלי טפטוף.'],
                'description': 'קנקן אטום לשמן זית שמונע חשיפה לאור השיש ומוזג זרם מדויק לבישול יומיומי.',
            },
        }
        self.assertEqual([], co.check_catalog_similarity(distinct, corpus))
        co.append_bundle_to_corpus(corpus, 'p-2', distinct)
        self.assertTrue(co.check_catalog_similarity(distinct, corpus))

    def test_enrich_product_copy_retries_with_originality_feedback(self):
        base_bundle = _clean_bundle()
        src_title = 'Stainless Rotary Herb Mill Cutter Kitchen Tool'
        ctx = {
            'id': 'herb-mill',
            'category': 'home',
            'source_title': src_title,
            'source_category': 'Kitchen Gadgets',
        }
        calls = []

        def fake_transport(url, payload, headers, timeout=35):
            calls.append(json.loads(payload['contents'][0]['parts'][0]['text']))
            if len(calls) == 1:
                bad = _clean_bundle()
                bad['en']['name'] = 'Stainless Rotary Herb Mill Cutter Kitchen Tool'
                bad['en']['description'] = 'Stainless rotary herb mill cutter kitchen tool for slicing fresh herbs fast.'
                return {'candidates': [{'content': {'parts': [{'text': json.dumps(bad, ensure_ascii=False)}]}}]}

            good = _clean_bundle()
            good['ru'] = {
                'name': 'Мельница для свежей зелени',
                'headline': ['Листья крупно,', 'руки чистые.'],
                'description': 'Барабанные лезвия аккуратно шинковали петрушку и кинзу прямо в тарелку без следов на доске.',
            }
            good['en'] = {
                'name': 'Rotary Herb Grinder Mill',
                'headline': ['Fresh leaves', 'minced neat.'],
                'description': 'Dual steel drums shear parsley and cilantro over soup bowls without bruising delicate stems.',
            }
            good['pt'] = {
                'name': 'Moedor Giratório de Ervas',
                'headline': ['Temperos soltos', 'na hora.'],
                'description': 'Cilindro de aço pica salsa e coentro direto sobre o prato sem amassar as folhas.',
            }
            good['es'] = {
                'name': 'Molinillo Giratorio de Hierbas',
                'headline': ['Hojas limpias', 'sobre el plato.'],
                'description': 'Rodillos de acero cortan perejil y cilantro al instante sin machacar el tallo.',
            }
            good['fr'] = {
                'name': 'Moulin Rotatif à Herbes',
                'headline': ['Feuilles nettes', 'sans planche.'],
                'description': 'Tambours crantés cisèlent persil et coriandre au-dessus du bol sans écraser les arômes.',
            }
            good['he'] = {
                'name': 'מטחנת תבלינים ידנית לעלים',
                'headline': ['עשבי תיבול', 'בסיבוב קל.'],
                'description': 'תוף נירוסטה קוצץ פטרוזיליה וכוסברה ישירות לצלחת בלי למעוך את העלים הירוקים.',
            }
            return {'candidates': [{'content': {'parts': [{'text': json.dumps(good, ensure_ascii=False)}]}}]}

        bundle, provider = ai_seo.enrich_product_copy(
            ctx,
            base_bundle,
            keys={'GEMINI_API_KEY': 'fake-gemini-key'},
            transport=fake_transport,
        )
        self.assertEqual(2, len(calls))
        self.assertTrue(provider.startswith('gemini:'), provider)
        retry_payload = calls[1]
        self.assertIn('previous_validation_errors', retry_payload)
        self.assertTrue(
            any('source_title' in err or 'mirrors' in err for err in retry_payload['previous_validation_errors']),
            retry_payload['previous_validation_errors'],
        )
        self.assertEqual('Rotary Herb Grinder Mill', bundle['en']['name'])

    def test_validate_route_override_rejects_near_dup_title_and_description(self):
        existing_titles = ['Quiet Magnetic Focus Timer for Desk Work']
        existing_descs = ['Silent visual timer that tracks focused desk sprints without phone notifications or buzzers.']

        dup_title = {
            'title': 'Quiet Magnetic Focus Timer for Desk Work Today',
            'description': 'Minimal stoneware dish holds everyday keys and small pocket coins neatly by the front entry.',
        }
        probs_t = ai_seo.validate_route_override(dup_title, 'en', existing_titles=existing_titles, existing_descs=existing_descs)
        self.assertTrue(any('title' in p for p in probs_t), probs_t)

        dup_desc = {
            'title': 'Compact Desk Tray for Daily Pocket Gear',
            'description': 'Silent visual timer that tracks focused desk sprints without any phone notifications.',
        }
        probs_d = ai_seo.validate_route_override(dup_desc, 'en', existing_titles=existing_titles, existing_descs=existing_descs)
        self.assertTrue(any('description' in p for p in probs_d), probs_d)

        clean = {
            'title': 'Compact Desk Tray for Daily Pocket Gear',
            'description': 'Minimal stoneware dish keeps everyday keys, earbuds, and pocket coins organized beside the door.',
        }
        self.assertEqual([], ai_seo.validate_route_override(clean, 'en', existing_titles=existing_titles, existing_descs=existing_descs))

    def test_verify_snippet_uniqueness_all_modes(self):
        cands = [('description', 'Compact stoneware tray keeps keys and pocket tools tidy on entryway shelves.')]

        # 1. FLUXIXO_OFFLINE=1
        with patch.dict(os.environ, {'FLUXIXO_OFFLINE': '1'}, clear=False):
            ok, issues, meta = co.verify_snippet_uniqueness(cands, snippet_fetcher=lambda *_: self.fail('must not call network offline'))
        self.assertTrue(ok)
        self.assertEqual([], issues)
        self.assertEqual('offline', meta.get('skipped'))

        # 2. Unconfigured default
        with patch.dict(os.environ, {'FLUXIXO_OFFLINE': '', 'FLUXIXO_WEB_CHECK': '', 'SERPER_API_KEY': '', 'GOOGLE_CSE_KEY': '', 'GOOGLE_CSE_CX': ''}, clear=False):
            ok, issues, meta = co.verify_snippet_uniqueness(cands)
        self.assertTrue(ok)
        self.assertEqual('disabled_or_unconfigured', meta.get('skipped'))

        # 3. External collision rejected
        with patch.dict(os.environ, {'FLUXIXO_OFFLINE': ''}, clear=False):
            ok, issues, _ = co.verify_snippet_uniqueness(
                cands,
                snippet_fetcher=lambda q, lang, t: [
                    {'url': 'https://competitor.example/tray', 'title': 'Tray', 'snippet': cands[0][1]}
                ],
            )
            self.assertFalse(ok)
            self.assertTrue(issues)

            # 4. Self-domain ignored
            ok_self, issues_self, _ = co.verify_snippet_uniqueness(
                cands,
                snippet_fetcher=lambda q, lang, t: [
                    {'url': 'https://www.fluxixo.shop/en/products/tray/', 'title': 'Tray', 'snippet': cands[0][1]}
                ],
            )
            self.assertTrue(ok_self)
            self.assertEqual([], issues_self)

            # 5. TimeoutError fails open by default, closed if requested
            def _boom(*_):
                raise TimeoutError('timed out')

            ok_open, issues_open, meta_open = co.verify_snippet_uniqueness(cands, snippet_fetcher=_boom)
            self.assertTrue(ok_open)
            self.assertEqual([], issues_open)
            self.assertEqual('network_error', meta_open.get('skipped'))

            ok_closed, issues_closed, _ = co.verify_snippet_uniqueness(cands, snippet_fetcher=_boom, fail_on_network_error=True)
            self.assertFalse(ok_closed)
            self.assertTrue(issues_closed)


if __name__ == '__main__':
    unittest.main()
