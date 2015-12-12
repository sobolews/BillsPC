from mock import patch
from unittest import TestCase

from battle.battleengine import BattleEngine
from pokedex import effects
from pokedex.enums import (MoveCategory, Status, Cause, FAIL, Weather, Volatile, Hazard,
                           PseudoWeather, SideCondition)
from pokedex.items import itemdex
from pokedex.moves import movedex, Move, _MAX_PP
from pokedex.types import Type
from pokedex.stats import Boosts
from mining.statistics import RandbatsStatistics
from tests.multi_move_test_case import MultiMoveTestCase

class TestMoveDefinitions(TestCase):
    def setUp(self):
        self.all_moves = movedex.values()

    def test_all_moves_have_correct_enums(self):
        for move in self.all_moves:
            self.assertIsInstance(move.category, MoveCategory)
            self.assertIsInstance(move.type, Type)

    def test_nonstatus_moves_have_base_power_or_damage(self):
        for move in self.all_moves:
            if move.category is not MoveCategory.STATUS:
                self.assertTrue((move.base_power > 0 or
                                 move.get_base_power.__func__ is not
                                 Move.get_base_power.__func__ or
                                 move.damage_callback.__func__ is not
                                 Move.damage_callback.__func__),
                                'Found non-status move "%s" with no power' % move.name)

    def test_all_moves_have_valid_max_pp(self):
        for move in self.all_moves:
            if move not in (movedex['struggle'], movedex['confusiondamage']):
                self.assertIn(move.max_pp, _MAX_PP.values(),
                              'Found move "%s" with invalid max_pp' % move.name)

    def test_all_moves_in_randbatsstatistics_are_implemented(self):
        rbstats = RandbatsStatistics.from_pickle()
        unimplemented_moves = [move for move in rbstats.moves_index if move not in movedex]
        self.assertListEqual(unimplemented_moves, [])

    def test_all_secondary_effects_are_tuple(self): # not a single secondary_effect object (it's
                                                    # easy to miss the comma)
        for move in self.all_moves:
            self.assertIsInstance(move.secondary_effects, tuple)

    def test_all_moves_accuracy_in_range(self):
        for move in self.all_moves:
            if move.accuracy is not None:
                self.assertGreaterEqual(move.accuracy, 50)
                self.assertLessEqual(move.accuracy, 100)

    def test_all_moves_recoil_in_range(self):
        for move in self.all_moves:
            if move.recoil is not None:
                self.assertGreaterEqual(move.recoil, -1)
                self.assertLessEqual(move.recoil, 50)

    def test_targets_user_moves_dont_have_inappropriate_attributes(self):
        for move in self.all_moves:
            if move.targets_user:
                if move != movedex['confusiondamage']:
                    self.assertEqual(move.category, MoveCategory.STATUS, move)
                self.assertIsNone(move.accuracy, move)
                self.assertFalse(move.is_protectable, move)
                self.assertIsNone(move.multihit, move)
                self.assertFalse(move.secondary_effects, move)
                self.assertFalse(move.recoil, move)
                self.assertIsNone(move.target_status, move)
                self.assertIsNone(move.drain, move)

    def test_damage_callback_moves_have_attribute(self):
        for move in self.all_moves:
            if move.damage_callback.__func__ != Move.damage_callback.__func__:
                self.assertTrue(move.has_damage_callback)
            else:
                self.assertFalse(move.has_damage_callback)

