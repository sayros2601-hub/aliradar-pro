"""Readable search metadata with safe duplicate handling for new items."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'fluxixo_site/redesign/build_redesign.py'
spec = importlib.util.spec_from_file_location('fluxixo_redesign_metadata_test', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MetadataTests(unittest.TestCase):
    def entry(self, source_id, name, desc='Check the seller listing.'):
        return {'id': 'auto-' + str(source_id), 'sourceProductId': str(source_id), 'name': name, 'description': desc}

    def test_unique_new_item_has_clean_readable_title_no_numeric_identifier(self):
        product = self.entry('12345678901', 'Экстрактор винтов', 'Извлечение повреждённого винта. Проверьте размер у продавца.')
        metadata = module.assign_product_metadata({'ru': [product]})[('ru', product['id'])]
        self.assertEqual(module.L.fit_title(product['name'], 'ru'), metadata[0])
        self.assertEqual(module.L.fit_description(product['description'], 'ru'), metadata[1])
        self.assertNotIn('12345678901', ' '.join(metadata))
        self.assertNotIn('Предложение', metadata[0])

    def test_same_label_different_items_are_distinct_on_six_locales(self):
        labels = {'ru':'Зеркало для осмотра','en':'Inspection mirror','pt':'Espelho de inspeção',
                  'es':'Espejo de inspección','fr':'Miroir d’inspection','he':'מראת בדיקה'}
        items = {lang: [self.entry('12345678902', name), self.entry('12345678901', name)] for lang, name in labels.items()}
        metadata = module.assign_product_metadata(items)
        titles = {v[0] for v in metadata.values()}; descriptions = {v[1] for v in metadata.values()}
        self.assertEqual(12, len(titles)); self.assertEqual(12, len(descriptions))
        for lang in labels:
            a=metadata[(lang, 'auto-12345678901')]; b=metadata[(lang, 'auto-12345678902')]
            self.assertIn('1', a[0]); self.assertIn('2', b[0])
            self.assertTrue(all('1234567890' not in text for text in (*a,*b)))
            self.assertLessEqual(len(a[0]), 70); self.assertLessEqual(len(b[1]), 170)

    def test_legacy_duplicate_keeps_its_metadata_and_new_one_is_distinct(self):
        old = {'id':'old','name':'Inspection mirror','description':'Check the seller listing.'}
        new = self.entry('12', old['name'], old['description'])
        metadata = module.assign_product_metadata({'en':[old, new]})
        self.assertEqual((module.L.fit_title(old['name'],'en'), module.L.fit_description(old['description'],'en')), metadata[('en','old')])
        self.assertIn('Listing 2', metadata[('en',new['id'])][0])
        self.assertNotEqual(metadata[('en','old')][0], metadata[('en',new['id'])][0])
        self.assertNotEqual(metadata[('en','old')][1], metadata[('en',new['id'])][1])

    def test_same_untranslated_long_name_across_six_languages_is_distinguished(self):
        name = 'Detailed source seller title ' * 8
        product = self.entry('12345', name, 'Check the seller listing. ' * 12)
        metadata=module.assign_product_metadata({lang:[product] for lang in ('ru','en','pt','es','fr','he')})
        self.assertEqual(6,len({v[0] for v in metadata.values()}))
        self.assertEqual(6,len({v[1] for v in metadata.values()}))
        for title,description in metadata.values():
            self.assertLessEqual(len(title),70);self.assertLessEqual(len(description),170)
            self.assertNotIn('12345',title);self.assertNotIn('12345',description)

    def test_assignment_is_stable_when_catalog_reordered(self):
        first=self.entry('2','Inspection mirror'); second=self.entry('10','Inspection mirror')
        one=module.assign_product_metadata({'en':[first, second]})
        two=module.assign_product_metadata({'en':[second, first]})
        self.assertEqual(one, two)

    def test_existing_metadata_helper_matches_original(self):
        title, description=module.product_metadata('Existing name','Existing description.','en',None)
        self.assertEqual(module.L.fit_title('Existing name','en'),title)
        self.assertEqual(module.L.fit_description('Existing description.','en'),description)

if __name__ == '__main__': unittest.main()
