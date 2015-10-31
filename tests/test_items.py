from mock import patch

from pokedex.abilities import abilitydex
from pokedex.enums import Status, Volatile, Weather
from pokedex.items import itemdex
from pokedex.moves import movedex
from pokedex.stats import Boosts
from tests.multi_move_test_case import MultiMoveTestCaseWithoutSetup

class TestItems(MultiMoveTestCaseWithoutSetup):
    @patch('random.choice', lambda choices: choices[0])
    def test_airballoon(self):
        self.reset_items('airballoon')
        self.add_pokemon('flareon', 0, item='airballoon')
        self.add_pokemon('umbreon', 0, item='airballoon')
        self.choose_move(self.leafeon, movedex['earthquake'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertItem(self.vaporeon, 'airballoon')

        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertItem(self.vaporeon, None)

        self.choose_move(self.leafeon, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 + 139)

        self.choose_move(self.leafeon, movedex['toxicspikes'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['roar'])
        self.run_turn()

        self.assertActive(self.flareon)
        self.assertStatus(self.flareon, None)

        self.choose_move(self.leafeon, movedex['roar'])
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PSN)

        self.choose_move(self.leafeon, movedex['stealthrock'])
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()

        self.assertDamageTaken(self.umbreon, self.umbreon.max_hp / 8)
        self.assertStatus(self.umbreon, None)
        self.assertItem(self.umbreon, 'airballoon')

    @patch('random.randrange', lambda _: 0) # no miss, confusion hit
    def test_airballoon_behind_substitute_and_confusion_damage(self):
        self.reset_items('airballoon', 'airballoon')
        self.choose_move(self.leafeon, movedex['substitute'])
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertItem(self.leafeon, None)

        self.choose_move(self.leafeon, movedex['confuseray'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 37)

        self.assertItem(self.vaporeon, 'airballoon')

    def test_assaultvest(self):
        self.reset_leads(p0_item='assaultvest',
                         p0_moves=[movedex['taunt'], movedex['recover'],
                                   movedex['protect'], movedex['leechseed']])
        self.assertMoveChoices(self.vaporeon, {movedex['struggle']})


        self.reset_leads(p0_item='assaultvest', p0_ability='noguard',
                         p0_moves=[movedex['taunt'], movedex['return'],
                                   movedex['protect'], movedex['leafblade']])

        self.assertMoveChoices(self.vaporeon, {movedex['return'], movedex['leafblade']})

        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

        self.choose_move(self.leafeon, movedex['leafstorm'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 + 156)

    def test_blacksludge(self):
        self.reset_leads('vaporeon', 'muk', p0_item='blacksludge', p1_item='blacksludge')
        self.choose_move(self.muk, movedex['bellydrum'])
        self.run_turn()

        self.assertDamageTaken(self.muk, (self.muk.max_hp / 2) - (self.muk.max_hp / 16))
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

    # def test_blueorb(self):
    #     pass # TODO when: implement forme changes

    def test_chestoberry(self):
        self.reset_leads(p0_ability='baddreams', p1_ability='noguard',
                         p0_item='chestoberry', p1_item='chestoberry')
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertDamageTaken(self.leafeon, 50)

        self.choose_move(self.leafeon, movedex['rest'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.assertItem(self.leafeon, 'chestoberry')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertStatus(self.leafeon, None)
        self.assertItem(self.leafeon, None)

        self.choose_move(self.vaporeon, movedex['darkvoid'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50 + self.leafeon.max_hp / 8)
        self.assertStatus(self.leafeon, Status.SLP)

    def test_choiceband(self):
        self.reset_leads(p0_item='choiceband', p1_item='choiceband',
                         p1_ability='magicbounce',
                         p0_moves=('xscissor', 'protect', 'taunt', 'dragonclaw'),
                         p1_moves=('return', 'toxic', 'ironhead', 'crunch'))
        self.add_pokemon('flareon', 0)
        self.add_pokemon('espeon', 1, item='choiceband')
        self.assertMoveChoices(self.vaporeon, ('xscissor', 'protect', 'taunt', 'dragonclaw'))
        self.assertMoveChoices(self.leafeon, ('return', 'toxic', 'ironhead', 'crunch'))

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['taunt'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 212)
        self.assertTrue(self.vaporeon.has_effect(Volatile.TAUNT))
        self.assertMoveChoices(self.vaporeon, {'struggle'})
        self.assertSwitchChoices(self.vaporeon, {self.flareon})
        self.assertMoveChoices(self.leafeon, {'return'})

        self.choose_switch(self.leafeon, self.espeon)
        self.choose_move(self.vaporeon, movedex['struggle'])
        self.run_turn()

        self.assertDamageTaken(self.espeon, 69)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.espeon, movedex['voltswitch'])
        self.choose_move(self.vaporeon, movedex['struggle'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 158 + self.vaporeon.max_hp / 4)
        self.assertActive(self.leafeon)
        self.assertMoveChoices(self.leafeon, ('return', 'toxic', 'ironhead', 'crunch'))

        self.run_turn()
        self.assertFalse(self.vaporeon.has_effect(Volatile.TAUNT))
        self.assertMoveChoices(self.vaporeon, {'taunt'})

        self.vaporeon.take_item()
        self.assertMoveChoices(self.vaporeon, ('xscissor', 'protect', 'taunt', 'dragonclaw'))

    def test_choicescarf(self):
        self.reset_leads(p0_item='choicescarf', p1_item='choicescarf',
                         p0_moves=('fakeout', 'protect', 'taunt', 'dragonclaw'),
                         p1_moves=('fakeout', 'toxic', 'ironhead', 'crunch'))
        self.engine.apply_boosts(self.leafeon, Boosts(spe=-1))
        self.choose_move(self.leafeon, movedex['fakeout'])
        self.choose_move(self.vaporeon, movedex['fakeout'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 20)
        self.assertMoveChoices(self.vaporeon, {'fakeout'})
        self.assertMoveChoices(self.leafeon, {'fakeout', 'toxic', 'ironhead', 'crunch'})

        self.choose_move(self.vaporeon, movedex['fakeout'])
        self.choose_move(self.leafeon, movedex['ironhead'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 20)
        self.assertDamageTaken(self.vaporeon, 56)
        self.assertMoveChoices(self.vaporeon, {'fakeout'})
        self.assertMoveChoices(self.leafeon, {'ironhead'})

    def test_choicespecs(self):
        self.reset_leads(p0_item='choicespecs', p1_item='choicespecs',
                         p0_moves=('fakeout', 'protect', 'taunt', 'dragonclaw'),
                         p1_moves=('surf', 'toxic', 'ironhead', 'crunch'))
        self.choose_move(self.leafeon, movedex['surf'])
        self.choose_move(self.vaporeon, movedex['dragonclaw'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 40)
        self.assertDamageTaken(self.leafeon, 39)
        self.assertMoveChoices(self.leafeon, {'surf'})
        self.assertMoveChoices(self.vaporeon, {'dragonclaw'})

    def test_custapberry(self):
        self.reset_items('custapberry')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertDamageTaken(self.vaporeon, 378)
        self.assertItem(self.vaporeon, 'custapberry')

        self.choose_move(self.leafeon, movedex['leafblade'])
        self.choose_move(self.vaporeon, movedex['flamethrower'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertDamageTaken(self.vaporeon, 378)
        self.assertItem(self.vaporeon, None)

        self.reset_items(None, 'custapberry')
        self.leafeon.hp = self.vaporeon.hp = 1
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['quickattack'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertStatus(self.vaporeon, None)

    def test_damprock(self):
        self.reset_leads(p0_item='damprock', p0_ability='drizzle')

        for _ in range(8):
            self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
            self.run_turn()
        self.assertIsNone(self.battlefield.weather)

        self.reset_items('damprock')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['raindance'])
        self.run_turn()

        for _ in range(7):
            self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
            self.run_turn()
        self.assertIsNone(self.battlefield.weather)

    def test_eviolite(self):
        self.reset_leads('vaporeon', 'porygon2', p0_item='eviolite', p1_item='eviolite')
        self.choose_move(self.porygon2, movedex['dragonclaw'])
        self.choose_move(self.vaporeon, movedex['xscissor'])
        self.run_turn()

        self.assertDamageTaken(self.porygon2, 36)
        self.assertDamageTaken(self.vaporeon, 86)

        self.reset_leads('spiritomb', 'scyther', p0_item='eviolite', p1_item='eviolite')
        self.choose_move(self.scyther, movedex['bugbuzz'])
        self.choose_move(self.spiritomb, movedex['shadowball'])
        self.run_turn()

        self.assertDamageTaken(self.scyther, 78)
        self.assertDamageTaken(self.spiritomb, 67)

    def test_expertbelt(self):
        self.reset_items('expertbelt', 'expertbelt')
        self.choose_move(self.leafeon, movedex['hiddenpowerelectric'])
        self.choose_move(self.vaporeon, movedex['flamecharge'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 86)
        self.assertDamageTaken(self.leafeon, 60)

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 86 + 142)
        self.assertDamageTaken(self.leafeon, 60 + 50)
