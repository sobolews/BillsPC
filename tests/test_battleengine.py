from unittest import TestCase
from mock import patch, Mock

from battle.battleengine import Battle
from battle.battlepokemon import BattlePokemon
from showdowndata import pokedex
from battle import effects
from battle.moves import movedex
from battle.abilities import abilitydex
from battle.items import itemdex
from battle.enums import FAIL, Status, Volatile, Type, Weather
from battle.stats import Boosts
from tests.multi_move_test_case import MultiMoveTestCase


class BattleEngineMovesTestCase(TestCase):
    def setUp(self):
        _none_ = abilitydex['_none_']
        self.vaporeon = BattlePokemon(pokedex['vaporeon'], evs=(0,)*6, ivs=(31,)*6, ability=_none_)
        self.flareon = BattlePokemon(pokedex['flareon'], evs=(0,)*6, ivs=(31,)*6,  ability=_none_)
        self.espeon = BattlePokemon(pokedex['espeon'], evs=(0,)*6, ivs=(31,)*6,  ability=_none_)
        self.golem = BattlePokemon(pokedex['golem'], evs=(0,)*6, ivs=(31,)*6,  ability=_none_)
        self.leafeon = BattlePokemon(pokedex['leafeon'], evs=(0,)*6, ivs=(31,)*6,  ability=_none_)
        self.palkia = BattlePokemon(pokedex['palkia'], evs=(0,)*6, ivs=(31,)*6,  ability=_none_)
        self.sylveon = BattlePokemon(pokedex['sylveon'], evs=(0,)*6, ivs=(31,)*6,  ability=_none_)
        self.battle = Battle([self.vaporeon], [self.flareon, self.sylveon, self.leafeon,
                                               self.golem, self.espeon, self.palkia])
        self.battle.init_battle()
        # make it deterministic
        self.battle.get_critical_hit = lambda crit: False
        self.battle.damage_randomizer = lambda: 100 # max damage

class TestBattleEngineCalculateDamage(BattleEngineMovesTestCase):
    def test_damage_calculation_physical_simple_max(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 73)

    def test_damage_calculation_physical_simple_min(self):
        self.battle.damage_randomizer = lambda: 85 # min damage
        damage = self.battle.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 62)

    def test_damage_calculation_special_simple(self):
        damage = self.battle.calculate_damage(self.flareon, movedex['dazzlinggleam'], self.vaporeon)
        self.assertEqual(damage, 69)

    def test_damage_calculation_physical_stab_super_effective(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['waterfall'], self.flareon)
        self.assertEqual(damage, 218)

    def test_damage_calculation_special_stab_double_effective(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['scald'], self.golem)
        self.assertEqual(damage, 628)

    def test_damage_calculation_resisted(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['earthquake'], self.leafeon)
        self.assertEqual(damage, 24)

    def test_damage_calculation_double_resisted(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['waterfall'], self.palkia)
        self.assertEqual(damage, 18)

    def test_damage_calculation_immune(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.sylveon)
        self.assertEqual(damage, FAIL)

    def test_damage_calculation_damage_callback(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['nightshade'], self.flareon)
        self.assertEqual(damage, 100)

    def test_damage_calculation_get_base_power(self):
        damage = self.battle.calculate_damage(self.vaporeon, movedex['eruption'], self.sylveon)
        self.assertEqual(damage, 110)

    def test_damage_calculation_full_spectrum(self):
        damages = []
        for i in range(85, 101):
            self.battle.damage_randomizer = lambda: i
            damages.append(self.battle.calculate_damage(self.vaporeon, movedex['hydropump'],
                                                        self.flareon))
        self.assertListEqual(damages, [236, 240, 242, 246, 248, 252, 254, 258,
                                       260, 264, 266, 270, 272, 276, 278, 282])

    def test_damage_calculation_boosted_atk(self):
        self.leafeon.boosts.update(Boosts(atk=3))
        damage = self.battle.calculate_damage(self.leafeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 277)

    def test_damage_calculation_boosted_spd(self):
        self.flareon.boosts.update(Boosts(spd=6))
        damage = self.battle.calculate_damage(self.leafeon, movedex['hypervoice'], self.flareon)
        self.assertEqual(damage, 13)

    def test_damage_calculation_mix_boost_and_lowered(self):
        self.flareon.boosts.update(Boosts(def_=1, atk=3, spe=-4))
        self.leafeon.boosts.update(Boosts(atk=-2, spa=3, spe=-3))
        damage = self.battle.calculate_damage(self.leafeon, movedex['waterfall'], self.flareon)
        self.assertEqual(damage, 76)

    def test_damage_calculation_crit(self):
        self.battle.get_critical_hit = lambda crit: True
        damage = self.battle.calculate_damage(self.leafeon, movedex['xscissor'], self.vaporeon)
        self.assertEqual(damage, 168)

    def test_crit_breaks_through_def_boost(self):
        self.battle.get_critical_hit = lambda crit: True
        self.vaporeon.boosts.update(Boosts(def_=4))
        damage = self.battle.calculate_damage(self.leafeon, movedex['dragonclaw'], self.vaporeon)
        self.assertEqual(damage, 168)

    def test_crit_doesnt_override_spa_boost(self):
        self.battle.get_critical_hit = lambda crit: True
        self.flareon.boosts.update(Boosts(spa=2))
        damage = self.battle.calculate_damage(self.flareon, movedex['fireblast'], self.vaporeon)
        self.assertEqual(damage, 209)

    def test_crit_breaks_through_atk_drop(self):
        self.battle.get_critical_hit = lambda crit: True
        self.leafeon.boosts.update(Boosts(atk=-1))
        damage = self.battle.calculate_damage(self.leafeon, movedex['dragonclaw'], self.vaporeon)
        self.assertEqual(damage, 168)

    def test_crit_ratio_3_always_crits(self):
        self.battle.get_critical_hit = Battle.get_critical_hit
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw, 'crit_ratio', 3):
            damage = self.battle.calculate_damage(self.leafeon, dragonclaw, self.vaporeon)
            self.assertEqual(damage, 168)

    def test_damage_calculation_with_different_levels(self):
        self.vaporeon = BattlePokemon(pokedex['vaporeon'], level=80, evs=(0,)*6, ivs=(31,)*6)
        self.flareon = BattlePokemon(pokedex['flareon'], level=70, evs=(0,)*6, ivs=(31,)*6)
        self.battle = Battle([self.vaporeon], [self.flareon])
        self.battle.init_battle()
        self.battle.get_critical_hit = lambda crit: False
        self.battle.damage_randomizer = lambda: 100
        damage = self.battle.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 67)

