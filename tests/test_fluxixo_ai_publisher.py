"""Offline batch preparation for the existing FLUXIXO catalog."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from fluxixo_ai.publisher import PublisherError, prepare_batch, source_content
from fluxixo_ai.store import Store
from tests.test_fluxixo_ai_store import candidate

NOW = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)
DAY = '2026-11-10'


def selected(pid):
    result = candidate(str(pid))
    result.update({'category': 'Техника', 'affiliate_url': f'https://s.click.aliexpress.com/e/{pid}',
                   'image_url': 'https://ae01.alicdn.com/example.jpg',
                   'selection': {'rationale': 'PRIVATE SELECTION NOTE; DO NOT PUBLISH'}})
    return result


def media(_candidate, internal_id):
    return {'image': f'assets/images/{internal_id}.webp',
            'original': f'assets/originals/{internal_id}.webp'}


def legacy(pid='11111111111'):
    link = 'https://s.click.aliexpress.com/e/old-original'
    record = {'id': 'existing-product', 'name': 'Existing', 'affiliateUrl': link}
    evidence = {'product_id': pid, 'source_affiliate_url': link,
                'resolved_detail_url': f'https://www.aliexpress.com/item/{pid}.html',
                'method': 'verified_redirect', 'evidence_sha256': 'f' * 64}
    return {'products': [record], 'version': 'preserve-me'}, {'existing-product': evidence}


class OfflinePublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'queue.sqlite3')
        self.catalog, self.identity = legacy()
        self.i18n = {'ui': {'keep': True}, 'cats': {'keep': True},
                     'products': {'existing-product': {'en': {'name': 'Existing'}}}}

    def put(self, n, pid=None):
        pid = pid or str(12345678901 + n)
        return self.store.enqueue(f'request-{n}', selected(pid), now=NOW)

    def prepare(self, **kwargs):
        arguments = dict(store=self.store, day=DAY, owner='daily-job', catalog=self.catalog,
                         translations=self.i18n, prepare_media=media, identity_index=self.identity, now=NOW)
        arguments.update(kwargs)
        return prepare_batch(**arguments)

    def test_preserves_catalog_and_translates_the_exact_selected_product(self):
        self.put(0)
        self.put(1)
        original_catalog, original_i18n = deepcopy(self.catalog), deepcopy(self.i18n)
        result = self.prepare()
        self.assertEqual(original_catalog, self.catalog)
        self.assertEqual(original_i18n, self.i18n)
        self.assertEqual(original_catalog['products'], result['catalog']['products'][2:])
        self.assertEqual('preserve-me', result['catalog']['version'])
        self.assertEqual({'keep': True}, result['translations']['ui'])
        self.assertEqual(2, len(result['claims']))
        for n in (0, 1):
            actual = next(p for p in result['catalog']['products'] if p['sourceProductId'] == str(12345678901 + n))
            source = selected(str(12345678901 + n))
            self.assertEqual(source['title'], actual['sourceTitle'])
            self.assertEqual(source['title'], actual['name'])
            self.assertEqual(source_content(source)['ru']['description'], actual['description'])
            self.assertEqual(source['detail_url'], actual['sourceDetailUrl'])
            self.assertEqual(source['affiliate_url'], actual['affiliateUrl'])
            self.assertEqual('reserved', self.store.status(f'request-{n}')['state'])
            self.assertNotIn('PRIVATE SELECTION NOTE', str(actual))
            localized = result['translations']['products'][actual['id']]
            self.assertEqual(set(('en', 'pt', 'es', 'fr', 'he')), set(localized))
            self.assertEqual(source_content(source)['he'], localized['he'])

    def test_untrusted_generated_claims_never_enter_published_content(self):
        item = selected('12345678901')
        item['content']['ru']['description'] = 'An invented medical guarantee and fake stock.'
        item['content']['he']['name'] = 'An invented product identity.'
        self.store.enqueue('request-0', item, now=NOW)
        result = self.prepare()
        output = str(result['catalog']) + str(result['translations'])
        self.assertNotIn('invented medical guarantee', output)
        self.assertNotIn('invented product identity', output)
        self.assertNotIn('PRIVATE SELECTION NOTE', output)
        product = result['catalog']['products'][0]
        self.assertEqual(item['title'], product['name'])
        self.assertEqual(item['title'], result['translations']['products'][product['id']]['he']['name'])

    def test_unresolved_historical_identity_fails_before_claim_or_media(self):
        self.put(0)
        called = []
        with self.assertRaises(PublisherError) as error:
            self.prepare(identity_index={}, prepare_media=lambda *_: called.append(1))
        self.assertEqual('historical_identity_incomplete', error.exception.code)
        self.assertEqual('queued', self.store.status('request-0')['state'])
        self.assertEqual([], called)

    def test_mapping_must_refer_to_exact_original_affiliate_url_and_numeric_id(self):
        self.put(0)
        wrong = deepcopy(self.identity)
        wrong['existing-product']['source_affiliate_url'] = 'https://s.click.aliexpress.com/e/wrong'
        with self.assertRaises(PublisherError):
            self.prepare(identity_index=wrong)
        self.assertEqual('queued', self.store.status('request-0')['state'])

    def test_existing_product_id_is_not_added_again(self):
        self.put(0, '11111111111')
        result = self.prepare()
        self.assertEqual(self.catalog, result['catalog'])
        self.assertEqual([], result['claims'])
        self.assertEqual('failed', self.store.status('request-0')['state'])
        self.assertEqual('duplicate_existing', self.store.status('request-0')['reason'])

    def test_callback_failure_marks_all_claims_failed_without_mutating_input(self):
        self.put(0)
        self.put(1)
        original_catalog, original_i18n = deepcopy(self.catalog), deepcopy(self.i18n)
        def fail_media(*_):
            raise OSError('untrusted provider details should not escape')
        with self.assertRaises(PublisherError) as error:
            self.prepare(prepare_media=fail_media)
        self.assertEqual('batch_preparation_failed', error.exception.code)
        self.assertNotIn('provider details', str(error.exception))
        self.assertEqual(original_catalog, self.catalog)
        self.assertEqual(original_i18n, self.i18n)
        self.assertEqual('failed', self.store.status('request-0')['state'])
        self.assertEqual('failed', self.store.status('request-1')['state'])

    def test_invalid_asset_path_and_missing_category_fail_closed(self):
        self.put(0)
        with self.assertRaises(PublisherError):
            self.prepare(prepare_media=lambda *_: {'image': '../escaped.webp', 'original': 'x'})
        self.assertEqual('failed', self.store.status('request-0')['state'])
        invalid = selected('12345678902')
        del invalid['category']
        self.store.enqueue('request-bad-category', invalid, now=NOW)
        with self.assertRaises(PublisherError):
            self.prepare()
        self.assertEqual('failed', self.store.status('request-bad-category')['state'])

    def test_three_per_day_and_no_implicit_publication(self):
        for n in range(4):
            self.put(n)
        first = self.prepare()
        self.assertEqual(3, len(first['claims']))
        self.assertEqual(4, len(first['catalog']['products']))
        second = self.prepare(catalog=first['catalog'], translations=first['translations'])
        self.assertEqual([], second['claims'])
        self.assertEqual(4, len(second['catalog']['products']))
        self.assertEqual('queued', self.store.status('request-3')['state'])
        self.assertTrue(all(self.store.status(f'request-{n}')['state'] == 'reserved' for n in range(3)))

    def test_untrusted_affiliate_url_is_rejected_and_not_published(self):
        item = selected('12345678901')
        item['affiliate_url'] = 'https://s.click.aliexpress.com.attacker.invalid/e/not-an-affiliate'
        self.store.enqueue('request-0', item, now=NOW)
        with self.assertRaises(PublisherError):
            self.prepare()
        self.assertEqual('failed', self.store.status('request-0')['state'])

    def test_broker_queue_to_catalog_plan_uses_same_api_identity_without_publication(self):
        from fluxixo_ai.broker import handle_request
        from fluxixo_ai.policy import DETAIL, normalize_product
        product_id = '12345678901'
        api_title = 'Synthetic narrow inspection mirror'
        observed = normalize_product({'product_id': product_id, 'product_title': api_title,
                                      'product_detail_url': f'https://www.aliexpress.com/item/{product_id}.html',
                                      'product_main_image_url': 'https://ae01.alicdn.com/example.jpg'},
                                     'MX', DETAIL, NOW.isoformat())
        search_id, queue_id = '1' * 32, '2' * 32
        artifact = {'request_id': search_id, 'operation': 'search', 'status': 'complete',
                    'result': {'observed_at': NOW.isoformat(), 'candidates': [observed]}}
        detail = observed['detail_url']
        def api(method, params):
            self.assertEqual('aliexpress.affiliate.link.generate', method)
            self.assertEqual(detail, params['source_values'])
            return {'aliexpress_affiliate_link_generate_response': {'resp_result': {'resp_code': 200,
                    'result': {'promotion_links': {'promotion_link': [{'source_value': detail,
                    'promotion_link': 'https://s.click.aliexpress.com/e/_synthetic'}]}}}}}
        selection = {'product_id': product_id, 'category': 'Инструменты', 'markets': ['MX'],
                     'problem': 'Cannot inspect the narrow gap behind a shelf',
                     'use': 'Inspect the hidden gap with a small mirror',
                     'rationale': 'The seller title identifies an inspection mirror',
                     'evidence': [{'field': 'title', 'quote': 'inspection mirror'}]}
        response = handle_request('queue', {'search_id': search_id, 'selections': [selection]},
                                  queue_id, api, self.store, lambda _: artifact, now=NOW)
        self.assertFalse(response['published'])
        self.assertEqual(1, len(response['queued']))
        plan = self.prepare()
        item = plan['catalog']['products'][0]
        self.assertEqual(product_id, item['sourceProductId'])
        self.assertEqual(detail, item['sourceDetailUrl'])
        self.assertEqual(api_title, item['sourceTitle'])
        self.assertEqual('https://s.click.aliexpress.com/e/_synthetic', item['affiliateUrl'])
        self.assertFalse(plan['report']['published'])
        self.assertEqual('reserved', self.store.status(response['queued'][0]['request_id'])['state'])


if __name__ == '__main__':
    unittest.main()
