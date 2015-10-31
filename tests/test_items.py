from mock import patch

from pokedex.abilities import abilitydex
from pokedex.enums import Status
from pokedex.items import itemdex
from pokedex.moves import movedex
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