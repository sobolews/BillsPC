from mock import patch

from battle.battleengine import BattleEngine
from pokedex.abilities import abilitydex
from pokedex.enums import Status, Volatile, Weather, FAIL, SideCondition
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

    def test_fightinggem(self):
        self.reset_leads(p0_item='fightinggem', p1_item='fightinggem',
                         p0_ability='noguard', p1_ability='shielddust')
        self.add_pokemon('gengar', 0)
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['focusblast'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertItem(self.leafeon, 'fightinggem')
        self.assertDamageTaken(self.leafeon, 204)
        self.assertItem(self.vaporeon, None)

        self.engine.heal(self.leafeon, 300)
        self.choose_move(self.vaporeon, movedex['focusblast'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 157)

        self.choose_switch(self.vaporeon, self.gengar)
        self.choose_move(self.leafeon, movedex['drainpunch'])
        self.run_turn()

        self.assertDamageTaken(self.gengar, 0)
        self.assertItem(self.leafeon, 'fightinggem')

    def test_flameorb(self):
        self.reset_leads(p0_item='flameorb', p1_item='flameorb',
                         p0_ability='noguard')
        self.choose_move(self.leafeon, movedex['toxic'])
        self.assertStatus(self.leafeon, None)
        self.assertStatus(self.vaporeon, None)
        self.run_turn()

        self.assertStatus(self.leafeon, Status.BRN)
        self.assertStatus(self.vaporeon, Status.TOX)

        self.choose_move(self.leafeon, movedex['aromatherapy'])
        self.choose_move(self.vaporeon, movedex['psychoshift'])
        self.run_turn()

        self.assertStatus(self.leafeon, Status.TOX)
        self.assertStatus(self.vaporeon, Status.BRN)

    def test_flyinggem(self):
        self.reset_items('flyinggem', 'flyinggem')
        self.choose_move(self.leafeon, movedex['acrobatics'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 199)
        self.assertDamageTaken(self.leafeon, 50)

    @patch('random.randrange', lambda _: 0) # no miss, confusion hit
    def test_focussash(self):
        self.reset_leads('vaporeon', 'shedinja',
                         p0_item='focussash', p1_item='focussash')
        self.engine.apply_boosts(self.shedinja, Boosts(atk=5))
        self.choose_move(self.vaporeon, movedex['pursuit'])
        self.choose_move(self.shedinja, movedex['shadowclaw'])
        self.assertItem(self.vaporeon, 'focussash')
        self.assertItem(self.shedinja, 'focussash')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 1)
        self.assertDamageTaken(self.shedinja, 0)
        self.assertItem(self.vaporeon, None)
        self.assertItem(self.shedinja, None)

        self.choose_move(self.vaporeon, movedex['pursuit'])
        self.choose_move(self.shedinja, movedex['shadowclaw'])
        self.run_turn()

        self.assertFainted(self.shedinja)
        self.assertEqual(self.vaporeon.hp, 1)

        self.reset_leads('vaporeon', 'leafeon', # second hit should cause faint
                         p0_item='focussash', p1_ability='parentalbond')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()
        self.assertFainted(self.vaporeon)
        self.assertEqual(self.vaporeon.item.name, 'focussash')

        self.reset_leads('vaporeon', 'shedinja', # shouldn't block residual damage
                         p0_ability='noguard', p1_item='focussash')
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.run_turn()

        self.assertFainted(self.shedinja)

        self.reset_leads('vaporeon', 'shedinja', # shouldn't block recoil damage
                         p0_item='focussash', p1_item='focussash')
        self.add_pokemon('espeon', 1)
        self.engine.apply_boosts(self.shedinja, Boosts(atk=4, spe=2))
        self.choose_move(self.shedinja, movedex['doubleedge'])
        self.choose_move(self.vaporeon, movedex['synthesis'])
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 1 + (round(self.vaporeon.max_hp / 2.0)))
        self.assertFainted(self.shedinja)

        self.reset_leads('vaporeon', 'shedinja', # should block self-damage due to confusion
                         p1_item='focussash')
        self.choose_move(self.vaporeon, movedex['confuseray'])
        self.choose_move(self.shedinja, movedex['focusblast'])
        self.run_turn()

        self.assertDamageTaken(self.shedinja, 0)
        self.assertItem(self.shedinja, None)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_focussash_0_damage_shedinja_still_allows_other_effects(self):
        self.reset_leads('vaporeon', 'shedinja', p1_item='focussash')
        self.choose_move(self.vaporeon, movedex['nuzzle'])
        self.run_turn()

        self.assertItem(self.shedinja, None)
        self.assertDamageTaken(self.shedinja, 0)
        self.assertStatus(self.shedinja, Status.PAR)

        self.reset_leads('vaporeon', 'shedinja', p1_item='focussash')
        self.choose_move(self.vaporeon, movedex['flamecharge'])
        self.run_turn()

        self.assertItem(self.shedinja, None)
        self.assertDamageTaken(self.shedinja, 0)
        self.assertBoosts(self.vaporeon, {'spe': 1})

    def test_focussash_with_sturdy(self):
        self.reset_leads(p0_ability='sturdy', p0_item='focussash')
        self.choose_move(self.leafeon, movedex['woodhammer'])
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 1)
        self.assertItem(self.vaporeon, None)

    def test_griseousorb(self):
        self.reset_leads('vaporeon', 'giratinaorigin', p1_item='griseousorb')

        self.assertIs(self.giratinaorigin.take_item(), FAIL)

        self.choose_move(self.giratinaorigin, movedex['shadowball'])
        self.choose_move(self.vaporeon, movedex['dragonpulse'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 150)
        self.assertDamageTaken(self.giratinaorigin, 158)

        self.choose_move(self.giratinaorigin, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 150 + 150)

    def test_heatrock(self):
        self.reset_leads(p0_item='heatrock', p0_ability='drought')

        for _ in range(8):
            self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)
            self.run_turn()
        self.assertIsNone(self.battlefield.weather)

        self.reset_items('heatrock')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['sunnyday'])
        self.run_turn()

        for _ in range(7):
            self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)
            self.run_turn()
        self.assertIsNone(self.battlefield.weather)

    def test_leftovers(self):
        self.reset_leads(p0_item='leftovers', p1_item='leftovers',
                         p1_ability='noguard')
        self.add_pokemon('flareon', 0, item='leftovers')
        self.choose_move(self.leafeon, movedex['stealthrock'])
        self.choose_move(self.vaporeon, movedex['lightofruin'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 183 - self.leafeon.max_hp / 16)
        self.assertDamageTaken(self.vaporeon, 92 - self.vaporeon.max_hp / 16)

        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()

        self.assertDamageTaken(self.flareon, (self.flareon.max_hp / 4) - (self.flareon.max_hp / 16))

    @patch('random.randrange', lambda _: 0) # no miss, confusion hit
    def test_lifeorb(self):
        self.reset_items('lifeorb', 'lifeorb')
        self.add_pokemon('sylveon', 0, item='lifeorb')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['stickyweb'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 185)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 10)

        self.engine.heal(self.vaporeon, 400)
        self.engine.heal(self.leafeon, 400)
        self.choose_move(self.vaporeon, movedex['seismictoss'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 100)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 10)

        self.choose_switch(self.vaporeon, self.sylveon)
        self.choose_move(self.leafeon, movedex['outrage'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 100)
        self.assertDamageTaken(self.sylveon, 0)

        self.choose_move(self.leafeon, movedex['confuseray'])
        self.choose_move(self.sylveon, movedex['explosion'])
        self.run_turn()

        self.assertDamageTaken(self.sylveon, 45) # life orb boosted confusion hit

    def test_lifeorb_faint_order(self):
        self.reset_items(None, 'lifeorb')
        self.leafeon.hp = 10
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertFainted(self.leafeon)
        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    def test_lifeorb_with_sheerforce(self):
        self.reset_leads(p0_ability='sheerforce', p1_ability='sheerforce',
                         p0_item='lifeorb', p1_item='lifeorb')
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 10)
        self.assertDamageTaken(self.vaporeon, 185)

        self.engine.heal(self.vaporeon, 400)
        self.engine.heal(self.leafeon, 400)
        self.choose_move(self.vaporeon, movedex['flamecharge'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 83)
        self.assertBoosts(self.vaporeon, {'spe': 0})

    def test_lightclay(self):
        self.reset_items(None, 'lightclay')
        self.choose_move(self.leafeon, movedex['lightscreen'])
        self.choose_move(self.vaporeon, movedex['lightscreen'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['reflect'])
        self.choose_move(self.vaporeon, movedex['reflect'])
        self.run_turn()

        self.assertEqual(6, self.leafeon.side.get_effect(SideCondition.LIGHTSCREEN).duration)
        self.assertEqual(3, self.vaporeon.side.get_effect(SideCondition.LIGHTSCREEN).duration)
        self.assertEqual(7, self.leafeon.side.get_effect(SideCondition.REFLECT).duration)
        self.assertEqual(4, self.vaporeon.side.get_effect(SideCondition.REFLECT).duration)

    @patch('random.randrange', lambda _: 0) # parahax if possible; no miss
    def test_lumberry(self):
        self.reset_items('lumberry', 'lumberry')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertStatus(self.vaporeon, None)
        self.assertItem(self.leafeon, None)
        self.assertStatus(self.leafeon, None)
        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.leafeon, movedex['nuzzle'])
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertStatus(self.vaporeon, Status.PAR)

        self.reset_items('lumberry', 'lumberry')
        self.choose_move(self.leafeon, movedex['confuseray'])
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))
        self.assertItem(self.vaporeon, None)

    def test_lustrousorb(self):
        self.reset_leads('vaporeon', 'palkia',
                         p0_item='lustrousorb', p1_item='lustrousorb')
        self.choose_move(self.palkia, movedex['outrage'])
        self.choose_move(self.vaporeon, movedex['dragonpulse'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 324)
        self.assertDamageTaken(self.palkia, 136)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.palkia, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 150)
        self.assertIs(self.palkia.take_item(), itemdex['lustrousorb'])

    def test_normalgem(self):
        self.reset_items('normalgem', 'normalgem')
        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.vaporeon, movedex['rapidspin'])
        self.choose_move(self.leafeon, movedex['weatherball'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 14)
        self.assertItem(self.vaporeon, None)
        self.assertDamageTaken(self.vaporeon, 44)
        self.assertItem(self.leafeon, 'normalgem')

    def test_petayaberry(self):
        self.reset_items('petayaberry', 'petayaberry')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.choose_move(self.vaporeon, movedex['hypervoice'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)
        self.assertDamageTaken(self.leafeon, 176)
        self.assertBoosts(self.vaporeon, {'spa': 1})
        self.assertItem(self.vaporeon, None)
        self.assertItem(self.leafeon, 'petayaberry')

        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 176 + 50)
        self.assertBoosts(self.leafeon, {'spa': 1})
        self.assertItem(self.leafeon, None)

    def test_powerherb(self):
        self.reset_items('powerherb', 'powerherb')
        self.choose_move(self.leafeon, movedex['geomancy'])
        self.choose_move(self.vaporeon, movedex['solarbeam'])
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertItem(self.leafeon, None)
        self.assertBoosts(self.leafeon, {'spa': 2, 'spd': 2, 'spe': 2})
        self.assertDamageTaken(self.leafeon, 39)

        self.choose_move(self.leafeon, movedex['geomancy'])
        self.choose_move(self.vaporeon, movedex['solarbeam'])
        self.run_turn()

        self.assertMoveChoices(self.leafeon, {'geomancy'})
        self.assertMoveChoices(self.vaporeon, {'solarbeam'})
        self.assertBoosts(self.leafeon, {'spa': 2, 'spd': 2, 'spe': 2})
        self.assertDamageTaken(self.leafeon, 39)

    def test_redcard(self):
        self.reset_items('redcard', 'redcard')
        self.add_pokemon('flareon', 0, item='redcard', ability='flashfire')
        self.add_pokemon('jolteon', 1, item='redcard')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['earthquake'])
        self.run_turn()

        self.assertActive(self.flareon)
        self.assertActive(self.jolteon)
        self.assertDamageTaken(self.vaporeon, 142)
        self.assertDamageTaken(self.jolteon, 182)
        self.assertItem(self.vaporeon, None)
        self.assertItem(self.jolteon, None)
        self.assertItem(self.leafeon, 'redcard')

        self.choose_switch(self.jolteon, self.leafeon)
        self.run_turn()
        self.choose_move(self.leafeon, movedex['flamethrower'])
        self.choose_move(self.flareon, movedex['thunderwave'])
        self.run_turn()

        self.assertActive(self.flareon)
        self.assertActive(self.leafeon)
        self.assertDamageTaken(self.flareon, 0)
        self.assertTrue(self.flareon.has_effect(Volatile.FLASHFIRE))
        self.assertStatus(self.leafeon, Status.PAR)
        self.assertItem(self.flareon, 'redcard')
        self.assertItem(self.leafeon, 'redcard')

    @patch('random.randrange', lambda _: 0) # confusion hit
    def test_redcard_confusion_hit_doesnt_activate(self):
        self.reset_items('redcard', None)
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, movedex['confuseray'])
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()

        self.assertActive(self.leafeon)
        self.assertItem(self.vaporeon, 'redcard')
        self.assertDamageTaken(self.vaporeon, 37)

    def test_redcard_fails_if_holder_is_fainted(self):
        self.reset_items('redcard', None)
        self.add_pokemon('flareon', 0)
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, movedex['woodhammer'])
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()

        self.assertActive(self.leafeon)
        self.assertFainted(self.vaporeon)
        self.assertDamageTaken(self.leafeon, 132) # recoil

    def test_redcard_vs_sheerforce(self):
        """ The opponent's sheerforce should prevent redcard from activating """
        self.reset_leads(p0_item='redcard', p1_ability='sheerforce')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, movedex['flamecharge'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45)
        self.assertActive(self.leafeon)
        self.assertItem(self.vaporeon, 'redcard')

        self.choose_move(self.leafeon, movedex['dragonclaw'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45 + 112)
        self.assertActive(self.espeon)
        self.assertItem(self.vaporeon, None)

    def test_redcard_vs_suctioncups(self):
        """ RedCard activates but fails to force switch against suctioncups """
        self.reset_leads(p0_item='redcard', p1_ability='suctioncups')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertItem(self.vaporeon, None)
        self.assertActive(self.leafeon)

    # def test_redorb(self):
    #     pass # TODO when: implement forme changes

    def test_rockyhelmet(self):
        self.reset_leads(p0_item='rockyhelmet', p1_item='rockyhelmet',
                         p0_ability='noguard')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24 + (self.leafeon.max_hp / 6))
        self.assertDamageTaken(self.vaporeon, 142 + 0) # no rockyhelmet damage

        self.leafeon.hp = self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, movedex['vcreate'])
        self.run_turn()

        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    def test_scopelens(self):
        crit = [None]
        def get_critical_hit(crit_ratio):
            crit[0] = crit_ratio
            return BattleEngine.get_critical_hit(crit_ratio)

        self.reset_leads(p0_item='scopelens', p0_ability='superluck',
                         p1_ability='angerpoint')
        self.engine.get_critical_hit = get_critical_hit
        self.choose_move(self.vaporeon, movedex['nightslash'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 51)
        self.assertBoosts(self.leafeon, {'atk': 6})
        self.assertEqual(crit[0], 3)

        self.choose_move(self.vaporeon, movedex['bite'])
        self.run_turn()

        self.assertEqual(crit[0], 2)

    def test_sharpbeak(self):
        self.reset_items('sharpbeak', 'sharpbeak')
        self.choose_move(self.leafeon, movedex['acrobatics'])
        self.choose_move(self.vaporeon, movedex['xscissor'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 92)
        self.assertDamageTaken(self.leafeon, 78)

    def test_sitrusberry(self):
        self.reset_items('sitrusberry', 'sitrusberry')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.choose_move(self.vaporeon, movedex['eruption'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 122)
        self.assertDamageTaken(self.vaporeon, 378 - (self.vaporeon.max_hp / 4))
        self.assertItem(self.vaporeon, None)


    def test_sitrusberry_with_recoil_vs_rockyhelmet(self):
        self.reset_leads(p0_ability='noguard', p0_item='rockyhelmet',
                         p1_item='sitrusberry')
        self.leafeon.hp = 137
        self.choose_move(self.leafeon, movedex['headsmash'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertEqual(self.leafeon.item.name, 'sitrusberry')

    def test_sitrusberry_with_multiple_residuals(self):
        self.reset_leads('vaporeon', 'jolteon', p0_ability='noguard', p1_item='sitrusberry')
        self.choose_move(self.vaporeon, movedex['infestation'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['leechseed'])
        self.run_turn()
        self.engine.heal(self.jolteon, 400)
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.run_turn()
        self.jolteon.get_effect(Status.TOX).stage = 4
        self.jolteon.hp = 137
        self.run_turn()

        self.assertFainted(self.jolteon)
        self.assertEqual(self.jolteon.item.name, 'sitrusberry')

    def test_sitrusberry_with_multiple_hazards(self):
        self.reset_leads()
        self.add_pokemon('volcarona', 1, item='sitrusberry')
        self.volcarona.hp = int(self.volcarona.max_hp * 0.6)
        self.choose_move(self.vaporeon, movedex['stealthrock'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['spikes'])
        self.run_turn()
        self.choose_switch(self.leafeon, self.volcarona)
        self.run_turn()

        self.assertFainted(self.volcarona)

    def test_stick(self):
        crit = [None]
        def get_critical_hit(crit_ratio):
            crit[0] = crit_ratio
            return BattleEngine.get_critical_hit(crit_ratio)

        self.reset_leads('vaporeon', 'farfetchd', p0_item='stick', p1_item='stick')
        self.engine.get_critical_hit = get_critical_hit
        self.choose_move(self.farfetchd, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 246)
        self.assertEqual(crit[0], 3)

        self.choose_move(self.vaporeon, movedex['nightslash'])
        self.run_turn()

        self.assertEqual(crit[0], 1)

    def test_thickclub(self):
        self.reset_leads('vaporeon', 'marowak', p0_item='thickclub', p1_item='thickclub')
        self.choose_move(self.vaporeon, movedex['return'])
        self.choose_move(self.marowak, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.marowak, 57)
        self.assertDamageTaken(self.vaporeon, 319)

        self.choose_move(self.marowak, movedex['hypervoice'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 319 + 47)
