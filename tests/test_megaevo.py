from pokedex.enums import Weather, Type
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

    def test_mega_evolution(self):
        self.new_battle('vaporeon', 'charizard', p1_item='charizarditex', p1_ability='blaze')
        self.choose_move(self.charizard, 'dragonclaw')
        self.add_pokemon('leafeon', 1)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 89)
        self.assertFalse(self.charizard.is_mega)
        self.choose_move(self.charizard, 'dragonclaw')
        self.choose_mega_evo(self.charizard)
        self.run_turn()

        self.assertListEqual(self.charizard.types, [Type.FIRE, Type.DRAGON])
        self.assertAbility(self.charizard, 'toughclaws')
        self.assertDictEqual(self.charizard.stats, {'max_hp': 297, 'atk': 296, 'def': 258,
                                                    'spa': 296, 'spd': 206, 'spe': 236})
        self.assertDamageTaken(self.vaporeon, 89 + 250)
        self.assertFalse(self.charizard.can_mega_evolve)
        self.assertTrue(self.charizard.is_mega)

        self.choose_switch(self.charizard, self.leafeon)
        self.choose_move(self.vaporeon, 'roar')
        self.run_turn()

        self.assertActive(self.charizard)
        self.assertEqual(self.charizard.name, 'charizardmegax')
        self.assertListEqual(self.charizard.types, [Type.FIRE, Type.DRAGON])
        self.assertAbility(self.charizard, 'toughclaws')
        self.assertFalse(self.charizard.can_mega_evolve)
        self.assertTrue(self.charizard.is_mega)

    def test_mega_evolution_order(self):
        self.new_battle('tyranitar', 'charizard',
                        p0_ability='unnerve', p0_item='tyranitarite',
                        p1_ability='blaze', p1_item='charizarditey')
        self.choose_mega_evo(self.tyranitar)
        self.choose_mega_evo(self.charizard)
        self.choose_move(self.tyranitar, 'dragondance')
        self.choose_move(self.charizard, 'honeclaws')
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.SANDSTORM)

    def test_only_one_mega_evolution_allowed(self):
        self.new_battle('vaporeon', 'kangaskhan', p1_item='kangaskhanite')
        self.add_pokemon('beedrill', 1, item='beedrillite')
        self.choose_mega_evo(self.kangaskhan)
        self.choose_move(self.kangaskhan, 'poweruppunch')
        self.choose_move(self.vaporeon, 'hydropump')
        self.run_turn()
        self.assertBoosts(self.kangaskhan, {'atk': 2})

        self.assertFalse(self.beedrill.can_mega_evolve)

    def test_mega_evolution_ability_gain_and_loss(self):
        self.new_battle('absol', 'manectric',
                        p0_ability='lightningrod', p0_item='absolite',
                        p1_ability='contrary', p1_item='manectite')
        self.choose_mega_evo(self.absol)
        self.choose_mega_evo(self.manectric)
        self.choose_move(self.absol, 'partingshot')
        self.choose_move(self.manectric, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.absol, None)
        self.assertBoosts(self.absol, {'atk': -1, 'spa': 0})
        self.assertBoosts(self.manectric, {'atk': -1, 'spa': -1})

    def test_mega_evolution_speed_change_turn_order(self):
        self.new_battle('vaporeon', 'diancie', p1_item='diancite')
        self.choose_mega_evo(self.diancie)
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.choose_move(self.diancie, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.diancie, 22)

        self.choose_move(self.vaporeon, 'suckerpunch')
        self.choose_move(self.diancie, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 155)
        self.assertDamageTaken(self.diancie, 22)

    def test_mega_stone_removal(self):
        self.new_battle('vaporeon', 'blaziken', p1_item='blazikenite')

        self.choose_move(self.blaziken, 'switcheroo')
        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertItem(self.blaziken, 'blazikenite')

    def test_mega_evo_weight_change(self):
        self.new_battle('slowbro', 'volbeat', p0_item='slowbronite')

        self.choose_move(self.volbeat, 'grassknot')
        self.run_turn()

        self.assertDamageTaken(self.slowbro, 92)
        self.assertEqual(self.slowbro.weight, 78.5)

        self.choose_mega_evo(self.slowbro)
        self.choose_move(self.volbeat, 'grassknot')
        self.run_turn()

        self.assertDamageTaken(self.slowbro, 92 + 114)
        self.assertEqual(self.slowbro.weight, 120)

    def test_mega_evo_catching_hard_switch_with_pursuit(self):
        self.new_battle('gallade', 'leafeon', p0_item='galladite')
        self.add_pokemon('espeon', 1)
        self.choose_switch(self.leafeon, self.espeon)
        self.choose_mega_evo(self.gallade)
        self.choose_move(self.gallade, 'pursuit')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 85)
