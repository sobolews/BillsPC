from unittest import TestCase
from mock import patch

from battle.battleengine import BattleEngine
from battle.battlepokemon import BattlePokemon
from mining.pokedexmaker import create_pokedex
from pokedex.moves import movedex
from pokedex.abilities import abilitydex
from pokedex.enums import FAIL, Status, Volatile, Type, Weather
from pokedex.stats import Boosts
from tests.multi_move_test_case import MultiMoveTestCase

pokedex = create_pokedex()

class BattleEngineMovesTestCase(TestCase):
    def setUp(self):
        _none_ = abilitydex['_none_']
        self.vaporeon = BattlePokemon(pokedex['vaporeon'], evs=(0,)*6, ability=_none_)
        self.flareon = BattlePokemon(pokedex['flareon'], evs=(0,)*6, ability=_none_)
        self.espeon = BattlePokemon(pokedex['espeon'], evs=(0,)*6, ability=_none_)
        self.golem = BattlePokemon(pokedex['golem'], evs=(0,)*6, ability=_none_)
        self.leafeon = BattlePokemon(pokedex['leafeon'], evs=(0,)*6, ability=_none_)
        self.palkia = BattlePokemon(pokedex['palkia'], evs=(0,)*6, ability=_none_)
        self.sylveon = BattlePokemon(pokedex['sylveon'], evs=(0,)*6, ability=_none_)
        self.engine = BattleEngine([self.vaporeon], [self.flareon, self.sylveon, self.leafeon,
                                                     self.golem, self.espeon, self.palkia])
        self.engine.init_battle()
        # make it deterministic
        self.engine.get_critical_hit = lambda crit: False
        self.engine.damage_randomizer = lambda: 100 # max damage

class TestBattleEngineCalculateDamage(BattleEngineMovesTestCase):
    def test_damage_calculation_physical_simple_max(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 73)

    def test_damage_calculation_physical_simple_min(self):
        self.engine.damage_randomizer = lambda: 85 # min damage
        damage = self.engine.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 62)

    def test_damage_calculation_special_simple(self):
        damage = self.engine.calculate_damage(self.flareon, movedex['dazzlinggleam'], self.vaporeon)
        self.assertEqual(damage, 69)

    def test_damage_calculation_physical_stab_super_effective(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['waterfall'], self.flareon)
        self.assertEqual(damage, 218)

    def test_damage_calculation_special_stab_double_effective(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['scald'], self.golem)
        self.assertEqual(damage, 628)

    def test_damage_calculation_resisted(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['earthquake'], self.leafeon)
        self.assertEqual(damage, 24)

    def test_damage_calculation_double_resisted(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['waterfall'], self.palkia)
        self.assertEqual(damage, 18)

    def test_damage_calculation_immune(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.sylveon)
        self.assertEqual(damage, FAIL)

    def test_damage_calculation_damage_callback(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['nightshade'], self.flareon)
        self.assertEqual(damage, 100)

    def test_damage_calculation_get_base_power(self):
        damage = self.engine.calculate_damage(self.vaporeon, movedex['eruption'], self.sylveon)
        self.assertEqual(damage, 110)

    def test_damage_calculation_full_spectrum(self):
        damages = []
        for i in range(85, 101):
            self.engine.damage_randomizer = lambda: i
            damages.append(self.engine.calculate_damage(self.vaporeon, movedex['hydropump'],
                                                        self.flareon))
        self.assertListEqual(damages, [236, 240, 242, 246, 248, 252, 254, 258,
                                       260, 264, 266, 270, 272, 276, 278, 282])

    def test_damage_calculation_boosted_atk(self):
        self.leafeon.boosts.update(Boosts(atk=3))
        damage = self.engine.calculate_damage(self.leafeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 277)

    def test_damage_calculation_boosted_spd(self):
        self.flareon.boosts.update(Boosts(spd=6))
        damage = self.engine.calculate_damage(self.leafeon, movedex['hypervoice'], self.flareon)
        self.assertEqual(damage, 13)

    def test_damage_calculation_mix_boost_and_lowered(self):
        self.flareon.boosts.update(Boosts(def_=1, atk=3, spe=-4))
        self.leafeon.boosts.update(Boosts(atk=-2, spa=3, spe=-3))
        damage = self.engine.calculate_damage(self.leafeon, movedex['waterfall'], self.flareon)
        self.assertEqual(damage, 76)

    def test_damage_calculation_crit(self):
        self.engine.get_critical_hit = lambda crit: True
        damage = self.engine.calculate_damage(self.leafeon, movedex['xscissor'], self.vaporeon)
        self.assertEqual(damage, 168)

    def test_crit_breaks_through_def_boost(self):
        self.engine.get_critical_hit = lambda crit: True
        self.vaporeon.boosts.update(Boosts(def_=4))
        damage = self.engine.calculate_damage(self.leafeon, movedex['dragonclaw'], self.vaporeon)
        self.assertEqual(damage, 168)

    def test_crit_doesnt_override_spa_boost(self):
        self.engine.get_critical_hit = lambda crit: True
        self.flareon.boosts.update(Boosts(spa=2))
        damage = self.engine.calculate_damage(self.flareon, movedex['fireblast'], self.vaporeon)
        self.assertEqual(damage, 209)

    def test_crit_breaks_through_atk_drop(self):
        self.engine.get_critical_hit = lambda crit: True
        self.leafeon.boosts.update(Boosts(atk=-1))
        damage = self.engine.calculate_damage(self.leafeon, movedex['dragonclaw'], self.vaporeon)
        self.assertEqual(damage, 168)

    def test_crit_ratio_3_always_crits(self):
        self.engine.get_critical_hit = BattleEngine.get_critical_hit
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw, 'crit_ratio', 3):
            damage = self.engine.calculate_damage(self.leafeon, dragonclaw, self.vaporeon)
            self.assertEqual(damage, 168)

    def test_damage_calculation_with_different_levels(self):
        self.vaporeon = BattlePokemon(pokedex['vaporeon'], level=80, evs=(0,)*6)
        self.flareon = BattlePokemon(pokedex['flareon'], level=70, evs=(0,)*6)
        self.engine = BattleEngine([self.vaporeon], [self.flareon])
        self.engine.init_battle()
        self.engine.get_critical_hit = lambda crit: False
        self.engine.damage_randomizer = lambda: 100
        damage = self.engine.calculate_damage(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 67)