class TestMoves(MultiMoveTestCase):
    """
    Moves that have general cases (damage only, status only, secondary effects, etc.) are tested
    in tests.test_battleengine. This suite is for testing specific moves with unique effects.
    """
    def test_double_batonpass(self):
        """
        Regression: Using batonpass twice in a row would cause an infinite loop calling run_switch
        back and forth between the two pokemon.
        """
        self.add_pokemon('flareon', 0)
        self.choose_move(self.vaporeon, 'batonpass')
        self.choose_move(self.leafeon, 'bugbuzz')
        self.run_turn()
        self.choose_move(self.flareon, 'batonpass')
        self.choose_move(self.leafeon, 'recover')
        self.run_turn()

    def test_acrobatics(self):
        self.vaporeon.item = itemdex['lightclay']
        damage = self.engine.use_move(self.vaporeon, movedex['acrobatics'], self.leafeon)
        self.assertEqual(damage, 54)
        self.vaporeon.take_item()
        damage = self.engine.use_move(self.vaporeon, movedex['acrobatics'], self.leafeon)
        self.assertEqual(damage, 106)

    def test_aromatherapy(self):
        self.add_pokemon('flareon', 1)
        self.add_pokemon('sylveon', 1)

        self.engine.set_status(self.sylveon, Status.SLP, None)
        self.engine.faint(self.flareon, Cause.OTHER)
        self.engine.set_status(self.leafeon, Status.PSN, None)

        self.engine.use_move(self.leafeon, movedex['aromatherapy'], self.vaporeon)

        self.assertIsNone(self.leafeon.status)
        self.assertIsNone(self.sylveon.status)
        self.assertFainted(self.flareon)

    def test_autotomize_under_100kg(self):
        damage = self.engine.use_move(self.vaporeon, movedex['autotomize'], self.leafeon)
        self.assertIsNone(damage)
        self.assertEqual(self.vaporeon.weight, 0.1)

    def test_autotomize_over_100kg(self):
        self.new_battle('aggron', 'flareon')
        self.engine.use_move(self.aggron, movedex['autotomize'], self.flareon)
        self.assertEqual(self.aggron.weight, self.aggron.pokedex_entry.weight - 100)
        self.engine.use_move(self.aggron, movedex['autotomize'], self.flareon)
        self.assertEqual(self.aggron.weight, self.aggron.pokedex_entry.weight - 200)
        self.engine.use_move(self.aggron, movedex['autotomize'], self.flareon)
        self.assertEqual(self.aggron.weight, self.aggron.pokedex_entry.weight - 300)
        damage = self.engine.use_move(self.aggron, movedex['autotomize'], self.flareon)
        self.assertEqual(damage, FAIL)
        self.assertEqual(self.aggron.weight, self.aggron.pokedex_entry.weight - 300)

    def test_avalanche_move_first(self):
        damage = self.engine.use_move(self.leafeon, movedex['avalanche'], self.vaporeon)
        self.assertEqual(damage, 42)

    def test_avalanche_no_damage_taken(self):
        self.engine.use_move(self.vaporeon, movedex['toxic'], self.leafeon)
        damage = self.engine.use_move(self.leafeon, movedex['avalanche'], self.vaporeon)
        self.assertEqual(damage, 42)

    def test_avalanche_with_damage_taken(self):
        self.engine.use_move(self.vaporeon, movedex['dragonclaw'], self.leafeon)
        damage = self.engine.use_move(self.leafeon, movedex['avalanche'], self.vaporeon)
        self.assertEqual(damage, 83)

    def test_avalanche_with_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'avalanche')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 42)

        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'avalanche')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 42 + 83)

    def test_batonpass_boosts(self):
        self.add_pokemon('flareon', 0)
        self.vaporeon.apply_boosts(Boosts(spe=2, atk=-3))
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertEqual(self.engine.battlefield.sides[0].active_pokemon, self.flareon)
        self.assertEqual(self.flareon.boosts, Boosts(spe=2, atk=-3))
        self.assertFalse(self.flareon.has_effect(Volatile.BATONPASS))
        self.assertNotIn(Volatile.BATONPASS, self.flareon._effect_index)

    @patch('random.randrange', lambda _: 1) # no confusion damage
    def test_batonpass_effect(self):
        self.add_pokemon('flareon', 0)
        self.vaporeon.confuse()
        self.vaporeon.set_effect(effects.Yawn())
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertEqual(self.engine.battlefield.sides[0].active_pokemon, self.flareon)
        self.assertTrue(self.flareon.has_effect(Volatile.CONFUSE)) # should be batonpassed
        self.assertFalse(self.flareon.has_effect(Volatile.YAWN))   # should not be batonpassed

    def test_bellydrum_successful(self):
        damage = self.engine.use_move(self.vaporeon, movedex['bellydrum'], self.leafeon)
        self.assertIsNone(damage)
        self.assertEqual(self.vaporeon.hp, 201)
        self.assertEqual(self.vaporeon.boosts['atk'], 6)

    def test_bellydrum_with_low_hp(self):
        self.vaporeon.hp = 100
        damage = self.engine.use_move(self.vaporeon, movedex['bellydrum'], self.leafeon)
        self.assertEqual(damage, FAIL)
        self.assertEqual(self.vaporeon.hp, 100)
        self.assertEqual(self.vaporeon.boosts['atk'], 0)

    def test_bellydrum_fails_already_maxed_atk(self):
        self.vaporeon.apply_boosts(Boosts(atk=6))
        damage = self.engine.use_move(self.vaporeon, movedex['bellydrum'], self.leafeon)
        self.assertEqual(damage, FAIL)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertEqual(self.vaporeon.boosts['atk'], 6)

    def test_shedinja_cant_use_bellydrum(self):
        self.new_battle('shedinja', 'leafeon')
        damage = self.engine.use_move(self.shedinja, movedex['bellydrum'], self.leafeon)
        self.assertEqual(damage, FAIL)
        self.assertEqual(self.shedinja.hp, 1)
        self.assertEqual(self.shedinja.boosts['atk'], 0)

    @patch('random.randrange', lambda _: 99) # miss
    def test_blizzard_accuracy_in_hail(self):
        self.engine.battlefield.set_weather(Weather.HAIL)
        self.engine.use_move(self.vaporeon, movedex['blizzard'], self.leafeon)
        self.assertFainted(self.leafeon)

    @patch('random.randrange', lambda _: 1) # no miss
    def test_bounce(self):
        self.vaporeon.apply_boosts(Boosts(spe=3))
        self.choose_move(self.vaporeon, 'bounce')
        self.choose_move(self.leafeon, 'flamecharge')
        self.run_turn()

        # vaporeon should not have been hit
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertTrue(self.vaporeon.has_effect(Volatile.TWOTURNMOVE))
        # mid-twoturnmove, can only select same move
        self.assertMoveChoices(self.vaporeon, {movedex['bounce']})

        self.choose_move(self.vaporeon, 'bounce')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 84)
        self.assertDamageTaken(self.vaporeon, 142)

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_bounce_hit_by_thunder(self):
        bounce = movedex['bounce']
        with patch.object(bounce, 'secondary_effects', ()): # no paralysis
            self.vaporeon.apply_boosts(Boosts(spe=3))
            self.choose_move(self.vaporeon, bounce)
            self.choose_move(self.leafeon, 'thunder')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 130)
            self.assertDamageTaken(self.leafeon, 0)

    def test_bounce_resets_next_turn_if_disabled(self):
        """
        If a mid-bounce pokemon gets disabled (via no guard for example) it should remain airborne
        until the second phase, at which point it WILL have bounce as its only choice, but when
        attempted it will fail (due to disable, as though disable had just been applied), and
        the pokemon will then no longer be airborne (can be hit normally).
        """
        self.new_battle(p0_ability='noguard')
        self.choose_move(self.leafeon, 'bounce')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {'bounce'})
        self.assertTrue(self.leafeon.has_effect(Volatile.TWOTURNMOVE))

        self.choose_move(self.leafeon, 'bounce')
        self.vaporeon.suppress_ability(self.engine)
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 24)

    def test_brickbreak(self):
        self.add_pokemon('gengar', 1)
        self.choose_move(self.leafeon, 'reflect')
        self.choose_move(self.vaporeon, 'brickbreak')
        self.run_turn()

        self.assertFalse(self.leafeon.side.has_effect(SideCondition.REFLECT))
        self.assertDamageTaken(self.leafeon, 37)

        self.choose_switch(self.leafeon, self.gengar)
        self.run_turn()
        self.choose_move(self.gengar, 'reflect')
        self.choose_move(self.vaporeon, 'brickbreak')
        self.run_turn()

        self.assertDamageTaken(self.gengar, 0)
        self.assertTrue(self.gengar.side.has_effect(SideCondition.REFLECT))

        self.choose_switch(self.gengar, self.leafeon)
        self.run_turn()
        self.choose_move(self.leafeon, 'protect')
        self.choose_move(self.vaporeon, 'brickbreak')
        self.run_turn()

        self.assertTrue(self.leafeon.side.has_effect(SideCondition.REFLECT))

    def test_bugbite_and_pluck(self):
        for eatberry in ('bugbite', 'pluck'):
            self.new_battle(p0_ability='noguard', p1_item='sitrusberry',
                            p0_moves=(eatberry, 'sleeptalk'))
            self.add_pokemon('espeon', 1, item='lumberry')
            self.add_pokemon('jolteon', 1, item='chestoberry')
            self.add_pokemon('alakazam', 1, item='custapberry')
            self.add_pokemon('dedenne', 1, item='petayaberry')
            self.add_pokemon('gengar', 1, item='weaknesspolicy')
            self.leafeon.hp = (self.leafeon.max_hp / 2) + 10
            self.choose_move(self.leafeon, 'leafstorm')
            self.choose_move(self.vaporeon, eatberry)
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 230 - (self.vaporeon.max_hp / 4))
            self.assertEqual(self.leafeon.hp, (self.leafeon.max_hp / 2) + 10 - 60)
            self.assertItem(self.leafeon, None)

            self.choose_switch(self.leafeon, self.espeon)
            self.run_turn()
            self.choose_move(self.espeon, 'toxic')
            self.choose_move(self.vaporeon, eatberry)
            self.run_turn()

            self.assertDamageTaken(self.espeon, 110 if eatberry == 'bugbite' else 55)
            self.assertItem(self.espeon, None)
            self.assertStatus(self.vaporeon, None)

            self.choose_switch(self.espeon, self.jolteon)
            self.run_turn()
            self.choose_move(self.jolteon, 'spore')
            self.choose_move(self.vaporeon, 'sleeptalk')
            self.run_turn()

            self.assertItem(self.jolteon, None)
            self.assertStatus(self.vaporeon, None)

            self.choose_switch(self.jolteon, self.alakazam)
            self.engine.heal(self.vaporeon, 400)
            self.alakazam.hp = 100
            self.run_turn()
            self.choose_move(self.alakazam, 'aerialace')
            self.choose_move(self.vaporeon, eatberry)
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 45)
            self.assertItem(self.alakazam, None)
            if eatberry == 'bugbite':
                self.assertFainted(self.alakazam)
                self.choose_switch(self.leafeon, self.dedenne)
            else:
                self.assertEqual(self.alakazam.hp, 100 - 68)
                self.choose_switch(self.alakazam, self.dedenne)

            self.choose_move(self.vaporeon, eatberry)
            self.run_turn()

            self.assertDamageTaken(self.dedenne, 28)
            self.assertBoosts(self.vaporeon, {'spa': 1})

            self.choose_switch(self.dedenne, self.gengar)
            self.choose_move(self.vaporeon, eatberry)
            self.run_turn()

            self.assertItem(self.gengar, 'weaknesspolicy')

    def test_bugbite_sitrusberry_loses_to_ironbarbs(self):
        self.new_battle(p1_item='sitrusberry', p1_ability='ironbarbs')
        self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'bugbite')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertItem(self.leafeon, 'sitrusberry')

    def test_clearsmog(self):
        self.leafeon.apply_boosts(Boosts(atk=2, spa=-3))
        self.vaporeon.apply_boosts(Boosts(spd=1))
        self.choose_move(self.leafeon, 'swordsdance')
        self.choose_move(self.vaporeon, 'clearsmog')
        self.run_turn()

        self.assertFalse(self.leafeon.boosts)
        self.assertEqual(self.vaporeon.boosts['spd'], 1)

    def test_copycat_no_previous_move(self):
        self.choose_move(self.leafeon, 'copycat') # should fail because leafeon's faster
        self.choose_move(self.vaporeon, 'fusionbolt')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_copycat_copy_same_turn(self):
        self.choose_move(self.leafeon, 'flamewheel')
        self.choose_move(self.vaporeon, 'copycat')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 42)
        self.assertDamageTaken(self.leafeon, 60)

    def test_copycat_copy_previous_turn(self):
        self.choose_move(self.leafeon, 'splash')
        self.choose_move(self.vaporeon, 'leafblade')
        self.run_turn()
        self.choose_move(self.leafeon, 'copycat')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    def test_copycat_copies_copycatted_move(self):
        self.add_pokemon('umbreon', 1)
        self.choose_move(self.leafeon, 'dragonclaw')
        self.choose_move(self.vaporeon, 'copycat')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39)
        self.assertDamageTaken(self.vaporeon, 112)

        self.vaporeon.apply_boosts(Boosts(spe=2))
        self.choose_switch(self.leafeon, self.umbreon)
        self.choose_move(self.vaporeon, 'copycat')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 45)

        self.choose_move(self.umbreon, 'copycat')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112 + 73)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_copycat_fails_on_NO_COPYCAT_moves(self):
        circlethrow = movedex['circlethrow']
        with patch.object(circlethrow, 'priority', 0):
            self.choose_move(self.leafeon, circlethrow)
            self.choose_move(self.vaporeon, 'copycat')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 84)
            self.assertDamageTaken(self.leafeon, 0)

            result = self.engine.use_move(self.vaporeon, movedex['copycat'], self.leafeon)
            self.assertEqual(result, FAIL)

    def test_copycat_two_turn_move(self):
        self.new_battle(p0_moves=('copycat', 'scald'),
                        p1_moves=('leafblade', 'phantomforce'), any_move=False)
        self.choose_move(self.leafeon, 'phantomforce')
        self.choose_move(self.vaporeon, 'copycat')
        self.run_turn()
        self.assertTrue(self.leafeon.has_effect(Volatile.TWOTURNMOVE))
        self.assertTrue(self.vaporeon.has_effect(Volatile.TWOTURNMOVE))
        self.assertMoveChoices(self.vaporeon, {'phantomforce'})
        self.choose_move(self.leafeon, 'phantomforce')
        self.choose_move(self.vaporeon, 'phantomforce')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 44)
        self.assertFalse(self.vaporeon.has_effect(Volatile.TWOTURNMOVE))

    def test_counter_success(self):
        self.choose_move(self.leafeon, 'counter')
        self.choose_move(self.vaporeon, 'dragonclaw')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39)
        self.assertDamageTaken(self.vaporeon, 39 * 2)

    def test_counter_vs_special_move(self):
        self.choose_move(self.leafeon, 'counter')
        self.choose_move(self.vaporeon, 'aurasphere')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 105)
        self.assertDamageTaken(self.vaporeon, 0)

    @patch('random.choice', lambda _: 3) # hit 3 times
    def test_counter_vs_multihit(self):
        self.choose_move(self.vaporeon, 'bulletseed')
        self.choose_move(self.leafeon, 'counter')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 6 * 3) # x3 for 3 hits
        self.assertDamageTaken(self.vaporeon, 6 * 2) # x2 for doubling damage of last hit

    def test_counter_vs_switch(self):
        self.add_pokemon('espeon', 0)
        self.choose_move(self.vaporeon, 'dragonclaw')
        self.run_turn()

        self.choose_move(self.leafeon, 'counter')
        self.choose_switch(self.vaporeon, self.espeon)
        self.run_turn()

        self.assertDamageTaken(self.espeon, 0)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_counter_one_turn_later(self):
        self.choose_move(self.vaporeon, 'dragonclaw')
        self.run_turn()

        self.choose_move(self.leafeon, 'counter')
        self.choose_move(self.vaporeon, 'circlethrow')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 39 + 30) # dragonclaw + circlethrow

    def test_defog_clears_foe_lightscreen(self):
        self.choose_move(self.leafeon, 'lightscreen')
        self.choose_move(self.vaporeon, 'lightscreen')
        self.run_turn()
        self.choose_move(self.leafeon, 'defog')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertListEqual(self.engine.battlefield.sides[0].effects, [])
        self.assertEqual(self.vaporeon.boosts['evn'], -1)
        self.assertDamageTaken(self.leafeon, 44)

    def test_defog_clears_hazards_both_sides(self):
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'stickyweb')
        self.run_turn()
        self.choose_move(self.leafeon, 'toxicspikes')
        self.choose_move(self.vaporeon, 'stealthrock')
        self.run_turn()
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'defog')
        self.run_turn()

        [self.assertListEqual(self.engine.battlefield.sides[i].effects, [])
         for i in (0, 1)]

    def test_destinybond(self):
        self.vaporeon.apply_boosts(Boosts(spa=6))
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_destinybond_next_turn(self):
        self.vaporeon.apply_boosts(Boosts(spa=6))
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'flareblitz')
        self.run_turn()
        self.choose_move(self.vaporeon, 'vacuumwave')
        self.choose_move(self.leafeon, 'circlethrow')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_destinybond_ends_at_next_move(self):
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'bugbuzz')
        self.run_turn()
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'bugbuzz')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertIsNone(self.vaporeon.status)

    def test_destinybond_doesnt_activate_for_residual_damage(self):
        self.vaporeon.hp = 150
        self.engine.set_status(self.vaporeon, Status.BRN, None)
        self.choose_move(self.leafeon, 'return') # 142 damage
        self.choose_move(self.vaporeon, 'destinybond')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertIsNone(self.leafeon.status)

    @patch('random.randrange', lambda _: 0) # always parahax
    def test_destinybond_ends_on_paralysis_move_fail(self):
        self.leafeon.apply_boosts(Boosts(spe=6))
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertIsNone(self.vaporeon.status)

    def test_destinybond_faint_order(self):
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'scald')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)
        self.assertEqual(self.battlefield.win, self.vaporeon.side.index)

    def test_destinybond_bypasses_magicguard(self):
        self.new_battle(p0_ability='prankster', p1_ability='magicguard')
        self.choose_move(self.vaporeon, 'destinybond')
        self.choose_move(self.leafeon, 'woodhammer')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_destinybond_bypasses_focussash_and_sturdy(self):
        self.new_battle(p0_ability='prankster', p1_ability='toughclaws', p1_item='focussash')
        self.choose_move(self.vaporeon, 'destinybond')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

        self.new_battle(p0_item='choicescarf', p1_ability='sturdy')
        self.choose_move(self.vaporeon, 'destinybond')
        self.choose_move(self.leafeon, 'woodhammer')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_disable_removes_choice_and_restores_it_later(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['return'], movedex['leafblade'],
                                  movedex['uturn'], movedex['splash']))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['leafblade'], movedex['uturn'],
                                              movedex['splash']})

        for _ in range(4):      # disable lasts 4 turns
            self.choose_move(self.leafeon, 'splash')
            self.choose_move(self.vaporeon, 'splash')
            self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['return'], movedex['leafblade'],
                                              movedex['uturn'], movedex['splash']})

    def test_disable_prevents_move_used_same_turn(self):
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.engine.heal(self.leafeon, self.leafeon.max_hp)
        self.choose_move(self.leafeon, 'disable')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

    def test_disable_causes_struggle_when_its_the_last_available_move(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['return'], movedex['leafblade'],
                                  movedex['uturn'], movedex['splash']))
        self.leafeon.pp[movedex['leafblade']] = 0
        self.leafeon.pp[movedex['uturn']] = 0
        self.leafeon.pp[movedex['splash']] = 0
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['struggle']})

    def test_disable_fails_when_pokemon_already_disabled(self):
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()
        self.engine.init_turn()
        self.engine.run_move(self.leafeon, movedex['flamecharge'], self.vaporeon)

        self.assertEqual(self.engine.use_move(self.vaporeon, movedex['disable'], self.leafeon),
                         FAIL)

    def test_disable_fails_when_pokemon_out_of_pp(self):
        self.leafeon.pp[movedex['return']] = 1
        self.engine.init_turn()
        self.engine.run_move(self.leafeon, movedex['return'], self.vaporeon)

        self.assertEqual(self.engine.use_move(self.vaporeon, movedex['disable'], self.leafeon),
                         FAIL)

    def test_disable_fails_when_pokemon_has_not_used_move(self):
        self.add_pokemon('flareon', 1)
        self.choose_move(self.leafeon, 'disable')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()
        self.assertFalse(self.vaporeon.has_effect(Volatile.DISABLE))

        self.choose_move(self.leafeon, 'uturn')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.DISABLE))
        self.assertFalse(self.flareon.has_effect(Volatile.DISABLE))

    @patch('random.randint', lambda *_: 2) # two outrage turns
    def test_disable_vs_locking_moves(self):
        """
        If outrage is disabled during rampage, outrage is still selectable (LOCKEDMOVE overrides
        DISABLE), but it will fail when it is tried. The user can then use its other moves (but if
        the rampage is over it still gets confused)
        """
        self.choose_move(self.leafeon, 'outrage')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {'outrage'})
        self.assertTrue(self.leafeon.has_effect(Volatile.DISABLE))
        self.assertDamageTaken(self.vaporeon, 167)

        self.choose_move(self.leafeon, 'outrage')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 167)
        self.assertTrue(self.leafeon.has_effect(Volatile.CONFUSE))

    def test_electricterrain(self):
        self.new_battle('skarmory', 'flareon')
        self.flareon.apply_boosts(Boosts(spe=1))
        self.choose_move(self.flareon, 'electricterrain')
        self.choose_move(self.skarmory, 'spore')
        self.run_turn()

        self.assertIsNone(self.flareon.status)

        self.choose_move(self.flareon, 'hiddenpowerelectric')
        self.choose_move(self.skarmory, 'hiddenpowerelectric')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 24)
        self.assertDamageTaken(self.skarmory, 198)

        self.choose_move(self.flareon, 'spore')
        self.run_turn()
        self.assertEqual(self.skarmory.status, Status.SLP)
        self.skarmory.cure_status()

        self.choose_move(self.flareon, 'magnetrise')
        self.choose_move(self.skarmory, 'spore')
        self.run_turn()

        self.assertEqual(self.flareon.status, Status.SLP)

    def test_encore_modifies_move_choices(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['return'], movedex['leafblade'],
                                  movedex['uturn'], movedex['splash']))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        for _ in range(3):
            self.assertMoveChoices(self.leafeon, {movedex['return']})

            self.choose_move(self.leafeon, 'return')
            self.choose_move(self.vaporeon, 'recover')
            self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['return'], movedex['leafblade'],
                                              movedex['uturn'], movedex['splash']})

    def test_encore_overrides_move_choice(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['splash'],
                                  movedex['uturn'], movedex['toxic']))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()
        self.choose_move(self.leafeon, 'encore')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

    def test_encore_failure_cases(self):
        self.vaporeon.apply_boosts(Boosts(spe=-1))
        self.add_pokemon('umbreon', 1, moves=(movedex['toxic'], movedex['foulplay'],
                                              movedex['wish'], movedex['protect']))
        self.choose_move(self.leafeon, 'uturn')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        self.assertMoveChoices(self.umbreon, set(self.umbreon.moveset))

        self.umbreon.pp[movedex['toxic']] = 1
        self.choose_move(self.umbreon, 'toxic')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        self.assertMoveChoices(self.umbreon, set(self.umbreon.moveset) - {movedex['toxic']})

        self.choose_move(self.umbreon, 'encore')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        self.assertFalse(self.umbreon.has_effect(Volatile.ENCORE))
        self.assertFalse(self.vaporeon.has_effect(Volatile.ENCORE))

    def test_endeavor(self):
        self.leafeon.hp = 42
        self.choose_move(self.leafeon, 'endeavor')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 42)

        self.choose_move(self.leafeon, 'endeavor')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 42)

    def test_eruption(self):
        self.choose_move(self.leafeon, 'eruption')
        self.choose_move(self.vaporeon, 'hiddenpowerice')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 44)
        self.assertDamageTaken(self.leafeon, 158)
        self.choose_move(self.leafeon, 'eruption')
        self.choose_move(self.vaporeon, 'hiddenpowerdark')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 44 + 18)
        self.assertDamageTaken(self.leafeon, 158 + 79)
        self.choose_move(self.leafeon, 'eruption')
        self.choose_move(self.vaporeon, 'hiddenpowerfire')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 44 + 18 + 6)
        self.assertFainted(self.leafeon)

    def test_explosion_faints_user(self):
        self.choose_move(self.leafeon, 'explosion')
        self.run_turn()

        self.assertFainted(self.leafeon)

    def test_explosion_faints_user_even_if_no_target(self):
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'flareblitz')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_explosion_faints_user_even_if_target_immune(self):
        self.new_battle('leafeon', 'gengar')
        self.choose_move(self.leafeon, 'explosion')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertDamageTaken(self.gengar, 0)

    def test_extremespeed_priority(self):
        self.vaporeon.hp = self.leafeon.hp = 1
        self.vaporeon.apply_boosts(Boosts(spe=-6))
        self.leafeon.apply_boosts(Boosts(spe=6))
        self.choose_move(self.vaporeon, 'extremespeed')
        self.choose_move(self.leafeon, 'quickattack')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertFainted(self.leafeon)

    def test_facade(self):
        self.engine.set_status(self.vaporeon, Status.PSN, None)
        self.choose_move(self.vaporeon, 'facade')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 67)

    def test_facade_overcomes_burn(self):
        self.engine.set_status(self.vaporeon, Status.BRN, None)
        self.choose_move(self.vaporeon, 'facade')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 67)

    def test_fakeout(self):
        self.add_pokemon('jolteon', 1)
        self.add_pokemon('flareon', 0)
        self.vaporeon.hp = 1
        self.vaporeon.apply_boosts(Boosts(spe=-2))
        self.choose_move(self.vaporeon, 'fakeout')
        self.choose_move(self.leafeon, 'extremespeed')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.engine.faint(self.leafeon, Cause.OTHER)
        self.engine.resolve_faint_queue()

        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.jolteon, 'fakeout')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertDamageTaken(self.jolteon, 0)

        self.choose_move(self.flareon, 'return')
        self.choose_move(self.jolteon, 'fakeout')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 164)
        self.assertDamageTaken(self.flareon, 0)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_flyingpress(self):
        self.new_battle('vaporeon', 'sawsbuck')
        damage = self.engine.use_move(self.vaporeon, movedex['flyingpress'], self.sawsbuck)
        self.assertEqual(damage, 260)

        self.new_battle('vaporeon', 'heliolisk')
        damage = self.engine.use_move(self.vaporeon, movedex['flyingpress'], self.heliolisk)
        self.assertEqual(damage, 81)

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_focuspunch(self):
        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.leafeon, 'focuspunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, 'toxic')
        self.choose_move(self.leafeon, 'focuspunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)
        self.assertDamageTaken(self.vaporeon, 208)

        self.choose_move(self.vaporeon, 'focusblast')
        self.choose_move(self.leafeon, 'focuspunch')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    def test_focuspunch_two_in_a_row(self):
        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.leafeon, 'focuspunch')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 0)
        self.choose_move(self.vaporeon, 'circlethrow')
        self.choose_move(self.leafeon, 'focuspunch')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 208)

    def test_foulplay(self):
        self.leafeon.apply_boosts(Boosts(atk=3))
        self.vaporeon.apply_boosts(Boosts(atk=-3))
        damage = self.engine.use_move(self.vaporeon, movedex['foulplay'], self.leafeon)
        self.assertEqual(damage, 174)

    @patch('random.randrange', lambda _: 99) # no freeze
    def test_freezedry(self):
        self.new_battle('vaporeon', 'swampert')
        self.choose_move(self.vaporeon, 'freezedry')
        self.choose_move(self.swampert, 'freezedry')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 110)
        self.assertDamageTaken(self.swampert, 284)

    def test_grassknot(self):
        self.new_battle('swampert', 'leafeon')
        self.choose_move(self.leafeon, 'grassknot')
        self.run_turn()
        self.assertDamageTaken(self.swampert, 300)

        self.new_battle('phione', 'leafeon')
        self.choose_move(self.leafeon, 'grassknot')
        self.run_turn()
        self.assertDamageTaken(self.phione, 44)

        self.new_battle('aggron', 'leafeon')
        self.choose_move(self.leafeon, 'grassknot')
        self.run_turn()
        self.assertDamageTaken(self.aggron, 153)

    def test_growth_in_sun(self):
        self.choose_move(self.leafeon, 'growth')
        self.run_turn()
        self.assertEqual(self.leafeon.boosts['atk'], 1)

        self.engine.battlefield.set_weather(Weather.DESOLATELAND)
        self.choose_move(self.leafeon, 'growth')
        self.run_turn()
        self.assertEqual(self.leafeon.boosts['atk'], 3)

    def test_gyroball(self):
        self.vaporeon.apply_boosts(Boosts(spe=6))
        self.choose_move(self.leafeon, 'gyroball')
        self.choose_move(self.vaporeon, 'gyroball')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 5)
        self.assertDamageTaken(self.vaporeon, 51)

        self.new_battle('ferrothorn', 'deoxysspeed')
        self.choose_move(self.ferrothorn, 'gyroball')
        self.choose_move(self.deoxysspeed, 'gyroball')
        self.run_turn()

        self.assertDamageTaken(self.ferrothorn, 2)
        self.assertDamageTaken(self.deoxysspeed, 172)

    def test_haze(self):
        self.vaporeon.apply_boosts(Boosts(def_=2, atk=-2))
        self.leafeon.apply_boosts(Boosts(spd=1))
        self.choose_move(self.leafeon, 'haze')
        self.choose_move(self.vaporeon, 'dragonclaw')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39)
        self.assertEqual(self.leafeon.boosts, Boosts())
        self.assertEqual(self.vaporeon.boosts, Boosts())

    def test_haze_doesnt_fail_with_no_foe(self):
        self.add_pokemon('flareon', 1)
        self.choose_move(self.leafeon, 'memento')
        self.choose_move(self.vaporeon, 'haze')
        self.run_turn()

        self.assertFalse(self.vaporeon.boosts)

    def test_healingwish(self):
        self.add_pokemon('flareon', 1)
        self.flareon.hp = 100
        self.flareon.status = Status.PAR
        self.choose_move(self.leafeon, 'healingwish')
        self.choose_move(self.vaporeon, 'scald')
        self.run_turn()

        self.assertFainted(self.leafeon)

        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.flareon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 230)
        self.assertDamageTaken(self.vaporeon, 164)

    def test_healingwish_fail_for_last_pokemon(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('umbreon', 0)
        for pokemon in (self.flareon, self.jolteon, self.umbreon):
            pokemon.hp = 0
            pokemon.status = Status.FNT
        self.choose_move(self.vaporeon, 'healingwish')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertListEqual(self.engine.battlefield.sides[0].effects, [])

    def test_heavyslam(self):
        self.new_battle('phione', 'leafeon')
        self.choose_move(self.phione, 'heavyslam')
        self.choose_move(self.leafeon, 'heavyslam')
        self.run_turn()
        self.assertDamageTaken(self.phione, 66)
        self.assertDamageTaken(self.leafeon, 24)

        self.new_battle('aggron', 'leafeon')
        self.choose_move(self.aggron, 'heavyslam')
        self.choose_move(self.leafeon, 'heavyslam')
        self.run_turn()
        self.assertDamageTaken(self.aggron, 23)
        self.assertDamageTaken(self.leafeon, 133)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_highjumpkick_success(self):
        self.choose_move(self.vaporeon, 'highjumpkick')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 63)
        self.assertDamageTaken(self.vaporeon, 0)

    @patch('random.randrange', lambda _: 99) # miss
    def test_highjumpkick_miss(self):
        self.choose_move(self.vaporeon, 'highjumpkick')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 200)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_highjumpkick_fail(self):
        self.choose_move(self.vaporeon, 'highjumpkick')
        self.choose_move(self.leafeon, 'protect')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 200)

    def test_highjumpkick_fails_without_crash_vs_no_target(self):
        self.choose_move(self.leafeon, 'memento')
        self.choose_move(self.vaporeon, 'highjumpkick')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_hurricane(self):
        self.battlefield.set_weather(Weather.SUNNYDAY)
        with patch('random.randrange', lambda _: 51): # miss at 50%
            self.choose_move(self.vaporeon, 'hurricane')
            self.run_turn()
            self.assertDamageTaken(self.leafeon, 0)

        self.battlefield.set_weather(Weather.HAIL)
        with patch('random.randrange', lambda _: 71): # miss at 70%
            self.choose_move(self.vaporeon, 'hurricane')
            self.run_turn()
            self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)

        self.battlefield.set_weather(Weather.RAINDANCE)
        with patch('random.randrange', lambda _: 99): # miss if possible
            self.choose_move(self.vaporeon, 'hurricane')
            self.run_turn()
            self.assertFainted(self.leafeon)

        self.new_battle()
        self.battlefield.set_weather(Weather.SUNNYDAY)
        with patch('random.randrange', lambda _: 49): # hit at 50%
            self.choose_move(self.vaporeon, 'hurricane')
            self.run_turn()
            self.assertFainted(self.leafeon)

    def test_hyperspacefury_hoopaunbound_only(self):
        self.new_battle('hoopaunbound', 'leafeon')
        self.choose_move(self.hoopaunbound, 'hyperspacefury')
        self.choose_move(self.leafeon, 'hyperspacefury')
        self.run_turn()

        self.assertEqual(self.hoopaunbound.boosts['def'], -1)
        self.assertEqual(self.leafeon.boosts['def'], 0)
        self.assertDamageTaken(self.hoopaunbound, 0)

    def test_hyperspacefury_breaks_protect(self):
        self.new_battle('hoopaunbound', 'leafeon')
        self.choose_move(self.leafeon, 'protect')
        self.choose_move(self.hoopaunbound, 'hyperspacefury')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 154)

    @patch('random.randint', lambda *_: 5) # 4 turns + 1 non-damaging trap turn
    def test_infestation(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'infestation')
        self.run_turn()

        self.assertSwitchChoices(self.vaporeon, set())
        self.assertDamageTaken(self.vaporeon, 13 + self.vaporeon.max_hp / 8)

        for _ in range(3):
            self.run_turn()
            self.assertSwitchChoices(self.vaporeon, set())

        self.assertDamageTaken(self.vaporeon, 13 + 4 * self.vaporeon.max_hp / 8)

        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 13 + 4 * self.vaporeon.max_hp / 8)
        self.assertSwitchChoices(self.vaporeon, {self.flareon, self.umbreon})

    def test_infestation_is_batonpassed_properly(self):
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('flareon', 1)
        self.choose_move(self.leafeon, 'infestation')
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertTrue(self.jolteon.has_effect(Volatile.PARTIALTRAP))
        self.assertTrue(self.leafeon.get_effect(Volatile.TRAPPER).trappee == self.jolteon)
        self.assertDamageTaken(self.jolteon, self.jolteon.max_hp / 8)

        self.choose_switch(self.leafeon, self.flareon)
        self.run_turn()

        self.assertDamageTaken(self.jolteon, self.jolteon.max_hp / 8)
        self.assertFalse(self.jolteon.has_effect(Volatile.PARTIALTRAP))

    def test_infestation_released_when_trapper_switches_out(self):
        self.add_pokemon('espeon', 0)
        self.choose_move(self.leafeon, 'infestation')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertEqual(self.engine.battlefield.sides[0].active_pokemon, self.espeon)
        self.assertActive(self.espeon)
        self.assertSwitchChoices(self.espeon, {self.vaporeon})
        self.assertDamageTaken(self.vaporeon, 13)
        for pokemon in [self.espeon, self.vaporeon, self.leafeon]:
            self.assertFalse(pokemon.has_effect(Volatile.TRAPPER))
            self.assertFalse(pokemon.has_effect(Volatile.PARTIALTRAP))

    def test_infestation_released_when_trapper_faints(self):
        self.add_pokemon('espeon', 0)
        self.add_pokemon('glaceon', 1)
        self.choose_move(self.leafeon, 'infestation')
        self.choose_move(self.vaporeon, 'eruption')
        self.run_turn()

        for pokemon in (self.vaporeon, self.leafeon):
            self.assertFalse(pokemon.has_effect(Volatile.PARTIALTRAP))
            self.assertFalse(pokemon.has_effect(Volatile.TRAPPER))
        self.assertDamageTaken(self.vaporeon, 13)

    def test_infestation_when_trappee_faints(self):
        self.add_pokemon('espeon', 0)
        self.add_pokemon('glaceon', 1)
        self.choose_move(self.leafeon, 'infestation')
        self.run_turn()
        self.choose_move(self.leafeon, 'woodhammer')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.TRAPPER))

    def test_infestation_doesnt_trap_ghosts(self):
        self.new_battle('gengar', 'leafeon')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'infestation')
        self.run_turn()

        self.assertSwitchChoices(self.gengar, {self.flareon})

    def test_infestation_ko(self):
        self.new_battle(p0_item='lifeorb', p1_item='rockyhelmet')
        self.add_pokemon('espeon', 1)
        self.leafeon.hp = 10
        self.choose_move(self.vaporeon, 'infestation')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFalse(self.vaporeon.has_effect(Volatile.TRAPPER))
        self.engine.init_turn()
        self.assertActive(self.espeon)

    def test_infestation_user_faints(self):
        self.new_battle(p1_item='rockyhelmet')
        self.add_pokemon('flareon', 0)
        self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'infestation')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertFalse(self.leafeon.has_effect(Volatile.PARTIALTRAP))

    def test_kingsshield(self):
        self.choose_move(self.vaporeon, 'kingsshield')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertEqual(self.leafeon.boosts['atk'], -2)

    def test_kingsshield_against_status(self):
        self.choose_move(self.vaporeon, 'kingsshield')
        self.choose_move(self.leafeon, 'confuseray')
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    def test_kingsshield_against_noncontact_attack(self):
        self.choose_move(self.vaporeon, 'kingsshield')
        self.choose_move(self.leafeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertEqual(self.leafeon.boosts['atk'], 0)

    def test_knockoff(self):
        self.new_battle(p0_item='sitrusberry')
        self.leafeon.apply_boosts(Boosts(atk=1))
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 202)
        self.assertItem(self.vaporeon, None)

        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 202 + 136)

    def test_knockoff_fails_if_user_faints(self):
        self.new_battle(p0_item='rockyhelmet', p0_ability='ironbarbs')
        self.leafeon.hp = 75
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 135)
        self.assertFainted(self.leafeon)
        self.assertItem(self.vaporeon, 'rockyhelmet')

    def test_knockoff_vs_focussash_and_evolite(self):
        self.new_battle(p0_item='focussash')
        self.add_pokemon('chansey', 0, item='eviolite')
        self.leafeon.apply_boosts(Boosts(atk=4))
        self.choose_move(self.leafeon, 'knockoff')
        self.choose_move(self.vaporeon, 'haze')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 1)
        self.assertItem(self.vaporeon, None)

        self.choose_switch(self.vaporeon, self.chansey)
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.chansey, 304)

        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.chansey, 304 + 305)

    def test_knockoff_hits_substitute(self):
        self.new_battle(p1_item='heatrock')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)
        self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                         self.leafeon.max_hp / 4 - 47)
        self.assertItem(self.leafeon, 'heatrock')

    def test_knockoff_vs_drives_and_plates(self):
        self.new_battle('arceuspoison', 'genesectdouse',
                        p0_item='toxicplate', p0_ability='multitype',
                        p1_item='dousedrive')
        self.choose_move(self.arceuspoison, 'knockoff')
        self.choose_move(self.genesectdouse, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.arceuspoison, 56)
        self.assertDamageTaken(self.genesectdouse, 68)

    def test_knockoff_berry(self):
        self.new_battle(p0_item='sitrusberry')
        self.leafeon.apply_boosts(Boosts(atk=2))
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 269)
        self.assertItem(self.vaporeon, None)

    def test_knockoff_choice_item(self):
        self.new_battle(p0_item='choiceband',
                        p0_moves=('return', 'protect', 'toxic', 'surf'))
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.choose_move(self.leafeon, 'knockoff')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertMoveChoices(self.vaporeon, {'return', 'protect', 'toxic', 'surf'})

    def test_knockoff_ko_target(self):
        self.new_battle(p0_item='lumberry', p0_ability='unburden')
        self.leafeon.apply_boosts(Boosts(atk=4))
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_leechseed_residual(self):
        self.leafeon.hp = 100
        self.choose_move(self.leafeon, 'leechseed')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 50)
        self.assertEqual(self.leafeon.hp, 150)

        self.vaporeon.hp = 10
        self.leafeon.hp = 100
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 110)
        self.assertFainted(self.vaporeon)

    def test_leechseed_grass_immunity(self):
        result = self.engine.use_move(self.vaporeon, movedex['leechseed'], self.leafeon)
        self.assertEqual(result, FAIL)

    def test_leechseed_removed_on_switch(self):
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'leechseed')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()

        self.assertActive(self.umbreon)
        self.assertDamageTaken(self.umbreon, 0)
        self.assertFalse(self.umbreon.has_effect(Volatile.LEECHSEED))

    def test_lightscreen_damage_calculations(self):
        self.choose_move(self.leafeon, 'protect')
        self.choose_move(self.vaporeon, 'lightscreen')
        self.run_turn()

        damage = self.engine.use_move(self.leafeon, movedex['vacuumwave'], self.vaporeon)
        self.assertEqual(damage, 12)

        damage = self.engine.use_move(self.leafeon, movedex['earthquake'], self.vaporeon)
        self.assertEqual(damage, 139)

    def test_crit_breaks_through_lightscreen(self):
        self.engine.get_critical_hit = lambda crit: True
        self.choose_move(self.leafeon, 'lightscreen')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 132)

    def test_lightscreen_wears_off(self):
        self.choose_move(self.vaporeon, 'lightscreen')
        self.run_turn()

        for _ in range(4):
            damage = self.engine.use_move(self.leafeon, movedex['vacuumwave'], self.vaporeon)
            self.assertEqual(damage, 12)
            self.run_turn()

        damage = self.engine.use_move(self.leafeon, movedex['vacuumwave'], self.vaporeon)
        self.assertEqual(damage, 25)

    def test_magiccoat_bounce_status(self):
        self.add_pokemon('umbreon', 0)
        self.add_pokemon('flareon', 1)
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'magiccoat')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.PAR)
        self.assertIsNone(self.vaporeon.status)

        self.leafeon.cure_status()
        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.PAR)

        self.vaporeon.cure_status()
        self.choose_move(self.leafeon, 'roar')
        self.choose_move(self.vaporeon, 'magiccoat')
        self.run_turn()

        self.assertActive(self.flareon)
        self.assertActive(self.vaporeon)
        self.assertFalse(self.leafeon.is_active)

        self.choose_move(self.flareon, 'magiccoat')
        self.choose_move(self.vaporeon, 'taunt')
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.TAUNT))
        self.assertFalse(self.flareon.has_effect(Volatile.TAUNT))

    def test_magiccoat_bounce_encore_but_fails(self):
        self.choose_move(self.leafeon, 'encore')
        self.choose_move(self.vaporeon, 'magiccoat')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ENCORE))
        self.assertFalse(self.vaporeon.has_effect(Volatile.ENCORE))

    def test_magiccoat_no_bounce_attack(self):
        self.choose_move(self.leafeon, 'earthquake')
        self.choose_move(self.vaporeon, 'magiccoat')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 139)

        self.choose_move(self.leafeon, 'magiccoat')
        self.choose_move(self.vaporeon, 'recover')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    def test_magnetrise(self):
        self.choose_move(self.leafeon, 'magnetrise')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)

    def test_memento(self):
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('espeon', 1)
        self.choose_move(self.vaporeon, 'memento')
        self.choose_move(self.leafeon, 'protect')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertIsNone(self.leafeon.status)

        self.choose_move(self.leafeon, 'explosion')
        self.choose_move(self.vaporeon, 'memento')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertDamageTaken(self.vaporeon, 346)

        self.choose_move(self.vaporeon, 'memento')
        self.choose_move(self.espeon, 'magiccoat')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertTrue(self.espeon.boosts['atk'] == self.espeon.boosts['spa'] == -2)

    def test_metalburst(self):
        self.add_pokemon('jolteon', 1)
        self.choose_switch(self.leafeon, self.jolteon)
        self.choose_move(self.vaporeon, 'metalburst')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 0)

        self.choose_move(self.jolteon, 'metalburst')
        self.choose_move(self.vaporeon, 'metalburst')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 0)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.jolteon, 'return')
        self.choose_move(self.vaporeon, 'metalburst')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 93)
        self.assertDamageTaken(self.jolteon, int(93 * 1.5))

        self.choose_move(self.jolteon, 'metalburst')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 93)

    def test_mirrorcoat(self):
        self.choose_move(self.leafeon, 'mirrorcoat')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)
        self.assertDamageTaken(self.vaporeon, 2 * 88)
        self.choose_move(self.leafeon, 'mirrorcoat')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88 + 24)
        self.assertDamageTaken(self.vaporeon, 2 * 88)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, 'mirrorcoat')
        self.choose_move(self.vaporeon, 'nightshade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 200)

    def test_moonlight(self):
        self.engine.battlefield.set_weather(Weather.SUNNYDAY)
        self.vaporeon.hp = 1
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'moonlight')
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 182)

        self.engine.battlefield.set_weather(Weather.RAINDANCE)
        self.choose_move(self.vaporeon, 'morningsun')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 101)

    def test_nightshade(self):
        self.new_battle('vaporeon', 'leafeon', p0_level=42)
        self.choose_move(self.vaporeon, 'nightshade')
        self.choose_move(self.leafeon, 'nightshade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 100)
        self.assertDamageTaken(self.leafeon, 42)

    def test_painsplit(self):
        self.choose_move(self.vaporeon, 'painsplit')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 336)
        self.assertEqual(self.leafeon.hp, self.leafeon.max_hp)

        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'painsplit')
        self.run_turn()

        self.assertTrue(self.vaporeon.hp == self.leafeon.hp == 168)

    def test_partingshot(self):
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, 'partingshot')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertActive(self.espeon)
        self.assertDamageTaken(self.espeon, 87)

    def test_perishsong(self):
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'perishsong')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()         # 3 left

        self.run_turn()         # 2 left

        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()         # 1 left

        self.assertIsNone(self.leafeon.status)
        self.assertIsNone(self.umbreon.status)
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.umbreon)
        self.assertIsNone(self.vaporeon.status)

    def test_phantomforce(self):
        self.add_pokemon('flareon', 1)
        self.choose_move(self.leafeon, 'phantomforce')
        self.choose_move(self.vaporeon, 'aerialace')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertMoveChoices(self.leafeon, {movedex['phantomforce']})
        self.assertSwitchChoices(self.leafeon, set())

        self.choose_move(self.leafeon, 'phantomforce')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 126)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_protect_doesnt_block_first_turn_of_charge_move(self):
        self.choose_move(self.leafeon, 'bounce')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertTrue(self.leafeon.has_effect(Volatile.TWOTURNMOVE))

        self.choose_move(self.leafeon, 'bounce')
        self.choose_move(self.vaporeon, 'quickattack')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 119)

    def test_protect_doesnt_block_user_targeting_move(self):
        self.choose_move(self.leafeon, 'swordsdance')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertEqual(self.leafeon.boosts['atk'], 2)

    def test_protect_blocks_attacking_move(self):
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    @patch('random.randrange', lambda _: 1) # fail the roll to get a second protect
    def test_protect_fails_second_time_then_succeeds_third_time(self):
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    @patch('random.randrange', lambda _: 1) # no parahax, no miss
    def test_psychoshift(self):
        self.leafeon.apply_boosts(Boosts(spe=6))
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'psychoshift')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertEqual(self.leafeon.status, Status.PAR)

        self.choose_move(self.leafeon, 'toxic')
        self.choose_move(self.vaporeon, 'psychoshift')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.PAR)
        self.assertEqual(self.vaporeon.status, Status.TOX)

    def test_psychoshift_against_immune_pokemon(self):
        self.new_battle('muk', 'leafeon')
        self.engine.set_status(self.leafeon, Status.PSN, None)
        self.choose_move(self.leafeon, 'psychoshift')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.PSN)
        self.assertIsNone(self.muk.status)

    def test_psyshock(self):
        self.choose_move(self.vaporeon, 'psyshock')
        self.choose_move(self.leafeon, 'psystrike')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 86)
        self.assertDamageTaken(self.leafeon, 60)

    def test_pursuit_vs_switch(self):
        self.add_pokemon('umbreon', 1)
        self.choose_switch(self.leafeon, self.umbreon)
        self.choose_move(self.vaporeon, 'pursuit')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39)
        self.assertDamageTaken(self.umbreon, 0)
        self.assertActive(self.umbreon)
        self.assertFalse(self.leafeon.is_active)

        self.choose_move(self.umbreon, 'quickattack')
        self.choose_move(self.vaporeon, 'pursuit')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 11)

    def test_pursuit_KO_switching_pokemon(self):
        self.add_pokemon('flareon', 1)
        self.add_pokemon('jolteon', 1)
        self.add_pokemon('umbreon', 1)
        self.leafeon.hp = 1
        self.choose_switch(self.leafeon, self.umbreon)
        self.choose_move(self.vaporeon, 'pursuit')
        self.run_turn()

        self.assertFainted(self.leafeon)

        self.engine.init_turn()
        # pursuit interrupts the choice to switch to umbreon, such that player1 is allowed to choose
        # again (and will choose flareon as the first choice by default)
        self.assertActive(self.flareon)

    def test_faster_pursuit_vs_switching_move(self):
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'pursuit')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 57) # 40 BP

    def test_slower_pursuit_vs_switching_move(self):
        self.add_pokemon('flareon', 0)
        self.leafeon.apply_boosts(Boosts(spe=-1))
        self.choose_move(self.leafeon, 'pursuit')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112) # 80 BP

    def test_faster_pursuit_vs_switching_move_pursuit_hits_first(self):
        self.add_pokemon('flareon', 0)
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'pursuit')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertDamageTaken(self.leafeon, 0)

    def test_slower_pursuit_vs_switching_move_pursuit_hits_second(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('espeon', 1)
        self.leafeon.hp = 1
        self.leafeon.apply_boosts(Boosts(spe=-1))
        self.choose_move(self.leafeon, 'pursuit')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertFainted(self.leafeon)
        self.assertActive(self.flareon)

    def test_slower_pursuit_vs_no_target(self):
        """ Regression: pursuit didn't correctly handle a lack of target """
        self.new_battle(p1_item='lifeorb')
        self.leafeon.hp = 10
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'pursuit')
        self.run_turn()
        self.assertFainted(self.leafeon)

    def test_switch_move_KO_pursuiter_before_pursuit(self):
        self.add_pokemon('flareon', 1)
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'voltswitch')
        self.choose_move(self.vaporeon, 'pursuit')
        self.run_turn()

        self.assertIsNone(self.leafeon.status)
        self.assertFainted(self.vaporeon)

    def test_pursuit_vs_batonpass(self):
        self.add_pokemon('flareon', 0)
        self.leafeon.apply_boosts(Boosts(spe=-1, acc=1))
        self.vaporeon.apply_boosts(Boosts(spd=3))
        self.choose_move(self.leafeon, 'leechseed')
        self.run_turn()
        self.choose_move(self.leafeon, 'pursuit')
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 57 + self.flareon.max_hp / 8) # 40 BP + leechseed
        self.assertBoosts(self.flareon, {'spd': 3})
        self.assertTrue(self.flareon.has_effect(Volatile.LEECHSEED))

    @patch('random.randrange', lambda _: 0) # always parahax
    def test_pursuit_catches_switcher_but_fails(self):
        self.add_pokemon('flareon', 0)
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()
        self.choose_move(self.leafeon, 'pursuit')
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn() # Don't run pursuit a second time
        self.assertActive(self.flareon)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.flareon, 0)

    def test_raindance(self):
        self.choose_move(self.leafeon, 'protect')
        self.choose_move(self.vaporeon, 'raindance')
        self.run_turn()

        self.assertEqual(self.engine.battlefield.weather, Weather.RAINDANCE)
        self.assertTrue(self.engine.battlefield.has_effect(Weather.RAINDANCE))

    @patch('random.randrange', lambda _: 0) # no miss
    def test_rapidspin(self):
        for _ in range(3):
            self.engine.use_move(self.vaporeon, movedex['spikes'], self.leafeon)
        self.choose_move(self.leafeon, 'rapidspin')
        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()

        self.assertEqual(self.leafeon.side.get_effect(Hazard.SPIKES).layers, 1)

        self.choose_move(self.leafeon, 'leechseed')
        self.choose_move(self.vaporeon, 'rapidspin')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.LEECHSEED))

        self.choose_move(self.leafeon, 'infestation')
        self.choose_move(self.vaporeon, 'rapidspin')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.PARTIALTRAP))

    def test_rapidspin_with_lifeorb(self):
        self.new_battle(p0_item='lifeorb')
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'rapidspin')
        self.run_turn()

        self.assertFalse(self.vaporeon.side.has_effect(Hazard.SPIKES))
        self.assertFainted(self.vaporeon)

    def test_rapidspin_vs_roughskin(self):
        self.new_battle(p1_ability='roughskin')
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'rapidspin')
        self.run_turn()

        self.assertTrue(self.vaporeon.side.has_effect(Hazard.SPIKES))
        self.assertFainted(self.vaporeon)

    def test_recover(self):
        for move in ('healorder', 'milkdrink', 'moonlight', 'recover', 'roost', 'slackoff',
                     'softboiled', 'morningsun', 'synthesis'):
            self.vaporeon.hp = 100
            self.leafeon.hp = 200

            self.choose_move(self.vaporeon, move)
            self.choose_move(self.leafeon, move)
            self.run_turn()

            self.assertEqual(self.vaporeon.hp, 301)
            self.assertEqual(self.leafeon.hp, self.leafeon.max_hp)

    def test_reflect_damage_calculations(self):
        self.choose_move(self.leafeon, 'protect')
        self.choose_move(self.vaporeon, 'reflect')
        self.run_turn()

        damage = self.engine.use_move(self.leafeon, movedex['vacuumwave'], self.vaporeon)
        self.assertEqual(damage, 25)

        damage = self.engine.use_move(self.leafeon, movedex['earthquake'], self.vaporeon)
        self.assertEqual(damage, 69)

    @patch('random.randrange', lambda _: 0) # no miss; confusion damage
    def test_reflect_with_confusion_damage(self):
        self.choose_move(self.leafeon, 'reflect')
        self.choose_move(self.vaporeon, 'confuseray')
        self.run_turn()
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 31)
        self.assertDamageTaken(self.vaporeon, 0)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_relicsong_forme_change(self):
        self.new_battle('vaporeon', 'meloetta', p0_ability='shielddust', p1_ability='serenegrace')
        self.add_pokemon('leafeon', 1)
        self.choose_move(self.meloetta, 'relicsong')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 124)
        self.assertDamageTaken(self.meloetta, 154)
        self.assertEqual(self.meloetta.name, 'meloettapirouette')
        self.assertEqual(self.meloetta.types, [Type.NORMAL, Type.FIGHTING])

        self.choose_move(self.meloetta, 'relicsong')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 124 + 81)
        self.assertDamageTaken(self.meloetta, 154 + 102)
        self.assertEqual(self.meloetta.name, 'meloetta')
        self.assertEqual(self.meloetta.types, [Type.NORMAL, Type.PSYCHIC])

        self.choose_move(self.meloetta, 'relicsong')
        self.choose_move(self.vaporeon, 'circlethrow')
        self.run_turn()

        self.assertDamageTaken(self.meloetta, 154 + 102 + 80)

        self.choose_switch(self.leafeon, self.meloetta)
        self.run_turn()

        self.assertEqual(self.meloetta.name, 'meloetta')
        self.assertEqual(self.meloetta.types, [Type.NORMAL, Type.PSYCHIC])

    def test_rest(self):
        self.choose_move(self.leafeon, 'uturn')
        self.choose_move(self.vaporeon, 'rest')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertEqual(self.vaporeon.status, Status.SLP)

        for _ in range(2):
            self.choose_move(self.vaporeon, 'return')
            self.choose_move(self.leafeon, 'uturn')
            self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.SLP)
        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.leafeon, 'rest')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertIsNone(self.leafeon.status)
        self.assertDamageTaken(self.leafeon, 50)

    def test_rest_fails_when_already_asleep(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['rest'], movedex['sleeptalk']))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'rest')
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.SLP)
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'sleeptalk')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertStatus(self.vaporeon, Status.SLP)

    def test_retaliate(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 0)
        self.leafeon.apply_boosts(Boosts(atk=1))
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()
        self.assertFainted(self.vaporeon)
        self.choose_move(self.leafeon, 'vacuumwave')
        self.choose_move(self.flareon, 'retaliate')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 119) # 140 BP

        self.flareon.apply_boosts(Boosts(spe=1))
        self.choose_move(self.leafeon, 'earthquake')
        self.choose_move(self.flareon, 'retaliate')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 119 + 60) # 140 + 70 BP

        self.choose_move(self.leafeon, 'retaliate')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 146) # 70 BP (+1 atk)

    def test_reversal(self):
        self.vaporeon.hp = self.leafeon.hp = 100
        self.choose_move(self.leafeon, 'reversal')
        self.choose_move(self.vaporeon, 'reversal')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 100 - 57)
        self.assertEqual(self.leafeon.hp, 100 - 49)

        self.vaporeon.hp = self.vaporeon.max_hp
        self.leafeon.hp = 12

        self.vaporeon.apply_boosts(Boosts(spe=1))
        self.choose_move(self.vaporeon, 'reversal')
        self.choose_move(self.leafeon, 'reversal')
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 1)
        self.assertDamageTaken(self.vaporeon, 277)

    def test_roar(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 1)
        self.choose_move(self.vaporeon, 'roar')
        self.choose_move(self.leafeon, 'roar')
        self.run_turn()

        self.assertActive(self.flareon)
        self.assertActive(self.leafeon)
        self.assertFalse(self.vaporeon.is_active)
        self.assertFalse(self.jolteon.is_active)

    def test_roost(self):
        self.new_battle('moltres', 'articuno')
        self.choose_move(self.moltres, 'roost')
        self.choose_move(self.articuno, 'earthpower')
        self.run_turn()

        self.assertDamageTaken(self.moltres, 0)

        self.choose_move(self.moltres, 'hiddenpowerelectric')
        self.choose_move(self.articuno, 'hiddenpowerelectric')
        self.run_turn()
        self.choose_move(self.moltres, 'roost')
        self.choose_move(self.articuno, 'earthpower')
        self.run_turn()

        self.assertDamageTaken(self.moltres, 168)

        self.choose_move(self.articuno, 'earthpower')
        self.run_turn()

        self.assertDamageTaken(self.moltres, 168)

    def test_roost_no_type_change(self):
        self.vaporeon.hp = 100
        self.choose_move(self.vaporeon, 'roost')
        self.run_turn()
        self.assertEqual(self.vaporeon.types, [Type.WATER, None])

    def test_sacredsword(self):
        self.vaporeon.apply_boosts(Boosts(evn=6, def_=6))
        self.choose_move(self.leafeon, 'sacredsword')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 126)

    @patch('random.randrange', lambda _: 0) # no miss, static succeeds
    def test_safeguard(self):
        self.new_battle(p0_ability='static')
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertIsNone(self.leafeon.status)

        self.choose_move(self.leafeon, 'willowisp')
        self.choose_move(self.vaporeon, 'nuzzle')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.BRN)
        self.assertIsNone(self.leafeon.status)

        for _ in range(3):
            self.assertTrue(self.leafeon.side.has_effect(SideCondition.SAFEGUARD))
            self.run_turn()

        self.assertFalse(self.leafeon.side.has_effect(SideCondition.SAFEGUARD))

        self.choose_move(self.leafeon, 'safeguard')
        self.run_turn()
        self.choose_move(self.leafeon, 'aquatail')
        self.run_turn()

        self.assertStatus(self.leafeon, None)

    def test_safeguard_removed_by_defog(self):
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'defog')
        self.choose_move(self.vaporeon, 'nuzzle')
        self.run_turn()

        self.assertIsNone(self.leafeon.status)

        self.choose_move(self.vaporeon, 'defog')
        self.run_turn()
        self.choose_move(self.vaporeon, 'nuzzle')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_safeguard_infiltrator(self):
        self.new_battle('vaporeon', 'leafeon', p0_ability='infiltrator')
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'willowisp')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.BRN)

        self.choose_move(self.leafeon, 'aromatherapy')
        self.choose_move(self.vaporeon, 'nuzzle')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)

    def test_safeguard_yawn(self):
        self.new_battle('vaporeon', 'leafeon', p0_ability='infiltrator')
        self.choose_move(self.vaporeon, 'safeguard')
        self.choose_move(self.leafeon, 'safeguard')
        self.run_turn()

        self.choose_move(self.vaporeon, 'yawn')
        self.choose_move(self.leafeon, 'yawn')
        self.run_turn()

        self.assertTrue(self.leafeon.has_effect(Volatile.YAWN))
        self.assertFalse(self.vaporeon.has_effect(Volatile.YAWN))

        self.run_turn()
        self.assertStatus(self.leafeon, Status.SLP)

    def test_safeguard_blocks_confusion(self):
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'confuseray')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.CONFUSE))

    def test_safeguard_doesnt_block_infiltrator_confusion(self):
        self.new_battle('vaporeon', 'leafeon', p0_ability='infiltrator')
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'confuseray')
        self.run_turn()

        self.assertTrue(self.leafeon.has_effect(Volatile.CONFUSE))

    @patch('random.randint', lambda *_: 2) # two outrage turns
    def test_safeguard_doesnt_block_outrage_confusion(self):
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'wish')
        self.run_turn()

        self.choose_move(self.leafeon, 'outrage')
        self.choose_move(self.vaporeon, 'recover')
        self.run_turn()
        self.assertTrue(self.leafeon.has_effect(Volatile.LOCKEDMOVE))
        self.choose_move(self.leafeon, 'outrage')
        self.choose_move(self.vaporeon, 'recover')
        self.run_turn()
        self.assertFalse(self.leafeon.has_effect(Volatile.LOCKEDMOVE))

        self.assertTrue(self.leafeon.has_effect(Volatile.CONFUSE))

    def test_safeguard_doesnt_block_rest(self):
        self.choose_move(self.leafeon, 'safeguard')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.choose_move(self.leafeon, 'rest')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertTrue(self.leafeon.is_resting)
        self.assertEqual(self.leafeon.sleep_turns, 2)

    def test_safeguard_blocks_toxicspikes(self):
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'toxicspikes')
        self.choose_move(self.vaporeon, 'safeguard')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()

        self.assertStatus(self.flareon, None)

    def test_safeguard_doesnt_block_status_orbs(self):
        self.add_pokemon('flareon', 0, item='toxicorb')
        self.add_pokemon('sylveon', 0, item='flameorb')
        self.choose_move(self.vaporeon, 'safeguard')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()

        self.assertStatus(self.flareon, Status.TOX)

        self.choose_switch(self.flareon, self.sylveon)
        self.run_turn()

        self.assertStatus(self.sylveon, Status.BRN)

    @patch('random.randint', lambda *_: 1) # one turn sleep
    def test_sleeptalk(self):
        self.new_battle(p0_name='vaporeon', p1_name='jolteon',
                        p0_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                  movedex['seedbomb'], movedex['xscissor']))
        self.choose_move(self.jolteon, 'spore')
        self.run_turn()

        self.choose_move(self.vaporeon, 'sleeptalk')
        self.choose_move(self.jolteon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 73)

        self.choose_move(self.jolteon, 'splash')
        self.choose_move(self.vaporeon, 'sleeptalk')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 73)

    def test_sleeptalk_uses_rest_fails(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['rest'], movedex['sleeptalk']))
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'rest')
        self.run_turn()

        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'sleeptalk')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

        self.choose_move(self.leafeon, 'agility')
        self.choose_move(self.vaporeon, 'sleeptalk')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    @patch('random.randint', lambda *_: 3) # three turns sleep
    def test_faster_sleeptalk_roar_opponent_doesnt_get_to_move(self):
        self.new_battle('vaporeon', 'giratina',
                        p1_moves=(movedex['sleeptalk'], movedex['roar']))
        self.add_pokemon('flareon', 0)
        self.choose_move(self.giratina, 'sleeptalk')
        self.choose_move(self.vaporeon, 'spore')
        self.run_turn()
        self.choose_move(self.giratina, 'sleeptalk')
        self.choose_move(self.vaporeon, 'dragonpulse')
        self.run_turn()

        self.assertDamageTaken(self.giratina, 0)
        self.assertFalse(self.vaporeon.is_active)
        self.assertActive(self.flareon)

        self.choose_move(self.giratina, 'sleeptalk')
        self.choose_move(self.flareon, 'dragonclaw')
        self.run_turn()

        self.assertDamageTaken(self.giratina, 0)
        self.assertFalse(self.flareon.is_active)
        self.assertActive(self.vaporeon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_sleeppowder(self):
        self.choose_move(self.leafeon, 'sleeppowder')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.SLP)
        self.assertDamageTaken(self.leafeon, 0)

    def test_solarbeam(self):
        self.choose_move(self.vaporeon, 'solarbeam')
        self.choose_move(self.leafeon, 'clearsmog')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.vaporeon, 'solarbeam')
        self.choose_move(self.leafeon, 'clearsmog')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 78)

        self.engine.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.leafeon, 'milkdrink')
        self.choose_move(self.vaporeon, 'solarbeam')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 78)

    def test_spikes(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('umbreon', 1)
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 8)

        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.flareon, 'batonpass')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 6)

        self.flareon.hp = self.flareon.max_hp
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 4)

    def test_spikes_doesnt_hurt_ungrounded(self):
        self.add_pokemon('pidgeot', 0)
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertActive(self.pidgeot)
        self.assertDamageTaken(self.pidgeot, 0)

    def test_spikes_fails_after_three_layers(self):
        self.add_pokemon('umbreon', 1)
        for _ in range(3):
            self.engine.use_move(self.vaporeon, movedex['spikes'], self.leafeon)

        self.choose_switch(self.leafeon, self.umbreon)
        self.run_turn()

        self.assertDamageTaken(self.umbreon, self.umbreon.max_hp / 4)

        result = self.engine.use_move(self.vaporeon, movedex['spikes'], self.umbreon)
        self.assertEqual(result, FAIL)

    def test_spikyshield(self):
        self.choose_move(self.vaporeon, 'spikyshield')
        self.choose_move(self.leafeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 0)

        self.run_turn()
        self.choose_move(self.vaporeon, 'spikyshield')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 8)

    def test_stealthrock(self):
        for p in ('pidgeot', 'volcarona', 'machamp', 'excadrill', 'espeon'):
            self.add_pokemon(p, 0)
        self.choose_move(self.leafeon, 'stealthrock')
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertActive(self.pidgeot)
        self.assertDamageTaken(self.pidgeot, self.pidgeot.max_hp / 4)

        self.choose_switch(self.pidgeot, self.volcarona)
        self.run_turn()
        self.assertDamageTaken(self.volcarona, self.volcarona.max_hp / 2)

        self.choose_switch(self.volcarona, self.machamp)
        self.run_turn()
        self.assertDamageTaken(self.machamp, self.machamp.max_hp / 16)

        self.choose_switch(self.machamp, self.excadrill)
        self.run_turn()
        self.assertDamageTaken(self.excadrill, self.excadrill.max_hp / 32)

        self.choose_switch(self.excadrill, self.espeon)
        self.run_turn()
        self.assertDamageTaken(self.espeon, self.espeon.max_hp / 8)

    def test_stickyweb(self):
        self.add_pokemon('umbreon', 0)
        self.add_pokemon('pidgeot', 0)
        self.choose_move(self.leafeon, 'stickyweb')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertEqual(self.umbreon.boosts['spe'], -1)

        self.choose_switch(self.umbreon, self.pidgeot)
        self.run_turn()

        self.assertEqual(self.umbreon.boosts['spe'], 0)
        self.assertEqual(self.pidgeot.boosts['spe'], 0)

    def test_storedpower(self):
        self.vaporeon.apply_boosts(Boosts(spa=1, spd=1, def_=3))
        self.choose_move(self.vaporeon, 'storedpower')
        self.choose_move(self.leafeon, 'storedpower')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 9)
        self.assertDamageTaken(self.leafeon, 235)

        self.vaporeon.apply_boosts(Boosts(atk=-4))
        self.choose_move(self.leafeon, 'rest')
        self.choose_move(self.vaporeon, 'storedpower')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 235)

    def test_struggle(self):
        self.choose_move(self.leafeon, 'struggle')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 70)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_struggle_is_only_move_choice_when_out_of_pp(self):
        self.assertMoveChoices(self.vaporeon, {movedex['struggle']})

    def test_struggle_is_only_move_choice_when_disable_taunted(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['wish'],
                                  movedex['protect'], movedex['toxic']))
        self.choose_move(self.leafeon, 'taunt')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.choose_move(self.leafeon, 'disable')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 50)

        self.assertMoveChoices(self.vaporeon, {movedex['struggle']})

    def test_struggle_doesnt_damage_if_user_already_fainted(self):
        self.new_battle(p1_item='rockyhelmet')
        self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'struggle')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    def test_stormthrow_always_crit(self):
        self.engine.get_critical_hit = BattleEngine.get_critical_hit
        self.choose_move(self.vaporeon, 'stormthrow')
        self.choose_move(self.leafeon, 'stormthrow')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 126)
        self.assertDamageTaken(self.leafeon, 45)

    def test_suckerpunch_success(self):
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39)

        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertIsNone(self.vaporeon.status)

    def test_suckerpunch_fails_vs_status(self):
        self.choose_move(self.leafeon, 'toxic')
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

    def test_suckerpunch_fails_vs_switch(self):
        self.add_pokemon('espeon', 1)
        self.choose_switch(self.leafeon, self.espeon)
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.run_turn()

        self.assertActive(self.espeon)
        self.assertDamageTaken(self.espeon, 0)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_superfang(self):
        self.choose_move(self.vaporeon, 'superfang')
        self.choose_move(self.leafeon, 'superfang')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 2)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 2)

        self.leafeon.hp = 1
        self.choose_move(self.vaporeon, 'superfang')
        self.choose_move(self.leafeon, 'superfang')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp * 3/4)
        self.assertFainted(self.leafeon)

    def test_switcheroo_and_trick(self):
        for trick in ('trick', 'switcheroo'):
            self.new_battle(p0_item='airballoon', p1_item='powerherb')
            self.choose_move(self.leafeon, trick)
            self.choose_move(self.vaporeon, 'earthquake')
            self.run_turn()

            self.assertItem(self.vaporeon, 'powerherb')
            self.assertItem(self.leafeon, 'airballoon')
            self.assertDamageTaken(self.leafeon, 0)

            self.choose_move(self.leafeon, trick)
            self.choose_move(self.vaporeon, trick)
            self.run_turn()

            self.assertItem(self.vaporeon, 'powerherb')
            self.assertItem(self.leafeon, 'airballoon')

            self.choose_move(self.vaporeon, 'extremespeed')
            self.choose_move(self.leafeon, trick)
            self.run_turn()

            self.assertItem(self.leafeon, 'powerherb')
            self.assertItem(self.vaporeon, None)

            self.choose_move(self.leafeon, 'solarbeam')
            self.choose_move(self.vaporeon, trick)
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 212)
            self.assertItem(self.vaporeon, None)
            self.assertItem(self.leafeon, None)

    def test_trick_with_choicescarf(self):
        self.new_battle(p0_item='choicescarf', p1_item='toxicorb',
                        p0_moves=('trick', 'switcheroo', 'surf', 'protect'),
                        p1_moves=('trick', 'switcheroo', 'leafblade', 'dragonclaw'))
        self.choose_move(self.vaporeon, 'trick')
        self.choose_move(self.leafeon, 'dragonclaw')
        self.run_turn()

        self.assertItem(self.vaporeon, 'toxicorb')
        self.assertItem(self.leafeon, 'choicescarf')
        self.assertStatus(self.vaporeon, Status.TOX)
        self.assertStatus(self.leafeon, None)
        self.assertMoveChoices(self.vaporeon, {'trick', 'switcheroo', 'surf', 'protect'})
        self.assertMoveChoices(self.leafeon, {'dragonclaw'})

    def test_trick_fails_if_foe_item_is_unremovable(self):
        self.new_battle('vaporeon', 'arceuspsychic', p0_item='flameorb',
                        p1_item='mindplate', p1_ability='multitype')
        self.add_pokemon('genesectchill', 1, item='chilldrive')
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.BRN)
        self.assertStatus(self.arceuspsychic, None)

        self.choose_switch(self.arceuspsychic, self.genesectchill)
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()

        self.assertStatus(self.genesectchill, None)

    def test_trick_encored_with_assaultvest(self):
        self.new_battle(p0_item='lifeorb', p1_item='assaultvest',
                        p0_moves=('trick', 'explosion', 'surf', 'protect'),
                        p1_moves=('trick', 'return', 'encore', 'dragonclaw'))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()
        self.choose_move(self.leafeon, 'encore')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertItem(self.vaporeon, 'lifeorb')
        self.assertItem(self.leafeon, 'assaultvest')
        self.assertMoveChoices(self.vaporeon, {'trick'})

        self.choose_move(self.leafeon, 'dragonclaw')
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()

        self.assertItem(self.vaporeon, 'assaultvest')
        self.assertItem(self.leafeon, 'lifeorb')
        self.assertMoveChoices(self.vaporeon, {'struggle'})

    def test_tailwind(self):
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'tailwind')
        self.run_turn()

        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertFainted(self.leafeon)

    def test_taunt_limits_choices(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['dragonclaw'], movedex['protect'],
                                  movedex['xscissor'], movedex['substitute']))
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'taunt')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['dragonclaw'], movedex['xscissor']})

    def test_taunt_prevents_slower_status_move_same_turn(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['dragonclaw'], movedex['protect'],
                                  movedex['xscissor'], movedex['substitute']))
        self.choose_move(self.leafeon, 'taunt')
        self.choose_move(self.vaporeon, 'substitute')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.SUBSTITUTE))

    @patch('random.randrange', lambda _: 0) # no miss
    def test_thunderwave_ground_immunity(self):
        self.new_battle('golem', 'jolteon')
        self.engine.init_turn()
        result = self.engine.use_move(self.jolteon, movedex['thunderwave'], self.golem)
        self.assertEqual(result, FAIL)

        result = self.engine.use_move(self.jolteon, movedex['stunspore'], self.golem) # as a control
        self.assertEqual(result, None)
        self.assertEqual(self.golem.status, Status.PAR)

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_toxic_accuracy(self):
        self.add_pokemon('muk', 0)
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()

        self.assertIsNone(self.leafeon.status)

        self.choose_switch(self.vaporeon, self.muk)
        self.run_turn()
        self.choose_move(self.muk, 'toxic')
        self.run_turn()
        self.assertEqual(self.leafeon.status, Status.TOX)

    def test_toxicspikes(self):
        self.add_pokemon('flareon', 0)
        self.add_pokemon('umbreon', 1)
        self.add_pokemon('pidgeot', 1)
        self.choose_move(self.vaporeon, 'toxicspikes')
        self.choose_move(self.leafeon, 'toxicspikes')
        self.run_turn()
        self.choose_switch(self.leafeon, self.pidgeot)
        self.choose_move(self.vaporeon, 'toxicspikes')
        self.run_turn()

        self.assertIsNone(self.pidgeot.status)

        self.choose_switch(self.pidgeot, self.umbreon)
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()

        self.assertEqual(self.umbreon.status, Status.TOX)
        self.assertEqual(self.flareon.status, Status.PSN)

    def test_toxicspikes_eliminated_by_grounded_poison_type(self):
        self.add_pokemon('crobat', 0)
        self.add_pokemon('muk', 0)
        self.choose_move(self.leafeon, 'toxicspikes')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.crobat)
        self.run_turn()

        self.assertIsNone(self.crobat.status)
        self.assertTrue(self.engine.battlefield.sides[0].has_effect(Hazard.TOXICSPIKES))

        self.choose_switch(self.crobat, self.muk)
        self.run_turn()
        self.assertIsNone(self.muk.status)
        self.assertFalse(self.engine.battlefield.sides[0].has_effect(Hazard.TOXICSPIKES))

    def test_toxicspikes_fails_after_2_layers(self):
        for _ in range(2):
            result = self.engine.use_move(self.vaporeon, movedex['toxicspikes'], self.leafeon)
            self.assertIsNone(result)

        result = self.engine.use_move(self.vaporeon, movedex['toxicspikes'], self.leafeon)
        self.assertEqual(result, FAIL)

    def test_transform(self):
        self.new_battle('vaporeon', 'ditto')
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('flareon', 1)
        self.choose_move(self.vaporeon, 'substitute')
        self.choose_move(self.ditto, 'transform')
        self.run_turn()

        self.assertFalse(self.ditto.is_transformed)

        self.choose_move(self.vaporeon, 'partingshot')
        self.choose_move(self.ditto, 'transform')
        self.run_turn()

        self.assertTrue(self.ditto.is_transformed)
        self.assertFalse(self.ditto.boosts)
        self.assertDictContainsSubset({stat: val for stat, val in self.ditto.stats.items()
                                       if stat != 'max_hp'},
                                      self.jolteon.stats)

        self.choose_switch(self.ditto, self.flareon)
        self.choose_switch(self.jolteon, self.vaporeon)
        self.run_turn()
        self.choose_switch(self.flareon, self.ditto)
        self.run_turn()
        self.choose_move(self.ditto, 'transform')
        self.run_turn()

        self.assertTrue(self.ditto.is_transformed)
        self.assertEqual(self.ditto.name, 'vaporeon')

    def test_transform_fail_then_switch(self):
        self.new_battle('zoroark', 'ditto', p0_ability='illusion',
                        p0_item='choiceband', p1_item='choicescarf')
        self.add_pokemon('leafeon', 1)
        self.choose_move(self.ditto, 'transform')
        self.choose_move(self.zoroark, 'trick')
        self.run_turn()
        self.choose_switch(self.ditto, self.leafeon)
        self.choose_move(self.zoroark, 'trick')
        self.run_turn()

    @patch('random.randrange', lambda _: 1) # triattack causes paralysis
    def test_triattack_status(self):
        self.engine.use_move(self.vaporeon, movedex['triattack'], self.leafeon)
        self.assertEqual(self.leafeon.status, Status.PAR)

    def test_trickroom(self):
        self.add_pokemon('jolteon', 1)
        self.choose_move(self.leafeon, 'trickroom')
        self.choose_move(self.vaporeon, 'trickroom')
        self.run_turn()

        self.assertFalse(self.engine.battlefield.has_effect(PseudoWeather.TRICKROOM))

        self.choose_move(self.leafeon, 'trickroom')
        self.run_turn()
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertIsNone(self.vaporeon.status)

        self.choose_move(self.jolteon, 'quickattack')
        self.choose_move(self.vaporeon, 'earthpower')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertDamageTaken(self.jolteon, 0)

    def test_wakeupslap(self):
        self.engine.set_status(self.vaporeon, Status.SLP, None)
        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'wakeupslap')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 194)
        self.assertDamageTaken(self.leafeon, 50)

        self.choose_move(self.leafeon, 'wakeupslap')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 194 + 98)

    def test_weatherball(self):
        self.choose_move(self.vaporeon, 'weatherball')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 66)

        self.leafeon.hp = self.leafeon.max_hp
        self.vaporeon.apply_boosts(Boosts(spa=-1))
        self.choose_move(self.leafeon, 'sunnyday')
        self.choose_move(self.vaporeon, 'weatherball')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 264)

        self.leafeon.hp = self.leafeon.max_hp
        self.choose_move(self.leafeon, 'raindance')
        self.choose_move(self.vaporeon, 'weatherball')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 99)

    def test_wish(self):
        self.choose_move(self.leafeon, 'wish')
        self.choose_move(self.vaporeon, 'hiddenpowerfire')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 158)

        self.choose_move(self.leafeon, 'protect')
        self.choose_move(self.vaporeon, 'hiddenpowerfire')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 158 - self.leafeon.max_hp / 2)

    def test_wish_fails_during_active_wish(self):
        self.choose_move(self.leafeon, 'wish')
        self.run_turn()
        self.choose_move(self.vaporeon, 'hiddenpowerfire')
        self.choose_move(self.leafeon, 'wish')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 158 - self.leafeon.max_hp / 2)

        self.run_turn()
        self.assertDamageTaken(self.leafeon, 158 - self.leafeon.max_hp / 2)

    def test_wish_pass(self):
        self.add_pokemon('espeon', 0)
        self.choose_move(self.vaporeon, 'wish')
        self.choose_move(self.leafeon, 'xscissor')
        self.run_turn()

        self.choose_switch(self.vaporeon, self.espeon)
        self.choose_move(self.leafeon, 'xscissor')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 224 - self.vaporeon.max_hp / 2)

    def test_yawn(self):
        self.add_pokemon('espeon', 1)
        self.choose_move(self.vaporeon, 'yawn')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertIsNone(self.leafeon.status)

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.SLP)

        self.choose_switch(self.leafeon, self.espeon)
        self.choose_move(self.vaporeon, 'yawn')
        self.run_turn()
        self.assertTrue(self.espeon.has_effect(Volatile.YAWN))
        self.run_turn()
        self.assertIsNone(self.espeon.status) # sleep clause


