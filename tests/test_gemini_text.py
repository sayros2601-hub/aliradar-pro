"""Offline contract tests: explicitly selected Gemini never spends another provider's quota."""
import json
from copy import deepcopy
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


def claim_verdict(bundle, fields=('name', 'headline', 'description')):
    return {'accepted': True, 'checks': {lang: dict.fromkeys(fields, True) for lang in bundle},
            'unsupported_claims': []}


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
        from fluxixo_ai import gemini_client
        clock = [2_000_000_000.0]
        for patcher in (patch.object(gemini_client.time, 'time', side_effect=lambda: clock[0]),
                        patch.object(gemini_client.time, 'sleep', side_effect=lambda delay: clock.__setitem__(0, clock[0]+delay))):
            patcher.start()
            self.addCleanup(patcher.stop)

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
            request = json.loads(payload['contents'][0]['parts'][0]['text'])
            seen.append(request)
            if request.get('task') == 'verify_source_claims':
                return reply(claim_verdict(request['proposed_copy'], request['required_fields']))
            return reply(bundle)
        result, provider = ai_seo.enrich_product_copy(
            {'source_title': source, 'category': 'Инструменты', 'market': 'US'}, bundle,
            transport=fake, min_desc_len=160, snippet_fetcher=lambda *args: [],
        )
        self.assertEqual(set(ai_seo.LANGS), set(result))
        self.assertEqual(bundle, result)
        self.assertEqual('gemini:gemini-3.5-flash-lite:HIGH', provider)
        self.assertEqual(source, seen[0]['source_title'])
        self.assertEqual(2, len(seen))
        self.assertNotIn('baseline_6_languages', seen[0])
        self.assertEqual(bundle, seen[1]['proposed_copy'])
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

    def test_gemini_ignores_legacy_claims_and_rewrites_unsupported_headline(self):
        bundle = mirror_bundle()
        legacy = deepcopy(bundle)
        legacy['en']['description'] = 'LEGACY_DRAFT_ONLY_LOCKING_VALVE 999ml'
        unsupported = deepcopy(bundle)
        unsupported['en']['headline'] = ['Push-button', 'water return.']
        seen = []
        generation_count = [0]
        def fake(url, body, headers):
            request = json.loads(body['contents'][0]['parts'][0]['text'])
            seen.append(request)
            if request.get('task') == 'verify_source_claims':
                verdict = claim_verdict(request['proposed_copy'])
                if request['proposed_copy'] == unsupported:
                    verdict['accepted'] = False
                    verdict['checks']['en']['headline'] = False
                    verdict['unsupported_claims'] = [{'locale': 'en', 'field': 'headline',
                        'claim': 'Push-button water return', 'reason': 'The seller title does not state this mechanism.'}]
                return reply(verdict)
            generation_count[0] += 1
            return reply(unsupported if generation_count[0] == 1 else bundle)
        with patch.object(ai_seo, 'validate_product_bundle', wraps=ai_seo.validate_product_bundle) as validate:
            result, _ = ai_seo.enrich_product_copy(
                {'source_title': 'Handheld inspection mirror with pivoting head', 'category': 'Tools'},
                legacy, transport=fake, snippet_fetcher=lambda *a: [])
        self.assertEqual(bundle, result)
        self.assertEqual(4, len(seen))
        self.assertNotIn('LEGACY_DRAFT_ONLY', json.dumps(seen))
        self.assertEqual(['Handheld inspection mirror with pivoting head'] * 2,
                         [call.kwargs['source_text'] for call in validate.call_args_list])
        self.assertTrue(any('Push-button water return' in value for value in seen[2]['previous_validation_errors']))
        self.assertEqual(['name', 'headline', 'description'], seen[1]['required_fields'])

    def test_incomplete_claim_checks_fail_closed_after_two_attempts(self):
        from fluxixo_ai.gemini_client import GeminiDeferred
        bundle = mirror_bundle()
        valid = claim_verdict(bundle)
        missing_locale = deepcopy(valid)
        del missing_locale['checks']['he']
        missing_headline = deepcopy(valid)
        del missing_headline['checks']['fr']['headline']
        non_boolean = deepcopy(valid)
        non_boolean['checks']['pt']['name'] = 'true'
        for bad in (missing_locale, missing_headline, non_boolean, {'accepted': True}):
            calls = []
            state = {}
            def fake(url, body, headers):
                request = json.loads(body['contents'][0]['parts'][0]['text'])
                calls.append(request)
                return reply(bad if request.get('task') == 'verify_source_claims' else bundle)
            with self.subTest(verdict=bad):
                for _ in range(2):
                    with self.assertRaises(GeminiDeferred):
                        ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle,
                            transport=fake, snippet_fetcher=lambda *a: [], copy_state=state)
                self.assertEqual(3, len(calls))  # One draft, two reviews; no replacement for malformed reviews.

    def test_numbers_in_legacy_copy_are_not_source_evidence(self):
        from fluxixo_ai.gemini_client import GeminiDeferred
        bundle = mirror_bundle()
        bundle['en']['description'] += ' The mirror weighs 999g.'
        seen = []
        def fake(url, body, headers):
            seen.append(json.loads(body['contents'][0]['parts'][0]['text']))
            return reply(bundle)
        with self.assertRaises(GeminiDeferred):
            ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle,
                                      transport=fake, snippet_fetcher=lambda *a: [])
        self.assertEqual(2, len(seen))
        self.assertTrue(any('ungrounded specs' in issue for issue in seen[1]['previous_validation_errors']))

    def test_optional_russian_copy_uses_only_source_and_checks_every_field(self):
        source = 'Handheld mirror with swivel head'
        baseline = mirror_bundle()
        baseline['ru']['description'] = 'LEGACY_DRAFT_ONLY_LOCKING_VALVE 999ml'
        candidate = {'who': 'Зеркало пригодится для осмотра крепежа за шкафом и под капотом, когда к детали трудно подойти напрямую. Подвижная головка помогает подобрать направление отражения.',
                     'check': ['Сверьте длину ручки и размер зеркала с доступным пространством.',
                               'Уточните диапазон поворота головки и способ фиксации шарнира.',
                               'Проверьте комплектацию выбранного варианта на странице продавца.']}
        seen = []
        def fake(url, body, headers):
            request = json.loads(body['contents'][0]['parts'][0]['text'])
            seen.append(request)
            if request.get('task') == 'verify_source_claims':
                return reply(claim_verdict(request['proposed_copy'], request['required_fields']))
            return reply(candidate)
        with patch.object(ai_seo, 'validate_ru_long_entry', wraps=ai_seo.validate_ru_long_entry) as validate:
            result, _ = ai_seo.enrich_ru_long_copy({'source_title': source, 'category': 'Tools'}, baseline, transport=fake)
        self.assertEqual(candidate, result)
        self.assertEqual(2, len(seen))
        self.assertNotIn('LEGACY_DRAFT_ONLY', json.dumps(seen))
        self.assertNotIn('ru_description', seen[0])
        self.assertEqual(source, validate.call_args.kwargs['grounding_text'])
        self.assertEqual({'ru': candidate}, seen[1]['proposed_copy'])
        self.assertEqual(['who', 'check'], seen[1]['required_fields'])

    def test_rejected_copy_has_only_two_lifetime_drafts_for_same_seller_facts(self):
        bundle = mirror_bundle()
        state = {}
        calls = []
        saved = []
        def fake(url, body, headers):
            request = json.loads(body['contents'][0]['parts'][0]['text'])
            calls.append(request)
            self.assertTrue(saved, 'reservation must be checkpointed before requests')
            if request.get('task') == 'verify_source_claims':
                verdict = claim_verdict(bundle)
                verdict['accepted'] = False
                verdict['checks']['en']['headline'] = False
                return reply(verdict)
            return reply(bundle)
        def run(title, current):
            return ai_seo.enrich_product_copy({'source_title': title}, bundle, transport=fake,
                snippet_fetcher=lambda *a: [], copy_state=current,
                checkpoint=lambda: saved.append(json.dumps(current)))
        with self.assertRaises(ai_seo.GeminiCopyStopped) as caught:
            run('Handheld mirror with swivel head', state)
        self.assertEqual('copy_source_claims_failed', caught.exception.reason)
        self.assertEqual(ai_seo.copy_source_version('Handheld mirror with swivel head'), caught.exception.source_version)
        self.assertEqual(4, len(calls))
        restored = json.loads(json.dumps(state))
        with self.assertRaises(ai_seo.GeminiCopyStopped):
            run(' HANDHELD mirror-with SWIVEL head! ', restored)
        self.assertEqual(4, len(calls))
        self.assertEqual(ai_seo.copy_source_version(' 285 ml bowl '), ai_seo.copy_source_version('285ml BOWL.'))
        self.assertNotEqual(ai_seo.copy_source_version('1.5ml bowl'), ai_seo.copy_source_version('15ml bowl'))
        for before, after in (('1/2 inch', '12 inch'), ('10-15 kg', '1015 kg'),
                              ('-10 C', '+10 C'), ('50% power', '50 power')):
            with self.subTest(before=before):
                self.assertNotEqual(ai_seo.copy_source_version(before), ai_seo.copy_source_version(after))
        with self.assertRaises(ai_seo.GeminiCopyStopped):
            run('Handheld mirror with swivel head and light', restored)
        self.assertEqual(8, len(calls))
        with self.assertRaises(ai_seo.GeminiCopyStopped):
            run('Handheld mirror with swivel head', restored)
        self.assertEqual(8, len(calls))

    def test_retry_reviews_saved_draft_without_another_generation(self):
        from fluxixo_ai.gemini_client import GeminiDeferred
        state = {}
        bundle = mirror_bundle()
        calls = []
        def fake_complete(system, prompt, **kwargs):
            request = json.loads(prompt)
            calls.append(request)
            if request.get('task') == 'verify_source_claims':
                if len(calls) == 2:
                    raise GeminiDeferred('gemini_http_429')
                return claim_verdict(bundle), 'test-provider'
            return bundle, 'test-provider'
        with patch.object(ai_seo, 'complete_json', side_effect=fake_complete):
            with self.assertRaises(GeminiDeferred):
                ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle,
                    snippet_fetcher=lambda *a: [], copy_state=state)
            restored = json.loads(json.dumps(state))
            result, _ = ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle,
                snippet_fetcher=lambda *a: [], copy_state=restored)
            self.assertEqual(bundle, result)
            ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle,
                snippet_fetcher=lambda *a: [], copy_state=restored)
        self.assertEqual(3, len(calls))
        self.assertEqual(1, sum(request.get('task') != 'verify_source_claims' for request in calls))

    def test_review_transport_failures_stop_without_regenerating(self):
        from fluxixo_ai.gemini_client import GeminiDeferred
        state = {}
        calls = []
        def fake_complete(system, prompt, **kwargs):
            request = json.loads(prompt)
            calls.append(request)
            if request.get('task') == 'verify_source_claims':
                raise GeminiDeferred('gemini_transport_unavailable')
            return mirror_bundle(), 'test-provider'
        with patch.object(ai_seo, 'complete_json', side_effect=fake_complete):
            for _ in range(3):
                with self.assertRaises(GeminiDeferred) as caught:
                    ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, mirror_bundle(),
                        snippet_fetcher=lambda *a: [], copy_state=state)
            self.assertIsInstance(caught.exception, ai_seo.GeminiCopyStopped)
            self.assertEqual('copy_claim_review_gemini_transport_unavailable', caught.exception.reason)
        self.assertEqual(3, len(calls))

    def test_checkpoint_failure_prevents_request_and_lost_generations_are_bounded(self):
        from fluxixo_ai.gemini_client import GeminiDeferred
        state = {}
        with patch.object(ai_seo, 'complete_json') as complete:
            with self.assertRaises(GeminiDeferred) as caught:
                ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, mirror_bundle(),
                    copy_state=state, checkpoint=lambda: (_ for _ in ()).throw(OSError('private details')))
            self.assertEqual('checkpoint_unavailable', caught.exception.code)
            complete.assert_not_called()
        state = {}
        with patch.object(ai_seo, 'complete_json', side_effect=KeyboardInterrupt) as complete:
            for _ in range(2):
                with self.assertRaises(KeyboardInterrupt):
                    ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, mirror_bundle(),
                                              copy_state=state)
                state = json.loads(json.dumps(state))
            with self.assertRaises(ai_seo.GeminiCopyStopped):
                ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, mirror_bundle(),
                                          copy_state=state)
            self.assertEqual(2, complete.call_count)

    def test_optional_long_copy_rejections_do_not_restart_after_reloading_state(self):
        state = {}
        with patch.object(ai_seo, 'complete_json', return_value=({'who': 'too short', 'check': []}, 'test')) as complete:
            for _ in range(3):
                result, mode = ai_seo.enrich_ru_long_copy({'source_title': 'Handheld mirror'}, mirror_bundle(),
                                                         copy_state=state)
                self.assertIsNone(result)
                self.assertEqual('rejected', mode)
                state = json.loads(json.dumps(state))
            self.assertEqual(2, complete.call_count)

    def test_outer_rejection_consumes_existing_draft_and_permits_only_one_correction(self):
        title = 'Handheld mirror with swivel head'
        state = {}
        bundle = mirror_bundle()
        calls = []
        def fake_complete(system, prompt, **kwargs):
            request = json.loads(prompt)
            calls.append(request)
            return (claim_verdict(bundle) if request.get('task') == 'verify_source_claims' else bundle), 'test'
        def run():
            return ai_seo.enrich_product_copy({'source_title': title}, bundle,
                                              snippet_fetcher=lambda *a: [], copy_state=state)
        with patch.object(ai_seo, 'complete_json', side_effect=fake_complete):
            run()
            ai_seo.reject_cached_copy(title, state, problems=['Outer gate found duplicate product wording.'])
            run()
            self.assertTrue(any('Outer gate' in error for error in calls[2]['previous_validation_errors']))
            with self.assertRaises(ai_seo.GeminiCopyStopped) as caught:
                ai_seo.reject_cached_copy(title, state)
            self.assertEqual('copy_outer_validation_failed', caught.exception.reason)
            with self.assertRaises(ai_seo.GeminiCopyStopped):
                run()
        self.assertEqual(4, len(calls))

    def test_rejected_legacy_cached_copy_counts_as_first_draft(self):
        title = 'Handheld mirror with swivel head'
        state = {}
        ai_seo.reject_cached_copy(title, state)
        with patch.object(ai_seo, 'complete_json', return_value=({'ru': {}}, 'test')) as complete:
            with self.assertRaises(ai_seo.GeminiCopyStopped):
                ai_seo.enrich_product_copy({'source_title': title}, mirror_bundle(),
                                          snippet_fetcher=lambda *a: [], copy_state=state)
            self.assertEqual(1, complete.call_count)

    def test_free_search_outage_resumes_saved_copy_without_another_gemini_call(self):
        from fluxixo_ai.free_search import SearchDeferred
        from fluxixo_ai.gemini_client import GeminiDeferred
        bundle = mirror_bundle()
        state = {}
        model_calls = []
        def model(system, prompt, **kwargs):
            request = json.loads(prompt)
            model_calls.append(request)
            return (claim_verdict(bundle) if request.get('task') == 'verify_source_claims' else bundle), 'test'
        with patch.dict(os.environ, {'FLUXIXO_WEB_CHECK': '1', 'FLUXIXO_WEB_CHECK_PROVIDER': 'tavily_keyless'}), \
             patch.object(ai_seo, 'complete_json', side_effect=model), \
             patch.object(ai_seo, 'require_free_search_capacity', return_value=None), \
             patch.object(ai_seo.copy_originality, 'verify_snippet_uniqueness', side_effect=AssertionError('old/paid check forbidden')), \
             patch.object(ai_seo.copy_originality, 'verify_external_bundle_uniqueness',
                          side_effect=[SearchDeferred('free_search_unavailable', 2000000123), (True, [], {'locales': {}})]):
            with self.assertRaises(GeminiDeferred) as caught:
                ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle, copy_state=state)
            self.assertEqual(2000000123, caught.exception.retry_at)
            restored = json.loads(json.dumps(state))
            result, _ = ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle, copy_state=restored)
            self.assertEqual(bundle, result)
        self.assertEqual(2, len(model_calls))

    def test_external_overlap_uses_only_two_existing_draft_slots(self):
        bundle = mirror_bundle()
        state = {}
        calls = []
        def model(system, prompt, **kwargs):
            request = json.loads(prompt)
            calls.append(request)
            return (claim_verdict(bundle) if request.get('task') == 'verify_source_claims' else bundle), 'test'
        with patch.dict(os.environ, {'FLUXIXO_WEB_CHECK': '1', 'FLUXIXO_WEB_CHECK_PROVIDER': 'tavily_keyless'}), \
             patch.object(ai_seo, 'complete_json', side_effect=model), \
             patch.object(ai_seo, 'require_free_search_capacity', return_value=None), \
             patch.object(ai_seo.copy_originality, 'verify_external_bundle_uniqueness',
                          return_value=(False, ['en.description: external_prose_overlap https://example.com/item'], {'locales': {}})):
            for _ in range(2):
                with self.assertRaises(ai_seo.GeminiCopyStopped) as caught:
                    ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle, copy_state=state)
                self.assertEqual('copy_external_overlap', caught.exception.reason)
        self.assertEqual(4, len(calls))
        self.assertTrue(any('external_prose_overlap' in issue for issue in calls[2]['previous_validation_errors']))

    def test_external_receipt_binds_published_hebrew_and_requires_all_six_successes(self):
        from fluxixo_ai import free_search
        from fluxixo_ai.gemini_client import GeminiDeferred
        from fluxixo_ai.originality_receipt import description_hash
        bundle = mirror_bundle()
        bundle['he']['description'] += ' תאורת לד.'
        seen = {}
        def checker(text, lang, **kwargs):
            seen[lang] = text
            return {'passed': True, 'issues': [], 'evidence_urls': [], 'checked_at': 2000000000.0, 'cache_hit': True}
        receipt = {}
        with patch.object(free_search, 'check_external_text', side_effect=checker):
            self.assertEqual([], ai_seo.external_copy_problems(bundle, receipt=receipt))
        self.assertEqual(set(ai_seo.LANGS), set(receipt))
        self.assertIn('LED', seen['he'])
        self.assertNotIn(' לד.', seen['he'])
        self.assertEqual(description_hash(seen['he']), receipt['he']['sha256'])
        self.assertNotEqual(description_hash(bundle['he']['description']), receipt['he']['sha256'])
        self.assertTrue(all(value['checked_at'] == 2000000000 for value in receipt.values()))
        partial = {}
        def outage(text, lang, **kwargs):
            if lang == 'he':
                raise free_search.SearchDeferred('search_http_429', 2000000500)
            return checker(text, lang, **kwargs)
        with patch.object(free_search, 'check_external_text', side_effect=outage):
            with self.assertRaises(GeminiDeferred):
                ai_seo.external_copy_problems(bundle, receipt=partial)
        self.assertEqual({}, partial)

    def test_known_search_backoff_does_not_spend_new_copy_and_existing_draft_can_resume(self):
        from fluxixo_ai import free_search
        from fluxixo_ai.gemini_client import GeminiDeferred
        bundle = mirror_bundle()
        state = {}
        model_calls = []
        def model(system, prompt, **kwargs):
            request = json.loads(prompt)
            model_calls.append(request)
            return (claim_verdict(bundle) if request.get('task') == 'verify_source_claims' else bundle), 'test'
        enabled = {'FLUXIXO_WEB_CHECK': '1', 'FLUXIXO_WEB_CHECK_PROVIDER': 'tavily_keyless'}
        with patch.object(ai_seo, 'complete_json', side_effect=model), \
             patch.object(ai_seo.copy_originality, 'verify_external_bundle_uniqueness', return_value=(True, [], {'locales': {}})):
            with patch.dict(os.environ, enabled), \
                 patch.object(free_search, 'require_search_capacity', create=True,
                              side_effect=free_search.SearchDeferred('search_http_429', 2000000999)):
                with self.assertRaises(GeminiDeferred) as caught:
                    ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle, copy_state=state)
                self.assertEqual(2000000999, caught.exception.retry_at)
                self.assertEqual([], model_calls)
                journal = state['versions'][ai_seo.copy_source_version('Handheld mirror with swivel head')]['bundle']
                self.assertEqual([], journal['drafts'])
            # A pre-existing approved draft needs no generation reservation/preflight.
            with patch.dict(os.environ, {'FLUXIXO_WEB_CHECK': '0'}):
                ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle, copy_state=state)
            with patch.dict(os.environ, enabled), \
                 patch.object(free_search, 'require_search_capacity', create=True,
                              side_effect=AssertionError('saved draft must not regenerate')):
                result, _ = ai_seo.enrich_product_copy({'source_title': 'Handheld mirror with swivel head'}, bundle, copy_state=state)
                self.assertEqual(bundle, result)
        self.assertEqual(2, len(model_calls))


if __name__ == '__main__':
    unittest.main()
