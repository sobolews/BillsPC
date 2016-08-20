from unittest import TestCase

from mining import pokedex
from pokedex.enums import Type

class TestDataminer(TestCase):
    def test_parse_pokedex_js(self):
        self.assertEqual(pokedex['arcanine'].base_stats['max_hp'], 90)
        self.assertIs(pokedex['poliwag'].types[0], Type.WATER)
        self.assertIsNone(pokedex['poliwhirl'].types[1])
        self.assertIs(pokedex['poliwrath'].types[1], Type.FIGHTING)
        self.assertEqual(pokedex['giratinaorigin'].base_stats['def'], 100)
        self.assertEqual(pokedex['mimejr'].species, 'Mime Jr.')
        self.assertEqual(pokedex['Mime Jr.'].name, 'mimejr')
        self.assertIs(pokedex['arceusfairy'], pokedex['Arceus-Fairy'])
        self.assertIn('charizardmegay', pokedex['charizard'].mega_formes)
        self.assertEqual(len(pokedex['Muk'].mega_formes), 0)
        self.assertIn('swampertmega', pokedex['swampert'].mega_formes)
        self.assertTrue(pokedex['charizard'].fully_evolved)
        self.assertTrue(pokedex['muk'].fully_evolved)
        self.assertFalse(pokedex['porygon2'].fully_evolved)
        self.assertFalse(pokedex['scyther'].fully_evolved)