class TestBattleEngineMoveHit(BattleEngineMovesTestCase):
    def test_move_hit_deals_damage(self):
        damage = self.engine.move_hit(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, 73)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 73)
        self.assertEqual(self.vaporeon.damage_done_this_turn, 73)

    def test_move_hit_causes_faint(self):
        self.vaporeon.boosts.update(Boosts(atk=6))
        damage = self.engine.move_hit(self.vaporeon, movedex['dragonclaw'], self.flareon)
        self.assertEqual(damage, self.flareon.max_hp) # OHKO
        self.assertEqual(self.flareon.hp, 0)
        self.assertIs(self.flareon.status, Status.FNT)

    def test_move_hit_immune_fails(self):
        damage = self.engine.move_hit(self.vaporeon, movedex['dragonclaw'], self.sylveon)
        self.assertEqual(damage, FAIL)

    def test_move_hit_drain_move(self):
        self.vaporeon.hp = 200
        damage = self.engine.move_hit(self.vaporeon, movedex['drainpunch'], self.flareon)
        self.assertEqual(damage, 69)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 69)
        self.assertEqual(self.vaporeon.hp, 200 + 35)

    def test_move_hit_status_move_success(self):
        damage = self.engine.move_hit(self.vaporeon, movedex['willowisp'], self.sylveon)
        self.assertIsNone(damage)
        self.assertIs(self.sylveon.status, Status.BRN)

    def test_move_hit_status_move_already_statused(self):
        self.engine.set_status(self.sylveon, Status.SLP)
        damage = self.engine.move_hit(self.vaporeon, movedex['willowisp'], self.sylveon)
        self.assertEqual(damage, FAIL)
        self.assertIs(self.sylveon.status, Status.SLP)

    def test_move_hit_status_type_immunity(self):
        damage = self.engine.move_hit(self.vaporeon, movedex['willowisp'], self.flareon)
        self.assertEqual(damage, FAIL)
        self.assertIsNone(self.flareon.status)

    def test_move_hit_powder_immunity(self):
        damage = self.engine.move_hit(self.vaporeon, movedex['sleeppowder'], self.leafeon)
        self.assertEqual(damage, FAIL)
        self.assertIsNone(self.leafeon.status)

    def test_move_hit_boosts(self):
        damage = self.engine.move_hit(self.vaporeon, movedex['calmmind'], self.flareon)
        self.assertIsNone(damage)
        self.assertEqual(self.vaporeon.boosts, Boosts(spa=1, spd=1))

    def test_move_hit_negative_user_boosts(self):
        self.engine.move_hit(self.vaporeon, movedex['leafstorm'], self.flareon)
        self.assertEqual(self.vaporeon.boosts, Boosts(spa=-2))

    def test_move_hit_negative_user_boosts_successful_when_bottomed_out(self):
        self.vaporeon.boosts.update(Boosts(spa=-6))
        self.engine.move_hit(self.vaporeon, movedex['leafstorm'], self.flareon)
        self.assertEqual(self.vaporeon.boosts, Boosts(spa=-6))

    def test_move_hit_secondary_effect_self_boost(self):
        self.engine.move_hit(self.vaporeon, movedex['flamecharge'], self.flareon)
        self.assertEqual(self.vaporeon.boosts, Boosts(spe=1))

    def test_move_hit_secondary_effect_status(self):
        self.engine.move_hit(self.vaporeon, movedex['nuzzle'], self.flareon)
        self.assertIs(self.flareon.status, Status.PAR)

    def test_move_hit_secondary_effect_volatile(self):
        self.engine.move_hit(self.vaporeon, movedex['dynamicpunch'], self.flareon)
        self.assertTrue(self.flareon.has_effect(Volatile.CONFUSE))

    def test_move_hit_set_must_switch_flag(self):
        self.engine.move_hit(self.vaporeon, movedex['voltswitch'], self.flareon)
        self.assertTrue(self.vaporeon.must_switch)

