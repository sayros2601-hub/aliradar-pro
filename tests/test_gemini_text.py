"""Offline contract tests: explicitly selected Gemini never spends another provider's quota."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'fluxixo_site/tools'))
import ai_seo


def reply(body, finish='STOP'):
    return {'candidates': [{'finishReason': finish, 'content': {'parts': [
        {'thought': True, 'text': 'not output'}, {'text': json.dumps(body)},
    ]}}]}


def mirror_bundle():
    return {
        'ru': {'name': 'Складное зеркало осмотра', 'headline': ['Видно', 'за углом.'],
               'description': 'Компактное зеркало помогает проверить крепёж за шкафом и под капотом без демонтажа. Подвижная головка направляет отражение в узкое пространство. Перед заказом сверьте длину ручки, размер зеркала и форму шарнира у продавца.'},
        'en': {'name': 'Compact Inspection Mirror', 'headline': ['See around', 'tight bends.'],
               'description': 'A slim mirror brings hidden fasteners into view behind cabinets or inside an engine bay. Its pivoting head helps find the useful viewing angle. Check the handle length, mirror size and joint shape in the seller listing.'},
        'pt': {'name': 'Espelho de Inspeção Compacto', 'headline': ['Veja o que', 'fica oculto.'],
               'description': 'O espelho fino ajuda a conferir parafusos atrás de móveis ou no cofre do motor sem desmontar peças. A cabeça móvel ajusta o ângulo de visão. Confira o comprimento da haste, o tamanho do espelho e o formato da articulação na página do vendedor.'},
        'es': {'name': 'Espejo de Inspección Compacto', 'headline': ['Mira detrás', 'sin desmontar.'],
               'description': 'El espejo delgado permite revisar tornillos ocultos detrás de muebles o dentro del motor sin desmontar piezas. La cabeza orientable ajusta el ángulo de visión. Revisa el largo del mango, el tamaño del espejo y la forma de la articulación con el vendedor.'},
        'fr': {'name': 'Miroir d’Inspection Compact', 'headline': ['Voyez dans', 'les recoins.'],
               'description': 'Un miroir fin permet de voir les fixations cachées derrière un meuble ou sous le capot sans démontage. Sa tête mobile ajuste l’angle de vue. Vérifiez la longueur de la tige, la taille du miroir et la forme de l’articulation chez le vendeur.'},
        'he': {'name': 'מראת ביקורת מתקפלת', 'headline': ['רואים מעבר', 'לפינה צרה.'],
               'description': 'מראה דקה מאפשרת לראות חיבורים נסתרים מאחורי ארון או בתוך תא מנוע בלי לפרק חלקים. הראש המתכוונן עוזר למצוא זווית צפייה נוחה גם במקום צפוף. לפני ההזמנה בדקו בעמוד המוצר את אורך הידית, גודל המראה וצורת המפרק.'},
    }


class GeminiTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {
            'FLUXIXO_TEXT_PROVIDER': 'gemini',
            'FLUXIXO_TEXT_GEMINI_API_KEY': 'test-only-not-a-real-key',
            'FLUXIXO_GEMINI_BUDGET_PATH': str(Path(self.tmp.name) / 'usage.sqlite3'),
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_scoped_key_and_provider_are_loaded_without_other_credentials(self):
        keys = ai_seo.load_ai_keys()
        self.assertEqual('gemini', keys.get('FLUXIXO_TEXT_PROVIDER'))
        self.assertEqual('test-only-not-a-real-key', keys.get('FLUXIXO_TEXT_GEMINI_API_KEY'))
        self.assertNotIn('CLOUDFLARE_API_TOKEN', keys)

    def test_explicit_gemini_sends_high_structured_request_even_with_cf_keys(self):
        calls = []
        def fake(url, payload, headers):
            calls.append((url, payload, headers))
            return reply({'accepted': True})
        result, provider = ai_seo.complete_json('system', 'user', keys={
            'FLUXIXO_TEXT_PROVIDER': 'gemini',
            'FLUXIXO_TEXT_GEMINI_API_KEY': 'test-only-not-a-real-key',
            'CLOUDFLARE_API_TOKEN': 'not-a-real-cf-key',
        }, transport=fake)
        self.assertEqual({'accepted': True}, result)
        self.assertEqual('gemini:gemini-3.5-flash-lite:HIGH', provider)
        self.assertEqual(1, len(calls))
        url, body, headers = calls[0]
        self.assertEqual('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent', url)
        self.assertEqual({'thinkingLevel': 'HIGH'}, body['generationConfig']['thinkingConfig'])
        self.assertEqual('application/json', body['generationConfig']['responseMimeType'])
        self.assertNotIn('test-only-not-a-real-key', url)
        self.assertEqual('test-only-not-a-real-key', headers['x-goog-api-key'])

    def test_missing_scoped_key_does_not_call_other_providers(self):
        calls = []
        with self.assertRaises(Exception) as caught:
            ai_seo.complete_json('system', 'user', keys={
                'FLUXIXO_TEXT_PROVIDER': 'gemini', 'CLOUDFLARE_API_TOKEN': 'fake',
            }, transport=lambda *args: calls.append(args))
        self.assertEqual('gemini_key_missing', str(caught.exception))
        self.assertEqual([], calls)

    def test_one_isolated_card_keeps_six_locales_and_real_copy_validators(self):
        bundle = mirror_bundle()
        source = 'New Telescoping Magnetic Inspection Mirror Tool 360 Swivel Mechanic'
        seen = []
        def fake(url, payload, headers):
            seen.append(json.loads(payload['contents'][0]['parts'][0]['text']))
            return reply(bundle)
        result, provider = ai_seo.enrich_product_copy(
            {'source_title': source, 'category': 'Инструменты', 'market': 'US'}, bundle,
            transport=fake, min_desc_len=160, snippet_fetcher=lambda *args: [],
        )
        self.assertEqual(set(ai_seo.LANGS), set(result))
        self.assertEqual(bundle, result)
        self.assertEqual('gemini:gemini-3.5-flash-lite:HIGH', provider)
        self.assertEqual(source, seen[0]['source_title'])
        self.assertEqual([], ai_seo.validate_product_bundle(result, source_title=source, min_desc_len=160,
                                                            snippet_fetcher=lambda *args: []))

    def test_duplicate_copy_rejected_after_bounded_rewrite_not_baseline_fallback(self):
        from fluxixo_ai import gemini_client
        bundle = mirror_bundle()
        corpus = ai_seo.copy_originality.build_catalog_copy_corpus(
            [{'id': 'already-listed', **bundle['ru']}],
            {'products': {'already-listed': {k: v for k, v in bundle.items() if k != 'ru'}}},
        )
        seen = []
        def fake(url, payload, headers):
            seen.append(json.loads(payload['contents'][0]['parts'][0]['text']))
            return reply(bundle)
        clock = [2_000_000_000.0]
        with patch.object(gemini_client.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(gemini_client.time, 'sleep', side_effect=lambda delay: clock.__setitem__(0, clock[0]+delay)):
            with self.assertRaises(gemini_client.GeminiDeferred) as error:
                ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with adjustable joint'}, bundle,
                                           transport=fake, catalog_corpus=corpus, min_desc_len=160,
                                           snippet_fetcher=lambda *args: [])
        self.assertEqual('gemini_copy_validation_failed', error.exception.code)
        self.assertEqual(2, len(seen))
        self.assertTrue(any('duplicate' in message for message in seen[1]['previous_validation_errors']))


if __name__ == '__main__':
    unittest.main()
