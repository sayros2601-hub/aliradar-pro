"""New items of one task must never produce duplicate search metadata."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'fluxixo_site/redesign/build_redesign.py'
spec = importlib.util.spec_from_file_location('fluxixo_redesign_metadata_test', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MetadataTests(unittest.TestCase):
    def test_same_label_different_items_have_distinct_six_locale_metadata(self):
        labels = {'ru':'Зеркало для осмотра','en':'Inspection mirror','pt':'Espelho de inspeção',
                  'es':'Espejo de inspección','fr':'Miroir d’inspection','he':'מראת בדיקה'}
        titles, descriptions = set(), set()
        for locale, label in labels.items():
            for product_id in ('12345678901', '12345678902'):
                title, description = module.product_metadata(label, label + '. Check the seller listing.', locale, product_id)
                self.assertLessEqual(len(title), 70)
                self.assertLessEqual(len(description), 170)
                self.assertIn(product_id, title)
                self.assertIn(product_id, description)
                titles.add(title)
                descriptions.add(description)
        self.assertEqual(12, len(titles))
        self.assertEqual(12, len(descriptions))

    def test_existing_items_keep_their_original_metadata(self):
        title, description = module.product_metadata('Existing name', 'Existing description.', 'en', None)
        self.assertEqual(module.L.fit_title('Existing name', 'en'), title)
        self.assertEqual(module.L.fit_description('Existing description.', 'en'), description)


if __name__ == '__main__': unittest.main()