class TestBattleEngineTryMoveHit(BattleEngineMovesTestCase):
    @patch('random.randrange', lambda _: 99) # miss
    def test_try_move_hit_miss(self):
        damage = self.engine.try_move_hit(self.vaporeon, movedex['dynamicpunch'], self.flareon)
        self.assertEqual(damage, FAIL)

    @patch('random.randrange', lambda _: 0) # hit
    def test_try_move_hit_no_miss(self):
        damage = self.engine.try_move_hit(self.vaporeon, movedex['dynamicpunch'], self.flareon)
        self.assertEqual(damage, 91)

    def test_try_move_hit_fails_check_success(self):
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw, 'check_success', lambda *_: FAIL):
            damage = self.engine.try_move_hit(self.vaporeon, dragonclaw, self.flareon)
            self.assertEqual(damage, FAIL)

    def test_try_move_hit_immune(self):
        with patch.object(self.flareon, 'types', (Type.FAIRY, None)):
            damage = self.engine.try_move_hit(self.vaporeon, movedex['dragonclaw'], self.flareon)
            self.assertEqual(damage, FAIL)

    def test_try_move_hit_multihit(self):
        bulletseed = movedex['bulletseed']
        with patch.object(bulletseed, 'multihit', (5,)): # hit 5 times
            damage = self.engine.try_move_hit(self.vaporeon, movedex['bulletseed'], self.flareon)
            self.assertEqual(damage, 12) # damage returned is from one hit
            self.assertEqual(self.flareon.hp, self.flareon.max_hp - (5 * damage))

    def test_acc_boost(self):
        self.leafeon.is_active = True
        self.leafeon.set_effect(self.leafeon.ability())
        self.engine.apply_boosts(self.leafeon, Boosts(acc=1))

        with patch('random.randrange', lambda _: 92): # accuracy is 93.3333, floors to 93
            damage = self.engine.try_move_hit(self.leafeon, movedex['focusblast'], self.vaporeon)
            self.assertEqual(damage, 71)

        with patch('random.randrange', lambda _: 93):
            damage = self.engine.try_move_hit(self.leafeon, movedex['focusblast'], self.vaporeon)
            self.assertEqual(damage, FAIL)

    def test_evn_boost(self):
        self.leafeon.is_active = True
        self.leafeon.set_effect(self.leafeon.ability())
        self.vaporeon.is_active = True
        self.engine.battlefield.sides[0].active_pokemon = self.vaporeon
        self.engine.battlefield.sides[1].active_pokemon = self.leafeon
        self.engine.apply_boosts(self.leafeon, Boosts(evn=-1))

        with patch('random.randrange', lambda _: 99): # miss if possible
            damage = self.engine.try_move_hit(self.vaporeon, movedex['stoneedge'], self.leafeon)
            self.assertEqual(damage, 49)

