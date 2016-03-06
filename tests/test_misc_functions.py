from unittest import TestCase

from misc.functions import clamp_int, normalize_name, gf_round

class TestMisc(TestCase):
    def test_clamp_int(self):
        self.assertEqual(clamp_int(5, 1, 10), 5)
        self.assertEqual(clamp_int(3, 6, 10), 6)
        self.assertEqual(clamp_int(15, 5, 10), 10)
        self.assertEqual(clamp_int(0, 0, 0), 0)
        if __debug__:
            with self.assertRaises(AssertionError):
                clamp_int(0, 5, 2)

    def test_gf_round(self):
        self.assertEqual(gf_round(1), 1)
        self.assertEqual(gf_round(1.0), 1)
        self.assertTrue(isinstance(gf_round(1.0), int))
        self.assertEqual(gf_round(13.1), 13)
        self.assertEqual(gf_round(127.5), 127)
        self.assertEqual(gf_round(1.75), 2)
        self.assertEqual(gf_round(0.9999999999999999999999), 1)

    def test_normalize_name(self):
        self.assertEqual(normalize_name('p2a: Galvantula'), 'galvantula')
        self.assertEqual(normalize_name('Thundurus-Therian'), 'thundurustherian')
        self.assertEqual(normalize_name('Bug Buzz'), 'bugbuzz')
        self.assertEqual(normalize_name("Farfetch'd"), 'farfetchd')
        self.assertEqual(normalize_name("Mr. Mime"), 'mrmime')
        self.assertEqual(normalize_name('ability: Slow Start'), 'slowstart')
        self.assertEqual(normalize_name('move: Taunt'), 'taunt')