class TestBattleEngineMoveHit(BattleEngineMovesTestCase):
    def test_move_hit_deals_damage(self):
        damage = self.battle.move_hit(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 73)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 73)
        self.assertEqual(self.vaporeon.damage_done_this_turn, 73)

    def test_move_hit_causes_faint(self):
        self.vaporeon.boosts.update(Boosts(atk=6))
        damage = self.battle.move_hit(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, self.flareon.max_hp) # OHKO
        self.assertEqual(self.flareon.hp, 0)
        self.assertIs(self.flareon.status, Status.FNT)

    def test_move_hit_immune_fails(self):
        damage = self.battle.move_hit(self.vaporeon, movedex['dragonclaw'], self.sylveon)
        self.assertEqual(damage, FAIL)

    def test_move_hit_drain_move(self):
        self.vaporeon.hp = 200
        damage = self.battle.move_hit(self.vaporeon, movedex['drainpunch'], self.flareon)
        self.assertEqual(damage, 69)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 69)
        self.assertEqual(self.vaporeon.hp, 200 + 35)

    def test_move_hit_status_move_success(self):
        damage = self.battle.move_hit(self.vaporeon, movedex['willowisp'], self.sylveon)
        self.assertIsNone(damage)
        self.assertIs(self.sylveon.status, Status.BRN)

    def test_move_hit_status_move_already_statused(self):
        self.battle.set_status(self.sylveon, Status.SLP, None)
        damage = self.battle.move_hit(self.vaporeon, movedex['willowisp'], self.sylveon)
        self.assertEqual(damage, FAIL)
        self.assertIs(self.sylveon.status, Status.SLP)

    def test_move_hit_status_type_immunity(self):
        damage = self.battle.move_hit(self.vaporeon, movedex['willowisp'], self.flareon)
        self.assertEqual(damage, FAIL)
        self.assertIsNone(self.flareon.status)

    def test_move_hit_powder_immunity(self):
        damage = self.battle.move_hit(self.vaporeon, movedex['sleeppowder'], self.leafeon)
        self.assertEqual(damage, FAIL)
        self.assertIsNone(self.leafeon.status)

    def test_move_hit_boosts(self):
        damage = self.battle.move_hit(self.vaporeon, movedex['calmmind'], self.flareon)
        self.assertIsNone(damage)
        self.assertEqual(self.vaporeon.boosts, Boosts(spa=1, spd=1))

    def test_move_hit_negative_user_boosts(self):
        self.battle.move_hit(self.vaporeon, movedex['leafstorm'], self.flareon)
        self.assertEqual(self.vaporeon.boosts, Boosts(spa=-2))

    def test_move_hit_negative_user_boosts_successful_when_bottomed_out(self):
        self.vaporeon.boosts.update(Boosts(spa=-6))
        self.battle.move_hit(self.vaporeon, movedex['leafstorm'], self.flareon)
        self.assertEqual(self.vaporeon.boosts, Boosts(spa=-6))

    def test_move_hit_secondary_effect_self_boost(self):
        self.battle.move_hit(self.vaporeon, movedex['flamecharge'], self.flareon)
        self.assertEqual(self.vaporeon.boosts, Boosts(spe=1))

    def test_move_hit_secondary_effect_status(self):
        self.battle.move_hit(self.vaporeon, movedex['nuzzle'], self.flareon)
        self.assertIs(self.flareon.status, Status.PAR)

    def test_move_hit_secondary_effect_volatile(self):
        self.battle.move_hit(self.vaporeon, movedex['dynamicpunch'], self.flareon)
        self.assertTrue(self.flareon.has_effect(Volatile.CONFUSE))

    def test_move_hit_set_must_switch_flag(self):
        self.battle.move_hit(self.vaporeon, movedex['voltswitch'], self.flareon)
        self.assertTrue(self.vaporeon.must_switch)

