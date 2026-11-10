import unittest

from fluxixo_ai.autonomous import SEEDS
from fluxixo_ai.task_copy import LANGS, TASK_COPY, task_description


class TaskCopyTests(unittest.TestCase):
    def test_every_seed_has_distinct_complete_translations(self):
        self.assertEqual(set(TASK_COPY), {seed['key'] for seed in SEEDS})
        self.assertEqual(set(LANGS), {'ru', 'en', 'pt', 'es', 'fr', 'he'})
        for key, translations in TASK_COPY.items():
            self.assertEqual(set(translations), set(LANGS), key)
            for lang in LANGS:
                copy = task_description(key, lang)
                self.assertIsInstance(copy, str)
                self.assertGreater(len(copy), 35, (key, lang))
                self.assertLessEqual(len(copy), 220, (key, lang))
                self.assertNotIn('http', copy)
                self.assertNotIn('{', copy)
        for lang in LANGS:
            self.assertEqual(len({task_description(key, lang) for key in TASK_COPY}), len(TASK_COPY), lang)

    def test_missing_task_or_language_is_an_error(self):
        for key, lang in [('unknown', 'ru'), ('screw_extractor', 'xx')]:
            with self.assertRaises(ValueError):
                task_description(key, lang)

    def test_russian_copy_describes_use_and_a_relevant_check(self):
        expected = {
            'inspection_mirror': ('осмотр', 'размер'),
            'magnetic_pickup': ('магнит', 'грузоподъём'),
            'screw_extractor': ('винт', 'диаметр'),
            'sewing_seam_guide': ('шв', 'машин'),
            'watch_hand_tool': ('стрел', 'насад'),
            'irrigation_punch': ('полив', 'диаметр'),
            'reed_trimmer': ('саксофон', 'трости'),
            'aquarium_tweezers': ('аквариум', 'длин'),
            'keyboard_switch_opener': ('переключател', 'совместим'),
            'bearing_puller': ('подшипник', 'размер'),
            'cable_fish_tape': ('кабел', 'длин'),
            'button_hook': ('пуговиц', 'размер'),
            'bead_spinner': ('бисер', 'игл'),
            'fly_tying_vise': ('мушк', 'крючк'),
        }
        for key, words in expected.items():
            copy = task_description(key, 'ru').lower()
            for word in words:
                self.assertIn(word, copy, key)
            self.assertRegex(copy, r'проверьте|уточните|сверьте')
            for claim in ('проверено', 'протестирован', 'гарантир', 'лучший', '100%'):
                self.assertNotIn(claim, copy)


if __name__ == '__main__':
    unittest.main()
