from mock import patch

from pokedex import statuses
from pokedex.abilities import abilitydex
from pokedex.enums import Status, Weather, Volatile, Hazard, PseudoWeather, Type
from pokedex.moves import movedex
from pokedex.stats import Boosts
from tests.multi_move_test_case import MultiMoveTestCaseWithoutSetup

class TestAbilities(MultiMoveTestCaseWithoutSetup):
    def test_adaptability(self):
        self.new_battle('vaporeon', 'blastoise', p0_ability='adaptability')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.blastoise, 80)

        self.choose_move(self.blastoise, 'surf')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.blastoise, 80 + 62)
        self.assertDamageTaken(self.vaporeon, 52)

    def test_aftermath(self):
        self.new_battle(p0_ability='aftermath')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertIsNone(self.vaporeon.status)
        self.assertIsNone(self.leafeon.status)

        self.vaporeon.hp = 1
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.FNT)
        self.assertStatus(self.leafeon, Status.FNT)
        self.assertEqual(self.battlefield.win, self.vaporeon.side.index)

    def test_aftermath_doesnt_activate_on_non_contact_move_damage(self):
        self.new_battle(p0_ability='aftermath')
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.new_battle(p0_ability='aftermath')
        self.vaporeon.hp = 1
        self.engine.set_status(self.vaporeon, Status.PSN, None)
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.FNT)

        self.assertDamageTaken(self.leafeon, 0)

    def test_aerilate(self):
        self.new_battle(p0_ability='aerilate')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 128)

        self.choose_move(self.vaporeon, 'aerialace')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 128 + 60)

        self.new_battle('tornadus', 'leafeon', p0_ability='aerilate')
        self.choose_move(self.tornadus, 'bodyslam')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 254)

    def test_airlock_and_cloudnine(self):
        for ability in ('airlock', 'cloudnine'):
            self.new_battle()
            self.add_pokemon('rayquaza', 0, ability=ability)
            self.battlefield.set_weather(Weather.SANDSTORM)
            self.choose_move(self.vaporeon, 'batonpass')
            self.run_turn()

            self.assertIsNone(self.battlefield.weather)
            self.assertEqual(self.battlefield._weather, Weather.SANDSTORM)
            self.assertDamageTaken(self.rayquaza, 0)
            self.assertDamageTaken(self.leafeon, 0)

            self.choose_switch(self.rayquaza, self.vaporeon)
            self.run_turn()

            self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)
            self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16)

            self.choose_switch(self.vaporeon, self.rayquaza)
            self.choose_move(self.leafeon, 'sunnyday')
            self.run_turn()
            self.assertTrue(self.battlefield.has_effect(Weather.SUNNYDAY))
            self.choose_move(self.leafeon, 'hiddenpowerfire')
            self.run_turn()

            self.assertDamageTaken(self.rayquaza, 19)

    def test_weather_starts_during_airlock_and_ends(self):
        self.new_battle(p0_ability='airlock')
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'raindance')

        for _ in range(3):
            self.run_turn()
            self.assertIsNone(self.battlefield.weather)

        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.run_turn()
        self.assertIsNone(self.battlefield.weather)

    def test_weather_ends_during_airlock(self):
        self.new_battle()
        self.add_pokemon('espeon', 0, ability='airlock')
        self.choose_move(self.vaporeon, 'sunnyday')
        for _ in range(3):
            self.run_turn()

        self.choose_switch(self.vaporeon, self.espeon)
        self.run_turn()
        self.assertIsNone(self.battlefield.weather)
        self.assertTrue(self.battlefield.has_effect(Weather.SUNNYDAY))
        self.run_turn()
        self.assertIsNone(self.battlefield.weather)
        self.assertFalse(self.battlefield.has_effect(Weather.SUNNYDAY))

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_blizzard_can_miss_in_airlocked_hail(self):
        self.new_battle(p1_ability='airlock')
        self.add_pokemon('umbreon', 1)
        self.battlefield.set_weather(Weather.HAIL)

        self.choose_move(self.vaporeon, 'blizzard')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_switch(self.leafeon, self.umbreon)
        self.choose_move(self.vaporeon, 'blizzard')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 81 + 20) # blizzard damage plus hail

    def test_analytic(self):
        self.new_battle(p0_ability='analytic',
                        p1_ability='analytic')
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertDamageTaken(self.leafeon, 64)

        self.vaporeon.apply_boosts(Boosts(spe=1))
        self.engine.heal(self.vaporeon, 200)
        self.engine.heal(self.leafeon, 200)
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 185)
        self.assertDamageTaken(self.leafeon, 50)

        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 113)

    def test_angerpoint(self):
        self.new_battle(p0_ability='angerpoint')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertEqual(0, self.vaporeon.boosts['atk'])

        self.choose_move(self.leafeon, 'stormthrow')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(6, self.vaporeon.boosts['atk'])
        self.assertDamageTaken(self.leafeon, 194)

    def test_arenatrap(self):
        self.new_battle(p0_ability='arenatrap')
        self.add_pokemon('flareon', 1, ability='arenatrap')
        self.add_pokemon('jolteon', 1)
        self.add_pokemon('umbreon', 0)
        self.engine.init_turn()

        self.assertSwitchChoices(self.leafeon, set())
        self.assertSwitchChoices(self.vaporeon, {self.umbreon})

        self.choose_move(self.leafeon, 'batonpass')
        self.run_turn()

        self.engine.init_turn()

        self.assertSwitchChoices(self.vaporeon, set())
        self.assertSwitchChoices(self.flareon, set())

    def test_arenatrap_doesnt_trap_flying(self):
        self.new_battle('vaporeon', 'pidgeot', p0_ability='arenatrap')
        self.add_pokemon('sylveon', 1, ability='levitate')
        self.engine.init_turn()

        self.assertSwitchChoices(self.pidgeot, {self.sylveon})

        self.choose_move(self.pidgeot, 'uturn')
        self.run_turn()
        self.engine.init_turn()

        self.assertSwitchChoices(self.sylveon, {self.pidgeot})

    def test_aromaveil(self):
        self.new_battle(p0_ability='aromaveil')
        self.choose_move(self.leafeon, 'taunt')
        self.choose_move(self.vaporeon, 'disable')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.TAUNT))
        self.assertTrue(self.leafeon.has_effect(Volatile.DISABLE))

        self.choose_move(self.leafeon, 'encore')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

        self.choose_move(self.leafeon, 'disable')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50 + 50)

    @patch('random.randrange', lambda _: 99) # moonblast: no spa drop
    def test_aurabreak(self):
        self.new_battle('xerneas', 'zygarde', p0_ability='fairyaura', p1_ability='aurabreak')
        self.choose_move(self.xerneas, 'moonblast')
        self.choose_move(self.zygarde, 'darkpulse')
        self.run_turn()

        self.assertDamageTaken(self.zygarde, 240)
        self.assertDamageTaken(self.xerneas, 29)

    @patch('random.randint', lambda *_: 1)
    def test_baddreams(self):
        self.new_battle(p1_ability='baddreams')
        self.choose_move(self.leafeon, 'spore')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)
        self.assertDamageTaken(self.leafeon, 50)

    def test_battlearmor(self):
        self.new_battle(p0_ability='battlearmor')
        self.choose_move(self.leafeon, 'stormthrow')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 84)

    def test_blaze(self):
        self.new_battle('flareon', 'leafeon', p0_ability='blaze')
        self.leafeon.apply_boosts(Boosts(atk=2))
        self.choose_move(self.leafeon, 'aquajet')
        self.choose_move(self.flareon, 'flamewheel')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 230)

    def test_bulletproof(self):
        self.new_battle(p0_ability='bulletproof')
        self.choose_move(self.vaporeon, 'shadowball')
        self.choose_move(self.leafeon, 'sludgebomb')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 105)

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    def test_cheekpouch(self):
        self.new_battle(p0_ability='cheekpouch', p0_item='sitrusberry',
                        p1_ability='noguard', p1_item='petayaberry')
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon,
                               378 - (self.vaporeon.max_hp / 4) - (self.vaporeon.max_hp / 3))

        self.choose_move(self.leafeon, 'leafstorm')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': 1})
        self.assertDamageTaken(self.vaporeon,
                               (378 + 230) -
                               (self.vaporeon.max_hp / 4) - (self.vaporeon.max_hp / 3) * 2)

    def test_chlorophyll(self):
        self.new_battle(p0_ability='chlorophyll')
        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertStatus(self.vaporeon, None)

    def test_chlorophyll_blocked_in_airlock(self):
        self.new_battle(p0_ability='chlorophyll', p1_ability='airlock')
        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertStatus(self.leafeon, None)

    def test_clearbody_and_whitesmoke(self):
        for ability in ('clearbody', 'whitesmoke'):
            self.new_battle(p0_ability=ability)
            self.choose_move(self.leafeon, 'partingshot')
            self.choose_move(self.vaporeon, 'superpower')
            self.run_turn()

            self.assertBoosts(self.vaporeon, {'atk': -1, 'spa': 0, 'def': -1})

            self.vaporeon.apply_boosts(Boosts(spe=-3), self_induced=False)
            self.assertEqual(self.vaporeon.boosts['spe'], 0)
            self.vaporeon.apply_boosts(Boosts(spe=-3), self_induced=True)
            self.assertEqual(self.vaporeon.boosts['spe'], -3)

    def test_competitive(self):
        self.new_battle(p0_ability='competitive')
        self.add_pokemon('umbreon', 0, ability='competitive')
        self.choose_move(self.leafeon, 'defog')
        self.choose_move(self.vaporeon, 'closecombat')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': 2, 'evn': -1, 'def': -1, 'spd': -1})

        self.choose_move(self.leafeon, 'stickyweb')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'memento')
        self.run_turn()

        self.assertBoosts(self.umbreon, {'spa': 4, 'atk': -2, 'spe': -1})

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_compoundeyes(self):
        self.new_battle(p0_ability='compoundeyes')
        self.choose_move(self.vaporeon, 'stoneedge')
        self.choose_move(self.leafeon, 'stoneedge')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 49)

    def test_contrary(self):
        self.new_battle(p0_ability='contrary')
        self.choose_move(self.leafeon, 'partingshot')
        self.choose_move(self.vaporeon, 'superpower')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 2, 'spa': 1, 'def': 1})
        self.assertDamageTaken(self.leafeon, 86)

        self.choose_move(self.vaporeon, 'agility')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spe': -2})

    @patch('random.randrange', lambda _: 2) # cursedbody success
    def test_cursedbody(self):
        self.new_battle(p0_ability='cursedbody', p1_moves=[movedex['return'], movedex['protect'],
                                                           movedex['foulplay'], movedex['toxic']])
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertMoveChoices(self.leafeon, ('protect', 'foulplay', 'toxic'))

        for _ in range(4):
            self.assertTrue(self.leafeon.has_effect(Volatile.DISABLE))
            self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.DISABLE))

    @patch('random.randrange', lambda _: 1) # cutecharm success and infatuate fail
    def test_cutecharm(self):
        self.new_battle(p0_ability='cutecharm', p0_gender='M', p1_gender='F')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertTrue(self.leafeon.has_effect(Volatile.ATTRACT))
        self.assertDamageTaken(self.vaporeon, 142)

        self.choose_move(self.leafeon, 'recover')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

        self.new_battle(p0_ability='cutecharm', p0_gender=None, p1_gender='F')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ATTRACT))

        self.new_battle(p0_ability='cutecharm', p1_ability='aromaveil',
                        p0_gender='F', p1_gender='M')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ATTRACT))

        self.new_battle(p0_ability='cutecharm', p0_gender='F', p1_gender='M')
        self.choose_move(self.leafeon, 'hypervoice')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ATTRACT))

    @patch('random.randrange', lambda _: 99) # no flinch
    def test_darkaura(self):
        self.new_battle('yveltal', 'leafeon', p0_ability='darkaura')
        self.choose_move(self.yveltal, 'darkpulse')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.yveltal, 99)
        self.assertDamageTaken(self.leafeon, 241)

        self.choose_move(self.leafeon, 'crunch')
        self.run_turn()
        self.assertDamageTaken(self.yveltal, 99 + 51)

    def test_defeatist(self):
        self.new_battle('archeops', 'leafeon', p0_ability='defeatist')
        self.choose_move(self.archeops, 'pluck')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 164)
        self.assertDamageTaken(self.archeops, 177)

        self.choose_move(self.archeops, 'pluck')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 164 + 84)

    def test_defiant(self):
        self.new_battle(p0_ability='defiant')
        self.choose_move(self.leafeon, 'partingshot')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 3, 'spa': -1})
        self.assertDamageTaken(self.leafeon, 122)

    def test_deltastream(self):
        self.new_battle()
        self.add_pokemon('umbreon', 0, ability='deltastream')
        self.add_pokemon('jolteon', 1, ability='deltastream')
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'sunnyday')
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.DELTASTREAM)

        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()

        self.assertIsNone(self.battlefield.weather)

        self.choose_move(self.leafeon, 'sunnyday')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'sunnyday')
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.DELTASTREAM)

        self.choose_switch(self.leafeon, self.jolteon)
        self.run_turn()
        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.DELTASTREAM)

        self.choose_switch(self.jolteon, self.leafeon)
        self.choose_move(self.vaporeon, 'raindance')
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

    def test_desolateland(self):
        self.new_battle()
        self.add_pokemon('umbreon', 0, ability='desolateland')
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'waterfall')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 0)
        self.assertEqual(self.battlefield.weather, Weather.DESOLATELAND)

    def test_download(self):
        self.new_battle(p0_ability='download', p1_ability='download')
        self.add_pokemon('umbreon', 0, ability='download')
        self.assertBoosts(self.vaporeon, {'atk': 0, 'spa': 1})
        self.assertBoosts(self.leafeon, {'atk': 1, 'spa': 0})
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertBoosts(self.umbreon, {'atk': 0, 'spa': 1})

    def test_drizzle(self):
        self.new_battle(p0_ability='drizzle')
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 132)

        self.new_battle(p0_ability='drizzle', p1_ability='desolateland')
        self.assertEqual(self.battlefield.weather, Weather.DESOLATELAND)

    def test_drought(self):
        self.new_battle(p0_ability='drought')
        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

    @patch('random.randrange', lambda _: 99) # no secondary effects
    def test_dryskin(self):
        self.new_battle(p0_ability='dryskin')
        self.choose_move(self.leafeon, 'scald')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'raindance')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 - 50)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, 'flareblitz')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 52 - 50)

        self.choose_move(self.leafeon, 'sunnyday')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 52 - 50 + 50)

    @patch('random.randint', lambda *_: 3)
    def test_earlybird(self):
        self.new_battle(p0_ability='earlybird')
        self.choose_move(self.leafeon, 'spore')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertEqual(self.vaporeon.get_effect(Status.SLP).turns_left, 1)
        self.assertEqual(self.vaporeon.sleep_turns, 1)

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

    @patch('random.randint', lambda *_: 1)
    def test_earlybird_immediate_wake_up(self):
        self.new_battle(p0_ability='earlybird')
        self.choose_move(self.leafeon, 'spore')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

    @patch('random.randrange', lambda _: 25) # poison
    def test_effectspore(self):
        self.new_battle('vaporeon', 'flareon', p0_ability='effectspore')
        self.choose_move(self.flareon, 'return')
        self.run_turn()

        self.assertStatus(self.flareon, Status.PSN)
        self.flareon.cure_status()

        self.choose_move(self.flareon, 'earthquake')
        self.run_turn()

        self.assertStatus(self.flareon, None)

    @patch('random.randrange', lambda _: 25) # poison
    def test_effectspore_vs_grass_type(self):
        self.new_battle(p0_ability='effectspore')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertStatus(self.leafeon, None)

    def test_filter(self):
        self.new_battle(p0_ability='filter')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 283)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    @patch('random.randrange', lambda _: 2)
    def test_flamebody(self):
        self.new_battle(p0_ability='flamebody')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.BRN)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 8)

    def test_flashfire(self):
        self.new_battle('vaporeon', 'espeon', p0_ability='flashfire')
        self.choose_move(self.espeon, 'sacredfire')
        self.choose_move(self.vaporeon, 'hiddenpowerfire')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 87)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertStatus(self.vaporeon, None)
        self.assertTrue(self.vaporeon.has_effect(Volatile.FLASHFIRE))

        self.choose_move(self.espeon, 'willowisp')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 87 + 130)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_flowergift(self):
        self.new_battle('cherrim', 'leafeon', p0_ability='flowergift')
        self.choose_move(self.leafeon, 'sunnyday')
        self.choose_move(self.cherrim, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 69)

        self.choose_move(self.leafeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.cherrim, 42)

    def test_existence_of_noneffect_abilities(self):
        self.new_battle(p0_ability='flowerveil')
        self.new_battle(p0_ability='frisk')
        self.new_battle(p0_ability='illusion')
        self.new_battle(p0_ability='symbiosis')

    def test_forecast(self):
        self.new_battle('vaporeon', 'castform',
                        p0_ability='snowwarning', p1_ability='forecast')
        self.add_pokemon('espeon', 0, ability='airlock')
        self.add_pokemon('flareon', 0)

        self.assertEqual(self.castform.types[0], Type.ICE)

        self.choose_move(self.castform, 'sunnyday')
        self.choose_move(self.vaporeon, 'raindance')
        self.run_turn()

        self.assertEqual(self.castform.types[0], Type.WATER)

        self.choose_switch(self.vaporeon, self.espeon)
        self.choose_move(self.castform, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 60)
        self.assertEqual(self.castform.types[0], Type.NORMAL)

        self.choose_switch(self.espeon, self.flareon)
        self.choose_move(self.castform, 'aquajet')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 174)
        self.assertEqual(self.castform.types[0], Type.WATER)

    def test_furcoat(self):
        self.new_battle(p0_ability='furcoat')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192)

        self.choose_move(self.leafeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192 + 27)

    def test_galewings(self):
        self.new_battle(p0_ability='galewings')
        self.add_pokemon('jolteon', 1)
        self.vaporeon.hp = self.leafeon.hp = self.jolteon.hp = 1
        self.choose_move(self.vaporeon, 'hiddenpowerflying')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertStatus(self.vaporeon, None)

        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.jolteon, 'thunderbolt')
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertStatus(self.jolteon, None)

    @patch('random.randrange', lambda _: 1) # no parahax
    def test_guts(self):
        self.new_battle(p0_ability='guts', p1_ability='guts')
        self.engine.set_status(self.vaporeon, Status.BRN, None)
        self.choose_move(self.vaporeon, 'facade')
        self.choose_move(self.leafeon, 'xscissor')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112 + 50)
        self.assertDamageTaken(self.leafeon, 100)

    def test_harvest(self):
        self.new_battle(p0_ability='harvest', p0_item='lumberry', p1_ability='noguard')
        self.add_pokemon('flareon', 0, ability='harvest', item='sitrusberry')
        with patch('random.randrange', lambda _: 0): # harvest success
            for _ in range(3):
                self.choose_move(self.leafeon, 'thunderwave')
                self.run_turn()
                self.assertStatus(self.vaporeon, None)
                self.assertItem(self.vaporeon, 'lumberry')

        with patch('random.randrange', lambda _: 1): # harvest failure; no parahax
            self.choose_move(self.leafeon, 'thunderwave')
            self.run_turn()
            self.assertStatus(self.vaporeon, None)
            self.assertItem(self.vaporeon, None)

            self.choose_move(self.leafeon, 'thunderwave')
            self.choose_move(self.vaporeon, 'sunnyday')
            self.run_turn()
            self.assertStatus(self.vaporeon, None)
            self.assertItem(self.vaporeon, None)

        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_move(self.leafeon, 'rockslide')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 210 - 2 * (self.flareon.max_hp / 4)) # 2 sitrusberries
        self.assertItem(self.flareon, None)

        self.choose_switch(self.flareon, self.vaporeon)
        self.choose_move(self.leafeon, 'willowisp')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)
        self.assertStatus(self.vaporeon, None)
        self.assertItem(self.vaporeon, None)

    def test_harvest_is_prevented_by_item_removal(self):
        for move in ('knockoff', 'bugbite', 'trick'):
            self.new_battle(p0_ability='harvest', p0_item='lumberry', p1_ability='noguard')
            self.choose_move(self.leafeon, 'willowisp')
            self.choose_move(self.vaporeon, 'sunnyday')
            self.run_turn()
            self.assertStatus(self.vaporeon, None)
            self.assertItem(self.vaporeon, 'lumberry')
            self.assertDamageTaken(self.vaporeon, 0)

            self.choose_move(self.leafeon, move)
            self.run_turn()

            self.assertItem(self.vaporeon, None)

            self.choose_move(self.leafeon, 'thunderwave')
            self.run_turn()

            self.assertStatus(self.vaporeon, Status.PAR)

    def test_harvest_stops_after_using_other_item(self):
        self.new_battle(p0_ability='harvest', p0_item='lumberry',
                        p1_ability='noguard', p1_item='normalgem')
        self.choose_move(self.leafeon, 'willowisp')
        self.choose_move(self.vaporeon, 'sunnyday')
        self.run_turn()
        self.assertStatus(self.vaporeon, None)
        self.assertItem(self.vaporeon, 'lumberry')

        self.choose_move(self.leafeon, 'switcheroo')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 64)

        self.assertItem(self.vaporeon, None)
        self.assertIsNone(self.vaporeon.last_berry_used)

        self.choose_move(self.leafeon, 'willowisp')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertStatus(self.vaporeon, Status.BRN)

    def test_hugepower(self):
        self.new_battle(p0_ability='hugepower', p1_ability='hugepower')
        self.choose_move(self.leafeon, 'hiddenpowergrass')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 108)
        self.assertDamageTaken(self.leafeon, 98)

    def test_hustle(self):
        with patch('random.randrange', lambda _: 71): # no miss
            self.new_battle(p0_ability='hustle', p1_ability='hustle')
            self.choose_move(self.vaporeon, 'aquatail')
            self.choose_move(self.leafeon, 'hydropump')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 32)
            self.assertDamageTaken(self.leafeon, 48)

        with patch('random.randrange', lambda _: 72): # miss at 90% * 80% accuracy
            self.new_battle(p0_ability='hustle', p1_ability='hustle')
            self.choose_move(self.vaporeon, 'aquatail')
            self.choose_move(self.leafeon, 'hydropump')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 32)
            self.assertDamageTaken(self.leafeon, 0)

    @patch('random.randrange', lambda _: 1) # no parahax
    def test_hydration(self):
        self.new_battle(p0_ability='hydration')
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'raindance')
        self.engine.set_status(self.leafeon, Status.PSN, None)
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, Status.PSN)

        for _ in range(4):
            self.run_turn()

        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PAR)

    def test_hypercutter(self):
        self.new_battle(p0_ability='hypercutter', p1_ability='intimidate')
        self.assertBoosts(self.vaporeon, {'atk': 0})
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 0, 'spa': -1})

    def test_icebody(self):
        self.new_battle(p0_ability='icebody')
        self.choose_move(self.leafeon, 'return')
        self.battlefield.set_weather(Weather.HAIL)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 - 25)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)

    def test_immunity(self):
        self.new_battle('gligar', 'muk', p0_ability='immunity')
        self.choose_move(self.muk, 'toxic')
        self.run_turn()

        self.assertStatus(self.gligar, None)

        self.choose_move(self.muk, 'glare')
        self.run_turn()

        self.assertStatus(self.gligar, Status.PAR)

    def test_imposter_transformation(self):
        self.new_battle('ditto', p0_ability='imposter', p1_ability='download',
                        p0_moves=[movedex['transform']], p1_gender='F',
                        p1_moves=(movedex['leafblade'], movedex['xscissor'],
                                  movedex['swordsdance'], movedex['toxic']))

        self.assertTrue(self.ditto.is_transformed)
        self.assertEqual(self.ditto.name, 'leafeon')
        self.assertEqual(self.ditto.base_species, 'ditto')
        ditto_stats = self.ditto.stats.copy()
        self.assertEqual(ditto_stats.pop('max_hp'), 237)
        self.assertDictContainsSubset(ditto_stats, self.leafeon.stats)
        self.assertEqual(self.ditto.weight, self.leafeon.weight)
        self.assertEqual(self.ditto.ability, self.leafeon.ability)
        self.assertEqual(self.ditto.base_ability.name, 'imposter')
        self.assertEqual(self.ditto.gender, self.leafeon.gender)
        self.assertSequenceEqual(self.ditto.moveset, self.leafeon.moveset)
        self.assertListEqual(self.ditto.types, self.leafeon.types)

        self.assertBoosts(self.leafeon, {'spa': 1})
        self.assertBoosts(self.ditto, {'spa': 2})

    def test_imposter_fail_to_transform_substitute(self):
        self.new_battle()
        self.add_pokemon('ditto', 0, ability='imposter')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertActive(self.ditto)
        self.assertFalse(self.ditto.is_transformed)

    def test_imposter_fail_to_transform_illusion(self):
        self.new_battle('ditto', p0_ability='imposter', p1_ability='illusion')
        self.assertFalse(self.ditto.is_transformed)

    def test_imposter_moves(self):
        self.new_battle('ditto', p0_ability='imposter',
                        p1_moves=(movedex['leafblade'], movedex['xscissor'],
                                  movedex['swordsdance'], movedex['return']))

        self.assertEqual(self.ditto.calculate_stat('spe'),
                         self.leafeon.calculate_stat('spe'))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.ditto, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 76)
        self.assertDamageTaken(self.ditto, 76)
        self.assertEqual(self.ditto.pp[movedex['return']], 4)

    def test_imposter_switch_and_transform_different_foes(self):
        self.new_battle(p1_moves=(movedex['leafblade'], movedex['uturn'],
                                  movedex['swordsdance'], movedex['return']), p1_ability='moxie')
        self.add_pokemon('ditto', 0, ability='imposter')
        self.add_pokemon('umbreon', 1, moves=(movedex['stickyweb'], movedex['splash'],
                                              movedex['swordsdance'], movedex['foulplay']),
                         ability='flowerveil')

        self.choose_move(self.leafeon, 'swordsdance')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertBoosts(self.ditto, {'atk': 2})
        self.assertDamageTaken(self.leafeon, 68)
        self.assertAbility(self.ditto, 'moxie')

        self.leafeon.apply_boosts(Boosts(spe=1))
        self.choose_move(self.leafeon, 'uturn')
        self.choose_move(self.ditto, 'return')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 173)
        self.assertDamageTaken(self.ditto, 206)

        self.choose_switch(self.ditto, self.vaporeon)
        self.choose_move(self.umbreon, 'stickyweb')
        self.run_turn()

        self.choose_move(self.vaporeon, 'voltswitch')
        self.choose_move(self.umbreon, 'splash')
        self.run_turn()

        self.assertFalse(self.ditto.boosts)
        self.assertTrue(all(pp == 5 for pp in self.ditto.pp.values()))
        self.assertDamageTaken(self.ditto, 206)
        self.assertEqual(self.ditto.name, 'umbreon')
        self.assertAbility(self.ditto, 'flowerveil')
        self.assertEqual(self.ditto.base_ability.name, 'imposter')

    def test_imposter_copy_ability(self):
        self.new_battle('ditto', p0_ability='imposter', p1_ability='magicbounce',
                        p1_moves=(movedex['partingshot'], movedex['xscissor'],
                                  movedex['swordsdance'], movedex['return']))
        self.assertEqual(self.ditto.ability, self.leafeon.ability)
        self.assertEqual(self.ditto.base_ability.name, 'imposter')

        self.choose_move(self.ditto, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.ditto, {'spa': -1, 'atk': -1})

        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': -1, 'atk': -1})

    def test_imposter_switch_into_toxic_spikes_with_poison_foe(self):
        self.new_battle('vaporeon', 'muk', p1_ability='prankster')
        self.add_pokemon('ditto', 0, ability='imposter', item='choicescarf')
        self.choose_move(self.muk, 'toxicspikes')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertActive(self.ditto)
        self.assertStatus(self.ditto, Status.PSN)
        self.assertEqual(self.ditto.types[0], Type.POISON)
        self.assertDamageTaken(self.ditto, self.ditto.max_hp / 8)

    def test_imposter_with_choice_scarf_struggles_after_5_moves(self):
        self.new_battle('ditto', 'leafeon', p0_ability='imposter', p0_item='choicescarf',
                        p1_ability='chlorophyll',
                        p1_moves=('earthquake', 'xscissor', 'swordsdance', 'return'))
        self.assertMoveChoices(self.ditto, {'earthquake', 'xscissor', 'swordsdance', 'return'})
        for _ in range(4):
            self.choose_move(self.leafeon, 'swordsdance')
            self.choose_move(self.ditto, 'earthquake')
            self.run_turn()
            self.assertMoveChoices(self.ditto, {'earthquake'})

        self.choose_move(self.leafeon, 'swordsdance')
        self.choose_move(self.ditto, 'earthquake')
        self.run_turn()
        self.assertMoveChoices(self.ditto, {'struggle'})
        self.assertEqual(self.ditto.pp[movedex['earthquake']], 0)

    def test_infiltrator(self):
        self.new_battle(p0_ability='infiltrator', p1_ability='infiltrator')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'lightscreen')
        self.run_turn()

        self.engine.heal(self.leafeon, 200)
        self.choose_move(self.leafeon, 'surf')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)
        self.assertDamageTaken(self.vaporeon, 27)

        self.choose_move(self.leafeon, 'reflect')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88 + 50)

    def test_innerfocus(self):
        self.new_battle(p0_ability='innerfocus')
        self.choose_move(self.leafeon, 'fakeout')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1, 'def': 1})

    def test_insomnia_and_sweetveil_and_vitalspirit(self):
        for ability in ('insomnia', 'sweetveil', 'vitalspirit'):
            self.new_battle(p0_ability=ability, p1_ability=ability)
            self.choose_move(self.leafeon, 'spore')
            self.choose_move(self.vaporeon, 'yawn')
            self.run_turn()

            self.assertIsNone(self.vaporeon.status)
            self.assertFalse(self.leafeon.has_effect(Volatile.YAWN))

            self.choose_move(self.leafeon, 'return')
            self.choose_move(self.vaporeon, 'rest')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 142)
            self.assertStatus(self.vaporeon, None)

            # hack a sleep onto vaporeon, check that it wakes up anyway
            self.vaporeon.status = Status.SLP
            self.vaporeon._effect_index[Status.SLP] = statuses.Sleep(self.vaporeon, 2)
            self.run_turn()

            self.assertIsNone(self.vaporeon.status)

    def test_intimidate(self):
        self.new_battle(p0_ability='intimidate', p1_ability='competitive')
        self.add_pokemon('flareon', 0, ability='intimidate')
        self.add_pokemon('espeon', 1, ability='intimidate')

        self.assertBoosts(self.leafeon, {'atk': -1, 'spa': 2})

        self.choose_move(self.leafeon, 'voltswitch')
        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 86) # vaporeon -1 atk
        self.assertBoosts(self.espeon, {'atk': -1})
        self.assertBoosts(self.flareon, {'atk': 0})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_ironbarbs(self):
        self.new_battle(p0_ability='ironbarbs', p1_ability='ironbarbs')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24 + (self.leafeon.max_hp / 8))
        self.assertDamageTaken(self.vaporeon, 142 + 0) # no ironbarbs damage

        self.leafeon.hp = self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'vcreate')
        self.run_turn()

        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    @patch('random.randrange', lambda _: 99) # no secondary effect
    def test_ironfist(self):
        self.new_battle(p0_ability='ironfist', p1_ability='ironfist')
        self.choose_move(self.leafeon, 'thunderpunch')
        self.choose_move(self.vaporeon, 'shadowpunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 35)
        self.assertDamageTaken(self.vaporeon, 252)

    def test_justified(self):
        self.new_battle(p0_ability='justified', p1_ability='justified')
        self.choose_move(self.leafeon, 'knockoff')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1})
        self.assertBoosts(self.leafeon, {'atk': 0})

    def test_justified_doesnt_activate_behind_substitute(self):
        self.new_battle(p1_ability='justified')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()
        self.choose_move(self.vaporeon, 'darkpulse')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': 0})

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_keeneye(self):
        self.new_battle(p0_ability='keeneye')
        self.leafeon.apply_boosts(Boosts(evn=6))
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

        self.vaporeon.apply_boosts(Boosts(acc=-1), self_induced=False)

        self.assertBoosts(self.vaporeon, {'acc': 0})

        self.vaporeon.apply_boosts(Boosts(acc=-1), self_induced=True)

        self.assertBoosts(self.vaporeon, {'acc': -1})

    def test_levitate(self):
        self.new_battle(p0_ability='levitate', p1_ability='levitate')
        self.choose_move(self.leafeon, 'earthquake')
        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertTrue(self.leafeon.side.has_effect(Hazard.SPIKES))

        self.choose_move(self.leafeon, 'bulldoze')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertBoosts(self.vaporeon, {'spe': 0})

    def test_lightningrod(self):
        self.new_battle(p0_ability='lightningrod', p1_ability='lightningrod')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, 'thunderbolt')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': 1})
        self.assertStatus(self.leafeon, None)
        self.assertBoosts(self.vaporeon, {'spa': 1})
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, 'voltswitch')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

    def test_lightningrod_magiccoat(self):
        self.new_battle(p0_ability='lightningrod')
        self.choose_move(self.vaporeon, 'magiccoat')
        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)
        self.assertBoosts(self.vaporeon, {'spa': 0})

    @patch('random.randrange', lambda _: 0) # bodyslam paralyzes
    def test_limber(self):
        self.new_battle(p0_ability='limber', p1_ability='limber')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.choose_move(self.leafeon, 'bodyslam')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, None)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_liquidooze(self):
        self.new_battle(p0_ability='liquidooze')
        self.choose_move(self.leafeon, 'drainpunch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 105)
        self.assertDamageTaken(self.leafeon, 53) # ceil(105 * 0.5)

        self.choose_move(self.leafeon, 'leechseed')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 105 + 50)
        self.assertDamageTaken(self.leafeon, 53 + 50)

        self.new_battle(p0_ability='liquidooze')
        self.vaporeon.hp = self.leafeon.hp = 200
        self.choose_move(self.leafeon, 'recover')
        self.choose_move(self.vaporeon, 'recover')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_liquidooze_behind_substitute(self):
        self.new_battle(p0_ability='liquidooze')
        self.choose_move(self.leafeon, 'suckerpunch')
        self.choose_move(self.vaporeon, 'substitute')
        self.run_turn()
        self.choose_move(self.leafeon, 'drainingkiss')
        self.run_turn()

        self.assertEqual(self.vaporeon.get_effect(Volatile.SUBSTITUTE).hp,
                         100 - 30)
        self.assertDamageTaken(self.leafeon, 23) # ceil(30 * 0.75)

        self.choose_move(self.leafeon, 'drainpunch')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.SUBSTITUTE))
        self.assertDamageTaken(self.vaporeon, 100) # from substitute only
        self.assertDamageTaken(self.leafeon, 23 + 35) # ceil(70 * 0.5)

    def test_liquidooze_wins_tie(self):
        self.new_battle(p1_ability='liquidooze')
        self.vaporeon.hp = 10
        self.leafeon.hp = 30
        self.choose_move(self.vaporeon, 'drainingkiss')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)
        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    def test_magicbounce(self):
        self.new_battle(p0_ability='magicbounce')
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'partingshot')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, Status.PAR)
        self.assertBoosts(self.leafeon, {'spa': -1, 'atk': -1})

    def test_magicbounce_no_infinite_recursion(self):
        self.new_battle(p0_ability='magicbounce', p1_ability='magicbounce')
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'partingshot')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)
        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_magicbounce_magiccoat(self):
        self.new_battle(p1_ability='magicbounce')
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'magiccoat')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)

    def test_magicbounce_encore(self):
        self.new_battle(p1_ability='magicbounce')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'encore')
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ENCORE))
        self.assertFalse(self.vaporeon.has_effect(Volatile.ENCORE))

    @patch('random.randrange', lambda _: 0) # no miss
    def test_magicguard(self):
        self.new_battle(p0_ability='magicguard', p0_item='lifeorb',
                        p1_ability='magicguard')
        self.add_pokemon('umbreon', 0, ability='magicguard')
        self.add_pokemon('jolteon', 1, ability='magicguard')

        self.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'toxicspikes')
        self.run_turn()
        self.choose_move(self.leafeon, 'willowisp')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()
        self.choose_move(self.leafeon, 'leechseed')
        self.choose_move(self.vaporeon, 'infestation')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 70)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, 'batonpass')
        self.choose_move(self.vaporeon, 'batonpass')
        self.run_turn()

        self.assertTrue(self.umbreon.has_effect(Volatile.LEECHSEED))
        self.assertActive(self.umbreon)
        self.assertActive(self.jolteon)
        self.assertDamageTaken(self.umbreon, 0)
        self.assertDamageTaken(self.jolteon, 0)

        self.choose_move(self.umbreon, 'return')
        self.choose_move(self.jolteon, 'spikyshield')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 0)
        self.assertDamageTaken(self.jolteon, 0)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_magicguard_vs_liquidooze(self): # move does damage but no heal/recoil
        self.new_battle(p0_ability='liquidooze', p1_ability='magicguard')
        self.leafeon.hp = 100
        self.choose_move(self.leafeon, 'leechseed')
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 100)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

    def test_magicguard_vs_destinybond(self):
        self.new_battle(p0_ability='magicguard')
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    @patch('random.randrange', lambda _: 0) # no miss; confusion roll fails
    def test_magicguard_vs_confusiondamage_perishsong_and_bellydrum(self):
        self.new_battle(p0_ability='magicguard', p1_ability='magicguard')
        self.choose_move(self.leafeon, 'perishsong')
        self.choose_move(self.vaporeon, 'bellydrum')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 2)
        self.assertBoosts(self.vaporeon, {'atk': 6})

        self.choose_move(self.leafeon, 'confuseray')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 200 + 145) # bellydrum + confusion damage at +6 atk

        self.run_turn()
        self.run_turn()
        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_magicguard_with_struggle_and_substitute(self):
        self.new_battle(p0_ability='magicguard')
        self.choose_move(self.vaporeon, 'substitute')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 4)

        self.choose_move(self.vaporeon, 'struggle')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 2 * self.vaporeon.max_hp / 4)

    def test_magicguard_vs_recoil(self):
        self.new_battle(p0_ability='magicguard')
        self.choose_move(self.vaporeon, 'flareblitz')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    def test_magicguard_with_explosion(self):
        self.new_battle(p0_ability='magicguard')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 119)
        self.assertFainted(self.vaporeon)

    def test_magicguard_vs_aftermath_and_ironbarbs(self):
        self.new_battle(p0_ability='magicguard', p1_ability='aftermath')
        self.add_pokemon('jolteon', 1, ability='ironbarbs')
        self.leafeon.hp = 10
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    def test_magician(self):
        self.new_battle(p0_ability='magician', p1_item='stick')
        self.add_pokemon('jolteon', 1, item='toxicorb')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, 'stick')

        self.choose_switch(self.leafeon, self.jolteon)
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertItem(self.vaporeon, 'stick')
        self.assertItem(self.jolteon, 'toxicorb')
        self.assertStatus(self.jolteon, Status.TOX)

        self.new_battle(p0_ability='magician')
        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

    def test_magician_steals_items_before_they_are_used(self):
        self.new_battle(p0_ability='magician', p1_item='sitrusberry')
        self.add_pokemon('espeon', 1, item='weaknesspolicy')
        self.vaporeon.hp = 100
        self.choose_move(self.vaporeon, 'icebeam')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 236)
        self.assertEqual(self.vaporeon.hp, 200)
        self.assertItem(self.leafeon, None)

        self.choose_switch(self.leafeon, self.espeon)
        self.choose_move(self.vaporeon, 'darkpulse')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 156)
        self.assertItem(self.espeon, None)
        self.assertItem(self.vaporeon, 'weaknesspolicy')

    def test_magician_ko_with_knockoff_steals_item(self):
        self.new_battle(p0_ability='magician', p1_item='flameorb')
        self.leafeon.hp = 10
        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, 'flameorb')
        self.assertStatus(self.vaporeon, Status.BRN)

    def test_magnetpull(self):
        self.new_battle('vaporeon', 'steelix', p0_ability='magnetpull')
        self.add_pokemon('aegislash', 1)
        self.add_pokemon('glaceon', 1)
        self.engine.init_turn()

        self.assertSwitchChoices(self.steelix, set())

        self.choose_move(self.steelix, 'voltswitch')
        self.run_turn()
        self.assertActive(self.aegislash)

        self.assertSwitchChoices(self.aegislash, {self.steelix, self.glaceon})

        self.choose_switch(self.aegislash, self.glaceon)
        self.run_turn()

        self.assertSwitchChoices(self.glaceon, {self.aegislash, self.steelix})

    @patch('random.randrange', lambda _: 1) # no miss; no parahax
    def test_marvelscale(self):
        self.new_battle(p0_ability='marvelscale', p1_ability='marvelscale',
                        p0_moves=(movedex['xscissor'], movedex['drillpeck'],
                                  movedex['poisonjab'], movedex['sleeptalk']))
        self.choose_move(self.vaporeon, 'drillpeck')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertDamageTaken(self.leafeon, 78)

        self.engine.heal(self.vaporeon, 200)
        self.engine.heal(self.leafeon, 200)
        self.vaporeon.apply_boosts(Boosts(spe=1))
        self.choose_move(self.vaporeon, 'thunderwave')
        self.choose_move(self.leafeon, 'sleeppowder')
        self.run_turn()

        self.choose_move(self.vaporeon, 'sleeptalk')
        self.choose_move(self.leafeon, 'boltstrike')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 242)
        self.assertDamageTaken(self.leafeon, 54)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_megalauncher(self):
        self.new_battle(p0_ability='megalauncher', p1_ability='megalauncher')
        self.choose_move(self.vaporeon, 'dragonpulse')
        self.choose_move(self.leafeon, 'leafstorm')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 230)
        self.assertDamageTaken(self.leafeon, 166)

    def test_motordrive(self):
        self.new_battle(p0_ability='motordrive', p1_ability='motordrive')
        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spe': 1})
        self.assertBoosts(self.vaporeon, {'spe': 1})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_moxie(self):
        self.new_battle(p0_ability='moxie')
        self.add_pokemon('flareon', 1)
        self.add_pokemon('jolteon', 1)
        self.leafeon.hp = self.flareon.hp = self.jolteon.hp = 1
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertFainted(self.leafeon)

        self.assertBoosts(self.vaporeon, {'atk': 1})

        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()
        self.assertFainted(self.flareon)

        self.assertBoosts(self.vaporeon, {'atk': 1})

        self.engine.init_turn()
        self.assertFainted(self.jolteon)

        self.assertBoosts(self.vaporeon, {'atk': 1})

    @patch('random.randrange', lambda _: 0) # no miss; confusion damage
    def test_multiscale(self):
        self.new_battle(p0_ability='multiscale', p1_ability='multiscale')
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 189)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)

        self.leafeon.cure_status()
        self.choose_move(self.leafeon, 'milkdrink')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 25)

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 189 + 142)
        self.assertDamageTaken(self.leafeon, 25 + 50)

        self.vaporeon.hp = self.vaporeon.max_hp
        self.choose_move(self.leafeon, 'confuseray')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 18) # half of normal confusion damage

    def test_multitype_vs_imposter(self):
        self.new_battle('ditto', 'arceusground',
                        p0_ability='imposter', p0_item='ironplate',
                        p1_ability='multitype', p1_item='earthplate')
        self.assertListEqual(self.ditto.types, [Type.GROUND, None])
        self.assertAbility(self.ditto, 'imposter')

    def test_mummy(self):
        self.new_battle(p0_ability='mummy', p1_ability='lightningrod')
        self.add_pokemon('sylveon', 0, 'flowerveil')
        self.add_pokemon('jolteon', 1, 'levitate')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'fusionbolt')
        self.run_turn()

        self.assertAbility(self.leafeon, 'mummy')
        self.assertEqual(self.leafeon.base_ability.name, 'lightningrod')
        self.assertDamageTaken(self.leafeon, 24)

        self.choose_switch(self.vaporeon, self.sylveon)
        self.run_turn()
        self.choose_move(self.sylveon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24 + 50)
        self.assertAbility(self.sylveon, 'mummy')

        self.choose_switch(self.leafeon, self.jolteon)
        self.choose_move(self.sylveon, 'whirlwind')
        self.run_turn()

        self.assertActive(self.leafeon)
        self.assertAbility(self.leafeon, 'lightningrod')
        self.assertEqual(self.leafeon.base_ability.name, 'lightningrod')
        self.choose_move(self.sylveon, 'thunderwave')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': 1})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_naturalcure(self):
        self.new_battle(p0_ability='naturalcure', p1_ability='naturalcure')
        self.add_pokemon('flareon', 0, ability='naturalcure')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, 'toxic')
        self.choose_move(self.vaporeon, 'darkvoid')
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.TOX)
        self.assertStatus(self.leafeon, Status.SLP)
        self.choose_switch(self.leafeon, self.espeon)
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()
        self.flareon.hp -= 1
        self.choose_move(self.flareon, 'rest')
        self.run_turn()
        self.assertStatus(self.flareon, Status.SLP)
        self.assertTrue(self.flareon.is_resting)
        self.choose_switch(self.flareon, self.vaporeon)
        self.choose_switch(self.espeon, self.leafeon)
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, None)
        self.assertStatus(self.flareon, None)
        self.assertFalse(self.flareon.is_resting)

    @patch('random.randrange', lambda _: 99) # miss if possible; no secondary effect
    def test_noguard(self):
        def test():
            self.vaporeon.apply_boosts(Boosts(acc=-6))
            self.leafeon.apply_boosts(Boosts(acc=-4))
            self.choose_move(self.leafeon, 'focusblast')
            self.choose_move(self.vaporeon, 'phantomforce')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 71)

            self.choose_move(self.leafeon, 'focusblast')
            self.choose_move(self.vaporeon, 'phantomforce')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 2 * 71)
            self.assertDamageTaken(self.leafeon, 44)

            self.choose_move(self.vaporeon, 'spore')
            self.run_turn()

            self.assertStatus(self.leafeon, None)

        self.new_battle(p0_ability='noguard')
        test()
        self.new_battle(p1_ability='noguard')
        test()

    @patch('random.randrange', lambda _: 25) # effectspore causes poison
    def test_overcoat(self):
        self.new_battle(p0_ability='overcoat', p1_ability='effectspore')
        self.battlefield.set_weather(Weather.HAIL)
        self.run_turn()
        self.battlefield.set_weather(Weather.SANDSTORM)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 2 * (self.leafeon.max_hp / 16))
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)

    def test_overgrow(self):
        self.new_battle(p1_ability='overgrow')
        self.vaporeon.apply_boosts(Boosts(spe=2))
        self.choose_move(self.vaporeon, 'bugbuzz')
        self.choose_move(self.leafeon, 'energyball')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 236)
        self.assertDamageTaken(self.vaporeon, 240)

        self.choose_move(self.leafeon, 'ironhead')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 240 + 56)

    def test_owntempo(self):
        self.new_battle(p0_ability='owntempo', p1_ability='noguard')
        self.choose_move(self.leafeon, 'confuseray')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))

        self.choose_move(self.leafeon, 'dynamicpunch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 139)
        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))

    def test_parentalbond(self):
        self.new_battle('vaporeon', 'espeon', p0_ability='parentalbond', p1_ability='justified')
        self.choose_move(self.vaporeon, 'darkpulse')
        self.run_turn()

        self.assertDamageTaken(self.espeon, 156 + 80) # 80 + 40 BP
        self.assertBoosts(self.espeon, {'atk': 2})

        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()

        self.assertEqual(self.espeon.side.get_effect(Hazard.SPIKES).layers, 1)

    def test_parentalbond_break_substitute(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4 + 45) # sub + 45 BP
        self.assertFalse(self.leafeon.has_effect(Volatile.SUBSTITUTE))

    def test_parentalbond_secondary_effects_trigger_twice(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.vaporeon, 'poweruppunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 20 + 16) # 40BP + (+1)20BP
        self.assertBoosts(self.vaporeon, {'atk': 2})

        self.leafeon.hp = 1
        self.choose_move(self.vaporeon, 'poweruppunch')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertBoosts(self.vaporeon, {'atk': 3})

    def test_parentalbond_fakeout_activates_steadfast_once(self):
        self.new_battle(p0_ability='parentalbond', p1_ability='steadfast')
        self.choose_move(self.vaporeon, 'fakeout')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 20 + 11)
        self.assertBoosts(self.leafeon, {'spe': 1})

    @patch('random.choice', lambda _: 5) # iciclespear hits 5 times
    def test_parentalbond_doesnt_affect_multihit(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.vaporeon, 'iciclespear')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 5 * 26)

    def test_parentalbond_doesnt_affect_status_move(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1, 'def': 1})

        self.choose_move(self.vaporeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': -1, 'spa': -1})

    def test_parentalbond_doesnt_affect_selfdestruct_moves(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 119)
        self.assertFainted(self.vaporeon)

    def test_parentalbond_doesnt_affect_charge_moves(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'phantomforce')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 142)
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'phantomforce')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertDamageTaken(self.leafeon, 44)

    def test_parentalbond_vs_ironbarbs(self):
        self.new_battle(p0_ability='parentalbond', p1_ability='ironbarbs')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50 + 26)
        self.assertDamageTaken(self.vaporeon, 2 * (self.vaporeon.max_hp / 8))

    def test_parentalbond_with_recoil_move(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.vaporeon, 'doubleedge')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 58 + 30)
        self.assertDamageTaken(self.vaporeon, 29)

    def test_parentalbond_with_drain_move(self):
        self.new_battle(p0_ability='parentalbond', p1_ability='ironbarbs')
        self.vaporeon.hp = 100
        self.choose_move(self.vaporeon, 'drainpunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 37 + 19)
        self.assertEqual(self.vaporeon.hp, 100 + 19 - 50 + 10 - 50) # 29

    def test_parentalbond_with_seismictoss(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.vaporeon, 'seismictoss')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 200)

    def test_parentalbond_with_counter(self):
        self.new_battle(p0_ability='parentalbond')
        self.choose_move(self.leafeon, 'aquajet')
        self.choose_move(self.vaporeon, 'counter')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 28)
        self.assertDamageTaken(self.leafeon, 28 * 4)

    def test_parentalbond_breaks_sturdy(self):
        self.new_battle(p0_ability='sturdy', p1_ability='parentalbond')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    def test_pickpocket(self):
        self.new_battle(p0_ability='pickpocket', p1_item='sitrusberry')
        self.add_pokemon('jolteon', 1, item='airballoon')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378 - self.vaporeon.max_hp / 4)
        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, None)

        self.choose_switch(self.leafeon, self.jolteon)
        self.run_turn()
        self.choose_move(self.jolteon, 'powergem')
        self.choose_move(self.vaporeon, 'recover')
        self.run_turn()

        self.assertItem(self.jolteon, 'airballoon')

        self.choose_move(self.jolteon, 'return')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 182)
        self.assertItem(self.vaporeon, 'airballoon')
        self.assertItem(self.jolteon, None)

    def test_pickpocket_vs_suicide_lifeorb(self):
        self.new_battle(p0_ability='pickpocket', p1_item='lifeorb')
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 1)
        self.assertItem(self.vaporeon, 'lifeorb')

    def test_pickpocket_vs_suicide_recoil(self):
        self.new_battle(p0_ability='pickpocket', p1_item='heatrock')
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'doubleedge')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, 'heatrock')

    def test_pickpocket_vs_sheerforce(self):
        self.new_battle(p0_ability='pickpocket',
                        p1_ability='sheerforce', p1_item='scopelens')
        self.choose_move(self.leafeon, 'flamecharge')
        self.run_turn()

        self.assertItem(self.leafeon, 'scopelens')
        self.assertItem(self.vaporeon, None)

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, 'scopelens')

    def test_pickup(self):
        self.new_battle(p0_ability='pickup', p1_item='sitrusberry')
        self.choose_move(self.vaporeon, 'hiddenpowerice')
        self.run_turn()
        self.assertItem(self.leafeon, None)
        self.assertDamageTaken(self.leafeon, 158 - self.leafeon.max_hp / 4)
        self.assertItem(self.vaporeon, 'sitrusberry')

        self.new_battle(p0_ability='pickup', p1_item='airballoon')
        self.choose_move(self.vaporeon, 'hiddenpowerice')
        self.run_turn()
        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, None)

        self.new_battle(p0_ability='pickup', p1_item='flyinggem')
        self.choose_move(self.leafeon, 'hiddenpowerflying')
        self.choose_move(self.vaporeon, 'hiddenpowerflying')
        self.run_turn()
        self.assertItem(self.leafeon, None)
        self.assertDamageTaken(self.vaporeon, 47)
        self.assertItem(self.vaporeon, 'flyinggem')
        self.assertDamageTaken(self.leafeon, 158)

        self.new_battle(p0_ability='pickup', p1_item='whiteherb')
        self.choose_move(self.vaporeon, 'partingshot')
        self.run_turn()
        self.assertItem(self.vaporeon, 'whiteherb')

        self.new_battle(p0_ability='pickup', p1_item='weaknesspolicy')
        self.choose_move(self.vaporeon, 'iceshard')
        self.choose_move(self.leafeon, 'thunderbolt')
        self.run_turn()
        self.assertItem(self.vaporeon, 'weaknesspolicy')

        self.new_battle(p0_item='focussash', p1_ability='pickup')
        self.choose_move(self.leafeon, 'woodhammer')
        self.run_turn()
        self.assertItem(self.leafeon, 'focussash')

    def test_pickup_doesnt_pick_up_knocked_off_items(self):
        self.new_battle(p0_ability='pickup', p1_item='sitrusberry')
        self.leafeon.hp = 150
        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()

        self.assertItem(self.leafeon, None)
        self.assertEqual(self.leafeon.hp, 150 - 47)
        self.assertItem(self.vaporeon, None)

    def test_pixilate(self):
        self.new_battle('sylveon', 'flareon', p0_ability='pixilate', p1_ability='pixilate')
        self.choose_move(self.flareon, 'substitute')
        self.choose_move(self.sylveon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.flareon, (self.flareon.max_hp / 4) + 75)
        self.assertTrue(self.flareon.has_effect(Volatile.SUBSTITUTE))

        self.engine.heal(self.flareon, 200)
        self.flareon.remove_effect(Volatile.SUBSTITUTE)
        self.choose_move(self.flareon, 'return')
        self.choose_move(self.sylveon, 'psyshock')
        self.run_turn()

        self.assertDamageTaken(self.sylveon, 201)
        self.assertDamageTaken(self.flareon, 112)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_poisonheal(self):
        self.new_battle(p0_ability='poisonheal', p1_ability='poisonheal')
        self.add_pokemon('umbreon', 1)
        self.choose_move(self.leafeon, 'toxic')
        self.choose_move(self.vaporeon, 'toxicspikes')
        self.run_turn()
        self.choose_switch(self.leafeon, self.umbreon)
        self.choose_move(self.vaporeon, 'roar')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 0)
        self.assertStatus(self.vaporeon, Status.TOX)
        self.assertStatus(self.leafeon, Status.PSN)

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'flamethrower')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 236 - self.leafeon.max_hp / 8)
        self.assertDamageTaken(self.vaporeon, 142 - self.vaporeon.max_hp / 8)

        self.leafeon.hp = 100
        self.engine.heal(self.vaporeon, 400)
        self.leafeon.change_ability(abilitydex['mummy'], self.engine)
        self.vaporeon.change_ability(abilitydex['mummy'], self.engine)
        self.leafeon.cure_status()
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 100)
        self.assertDamageTaken(self.vaporeon, 4 * (self.vaporeon.max_hp / 16))

    def test_poisontouch(self):
        self.new_battle(p0_ability='poisontouch', p1_ability='steadfast')
        self.vaporeon.apply_boosts(Boosts(spe=1))
        with patch('random.randrange', lambda _: 5): # icepunch freezes before poisontouch
            self.choose_move(self.vaporeon, 'icepunch')
            self.run_turn()

        self.assertDamageTaken(self.leafeon, 74)
        self.assertStatus(self.leafeon, Status.FRZ)

        self.leafeon.cure_status()
        self.engine.heal(self.leafeon, 300)

        with patch('random.randrange', lambda _: 15): # no freeze, poisontouch succeeds
            self.choose_move(self.vaporeon, 'icepunch')
            self.run_turn()

        self.assertDamageTaken(self.leafeon, 74 + self.leafeon.max_hp / 8)
        self.assertStatus(self.leafeon, Status.PSN)

        self.leafeon.cure_status()
        self.engine.heal(self.leafeon, 300)

        with patch('random.randrange', lambda _: 15): # flinch and poison
            self.choose_move(self.vaporeon, 'ironhead')
            self.choose_move(self.leafeon, 'return')
            self.run_turn()

        self.assertDamageTaken(self.leafeon, 39 + self.leafeon.max_hp / 8)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertBoosts(self.leafeon, {'spe': 1})
        self.assertStatus(self.leafeon, Status.PSN)

        self.leafeon.cure_status()
        self.engine.heal(self.leafeon, 300)

        self.vaporeon.apply_boosts(Boosts(spe=-1))
        with patch('random.randrange', lambda _: 15): # flinch and poison
            self.choose_move(self.leafeon, 'substitute')
            self.choose_move(self.vaporeon, 'ironhead')
            self.run_turn()

        self.assertStatus(self.leafeon, None)

    def test_prankster(self):
        self.new_battle(p0_ability='prankster')
        self.vaporeon.apply_boosts(Boosts(spe=-5))
        self.choose_move(self.leafeon, 'partingshot')
        self.choose_move(self.vaporeon, 'taunt')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 0, 'spa': 0})

        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    def test_prankster_vs_priority(self):
        self.new_battle(p0_ability='prankster')
        self.vaporeon.apply_boosts(Boosts(spe=-5))
        self.choose_move(self.leafeon, 'fakeout')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.leafeon, None)

        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, 'quickattack')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.leafeon, None)
        self.assertFainted(self.vaporeon)

    def test_pressure(self):
        self.new_battle(p0_moves=(movedex['protect'], movedex['rest'],
                                  movedex['toxic'], movedex['return']),
                        p1_moves=(movedex['xscissor'], movedex['drillpeck'],
                                  movedex['dragonclaw'], movedex['bulkup']),
                        p0_ability='pressure')
        self.choose_move(self.leafeon, 'xscissor')
        self.choose_move(self.vaporeon, 'protect')
        self.run_turn()

        self.assertPpUsed(self.leafeon, 'xscissor', 2)
        self.assertPpUsed(self.vaporeon, 'protect', 1)

        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertPpUsed(self.leafeon, 'bulkup', 1)
        self.assertPpUsed(self.vaporeon, 'return', 1)

    def test_primordialsea(self):
        self.new_battle()
        self.add_pokemon('umbreon', 0, ability='primordialsea')
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, 'flamecharge')
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 0)
        self.assertEqual(self.battlefield.weather, Weather.PRIMORDIALSEA)

        self.choose_switch(self.umbreon, self.vaporeon)
        self.choose_move(self.leafeon, 'flamecharge')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spe': 1})

    def test_protean(self):
        self.new_battle(p0_ability='protean', p1_ability='protean')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'flamecharge')
        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 52)
        self.assertIn(Type.FIRE, self.leafeon.types)
        self.assertNotIn(Type.GRASS, self.leafeon.types)
        self.assertIn(Type.GROUND, self.vaporeon.types)
        self.assertNotIn(Type.WATER, self.vaporeon.types)

        self.choose_move(self.leafeon, 'thunderwave')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertDamageTaken(self.leafeon, 146)

        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_move(self.leafeon, 'whirlwind')
        self.run_turn()

        self.assertListEqual(self.vaporeon.types, list(self.vaporeon.pokedex_entry.types))

    def test_protean_vs_immunity(self):
        self.new_battle(p0_ability='protean', p1_ability='levitate')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertEqual(self.vaporeon.types, [Type.GROUND, None])

    def test_double_taunt_protean(self):
        self.new_battle(p0_ability='protean')
        self.choose_move(self.vaporeon, 'taunt')
        self.run_turn()
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()
        self.choose_move(self.vaporeon, 'taunt')
        self.run_turn()

        self.assertEqual(self.vaporeon.types, [Type.DARK, None])

    def test_protean_when_toxic_spikes_fails(self):
        self.new_battle(p0_ability='protean')
        for _ in range(2):
            self.choose_move(self.vaporeon, 'toxicspikes')
            self.run_turn()

        self.choose_move(self.vaporeon, 'flamecharge')
        self.run_turn()
        self.assertEqual(self.vaporeon.types, [Type.FIRE, None])
        self.choose_move(self.vaporeon, 'toxicspikes')
        self.run_turn()

        self.assertEqual(self.vaporeon.types, [Type.POISON, None])

    def test_protean_vs_magicbounce(self):
        self.new_battle(p0_ability='protean', p1_ability='magicbounce')
        self.choose_move(self.vaporeon, 'taunt')
        self.run_turn()

        self.assertEqual(self.vaporeon.types, [Type.DARK, None])

    def test_protean_second_fakeout(self):
        self.new_battle(p0_ability='protean')
        self.choose_move(self.vaporeon, 'flamecharge')
        self.run_turn()
        self.choose_move(self.vaporeon, 'fakeout')
        self.run_turn()

        self.assertEqual(self.vaporeon.types, [Type.NORMAL, None])

    def test_protean_suckerpunch(self):
        self.new_battle(p0_ability='protean')
        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.run_turn()

        self.assertEqual(self.vaporeon.types, [Type.DARK, None])

    def test_purepower(self):
        self.new_battle(p0_ability='purepower', p1_ability='purepower')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 283)
        self.assertDamageTaken(self.leafeon, 88)

    @patch('random.randrange', lambda _: 1) # no parahax
    def test_quickfeet(self):
        self.new_battle(p0_ability='quickfeet')
        self.add_pokemon('flareon', 0, ability='quickfeet')
        self.flareon.status = Status.PAR
        self.add_pokemon('umbreon', 0, ability='quickfeet')
        self.umbreon.status = Status.BRN
        self.vaporeon.hp = self.flareon.hp = self.umbreon.hp = 1
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertFainted(self.vaporeon)

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.flareon, 'raindance')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()
        self.assertFainted(self.flareon)

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

        self.choose_move(self.umbreon, 'sunnyday')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()
        self.assertFainted(self.umbreon)

        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

    def test_raindish(self):
        self.new_battle(p0_ability='raindish', p1_ability='airlock')
        self.add_pokemon('glaceon', 1, ability='drizzle')
        self.add_pokemon('flareon', 1, ability='primordialsea')
        self.choose_move(self.leafeon, 'nightshade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 100)

        self.choose_switch(self.leafeon, self.flareon)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 100 - self.vaporeon.max_hp / 16)

        self.choose_switch(self.flareon, self.glaceon)
        self.run_turn()
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

        self.assertDamageTaken(self.vaporeon, 100 - 2 * (self.vaporeon.max_hp / 16))

        self.choose_switch(self.glaceon, self.leafeon)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 100 - 2 * (self.vaporeon.max_hp / 16))

    @patch('random.randrange', lambda _: 0) # no miss
    def test_reckless(self):
        self.new_battle(p0_ability='reckless', p1_ability='reckless')
        self.choose_move(self.leafeon, 'headcharge')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 200)
        self.assertDamageTaken(self.leafeon, 50 + 50) # recoil + return

        self.choose_move(self.leafeon, 'jumpkick')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 200 + 167)

    def test_refrigerate(self):
        self.new_battle('vaporeon', 'espeon', p0_ability='refrigerate', p1_ability='refrigerate')
        self.choose_move(self.espeon, 'substitute')
        self.choose_move(self.vaporeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.espeon, (self.espeon.max_hp / 4) + 113)
        self.assertTrue(self.espeon.has_effect(Volatile.SUBSTITUTE))

        self.engine.heal(self.espeon, 200)
        self.espeon.remove_effect(Volatile.SUBSTITUTE)
        self.choose_move(self.espeon, 'return')
        self.choose_move(self.vaporeon, 'psystrike')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 60)
        self.assertDamageTaken(self.espeon, 69)

    def test_regenerator(self):
        self.new_battle(p0_ability='regenerator', p1_ability='regenerator')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('espeon', 1)
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_switch(self.leafeon, self.espeon)
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 10 + self.vaporeon.max_hp / 3)
        self.assertEqual(self.leafeon.hp, 10 + self.leafeon.max_hp / 3)

        self.choose_switch(self.flareon, self.vaporeon)
        self.choose_move(self.espeon, 'roar')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 10 + 2 * (self.vaporeon.max_hp / 3))

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_rockhead(self):
        self.new_battle(p0_ability='rockhead', p1_ability='rockhead')
        self.choose_move(self.leafeon, 'doubleedge')
        self.choose_move(self.vaporeon, 'jumpkick')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 167 + self.vaporeon.max_hp / 2)
        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.leafeon, 'struggle')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_roughskin(self):
        self.new_battle(p0_ability='roughskin', p1_ability='roughskin')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24 + (self.leafeon.max_hp / 8))
        self.assertDamageTaken(self.vaporeon, 142 + 0) # no roughskin damage

        self.leafeon.hp = self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, 'vcreate')
        self.run_turn()

        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    def test_sandrush(self):
        self.new_battle(p0_ability='sandrush')
        self.add_pokemon('jolteon', 1, ability='airlock')
        self.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.choose_move(self.leafeon, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39 + self.leafeon.max_hp / 16)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_switch(self.leafeon, self.jolteon)
        self.run_turn()

        self.choose_move(self.jolteon, 'suckerpunch')
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 73)

    def test_sandstream(self):
        self.new_battle(p0_ability='sandstream', p1_ability='drizzle')
        self.assertEqual(self.battlefield.weather, Weather.SANDSTORM)

        self.new_battle(p0_ability='sandstream', p1_ability='primordialsea')
        self.assertEqual(self.battlefield.weather, Weather.PRIMORDIALSEA)

    def test_sandveil(self):
        with patch('random.randrange', lambda _: 81): # miss at 80%- accuracy
            self.new_battle(p0_ability='sandveil')
            self.choose_move(self.leafeon, 'superfang')
            self.choose_move(self.vaporeon, 'rockslide')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 200)
            self.assertDamageTaken(self.leafeon, 37)

            self.battlefield.set_weather(Weather.SANDSTORM)
            self.choose_move(self.leafeon, 'return')
            self.choose_move(self.vaporeon, 'rockslide')
            self.run_turn()

            self.assertDamageTaken(self.leafeon, (37 * 2) + (self.leafeon.max_hp / 16))
            self.assertDamageTaken(self.vaporeon, 200)

        with patch('random.randrange', lambda _: 99): # miss if possible
            self.choose_move(self.leafeon, 'aerialace')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 200 + 84)

    def test_sapsipper(self):
        self.new_battle(p0_ability='sapsipper', p1_ability='magicbounce')
        self.choose_move(self.leafeon, 'leafstorm')
        self.choose_move(self.vaporeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertBoosts(self.vaporeon, {'atk': 1})
        self.assertDamageTaken(self.leafeon, 32)
        self.assertBoosts(self.leafeon, {'spa': 0})

        self.choose_move(self.vaporeon, 'leechseed')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 2})

    def test_scrappy(self):
        self.new_battle('gengar', 'drifblim', p0_ability='scrappy', p1_ability='scrappy')
        self.add_pokemon('jellicent', 0, ability='soundproof')
        self.choose_move(self.gengar, 'earthquake')
        self.choose_move(self.drifblim, 'brickbreak')
        self.run_turn()

        self.assertDamageTaken(self.drifblim, 0)
        self.assertDamageTaken(self.gengar, 40)

        self.engine.heal(self.gengar, 40)
        self.choose_move(self.gengar, 'substitute')
        self.choose_move(self.drifblim, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.gengar, (self.gengar.max_hp / 4) + 89)

        self.choose_switch(self.gengar, self.jellicent)
        self.choose_move(self.drifblim, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.jellicent, 0)

    def test_scrappy_aurasphere_vs_bulletproof(self):
        self.new_battle(p0_ability='scrappy', p1_ability='bulletproof')
        self.choose_move(self.vaporeon, 'aurasphere')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

    @patch('random.randrange', lambda _: 50)
    def test_serenegrace(self):
        self.new_battle(p0_ability='serenegrace', p1_ability='serenegrace')
        self.choose_move(self.leafeon, 'airslash')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45)
        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.vaporeon, 'crunch')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'def': 0})

    def test_serenegrace_with_triattack(self):
        def roll(stop):
            if roll.first:
                roll.first = False
                return 35
            return 2 # FRZ
        roll.first = True

        with patch('random.randrange', roll):
            self.new_battle(p0_ability='serenegrace')
            self.choose_move(self.vaporeon, 'triattack')
            self.run_turn()

            self.assertStatus(self.leafeon, Status.FRZ)

    def test_shadowtag(self):
        self.new_battle(p0_ability='shadowtag')
        self.add_pokemon('jolteon', 1, ability='shadowtag')
        self.add_pokemon('gengar', 1)
        self.add_pokemon('flareon', 0)
        self.add_pokemon('ditto', 0, ability='imposter')
        self.engine.init_turn()

        self.assertSwitchChoices(self.leafeon, set())
        self.assertSwitchChoices(self.vaporeon, {self.flareon, self.ditto})

        self.choose_move(self.leafeon, 'uturn')
        self.run_turn()
        self.assertActive(self.jolteon)
        self.engine.init_turn()

        self.assertSwitchChoices(self.jolteon, {self.leafeon, self.gengar})
        self.assertSwitchChoices(self.vaporeon, {self.flareon, self.ditto})

        self.choose_switch(self.vaporeon, self.ditto)
        self.run_turn()
        self.engine.init_turn()

        self.assertSwitchChoices(self.jolteon, {self.leafeon, self.gengar})
        self.assertSwitchChoices(self.ditto, {self.flareon, self.vaporeon})

        self.choose_switch(self.jolteon, self.gengar)
        self.run_turn()
        self.engine.init_turn()

        self.assertSwitchChoices(self.gengar, {self.leafeon, self.jolteon})
        self.assertSwitchChoices(self.ditto, {self.flareon, self.vaporeon})

        self.choose_switch(self.gengar, self.leafeon)
        self.run_turn()
        self.engine.init_turn()

        self.assertSwitchChoices(self.leafeon, set())
        self.assertSwitchChoices(self.ditto, {self.flareon, self.vaporeon})

    def test_shedskin(self):
        self.new_battle(p0_ability='shedskin', p1_ability='shedskin')
        with patch('random.randrange', lambda _: 0): # shedskin succeeds; no miss
            self.choose_move(self.leafeon, 'willowisp')
            self.choose_move(self.vaporeon, 'darkvoid')
            self.run_turn()

        self.assertStatus(self.leafeon, None)
        self.assertStatus(self.vaporeon, None)
        self.assertDamageTaken(self.vaporeon, 0)

        with patch('random.randrange', lambda _: 1): # shedskin fails; no miss
            self.choose_move(self.leafeon, 'willowisp')
            self.choose_move(self.vaporeon, 'darkvoid')
            self.run_turn()

        self.assertStatus(self.leafeon, Status.SLP)
        self.assertStatus(self.vaporeon, Status.BRN)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

    @patch('random.randrange', lambda _: 2) # triattack freezes if possible
    def test_sheerforce(self):
        self.new_battle(p0_ability='sheerforce', p1_ability='sheerforce')
        self.choose_move(self.leafeon, 'flamecharge')
        self.choose_move(self.vaporeon, 'triattack')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45)
        self.assertFalse(self.leafeon.boosts)
        self.assertDamageTaken(self.leafeon, 136)
        self.assertStatus(self.leafeon, None)

        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 136 + 88)

    def test_shellarmor(self):
        self.new_battle(p0_ability='shellarmor')
        self.choose_move(self.leafeon, 'stormthrow')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 84)

    @patch('random.randrange', lambda _: 0) # secondary effects activate if possible
    def test_shielddust(self):
        self.new_battle(p0_ability='shielddust', p1_ability='shielddust')
        self.choose_move(self.vaporeon, 'fakeout')
        self.choose_move(self.leafeon, 'flamecharge')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 35)

        self.assertBoosts(self.leafeon, {'spe': 1})

        self.choose_move(self.leafeon, 'icefang')
        self.choose_move(self.vaporeon, 'triattack')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 35 + 45)
        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, None)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_simple(self):
        self.new_battle(p0_ability='simple', p1_ability='simple')
        self.choose_move(self.leafeon, 'partingshot')
        self.choose_move(self.vaporeon, 'leafstorm')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -2, 'spa': -6})

        self.choose_move(self.vaporeon, 'poweruppunch')
        self.choose_move(self.leafeon, 'autotomize')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 0, 'spa': -6})
        self.assertBoosts(self.leafeon, {'spe': 4})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_skilllink(self):
        self.new_battle(p0_ability='skilllink', p1_ability='skilllink')
        self.choose_move(self.leafeon, 'tailslap')
        self.choose_move(self.vaporeon, 'bonemerang')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 36 * 5)
        self.assertDamageTaken(self.leafeon, 12 * 2)

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 36 * 5 + 142)

    def test_slowstart(self):
        self.new_battle(p0_ability='slowstart', p1_ability='slowstart')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 72)
        self.assertDamageTaken(self.leafeon, 88)

        for _ in range(4):
            self.assertTrue(self.leafeon.has_effect(Volatile.SLOWSTART))
            self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.SLOWSTART))

        self.choose_move(self.leafeon, 'uturn')
        self.choose_move(self.vaporeon, 'roar')
        self.run_turn()
        self.assertActive(self.leafeon)

        self.assertDamageTaken(self.vaporeon, 72 + 98)

        self.choose_move(self.vaporeon, 'suckerpunch')
        self.choose_move(self.leafeon, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88 + 39)
        self.assertDamageTaken(self.vaporeon, 72 + 98)

    def test_sniper(self):
        self.new_battle(p0_ability='sniper', p1_ability='angerpoint')
        self.choose_move(self.vaporeon, 'stormthrow')
        self.run_turn()
        self.assertBoosts(self.leafeon, {'atk': 6})

        self.assertDamageTaken(self.leafeon, 67)

        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 67 + 50)

    @patch('random.randrange', lambda _: 81) # miss on 80%- accuracy
    def test_snowcloak(self):
        self.new_battle(p0_ability='snowcloak')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 142)
        self.battlefield.set_weather(Weather.HAIL)
        self.choose_move(self.leafeon, 'return')
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, 142)

    def test_snowwarning(self):
        self.new_battle(p0_ability='snowwarning', p1_ability='drizzle')
        self.assertEqual(self.battlefield.weather, Weather.HAIL)

        self.new_battle(p0_ability='snowwarning', p1_ability='primordialsea')
        self.assertEqual(self.battlefield.weather, Weather.PRIMORDIALSEA)

    def test_solarpower(self):
        self.new_battle(p0_ability='solarpower')
        self.choose_move(self.vaporeon, 'vacuumwave')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 53)

        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.vaporeon, 'vacuumwave')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)
        self.assertDamageTaken(self.leafeon, 53 + 79)

    def test_solidrock(self):
        self.new_battle(p0_ability='solidrock')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 283)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    def test_soundproof(self):
        self.new_battle(p0_ability='soundproof', p1_ability='soundproof')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 4)

        self.choose_move(self.leafeon, 'roar')
        self.choose_move(self.vaporeon, 'perishsong')
        self.run_turn()

        self.assertActive(self.vaporeon)
        self.assertFalse(self.vaporeon.has_effect(Volatile.PERISHSONG))
        self.assertFalse(self.leafeon.has_effect(Volatile.PERISHSONG))

        self.choose_move(self.leafeon, 'bugbuzz')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    def test_speedboost(self):
        self.new_battle(p0_ability='speedboost')
        self.add_pokemon('flareon', 0, ability='speedboost')

        self.run_turn()
        self.assertBoosts(self.vaporeon, {'spe': 1})
        self.run_turn()
        self.assertBoosts(self.vaporeon, {'spe': 2})

        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()

        self.assertBoosts(self.flareon, {'spe': 0})

        self.run_turn()
        self.assertBoosts(self.flareon, {'spe': 1})
        self.run_turn()
        self.assertBoosts(self.flareon, {'spe': 2})

        self.choose_move(self.leafeon, 'whirlwind')
        self.run_turn()
        self.assertActive(self.vaporeon)

        self.assertBoosts(self.vaporeon, {'spe': 0})
        self.run_turn()
        self.assertBoosts(self.vaporeon, {'spe': 1})

        for _ in range(10):
            self.run_turn()

        self.assertBoosts(self.vaporeon, {'spe': 6})

    def test_stancechange(self):
        self.new_battle('vaporeon', 'aegislash', p0_ability='shielddust', p1_ability='stancechange')
        self.assertEqual(self.aegislash.name, 'aegislash')
        self.choose_move(self.vaporeon, 'surf')
        self.choose_move(self.aegislash, 'shadowball')
        self.run_turn()

        self.assertDamageTaken(self.aegislash, 88)
        self.assertDamageTaken(self.vaporeon, 151)
        self.assertEqual(self.aegislash.name, 'aegislashblade')
        self.assertDictEqual(self.aegislash.stats, {'max_hp': 261, 'atk': 336, 'def': 136,
                                                    'spa': 336, 'spd': 136, 'spe': 156})

        self.choose_move(self.vaporeon, 'flareblitz')
        self.choose_move(self.aegislash, 'kingsshield')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -2})
        self.assertDictEqual(self.aegislash.stats, {'max_hp': 261, 'atk': 136, 'def': 336,
                                                    'spa': 136, 'spd': 336, 'spe': 156})

        self.choose_move(self.aegislash, 'shadowsneak')
        self.choose_move(self.vaporeon, 'surf')
        self.engine.heal(self.aegislash, 300)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 151 + 111)
        self.assertDamageTaken(self.aegislash, 216)

    def test_imposter_vs_stancechange(self):
        self.new_battle('aegislash', 'ditto', p0_ability='stancechange', p1_ability='imposter',
                        p0_moves=('ironhead', 'shadowsneak', 'kingsshield'))
        self.add_pokemon('leafeon', 1, ability='noguard')
        self.choose_move(self.ditto, 'shadowsneak')
        self.choose_move(self.aegislash, 'ironhead')
        self.run_turn()

        self.assertDamageTaken(self.aegislash, 44)
        self.assertDamageTaken(self.ditto, 51)

        self.choose_switch(self.ditto, self.leafeon)
        self.choose_move(self.aegislash, movedex['circlethrow'])
        self.run_turn()

        self.assertDictContainsSubset({'atk': 336, 'def': 136}, self.ditto.stats)

        self.choose_move(self.ditto, 'kingsshield')
        self.choose_move(self.aegislash, 'ironhead')
        self.run_turn()
        self.assertBoosts(self.aegislash, {'atk': -2})

        self.assertDictContainsSubset({'atk': 336, 'def': 136}, self.ditto.stats)

    def test_stancechange_reverts_upon_switch_out(self):
        self.new_battle('aegislash', 'leafeon', p0_ability='stancechange')
        self.add_pokemon('vaporeon', 0)
        self.choose_move(self.leafeon, 'aerialace')
        self.choose_move(self.aegislash, 'ironhead')
        self.run_turn()

        self.assertEqual(self.aegislash.name, 'aegislashblade')

        self.choose_switch(self.aegislash, self.vaporeon)
        self.choose_move(self.leafeon, 'roar')
        self.run_turn()

        self.assertEqual(self.aegislash.name, 'aegislash')
        self.assertDictContainsSubset({'atk': 136, 'def': 336}, self.aegislash.stats)

    @patch('random.randrange', lambda _: 0) # no miss, static success
    def test_static(self):
        self.new_battle(p0_ability='static')
        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertStatus(self.vaporeon, None)
        self.assertDamageTaken(self.vaporeon, 142)
        self.assertStatus(self.leafeon, Status.PAR)

    def test_steadfast(self):
        self.new_battle(p0_ability='steadfast')
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, 'fakeout')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertStatus(self.leafeon, None)
        self.assertBoosts(self.vaporeon, {'spe': 1})

    def test_stickyhold(self):
        self.new_battle(p0_item='toxicorb', p0_ability='immunity',
                        p1_ability='stickyhold',
                        p1_item='petayaberry')
        self.add_pokemon('flareon', 0, ability='magician')
        self.choose_move(self.vaporeon, 'trick')
        self.run_turn()

        self.assertItem(self.vaporeon, 'toxicorb')
        self.assertItem(self.leafeon, 'petayaberry')

        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 47)
        self.assertItem(self.leafeon, 'petayaberry')

        self.choose_move(self.vaporeon, 'bugbite')
        self.choose_move(self.leafeon, 'whirlwind')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 47 + 60)
        self.assertItem(self.leafeon, 'petayaberry')

        self.choose_move(self.flareon, 'drainpunch')
        self.run_turn()
        self.assertDamageTaken(self.leafeon, 47 + 60 + 65)

        self.assertItem(self.leafeon, 'petayaberry')

    def test_stickyhold_allows_item_usage(self):
        self.new_battle(p0_item='airballoon', p0_ability='stickyhold',
                        p1_item='lumberry', p1_ability='stickyhold')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.leafeon, None)
        self.assertItem(self.leafeon, None)
        self.assertItem(self.vaporeon, None)

    def test_stormdrain(self):
        self.new_battle(p0_ability='stormdrain', p1_ability='stormdrain')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': 1})
        self.assertStatus(self.leafeon, None)
        self.assertBoosts(self.vaporeon, {'spa': 0})
        self.assertDamageTaken(self.vaporeon, 142)

        self.choose_move(self.leafeon, 'raindance')
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.assertBoosts(self.vaporeon, {'spa': 0})

    def test_strongjaw(self):
        self.new_battle(p0_ability='strongjaw', p1_ability='strongjaw')
        self.choose_move(self.leafeon, 'crunch')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 167)
        self.assertDamageTaken(self.leafeon, 50)

    @patch('random.randrange', lambda _: 0) # no miss
    @patch('random.choice', lambda _: 5) # rockblast hits 5 times
    def test_sturdy(self):
        self.new_battle(p0_ability='sturdy', p1_ability='sturdy')
        self.add_pokemon('flareon', 0, ability='sturdy')
        self.add_pokemon('jolteon', 1, ability='sturdy')
        self.choose_move(self.leafeon, 'powerwhip')
        self.choose_move(self.vaporeon, 'counter')
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 1)
        self.assertStatus(self.leafeon, None)
        self.assertEqual(self.vaporeon.hp, 1)
        self.assertStatus(self.vaporeon, None)

        self.engine.heal(self.vaporeon, 500)
        self.choose_move(self.leafeon, 'powerwhip')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 1)
        self.assertStatus(self.vaporeon, None)

        self.choose_move(self.leafeon, 'destinybond')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

        self.engine.init_turn()
        self.jolteon.apply_boosts(Boosts(spa=1))
        self.flareon.apply_boosts(Boosts(atk=1))
        self.choose_move(self.jolteon, 'hydropump')
        self.choose_move(self.flareon, 'rockblast')
        self.run_turn()

        self.assertEqual(self.flareon.hp, 1)
        self.assertFainted(self.jolteon)

    def test_suctioncups(self):
        self.new_battle(p0_ability='suctioncups', p1_ability='noguard')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 1)
        self.choose_move(self.leafeon, 'dragontail')
        self.choose_move(self.vaporeon, 'circlethrow')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 84)
        self.assertDamageTaken(self.leafeon, 30)
        self.assertActive(self.vaporeon)
        self.assertActive(self.jolteon)
        self.assertFalse(self.leafeon.is_active)

        self.choose_move(self.jolteon, 'roar')
        self.run_turn()

        self.assertActive(self.vaporeon)
        self.assertFalse(self.flareon.is_active)

        self.choose_move(self.vaporeon, 'uturn')
        self.run_turn()

        self.assertDamageTaken(self.jolteon, 64)
        self.assertFalse(self.vaporeon.is_active)
        self.assertActive(self.flareon)

    def test_superluck(self):
        crit = [None]
        def get_critical_hit(crit_ratio):
            crit[0] = crit_ratio
            return False

        self.new_battle(p0_ability='superluck', p1_ability='superluck')
        self.engine.get_critical_hit = get_critical_hit
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertEqual(crit[0], 1)

        self.choose_move(self.vaporeon, 'nightslash')
        self.run_turn()

        self.assertEqual(crit[0], 2)

    def test_swarm(self):
        self.new_battle(p0_ability='swarm', p1_ability='swarm')
        self.choose_move(self.leafeon, 'xscissor')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertDamageTaken(self.vaporeon, 112)

        self.leafeon.hp = 85
        self.vaporeon.hp = 401

        self.choose_move(self.leafeon, 'xscissor')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 167)

        self.choose_move(self.leafeon, 'bugbuzz')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 167 + 80)

    def test_swiftswim(self):
        self.new_battle(p0_ability='swiftswim')
        self.choose_move(self.leafeon, 'suckerpunch')
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112)
        self.assertDamageTaken(self.leafeon, 0)

        self.battlefield.set_weather(Weather.PRIMORDIALSEA)
        self.choose_move(self.leafeon, 'suckerpunch')
        self.choose_move(self.vaporeon, 'suckerpunch')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 39)
        self.assertDamageTaken(self.vaporeon, 112)

    @patch('random.randrange', lambda _: 1) # no miss; no parahax
    def test_synchronize(self):
        self.new_battle(p0_ability='synchronize')
        self.add_pokemon('espeon', 1, ability='synchronize')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'toxicspikes')
        self.run_turn()
        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PAR)
        self.assertStatus(self.leafeon, Status.PAR)

        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()
        self.choose_switch(self.leafeon, self.espeon)
        self.run_turn()

        self.assertStatus(self.espeon, Status.PSN)
        self.assertStatus(self.flareon, None)

        self.choose_switch(self.espeon, self.leafeon)
        self.run_turn()

        self.assertStatus(self.flareon, None)

        self.new_battle(p0_ability='synchronize', p1_ability='synchronize')
        self.engine.set_status(self.vaporeon, Status.PSN, None)
        self.choose_move(self.vaporeon, 'willowisp')
        self.run_turn()

        self.assertStatus(self.leafeon, Status.BRN)
        self.assertStatus(self.vaporeon, Status.PSN)

    def test_synchronize_vs_safeguard(self):
        self.new_battle(p1_ability='synchronize')
        self.choose_move(self.leafeon, 'safeguard')
        self.run_turn()
        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PAR)
        self.assertStatus(self.leafeon, None)

    @patch('random.randrange', lambda _: 0) # icebeam freezes
    def test_synchronize_doesnt_activate_for_slp_or_frz(self):
        self.new_battle(p0_ability='synchronize')
        self.choose_move(self.leafeon, 'icebeam')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.FRZ)
        self.assertStatus(self.leafeon, None)

        self.vaporeon.cure_status()
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.SLP)
        self.assertStatus(self.leafeon, None)

        self.vaporeon.cure_status()
        self.vaporeon.hp -= 1
        self.choose_move(self.vaporeon, 'rest')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.SLP)
        self.assertStatus(self.leafeon, None)

    def test_synchronize_doesnt_activate_for_status_orb(self):
        self.new_battle(p0_item='toxicorb', p0_ability='synchronize')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.TOX)

        self.assertStatus(self.leafeon, None)

    @patch('random.randrange', lambda _: 49) # miss at 49%- accuracy
    def test_tangledfeet(self):
        self.new_battle(p0_ability='tangledfeet')
        self.choose_move(self.leafeon, 'airslash')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45)

        self.choose_move(self.leafeon, 'confuseray')
        self.run_turn()

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45 + 142)

        self.choose_move(self.leafeon, 'airslash')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 45 + 142)

    @patch('random.choice', lambda _: 2) # multihit hits 2 times
    def test_technician(self):
        self.new_battle(p0_ability='technician', p1_ability='technician')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'quickattack')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 30)
        self.assertDamageTaken(self.vaporeon, 142)

        self.new_battle(p0_ability='technician', p1_ability='technician')
        self.vaporeon.hp = 134 + 126
        self.choose_move(self.leafeon, 'lowkick')
        self.choose_move(self.vaporeon, 'waterspout')
        self.run_turn()

        self.assertEqual(self.vaporeon.hp, 134)
        self.assertDamageTaken(self.leafeon, 74)

        self.new_battle(p0_ability='technician', p1_ability='technician')
        self.choose_move(self.leafeon, 'bulletseed')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 2 * 158)

    def test_thickfat(self):
        self.new_battle(p0_ability='thickfat', p1_ability='thickfat')
        self.choose_move(self.leafeon, 'flamecharge')
        self.choose_move(self.vaporeon, 'hiddenpowerice')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 80)
        self.assertDamageTaken(self.vaporeon, 18)

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 18 + 142)

    def test_tintedlens(self):
        self.new_battle(p0_ability='tintedlens', p1_ability='tintedlens')
        self.choose_move(self.leafeon, 'eruption')
        self.choose_move(self.vaporeon, 'hiddenpowerice')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 88)
        self.assertDamageTaken(self.leafeon, 158)

    def test_torrent(self):
        self.new_battle(p0_ability='torrent', p1_ability='torrent')
        self.vaporeon.hp = 100
        self.choose_move(self.leafeon, 'surf')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertEqual(self.vaporeon.hp, 100 - 27)

        self.engine.heal(self.leafeon, 400)
        self.vaporeon.hp = 50

        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 132)

        self.choose_move(self.vaporeon, 'waterfall')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 132 + 43)

    def test_toughclaws(self):
        self.new_battle(p0_ability='toughclaws', p1_ability='toughclaws')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)
        self.assertDamageTaken(self.vaporeon, 185)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_toxicboost(self):
        self.new_battle(p0_ability='toxicboost', p1_ability='toxicboost')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'toxic')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 + 212)

        self.engine.set_status(self.vaporeon, Status.PSN, None)
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88 + (6 * (self.leafeon.max_hp / 16)))

    def test_trace(self):
        self.new_battle(p0_ability='trace', p1_ability='adaptability')
        self.engine.init_turn()

        self.assertAbility(self.vaporeon, 'adaptability')

        self.new_battle(p0_ability='trace', p1_ability='illusion')
        self.engine.init_turn()

        self.assertAbility(self.vaporeon, 'trace')

    def test_trace_untraceable_then_switch(self):
        self.new_battle(p0_ability='trace', p1_ability='flowergift')
        self.add_pokemon('espeon', 1, ability='hugepower')

        self.choose_switch(self.leafeon, self.espeon)
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertAbility(self.vaporeon, 'hugepower')
        self.assertDamageTaken(self.espeon, 184)

    def test_trace_untraceable_then_force_switch(self):
        self.new_battle(p0_ability='trace', p1_ability='flowergift')
        self.add_pokemon('espeon', 1, ability='hugepower')

        self.choose_move(self.vaporeon, 'roar')
        self.run_turn()

        self.assertAbility(self.vaporeon, 'hugepower')

    def test_trace_untraceable_then_untraceable_then_traceable(self):
        self.new_battle(p0_ability='trace', p1_ability='flowergift')
        self.add_pokemon('jolteon', 1, ability='illusion')
        self.add_pokemon('espeon', 1, ability='hugepower')

        self.choose_move(self.leafeon, 'voltswitch')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertAbility(self.vaporeon, 'trace')
        self.assertDamageTaken(self.jolteon, 93)

        self.choose_switch(self.jolteon, self.espeon)
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertAbility(self.vaporeon, 'hugepower')
        self.assertDamageTaken(self.espeon, 184)

    def test_trace_untraceable_then_switch_into_spikes_ko(self):
        self.new_battle(p0_ability='trace', p1_ability='flowergift')
        self.add_pokemon('jolteon', 1, ability='aftermath')
        self.add_pokemon('espeon', 1, ability='aerilate')
        self.leafeon.hp = self.jolteon.hp = 1
        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()
        self.choose_switch(self.leafeon, self.jolteon)
        self.choose_move(self.vaporeon, 'pursuit')
        self.run_turn()
        self.assertFainted(self.leafeon)
        self.engine.init_turn()
        self.assertFainted(self.jolteon)
        self.assertActive(self.espeon)

        self.assertAbility(self.vaporeon, 'aftermath')

    def test_trace_substitute(self):
        self.new_battle(p1_ability='airlock')
        self.add_pokemon('flareon', 0, ability='trace')
        self.choose_move(self.leafeon, 'substitute')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()
        self.assertActive(self.flareon)

        self.assertAbility(self.flareon, 'airlock')

    def test_trace_again_after_switch_out(self):
        self.new_battle(p0_ability='trace', p1_ability='analytic')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 1, ability='angerpoint')
        self.engine.init_turn()
        self.assertAbility(self.vaporeon, 'analytic')
        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_switch(self.leafeon, self.jolteon)
        self.run_turn()
        self.choose_switch(self.flareon, self.vaporeon)
        self.run_turn()

        self.assertAbility(self.vaporeon, 'angerpoint')

    def test_trace_then_suppress_with_moldbreaker(self):
        self.new_battle(p0_ability='trace', p1_ability='motordrive')
        self.add_pokemon('jolteon', 1, ability='moldbreaker')
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()
        self.choose_move(self.jolteon, 'fusionbolt')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 272)
        self.assertEqual(self.vaporeon.base_ability.name, 'trace')
        self.assertAbility(self.vaporeon, 'motordrive')

    def test_tracing_levitate_doesnt_block_hazards(self):
        self.new_battle(p1_ability='levitate')
        self.add_pokemon('flareon', 0, ability='trace')
        self.choose_move(self.leafeon, 'spikes')
        self.run_turn()
        self.choose_move(self.leafeon, 'toxicspikes')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()
        self.assertActive(self.flareon)

        self.assertStatus(self.flareon, Status.PSN)
        self.assertDamageTaken(self.flareon, 2 * (self.flareon.max_hp / 8)) # spikes + psn

    def test_tracing_levitate_on_between_turn_switch_in_doesnt_block_hazards(self):
        self.new_battle(p1_ability='levitate')
        self.add_pokemon('flareon', 0, ability='trace')
        self.choose_move(self.leafeon, 'spikes')
        self.choose_move(self.vaporeon, 'explosion')
        self.run_turn()
        self.engine.init_turn()

        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 8)

    def test_trace_ability_with_on_update(self):
        self.new_battle(p0_ability='trace', p1_ability='noguard')
        self.add_pokemon('flareon', 0)
        self.add_pokemon('jolteon', 1, ability='immunity')
        self.choose_move(self.leafeon, 'toxic')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_switch(self.leafeon, self.jolteon)
        self.assertEqual(self.vaporeon.status, Status.TOX)
        self.run_turn()
        self.choose_switch(self.flareon, self.vaporeon)
        self.run_turn()
        self.assertAbility(self.vaporeon, 'immunity')

        self.assertStatus(self.vaporeon, None)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16) # 1 turn of toxic

    def test_trace_regenerator(self):
        self.new_battle(p0_ability='trace', p1_ability='regenerator')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'voltswitch')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 - (self.vaporeon.max_hp / 3))

    def test_trace_ability_with_on_start(self):
        self.new_battle(p0_ability='trace', p1_ability='intimidate')
        self.add_pokemon('flareon', 0, ability='trace')
        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': -2})
        self.assertDamageTaken(self.flareon, 72)

    def test_faster_switch_into_tracer_traces_outgoing_opponent(self):
        self.new_battle(p0_ability='aurabreak')
        self.add_pokemon('flareon', 0, ability='baddreams')
        self.add_pokemon('jolteon', 1, ability='trace')
        self.choose_switch(self.leafeon, self.jolteon)
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()

        self.assertAbility(self.jolteon, 'aurabreak')

    @patch('random.randint', lambda *_: 1) # 1 sleep turn
    def test_truant(self):
        self.new_battle(p0_ability='truant')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()
        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': 2, 'def': 2})
        self.assertBoosts(self.vaporeon, {'atk': 1, 'def': 1})

        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': 3, 'def': 3})
        self.assertBoosts(self.vaporeon, {'atk': 2, 'def': 2})

        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': 4, 'def': 4})
        self.assertBoosts(self.vaporeon, {'atk': 2, 'def': 2})

        self.choose_move(self.leafeon, 'bulkup')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()
        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_move(self.leafeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 96)

        self.choose_switch(self.flareon, self.vaporeon)
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()
        self.assertEqual(self.vaporeon.sleep_turns, 1)
        self.choose_move(self.vaporeon, 'explosion')
        self.choose_move(self.leafeon, 'bulkup')
        self.run_turn()
        self.assertEqual(self.vaporeon.sleep_turns, 0)
        self.choose_move(self.vaporeon, 'bulkup')
        self.choose_move(self.leafeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1, 'def': 1})

        self.choose_move(self.vaporeon, 'bulkup')
        self.choose_move(self.leafeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1, 'def': 1})

    @patch('random.randrange', lambda _: 81) # miss at 81%- accuracy
    def test_unaware(self):
        self.new_battle(p0_ability='unaware')
        self.leafeon.apply_boosts(Boosts(spa=5))
        self.vaporeon.apply_boosts(Boosts(atk=1))
        self.choose_move(self.vaporeon, 'return')
        self.choose_move(self.leafeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 54)
        self.assertDamageTaken(self.leafeon, 74)

        self.leafeon.apply_boosts(Boosts(atk=-4))
        self.vaporeon.apply_boosts(Boosts(spa=-1))
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 54 + 142)
        self.assertDamageTaken(self.leafeon, 74 + 59)

        self.engine.heal(self.vaporeon, 400)
        self.vaporeon.apply_boosts(Boosts(spd=-2))
        self.choose_move(self.leafeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 106)

        self.engine.heal(self.vaporeon, 400)
        self.engine.heal(self.leafeon, 400)
        self.leafeon.apply_boosts(Boosts(acc=1, def_=6))
        self.choose_move(self.leafeon, 'stoneedge')
        self.choose_move(self.vaporeon, 'xscissor')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 116)

    def test_unburden_when_use_item(self):
        self.new_battle(p0_ability='unburden', p0_item='sitrusberry')
        self.leafeon.hp = 1
        self.assertFalse(self.vaporeon.has_effect(Volatile.UNBURDEN))
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertTrue(self.vaporeon.has_effect(Volatile.UNBURDEN))

        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'surf')
        self.run_turn()

        self.assertEqual(self.vaporeon.side.index, self.battlefield.win)

    def test_unburden_when_item_stolen(self):
        self.new_battle(p0_ability='unburden', p0_item='heatrock')
        self.leafeon.hp = self.vaporeon.hp = 1
        self.assertFalse(self.vaporeon.has_effect(Volatile.UNBURDEN))
        self.choose_move(self.leafeon, 'trick')
        self.run_turn()

        self.assertItem(self.vaporeon, None)
        self.assertTrue(self.vaporeon.has_effect(Volatile.UNBURDEN))

        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertEqual(self.vaporeon.side.index, self.battlefield.win)

    def test_unburden_with_regained_item_and_switch(self):
        self.new_battle(p0_ability='unburden', p0_item='heatrock',
                        p1_ability='magician', p1_item='sharpbeak')
        self.add_pokemon('flareon', 0)
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.UNBURDEN))
        self.assertItem(self.vaporeon, None)

        self.choose_move(self.leafeon, 'trick')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.UNBURDEN))
        self.assertItem(self.vaporeon, 'sharpbeak')

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.UNBURDEN))
        self.assertItem(self.vaporeon, None)

        self.choose_switch(self.vaporeon, self.flareon)
        self.choose_move(self.leafeon, 'roar')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.UNBURDEN))

    def test_unnerve(self):
        self.new_battle(p0_item='sitrusberry', p1_ability='unnerve')
        self.add_pokemon('jolteon', 1)
        self.choose_move(self.leafeon, 'leafblade')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)
        self.assertItem(self.vaporeon, 'sitrusberry')

        self.choose_switch(self.leafeon, self.jolteon)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378 - self.vaporeon.max_hp / 4)
        self.assertItem(self.vaporeon, None)

    def test_unnerve_vs_bugbite(self):
        self.new_battle(p1_ability='unnerve', p1_item='sitrusberry')
        self.vaporeon.hp = 100
        self.choose_move(self.vaporeon, 'bugbite')
        self.run_turn()

        self.assertItem(self.leafeon, None)
        self.assertEqual(self.vaporeon.hp, 100 + self.vaporeon.max_hp / 4)

    def test_victorystar(self):
        self.new_battle(p0_ability='victorystar')
        with patch('random.randrange', lambda _: 99): # 99%- accuracy misses
            self.choose_move(self.vaporeon, 'highjumpkick')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 2)

        with patch('random.randrange', lambda _: 98): # 99% accuracy hits
            self.choose_move(self.vaporeon, 'highjumpkick')
            self.run_turn()

            self.assertDamageTaken(self.leafeon, 63)

    def test_voltabsorb(self):
        self.new_battle(p0_ability='voltabsorb', p1_ability='voltabsorb')
        self.choose_move(self.leafeon, 'discharge')
        self.choose_move(self.vaporeon, 'hypervoice')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 118)

        self.choose_move(self.leafeon, 'electricterrain')
        self.choose_move(self.vaporeon, 'thunderwave')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 118 - (self.leafeon.max_hp / 4))
        self.assertTrue(self.engine.battlefield.has_effect(PseudoWeather.ELECTRICTERRAIN))

        self.engine.heal(self.leafeon, 400)
        self.choose_move(self.leafeon, 'magnetrise')
        self.choose_move(self.vaporeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

    def test_waterabsorb(self):
        self.new_battle(p0_ability='waterabsorb')
        self.choose_move(self.leafeon, 'raindance')
        self.choose_move(self.vaporeon, 'bellydrum')
        self.run_turn()
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.choose_move(self.leafeon, 'weatherball')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, (self.vaporeon.max_hp / 2 -
                                               self.vaporeon.max_hp / 4))

        self.choose_move(self.leafeon, 'aquajet')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_waterveil(self):
        self.new_battle(p0_ability='waterveil')
        self.choose_move(self.leafeon, 'willowisp')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)

        self.engine.set_status(self.vaporeon, Status.BRN, None)
        self.run_turn()

        self.assertStatus(self.vaporeon, None)

    @patch('random.randrange', lambda _: 0) # no miss, confusion hit
    def test_wonderguard(self):
        self.new_battle('vaporeon', p0_ability='wonderguard')
        self.add_pokemon('shedinja', 0, ability='wonderguard')
        self.choose_move(self.leafeon, 'knockoff')
        self.run_turn()
        self.choose_move(self.leafeon, 'lavaplume')
        self.run_turn()
        self.choose_move(self.leafeon, 'spikes')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertTrue(self.vaporeon.side.has_effect(Hazard.SPIKES))

        self.choose_move(self.leafeon, 'fusionbolt')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 278)

        self.choose_move(self.leafeon, 'darkvoid')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.SLP)
        self.vaporeon.cure_status()
        self.engine.heal(self.vaporeon, 400)

        self.choose_switch(self.vaporeon, self.shedinja)
        self.run_turn()

        self.assertFainted(self.shedinja)

        self.choose_move(self.leafeon, 'confuseray')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 50 + 37) # spikes + confusion damage

    @patch('random.randrange', lambda _: 45) # miss at 45%- accuracy
    def test_wonderskin(self):
        self.new_battle(p0_ability='wonderskin')
        self.choose_move(self.leafeon, 'willowisp')
        self.run_turn()
        self.choose_move(self.leafeon, 'stoneedge')
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertDamageTaken(self.vaporeon, 139)

        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PAR)

        self.choose_move(self.leafeon, 'stealthrock')
        self.run_turn()
        self.choose_move(self.leafeon, 'agility')
        self.run_turn()

        self.assertTrue(self.vaporeon.side.has_effect(Hazard.STEALTHROCK))
        self.assertBoosts(self.leafeon, {'spe': 2})