class TestBattleEngineTryMoveHit(BattleEngineMovesTestCase):
    @patch('random.randrange', lambda _: 99) # miss
    def test_try_move_hit_miss(self):
        damage = self.battle.try_move_hit(self.vaporeon, movedex['dynamicpunch'], self.flareon)
        self.assertEqual(damage, FAIL)

    @patch('random.randrange', lambda _: 0) # hit
    def test_try_move_hit_no_miss(self):
        damage = self.battle.try_move_hit(self.vaporeon, movedex['dynamicpunch'], self.flareon)
        self.assertEqual(damage, 91)

    def test_try_move_hit_fails_check_success(self):
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw, 'check_success', lambda *_: FAIL):
            damage = self.battle.try_move_hit(self.vaporeon, dragonclaw, self.flareon)
            self.assertEqual(damage, FAIL)

    def test_try_move_hit_immune(self):
        with patch.object(self.flareon, 'types', (Type.FAIRY, None)):
            damage = self.battle.try_move_hit(self.vaporeon, movedex['dragonclaw'], self.flareon)
            self.assertEqual(damage, FAIL)

    def test_try_move_hit_multihit(self):
        bulletseed = movedex['bulletseed']
        with patch.object(bulletseed, 'multihit', (5,)): # hit 5 times
            total_damage = self.battle.try_move_hit(self.vaporeon, movedex['bulletseed'],
                                                            self.flareon)
            self.assertEqual(self.flareon.hp, self.flareon.max_hp - total_damage)

    def test_acc_boost(self):
        self.leafeon.is_active = True
        self.leafeon.set_effect(self.leafeon.ability())
        self.leafeon.apply_boosts(Boosts(acc=1))

        with patch('random.randrange', lambda _: 92): # accuracy is 93.3333, floors to 93
            damage = self.battle.try_move_hit(self.leafeon, movedex['focusblast'], self.vaporeon)
            self.assertEqual(damage, 71)

        with patch('random.randrange', lambda _: 93):
            damage = self.battle.try_move_hit(self.leafeon, movedex['focusblast'], self.vaporeon)
            self.assertEqual(damage, FAIL)

    def test_evn_boost(self):
        self.leafeon.is_active = True
        self.leafeon.set_effect(self.leafeon.ability())
        self.vaporeon.is_active = True
        self.battle.battlefield.sides[0].active_pokemon = self.vaporeon
        self.battle.battlefield.sides[1].active_pokemon = self.leafeon
        self.leafeon.apply_boosts(Boosts(evn=-1))

        with patch('random.randrange', lambda _: 99): # miss if possible
            damage = self.battle.try_move_hit(self.vaporeon, movedex['stoneedge'], self.leafeon)
            self.assertEqual(damage, 49)

class TestBattleEngineUseMove(BattleEngineMovesTestCase):
    def test_use_move_recoil_damage(self):
        self.battle.use_move(self.vaporeon, movedex['doubleedge'], self.flareon)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 109)
        self.assertEqual(self.vaporeon.hp, self.vaporeon.max_hp - 36)

    def test_use_selfdestruction_move(self):
        self.battle.use_move(self.vaporeon, movedex['explosion'], self.flareon)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 225)
        self.assertTrue(self.vaporeon.is_fainted())

    def test_use_move_call_on_move_fail(self):
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw.__class__, 'check_success', lambda *_: FAIL):
            with patch.object(dragonclaw.__class__, 'on_move_fail') as move:
                self.battle.use_move(self.vaporeon, dragonclaw, self.flareon)
                move.assert_called_with(self.vaporeon, self.battle)

class TestBattleEngineRunMove(TestCase):
    def setUp(self):
        self.vaporeon = BattlePokemon(pokedex['vaporeon'], evs=(0,)*6,
                                      moves=(movedex['scald'],
                                             movedex['icebeam'],
                                             movedex['rest'],
                                             movedex['toxic']),
                                      ability=abilitydex['_none_'])
        self.flareon = BattlePokemon(pokedex['flareon'], evs=(0,)*6,
                                     moves=(movedex['flareblitz'],
                                            movedex['flamecharge'],
                                            movedex['facade'],
                                            movedex['protect']),
                                     ability=abilitydex['_none_'])
        self.battle = Battle([self.vaporeon], [self.flareon])
        # make it deterministic
        self.battle.get_critical_hit = lambda crit: False
        self.battle.damage_randomizer = lambda: 100 # max damage

    def test_run_move_decrements_pp(self):
        self.battle.init_battle()
        self.vaporeon.will_move_this_turn = True
        self.battle.run_move(self.vaporeon, movedex['scald'], self.flareon)
        self.assertEqual(self.vaporeon.pp[movedex['scald']],
                         movedex['scald'].max_pp - 1)

    def test_run_move_sets_last_move_used(self):
        self.battle.init_battle()
        self.vaporeon.will_move_this_turn = True
        self.battle.run_move(self.vaporeon, movedex['scald'], self.flareon)
        self.assertEqual(self.vaporeon.last_move_used, movedex['scald'])
        self.assertEqual(self.battle.battlefield.last_move_used, movedex['scald'])

