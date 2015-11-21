from mock import patch

from mining.pokedexmaker import create_pokedex
from pokedex.enums import Status, Weather
from tests.multi_move_test_case import MultiMoveTestCase

pokedex = create_pokedex()


class TestWeather(MultiMoveTestCase):
    def test_sunnyday_damage_modify(self):
        self.engine.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.leafeon, 'surf')
        self.choose_move(self.vaporeon, 'flamewheel')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 13)
        self.assertDamageTaken(self.leafeon, 90)

    @patch('random.randrange', lambda _: 1) # icebeam always freeze, don't thaw
    def test_sunnyday_freeze_immunity(self):
        self.engine.battlefield.set_weather(Weather.SUNNYDAY)
        self.choose_move(self.leafeon, 'icebeam')
        self.choose_move(self.vaporeon, 'return')
        self.run_turn()

        self.assertIsNone(self.vaporeon.status)

    def test_desolateland_stops_water_moves(self):
        self.engine.battlefield.set_weather(Weather.DESOLATELAND)
        self.choose_move(self.vaporeon, 'waterfall')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 0)

        self.choose_move(self.vaporeon, 'waterfall')
        self.choose_move(self.leafeon, 'kingsshield')
        self.run_turn()

        self.assertEqual(self.vaporeon.boosts['atk'], 0)

        self.choose_move(self.vaporeon, 'flamewheel')
        self.run_turn()

        self.assertDamageTaken(self.leafeon, 90)

    def test_raindance_damage_modify(self):
        self.engine.battlefield.set_weather(Weather.RAINDANCE)
        self.choose_move(self.leafeon, 'surf')
        self.choose_move(self.vaporeon, 'flamewheel')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 40)
        self.assertDamageTaken(self.leafeon, 30)

    def test_primordialsea_stops_fire_moves(self):
        self.engine.battlefield.set_weather(Weather.PRIMORDIALSEA)
        self.choose_move(self.leafeon, 'surf')
        self.choose_move(self.vaporeon, 'flamewheel')
        self.run_turn()

        self.assertDamageTaken(self.vaporeon, 40)
        self.assertDamageTaken(self.leafeon, 0)

    def test_hail_damages_both_sides_but_not_ice_types(self):
        self.add_pokemon('glaceon', 0)
        self.engine.battlefield.set_weather(Weather.HAIL)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16)

        self.choose_switch(self.vaporeon, self.glaceon)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16 * 2)
        self.assertDamageTaken(self.glaceon, 0)

    def test_hail_stops_after_5_turns(self):
        self.engine.battlefield.set_weather(Weather.HAIL)
        for _ in range(4):
            self.run_turn()

        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16 * 4)
        self.run_turn()
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16 * 4)

    def test_sandstorm_damages_both_sides_but_not_rock_steel_ground(self):
        self.add_pokemon('empoleon', 0)
        self.add_pokemon('swampert', 1)
        self.add_pokemon('aerodactyl', 0)
        self.add_pokemon('golem', 1)
        self.engine.battlefield.set_weather(Weather.SANDSTORM)
        self.run_turn()

        self.assertDamageTaken(self.leafeon, self.leafeon.max_hp / 16)
        self.assertDamageTaken(self.vaporeon, self.vaporeon.max_hp / 16)

        self.choose_switch(self.vaporeon, self.empoleon)
        self.choose_switch(self.leafeon, self.swampert)
        self.run_turn()

        self.assertDamageTaken(self.empoleon, 0)
        self.assertDamageTaken(self.swampert, 0)

        self.choose_switch(self.empoleon, self.aerodactyl)
        self.choose_switch(self.swampert, self.golem)
        self.run_turn()

        self.assertDamageTaken(self.aerodactyl, 0)
        self.assertDamageTaken(self.golem, 0)

    def test_sandstorm_boosts_spd_rock_types(self):
        self.new_battle('tyranitar', 'leafeon')
        self.engine.battlefield.set_weather(Weather.SANDSTORM)
        self.choose_move(self.leafeon, 'return')
        self.run_turn()

        self.assertDamageTaken(self.tyranitar, 43)

        self.choose_move(self.leafeon, 'hiddenpowerfighting')
        self.run_turn()
        self.assertDamageTaken(self.tyranitar, 43 + 96)

    def test_hail_kos_shedinja(self):
        self.new_battle('shedinja', 'leafeon', p0_ability='wonderguard')
        self.engine.battlefield.set_weather(Weather.HAIL)
        self.run_turn()

        self.assertEqual(self.shedinja.status, Status.FNT)

    def test_sandstorm_kos_shedinja(self):
        self.new_battle('shedinja', 'leafeon', p0_ability='wonderguard')
        self.engine.battlefield.set_weather(Weather.SANDSTORM)
        self.run_turn()

        self.assertEqual(self.shedinja.status, Status.FNT)

    def test_sandstorm_and_hail_ko_order(self):
        for weather in (Weather.SANDSTORM, Weather.HAIL):
            self.new_battle('vaporeon', 'leafeon')
            self.leafeon.hp = self.vaporeon.hp = 1
            self.engine.battlefield.set_weather(weather)
            self.run_turn()

            self.assertEqual(self.vaporeon.side.index, self.battlefield.win)

            self.new_battle('vaporeon', 'leafeon')
            self.leafeon.hp = self.vaporeon.hp = 1
            self.engine.battlefield.set_weather(weather)
            self.choose_move(self.vaporeon, 'autotomize')
            self.run_turn()

            self.assertEqual(self.leafeon.side.index, self.battlefield.win)

    def test_deltastream_suppresses_moves_supereffective_vs_flying(self):
        self.new_battle('rayquaza', 'leafeon')
        self.engine.battlefield.set_weather(Weather.DELTASTREAM)
        self.choose_move(self.leafeon, 'hiddenpowerice')
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 76)

        self.choose_move(self.leafeon, 'dragonpulse')
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 76 + 106)

        self.choose_move(self.leafeon, 'hiddenpowerrock')
        self.run_turn()

        self.assertDamageTaken(self.rayquaza, 76 + 106 + 38)

    def test_changing_normal_weather(self):
        self.choose_move(self.leafeon, 'sunnyday')
        self.choose_move(self.vaporeon, 'raindance')
        self.run_turn()

        self.assertEqual(self.engine.battlefield.weather, Weather.RAINDANCE)

        self.run_turn()
        self.choose_move(self.vaporeon, 'raindance')
        self.run_turn()

        self.assertEqual(self.engine.battlefield.get_effect(Weather.RAINDANCE).duration, 2)

    # def test_changing_weather_trio_weather_fails(self):
    #     pass # TODO: implement desolateland/primordialsea/deltastream abilities

    def test_weather_trio_does_not_expire(self):
        for weather in Weather.TRIO:
            self.battlefield.set_weather(weather)
            for _ in range(10):
                self.run_turn()
            self.assertEqual(self.battlefield.weather, weather)
