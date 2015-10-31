import os
import pickle
import shlex
import tempfile
from datetime import datetime, timedelta
from subprocess import check_call
from unittest import TestCase

from mock import patch
from nose.plugins.attrib import attr
from nose.tools import nottest

from mining import pokedexmaker
from pokedex.enums import Type

REPO_DIR = os.path.join(tempfile.mkdtemp(), 'Pokemon-Showdown')

class TestDataminer(TestCase):
    def test_parse_pokedex_js(self):
        miner = pokedexmaker.PokedexDataMiner()
        miner.parse_pokedex_js()
        self.assertEqual(miner.pokedex['arcanine'].base_stats['max_hp'], 90)
        self.assertIn('Intimidate', miner.pokedex['growlithe'].randbats_abilities)
        self.assertIs(miner.pokedex['poliwag'].types[0], Type.WATER)
        self.assertIsNone(miner.pokedex['poliwhirl'].types[1])
        self.assertIs(miner.pokedex['poliwrath'].types[1], Type.FIGHTING)
        self.assertEqual(miner.pokedex['giratinaorigin'].base_stats['def'], 100)
        self.assertEqual(miner.pokedex['mimejr'].species, 'Mime Jr.')
        self.assertEqual(miner.pokedex['Mime Jr.'].name, 'mimejr')
        self.assertIs(miner.pokedex['arceusfairy'], miner.pokedex['Arceus-Fairy'])
        self.assertIn('charizardmegay', miner.pokedex['charizard'].mega_formes)
        self.assertEqual(len(miner.pokedex['Muk'].mega_formes), 0)
        self.assertIn('swampertmega', miner.pokedex['swampert'].mega_formes)
        self.assertTrue(miner.pokedex['charizard'].fully_evolved)
        self.assertTrue(miner.pokedex['muk'].fully_evolved)
        self.assertFalse(miner.pokedex['porygon2'].fully_evolved)
        self.assertFalse(miner.pokedex['scyther'].fully_evolved)

    def test_parse_formats_js(self):
        miner = pokedexmaker.PokedexDataMiner()
        miner.make_pokedex()

        self.assertIn('counter', miner.pokedex['wobbuffet'].randbats_moves)
        self.assertEqual(miner.pokedex['giratinaorigin'].required_item, "Griseous Orb")
        self.assertIsNone(miner.pokedex['poliwrath'].required_item)
        self.assertIsNone(miner.pokedex.get('keldeoresolute'),
                          "Did not delete pokemon with no randbats moves")
        self.assertIsNone(miner.pokedex.get('missingno'), "Included missingno")