class TestBattleEngineMultiTurn(MultiMoveTestCase):
    def test_force_random_switch_into_hazards(self):
        """
        Regression: Forcing a switch into hazards failed to active hazards' effects.
        """
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'stealthrock')
        self.run_turn()
        self.choose_move(self.leafeon, 'roar')
        self.run_turn()

        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 4)

    def test_partialtrap_then_double_batonpass(self):
        """
        Regression: PartialTrap was not being removed properly when both trapper and trappee
        batonpassed in the same turn.
        """
        self.add_pokemon('umbreon', 0)
        self.add_pokemon('jolteon', 1)
        self.choose_move(self.vaporeon, 'infestation')
        self.run_turn()

        self.choose_move(self.vaporeon, 'batonpass')
        self.choose_move(self.leafeon, 'batonpass')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 0)
        self.assertFalse(self.jolteon.has_effect(Volatile.PARTIALTRAP))
        self.assertFalse(self.leafeon.has_effect(Volatile.PARTIALTRAP))

    def test_dont_try_user_boost_if_user_fainted(self):
        """
        Regression: Moves with user_boosts tried to boost the user even if it fainted
        """
        self.new_battle(p0_ability='aftermath')
        self.battle.apply_boosts = Mock()
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'closecombat')
        self.run_turn()

        self.assertFalse(self.battle.apply_boosts.called)

    def test_battlefield_weather_attribute_is_removed(self):
        """
        Regression: The weather effect was removed but battlefield.weather remained set
        """
        self.battlefield.set_weather(Weather.SUNNYDAY)
        for _ in range(5):
            self.run_turn()

        self.assertIsNone(self.battlefield.weather)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_move_without_base_power_doesnt_get_multiplied_by_effect(self):
        """
        Regression: effect.on_modify_base_power was being called with base_power=None
        """
        self.choose_move(self.leafeon, 'sunnyday')
        self.choose_move(self.vaporeon, 'willowisp')
        self.run_turn()         # would raise TypeError: <None> * 1.5

        self.assertEqual(self.battle.battlefield.weather, Weather.SUNNYDAY)
        self.assertEqual(self.leafeon.status, Status.BRN)

    def test_status_effects_still_work_after_switch_out_and_in(self):
        """
        Regression: Pokemon's pokemon.status was set upon switch in but they did not have the
        corresponding effect.
        """
        self.add_pokemon('umbreon', 0)
        self.battle.set_status(self.vaporeon, Status.SLP, None)
        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()
        self.assertTrue(self.vaporeon.has_effect(Status.SLP))
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 0)

    def test_order_by_speed_no_boost(self):
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'scald')
        self.battle.run_turn()

        self.assertEqual(self.vaporeon.status, Status.FNT)
        self.assertIsNone(self.leafeon.status)

    def test_order_by_speed_boosted(self):
        self.vaporeon.apply_boosts(Boosts(spe=1))
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'scald')
        self.battle.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    def test_order_with_increased_priority_move(self):
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'quickattack')
        self.battle.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    def test_order_with_decreased_priority_move(self):
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'circlethrow')
        self.choose_move(self.vaporeon, 'scald')
        self.battle.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_force_random_switch(self):
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'circlethrow')
        self.choose_move(self.vaporeon, 'return')
        self.battle.run_turn()

        self.assertEqual(self.battle.battlefield.sides[0].active_pokemon, self.umbreon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_force_random_switch_on_last_pokemon(self):
        self.battle.init_turn()
        damage = self.battle.use_move(self.vaporeon, movedex['circlethrow'], self.leafeon)
        self.assertEqual(damage, 30)
        self.assertEqual(self.battle.battlefield.sides[1].active_pokemon, self.leafeon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_force_random_switch_with_higher_priority_skips_outgoings_move(self):
        self.add_pokemon('umbreon', 1)
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw, 'priority', -7):
            self.choose_move(self.leafeon, dragonclaw)
            self.choose_move(self.vaporeon, 'circlethrow')
            self.battle.run_turn()

            self.assertEqual(self.battle.battlefield.sides[1].active_pokemon, self.umbreon)
            self.assertEqual(self.vaporeon.hp, self.vaporeon.max_hp)

    @patch('random.randrange', lambda *_: 0) # two-turn outrage
    def test_locked_move(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['splash'],
                                  movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, {movedex['outrage']})

        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, set(self.vaporeon.moves))
        self.assertEqual(self.vaporeon.pp[movedex['outrage']], movedex['outrage'].max_pp - 1)
        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    def test_locked_move_with_1_pp(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['splash'],
                                  movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, {movedex['outrage']})

    @patch('random.randrange', lambda *_: 1) # three-turn outrage
    def test_locked_move_unlocks_after_protect_without_confusion(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['splash'],
                                  movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, {movedex['outrage']})

        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.leafeon, 'protect')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, set(self.vaporeon.moves))
        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))

    @patch('random.randrange', lambda *_: 0) # two-turn outrage
    def test_locked_move_unlocks_after_immunity_with_confusion(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['splash'],
                                  movedex['outrage'], movedex['toxic']))
        self.add_pokemon('sylveon', 1)
        self.leafeon.apply_boosts(Boosts(spe=-1))
        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.leafeon, 'uturn')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, {movedex['outrage']})

        self.choose_move(self.vaporeon, 'outrage')
        self.choose_move(self.sylveon, 'return')
        self.run_turn()

        self.assertMoveChoices(self.vaporeon, set(self.vaporeon.moves))
        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    @patch('random.randrange', lambda *_: 1) # three-turn outrage
    def test_locked_move_unlocks_without_confusion_after_user_falls_asleep(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p0_moves=(movedex['return'], movedex['splash'],
                                  movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, 'petaldance')
        self.choose_move(self.leafeon, 'yawn')
        self.run_turn()
        self.choose_move(self.vaporeon, 'petaldance')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.SLP)
        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))
        self.assertFalse(self.vaporeon.has_effect(Volatile.LOCKEDMOVE))
        self.assertMoveChoices(self.vaporeon, set(self.vaporeon.moves))

    def test_locked_move_user_faints_first_turn(self):
        self.new_battle(p0_item='rockyhelmet')
        self.add_pokemon('jolteon', 1)
        self.leafeon.hp = 10
        self.choose_move(self.leafeon, 'outrage')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFalse(self.leafeon.has_effect(Volatile.CONFUSE))

    @patch('random.randint', lambda *_: 2) # two-turn outrage
    def test_locked_move_ko_user_last_turn(self):
        self.add_pokemon('jolteon', 1)
        self.leafeon.hp = 10
        self.choose_move(self.leafeon, 'outrage')
        self.run_turn()

        self.choose_move(self.vaporeon, 'extremespeed')
        self.choose_move(self.leafeon, 'outrage')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFalse(self.leafeon.has_effect(Volatile.CONFUSE))
        self.battle.init_turn()
        self.assertActive(self.jolteon)

    @patch('random.randint', lambda *_: 3) # three turns of confusion
    @patch('random.randrange', lambda *_: 1) # three turns of sleep
    def test_confusion_counter_doesnt_decrement_while_pokemon_is_asleep(self):
        self.choose_move(self.leafeon, 'confuseray')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.choose_move(self.leafeon, 'spore')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        for _ in range(2):
            self.choose_move(self.vaporeon, 'return')
            self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    def test_attempt_switch_with_member_of_other_team_raises_error(self):
        if __debug__: # will only assert in debug mode
            with self.assertRaises(AssertionError):
                self.add_pokemon('sylveon', 1)
                self.choose_switch(self.vaporeon, self.sylveon)
                self.choose_move(self.leafeon, 'return')
                self.run_turn()

    def test_sleep_clause(self):
        self.add_pokemon('umbreon', 0)
        self.add_pokemon('espeon', 0)
        self.choose_move(self.vaporeon, 'eruption')
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.SLP)
        self.assertIsNone(self.leafeon.status)

        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.choose_move(self.leafeon, 'spore')
        self.choose_move(self.umbreon, 'foulplay')
        self.run_turn()

        self.assertIsNone(self.umbreon.status)
        self.assertDamageTaken(self.leafeon, 106)

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.umbreon, 'rest')
        self.run_turn()

        self.assertTrue(self.umbreon.is_resting)
        self.assertTrue(self.umbreon.status is Status.SLP)
        self.assertDamageTaken(self.umbreon, 0)

        self.choose_switch(self.umbreon, self.vaporeon)
        self.choose_move(self.leafeon, 'wakeupslap')
        self.run_turn()
        self.assertIsNone(self.vaporeon.status)
        self.choose_switch(self.vaporeon, self.espeon)
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()

        self.assertEqual(self.espeon.status, Status.SLP)

    def test_item_used_this_turn(self):
        self.new_battle(p0_item='sitrusberry', p1_item='weaknesspolicy')
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertEqual(self.vaporeon.item_used_this_turn, itemdex['sitrusberry'])

        self.choose_move(self.vaporeon, 'flamecharge')
        self.run_turn()

        self.assertIsNone(self.vaporeon.item_used_this_turn)
        self.assertItem(self.leafeon, None)
        self.assertEqual(self.leafeon.item_used_this_turn, itemdex['weaknesspolicy'])

        self.run_turn()

        self.assertIsNone(self.leafeon.item_used_this_turn)

    def test_item_used_this_turn_when_switching(self):
        self.new_battle(p0_item='sitrusberry')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.choose_move(self.leafeon, 'roar')
        self.run_turn()

        self.assertIsNone(self.vaporeon.item_used_this_turn)


