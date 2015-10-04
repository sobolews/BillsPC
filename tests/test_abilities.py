from mock import patch

from pokedex import statuses
from pokedex.enums import Status, Weather, Volatile, Hazard, ABILITY
from pokedex.moves import movedex
from pokedex.stats import Boosts
from tests.multi_move_test_case import MultiMoveTestCase

class TestAbilities(MultiMoveTestCase):
    """
    Note: overrides MultiMoveTestCase's default setUp, so self.reset_leads must be called in
    each test.
    """
    def __init__(self, *args, **kwargs):
        self._names = []
        self.engine = None
        super(TestAbilities, self).__init__(*args, **kwargs)

    def setUp(self):
        pass

    def test_adaptability(self):
        self.reset_leads('vaporeon', 'blastoise', p0_ability='adaptability')
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.blastoise, 80)

        self.choose_move(self.blastoise, movedex['surf'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.blastoise, 80 + 62)
        self.assertDamageTaken(self.vaporeon, 52)

    def test_aftermath(self):
        self.reset_leads(p0_ability='aftermath')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertIsNone(self.vaporeon.status)
        self.assertIsNone(self.leafeon.status)

        self.vaporeon.hp = 1
        self.leafeon.hp = 1
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.FNT)
        self.assertStatus(self.leafeon, Status.FNT)
        self.assertEqual(self.battlefield.win, self.vaporeon.side.index)

    def test_aftermath_doesnt_activate_on_non_contact_move_damage(self):
        self.reset_leads(p0_ability='aftermath')
        self.vaporeon.hp = 1
        self.choose_move(self.leafeon, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.reset_leads(p0_ability='aftermath')
        self.vaporeon.hp = 1
        self.engine.set_status(self.vaporeon, Status.PSN)
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.FNT)

        self.assertDamageTaken(self.leafeon, 0)

    def test_aerilate(self):
        self.reset_leads(p0_ability='aerilate')
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 128)

        self.choose_move(self.vaporeon, movedex['aerialace'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 128 + 60)

        self.reset_leads('tornadus', 'leafeon', p0_ability='aerilate')
        self.choose_move(self.tornadus, movedex['bodyslam'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 254)

    def test_airlock(self):
        self.reset_leads()
        self.add_pokemon('rayquaza', 0, ability='airlock')
        self.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.vaporeon, movedex['batonpass'])
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
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.run_turn()
        self.assertTrue(self.battlefield.has_effect(Weather.SUNNYDAY))
        self.choose_move(self.leafeon, movedex['hiddenpowerfire'])
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 19)

    def test_weather_starts_during_airlock_and_ends(self):
        self.reset_leads(p0_ability='airlock')
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, movedex['raindance'])

        for _ in range(3):
            self.run_turn()
            self.assertIsNone(self.battlefield.weather)

        self.choose_switch(self.vaporeon, self.umbreon)
        self.run_turn()
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.run_turn()
        self.assertIsNone(self.battlefield.weather)

    def test_weather_ends_during_airlock(self):
        self.reset_leads()
        self.add_pokemon('espeon', 0, ability='airlock')
        self.choose_move(self.vaporeon, movedex['sunnyday'])
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
        self.reset_leads(p1_ability='airlock')
        self.add_pokemon('umbreon', 1)
        self.battlefield.set_weather(Weather.HAIL)

        self.choose_move(self.vaporeon, movedex['blizzard'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_switch(self.leafeon, self.umbreon)
        self.choose_move(self.vaporeon, movedex['blizzard'])
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 81 + 20) # blizzard damage plus hail

    def test_analytic(self):
        self.reset_leads(p0_ability='analytic',
                         p1_ability='analytic')
        self.add_pokemon('umbreon', 0)
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertDamageTaken(self.leafeon, 64)

        self.engine.apply_boosts(self.vaporeon, Boosts(spe=1))
        self.engine.heal(self.vaporeon, 200)
        self.engine.heal(self.leafeon, 200)
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 185)
        self.assertDamageTaken(self.leafeon, 50)

        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 113)

    def test_angerpoint(self):
        self.reset_leads(p0_ability='angerpoint')
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertEqual(0, self.vaporeon.boosts['atk'])

        self.choose_move(self.leafeon, movedex['stormthrow'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertEqual(6, self.vaporeon.boosts['atk'])
        self.assertDamageTaken(self.leafeon, 194)

    def test_arenatrap(self):
        self.reset_leads(p0_ability='arenatrap')
        self.add_pokemon('flareon', 1, ability='arenatrap')
        self.add_pokemon('jolteon', 1)
        self.add_pokemon('umbreon', 0)
        self.engine.init_turn()

        self.assertSwitchChoices(self.leafeon, set())
        self.assertSwitchChoices(self.vaporeon, {self.umbreon})

        self.choose_move(self.leafeon, movedex['batonpass'])
        self.run_turn()

        self.engine.init_turn()

        self.assertSwitchChoices(self.vaporeon, set())
        self.assertSwitchChoices(self.flareon, set())

    def test_arenatrap_doesnt_trap_flying(self):
        self.reset_leads('vaporeon', 'pidgeot', p0_ability='arenatrap')
        self.add_pokemon('sylveon', 1, ability='levitate')
        self.engine.init_turn()

        self.assertSwitchChoices(self.pidgeot, {self.sylveon})

        self.choose_move(self.pidgeot, movedex['uturn'])
        self.run_turn()
        self.engine.init_turn()

        self.assertSwitchChoices(self.sylveon, {self.pidgeot})

    def test_aromaveil(self):
        self.reset_leads(p0_ability='aromaveil')
        self.choose_move(self.leafeon, movedex['taunt'])
        self.choose_move(self.vaporeon, movedex['disable'])
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.TAUNT))
        self.assertTrue(self.leafeon.has_effect(Volatile.DISABLE))

        self.choose_move(self.leafeon, movedex['encore'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

        self.choose_move(self.leafeon, movedex['disable'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50 + 50)

    @patch('random.randrange', lambda _: 99) # moonblast: no spa drop
    def test_aurabreak(self):
        self.reset_leads('xerneas', 'zygarde', p0_ability='fairyaura', p1_ability='aurabreak')
        self.choose_move(self.xerneas, movedex['moonblast'])
        self.choose_move(self.zygarde, movedex['darkpulse'])
        self.run_turn()

        self.assertDamageTaken(self.zygarde, 240)
        self.assertDamageTaken(self.xerneas, 29)

    @patch('random.randint', lambda *_: 1)
    def test_baddreams(self):
        self.reset_leads(p1_ability='baddreams')
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

        self.choose_move(self.vaporeon, movedex['return'])
        self.choose_move(self.leafeon, movedex['spore'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)
        self.assertDamageTaken(self.leafeon, 50)

    def test_battlearmor(self):
        self.reset_leads(p0_ability='battlearmor')
        self.choose_move(self.leafeon, movedex['stormthrow'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 84)

    def test_blaze(self):
        self.reset_leads('flareon', 'leafeon', p0_ability='blaze')
        self.engine.apply_boosts(self.leafeon, Boosts(atk=2))
        self.choose_move(self.leafeon, movedex['aquajet'])
        self.choose_move(self.flareon, movedex['flamewheel'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 230)

    def test_bulletproof(self):
        self.reset_leads(p0_ability='bulletproof')
        self.choose_move(self.vaporeon, movedex['shadowball'])
        self.choose_move(self.leafeon, movedex['sludgebomb'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 105)

        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    def test_chlorophyll(self):
        self.reset_leads(p0_ability='chlorophyll')
        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, movedex['return'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertStatus(self.vaporeon, None)

    def test_chlorophyll_blocked_in_airlock(self):
        self.reset_leads(p0_ability='chlorophyll', p1_ability='airlock')
        self.battlefield.set_weather(Weather.SUNNYDAY)
        self.vaporeon.hp = self.leafeon.hp = 1
        self.choose_move(self.vaporeon, movedex['return'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertStatus(self.leafeon, None)

    def test_clearbody(self):
        self.reset_leads(p0_ability='clearbody')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.choose_move(self.vaporeon, movedex['superpower'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -1, 'spa': 0, 'def': -1})

        self.engine.apply_boosts(self.vaporeon, Boosts(spe=-3), self_imposed=False)
        self.assertEqual(self.vaporeon.boosts['spe'], 0)
        self.engine.apply_boosts(self.vaporeon, Boosts(spe=-3), self_imposed=True)
        self.assertEqual(self.vaporeon.boosts['spe'], -3)

    def test_competitive(self):
        self.reset_leads(p0_ability='competitive')
        self.add_pokemon('umbreon', 0, ability='competitive')
        self.choose_move(self.leafeon, movedex['defog'])
        self.choose_move(self.vaporeon, movedex['closecombat'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': 2, 'evn': -1, 'def': -1, 'spd': -1})

        self.choose_move(self.leafeon, movedex['stickyweb'])
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, movedex['memento'])
        self.run_turn()

        self.assertBoosts(self.umbreon, {'spa': 4, 'atk': -2, 'spe': -1})

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_compoundeyes(self):
        self.reset_leads(p0_ability='compoundeyes')
        self.choose_move(self.vaporeon, movedex['stoneedge'])
        self.choose_move(self.leafeon, movedex['stoneedge'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertDamageTaken(self.leafeon, 49)

    def test_contrary(self):
        self.reset_leads(p0_ability='contrary')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.choose_move(self.vaporeon, movedex['superpower'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 2, 'spa': 1, 'def': 1})
        self.assertDamageTaken(self.leafeon, 86)

        self.choose_move(self.vaporeon, movedex['agility'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spe': -2})

    @patch('random.randrange', lambda _: 2) # cursedbody success
    def test_cursedbody(self):
        self.reset_leads(p0_ability='cursedbody', p1_moves=[movedex['return'], movedex['protect'],
                                                            movedex['foulplay'], movedex['toxic']])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertListEqual(self.engine.get_move_choices(self.leafeon),
                             [movedex['protect'], movedex['foulplay'], movedex['toxic']])

        for _ in range(4):
            self.assertTrue(self.leafeon.has_effect(Volatile.DISABLE))
            self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.DISABLE))

    @patch('random.randrange', lambda _: 1) # cutecharm success and infatuate fail
    def test_cutecharm(self):
        self.reset_leads(p0_ability='cutecharm', p0_gender='M', p1_gender='F')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertTrue(self.leafeon.has_effect(Volatile.ATTRACT))
        self.assertDamageTaken(self.vaporeon, 142)

        self.choose_move(self.leafeon, movedex['recover'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

        self.reset_leads(p0_ability='cutecharm', p0_gender=None, p1_gender='F')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ATTRACT))

        self.reset_leads(p0_ability='cutecharm', p1_ability='oblivious', p0_gender='F', p1_gender='M')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ATTRACT))

    @patch('random.randrange', lambda _: 99) # no flinch
    def test_darkaura(self):
        self.reset_leads('yveltal', 'leafeon', p0_ability='darkaura')
        self.choose_move(self.yveltal, movedex['darkpulse'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.yveltal, 99)
        self.assertDamageTaken(self.leafeon, 241)

        self.choose_move(self.leafeon, movedex['crunch'])
        self.run_turn()
        self.assertDamageTaken(self.yveltal, 99 + 51)

    def test_defeatist(self):
        self.reset_leads('archeops', 'leafeon', p0_ability='defeatist')
        self.choose_move(self.archeops, movedex['pluck'])
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 164)
        self.assertDamageTaken(self.archeops, 177)

        self.choose_move(self.archeops, movedex['pluck'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 164 + 84)

    def test_defiant(self):
        self.reset_leads(p0_ability='defiant')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 3, 'spa': -1})
        self.assertDamageTaken(self.leafeon, 122)

    def test_deltastream(self):
        self.reset_leads()
        self.add_pokemon('umbreon', 0, ability='deltastream')
        self.add_pokemon('jolteon', 1, ability='deltastream')
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.DELTASTREAM)

        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()

        self.assertIsNone(self.battlefield.weather)

        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.run_turn()
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.DELTASTREAM)

        self.choose_switch(self.leafeon, self.jolteon)
        self.run_turn()
        self.choose_switch(self.umbreon, self.vaporeon)
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.DELTASTREAM)

        self.choose_switch(self.jolteon, self.leafeon)
        self.choose_move(self.vaporeon, movedex['raindance'])
        self.run_turn()

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)

    def test_desolateland(self):
        self.reset_leads()
        self.add_pokemon('umbreon', 0, ability='desolateland')
        self.choose_switch(self.vaporeon, self.umbreon)
        self.choose_move(self.leafeon, movedex['waterfall'])
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 0)
        self.assertEqual(self.battlefield.weather, Weather.DESOLATELAND)

    def test_download(self):
        self.reset_leads(p0_ability='download', p1_ability='download')
        self.add_pokemon('umbreon', 0, ability='download')
        self.assertBoosts(self.vaporeon, {'atk': 0, 'spa': 1})
        self.assertBoosts(self.leafeon, {'atk': 1, 'spa': 0})
        self.choose_move(self.vaporeon, movedex['voltswitch'])
        self.run_turn()

        self.assertBoosts(self.umbreon, {'atk': 0, 'spa': 1})

    def test_drizzle(self):
        self.reset_leads(p0_ability='drizzle')
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 132)

        self.reset_leads(p0_ability='drizzle', p1_ability='desolateland')
        self.assertEqual(self.battlefield.weather, Weather.DESOLATELAND)

    def test_drought(self):
        self.reset_leads(p0_ability='drought')
        self.assertEqual(self.battlefield.weather, Weather.SUNNYDAY)

    @patch('random.randrange', lambda _: 99) # no secondary effects
    def test_dryskin(self):
        self.reset_leads(p0_ability='dryskin')
        self.choose_move(self.leafeon, movedex['scald'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['raindance'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 - 50)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, movedex['flareblitz'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 52 - 50)

        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 52 - 50 + 50)

    @patch('random.randint', lambda *_: 3)
    def test_earlybird(self):
        self.reset_leads(p0_ability='earlybird')
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()

        self.assertEqual(self.vaporeon.get_effect(Status.SLP).turns_left, 1)
        self.assertEqual(self.vaporeon.sleep_turns, 1)

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

    @patch('random.randint', lambda *_: 1)
    def test_earlybird_immediate_wake_up(self):
        self.reset_leads(p0_ability='earlybird')
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

    @patch('random.randrange', lambda _: 25) # poison
    def test_effectspore(self):
        self.reset_leads('vaporeon', 'flareon', p0_ability='effectspore')
        self.choose_move(self.flareon, movedex['return'])
        self.run_turn()

        self.assertStatus(self.flareon, Status.PSN)
        self.flareon.cure_status()

        self.choose_move(self.flareon, movedex['earthquake'])
        self.run_turn()

        self.assertStatus(self.flareon, None)

    @patch('random.randrange', lambda _: 25) # poison
    def test_effectspore_vs_grass_type(self):
        self.reset_leads(p0_ability='effectspore')
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertStatus(self.leafeon, None)

    def test_filter(self):
        self.reset_leads(p0_ability='filter')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 283)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

        self.engine.heal(self.vaporeon, 400)
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

    @patch('random.randrange', lambda _: 2)
    def test_flamebody(self):
        self.reset_leads(p0_ability='flamebody')
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertStatus(self.leafeon, Status.BRN)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 8)

    def test_flashfire(self):
        self.reset_leads('vaporeon', 'espeon', p0_ability='flashfire')
        self.choose_move(self.espeon, movedex['sacredfire'])
        self.choose_move(self.vaporeon, movedex['hiddenpowerfire'])
        self.run_turn()

        self.assertDamageTaken(self.espeon, 87)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertStatus(self.vaporeon, None)
        self.assertTrue(self.vaporeon.has_effect(Volatile.FLASHFIRE))

        self.choose_move(self.espeon, movedex['willowisp'])
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.espeon, 87 + 130)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_flowergift(self):
        self.reset_leads('cherrim', 'leafeon', p0_ability='flowergift')
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.choose_move(self.cherrim, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 69)

        self.choose_move(self.leafeon, movedex['hypervoice'])
        self.run_turn()

        self.assertDamageTaken(self.cherrim, 42)

    def test_existence_of_noneffect_abilities(self):
        self.reset_leads(p0_ability='flowerveil')
        self.reset_leads(p0_ability='frisk')
        self.reset_leads(p0_ability='illusion')

    def test_furcoat(self):
        self.reset_leads(p0_ability='furcoat')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192)

        self.choose_move(self.leafeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 192 + 27)

    def test_galewings(self):
        self.reset_leads(p0_ability='galewings')
        self.add_pokemon('jolteon', 1)
        self.vaporeon.hp = self.leafeon.hp = self.jolteon.hp = 1
        self.choose_move(self.vaporeon, movedex['hiddenpowerflying'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertStatus(self.vaporeon, None)

        self.choose_move(self.vaporeon, movedex['surf'])
        self.choose_move(self.jolteon, movedex['thunderbolt'])
        self.run_turn()

        self.assertFainted(self.vaporeon)
        self.assertStatus(self.jolteon, None)

    @patch('random.randrange', lambda _: 1) # no parahax
    def test_guts(self):
        self.reset_leads(p0_ability='guts', p1_ability='guts')
        self.engine.set_status(self.vaporeon, Status.BRN)
        self.choose_move(self.vaporeon, movedex['facade'])
        self.choose_move(self.leafeon, movedex['xscissor'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 112 + 50)
        self.assertDamageTaken(self.leafeon, 100)

    def test_hugepower(self):
        self.reset_leads(p0_ability='hugepower', p1_ability='hugepower')
        self.choose_move(self.leafeon, movedex['hiddenpowergrass'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 108)
        self.assertDamageTaken(self.leafeon, 98)

    def test_hustle(self):
        with patch('random.randrange', lambda _: 71): # no miss
            self.reset_leads(p0_ability='hustle', p1_ability='hustle')
            self.choose_move(self.vaporeon, movedex['aquatail'])
            self.choose_move(self.leafeon, movedex['hydropump'])
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 32)
            self.assertDamageTaken(self.leafeon, 48)

        with patch('random.randrange', lambda _: 72): # miss at 90% * 80% accuracy
            self.reset_leads(p0_ability='hustle', p1_ability='hustle')
            self.choose_move(self.vaporeon, movedex['aquatail'])
            self.choose_move(self.leafeon, movedex['hydropump'])
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 32)
            self.assertDamageTaken(self.leafeon, 0)

    @patch('random.randrange', lambda _: 1) # no parahax
    def test_hydration(self):
        self.reset_leads(p0_ability='hydration')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.choose_move(self.vaporeon, movedex['raindance'])
        self.engine.set_status(self.leafeon, Status.PSN)
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, Status.PSN)

        for _ in range(4):
            self.run_turn()

        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.run_turn()

        self.assertStatus(self.vaporeon, Status.PAR)

    def test_hypercutter(self):
        self.reset_leads(p0_ability='hypercutter', p1_ability='intimidate')
        self.assertBoosts(self.vaporeon, {'atk': 0})
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 0, 'spa': -1})

    def test_icebody(self):
        self.reset_leads(p0_ability='icebody')
        self.choose_move(self.leafeon, movedex['return'])
        self.battlefield.set_weather(Weather.HAIL)
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142 - 25)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)

    def test_immunity(self):
        self.reset_leads('gligar', 'muk', p0_ability='immunity')
        self.choose_move(self.muk, movedex['toxic'])
        self.run_turn()

        self.assertStatus(self.gligar, None)

        self.choose_move(self.muk, movedex['glare'])
        self.run_turn()

        self.assertStatus(self.gligar, Status.PAR)

    def test_imposter_transformation(self):
        self.reset_leads('ditto', p0_ability='imposter', p1_ability='download',
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
        self.assertEqual(self.ditto._ability.name, 'imposter')
        self.assertEqual(self.ditto.gender, self.leafeon.gender)
        self.assertSequenceEqual(self.ditto.moveset, self.leafeon.moveset)
        self.assertListEqual(self.ditto.types, self.leafeon.types)

        self.assertBoosts(self.leafeon, {'spa': 1})
        self.assertBoosts(self.ditto, {'spa': 2})

    def test_imposter_fail_to_transform_substitute(self):
        self.reset_leads()
        self.add_pokemon('ditto', 0, ability='imposter')
        self.choose_move(self.leafeon, movedex['substitute'])
        self.choose_move(self.vaporeon, movedex['voltswitch'])
        self.run_turn()

        self.assertTrue(self.ditto.is_active)
        self.assertFalse(self.ditto.is_transformed)

    def test_imposter_fail_to_transform_illusion(self):
        self.reset_leads('ditto', p0_ability='imposter', p1_ability='illusion')
        self.assertFalse(self.ditto.is_transformed)

    def test_imposter_moves(self):
        self.reset_leads('ditto', p0_ability='imposter',
                         p1_moves=(movedex['leafblade'], movedex['xscissor'],
                                   movedex['swordsdance'], movedex['return']))

        self.assertEqual(self.ditto.calculate_stat('spe'),
                         self.leafeon.calculate_stat('spe'))
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.ditto, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 76)
        self.assertDamageTaken(self.ditto, 76)
        self.assertEqual(self.ditto.pp[movedex['return']], 4)

    def test_imposter_switch_and_transform_different_foes(self):
        self.reset_leads(p1_moves=(movedex['leafblade'], movedex['uturn'],
                                   movedex['swordsdance'], movedex['return']), p1_ability='moxie')
        self.add_pokemon('ditto', 0, ability='imposter')
        self.add_pokemon('umbreon', 1, moves=(movedex['stickyweb'], movedex['splash'],
                                              movedex['swordsdance'], movedex['foulplay']),
                         ability='flowerveil')

        self.choose_move(self.leafeon, movedex['swordsdance'])
        self.choose_move(self.vaporeon, movedex['uturn'])
        self.run_turn()

        self.assertBoosts(self.ditto, {'atk': 2})
        self.assertDamageTaken(self.leafeon, 68)
        self.assertAbility(self.ditto, 'moxie')

        self.engine.apply_boosts(self.leafeon, Boosts(spe=1))
        self.choose_move(self.leafeon, movedex['uturn'])
        self.choose_move(self.ditto, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 173)
        self.assertDamageTaken(self.ditto, 206)

        self.choose_switch(self.ditto, self.vaporeon)
        self.choose_move(self.umbreon, movedex['stickyweb'])
        self.run_turn()

        self.choose_move(self.vaporeon, movedex['voltswitch'])
        self.choose_move(self.umbreon, movedex['splash'])
        self.run_turn()

        self.assertFalse(self.ditto.boosts)
        self.assertTrue(all(pp == 5 for pp in self.ditto.pp.values()))
        self.assertDamageTaken(self.ditto, 206)
        self.assertEqual(self.ditto.name, 'umbreon')
        self.assertAbility(self.ditto, 'flowerveil')
        self.assertEqual(self.ditto._ability.name, 'imposter')

    def test_imposter_copy_ability(self):
        self.reset_leads('ditto', p0_ability='imposter', p1_ability='magicbounce',
                         p1_moves=(movedex['partingshot'], movedex['xscissor'],
                                   movedex['swordsdance'], movedex['return']))
        self.assertEqual(self.ditto.ability, self.leafeon.ability)
        self.assertEqual(self.ditto._ability.name, 'imposter')

        self.choose_move(self.ditto, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.ditto, {'spa': -1, 'atk': -1})

        self.choose_move(self.leafeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': -1, 'atk': -1})

    def test_infiltrator(self):
        self.reset_leads(p0_ability='infiltrator', p1_ability='infiltrator')
        self.choose_move(self.leafeon, movedex['substitute'])
        self.choose_move(self.vaporeon, movedex['lightscreen'])
        self.run_turn()

        self.engine.heal(self.leafeon, 200)
        self.choose_move(self.leafeon, movedex['surf'])
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88)
        self.assertDamageTaken(self.vaporeon, 27)

        self.choose_move(self.leafeon, movedex['reflect'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 88 + 50)

    def test_innerfocus(self):
        self.reset_leads(p0_ability='innerfocus')
        self.choose_move(self.leafeon, movedex['fakeout'])
        self.choose_move(self.vaporeon, movedex['bulkup'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1, 'def': 1})

    def test_insomnia(self):
        self.reset_leads(p0_ability='insomnia', p1_ability='insomnia')
        self.choose_move(self.leafeon, movedex['spore'])
        self.choose_move(self.vaporeon, movedex['yawn'])
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)
        self.assertFalse(self.leafeon.has_effect(Volatile.YAWN))

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['rest'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertStatus(self.vaporeon, None)

        # hack a sleep onto vaporeon, check that it wakes up anyway
        self.vaporeon.status = Status.SLP
        self.vaporeon._effect_index[Status.SLP] = statuses.Sleep(self.vaporeon, 2)
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)

    # def test_trace_insomnia_cures_sleep(self):
    #     pass # TODO when: implement trace

    # def test_mold_breaker_spore_causes_insomniac_to_sleep_then_immediately_wake(self):
    #     pass # TODO when: implement moldbreaker

    def test_intimidate(self):
        self.reset_leads(p0_ability='intimidate', p1_ability='competitive')
        self.add_pokemon('flareon', 0, ability='intimidate')
        self.add_pokemon('espeon', 1, ability='intimidate')

        self.assertBoosts(self.leafeon, {'atk': -1, 'spa': 2})

        self.choose_move(self.leafeon, movedex['voltswitch'])
        self.choose_move(self.vaporeon, movedex['uturn'])
        self.run_turn()

        self.assertDamageTaken(self.espeon, 86) # vaporeon -1 atk
        self.assertBoosts(self.espeon, {'atk': -1})
        self.assertBoosts(self.flareon, {'atk': 0})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_ironbarbs(self):
        self.reset_leads(p0_ability='ironbarbs', p1_ability='ironbarbs')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24 + (self.leafeon.max_hp / 8))
        self.assertDamageTaken(self.vaporeon, 142 + 0) # no ironbarbs damage

        self.leafeon.hp = self.vaporeon.hp = 10
        self.choose_move(self.vaporeon, movedex['vcreate'])
        self.run_turn()

        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    @patch('random.randrange', lambda _: 99) # no secondary effect
    def test_ironfist(self):
        self.reset_leads(p0_ability='ironfist', p1_ability='ironfist')
        self.choose_move(self.leafeon, movedex['thunderpunch'])
        self.choose_move(self.vaporeon, movedex['shadowpunch'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 35)
        self.assertDamageTaken(self.vaporeon, 252)

    def test_justified(self):
        self.reset_leads(p0_ability='justified', p1_ability='justified')
        self.choose_move(self.leafeon, movedex['knockoff'])
        self.choose_move(self.vaporeon, movedex['surf'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 1})
        self.assertBoosts(self.leafeon, {'atk': 0})

    def test_justified_doesnt_activate_behind_substitute(self):
        self.reset_leads(p1_ability='justified')
        self.choose_move(self.leafeon, movedex['substitute'])
        self.choose_move(self.vaporeon, movedex['knockoff'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['darkpulse'])
        self.run_turn()

        self.assertBoosts(self.leafeon, {'atk': 0})

    @patch('random.randrange', lambda _: 99) # miss if possible
    def test_keeneye(self):
        self.reset_leads(p0_ability='keeneye')
        self.engine.apply_boosts(self.leafeon, Boosts(evn=6))
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

        self.engine.apply_boosts(self.vaporeon, Boosts(acc=-1), self_imposed=False)

        self.assertBoosts(self.vaporeon, {'acc': 0})

        self.engine.apply_boosts(self.vaporeon, Boosts(acc=-1), self_imposed=True)

        self.assertBoosts(self.vaporeon, {'acc': -1})

    # def test_klutz(self):
    #     pass # TODO when: implement items

    def test_levitate(self):
        self.reset_leads(p0_ability='levitate', p1_ability='levitate')
        self.choose_move(self.leafeon, movedex['earthquake'])
        self.choose_move(self.vaporeon, movedex['spikes'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)
        self.assertTrue(self.leafeon.side.has_effect(Hazard.SPIKES))

        self.choose_move(self.leafeon, movedex['bulldoze'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)
        self.assertDamageTaken(self.vaporeon, 0)
        self.assertBoosts(self.vaporeon, {'spe': 0})

    def test_lightningrod(self):
        self.reset_leads(p0_ability='lightningrod', p1_ability='lightningrod')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, movedex['thunderbolt'])
        self.choose_move(self.vaporeon, movedex['thunderwave'])
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': 1})
        self.assertStatus(self.leafeon, None)
        self.assertBoosts(self.vaporeon, {'spa': 1})
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, movedex['voltswitch'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 50)

    def test_lightningrod_magiccoat(self):
        self.reset_leads(p0_ability='lightningrod')
        self.choose_move(self.vaporeon, movedex['magiccoat'])
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)
        self.assertBoosts(self.vaporeon, {'spa': 0})

    @patch('random.randrange', lambda _: 0) # bodyslam paralyzes
    def test_limber(self):
        self.reset_leads(p0_ability='limber', p1_ability='limber')
        self.choose_move(self.vaporeon, movedex['thunderwave'])
        self.choose_move(self.leafeon, movedex['bodyslam'])
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, None)

    # def test_tracing_limber_cures_paralysis(self):
    #     pass # TODO when: implement trace

    @patch('random.randrange', lambda _: 0) # no miss
    def test_liquidooze(self):
        self.reset_leads(p0_ability='liquidooze')
        self.choose_move(self.leafeon, movedex['drainpunch'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 105)
        self.assertDamageTaken(self.leafeon, 53) # ceil(105 * 0.5)

        self.choose_move(self.leafeon, movedex['leechseed'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 105 + 50)
        self.assertDamageTaken(self.leafeon, 53 + 50)

        self.reset_leads(p0_ability='liquidooze')
        self.vaporeon.hp = self.leafeon.hp = 200
        self.choose_move(self.leafeon, movedex['recover'])
        self.choose_move(self.vaporeon, movedex['recover'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)
        self.assertDamageTaken(self.vaporeon, 0)

    def test_liquidooze_behind_substitute(self):
        self.reset_leads(p0_ability='liquidooze')
        self.choose_move(self.leafeon, movedex['suckerpunch'])
        self.choose_move(self.vaporeon, movedex['substitute'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['drainingkiss'])
        self.run_turn()

        self.assertEqual(self.vaporeon.get_effect(Volatile.SUBSTITUTE).hp,
                         100 - 30)
        self.assertDamageTaken(self.leafeon, 23) # ceil(30 * 0.75)

        self.choose_move(self.leafeon, movedex['drainpunch'])
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.SUBSTITUTE))
        self.assertDamageTaken(self.vaporeon, 100) # from substitute only
        self.assertDamageTaken(self.leafeon, 23 + 35) # ceil(70 * 0.5)

    def test_liquidooze_wins_tie(self):
        self.reset_leads(p1_ability='liquidooze')
        self.vaporeon.hp = 10
        self.leafeon.hp = 30
        self.choose_move(self.vaporeon, movedex['drainingkiss'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)
        self.assertEqual(self.battlefield.win, self.leafeon.side.index)

    def test_magicbounce(self):
        self.reset_leads(p0_ability='magicbounce')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.choose_move(self.vaporeon, movedex['partingshot'])
        self.run_turn()

        self.assertStatus(self.vaporeon, None)
        self.assertStatus(self.leafeon, Status.PAR)
        self.assertBoosts(self.leafeon, {'spa': -1, 'atk': -1})

    def test_magicbounce_no_infinite_recursion(self):
        self.reset_leads(p0_ability='magicbounce', p1_ability='magicbounce')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.choose_move(self.vaporeon, movedex['partingshot'])
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)
        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_magicbounce_magiccoat(self):
        self.reset_leads(p1_ability='magicbounce')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.choose_move(self.vaporeon, movedex['magiccoat'])
        self.run_turn()

        self.assertStatus(self.leafeon, Status.PAR)

    def test_magicbounce_encore(self):
        self.reset_leads(p1_ability='magicbounce')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['encore'])
        self.run_turn()

        self.assertFalse(self.leafeon.has_effect(Volatile.ENCORE))
        self.assertFalse(self.vaporeon.has_effect(Volatile.ENCORE))

    @patch('random.randrange', lambda _: 0) # no miss
    def test_magicguard(self):
        self.reset_leads(p0_ability='magicguard', p1_ability='magicguard')
        # TODO: give vaporeon a lifeorb
        self.add_pokemon('umbreon', 0, ability='magicguard')
        self.add_pokemon('jolteon', 1, ability='magicguard')

        self.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.leafeon, movedex['spikes'])
        self.choose_move(self.vaporeon, movedex['toxicspikes'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['willowisp'])
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['leechseed'])
        self.choose_move(self.vaporeon, movedex['infestation'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 54)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.leafeon, movedex['batonpass'])
        self.choose_move(self.vaporeon, movedex['batonpass'])
        self.run_turn()

        self.assertTrue(self.umbreon.has_effect(Volatile.LEECHSEED))
        self.assertTrue(self.umbreon.is_active)
        self.assertTrue(self.jolteon.is_active)
        self.assertDamageTaken(self.umbreon, 0)
        self.assertDamageTaken(self.jolteon, 0)

        self.choose_move(self.umbreon, movedex['return'])
        self.choose_move(self.jolteon, movedex['spikyshield'])
        self.run_turn()

        self.assertDamageTaken(self.umbreon, 0)
        self.assertDamageTaken(self.jolteon, 0)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_magicguard_vs_liquidooze(self): # move does damage but no heal/recoil
        self.reset_leads(p0_ability='liquidooze', p1_ability='magicguard')
        self.leafeon.hp = 100
        self.choose_move(self.leafeon, movedex['leechseed'])
        self.run_turn()

        self.assertEqual(self.leafeon.hp, 100)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

    def test_magicguard_vs_destinybond(self):
        self.reset_leads(p0_ability='magicguard')
        self.vaporeon.hp = self.leafeon.hp = 10
        self.choose_move(self.leafeon, movedex['destinybond'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    @patch('random.randrange', lambda _: 0) # no miss; confusion roll fails
    def test_magicguard_vs_confusiondamage_perishsong_and_bellydrum(self):
        self.reset_leads(p0_ability='magicguard', p1_ability='magicguard')
        self.choose_move(self.leafeon, movedex['perishsong'])
        self.choose_move(self.vaporeon, movedex['bellydrum'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 2)
        self.assertBoosts(self.vaporeon, {'atk': 6})

        self.choose_move(self.leafeon, movedex['confuseray'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 200 + 145) # bellydrum + confusion damage at +6 atk

        self.run_turn()
        self.run_turn()
        self.assertFainted(self.leafeon)
        self.assertFainted(self.vaporeon)

    def test_magicguard_vs_recoil(self):
        self.reset_leads(p0_ability='magicguard')
        self.choose_move(self.vaporeon, movedex['flareblitz'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    def test_magicguard_with_explosion(self):
        self.reset_leads(p0_ability='magicguard')
        self.choose_move(self.vaporeon, movedex['explosion'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 119)
        self.assertFainted(self.vaporeon)

    def test_magicguard_vs_aftermath_and_ironbarbs(self):
        self.reset_leads(p0_ability='magicguard', p1_ability='aftermath')
        self.add_pokemon('jolteon', 1, ability='ironbarbs')
        self.leafeon.hp = 10
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertFainted(self.leafeon)
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 0)

    # def test_magician(self):
    #     pass # TODO when: implement items

    def test_magnetpull(self):
        self.reset_leads('vaporeon', 'steelix', p0_ability='magnetpull')
        self.add_pokemon('aegislash', 1)
        self.add_pokemon('glaceon', 1)
        self.engine.init_turn()

        self.assertSwitchChoices(self.steelix, set())

        self.choose_move(self.steelix, movedex['voltswitch'])
        self.run_turn()
        self.assertTrue(self.aegislash.is_active)

        self.assertSwitchChoices(self.aegislash, {self.steelix, self.glaceon})

        self.choose_switch(self.aegislash, self.glaceon)
        self.run_turn()

        self.assertSwitchChoices(self.glaceon, {self.aegislash, self.steelix})

    @patch('random.randrange', lambda _: 1) # no miss; no parahax
    def test_marvelscale(self):
        self.reset_leads(p0_ability='marvelscale', p1_ability='marvelscale',
                         p0_moves=(movedex['xscissor'], movedex['drillpeck'],
                                   movedex['poisonjab'], movedex['sleeptalk']))
        self.choose_move(self.vaporeon, movedex['drillpeck'])
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertDamageTaken(self.leafeon, 78)

        self.engine.heal(self.vaporeon, 200)
        self.engine.heal(self.leafeon, 200)
        self.engine.apply_boosts(self.vaporeon, Boosts(spe=1))
        self.choose_move(self.vaporeon, movedex['thunderwave'])
        self.choose_move(self.leafeon, movedex['sleeppowder'])
        self.run_turn()

        self.choose_move(self.vaporeon, movedex['sleeptalk'])
        self.choose_move(self.leafeon, movedex['boltstrike'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 242)
        self.assertDamageTaken(self.leafeon, 54)

    @patch('random.randrange', lambda _: 0) # no miss
    def test_megalauncher(self):
        self.reset_leads(p0_ability='megalauncher', p1_ability='megalauncher')
        self.choose_move(self.vaporeon, movedex['dragonpulse'])
        self.choose_move(self.leafeon, movedex['leafstorm'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 230)
        self.assertDamageTaken(self.leafeon, 166)

    def test_moldbreaker_vs_aromaveil(self):
        self.reset_leads(p0_ability='aromaveil', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['taunt'])
        self.run_turn()

        self.assertTrue(self.vaporeon.has_effect(Volatile.TAUNT))

    def test_moldbreaker_vs_battlearmor(self):
        self.reset_leads(p0_ability='battlearmor', p1_ability='moldbreaker')
        self.engine.get_critical_hit = lambda crit: True # crit when possible
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 213)

    def test_moldbreaker_vs_bulletproof(self):
        self.reset_leads(p0_ability='bulletproof', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['aurasphere'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 48)

    def test_moldbreaker_vs_clearbody(self):
        self.reset_leads(p0_ability='clearbody', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_moldbreaker_vs_contrary(self):
        self.reset_leads(p0_ability='contrary', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_moldbreaker_vs_dryskin(self):
        self.reset_leads(p0_ability='dryskin', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['surf'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27)

        self.choose_move(self.leafeon, movedex['flamecharge'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 27 + 35)

    def test_moldbreaker_vs_filter(self):
        self.reset_leads(p0_ability='filter', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    def test_moldbreaker_vs_flashfire(self):
        self.reset_leads(p0_ability='flashfire', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['hiddenpowerfire'])
        self.run_turn()

        self.assertFalse(self.vaporeon.has_effect(Volatile.FLASHFIRE))
        self.assertDamageTaken(self.vaporeon, 18)

    def test_moldbreaker_vs_furcoat(self):
        self.reset_leads(p0_ability='furcoat', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 378)

    def test_moldbreaker_vs_hypercutter(self):
        self.reset_leads(p0_ability='hypercutter', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_moldbreaker_vs_immunity(self):
        self.reset_leads(p0_ability='immunity', p1_ability='moldbreaker')

        with patch.object(self.engine, 'set_status', wraps=self.engine.set_status) as set_status:
            self.choose_move(self.leafeon, movedex['toxic'])
            self.choose_move(self.vaporeon, movedex['facade'])
            self.run_turn()

            set_status.assert_called_with(self.vaporeon, Status.TOX, False)
            self.assertStatus(self.vaporeon, None)
            self.assertDamageTaken(self.leafeon, 34)

    def test_moldbreaker_vs_innerfocus(self):
        self.reset_leads(p0_ability='innerfocus', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['fakeout'])
        self.choose_move(self.vaporeon, movedex['bulkup'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': 0, 'def': 0})

    def test_moldbreaker_vs_insomnia(self):
        self.reset_leads(p0_ability='insomnia', p1_ability='moldbreaker')

        with patch.object(self.engine, 'set_status', wraps=self.engine.set_status) as set_status:
            self.choose_move(self.leafeon, movedex['spore'])
            self.choose_move(self.vaporeon, movedex['return'])
            self.run_turn()

            set_status.assert_called_with(self.vaporeon, Status.SLP, False)
            self.assertStatus(self.vaporeon, None)
            self.assertDamageTaken(self.leafeon, 50)

    def test_moldbreaker_vs_levitate(self):
        self.reset_leads(p0_ability='levitate', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['earthquake'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 139)

    def test_moldbreaker_vs_lightningrod(self):
        self.reset_leads(p0_ability='lightningrod', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['thunderbolt'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 108)

    def test_moldbreaker_vs_limber(self):
        self.reset_leads(p0_ability='limber', p1_ability='moldbreaker')

        with patch.object(self.engine, 'set_status', wraps=self.engine.set_status) as set_status:
            self.choose_move(self.leafeon, movedex['thunderwave'])
            self.choose_move(self.vaporeon, movedex['return'])
            self.run_turn()

            set_status.assert_called_with(self.vaporeon, Status.PAR, False)
            self.assertStatus(self.vaporeon, None)
            self.assertDamageTaken(self.leafeon, 50)

    def test_moldbreaker_vs_magicbounce(self):
        self.reset_leads(p0_ability='magicbounce', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'atk': -1, 'spa': -1})

    def test_moldbreaker_vs_marvelscale(self):
        self.reset_leads(p0_ability='marvelscale', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.run_turn()
        self.choose_move(self.leafeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)

    def test_moldbreaker_roar_vs_incoming_levitate_with_spikes(self):
        self.reset_leads(p0_ability='moldbreaker')
        self.add_pokemon('flareon', 1, ability='levitate')
        self.choose_move(self.vaporeon, movedex['spikes'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['roar'])
        self.run_turn()

        self.assertDamageTaken(self.flareon, self.flareon.max_hp / 8)

    def test_moldbreaker_roar_vs_non_mold_incoming_ability(self):
        pass

    def test_moldbreaker_magiccoat(self):
        self.reset_leads(p0_ability='clearbody', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['magiccoat'])
        self.choose_move(self.vaporeon, movedex['partingshot'])
        self.run_turn()

        self.assertBoosts(self.vaporeon, {'spa': -1, 'atk': -1})

    def test_moldbreaker_isnt_active_during_opponents_turn(self):
        self.reset_leads(p0_ability='insomnia', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['rest'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 142)
        self.assertStatus(self.vaporeon, None)

    def test_moldbreaker_doesnt_suppress_weather_effects(self):
        self.reset_leads(p0_ability='dryskin', p1_ability='moldbreaker')
        self.choose_move(self.leafeon, movedex['sunnyday'])
        self.choose_move(self.vaporeon, movedex['splash'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 8)

    def test_motordrive(self):
        self.reset_leads(p0_ability='motordrive', p1_ability='motordrive')
        self.choose_move(self.leafeon, movedex['thunderwave'])
        self.choose_move(self.vaporeon, movedex['voltswitch'])
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spe': 1})
        self.assertBoosts(self.vaporeon, {'spe': 1})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_moxie(self):
        self.reset_leads(p0_ability='moxie')
        self.add_pokemon('flareon', 1)
        self.add_pokemon('jolteon', 1)
        self.leafeon.hp = self.flareon.hp = self.jolteon.hp = 1
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()
        self.assertFainted(self.leafeon)

        self.assertBoosts(self.vaporeon, {'atk': 1})

        self.choose_move(self.vaporeon, movedex['spikes'])
        self.run_turn()
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.run_turn()
        self.assertFainted(self.flareon)

        self.assertBoosts(self.vaporeon, {'atk': 1})

        self.engine.init_turn()
        self.assertFainted(self.jolteon)

        self.assertBoosts(self.vaporeon, {'atk': 1})

    @patch('random.randrange', lambda _: 0) # no miss; confusion damage
    def test_multiscale(self):
        self.reset_leads(p0_ability='multiscale', p1_ability='multiscale')
        self.choose_move(self.leafeon, movedex['leafblade'])
        self.choose_move(self.vaporeon, movedex['toxic'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 189)
        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)

        self.leafeon.cure_status()
        self.choose_move(self.leafeon, movedex['milkdrink'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 25)

        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 189 + 142)
        self.assertDamageTaken(self.leafeon, 25 + 50)

        self.vaporeon.hp = self.vaporeon.max_hp
        self.choose_move(self.leafeon, movedex['confuseray'])
        self.choose_move(self.vaporeon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 18) # half of normal confusion damage

    # def test_multiscale(self):
    #     pass # TODO when: implement plates

    def test_mummy(self):
        self.reset_leads(p0_ability='mummy', p1_ability='lightningrod')
        self.add_pokemon('sylveon', 0, 'flowerveil')
        self.add_pokemon('jolteon', 1, 'levitate')
        self.choose_move(self.leafeon, movedex['return'])
        self.choose_move(self.vaporeon, movedex['fusionbolt'])
        self.run_turn()

        self.assertAbility(self.leafeon, 'mummy')
        self.assertEqual(self.leafeon._ability.name, 'lightningrod')
        self.assertDamageTaken(self.leafeon, 24)

        self.choose_switch(self.vaporeon, self.sylveon)
        self.run_turn()
        self.choose_move(self.sylveon, movedex['return'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 24 + 50)
        self.assertAbility(self.sylveon, 'mummy')

        self.choose_switch(self.leafeon, self.jolteon)
        self.choose_move(self.sylveon, movedex['whirlwind'])
        self.run_turn()

        self.assertTrue(self.leafeon.is_active)
        self.assertAbility(self.leafeon, 'lightningrod')
        self.assertEqual(self.leafeon._ability.name, 'lightningrod')
        self.choose_move(self.sylveon, movedex['thunderwave'])
        self.run_turn()

        self.assertBoosts(self.leafeon, {'spa': 1})

    @patch('random.randrange', lambda _: 0) # no miss
    def test_naturalcure(self):
        self.reset_leads(p0_ability='naturalcure', p1_ability='naturalcure')
        self.add_pokemon('flareon', 0, ability='naturalcure')
        self.add_pokemon('espeon', 1)
        self.choose_move(self.leafeon, movedex['toxic'])
        self.choose_move(self.vaporeon, movedex['darkvoid'])
        self.run_turn()
        self.assertStatus(self.vaporeon, Status.TOX)
        self.assertStatus(self.leafeon, Status.SLP)
        self.choose_switch(self.leafeon, self.espeon)
        self.choose_switch(self.vaporeon, self.flareon)
        self.run_turn()
        self.flareon.hp -= 1
        self.choose_move(self.flareon, movedex['rest'])
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
            self.engine.apply_boosts(self.vaporeon, Boosts(acc=-6))
            self.engine.apply_boosts(self.leafeon, Boosts(acc=-4))
            self.choose_move(self.leafeon, movedex['focusblast'])
            self.choose_move(self.vaporeon, movedex['phantomforce'])
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 71)

            self.choose_move(self.leafeon, movedex['focusblast'])
            self.choose_move(self.vaporeon, movedex['phantomforce'])
            self.run_turn()

            self.assertDamageTaken(self.vaporeon, 2 * 71)
            self.assertDamageTaken(self.leafeon, 44)

            self.choose_move(self.vaporeon, movedex['spore'])
            self.run_turn()

            self.assertStatus(self.leafeon, None)

        self.reset_leads(p0_ability='noguard')
        test()
        self.reset_leads(p1_ability='noguard')
        test()

    @patch('random.randrange', lambda _: 25) # effectspore causes poison
    def test_overcoat(self):
        self.reset_leads(p0_ability='overcoat', p1_ability='effectspore')
        self.battlefield.set_weather(Weather.HAIL)
        self.run_turn()
        self.battlefield.set_weather(Weather.SANDSTORM)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 2 * (self.leafeon.max_hp / 16))
        self.assertDamageTaken(self.vaporeon, 0)

        self.choose_move(self.vaporeon, movedex['return'])
        self.choose_move(self.leafeon, movedex['spore'])
        self.run_turn()

        self.assertStatus(self.vaporeon, None)

    def test_overgrow(self):
        self.reset_leads(p1_ability='overgrow')
        self.engine.apply_boosts(self.vaporeon, Boosts(spe=2))
        self.choose_move(self.vaporeon, movedex['bugbuzz'])
        self.choose_move(self.leafeon, movedex['energyball'])
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 236)
        self.assertDamageTaken(self.vaporeon, 240)

        self.choose_move(self.leafeon, movedex['ironhead'])
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 240 + 56)
