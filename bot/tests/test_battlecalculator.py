from bot.battlecalculator import BattleCalculator
from pokedex.moves import movedex
from tests.multi_move_test_case import MultiMoveTestCaseWithoutSetup

class TestBattleCalculator(MultiMoveTestCaseWithoutSetup):
    def test_calculate_expected_damage(self):
        self.new_battle('vaporeon', 'leafeon')
        bc = BattleCalculator.from_battlefield(self.battlefield)
        damage = bc.calculate_expected_damage(self.vaporeon, movedex['return'], self.leafeon)

        self.assertEqual(damage, 46)
