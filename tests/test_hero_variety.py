import json
import unittest
from hero_variety import hero_products, hero_payload, HERO_IDS
from dealvault_core import BASE_DIR, LANGUAGES


class HeroSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = json.loads((BASE_DIR/'data/products.json').read_text(encoding='utf-8'))['products']

    def test_curated_distinct_images_and_locales(self):
        selected = hero_products(self.products)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len({key for p, key in selected}), 12)
        images = {p['image']: p['image'] for p, key in selected}
        for lang in LANGUAGES:
            for entry, (p, key) in zip(hero_payload(selected, images, lang), selected):
                self.assertEqual(entry['title'], p['title_i18n'][lang])
                self.assertIn(p['slug'], entry['href'])
                self.assertEqual(entry['image'], '/'+p['image'])

    def test_withdrawn_products_do_not_return(self):
        products = [p for p in self.products if p['id'] != HERO_IDS[0]]
        self.assertNotIn(HERO_IDS[0], [p['id'] for p, key in hero_products(products)])
        fallback = [p for p in products if p['id'] not in HERO_IDS]
        self.assertEqual(hero_products(fallback)[0][0], fallback[0])

    def test_duplicate_photo_is_not_a_new_scene(self):
        products = [dict(p) for p in self.products]
        first = next(p for p in products if p['id'] == HERO_IDS[0])
        second = next(p for p in products if p['id'] == HERO_IDS[1])
        second['image'] = first['image']
        self.assertEqual(len(hero_products(products)), 11)


if __name__ == '__main__':
    unittest.main()
