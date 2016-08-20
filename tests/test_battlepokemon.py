from unittest import TestCase

from battle.battlepokemon import BattlePokemon
from pokedex.abilities import abilitydex
from pokedex.moves import movedex
from pokedex.items import itemdex
from mining import pokedex
from tests.multi_move_test_case import MultiMoveTestCase


class TestBattlePokemon(TestCase):
    def test_initialize_pp(self):
        vaporeon = BattlePokemon(pokedex['vaporeon'], evs=(0,)*6,
                                 moves=(movedex['scald'],
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
        vaporeon = BattlePokemon(pokedex['vaporeon'], level=77, moves=(movedex['return'],
                                                                       movedex['surf']))
        self.assertDictEqual(vaporeon.stats, {'max_hp': 327, 'spa': 214, 'spd': 191,
                                              'atk': 145, 'def': 137, 'spe': 145})

        leafeon = BattlePokemon(pokedex['leafeon'], level=83,
                                evs=(10, 40, 60, 100, 20, 25),
                                ivs=(6, 20, 17, 29, 2, 11))
        self.assertDictEqual(leafeon.stats, {'max_hp': 207, 'spa': 149, 'spd': 118,
                                             'atk': 212, 'def': 247, 'spe': 176})

    def test_calculation_default_evs_ivs(self):
        bronzong = BattlePokemon(pokedex['bronzong'], level=79,
                                 moves=(movedex['gyroball'],
                                        movedex['toxic'],
                                        movedex['reflect'],
                                        movedex['earthquake']))
        self.assertDictEqual(bronzong.stats, {'max_hp': 235, 'atk': 186, 'def': 229,
                                              'spa': 170, 'spd': 229, 'spe': 57})
        delphox = BattlePokemon(pokedex['delphox'], level=79, moves=(movedex['return'],
                                                                     movedex['fireblast']))
        self.assertDictEqual(delphox.stats, {'max_hp': 247, 'atk': 155, 'def': 159,
                                             'spa': 226, 'spd': 204, 'spe': 210})

        beheeyem = BattlePokemon(pokedex['beheeyem'], level=83,
                                 moves=(movedex['return'],
                                        movedex['signalbeam'],
                                        movedex['psyshock'],
                                        movedex['trickroom']))
        self.assertDictEqual(beheeyem.stats, {'atk': 172, 'def': 172, 'max_hp': 260,
                                              'spa': 255, 'spd': 205, 'spe': 71})

        # No physical attacks, so use min attack
        abomasnow = BattlePokemon(pokedex['abomasnow'], level=100,
                                  moves=(movedex['leechseed'], movedex['gigadrain'],
                                         movedex['blizzard'], movedex['earthpower']))
        self.assertDictEqual(abomasnow.stats, {'atk': 189, 'def': 207, 'max_hp': 342,
                                               'spa': 241, 'spd': 227, 'spe': 177})

        # stealthrock weakness: lower hp
        volcarona = BattlePokemon(pokedex['volcarona'], level=76,
                                  moves=(movedex['fireblast'], movedex['gigadrain'],
                                         movedex['bugbuzz'], movedex['quiverdance']))
        self.assertDictEqual(volcarona.stats, {'atk': 96, 'def': 143, 'max_hp': 253,
                                               'spa': 249, 'spd': 204, 'spe': 196})

        # need to lower HP evs twice for SR weakness
        regice = BattlePokemon(pokedex['regice'], level=83,
                                  moves=(movedex['icebeam'], movedex['focusblast'],
                                         movedex['rockpolish'], movedex['thunderbolt']))
        self.assertDictEqual(regice.stats, {'atk': 88, 'def': 214, 'max_hp': 267,
                                            'spa': 214, 'spd': 380, 'spe': 131})

        # seismictoss and counter don't count as physical moves
        chansey = BattlePokemon(pokedex['chansey'], level=75,
                                moves=(movedex['counter'], movedex['toxic'],
                                       movedex['seismictoss'], movedex['wish']))
        self.assertDictEqual(chansey.stats, {'atk': 12, 'def': 51, 'spa': 96,
                                             'spd': 201, 'spe': 119, 'max_hp': 499})

        # sitrus/substitute overrides stealthrock weakness
        tropius = BattlePokemon(pokedex['tropius'], level=83, item=itemdex['sitrusberry'],
                                moves=(movedex['leechseed'], movedex['substitute'],
                                       movedex['gigadrain'], movedex['protect']))
        self.assertDictEqual(tropius.stats, {'atk': 117, 'def': 185, 'spa': 167,
                                             'spd': 192, 'spe': 132, 'max_hp': 300})

        # detect castformsunny forme and adjust HP for stealthrock weakness
        castform = BattlePokemon(pokedex['castform'], level=83, item=itemdex['heatrock'],
                                 moves=(movedex['weatherball'], movedex['solarbeam'],
                                        movedex['sunnyday'], movedex['icebeam']))
        self.assertDictEqual(castform.stats, {'atk': 121, 'def': 164, 'spa': 164,
                                              'spd': 164, 'spe': 164, 'max_hp': 251})


class TestAbilityChange(MultiMoveTestCase):
    def test_change_ability(self):
        self.new_battle(p0_ability='levitate')
        self.add_pokemon('espeon', 0)
        self.vaporeon.change_ability(abilitydex['motordrive'], self.battle)
        self.choose_move(self.leafeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 139)

        self.choose_move(self.leafeon, 'thunderbolt')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spe': 1})

        self.choose_switch(self.vaporeon, self.espeon)
        self.choose_move(self.leafeon, 'roar')
        self.run_turn()
        self.assertActive(self.vaporeon)

        self.assertEqual(self.vaporeon.ability.name, 'levitate')

        self.vaporeon.hp = self.vaporeon.max_hp
        self.choose_move(self.leafeon, 'fusionbolt')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 278)

        self.choose_move(self.leafeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 278)
