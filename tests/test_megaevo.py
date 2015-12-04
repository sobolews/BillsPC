from tests.multi_move_test_case import MultiMoveTestCaseWithoutSetup

class TestMegaEvolution(MultiMoveTestCaseWithoutSetup):
    def test_can_mega_evolve(self):
        self.new_battle('charizard', 'latios', p0_item='charizarditex', p1_item='latiosite')
        self.add_pokemon('salamence', 0, item='lifeorb')
        self.add_pokemon('pinsir', 0, item='gengarite')
        self.add_pokemon('scyther', 0, item='scizorite')
        self.assertTrue(self.charizard.can_mega_evolve)
        self.assertTrue(self.latios.can_mega_evolve)
        self.assertFalse(self.salamence.can_mega_evolve)
        self.assertFalse(self.pinsir.can_mega_evolve)
        self.assertFalse(self.scyther.can_mega_evolve)
