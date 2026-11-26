"""Regression tests for the 1/day autoposting, unit parser, border-stripper, and 6-lang editorial gate."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'fluxixo_site/tools'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ai_seo  # noqa: E402
from fluxixo_ai import daily_schedule, reviewed_media  # noqa: E402


class AutopostingOverhaulTests(unittest.TestCase):
    def test_numeric_units_ignores_spanish_portuguese_range_preposition(self):
        self.assertEqual({'32mm', '3.2mm'}, ai_seo._numeric_units('Llave de 8 a 32 mm y puntas de 3,2 mm'))
        self.assertEqual({'230v'}, ai_seo._numeric_units('Prise 230 V'))
        self.assertEqual({'5a'}, ai_seo._numeric_units('Salida 5A estable'))

    def test_validate_product_editorial_catches_cross_language_leaks(self):
        valid = {
            lang: {
                'who': 'x' * 95 + '.',
                'skip': 'x' * 85 + '.',
                'compare': 'x' * 85 + '.',
                'check': ['c' * 40 + '.', 'd' * 40 + '.', 'e' * 40 + '.'],
            }
            for lang in ai_seo.LANGS
        }
        valid['ru'] = {
            'who': 'Подходит для домашней мастерской и выездного ремонта узких креплений без громоздкого стационарного инструмента на верстаке.',
            'skip': 'Не подойдёт для крупногабаритного промышленного крепежа или ударных гайковёртов с высоким крутящим моментом на СТО.',
            'compare': 'В отличие от тяжёлых разводных ключей, набор из хром-ванадиевой стали занимает меньше места и точнее фиксирует грани.',
            'check': [
                'Проверьте рабочий диапазон в миллиметрах в таблице размеров продавца.',
                'Уточните наличие чехла или пластикового держателя в выбранной комплектации.',
                'Сравните толщину губок, если работаете в узких нишах под капотом.',
            ],
        }
        valid['en'] = {
            'who': 'Built for apartment repairs, bike maintenance, and compact toolkits where carrying full wrench rolls stays impractical.',
            'skip': 'Skip it for seized axle nuts or rusted suspension bolts needing long breaker bars and heavy torque.',
            'compare': 'Unlike chunky adjustable wrenches that slip on tight fasteners, fixed metric openings seat cleanly around hex flats.',
            'check': [
                'Confirm the full millimeter size span printed on the seller specification chart.',
                'Check whether a fabric pouch or storage rack ships with the selected kit.',
                'Compare jaw depth if you plan to reach recessed fittings.',
            ],
        }
        valid['es'] = {
            'who': 'Ideal para arreglos en casa, ajustes en bicicleta y estuches compactos donde cargar cajas grandes de llaves estorba demasiado.',
            'skip': 'Evita este juego si trabajas con tuercas oxidadas de eje pesado o tornillería industrial que exige manerales largos.',
            'compare': 'A diferencia de un perico ajustable que suele patinar bajo esfuerzo, la medida fija apoya firme en cada cara del tornillo.',
            'check': [
                'Revisa el rango completo en milímetros dentro de las variantes de la publicación.',
                'Confirma si la opción elegida incluye funda enrollable o soporte organizador.',
                'Verifica el largo total del mango antes de usarla en espacios reducidos.',
            ],
        }
        valid['pt'] = {
            'who': 'Indicado para reparos domésticos, ajustes de bicicleta e kits enxutos onde carregar jogos pesados no porta-malas atrapalha.',
            'skip': 'Não vale para porcas de roda travadas por ferrugem ou manutenção pesada que exige cabo de força comprido.',
            'compare': 'Diferente de chaves ajustáveis que criam folga no sextavado, a medida fixa apoia por igual em torno do parafuso.',
            'check': [
                'Confira as medidas em milímetros descritas na variação selecionada no anúncio.',
                'Verifique se o estojo organizador acompanha o pacote escolhido antes do pedido.',
                'Observe a espessura da cabeça para alcançar espaços estreitos com conforto.',
            ],
        }
        valid['fr'] = {
            'who': 'Conçu pour le bricolage domestique, l’entretien de vélo et les trousses compactes quand une mallette complète encombre inutilement.',
            'skip': 'Écartez ce coffret pour les écrous grippés d’essieu lourd ou la mécanique intensive demandant de longues barres de force.',
            'compare': 'Contrairement à une clé à molette qui prend du jeu sous charge, les empreintes fixes épousent nettement les six pans.',
            'check': [
                'Vérifiez la plage exacte en millimètres dans les options proposées sur la fiche.',
                'Contrôlez si une pochette de rangement est fournie avec le jeu retenu.',
                'Comparez la longueur du manche si vous travaillez dans des recoins exigus.',
            ],
        }
        valid['he'] = {
            'who': 'מתאים לתיקונים בבית, לתחזוקת אופניים ולערכת כלים קומפקטית כשאין מקום לנשיאת ארגז מפתחות כבד במיוחד.',
            'skip': 'דלגו על הסט אם אתם מתמודדים עם אומים תקועים מחלודה בכלי רכב כבדים הדורשים מוט הארכה ארוך במיוחד.',
            'compare': 'בניגוד למפתח שוודי מתכוונן שעלול להחליק תחת עומס חזק, מידה קבועה אוחזת בצורה יציבה יותר בצלעות הבורג.',
            'check': [
                'בדקו את טווח המידות המלא במילימטרים בתוך אפשרויות הדגם בדף המוצר.',
                'ודאו אם נרתיק בד או תפס אחסון כלול בערכה שבחרתם לפני ההזמנה.',
                'השוו את אורך הידית כאשר עובדים באזורים צפופים במיוחד.',
            ],
        }
        self.assertEqual([], ai_seo.validate_product_editorial(valid))

        leaked = {**valid, 'es': {**valid['es'], 'who': 'Ideal para llevar todo con sua mascota en casa cuando sales.'}}
        probs = ai_seo.validate_product_editorial(leaked)
        self.assertTrue(any('editorial.es.who' in p for p in probs))

    def test_strip_border_frame_removes_uniform_black_frame_and_preserves_unframed(self):
        framed = Image.new('RGBA', (800, 800), (0, 0, 0, 255))
        draw = ImageDraw.Draw(framed)
        draw.rectangle((20, 20, 779, 779), fill=(210, 205, 195, 255))
        stripped = reviewed_media._strip_border_frame(framed)
        self.assertEqual((760, 760), stripped.size)

        plain = Image.new('RGBA', (800, 800), (140, 145, 150, 255))
        draw_p = ImageDraw.Draw(plain)
        draw_p.rectangle((100, 100, 700, 700), fill=(40, 90, 150, 255))
        kept = reviewed_media._strip_border_frame(plain)
        self.assertEqual((800, 800), kept.size)

    def test_daily_schedule_target_is_one_per_day(self):
        self.assertEqual(1, daily_schedule.DAILY_TARGET)
        ledger = {'version': 1, 'days': {}, 'validation_runs': {}}
        state = {'version': 1, 'days': {}}
        plan = daily_schedule.plan(ledger, state, now=datetime(2026, 11, 25, 13, 30, tzinfo=timezone.utc))
        self.assertEqual(1, plan['add_count'])

    def test_daily_schedule_skips_sunday_rest_day_and_uses_90m_retry(self):
        self.assertEqual(90, daily_schedule.WAITING_RETRY_MINUTES)
        self.assertEqual(6, daily_schedule.REST_WEEKDAY)
        ledger = {'version': 1, 'days': {}, 'validation_runs': {}}
        state = {'version': 1, 'days': {}}
        sunday = datetime(2026, 11, 29, 14, 0, tzinfo=timezone.utc)  # Sunday 16:00 Asia/Jerusalem
        skipped = daily_schedule.plan(ledger, state, now=sunday)
        self.assertEqual(('skip', 'weekly_rest_day', 0), (skipped['action'], skipped['reason'], skipped['add_count']))
        manual = daily_schedule.plan(ledger, state, now=sunday, manual_count=1)
        self.assertEqual(('prepare', 1), (manual['action'], manual['add_count']))

    def test_transient_503_never_permanently_burns_copy_drafts(self):
        from fluxixo_ai import copy_revisions
        from fluxixo_ai.gemini_client import GeminiDeferred
        state = {}
        calls = 0

        def flaky(_problems):
            nonlocal calls
            calls += 1
            if calls <= 6:
                raise GeminiDeferred('gemini_http_503')
            return {'ok': True}, 'test'

        for _ in range(6):
            with self.assertRaises(GeminiDeferred) as err:
                copy_revisions.run_bounded_copy(
                    'Compact Pocket Tool',
                    scope='bundle',
                    state=state,
                    checkpoint=lambda: None,
                    generate=flaky,
                    validate=lambda _cand: [],
                    review=lambda _cand: [],
                )
            self.assertNotIsInstance(err.exception, copy_revisions.GeminiCopyStopped)

        cand, provider = copy_revisions.run_bounded_copy(
            'Compact Pocket Tool',
            scope='bundle',
            state=state,
            checkpoint=lambda: None,
            generate=flaky,
            validate=lambda _cand: [],
            review=lambda _cand: [],
        )
        self.assertEqual({'ok': True}, cand)
        self.assertEqual('test', provider)

    def test_link_health_guard_loads_catalog_js_and_ignores_demos(self):
        import tempfile
        import link_health_guard
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'catalog.js'
            p.write_text(
                'window.MIRA_CATALOG = {"products": ['
                '{"id": "a1", "affiliateUrl": "https://s.click.aliexpress.com/e/_real", "demo": false},'
                '{"id": "d1", "affiliateUrl": "https://s.click.aliexpress.com/e/_demo", "demo": true}'
                ']};',
                encoding='utf-8',
            )
            loaded = link_health_guard.load_catalog_products(p)
        self.assertEqual(1, len(loaded))
        self.assertEqual('a1', loaded[0]['id'])
        self.assertEqual('https://s.click.aliexpress.com/e/_real', loaded[0]['affiliate_url'])

    def test_thin_category_bonus_prioritizes_sparse_worlds(self):
        from fluxixo_ai import discovery_curator
        existing = [{'id': f't{i}', 'category': 'Техника', 'sourceTitle': f'Unrelated Gadget {i}'} for i in range(12)]
        existing.append({'id': 'o1', 'category': 'На природе', 'sourceTitle': 'Solar Camp Lantern'})
        ok_thin, _, meta_thin = discovery_curator.presearch_exclusivity_check(
            {'product_id': '901', 'title': 'Compact Folding Titanium Pocket Stove', 'category': 'На природе',
             'evaluate_rate': '98%', 'lastest_volume': 200},
            existing,
        )
        ok_full, _, meta_full = discovery_curator.presearch_exclusivity_check(
            {'product_id': '902', 'title': 'Compact Folding Titanium Pocket Stove', 'category': 'Техника',
             'evaluate_rate': '98%', 'lastest_volume': 200},
            existing,
        )
        self.assertTrue(ok_thin and ok_full)
        self.assertGreater(meta_thin['score'], meta_full['score'])

    def test_free_text_failover_requires_flag_and_falls_back_on_503(self):
        import json as json_mod
        from unittest.mock import patch
        from fluxixo_ai.gemini_client import GeminiDeferred
        keys_off = {'FLUXIXO_TEXT_PROVIDER': 'gemini', 'FLUXIXO_TEXT_GEMINI_API_KEY': 'k'}
        with patch('fluxixo_ai.gemini_client.call_json', side_effect=GeminiDeferred('gemini_http_503')):
            with self.assertRaises(GeminiDeferred):
                ai_seo.complete_json('sys', 'usr', keys=keys_off)

        keys_on = {**keys_off, 'FLUXIXO_TEXT_FALLBACK_FREE': '1', 'GITHUB_TOKEN': 'gh-test'}

        def fake_transport(_url, _payload, _headers):
            return {'choices': [{'message': {'content': json_mod.dumps({'ok': 'fallback'})}}]}

        with patch('fluxixo_ai.gemini_client.call_json', side_effect=GeminiDeferred('gemini_http_503')):
            data, prov = ai_seo.complete_json('sys', 'usr', keys=keys_on, transport=fake_transport)
        self.assertEqual({'ok': 'fallback'}, data)
        self.assertTrue(prov.startswith('github_models:'))