class TestSubstitute(MultiMoveTestCase):
    """
    All the substitute-specific tests go here
    """
    def test_substitute_basic(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'earthpower')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)
        self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                         (self.leafeon.max_hp / 4) - 59)

        self.choose_move(self.vaporeon, 'icebeam')
        self.run_turn()

        self.assertIsNone(self.leafeon.get_effect(Volatile.SUBSTITUTE))
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_substitute_blocks_status_move(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertIsNone(self.leafeon.status)

    def test_substitute_fails_at_or_below_25_percent_hp(self):
        self.new_battle('vaporeon', 'leafeon', p1_level=90) # leafeon.max_hp == 244
        self.leafeon.hp = 61                               # 244 / 4
        self.vaporeon.hp = 42
        self.engine.init_turn()

        result = self.engine.use_move(self.leafeon, movedex['substitute'], self.vaporeon)
        self.assertEqual(result, FAIL)

        result = self.engine.use_move(self.vaporeon, movedex['substitute'], self.leafeon)
        self.assertEqual(result, FAIL)

    def test_shedinja_cant_use_substitute(self):
        self.new_battle('shedinja', 'leafeon')
        self.engine.init_turn()
        result = self.engine.use_move(self.shedinja, movedex['substitute'], self.leafeon)
        self.assertEqual(result, FAIL)

    def test_substitute_fails_if_already_present(self):
        self.engine.init_turn()
        result = self.engine.use_move(self.leafeon, movedex['substitute'], self.vaporeon)
        self.assertIsNone(result)
        result = self.engine.use_move(self.leafeon, movedex['substitute'], self.vaporeon)
        self.assertEqual(result, FAIL)

    def test_substitute_doesnt_block_sound_move(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp/4 + 118)

    @patch('random.randrange', lambda _: 0) # confusion damage
    def test_confusion_damage_doesnt_hit_subsitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()
        self.leafeon.confuse()
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                         self.leafeon.max_hp / 4)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp/4 + 31)

    def test_switch_move_vs_substitute(self):
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertActive(self.umbreon)
        self.assertFalse(self.vaporeon.is_active)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_batonpass_substitute(self):
        self.add_pokemon('jolteon', 1)
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()
        self.choose_move(self.leafeon, 'batonpass')
        self.choose_move(self.vaporeon, 'aerialace')
        self.run_turn()

        self.assertTrue(self.jolteon.has_effect(Volatile.SUBSTITUTE))
        self.assertEqual(self.jolteon.get_effect(Volatile.SUBSTITUTE).hp,
                         67 - 27)
        self.assertDamageTaken(self.jolteon, 0)

    def test_struggle_vs_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'struggle')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 4)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_frozen_behind_substitute_cant_be_thawed_by_opponent(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.engine.set_status(self.leafeon, Status.FRZ, None)
        self.choose_move(self.vaporeon, 'scald')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.FRZ)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_haze_goes_through_substitute_but_clearsmog_doesnt(self):
        self.leafeon.apply_boosts(Boosts(atk=2, spa=-3))
        self.vaporeon.apply_boosts(Boosts(spd=1))
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'clearsmog')
        self.run_turn()

        self.assertEqual(self.leafeon.boosts['atk'], 2)

        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'haze')
        self.run_turn()
        self.assertFalse(self.leafeon.boosts)

    def test_rapidspin_clears_hazards_but_doesnt_damage_target_behind_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()
        self.choose_move(self.leafeon, 'toxicspikes')
        self.choose_move(self.vaporeon, 'rapidspin')
        self.run_turn()

        self.assertFalse(self.vaporeon.side.has_effect(Hazard.TOXICSPIKES))
        self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                         self.leafeon.max_hp / 4 - 11)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_defog_clears_hazards_but_not_lower_evn_behind_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'stealthrock')
        self.choose_move(self.vaporeon, 'defog')
        self.run_turn()

        self.assertEqual(self.leafeon.boosts['evn'], 0)
        self.assertFalse(self.vaporeon.side.has_effect(Hazard.STEALTHROCK))

    def test_brickbreak_hits_substitute_but_still_breaks_screen(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'reflect')
        self.choose_move(self.vaporeon, 'brickbreak')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)
        self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                         self.leafeon.max_hp / 4 - 37)
        self.assertFalse(self.leafeon.side.has_effect(SideCondition.REFLECT))

    def test_substitute_blocks_memento(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'memento')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertFalse(self.leafeon.boosts)

    def test_substitute_drain(self):
        self.vaporeon.hp = 100
        self.choose_move(self.leafeon, 'substitute') # 67 hp
        self.choose_move(self.vaporeon, 'drainpunch')
        self.run_turn()

        self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                         self.leafeon.max_hp / 4 - 37)
        self.assertEqual(self.vaporeon.hp, 100 + 19)

        self.choose_move(self.vaporeon, 'drainingkiss')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 100 + 19 + 23)
        self.assertFalse(self.leafeon.has_effect(Volatile.SUBSTITUTE))
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    def test_counter_with_substitute_fails(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()

        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'counter')
        self.run_turn()
        self.assertTrue(self.leafeon.has_effect(Volatile.SUBSTITUTE))

        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'counter')
        self.run_turn()
        self.assertFalse(self.leafeon.has_effect(Volatile.SUBSTITUTE))

        self.assertDamageTaken(self.vaporeon, 0)

    def test_recoil_vs_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'doubleedge')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, int(58 * 33 / 100))

    def test_highjumpkick_vs_substitute(self):
        with patch('random.randrange', lambda _: 99): # miss
            self.choose_move(self.leafeon, 'substitute')
            self.choose_move(self.vaporeon, 'highjumpkick')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 2)

        with patch('random.randrange', lambda _: 0): # no miss
            self.choose_move(self.vaporeon, 'highjumpkick')
            self.run_turn()

            self.assertEqual(self.leafeon.get_effect(Volatile.SUBSTITUTE).hp,
                             (self.leafeon.max_hp / 4) - 63)

    @patch('random.randrange', lambda _: 2) # triattack freeze
    def test_triattack_secondary_vs_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'triattack')
        self.run_turn()

        self.assertStatus(self.leafeon, None)

    @patch('random.randrange', lambda _: 1) # no miss; no parahax
    def test_psychoshift_vs_substitute(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'psychoshift')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PAR)
        self.assertStatus(self.leafeon, None)

    def test_substitute_ends_partialtrap(self):
        self.choose_move(self.leafeon, 'infestation')
        self.choose_move(self.vaporeon, 'substitute')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.PARTIALTRAP))
        self.assertDamageTaken(self.vaporeon, 13 + self.vaporeon.max_hp / 4)

    def test_substitute_blocks_trick(self):
        self.new_battle(p0_item='heatrock', p1_item='chestoberry')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()

        self.assertItem(self.vaporeon, 'heatrock')
        self.assertItem(self.leafeon, 'chestoberry')

    def test_substitute_blocks_magician(self):
        self.new_battle(p0_ability='magician', p1_item='eviolite')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertItem(self.leafeon, 'eviolite')

    def test_substitute_doesnt_block_pickup(self):
        self.new_battle(p0_ability='pickup', p1_item='sitrusberry')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'hypervoice')
        self.run_turn()

        self.assertItem(self.vaporeon, 'sitrusberry')

    def test_substitute_doesnt_block_pickpocket(self):
        self.new_battle(p0_ability='pickpocket', p1_item='eviolite')
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertItem(self.vaporeon, 'eviolite')
        self.assertItem(self.leafeon, None)
