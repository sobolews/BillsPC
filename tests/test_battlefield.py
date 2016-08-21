from copy import deepcopy

from battle import effects
from battle.enums import Weather, SideCondition, Volatile, ABILITY, ITEM
from battle.moves import movedex
from tests.multi_move_test_case import MultiMoveTestCaseWithoutSetup

class TestDeepcopyBattlefield(MultiMoveTestCaseWithoutSetup):
    def test_deepcopy_battlefield(self):
        self.new_battle(p0_moves=('thunderwave', 'wish', 'substitute', 'disable'),
                        p0_item='choiceband',
                        p1_moves=('pursuit', 'phantomforce', 'spikes', 'knockoff'),
                        p1_ability='drizzle',
                        p1_item='leftovers')
        self.choose_move(self.vaporeon, 'wish')
        self.choose_move(self.leafeon, 'spikes')
        self.run_turn()
        self.vaporeon.set_effect(effects.Attract(self.leafeon))

        orig = self.battlefield
        clone = deepcopy(orig)
        self.assertIsNot(clone, orig)
        orig_side = orig.sides[0]
        clone_side = clone.sides[0]
        self.assertIsNot(clone_side, orig_side)
        clone_vaporeon = clone_side.team[0]
        self.assertIsNot(clone_vaporeon, self.vaporeon)
        orig_disable = next(move for move in self.vaporeon.moves if move.name == 'disable')
        clone_disable = next(move for move in clone_vaporeon.moves if move.name == 'disable')
        self.assertIs(clone_disable, orig_disable)
        self.assertIs(clone_disable, movedex['disable'])

        self.assertIsNot(clone.effect_handlers, orig.effect_handlers)
        self.assertIsNot(clone.get_effect(Weather.RAINDANCE),
                         orig.get_effect(Weather.RAINDANCE))
        self.assertIs(clone.get_effect(Weather.RAINDANCE).__class__,
                      orig.get_effect(Weather.RAINDANCE).__class__)
        self.assertIsNot(orig_side.effect_handlers, clone_side.effect_handlers)
        self.assertIsNot(clone_side.get_effect(SideCondition.WISH),
                         orig_side.get_effect(SideCondition.WISH))
        self.assertIsNot(clone_vaporeon.effect_handlers, self.vaporeon.effect_handlers)
        self.assertIsNot(clone_vaporeon.get_effect(Volatile.CHOICELOCK),
                         self.vaporeon.get_effect(Volatile.CHOICELOCK))

        orig_attract = self.vaporeon.get_effect(Volatile.ATTRACT)
        clone_attract = clone_vaporeon.get_effect(Volatile.ATTRACT)
        clone_leafeon = clone.sides[1].active_pokemon
        self.assertEqual(clone_leafeon.name, 'leafeon')

        self.assertIs(clone_vaporeon.side, clone.sides[0])
        self.assertIs(clone_leafeon.side, clone.sides[1])

        for key in self.leafeon._effect_index.keys() + self.vaporeon._effect_index.keys():
            self.assertIn(key,
                          clone_leafeon._effect_index.keys() + clone_vaporeon._effect_index.keys())
        for key in clone_leafeon._effect_index.keys() + clone_vaporeon._effect_index.keys():
            self.assertIn(key,
                          self.leafeon._effect_index.keys() + self.vaporeon._effect_index.keys())

        orig_ability_effect = self.leafeon.get_effect(ABILITY)
        clone_ability_effect = clone_leafeon.get_effect(ABILITY)
        self.assertIsNot(clone_ability_effect, orig_ability_effect)
        self.assertIs(orig_ability_effect.__class__, clone_ability_effect.__class__)
        self.assertIs(clone_leafeon.ability, self.leafeon.ability)

        orig_item_effect = self.leafeon.get_effect(ITEM)
        clone_item_effect = clone_leafeon.get_effect(ITEM)
        self.assertIsNot(clone_item_effect, orig_item_effect)
        self.assertIs(orig_item_effect.__class__, clone_item_effect.__class__)
        self.assertIs(clone_leafeon.item, self.leafeon.item)

        self.assertIsNot(clone_leafeon, self.leafeon)
        self.assertIsNot(clone_attract, orig_attract)
        self.assertIs(clone_attract.mate, clone_leafeon)
        self.assertIsNot(clone_attract.mate, self.leafeon)

        self.assertEqual(clone.turns, 1)
        self.run_turn()
        self.assertEqual(orig.turns, 2)
        self.assertEqual(clone.turns, 1)