class TestMoldBreaker(MultiMoveTestCaseWithoutSetup):
    def test_moldbreaker_vs_aromaveil(self):
        self.new_battle(p0_ability='aromaveil', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'taunt')
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.TAUNT))

    def test_moldbreaker_vs_battlearmor(self):
        self.new_battle(p0_ability='battlearmor', p1_ability='moldbreaker')
        self.engine.get_critical_hit = lambda crit: True # crit when possible
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 213)

    def test_moldbreaker_vs_bulletproof(self):
        self.new_battle(p0_ability='bulletproof', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'aurasphere')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 48)

    def test_moldbreaker_vs_clearbody_and_whitesmoke(self):
        for ability in ('clearbody', 'whitesmoke'):
            self.new_battle(p0_ability=ability, p1_ability='moldbreaker')
            self.choose_move(self.leafeon, 'partingshot')
            self.run_turn()

            self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_moldbreaker_vs_contrary(self):
        self.new_battle(p0_ability='contrary', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_moldbreaker_vs_dryskin(self):
        self.new_battle(p0_ability='dryskin', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27)

        self.choose_move(self.leafeon, 'flamecharge')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27 + 35)

    def test_moldbreaker_vs_filter_and_solidrock(self):
        for ability in ('filter', 'solidrock'):
            self.new_battle(p0_ability=ability, p1_ability='moldbreaker')
            self.choose_move(self.leafeon, 'leafblade')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 378)

    def test_moldbreaker_vs_flashfire(self):
        self.new_battle(p0_ability='flashfire', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'hiddenpowerfire')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.FLASHFIRE))
        self.assertDamageTaken(self.vaporeon, 18)

    def test_moldbreaker_vs_furcoat(self):
        self.new_battle(p0_ability='furcoat', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    def test_moldbreaker_vs_hypercutter(self):
        self.new_battle(p0_ability='hypercutter', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_moldbreaker_vs_immunity(self):
        self.new_battle(p0_ability='immunity', p1_ability='moldbreaker')

        with patch.object(self.engine, 'set_status', wraps=self.engine.set_status) as set_status:
            self.choose_move(self.leafeon, 'toxic')
            self.choose_move(self.vaporeon, 'facade')
            self.run_turn()

            set_status.assert_called_with(self.vaporeon, Status.TOX, self.leafeon)
            self.assertStatus(self.vaporeon, None)
            self.assertDamageTaken(self.leafeon, 34)

    def test_moldbreaker_vs_innerfocus(self):
        self.new_battle(p0_ability='innerfocus', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'fakeout')
        self.choose_move(self.vaporeon, 'bulkup')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 0, 'def': 0})

    def test_moldbreaker_vs_insomnia_sweetveil_vitalspirit(self):
        for ability in ('insomnia', 'sweetveil', 'vitalspirit'):
            self.new_battle(p0_ability=ability, p1_ability='moldbreaker')

            with patch.object(self.engine, 'set_status',
                              wraps=self.engine.set_status) as set_status:
                self.choose_move(self.leafeon, 'spore')
                self.choose_move(self.vaporeon, 'return')
                self.run_turn()

                set_status.assert_called_with(self.vaporeon, Status.SLP, self.leafeon)
                self.assertStatus(self.vaporeon, None)
                self.assertDamageTaken(self.leafeon, 50)

    def test_moldbreaker_vs_levitate(self):
        self.new_battle(p0_ability='levitate', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'earthquake')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 139)

    def test_moldbreaker_vs_lightningrod(self):
        self.new_battle(p0_ability='lightningrod', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'thunderbolt')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 108)

    def test_moldbreaker_vs_limber(self):
        self.new_battle(p0_ability='limber', p1_ability='moldbreaker')

        with patch.object(self.engine, 'set_status', wraps=self.engine.set_status) as set_status:
            self.choose_move(self.leafeon, 'thunderwave')
            self.choose_move(self.vaporeon, 'return')
            self.run_turn()

            set_status.assert_called_with(self.vaporeon, Status.PAR, self.leafeon)
            self.assertStatus(self.vaporeon, None)
            self.assertDamageTaken(self.leafeon, 50)

    def test_moldbreaker_vs_magicbounce(self):
        self.new_battle(p0_ability='magicbounce', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -1, 'spa': -1})

    def test_moldbreaker_vs_marvelscale(self):
        self.new_battle(p0_ability='marvelscale', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'thunderwave')
        self.run_turn()
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    def test_moldbreaker_roar_vs_incoming_levitate_with_spikes(self):
        self.new_battle(p0_ability='moldbreaker')
        self.add_pokemon('flareon', 1, ability='levitate')
        self.choose_move(self.vaporeon, 'spikes')
        self.run_turn()
        self.choose_move(self.vaporeon, 'roar')
        self.run_turn()

        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 8)

    def test_moldbreaker_magiccoat(self):
        self.new_battle(p0_ability='clearbody', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'magiccoat')
        self.choose_move(self.vaporeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_moldbreaker_isnt_active_during_opponents_turn(self):
        self.new_battle(p0_ability='insomnia', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'return')
        self.choose_move(self.vaporeon, 'rest')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertStatus(self.vaporeon, None)

    def test_moldbreaker_doesnt_suppress_weather_effects(self):
        self.new_battle(p0_ability='dryskin', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'sunnyday')
        self.choose_move(self.vaporeon, 'splash')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

    def test_moldbreaker_aliases(self):
        for ability in ('teravolt', 'turboblaze'):
            self.new_battle(p0_ability='bulletproof', p1_ability=ability)
            self.choose_move(self.leafeon, 'aurasphere')
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 48)

    def test_moldbreaker_vs_multiscale(self):
        self.new_battle(p0_ability='multiscale', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    def test_moldbreaker_vs_overcoat(self):
        self.new_battle(p0_ability='overcoat', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'spore')
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.SLP)

    def test_moldbreaker_vs_owntempo(self):
        self.new_battle(p0_ability='owntempo', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'confuseray')
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.CONFUSE))

    @patch('random.randrange', lambda _: 80) # miss at 80%- accuracy
    def test_moldbreaker_vs_sandveil(self):
        self.new_battle(p0_ability='sandveil', p1_ability='moldbreaker')
        self.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.leafeon, 'crabhammer')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 69)

    def test_moldbreaker_vs_sapsipper(self):
        self.new_battle(p0_ability='sapsipper', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    def test_moldbreaker_vs_shielddust(self):
        self.new_battle(p0_ability='shielddust', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'nuzzle')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 58)
        self.assertStatus(self.vaporeon, Status.PAR)

    def test_moldbreaker_vs_simple(self):
        self.new_battle(p0_ability='simple', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -1, 'spa': -1})

    @patch('random.randrange', lambda _: 80) # miss at 80%- accuracy
    def test_moldbreaker_vs_snowcloak(self):
        self.new_battle(p0_ability='snowcloak', p1_ability='moldbreaker')
        self.battlefield.set_weather(Weather.HAIL)
        self.choose_move(self.leafeon, 'crabhammer')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 69)

    def test_moldbreaker_vs_soundproof(self):
        self.new_battle(p0_ability='soundproof', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'boomburst')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 83)

    def test_moldbreaker_vs_stickyhold(self):
        self.new_battle(p0_ability='moldbreaker',
                        p1_ability='stickyhold', p1_item='leftovers')
        self.choose_move(self.vaporeon, 'knockoff')
        self.run_turn()

        self.assertItem(self.leafeon, None)

    def test_moldbreaker_vs_stormdrain(self):
        self.new_battle(p0_ability='stormdrain', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27)

    def test_moldbreaker_vs_sturdy(self):
        self.new_battle(p0_ability='sturdy', p1_ability='moldbreaker')
        self.leafeon.apply_boosts(Boosts(atk=1))
        self.choose_move(self.leafeon, 'leafblade')
        self.run_turn()

        self.assertFainted(self.vaporeon)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_moldbreaker_vs_suctioncups(self):
        self.new_battle(p0_ability='suctioncups', p1_ability='moldbreaker')
        self.add_pokemon('flareon', 0, ability='suctioncups')
        self.choose_move(self.leafeon, 'roar')
        self.run_turn()

        self.assertActive(self.flareon)

        self.choose_move(self.leafeon, 'circlethrow')
        self.run_turn()

        self.assertDamageTaken(self.flareon, 84)
        self.assertActive(self.vaporeon)

    @patch('random.randrange', lambda _: 50) # miss at 50%- accuracy
    def test_moldbreaker_vs_tangledfeet(self):
        self.new_battle(p0_ability='tangledfeet', p1_ability='moldbreaker')
        self.vaporeon.confuse()
        self.choose_move(self.leafeon, 'taunt')
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.TAUNT))

    def test_moldbreaker_vs_thickfat(self):
        self.new_battle(p0_ability='thickfat', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'icebeam')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27)

    def test_moldbreaker_vs_unaware(self):
        self.new_battle(p0_ability='unaware', p1_ability='moldbreaker')
        self.leafeon.apply_boosts(Boosts(atk=2))
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 283)

    def test_moldbreaker_vs_voltabsorb(self):
        self.new_battle(p0_ability='voltabsorb', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'thunderbolt')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 108)

    def test_moldbreaker_vs_waterabsorb(self):
        self.new_battle(p0_ability='waterabsorb', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'surf')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_moldbreaker_vs_waterveil(self):
        self.new_battle(p0_ability='waterveil', p1_ability='moldbreaker')

        with patch.object(self.engine, 'set_status', wraps=self.engine.set_status) as set_status:
            self.choose_move(self.leafeon, 'willowisp')
            self.choose_move(self.vaporeon, 'facade')
            self.run_turn()

            set_status.assert_called_with(self.vaporeon, Status.BRN, self.leafeon)
            self.assertStatus(self.vaporeon, None)
            self.assertDamageTaken(self.leafeon, 34)

    def test_moldbreaker_vs_wonderguard(self):
        self.new_battle(p0_ability='wonderguard', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_moldbreaker_vs_wonderskin(self):
        self.new_battle(p0_ability='wonderskin', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, 'partingshot')
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -1, 'spa': -1})
