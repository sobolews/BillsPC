from unittest import TestCase

from battle.battlepokemon import BattlePokemon
from battle.battlefield import BattleSide
from pokedex.moves import movedex
from mining import create_pokedex

pokedex = create_pokedex()

class TestBattlePokemon(TestCase):
    def test_initialize_pp(self):
        vaporeon = BattlePokemon(pokedex['vaporeon'], evs=(0,)*6,
                                 moveset=(movedex['scald'],
                                          movedex['icebeam'],
                                          movedex['rest'],
                                          movedex['toxic']))
        self.assertEqual(vaporeon.pp[movedex['scald']], 24)

    def test_shedinja_gets_1_max_hp(self):
        shedinja = BattlePokemon(pokedex['shedinja'])
        self.assertEqual(shedinja.hp, 1)
        self.assertEqual(shedinja.max_hp, 1)


class TestCalculateInitialStats(TestCase):
    def test_calculations(self):
        vaporeon = BattlePokemon(pokedex['vaporeon'], level=77)
        self.assertDictEqual(vaporeon.stats, {'max_hp': 327, 'spa': 214, 'spd': 191,
                                              'atk': 145, 'def': 137, 'spe': 145})

        leafeon = BattlePokemon(pokedex['leafeon'], level=83,
                                evs=(10, 40, 60, 100, 20, 25),
                                ivs=(6, 20, 17, 29, 2, 11))
        self.assertDictEqual(leafeon.stats, {'max_hp': 207, 'spa': 149, 'spd': 118,
                                             'atk': 212, 'def': 247, 'spe': 176})

    def test_calculation_default_evs_ivs(self):
        bronzong = BattlePokemon(pokedex['bronzong'], level=79,
                                 moveset=(movedex['gyroball'],
                                          movedex['toxic'],
                                          movedex['reflect'],
                                          movedex['earthquake']))
        self.assertDictEqual(bronzong.stats, {'max_hp': 235, 'atk': 203, 'def': 229,
                                              'spa': 170, 'spd': 229, 'spe': 57})
        delphox = BattlePokemon(pokedex['delphox'], level=79)
        self.assertDictEqual(delphox.stats, {'max_hp': 247, 'atk': 155, 'def': 159,
                                             'spa': 226, 'spd': 204, 'spe': 210})

        beheeyem = BattlePokemon(pokedex['beheeyem'], level=83,
                                 moveset=(movedex['thunderbolt'],
                                          movedex['signalbeam'],
                                          movedex['psyshock'],
                                          movedex['trickroom']))
        self.assertDictEqual(beheeyem.stats, {'atk': 172, 'def': 172, 'max_hp': 278,
                                              'spa': 255, 'spd': 205, 'spe': 71})