class TestBattleEngineUseMove(BattleEngineMovesTestCase):
    def test_use_move_recoil_damage(self):
        self.engine.use_move(self.vaporeon, movedex['doubleedge'], self.flareon)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 109)
        self.assertEqual(self.vaporeon.hp, self.vaporeon.max_hp - 36)

    def test_use_selfdestruction_move(self):
        self.engine.use_move(self.vaporeon, movedex['explosion'], self.flareon)
        self.assertEqual(self.flareon.hp, self.flareon.max_hp - 225)
        self.assertTrue(self.vaporeon.is_fainted())

    def test_use_move_call_on_move_fail(self):
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw.__class__, 'check_success', lambda *_: FAIL):
            with patch.object(dragonclaw.__class__, 'on_move_fail') as move:
                self.engine.use_move(self.vaporeon, dragonclaw, self.flareon)
                move.assert_called_with(self.vaporeon, self.engine)

class TestBattleEngineRunMove(TestCase):
    def setUp(self):
        self.vaporeon = BattlePokemon(pokedex['vaporeon'], evs=(0,)*6,
                                      moveset=(movedex['scald'],
                                               movedex['icebeam'],
                                               movedex['rest'],
                                               movedex['toxic']))
        self.flareon = BattlePokemon(pokedex['flareon'], evs=(0,)*6,
                                     moveset=(movedex['flareblitz'],
                                              movedex['flamecharge'],
                                              movedex['facade'],
                                              movedex['protect']))
        self.engine = BattleEngine([self.vaporeon], [self.flareon])
        self.vaporeon.will_move_this_turn = True
        # make it deterministic
        self.engine.get_critical_hit = lambda crit: False
        self.engine.damage_randomizer = lambda: 100 # max damage

    def test_run_move_decrements_pp(self):
        self.engine.run_move(self.vaporeon, self.vaporeon.moveset[0], self.flareon)
        self.assertEqual(self.vaporeon.pp[self.vaporeon.moveset[0]],
                         self.vaporeon.moveset[0].max_pp - 1)

    def test_run_move_sets_last_move_used(self):
        self.engine.run_move(self.vaporeon, self.vaporeon.moveset[0], self.flareon)
        self.assertEqual(self.vaporeon.last_move_used, self.vaporeon.moveset[0])
        self.assertEqual(self.engine.battlefield.last_move_used, self.vaporeon.moveset[0])

