from mock import patch

from pokedex.enums import Status, Type
from pokedex.moves import movedex
from pokedex.stats import Boosts
from tests.multi_move_test_case import MultiMoveTestCase

class TestStatuses(MultiMoveTestCase):
    @patch('random.randrange', lambda *_: 1) # no parahax
    def test_paralyze_speed_drop(self):
        self.engine.set_status(self.leafeon, Status.PAR, None)
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    @patch('random.randrange', lambda *_: 1) # no auto thaw
    def test_freeze_block_move(self):
        self.engine.set_status(self.leafeon, Status.FRZ, None)
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.vaporeon.status)

    @patch('random.randrange', lambda *_: 0) # thaw
    def test_freeze_auto_thaw(self):
        self.engine.set_status(self.leafeon, Status.FRZ, None)
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.FNT)
        self.assertIsNone(self.leafeon.status)

    @patch('random.randrange', lambda *_: 1) # no auto thaw
    def test_freeze_thaw_by_use_move(self):
        self.engine.set_status(self.leafeon, Status.FRZ, None)
        self.leafeon.hp = 1
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'flamewheel')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(self.vaporeon.status, Status.FNT)
        self.assertIsNone(self.leafeon.status)

    @patch('random.randrange', lambda *_: 1) # no auto thaw
    def test_freeze_thaw_by_foe_move(self):
        self.new_battle('flareon', 'leafeon')
        self.engine.set_status(self.flareon, Status.FRZ, None)
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'scald')
        self.choose_move(self.flareon, 'return')
        self.run_turn()

        self.assertEqual(self.leafeon.status, Status.FNT)
        self.assertIsNone(self.flareon.status)

    @patch('random.randrange', lambda *_: 1) # no auto thaw, always freeze
    def test_freeze_shayminsky_causes_forme_change(self):
        self.new_battle('vaporeon', 'shayminsky', p1_ability='serenegrace')
        self.add_pokemon('leafeon', 1)
        self.assertEqual(self.shayminsky.name, 'shayminsky')
        self.choose_move(self.vaporeon, 'freezedry')
        self.run_turn()
        self.assertStatus(self.shayminsky, Status.FRZ)

        self.assertEqual(self.shayminsky.name, 'shaymin')
        self.assertEqual(self.shayminsky.types, [Type.GRASS, None])
        self.assertEqual(self.shayminsky.stats, {'max_hp': 341, 'atk': 236, 'def': 236,
                                                 'spa': 236, 'spd': 236, 'spe': 236})

        self.choose_switch(self.shayminsky, self.leafeon)
        self.run_turn()
        self.choose_switch(self.leafeon, self.shayminsky)
        self.run_turn()

        self.assertStatus(self.shayminsky, None) # naturalcure
        self.assertEqual(self.shayminsky.name, 'shaymin')
        self.assertEqual(self.shayminsky.types, [Type.GRASS, None])
        self.assertEqual(self.shayminsky.stats, {'max_hp': 341, 'atk': 236, 'def': 236,
                                                 'spa': 236, 'spd': 236, 'spe': 236})

    def test_sleep_block_move(self):
        self.new_battle('vaporeon', 'jolteon')
        self.vaporeon.apply_boosts(Boosts(spa=2))
        self.choose_move(self.jolteon, 'spore')
        self.choose_move(self.vaporeon, 'earthpower')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 0)
        self.assertEqual(self.vaporeon.status, Status.SLP)

    @patch('random.randrange', lambda *_: 1) # no miss, sleep for 3 turns
    def test_sleep_pokemon_wakes_up(self):
        self.new_battle('vaporeon', 'jolteon')
        self.choose_move(self.jolteon, 'splash')
        self.choose_move(self.vaporeon, 'spore')
        self.run_turn()

        for _ in range(3):
            self.choose_move(self.jolteon, 'return')
            self.choose_move(self.vaporeon, 'splash')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.jolteon, 'thunder')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 318)

    @patch('random.randrange', lambda *_: 1) # sleep for 3 turns
    def test_sleep_does_not_reset_upon_switch(self):
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'spore')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        for _ in range(2):
            self.choose_move(self.vaporeon, 'return')
            self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()
        self.choose_switch(self.flareon, self.vaporeon)
        self.run_turn()
        self.assertEqual(self.vaporeon.status, Status.SLP)
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 50)

    def test_burn_damage_drop(self):
        self.engine.init_turn()
        self.engine.set_status(self.leafeon, Status.BRN, None)
        self.engine.run_move(self.leafeon, movedex['doubleedge'], self.vaporeon)

        self.assertDamageTaken(self.vaporeon, 83)

    def test_burn_no_spa_drop(self):
        self.engine.init_turn()
        self.engine.set_status(self.leafeon, Status.BRN, None)
        self.engine.run_move(self.leafeon, movedex['dragonpulse'], self.vaporeon)

        self.assertDamageTaken(self.vaporeon, 51)

    @patch('random.randrange', lambda *_: 0) # no miss
    def test_burn_residual_damage(self):
        self.choose_move(self.vaporeon, 'willowisp')
        self.choose_move(self.leafeon, 'willowisp')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 50)
        self.assertDamageTaken(self.leafeon, 33)

    def test_poison_residual_damage(self):
        self.engine.set_status(self.vaporeon, Status.PSN, None)
        self.engine.set_status(self.leafeon, Status.PSN, None)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 50)
        self.assertDamageTaken(self.leafeon, 33)

    def test_toxic_residual_damage(self):
        self.new_battle('vaporeon', 'muk')
        self.choose_move(self.vaporeon, 'toxic')
        self.choose_move(self.muk, 'toxic')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25 + 3*25)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25 + 3*25 + 4*25)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25 + 3*25 + 4*25 + 5*25)
        self.run_turn()
        self.assertEqual(self.vaporeon.status, Status.FNT)

    def test_toxic_resets_on_switch_out(self):
        self.new_battle('vaporeon', 'muk')
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.vaporeon, 'toxic')
        self.choose_move(self.muk, 'toxic')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25 + 3*25)
        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 25 + 2*25 + 3*25 + 25)
