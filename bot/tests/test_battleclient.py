from __future__ import absolute_import
import json
from unittest import TestCase
from mock import patch

from bot.battleclient import BattleClient
from pokedex.enums import Status, Weather, Volatile
from pokedex.moves import movedex

class TestBattleClientBase(TestCase):
    def setUp(self):
        self.bc = BattleClient('test-BillsPC', 'battle-randombattle-1', lambda *_: None)

    REQUEST = '|request|{"side":{"name":"1BillsPC","id":"p1","pokemon":[{"ident":"p1: Hitmonchan","details":"Hitmonchan, L79, M","condition":"209/209","active":true,"stats":{"atk":211,"def":170,"spa":101,"spd":219,"spe":166},"moves":["solarbeam","machpunch","drainpunch","rapidspin"],"baseAbility":"ironfist","item":"assaultvest","pokeball":"pokeball","canMegaEvo":false},{"ident":"p1: Zekrom","details":"Zekrom, L73","condition":"266/266","active":false,"stats":{"atk":261,"def":218,"spa":218,"spd":188,"spe":174},"moves":["outrage","roost","voltswitch","boltstrike"],"baseAbility":"teravolt","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p1: Altaria","details":"Altaria, L75, M","condition":"236/236","active":false,"stats":{"atk":149,"def":179,"spa":149,"spd":201,"spe":164},"moves":["return","dragondance","earthquake","roost"],"baseAbility":"naturalcure","item":"altarianite","pokeball":"pokeball","canMegaEvo":true},{"ident":"p1: Charizard","details":"Charizard, L81, M","condition":"259/259","active":false,"stats":{"atk":183,"def":173,"spa":223,"spd":184,"spe":209},"moves":["earthquake","focusblast","fireblast","acrobatics"],"baseAbility":"blaze","item":"flyinggem","pokeball":"pokeball","canMegaEvo":false},{"ident":"p1: Rhyperior","details":"Rhyperior, L79, F","condition":"311/311","active":false,"stats":{"atk":267,"def":251,"spa":132,"spd":132,"spe":109},"moves":["earthquake","rockpolish","rockblast","megahorn"],"baseAbility":"reckless","item":"weaknesspolicy","pokeball":"pokeball","canMegaEvo":false},{"ident":"p1: Dunsparce","details":"Dunsparce, L83, M","condition":"302/302","active":false,"stats":{"atk":164,"def":164,"spa":156,"spd":156,"spe":122},"moves":["roost","coil","rockslide","headbutt"],"baseAbility":"serenegrace","item":"leftovers","pokeball":"pokeball","canMegaEvo":false}]}}'
    REQUEST = json.loads(REQUEST.split('|')[2])

    my_side = property(lambda self: self.bc.my_side)
    foe_side = property(lambda self: self.bc.foe_side)
    foe_name = property(lambda self: self.bc.foe_name)
    my_player = property(lambda self: self.bc.my_player)
    foe_player = property(lambda self: self.bc.foe_player)
    battlefield = property(lambda self: self.bc.battlefield)

    def handle(self, msg):
        if msg.startswith('|'):
            msg = msg[1:].split('|')
        self.bc.handle(msg[0], msg)

    def handle_request(self, request):
        if self.bc.my_side is None:
            self.bc.build_my_side(self.REQUEST)
        else:
            self.bc.handle_request(request)

    def set_up_players(self):
        self.handle('|player|p1|test-BillsPC|200')
        self.handle_request(self.REQUEST)
        self.handle('|player|p2|other-player|200')
        self.assertIsNotNone(self.bc.my_side)
        self.assertIsNotNone(self.bc.foe_side)
        self.assertIsNotNone(self.bc.battlefield)

    def set_up_turn_0(self):
        """
        p1: test-BillsPC
        p2: other-player
        p1 starts with Hitmonchan, p2 with Goodra. No moves have been made; it is turn 0.
        """
        self.set_up_players()
        self.handle('|start')
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')
        self.handle('|switch|p2a: Goodra|Goodra, L77, M|100/100')