class TestBattleEngineMultiTurn(MultiMoveTestCase):
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
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.choose_move(self.vaporeon, movedex['willowisp'])
        self.run_turn()         # would raise TypeError: <None> * 1.5

        self.assertEqual(self.engine.battlefield.weather, Weather.SUNNYDAY)
        self.assertEqual(self.leafeon.status, Status.BRN)

    def test_status_effects_still_work_after_switch_out_and_in(self):
        """
        Regression: Pokemon's pokemon.status was set upon switch in but they did not have the
        corresponding effect.
        """
        self.add_pokemon('umbreon', 0)
        self.engine.set_status(self.vaporeon, Status.SLP)
        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()
        self.assertTrue(self.vaporeon.has_effect(Status.SLP))
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 0)

    def test_order_by_speed_no_boost(self):
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['scald'])
        self.engine.run_turn()

        self.assertEqual(self.vaporeon.status, Status.FNT)
        self.assertIsNone(self.leafeon.status)

    def test_order_by_speed_boosted(self):
        self.engine.apply_boosts(self.vaporeon, Boosts(spe=1))
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['scald'])
        self.engine.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    def test_order_with_increased_priority_move(self):
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['quickattack'])
        self.engine.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    def test_order_with_decreased_priority_move(self):
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, movedex['circlethrow'])
        self.choose_move(self.vaporeon, movedex['scald'])
        self.engine.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_force_random_switch(self):
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, movedex['circlethrow'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.engine.run_turn()

        self.assertEqual(self.engine.battlefield.sides[0].active_pokemon, self.umbreon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_force_random_switch_on_last_pokemon(self):
        self.engine.init_turn()
        damage = self.engine.use_move(self.vaporeon, movedex['circlethrow'], self.leafeon)
        self.assertEqual(damage, 30)
        self.assertEqual(self.engine.battlefield.sides[1].active_pokemon, self.leafeon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_force_random_switch_with_higher_priority_skips_outgoings_move(self):
        self.add_pokemon('umbreon', 1)
        dragonclaw = movedex['dragonclaw']
        with patch.object(dragonclaw, 'priority', -7):
            self.choose_move(self.leafeon, dragonclaw)
            self.choose_move(self.vaporeon, movedex['circlethrow'])
            self.engine.run_turn()

            self.assertEqual(self.engine.battlefield.sides[1].active_pokemon, self.umbreon)
            self.assertEqual(self.vaporeon.hp, self.vaporeon.max_hp)

    @patch('random.randint', lambda *_: 2) # two-turn outrage
    def test_locked_move(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p0_moves=(movedex['return'], movedex['splash'],
                                   movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            {movedex['outrage']})

        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            set(self.vaporeon.moveset))
        self.assertEqual(self.vaporeon.pp[movedex['outrage']], movedex['outrage'].max_pp - 1)
        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    def test_locked_move_with_1_pp(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p0_moves=(movedex['return'], movedex['splash'],
                                   movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            {movedex['outrage']})

    @patch('random.randint', lambda *_: 3) # three-turn outrage
    def test_locked_move_unlocks_after_protect_without_confusion(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p0_moves=(movedex['return'], movedex['splash'],
                                   movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            {movedex['outrage']})

        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.leafeon, movedex['protect'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            set(self.vaporeon.moveset))
        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))

    @patch('random.randint', lambda *_: 2) # two-turn outrage
    def test_locked_move_unlocks_after_immunity_with_confusion(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p0_moves=(movedex['return'], movedex['splash'],
                                   movedex['outrage'], movedex['toxic']))
        self.add_pokemon('sylveon', 1)
        self.engine.apply_boosts(self.leafeon, Boosts(spe=-1))
        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.leafeon, movedex['uturn'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            {movedex['outrage']})

        self.choose_move(self.vaporeon, movedex['outrage'])
        self.choose_move(self.sylveon, movedex['return'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            set(self.vaporeon.moveset))
        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    @patch('random.randint', lambda *_: 3) # three-turn outrage
    def test_locked_move_unlocks_without_confusion_after_user_falls_asleep(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p0_moves=(movedex['return'], movedex['splash'],
                                   movedex['outrage'], movedex['toxic']))
        self.choose_move(self.vaporeon, movedex['petaldance'])
        self.choose_move(self.leafeon, movedex['yawn'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['petaldance'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.SLP)
        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))
        self.assertFalse(self.vaporeon.has_effect(Volatile.LOCKEDMOVE))
        self.assertSetEqual(set(self.engine.get_move_choices(self.vaporeon)),
                            set(self.vaporeon.moveset))

    @patch('random.randint', lambda *_: 3) # three turns of confusion and sleep
    def test_confusion_counter_doesnt_decrement_while_pokemon_is_asleep(self):
        self.choose_move(self.leafeon, movedex['confuseray'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()
        for _ in range(2):
            self.choose_move(self.vaporeon, movedex['return'])
            self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.CONFUSE))

    def test_attempt_switch_with_member_of_other_team_raises_error(self):
        if __debug__: # will only assert in debug mode
            with self.assertRaises(AssertionError):
                self.add_pokemon('sylveon', 1)
                self.choose_switch(self.vaporeon, self.sylveon)
                self.choose_move(self.leafeon, movedex['return'])
                self.run_turn()

    def test_sleep_clause(self):
        self.add_pokemon('umbreon', 0)
        self.add_pokemon('espeon', 0)
        self.choose_move(self.vaporeon, movedex['eruption'])
        self.choose_move(self.leafeon, movedex['spore'])
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.SLP)
        self.assertIsNone(self.leafeon.status)

        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.umbreon, movedex['foulplay'])
        self.run_turn()

        self.assertIsNone(self.umbreon.status)
        self.assertDamageTaken(self.leafeon, 106)

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.umbreon, movedex['rest'])
        self.run_turn()

        self.assertTrue(self.umbreon.is_resting)
        self.assertTrue(self.umbreon.status is Status.SLP)
        self.assertDamageTaken(self.umbreon, 0)

        self.choose_switch(self.umbreon, self.vaporeon)
        self.choose_move(self.leafeon, movedex['wakeupslap'])
        self.run_turn()
        self.assertIsNone(self.vaporeon.status)
        self.choose_switch(self.vaporeon, self.espeon)
        self.choose_move(self.leafeon, movedex['spore'])
        self.run_turn()

        self.assertEqual(self.espeon.status, Status.SLP)

class TestWeather(MultiMoveTestCase):
    def test_sunnyday_damage_modify(self):
        self.engine.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.leafeon, movedex['surf'])
        self.choose_move(self.vaporeon, movedex['flamewheel'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 13)
        self.assertDamageTaken(self.leafeon, 90)

    @patch('random.randrange', lambda _: 1) # icebeam always freeze, don't thaw
    def test_sunnyday_freeze_immunity(self):
        self.engine.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.leafeon, movedex['icebeam'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)

    def test_desolateland_stops_water_moves(self):
        self.engine.battlefield.set_weather(Weather.DESOLATELAND)
        self.choose_move(self.vaporeon, movedex['waterfall'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.vaporeon, movedex['waterfall'])
        self.choose_move(self.leafeon, movedex['kingsshield'])
        self.run_turn()

        self.assertEqual(self.vaporeon.boosts['atk'], 0)

        self.choose_move(self.vaporeon, movedex['flamewheel'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 90)

    def test_raindance_damage_modify(self):
        self.engine.battlefield.set_weather(Weather.RAINDANCE)
        self.choose_move(self.leafeon, movedex['surf'])
        self.choose_move(self.vaporeon, movedex['flamewheel'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 40)
        self.assertDamageTaken(self.leafeon, 30)

    def test_primordialsea_stops_fire_moves(self):
        self.engine.battlefield.set_weather(Weather.PRIMORDIALSEA)
        self.choose_move(self.leafeon, movedex['surf'])
        self.choose_move(self.vaporeon, movedex['flamewheel'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 40)
        self.assertDamageTaken(self.leafeon, 0)

    def test_hail_damages_both_sides_but_not_ice_types(self):
        self.add_pokemon('glaceon', 0)
        self.engine.battlefield.set_weather(Weather.HAIL)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16)

        self.choose_switch(self.vaporeon, self.glaceon)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16 * 2)
        self.assertDamageTaken(self.glaceon, 0)

    def test_hail_stops_after_5_turns(self):
        self.engine.battlefield.set_weather(Weather.HAIL)
        for _ in range(4):
            self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16 * 4)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16 * 4)

    def test_sandstorm_damages_both_sides_but_not_rock_steel_ground(self):
        self.add_pokemon('empoleon', 0)
        self.add_pokemon('swampert', 1)
        self.add_pokemon('aerodactyl', 0)
        self.add_pokemon('golem', 1)
        self.engine.battlefield.set_weather(Weather.SANDSTORM)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16)

        self.choose_switch(self.vaporeon, self.empoleon)
        self.choose_switch(self.leafeon, self.swampert)
        self.run_turn()

        self.assertDamageTaken(self.empoleon, 0)
        self.assertDamageTaken(self.swampert, 0)

        self.choose_switch(self.empoleon, self.aerodactyl)
        self.choose_switch(self.swampert, self.golem)
        self.run_turn()

        self.assertDamageTaken(self.aerodactyl, 0)
        self.assertDamageTaken(self.golem, 0)

    def test_sandstorm_boosts_spd_rock_types(self):
        self.reset_leads('tyranitar', 'leafeon')
        self.engine.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.tyranitar, 43)

        self.choose_move(self.leafeon, movedex['hiddenpowerfighting'])
        self.run_turn()
        self.assertDamageTaken(self.tyranitar, 43 + 96)

    def test_hail_kos_shedinja(self): # TODO: test with wonderguard
        self.reset_leads('shedinja', 'leafeon')
        self.engine.battlefield.set_weather(Weather.HAIL)
        self.run_turn()

        self.assertEqual(self.shedinja.status, Status.FNT)

    def test_sandstorm_kos_shedinja(self): # TODO: test with wonderguard
        self.reset_leads('shedinja', 'leafeon')
        self.engine.battlefield.set_weather(Weather.SANDSTORM)
        self.run_turn()

        self.assertEqual(self.shedinja.status, Status.FNT)

    def test_deltastream_suppresses_moves_supereffective_vs_flying(self):
        self.reset_leads('rayquaza', 'leafeon')
        self.engine.battlefield.set_weather(Weather.DELTASTREAM)
        self.choose_move(self.leafeon, movedex['hiddenpowerice'])
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 76)

        self.choose_move(self.leafeon, movedex['dragonpulse'])
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 76 + 106)

        self.choose_move(self.leafeon, movedex['hiddenpowerrock'])
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 76 + 106 + 38)

    def test_changing_normal_weather(self):
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.choose_move(self.vaporeon, movedex['raindance'])
        self.run_turn()

        self.assertEqual(self.engine.battlefield.weather, Weather.RAINDANCE)

        self.run_turn()
        self.choose_move(self.vaporeon, movedex['raindance'])
        self.run_turn()

        self.assertEqual(self.engine.battlefield.get_effect(Weather.RAINDANCE).duration, 2)

    # def test_changing_weather_trio_weather_fails(self):
    #     pass # TODO: implement desolateland/primordialsea/deltastream abilities

