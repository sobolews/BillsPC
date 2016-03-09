from bot.cheatsheetengine import CheatSheetEngine
from pokedex.moves import movedex
from tests.multi_move_test_case import MultiMoveTestCaseWithoutSetup

class TestCheatSheetEngine(MultiMoveTestCaseWithoutSetup):
    def test_calculate_expected_damage(self):
        self.new_battle('vaporeon', 'leafeon')
        cs = CheatSheetEngine.from_battlefield(self.battlefield)
        damage = cs.calculate_expected_damage(self.vaporeon, movedex['return'], self.leafeon)

        self.assertEqual(damage, 46)