class TestBattleClient(TestBattleClientBase):
    def test_build_my_side_from_request_msg(self):
        # TODO: ability/item
        self.bc.my_player = 0
        self.handle_request(self.REQUEST)

        side = self.my_side
        self.assertIsNotNone(side)
        self.assertEqual(side.team[0].name, 'hitmonchan')
        self.assertEqual(side.team[1].level, 73)
        self.assertListEqual(side.team[2].moveset,
                             [movedex[move] for move in ['return', 'dragondance',
                                                         'earthquake', 'roost']])
        self.assertDictEqual(dict(side.team[3].stats),
                             {'atk':183,'def':173,'spa':223,'spd':184,'spe':209,'max_hp':259})
        self.assertEqual(side.team[4].hp, 311)
        self.assertEqual(len(side.team), 6)

    def test_handle_player(self):
        msg = '|player|p1|test-BillsPC|200'
        self.handle(msg)

        self.assertEqual(self.my_player, 0)
        self.assertEqual(self.foe_player, 1)

        msg = '|player|p2|other-player|200'
        self.handle(msg)

        self.assertEqual(self.my_player, 0)
        self.assertEqual(self.foe_player, 1)
        self.assertEqual(self.foe_name, 'other-player')

    def test_handle_player_foe_first(self):
        msg = '|player|p1|other-player|266'
        self.handle(msg)

        self.assertEqual(self.my_player, 1)
        self.assertEqual(self.foe_player, 0)
        self.assertEqual(self.foe_name, 'other-player')

        msg = '|player|p2|test-BillsPC|266'
        self.assertEqual(self.my_player, 1)
        self.assertEqual(self.foe_player, 0)
        self.assertEqual(self.foe_name, 'other-player')