class TestMiscMultiTurn(MultiMoveTestCase):
    def test_prevent_bounce_invulnerability_persisting_when_move_fails(self):
        self.choose_move(self.vaporeon, movedex['yawn'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['bounce'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['bounce'])
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 88)

    def test_switch_move_succeeds_without_switching_when_bench_empty(self):
        self.add_pokemon('umbreon', 0)
        self.umbreon.status = Status.FNT
        self.umbreon.hp = 0
        self.choose_move(self.vaporeon, movedex['uturn'])
        self.run_turn()

        self.assertTrue(self.vaporeon.is_active)
        self.assertDamageTaken(self.leafeon, 68)
        self.run_turn()

    # def test_order_of_residuals(self): TODO
    #     """ -> order of residuals: test case
    #     Chesnaught used Spiky Shield!
    #     Chesnaught protected itself!
    #     The opposing Dragalge used Sludge Wave!
    #     Chesnaught protected itself!
    #     Chesnaught restored a little HP using its Leftovers!
    #     The opposing Dragalge restored HP using its Black Sludge!
    #     The opposing Dragalge's health is sapped by Leech Seed!
    #     Chesnaught was hurt by poison!
    #     The opposing Dragalge was hurt by its burn!
    #     The opposing Dragalge fainted!
    #     """

    def test_switch_in_wish_and_spikes(self):
        """ Spikes is on_switch_in, before wish (on_timeout) """
        self.add_pokemon('umbreon', 0)
        self.umbreon.hp = 1
        self.choose_move(self.vaporeon, movedex['wish'])
        self.choose_move(self.leafeon, movedex['spikes'])
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, movedex['spikes'])
        self.run_turn()

        self.assertEqual(self.umbreon.status, Status.FNT)

    def test_switch_in_healingwish_and_spikes(self):
        """ Spikes(priority=0) and healingwish(priority=1) are both on_switch_in """
        self.add_pokemon('umbreon', 0)
        self.umbreon.hp = 1
        self.choose_move(self.vaporeon, movedex['healingwish'])
        self.choose_move(self.leafeon, movedex['spikes'])
        self.run_turn()
        self.engine.init_turn()

        self.assertDamageTaken(self.umbreon, self.umbreon.max_hp / 8)

    @patch('random.randrange', lambda _: 1) # fail the roll to get a second protect
    def test_stall_crossover(self):
        self.choose_move(self.vaporeon, movedex['kingsshield'])
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['spikyshield'])
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192)

        self.choose_move(self.vaporeon, movedex['protect'])
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192)

        self.choose_move(self.vaporeon, movedex['protect'])
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192 * 2)

    def test_disable_vs_sleeptalk(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p1_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                   movedex['crunch'], movedex['xscissor']))
        self.engine.set_status(self.leafeon, Status.SLP)
        self.choose_move(self.leafeon, movedex['sleeptalk'])
        self.choose_move(self.vaporeon, movedex['disable'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.leafeon)),
                            {movedex['dragonclaw'], movedex['crunch'], movedex['xscissor']})

    def test_disable_vs_copycat(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p1_moves=(movedex['dragonclaw'], movedex['copycat'],
                                   movedex['crunch'], movedex['xscissor']))
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['copycat'])
        self.choose_move(self.vaporeon, movedex['disable'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.leafeon)),
                            {movedex['dragonclaw'], movedex['crunch'], movedex['xscissor']})


    def test_encore_vs_copycat(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p1_moves=(movedex['dragonclaw'], movedex['copycat'],
                                   movedex['crunch'], movedex['xscissor']))
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['copycat'])
        self.choose_move(self.vaporeon, movedex['encore'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.leafeon)),
                            {movedex['copycat']})

        self.choose_move(self.leafeon, movedex['copycat'])
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.ENCORE))

    def test_encore_vs_sleeptalk(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p1_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                   movedex['extremespeed'], movedex['xscissor']))
        self.engine.set_status(self.leafeon, Status.SLP)
        self.leafeon.get_effect(Status.SLP).turns_left = 3
        self.leafeon.sleep_turns = 3
        self.choose_move(self.leafeon, movedex['sleeptalk'])
        self.choose_move(self.vaporeon, movedex['encore'])
        self.run_turn()

        self.assertSetEqual(set(self.engine.get_move_choices(self.leafeon)),
                            {movedex['sleeptalk']})

        self.choose_move(self.leafeon, movedex['sleeptalk'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112 * 2)

    def test_copycat_vs_sleeptalk(self):
        self.reset_leads(p0_name='vaporeon', p1_name='leafeon',
                         p1_moves=(movedex['dragonclaw'], movedex['sleeptalk'],
                                   movedex['extremespeed'], movedex['crunch']))
        self.engine.set_status(self.leafeon, Status.SLP)
        self.choose_move(self.leafeon, movedex['sleeptalk'])
        self.choose_move(self.vaporeon, movedex['copycat'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112)
        self.assertDamageTaken(self.leafeon, 39)

    def test_drain_fails_on_aftermath(self):
        self.reset_leads('vaporeon', 'leafeon', p1_ability='aftermath')
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_move(self.vaporeon, movedex['drainpunch'])

        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertFainted(self.leafeon)

    def test_destinybond_with_aftermath(self):
        self.reset_leads('vaporeon', 'leafeon', p1_ability='aftermath')
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_move(self.leafeon, movedex['destinybond'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertFainted(self.leafeon)

    def test_faint_order_on_double_switch_out_into_spikes_ko(self):
        self.add_pokemon('jolteon', 0)
        self.add_pokemon('flareon', 1)
        for pokemon in (self.leafeon, self.vaporeon, self.flareon, self.jolteon):
            pokemon.hp = 1
        self.choose_move(self.leafeon, movedex['spikes'])
        self.choose_move(self.vaporeon, movedex['spikes'])
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

        self.choose_move(self.leafeon, movedex['stealthrock'])
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()
        self.engine.init_turn()

        # NOTE: relies on AutoDecisionMaker always choosing choices[0]
        self.assertListEqual(self.faint_log, [self.vaporeon, self.jolteon,
                                              self.espeon, self.umbreon])
        self.assertTrue(self.flareon.is_active)
        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 4)

    def test_order_of_abilities_depends_on_speed_of_switchins(self):
        self.reset_leads('vaporeon', 'leafeon', p0_ability='drizzle', p1_ability='drought')
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

        self.reset_leads('jolteon', 'flareon', p0_ability='drizzle', p1_ability='drought')
        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

    # TODO: test order of switchins after both faint, and order on both actively switch, and try
    # each with both p0/p1 being faster so as to catch orderings based on order of
    # battlefield.sides

    @patch('random.randrange', lambda _: 0) # no miss
    def test_order_of_switchins_after_double_ko(self):
        self.add_pokemon('alakazam', 0, ability='drought')
        self.add_pokemon('slowbro', 1, ability='drizzle')
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.choose_move(self.leafeon, movedex['toxic'])
        self.run_turn()
        self.engine.init_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

    def test_order_of_active_switchins(self):
        self.add_pokemon('alakazam', 0, ability='drought')
        self.add_pokemon('slowbro', 1, ability='drizzle')
        self.choose_switch(self.vaporeon, self.alakazam)
        self.choose_switch(self.leafeon, self.slowbro)
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

        self.reset_leads('leafeon', 'vaporeon')
        self.add_pokemon('alakazam', 0, ability='drought')
        self.add_pokemon('slowbro', 1, ability='drizzle')
        self.choose_switch(self.leafeon, self.alakazam)
        self.choose_switch(self.vaporeon, self.slowbro)
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

    def test_ability_doesnt_start_on_switch_into_hazard_ko(self):
        self.add_pokemon('jolteon', 0, ability='desolateland')
        self.jolteon.hp = 1
        self.choose_move(self.leafeon, movedex['spikes'])
        self.choose_move(self.vaporeon, movedex['uturn'])
        self.run_turn()

        self.assertIsNone(self.battlefield.weather)
