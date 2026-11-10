"""Update descriptions of an existing source-grounded product, without network."""
from copy import deepcopy
import unittest

from fluxixo_ai.copy_refresh import CopyRefreshError, prepare_update

PRODUCT_ID = '1005004679234788'
ITEM_ID = 'auto-' + PRODUCT_ID


def fixture():
    item = {'id': ITEM_ID, 'name': 'Экстрактор винтов', 'sourceProductId': PRODUCT_ID,
            'sourceTask': 'screw_extractor',
            'sourceTitle': '5pc HSS Left Hand Drill Bit Straight Shank Broken Bolt Damaged Screw Extractor Set',
            'description': 'Old description.', 'details': 'Old description.',
            'affiliateUrl': 'https://s.click.aliexpress.com/e/source',
            'image': 'assets/images/item.webp', 'original': 'assets/originals/item.webp'}
    catalog = {'products': [{'id': 'old-product', 'name': 'Keep me'}, item]}
    translations = {'ui': {'unchanged': True}, 'products': {ITEM_ID: {
        language: {'name': f'Name {language}', 'headline': ['One', 'Two'], 'description': 'Old description.'}
        for language in ('en', 'pt', 'es', 'fr', 'he')}}}
    return catalog, translations


class CopyRefreshTests(unittest.TestCase):
    def test_updates_only_one_existing_product_description_in_all_six_locales(self):
        catalog, translations = fixture()
        original_catalog, original_translations = deepcopy(catalog), deepcopy(translations)
        result = prepare_update(catalog, translations, PRODUCT_ID)
        self.assertEqual(catalog, original_catalog)
        self.assertEqual(translations, original_translations)
        self.assertEqual(catalog['products'][0], result['catalog']['products'][0])
        actual = result['catalog']['products'][1]
        original = catalog['products'][1]
        self.assertNotEqual(original['description'], actual['description'])
        self.assertEqual(actual['description'], actual['details'])
        self.assertIn('поврежд', actual['description'].lower())
        self.assertIn('проверьте', actual['description'].lower())
        for key in set(original) - {'description', 'details'}:
            self.assertEqual(original[key], actual[key])
        for lang, value in result['translations']['products'][ITEM_ID].items():
            self.assertNotEqual('Old description.', value['description'])
            self.assertEqual(translations['products'][ITEM_ID][lang]['name'], value['name'])
            self.assertEqual(translations['products'][ITEM_ID][lang]['headline'], value['headline'])
        self.assertEqual({'ru', 'en', 'pt', 'es', 'fr', 'he'}, set(result['locales']))

    def test_repeat_is_idempotent(self):
        catalog, translations = fixture()
        first = prepare_update(catalog, translations, PRODUCT_ID)
        second = prepare_update(first['catalog'], first['translations'], PRODUCT_ID)
        self.assertEqual(first['catalog'], second['catalog'])
        self.assertEqual(first['translations'], second['translations'])

    def test_missing_duplicate_or_mismatched_product_never_mutates(self):
        catalog, translations = fixture()
        for changed in ({'sourceTask':'reading_light'}, {'sourceTitle':'Unrelated kitchen tray'},
                        {'sourceProductId':'9'}, {'sourceTitle':'Replacement screw extractor for a device'}):
            mutated = deepcopy(catalog)
            mutated['products'][1].update(changed)
            snapshot = deepcopy(mutated)
            with self.subTest(changed=changed), self.assertRaises(CopyRefreshError):
                prepare_update(mutated, translations, PRODUCT_ID)
            self.assertEqual(snapshot, mutated)
        catalog['products'].append(deepcopy(catalog['products'][1]))
        with self.assertRaises(CopyRefreshError):
            prepare_update(catalog, translations, PRODUCT_ID)

    def test_missing_locale_fails_before_any_change(self):
        catalog, translations = fixture()
        del translations['products'][ITEM_ID]['he']
        original = deepcopy(catalog)
        with self.assertRaises(CopyRefreshError):
            prepare_update(catalog, translations, PRODUCT_ID)
        self.assertEqual(original, catalog)


if __name__ == '__main__': unittest.main()