class TestBattleClientPostTurn0(TestBattleClientBase):
    def setUp(self):
        self.bc = BattleClient('test-BillsPC', 'battle-randombattle-1', lambda *_: None)
        self.set_up_turn_0()

    def test_first_switch_in(self):
        self.assertEqual(self.my_side.active_pokemon.name, 'hitmonchan')
        goodra = self.foe_side.active_pokemon
        self.assertEqual(goodra.name, 'goodra')
        self.assertEqual(goodra.hp, 265)
        self.assertListEqual(goodra.moveset, [])

        self.assertEqual(self.foe_side.num_unrevealed, 5)

    def test_my_switch_in_on_active(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')

        zekrom = self.my_side.active_pokemon
        self.assertEqual(zekrom.name, 'zekrom')
        self.assertTrue(zekrom.is_active)
        self.assertListEqual(zekrom.moveset, [movedex[move] for move in
                                              ['outrage', 'roost', 'voltswitch', 'boltstrike']])
        self.assertFalse(hitmonchan.is_active)
        self.assertEqual(zekrom.hp, 266)

    def _foe_switch_in_flareon(self):
        goodra = self.foe_side.active_pokemon
        self.handle('|switch|p2a: Flareon|Flareon, L83|100/100')
        return goodra

    def test_opponent_switch_in_reveal_on_active(self):
        goodra = self._foe_switch_in_flareon()

        self.assertFalse(goodra.is_active)
        flareon = self.foe_side.active_pokemon
        self.assertEqual(flareon.name, 'flareon')
        self.assertTrue(flareon.is_active)
        self.assertEqual(self.foe_side.num_unrevealed, 4)
        self.assertEqual(flareon.hp, 243)

    def test_opponent_switch_in_previously_revealed(self):
        self._foe_switch_in_flareon()
        flareon = self.foe_side.active_pokemon

        self.handle('|switch|p2a: Goodra|Goodra, L77, M|100/100')

        self.assertEqual(self.foe_side.num_unrevealed, 4)
        goodra = self.foe_side.active_pokemon
        self.assertTrue(goodra.is_active)
        self.assertFalse(flareon.is_active)

    def test_opponent_switch_in_status(self):
        hitmonchan = self.my_side.active_pokemon
        self.bc.set_status(hitmonchan, 'psn')
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.assertListEqual(hitmonchan.effects, [])
        self.assertListEqual(hitmonchan.effect_handlers['on_residual'], [])
        self.assertFalse(hitmonchan.has_effect(Status.PSN))
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')
        self.assertTrue(hitmonchan.has_effect(Status.PSN))

    def test_opponent_switch_in_sleep_turns(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-status|p1a: Hitmonchan|slp')
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.assertEqual(hitmonchan.sleep_turns, 1)
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')
        self.assertEqual(hitmonchan.sleep_turns, 1)
        self.assertEqual(hitmonchan.status, Status.SLP)
        self.assertTrue(hitmonchan.has_effect(Status.SLP))
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.assertEqual(hitmonchan.sleep_turns, 0)

    def test_handle_my_damage(self):
        self.handle('|-damage|p1a: Hitmonchan|175/209')
        hitmonchan = self.my_side.active_pokemon
        self.assertEqual(hitmonchan.hp, 175)

    def test_handle_foe_damage(self):
        self.handle('|-damage|p2a: Goodra|55/100')
        goodra = self.foe_side.active_pokemon
        self.assertEqual(goodra.hp, 146) # round(0.55 * 265)

    def test_handle_damage_faint(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-damage|p1a: Hitmonchan|0 fnt')
        self.assertEqual(hitmonchan.hp, 0)
        self.assertEqual(hitmonchan.status, Status.FNT)

    def test_handle_faint(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-damage|p1a: Hitmonchan|0 fnt')
        self.assertIsNotNone(self.my_side.active_pokemon)
        self.assertEqual(hitmonchan.hp, 0)
        self.assertEqual(hitmonchan.status, Status.FNT)

        self.handle('|faint|p1a: Hitmonchan')

    def test_handle_status(self):
        goodra = self.foe_side.active_pokemon
        self.handle('|-status|p2a: Goodra|brn')
        self.assertEqual(goodra.status, Status.BRN)
        self.assertTrue(goodra.has_effect(Status.BRN))

    def test_handle_status_sleep_always_2_turns(self):
        goodra = self.foe_side.active_pokemon
        self.handle('|-status|p2a: Goodra|slp')
        self.assertEqual(goodra.status, Status.SLP)
        self.assertEqual(goodra.get_effect(Status.SLP).turns_left, 2)
        self.assertEqual(goodra.sleep_turns, 2)

    def test_handle_boost(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.assertEqual(hitmonchan.boosts['atk'], 2)
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.assertEqual(hitmonchan.boosts['atk'], 4)

    def test_handle_unboost(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-unboost|p1a: Hitmonchan|spe|1')
        self.assertEqual(hitmonchan.boosts['spe'], -1)

    def test_handle_curestatus(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-status|p1a: Hitmonchan|slp|[from] move: Rest')
        self.assertEqual(hitmonchan.status, Status.SLP)
        self.handle('|-curestatus|p1a: Hitmonchan|slp')
        self.assertIsNone(hitmonchan.status)

    def test_handle_cureteam(self):
        hitmonchan = self.my_side.active_pokemon
        self.bc.set_status(hitmonchan, 'psn')
        zekrom = self.my_side.team[1]
        altaria = self.my_side.team[2]
        zekrom.status = Status.SLP
        zekrom.sleep_turns = 1
        altaria.hp = 0
        altaria.status = Status.FNT
        self.handle('|-cureteam|p1a: Hitmonchan|[from] move: HealBell')
        self.assertIsNone(hitmonchan.status)
        self.assertIsNone(zekrom.status)
        self.assertIsNone(zekrom.sleep_turns)
        self.assertEqual(altaria.status, Status.FNT)

    def test_handle_weather_start(self):
        self.handle('|-weather|Sandstorm')
        self.assertEqual(self.battlefield.weather, Weather.SANDSTORM)
        self.assertTrue(self.battlefield.has_effect, Weather.SANDSTORM)
        self.assertEqual(self.battlefield.get_effect(Weather.SANDSTORM).duration, 5)

        self.handle('|-weather|RainDance')
        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.assertTrue(self.battlefield.has_effect, Weather.RAINDANCE)
        self.assertEqual(self.battlefield.get_effect(Weather.RAINDANCE).duration, 8)

    def test_handle_weather_upkeep(self):
        self.handle('|-weather|Hail')
        self.assertEqual(self.battlefield.get_effect(Weather.HAIL).duration, 5)
        self.handle('|-weather|Hail|[upkeep]')
        self.assertEqual(self.battlefield.get_effect(Weather.HAIL).duration, 4)

    def test_handle_weather_none(self):
        self.handle('|-weather|Hail')
        self.handle('|-weather|Hail|[upkeep]')
        self.handle('|-weather|none')
        self.assertIsNone(self.battlefield.weather)
        self.assertFalse(self.battlefield.has_effect(Weather.HAIL))

    def test_handle_sethp(self):
        hitmonchan = self.my_side.active_pokemon
        goodra = self.foe_side.active_pokemon
        self.handle('|-sethp|p2a: Goodra|55/100|p1a: Hitmonchan|175/209|[from] move: Pain Split')
        self.assertEqual(hitmonchan.hp, 175)
        self.assertEqual(goodra.hp, 146)

    def test_handle_setboost(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-setboost|p1a: Hitmonchan|atk|6|[from] move: Belly Drum')
        self.assertEqual(hitmonchan.boosts['atk'], 6)

    def test_handle_restoreboost(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.handle('|-boost|p1a: Hitmonchan|spa|2')
        self.handle('|-boost|p1a: Hitmonchan|spe|2')
        self.handle('|-unboost|p1a: Hitmonchan|def|1')
        self.handle('|-unboost|p1a: Hitmonchan|spd|1')
        for stat in ('atk', 'spa', 'spe'):
            self.assertEqual(hitmonchan.boosts[stat], 2)
        for stat in ('def', 'spd'):
            self.assertEqual(hitmonchan.boosts[stat], -1)

        self.handle('|-restoreboost|p1a: Hitmonchan|[silent]')

        for stat in ('atk', 'spa', 'spe'):
            self.assertEqual(hitmonchan.boosts[stat], 2)

        for stat in ('def', 'spd'):
            self.assertEqual(hitmonchan.boosts[stat], 0)

    def test_handle_clearboost(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-boost|p1a: Hitmonchan|spa|2')
        self.handle('|-boost|p1a: Hitmonchan|spe|2')
        self.handle('|-unboost|p1a: Hitmonchan|def|1')
        self.handle('|-clearboost|p1a: Hitmonchan')
        for stat in ('def', 'spa', 'spe'):
            self.assertEqual(hitmonchan.boosts[stat], 0)

    def test_handle_clearallboost(self):
        hitmonchan = self.my_side.active_pokemon
        goodra = self.foe_side.active_pokemon
        hitmonchan.boosts['atk'] += 3
        hitmonchan.boosts['def'] -= 1
        goodra.boosts['spe'] += 1
        goodra.boosts['spa'] -= 2
        self.handle('|-clearallboost')

        for pokemon in (hitmonchan, goodra):
            for stat in ('atk', 'def', 'spe', 'spa'):
                self.assertEqual(pokemon.boosts[stat], 0)

    def test_handle_prepare(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-prepare|p1a: Hitmonchan|Solar Beam|p2a: Goodra')
        self.assertTrue(hitmonchan.has_effect(Volatile.TWOTURNMOVE))
        self.assertEqual(hitmonchan.get_effect(Volatile.TWOTURNMOVE).move.name, 'solarbeam')

        self.handle('|move|p1a: Hitmonchan|Solar Beam|p2a: Goodra')
        self.assertFalse(hitmonchan.has_effect(Volatile.TWOTURNMOVE))

    def test_handle_anim(self):
        hitmonchan = self.my_side.active_pokemon
        self.handle('|-prepare|p1a: Hitmonchan|Solar Beam|p2a: Goodra')
        self.handle('|-anim|p1a: Hitmonchan|Solar Beam|p2a: Goodra')

        self.assertFalse(hitmonchan.has_effect(Volatile.TWOTURNMOVE))