class TestMiscMultiTurn(MultiMoveTestCase):
    def test_prevent_bounce_invulnerability_persisting_when_move_fails(self):
        self.choose_move(self.vaporeon, 'yawn')
        self.run_turn()
        self.choose_move(self.leafeon, 'bounce')
        self.run_turn()
        self.choose_move(self.leafeon, 'bounce')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 88)

    def test_switch_move_succeeds_without_switching_when_bench_empty(self):
        self.add_pokemon('umbreon', 0)
        self.umbreon.status = Status.FNT
        self.umbreon.hp = 0
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertActive(self.vaporeon)
        self.assertDamageTaken(self.leafeon, 68)
        self.run_turn()

    def test_switch_in_wish_and_spikes(self):
        """ Spikes is on_switch_in, before wish (on_timeout) """
        self.add_pokemon('umbreon', 0)
        self.umbreon.hp = 1
        self.choose_move(self.vaporeon, 'wish')
        self.choose_move(self.leafeon, 'spikes')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'spikes')
        self.run_turn()

        self.assertEqual(self.umbreon.status, Status.FNT)

    def test_switch_in_healingwish_and_spikes(self):
        """ Spikes(priority=0) and healingwish(priority=1) are both on_switch_in """
        self.add_pokemon('umbreon', 0)
        self.umbreon.hp = 1
        self.choose_move(self.vaporeon, 'healingwish')
        self.choose_move(self.leafeon, 'spikes')
        self.run_turn()
        self.battle.init_turn()

        self.assertDamageTaken(self.umbreon, self.umbreon.max_hp / 8)

    @patch('random.randrange', lambda _: 1) # fail the roll to get a second protect
    def test_stall_crossover(self):
        self.choose_move(self.vaporeon, 'kingsshield')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()
        self.choose_move(self.vaporeon, 'spikyshield')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192)

        self.choose_move(self.vaporeon, 'protect')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192)

        self.choose_move(self.vaporeon, 'protect')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192 * 2)

    def test_disable_vs_sleeptalk(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                  movedex['crunch'], movedex['xscissor']))
        self.battle.set_status(self.leafeon, Status.SLP, None)
        self.choose_move(self.leafeon, 'sleeptalk')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['dragonclaw'], movedex['crunch'],
                                              movedex['xscissor']})

    def test_disable_vs_copycat(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['dragonclaw'], movedex['copycat'],
                                  movedex['crunch'], movedex['xscissor']))
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()
        self.choose_move(self.leafeon, 'copycat')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['dragonclaw'], movedex['crunch'],
                                              movedex['xscissor']})

    def test_encore_vs_copycat(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['dragonclaw'], movedex['copycat'],
                                  movedex['crunch'], movedex['xscissor']))
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()
        self.choose_move(self.leafeon, 'copycat')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['copycat']})

        self.choose_move(self.leafeon, 'copycat')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.ENCORE))

    @patch('random.randrange', lambda _: 1) # 3 turn sleep
    def test_encore_vs_sleeptalk(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                  movedex['extremespeed'], movedex['xscissor']))
        self.battle.set_status(self.leafeon, Status.SLP, None)
        self.choose_move(self.leafeon, 'sleeptalk')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {movedex['sleeptalk']})

        self.choose_move(self.leafeon, 'sleeptalk')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112 * 2)

    def test_copycat_vs_sleeptalk(self):
        self.new_battle(p0_name='vaporeon', p1_name='leafeon',
                        p1_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                  movedex['extremespeed'], movedex['crunch']))
        self.battle.set_status(self.leafeon, Status.SLP, None)
        self.choose_move(self.leafeon, 'sleeptalk')
        self.choose_move(self.vaporeon, 'copycat')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112)
        self.assertDamageTaken(self.leafeon, 39)

    def test_drain_fails_on_aftermath(self):
        self.new_battle('vaporeon', 'leafeon', p1_ability='aftermath')
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_move(self.vaporeon, 'drainpunch')

        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertFainted(self.leafeon)

    def test_destinybond_with_aftermath(self):
        self.new_battle('vaporeon', 'leafeon', p1_ability='aftermath')
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertFainted(self.leafeon)

    def test_faint_order_on_double_switch_out_into_spikes_ko(self):
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('flareon', 1)
        for pokemon in (self.leafeon, self.vaporeon, self.flareon, self.jolteon):
            pokemon.hp = 1
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()
        self.choose_switch(self.leafeon, self.flareon)
        self.choose_switch(self.vaporeon, self.jolteon)
        self.run_turn()

        self.assertListEqual(self.faint_log, [self.flareon, self.jolteon])
        self.run_turn()

        self.assertListEqual(self.faint_log, [self.flareon, self.jolteon,
                                              self.leafeon, self.vaporeon])
        self.assertEqual(self.battlefield.win, 0)

    def test_3_pokemon_in_a_row_faint_from_spikes_before_foe_makes_move_choice(self):
        for pokemon in ('jolteon', 'espeon', 'umbreon'):
            self.add_pokemon(pokemon, 0)
            getattr(self, pokemon).hp = 1
        self.add_pokemon('flareon', 0)

        self.choose_move(self.leafeon, 'stealthrock')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()
        self.battle.init_turn()

        # NOTE: relies on AutoRolloutPolicy always choosing choices[0]
        self.assertListEqual(self.faint_log, [self.vaporeon, self.jolteon,
                                              self.espeon, self.umbreon])
        self.assertActive(self.flareon)
        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 4)

    def test_order_of_abilities_depends_on_speed_of_switchins(self):
        self.new_battle('vaporeon', 'leafeon', p0_ability='drizzle', p1_ability='drought')
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

        self.new_battle('jolteon', 'flareon', p0_ability='drizzle', p1_ability='drought')
        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_order_of_switchins_after_double_ko(self):
        self.add_pokemon('alakazam', 0, ability='drought')
        self.add_pokemon('slowbro', 1, ability='drizzle')
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, 'toxic')
        self.choose_move(self.leafeon, 'toxic')
        self.run_turn()
        self.battle.init_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

    def test_order_of_active_switchins(self):
        self.add_pokemon('alakazam', 0, ability='drought')
        self.add_pokemon('slowbro', 1, ability='drizzle')
        self.choose_switch(self.vaporeon, self.alakazam)
        self.choose_switch(self.leafeon, self.slowbro)
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

        self.new_battle('leafeon', 'vaporeon')
        self.add_pokemon('alakazam', 0, ability='drought')
        self.add_pokemon('slowbro', 1, ability='drizzle')
        self.choose_switch(self.leafeon, self.alakazam)
        self.choose_switch(self.vaporeon, self.slowbro)
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

    def test_ability_doesnt_start_on_switch_into_hazard_ko(self):
        self.add_pokemon('jolteon', 0, ability='desolateland')
        self.jolteon.hp = 1
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertIsNone(self.battlefield.weather)

    def test_drain_heal_before_on_after_damage(self):
        self.new_battle(p1_ability='ironbarbs')
        self.vaporeon.hp = 50
        self.choose_move(self.vaporeon, 'drainpunch')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertEqual(self.vaporeon.hp, 50 + 19 - 50)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_residual_order(self):
        self.vaporeon.hp = 51
        self.leafeon.hp = 100

        self.battle.set_status(self.vaporeon, Status.PSN, None)
        self.choose_move(self.leafeon, 'leechseed')
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 150) # leechseed happens first
        self.assertFainted(self.vaporeon)

    def test_same_residual_order_by_speed(self):
        self.new_battle(p0_ability='noguard')
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'toxic')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()

        self.assertEqual(self.vaporeon.side.index, self.battlefield.win)

        self.new_battle(p0_ability='noguard')
        self.vaporeon.apply_boosts(Boosts(spe=1))
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'toxic')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()

        self.assertEqual(self.leafeon.side.index, self.battlefield.win)

    def test_force_random_switch_with_forcer_faint(self):
        self.new_battle(p0_ability='ironbarbs', p1_ability='noguard')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 1)
        self.leafeon.hp = 10
        self.choose_move(self.leafeon, 'dragontail')
        self.run_turn()
        self.battle.init_turn()

        self.assertFainted(self.leafeon)
        self.assertActive(self.vaporeon)
        self.assertFalse(self.flareon.is_active)

    def test_force_random_switch_with_target_faint(self):
        self.new_battle(p1_ability='noguard')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('umbreon', 0)
        with patch('random.choice', lambda _, self=self: self.umbreon):
            self.vaporeon.hp = 10
            self.choose_move(self.leafeon, 'dragontail')
            self.run_turn()
            self.battle.init_turn()

        self.assertActive(self.flareon)

    def test_circlethrow_with_lifeorb_kos_foe_and_has_recoil(self):
        self.new_battle(p0_item='lifeorb', p0_ability='noguard')
        self.leafeon.hp = 10
        self.choose_move(self.vaporeon, 'circlethrow')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 10)

    @patch('random.randrange', lambda _: 1) # icebeam always freeze, don't thaw
    def test_scald_heals_but_doesnt_thaw_frozen_waterabsorber(self):
        self.new_battle(p0_ability='waterabsorb')
        self.choose_move(self.leafeon, 'icebeam')
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.FRZ)
        self.assertDamageTaken(self.vaporeon, 27)
        self.choose_move(self.leafeon, 'scald')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.FRZ)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_enormous_damage(self):
        self.new_battle('darmanitan', 'paras',
                        p0_item='choiceband', p0_ability='flashfire', p0_evs=(0, 252, 0, 0, 0, 0),
                        p1_level=1, p1_ability='dryskin', p1_evs=(0,)*6)
        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.darmanitan.apply_boosts(Boosts(atk=6))
        self.paras.apply_boosts(Boosts(def_=-6))
        self.choose_move(self.paras, 'flamethrower')
        self.run_turn()
        self.assertTrue(self.darmanitan.has_effect(Volatile.FLASHFIRE))
        self.battle.get_critical_hit = lambda crit: True

        damage = self.battle.calculate_damage(self.darmanitan, movedex['vcreate'], self.paras)
        self.assertEqual(damage, 8703184)

    def test_two_turn_move_only_decrements_pp_once(self):
        self.new_battle(p0_moves=('solarbeam', 'scald', 'toxic', 'protect'))
        self.choose_move(self.vaporeon, 'solarbeam')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 0)

        self.assertPpUsed(self.vaporeon, 'solarbeam', 1)

        self.choose_move(self.vaporeon, 'solarbeam')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 78)

        self.assertPpUsed(self.vaporeon, 'solarbeam', 1)

    def test_double_trap(self):
        self.new_battle(p0_ability='arenatrap', p1_ability='shadowtag')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 1)
        self.battle.init_turn()
        self.assertTrue(self.vaporeon.has_effect(Volatile.TRAPPED))
        self.assertTrue(self.leafeon.has_effect(Volatile.TRAPPED))
        self.assertSwitchChoices(self.vaporeon, set())
        self.assertSwitchChoices(self.vaporeon, set())

    def test_multihit_vs_justified(self):
        self.new_battle(p0_ability='justified', p1_ability='parentalbond')
        self.choose_move(self.leafeon, 'nightslash')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 2})

    @patch('random.choice', lambda _: 3) # tailslap hits 3 times
    def test_multihit_contact_vs_ironbarbs_and_rockyhelmet(self):
        self.new_battle(p0_ability='noguard', p1_ability='ironbarbs', p1_item='rockyhelmet')
        self.choose_move(self.vaporeon, 'tailslap')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 3 * (self.vaporeon.max_hp / 8 +
                                                   self.vaporeon.max_hp / 6))

    def test_multihit_vs_immunity_ability(self):
        self.new_battle(p0_ability='lightningrod', p1_ability='parentalbond')
        self.choose_move(self.leafeon, 'wildcharge')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': 1})
        self.assertDamageTaken(self.leafeon, 0)

    def test_two_turn_move_vs_immunity_ability(self):
        self.new_battle(p0_ability='wonderguard')
        self.choose_move(self.leafeon, 'shadowforce')
        self.run_turn()

        self.assertTrue(self.leafeon.has_effect(Volatile.TWOTURNMOVE))

        self.choose_move(self.leafeon, 'shadowforce')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertFalse(self.leafeon.has_effect(Volatile.TWOTURNMOVE))

    def test_sheerforce_lifeorb_recoil_when_mummified_mid_move(self):
        self.new_battle(p0_ability='sheerforce', p0_item='lifeorb', p1_ability='mummy')
        self.choose_move(self.vaporeon, 'flamecharge')
        self.run_turn()

        self.assertFalse(self.vaporeon.boosts)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 10)
        self.assertAbility(self.vaporeon, 'mummy')

    def test_item_residual_doesnt_attempt_to_heal_fainted_pokemon(self):
        self.new_battle('muk', 'leafeon', p0_ability='snowwarning', p0_item='blacksludge')
        self.muk.hp = 10
        self.run_turn()

        self.assertFainted(self.muk)

    def test_taunt_mid_geomancy(self):
        self.new_battle('xerneas', 'jolteon', p0_item='powerherb',
                        p0_moves=('geomancy', 'moonblast', 'thunder', 'focusblast'))

        self.choose_move(self.jolteon, 'knockoff')
        self.choose_move(self.xerneas, 'geomancy')
        self.run_turn()

        self.assertTrue(self.xerneas.has_effect(Volatile.TWOTURNMOVE))

        self.choose_move(self.jolteon, 'taunt')
        self.choose_move(self.xerneas, 'geomancy')
        self.run_turn()

        self.assertMoveChoices(self.xerneas, ('moonblast', 'thunder', 'focusblast'))
        self.assertFalse(self.xerneas.has_effect(Volatile.TWOTURNMOVE))
        self.assertFalse(self.xerneas.boosts)

    def test_pursuit_with_truant_vs_voltswitch(self):
        self.new_battle('slaking', 'rotomfan', p0_ability='truant', p0_item='choicescarf')
        self.add_pokemon('drapion', 1)
        self.choose_move(self.slaking, 'pursuit')
        self.choose_move(self.rotomfan, 'airslash')
        self.run_turn()
        self.choose_move(self.slaking, 'pursuit')
        self.choose_move(self.rotomfan, 'voltswitch')
        self.run_turn()

        self.assertDamageTaken(self.rotomfan, 49)
        self.assertActive(self.drapion)
        self.assertDamageTaken(self.drapion, 0)

    def test_spikes_ko_with_toxicspikes(self):
        # make sure toxicspikes runs after spikes; they normally have the same priority
        with patch.object(effects.ToxicSpikes.on_switch_in.__func__, 'priority', -100):
            self.add_pokemon('flareon', 0)
            self.flareon.hp = 10
            self.choose_move(self.leafeon, 'spikes')
            self.run_turn()
            self.choose_move(self.leafeon, 'toxicspikes')
            self.run_turn()
            self.choose_move(self.vaporeon, 'voltswitch')
            self.run_turn()
            self.assertFainted(self.flareon)

    def test_run_out_of_pp_mid_two_turn_move(self):
        self.new_battle(p0_moves=('return', 'toxic', 'solarbeam', 'scald'))
        self.vaporeon.pp[movedex['solarbeam']] = 1
        self.choose_move(self.vaporeon, 'solarbeam')
        self.choose_move(self.leafeon, 'bulkup')
        self.run_turn()
        self.assertEqual(self.vaporeon.pp[movedex['solarbeam']], 0)
        self.choose_move(self.vaporeon, 'solarbeam')
        self.choose_move(self.leafeon, 'bulkup')
        self.run_turn()         # don't assert on 0 pp
        self.assertDamageTaken(self.leafeon, 78)

    def test_hazards_with_shedinja(self):
        for hazard in ('stealthrock', 'spikes', 'toxicspikes'):
            self.new_battle()
            self.add_pokemon('shedinja', 0)
            self.choose_move(self.leafeon, hazard)
            self.choose_move(self.vaporeon, 'voltswitch')
            self.run_turn()

            self.assertFainted(self.shedinja)

    def test_second_after_move_damage_after_first_kos(self):
        self.new_battle('vaporeon', 'ferrothorn', p1_item='rockyhelmet', p1_ability='ironbarbs')
        self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'facade')
        self.run_turn() # no warnings
        self.assertFainted(self.vaporeon)

    def test_imposter_copies_forecast_but_no_forme_change(self):
        self.new_battle('castform', 'ditto', p0_ability='forecast', p1_ability='imposter')
        self.choose_move(self.castform, 'raindance')
        self.run_turn()

        self.assertEqual(self.castform.types[0], Type.WATER)
        self.assertEqual(self.ditto.types[0], Type.NORMAL)
        self.assertAbility(self.ditto, 'forecast')

    def test_recoil_move_vs_substitute_with_1_hp(self):
        self.choose_move(self.leafeon, 'substitute')
        self.run_turn()
        self.leafeon.get_effect(Volatile.SUBSTITUTE).hp = 1
        self.choose_move(self.vaporeon, 'bravebird')
        self.run_turn()
        self.assertFalse(self.leafeon.has_effect(Volatile.SUBSTITUTE))

        self.assertDamageTaken(self.vaporeon, 0)

    @patch('random.randrange', lambda _: 1) # flamebody always burns
    def test_synchronize_vs_flamebody_from_fainted_pokemon(self):
        self.new_battle(p0_ability='synchronize', p1_ability='flamebody')
        self.leafeon.hp = 10
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertFainted(self.leafeon)
        self.assertStatus(self.vaporeon, Status.BRN)

    def test_ko_hard_switching_regenerator_with_pursuit(self):
        self.new_battle(p0_ability='regenerator')
        self.add_pokemon('flareon', 0)
        self.vaporeon.hp = 10
        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_move(self.leafeon, 'pursuit')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    def test_ko_switch_move_regenerator_with_pursuit(self):
        self.new_battle(p0_ability='regenerator')
        self.vaporeon.apply_boosts(Boosts(spe=1))
        self.add_pokemon('flareon', 0)
        self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'uturn')
        self.choose_move(self.leafeon, 'pursuit')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    def test_pursuit_hits_before_stancechange_reversion(self):
        self.new_battle('aegislash', 'leafeon', p0_ability='stancechange')
        self.add_pokemon('vaporeon', 0)
        self.choose_move(self.aegislash, 'aerialace')
        self.run_turn()
        self.choose_switch(self.aegislash, self.vaporeon)
        self.choose_move(self.leafeon, 'pursuit')
        self.run_turn()

        self.assertDamageTaken(self.aegislash, 256) # takes the hit in blade forme

    def test_crash_damage_after_spikyshield_ko(self):
        self.new_battle('blaziken', 'chesnaught', p0_ability='noguard')
        self.blaziken.hp = 10
        self.choose_move(self.blaziken, 'highjumpkick')
        self.choose_move(self.chesnaught, 'spikyshield')
        self.run_turn()

        # no warning: tried to damage fainted pokemon
        self.assertFainted(self.blaziken)

    def test_confuse(self):
        self.new_battle('vaporeon', 'leafeon')
        self.vaporeon.confuse()

        self.choose_move(self.vaporeon, 'scald')
        with patch('random.random', lambda: 0.6):
            self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 37) # confusion damage

        self.assertEqual(self.vaporeon.get_effect(Volatile.CONFUSE).turns_left, 3)

        self.choose_move(self.vaporeon, 'recover')
        with patch('random.random', lambda: 0.36):
            self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, 'return')
        with patch('random.random', lambda: 0.90):
            self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))
        self.assertDamageTaken(self.leafeon, 50)
