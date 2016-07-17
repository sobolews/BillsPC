from __future__ import absolute_import
import json
from unittest import TestCase
from mock import patch

from battle.decisionmakers import AutoDecisionMaker
from bot.battleclient import BattleClient
from mining.statistics import RandbatsStatistics
from pokedex.abilities import abilitydex
from pokedex.enums import (Status, Weather, Volatile, ABILITY, ITEM, Type, SideCondition, Hazard,
                           PseudoWeather)
from pokedex.items import itemdex
from pokedex.moves import movedex

rbstats = RandbatsStatistics.from_pickle()

class TestBattleClientBase(TestCase):
    def setUp(self):
        self.bc = BattleClient('test-BillsPC', 'battle-randombattle-1', lambda *_: None)

    REQUEST = '|request|{"side":{"name":"test-BillsPC","id":"p1","pokemon":[{"ident":"p1: Hitmonchan","details":"Hitmonchan, L79, M","condition":"209/209","active":true,"stats":{"atk":211,"def":170,"spa":101,"spd":219,"spe":166},"moves":["solarbeam","machpunch","rapidspin","hiddenpowerice"],"baseAbility":"ironfist","item":"assaultvest","pokeball":"pokeball","canMegaEvo":false},{"ident":"p1: Zekrom","details":"Zekrom, L73","condition":"266/266","active":false,"stats":{"atk":261,"def":218,"spa":218,"spd":188,"spe":174},"moves":["outrage","roost","voltswitch","boltstrike"],"baseAbility":"regenerator","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p1: Altaria","details":"Altaria, L75, M","condition":"236/236","active":false,"stats":{"atk":149,"def":179,"spa":149,"spd":201,"spe":164},"moves":["return","dragondance","earthquake","roost"],"baseAbility":"naturalcure","item":"altarianite","pokeball":"pokeball","canMegaEvo":true},{"ident":"p2: Ditto","details":"Ditto, L83","condition":"215/215","active":true,"stats":{"atk":127,"def":127,"spa":127,"spd":127,"spe":127},"moves":["transform"],"baseAbility":"imposter","item":"choicescarf","pokeball":"pokeball"},{"ident":"p2: Giratina","details":"Giratina-Origin, L73","condition":"339/339","active":false,"stats":{"atk":218,"def":188,"spa":218,"spd":188,"spe":174},"moves":["defog","dragontail","taunt","shadowsneak"],"baseAbility":"mummy","item":"griseousorb","pokeball":"pokeball"},{"ident":"p1: Dunsparce","details":"Dunsparce, L83, M","condition":"302/302","active":false,"stats":{"atk":164,"def":164,"spa":156,"spd":156,"spe":122},"moves":["roost","coil","rockslide","headbutt"],"baseAbility":"trace","item":"leftovers","pokeball":"pokeball","canMegaEvo":false}]}}'
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
            self.bc.build_my_side(request)
        else:
            self.bc.handle_request(request)
        self.bc.request = request

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
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')
        self.handle('|switch|p2a: Goodra|Goodra, L77, F|100/100')
        self.handle('|turn|1')


class TestBattleClientInitialRequestBase(TestBattleClientBase):
    def setUp(self):
        self.bc = BattleClient('test-BillsPC', 'battle-randombattle-1', lambda *_: None)
        self.bc.make_moves = False

    def initial_request(self, request):
        self.handle('|player|p1|test-BillsPC|200')
        self.handle_request(request)
        self.handle('|player|p2|other-player|200')


class TestBattleClientDittoLead(TestBattleClientInitialRequestBase):
    def test_start_with_ditto_turn_0(self):
        request = '|request|{"active":[{"moves":[{"move":"Volt Switch","id":"voltswitch","pp":5,"maxpp":5,"target":"normal","disabled":false},{"move":"Ice Punch","id":"icepunch","pp":5,"maxpp":5,"target":"normal","disabled":false},{"move":"Wild Charge","id":"wildcharge","pp":5,"maxpp":5,"target":"normal","disabled":false},{"move":"Cross Chop","id":"crosschop","pp":5,"maxpp":5,"target":"normal","disabled":false}]}],"side":{"name":"test-BillsPC","id":"p1","pokemon":[{"ident":"p1: Ditto","details":"Ditto, L83","condition":"215/215","active":true,"stats":{"atk":127,"def":127,"spa":127,"spd":127,"spe":127},"moves":["voltswitch","icepunch","wildcharge","crosschop"],"baseAbility":"imposter","item":"choicescarf","pokeball":"pokeball"},{"ident":"p1: Unfezant","details":"Unfezant, L83, M","condition":"267/267","active":false,"stats":{"atk":239,"def":180,"spa":156,"spd":139,"spe":202},"moves":["pluck","uturn","tailwind","roost"],"baseAbility":"superluck","item":"scopelens","pokeball":"pokeball"},{"ident":"p1: Dugtrio","details":"Dugtrio, L79, F","condition":"185/185","active":false,"stats":{"atk":172,"def":125,"spa":125,"spd":156,"spe":235},"moves":["stealthrock","suckerpunch","reversal","earthquake"],"baseAbility":"arenatrap","item":"focussash","pokeball":"pokeball"},{"ident":"p1: Typhlosion","details":"Typhlosion, L79, M","condition":"253/253","active":false,"stats":{"atk":137,"def":169,"spa":218,"spd":180,"spe":204},"moves":["focusblast","eruption","extrasensory","fireblast"],"baseAbility":"flashfire","item":"choicescarf","pokeball":"pokeball"},{"ident":"p1: Kyogre","details":"Kyogre, L73","condition":"266/266","active":false,"stats":{"atk":151,"def":174,"spa":261,"spd":247,"spe":174},"moves":["waterspout","icebeam","scald","thunder"],"baseAbility":"drizzle","item":"choicespecs","pokeball":"pokeball"},{"ident":"p1: Manaphy","details":"Manaphy, L75","condition":"274/274","active":false,"stats":{"atk":155,"def":194,"spa":194,"spd":194,"spe":194},"moves":["surf","energyball","psychic","tailglow"],"baseAbility":"hydration","item":"leftovers","pokeball":"pokeball"}]},"rqid":1}'
        self.initial_request(json.loads(request.split('|')[2]))
        self.handle('|switch|p2a: Electivire|Electivire, L81, F|100/100')
        self.handle('|switch|p1a: Ditto|Ditto, L83|215/215')
        self.handle('|-transform|p1a: Ditto|p2a: Electivire|[from] ability: Imposter')
        self.handle('|turn|1')

        self.bc._validate_my_team()


class TestBattleClient(TestBattleClientBase):
    def test_build_my_side_from_request_msg(self):
        # TODO: ability/item
        self.bc.my_player = 0
        self.handle_request(self.REQUEST)

        side = self.my_side
        self.assertIsNotNone(side)
        self.assertEqual(side.team[0].name, 'hitmonchan')
        self.assertEqual(side.team[1].level, 73)
        self.assertSetEqual(set(move.name for move in side.team[2].moves),
                            {'return', 'dragondance', 'earthquake', 'roost'})
        self.assertDictEqual(dict(side.team[3].stats),
                             {'atk': 127, 'def': 127, 'spa': 127,
                              'spd': 127, 'spe': 127, 'max_hp': 215})
        self.assertEqual(side.team[4].hp, 339)
        self.assertEqual(side.team[5].ability.name, 'trace')
        self.assertEqual(side.team[5].item.name, 'leftovers')
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
        self.bc.make_moves = False
        self.bc.engine.decision_makers = (AutoDecisionMaker(0), AutoDecisionMaker(1))
        self.set_up_turn_0()
        self.hitmonchan = self.my_side.active_pokemon
        self.goodra = self.foe_side.active_pokemon

    def assertHiddenPowerType(self, pokemon, type):
        hps = [move for move in pokemon.moves if move.is_hiddenpower]
        if len(hps) == 0:
            raise AssertionError("%s doesn't have a hiddenpower: %s" % (pokemon, pokemon.moves))
        elif len(hps) > 1:
            raise AssertionError("%s has multiple hiddenpowers: %s" % (pokemon, pokemon.moves))
        self.assertEqual(hps[0].type, type)

    def test_first_switch_in(self):
        self.assertEqual(self.hitmonchan.name, 'hitmonchan')
        self.assertEqual(self.hitmonchan.get_effect(ABILITY).name, 'ironfist')
        self.assertIn(self.hitmonchan.get_effect(ABILITY).on_modify_base_power,
                      self.hitmonchan.effect_handlers['on_modify_base_power'])
        self.assertEqual(self.hitmonchan.get_effect(ITEM).name, 'assaultvest')
        self.assertIn(self.hitmonchan.get_effect(ITEM).on_modify_spd,
                      self.hitmonchan.effect_handlers['on_modify_spd'])
        self.assertEqual(self.hitmonchan.gender, 'M')

        self.assertEqual(self.goodra.name, 'goodra')
        self.assertEqual(self.goodra.hp, 265)
        self.assertDictEqual(self.goodra.moves, {})
        self.assertEqual(self.goodra.gender, 'F')

        self.assertEqual(self.foe_side.num_unrevealed, 5)

    def test_my_switch_in_on_active(self):
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')

        zekrom = self.my_side.active_pokemon
        self.assertEqual(zekrom.name, 'zekrom')
        self.assertTrue(zekrom.is_active)
        self.assertSetEqual(set(move.name for move in zekrom.moves),
                            {'outrage', 'roost', 'voltswitch', 'boltstrike'})
        self.assertFalse(self.hitmonchan.is_active)
        self.assertEqual(zekrom.hp, 266)
        self.assertEqual(zekrom.gender, None)

    def test_switch_in_ident_details_mismatch(self):
        """ details: "Giratina-Origin, L73" is referred to as ident: "p1: Giratina" """
        self.handle('|switch|p1a: Giratina|Giratina-Origin, L73|339/339')
        giratina = self.my_side.active_pokemon
        self.assertTrue(giratina.is_active)

    def _foe_switch_in_flareon(self):
        self.handle('|switch|p2a: Flareon|Flareon, L83|100/100')

    def test_opponent_switch_in_reveal_on_active(self):
        self._foe_switch_in_flareon()

        self.assertFalse(self.goodra.is_active)
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
        self.assertTrue(self.goodra.is_active)
        self.assertFalse(flareon.is_active)

    def test_opponent_switch_in_status(self):
        self.bc.set_status(self.hitmonchan, 'psn')
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.assertListEqual(self.hitmonchan.effects, [])
        self.assertListEqual(self.hitmonchan.effect_handlers['on_residual'], [])
        self.assertFalse(self.hitmonchan.has_effect(Status.PSN))
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209 psn')
        self.assertTrue(self.hitmonchan.has_effect(Status.PSN))

    def test_opponent_switch_in_turns_slept(self):
        self.handle('|-status|p1a: Hitmonchan|slp')
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.assertEqual(self.hitmonchan.turns_slept, 1)
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209 slp')
        self.assertEqual(self.hitmonchan.turns_slept, 1)
        self.assertEqual(self.hitmonchan.status, Status.SLP)
        self.assertTrue(self.hitmonchan.has_effect(Status.SLP))
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.handle('|cant|p1a: Hitmonchan|slp')
        self.assertEqual(self.hitmonchan.turns_slept, 3)

    def test_handle_my_move(self):
        self.handle('|move|p1a: Hitmonchan|Mach Punch|p2a: Goodra')
        self.assertEqual(self.hitmonchan.pp[movedex['machpunch']], 48 - 1)
        self.assertTrue(self.hitmonchan.last_move_used == movedex['machpunch'])

        for _ in range(10):
            self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2a: Goodra')
        self.assertEqual(self.hitmonchan.pp[movedex['rapidspin']], 64 - 10)

    def test_handle_my_move_hiddenpower(self):
        self.handle('|move|p1a: Hitmonchan|Hidden Power|p2a: Goodra')
        self.assertEqual(self.hitmonchan.pp[movedex['hiddenpowerice']], 24 - 1)

    def test_handle_foe_move(self):
        self.assertDictEqual(self.goodra.moves, {})
        self.handle('|move|p2a: Goodra|Draco Meteor|p1a: Hitmonchan')
        self.assertListEqual(self.goodra.moves.keys(), [movedex['dracometeor']])
        self.assertEqual(self.goodra.pp[movedex['dracometeor']], 8 - 1)

        self.handle('|move|p2a: Goodra|Draco Meteor|p1a: Hitmonchan')
        self.assertEqual(self.goodra.pp[movedex['dracometeor']], 8 - 2)

    def test_handle_foe_move_hiddenpower(self):
        self.handle('|move|p2a: Goodra|Hidden Power|p1a: Hitmonchan')
        hp = [move for move in self.goodra.moves if move.is_hiddenpower][0]
        self.assertEqual(self.goodra.pp[hp], 24 - 1)

    def test_handle_move_not_in_moveset(self):
        with self.assertRaises(AssertionError):
            self.handle('|move|p1a: Hitmonchan|Dragon Pulse|p2a: Goodra')

    def test_set_will_move_this_turn(self):
        self.assertTrue(self.hitmonchan.will_move_this_turn)
        self.assertTrue(self.goodra.will_move_this_turn)
        self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2a: Goodra')
        self.assertFalse(self.hitmonchan.will_move_this_turn)
        self.assertTrue(self.goodra.will_move_this_turn)
        self.handle('|move|p2a: Goodra|Dragon Pulse|p1a: Hitmonchan')
        self.assertFalse(self.hitmonchan.will_move_this_turn)
        self.assertFalse(self.goodra.will_move_this_turn)
        self.handle('|turn|2')
        self.assertTrue(self.hitmonchan.will_move_this_turn)
        self.assertTrue(self.goodra.will_move_this_turn)

    def test_handle_my_damage(self):
        self.handle('|-damage|p1a: Hitmonchan|175/209')
        self.assertEqual(self.hitmonchan.hp, 175)

    def test_handle_foe_damage(self):
        self.handle('|-damage|p2a: Goodra|55/100')
        self.assertEqual(self.goodra.hp, 146) # round(0.55 * 265)

    def test_handle_damage_faint(self):
        self.handle('|-damage|p1a: Hitmonchan|0 fnt')
        self.assertEqual(self.hitmonchan.hp, 0)
        self.assertEqual(self.hitmonchan.status, Status.FNT)

    def test_handle_faint(self):
        self.handle('|-damage|p1a: Hitmonchan|0 fnt')
        self.assertIsNotNone(self.my_side.active_pokemon)
        self.assertEqual(self.hitmonchan.hp, 0)
        self.assertEqual(self.hitmonchan.status, Status.FNT)

        self.handle('|faint|p1a: Hitmonchan')

    def test_handle_status(self):
        self.handle('|-status|p2a: Goodra|brn')
        self.assertEqual(self.goodra.status, Status.BRN)
        self.assertTrue(self.goodra.has_effect(Status.BRN))

    def test_handle_status_rest(self):
        self.bc.set_status(self.goodra, 'brn')
        self.goodra.hp -= 100
        self.handle('|-status|p2a: Goodra|slp')
        self.handle('|-heal|p2a: Goodra|100/100 slp|[silent]')
        self.handle('|-status|p2a: Goodra|slp|[from] move: Rest')

        self.assertEqual(self.goodra.hp, self.goodra.max_hp)
        self.assertEqual(self.goodra.status, Status.SLP)
        self.assertTrue(self.goodra.has_effect(Status.SLP))
        self.assertTrue(self.goodra.get_effect(Status.SLP).rest)
        self.assertTrue(self.goodra.is_resting)
        self.assertEqual(self.goodra.turns_slept, 0)

    def test_handle_boost(self):
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.assertEqual(self.hitmonchan.boosts['atk'], 2)
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.assertEqual(self.hitmonchan.boosts['atk'], 4)
        self.handle('|-boost|p1a: Hitmonchan|accuracy|1')
        self.assertEqual(self.hitmonchan.boosts['acc'], 1)
        self.handle('|-boost|p1a: Hitmonchan|atk|1')
        # server sends 2 even though it can only go up 1 from +5
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.assertEqual(self.hitmonchan.boosts['atk'], 6) # don't go above 6

    def test_handle_unboost(self):
        self.handle('|-unboost|p1a: Hitmonchan|spe|1')
        self.assertEqual(self.hitmonchan.boosts['spe'], -1)
        self.handle('|-unboost|p1a: Hitmonchan|evasion|1')
        self.assertEqual(self.hitmonchan.boosts['evn'], -1)
        self.handle('|-unboost|p1a: Hitmonchan|spe|4')
        self.handle('|-unboost|p1a: Hitmonchan|spe|5')
        self.assertEqual(self.hitmonchan.boosts['spe'], -6) # don't go below -6

    def test_handle_curestatus(self):
        self.handle('|-status|p1a: Hitmonchan|slp|[from] move: Rest')
        self.assertEqual(self.hitmonchan.status, Status.SLP)
        self.handle('|-curestatus|p1a: Hitmonchan|slp')
        self.assertIsNone(self.hitmonchan.status)

    def test_handle_cureteam(self):
        self.bc.set_status(self.hitmonchan, 'psn')
        zekrom = self.my_side.team[1]
        altaria = self.my_side.team[2]
        zekrom.status = Status.SLP
        zekrom.turns_slept = 1
        altaria.hp = 0
        altaria.status = Status.FNT
        self.handle('|-cureteam|p1a: Hitmonchan|[from] move: HealBell')
        self.assertIsNone(self.hitmonchan.status)
        self.assertIsNone(zekrom.status)
        self.assertIsNone(zekrom.turns_slept)
        self.assertEqual(altaria.status, Status.FNT)

    def test_handle_weather_start(self):
        self.handle('|-weather|Sandstorm')
        self.assertEqual(self.battlefield.weather, Weather.SANDSTORM)
        self.assertTrue(self.battlefield.has_effect, Weather.SANDSTORM)
        self.assertEqual(self.battlefield.get_effect(Weather.SANDSTORM).duration, 5)

        self.handle('|switch|p2a: Ludicolo|Ludicolo, L81, M|100/100')
        self.handle('|-enditem|p2a: Ludicolo|Damp Rock|[from] move: Knock Off|[of] p1a: Hitmonchan')
        self.handle('|move|p2a: Ludicolo|Rain Dance|p2a: Ludicolo')
        self.handle('|-weather|RainDance')

        self.assertEqual(self.battlefield.weather, Weather.RAINDANCE)
        self.assertTrue(self.battlefield.has_effect, Weather.RAINDANCE)
        self.assertEqual(self.battlefield.get_effect(Weather.RAINDANCE).duration, 5)

        self.handle('|-weather|Sandstorm')
        self.handle('|-item|p2a: Ludicolo|Damp Rock|[from] move: Trick')
        self.handle('|move|p2a: Ludicolo|Rain Dance|p2a: Ludicolo')
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

    def test_handle_weather_from_ability(self):
        self.handle('|switch|p2a: Aurorus|Aurorus, L81, F|100/100')
        self.handle('|-weather|Hail|[from] ability: Snow Warning|[of] p2a: Aurorus')
        self.handle('|turn|2')

        aurorus = self.foe_side.active_pokemon
        self.assertEqual(aurorus.ability, abilitydex['snowwarning'])
        self.assertTrue(self.battlefield.has_effect(Weather.HAIL))

    def test_handle_sethp(self):
        self.handle('|-sethp|p2a: Goodra|55/100|p1a: Hitmonchan|175/209|[from] move: Pain Split')
        self.assertEqual(self.hitmonchan.hp, 175)
        self.assertEqual(self.goodra.hp, 146)

    def test_handle_setboost(self):
        self.handle('|-setboost|p1a: Hitmonchan|atk|6|[from] move: Belly Drum')
        self.handle('|switch|p2a: Primeape|Primeape, L81, M|100/100')
        self.handle('|-setboost|p2a: Primeape|atk|12|[from] ability: Anger Point')
        self.handle('|turn|2')

        primeape = self.foe_side.active_pokemon
        self.assertEqual(self.hitmonchan.boosts['atk'], 6)
        self.assertEqual(primeape.boosts['atk'], 6)
        self.assertEqual(primeape.ability, abilitydex['angerpoint'])

    def test_handle_restoreboost(self):
        self.handle('|-boost|p1a: Hitmonchan|atk|2')
        self.handle('|-boost|p1a: Hitmonchan|spa|2')
        self.handle('|-boost|p1a: Hitmonchan|spe|2')
        self.handle('|-unboost|p1a: Hitmonchan|def|1')
        self.handle('|-unboost|p1a: Hitmonchan|spd|1')
        for stat in ('atk', 'spa', 'spe'):
            self.assertEqual(self.hitmonchan.boosts[stat], 2)
        for stat in ('def', 'spd'):
            self.assertEqual(self.hitmonchan.boosts[stat], -1)

        self.handle('|-restoreboost|p1a: Hitmonchan|[silent]')

        for stat in ('atk', 'spa', 'spe'):
            self.assertEqual(self.hitmonchan.boosts[stat], 2)

        for stat in ('def', 'spd'):
            self.assertEqual(self.hitmonchan.boosts[stat], 0)

    def test_handle_clearboost(self):
        self.handle('|-boost|p1a: Hitmonchan|spa|2')
        self.handle('|-boost|p1a: Hitmonchan|spe|2')
        self.handle('|-unboost|p1a: Hitmonchan|def|1')
        self.handle('|-clearboost|p1a: Hitmonchan')
        for stat in ('def', 'spa', 'spe'):
            self.assertEqual(self.hitmonchan.boosts[stat], 0)

    def test_handle_clearallboost(self):
        self.hitmonchan.boosts['atk'] += 3
        self.hitmonchan.boosts['def'] -= 1
        self.goodra.boosts['spe'] += 1
        self.goodra.boosts['spa'] -= 2
        self.handle('|-clearallboost')

        for pokemon in (self.hitmonchan, self.goodra):
            for stat in ('atk', 'def', 'spe', 'spa'):
                self.assertEqual(pokemon.boosts[stat], 0)

    def test_handle_prepare(self):
        self.handle('|-prepare|p1a: Hitmonchan|Solar Beam|p2a: Goodra')
        self.assertTrue(self.hitmonchan.has_effect(Volatile.TWOTURNMOVE))
        self.assertEqual(self.hitmonchan.get_effect(Volatile.TWOTURNMOVE).move.name, 'solarbeam')

        self.handle('|move|p1a: Hitmonchan|Solar Beam|p2a: Goodra')
        self.assertFalse(self.hitmonchan.has_effect(Volatile.TWOTURNMOVE))

    def test_handle_anim(self):
        self.handle('|-prepare|p1a: Hitmonchan|Solar Beam|p2a: Goodra')
        self.handle('|-anim|p1a: Hitmonchan|Solar Beam|p2a: Goodra')

        self.assertFalse(self.hitmonchan.has_effect(Volatile.TWOTURNMOVE))

    def test_handle_item(self):
        self.handle('|-item|p1a: Hitmonchan|Air Balloon')
        self.assertEqual(self.hitmonchan.item, itemdex['airballoon'])
        self.handle(
            '|-item|p2a: Goodra|Leftovers|[from] ability: Frisk|[of] p1a: Hitmonchan|[identify]')
        self.assertEqual(self.goodra.item, itemdex['leftovers'])
        self.assertIn(self.goodra.get_effect(ITEM).on_residual,
                      self.goodra.effect_handlers['on_residual'])
        self.handle('|-item|p2a: Goodra|Choice Scarf|[from] move: Trick')
        self.assertEqual(self.goodra.item, itemdex['choicescarf'])
        self.assertNotIn(self.goodra.get_effect(ITEM).on_residual,
                         self.goodra.effect_handlers['on_residual'])
        self.assertIn(self.goodra.get_effect(ITEM).on_modify_spe,
                      self.goodra.effect_handlers['on_modify_spe'])

    def test_handle_enditem(self):
        self.handle(
            '|-enditem|p1a: Hitmonchan|Assault Vest|[from] move: Knock Off|[of] p2a: Goodra')
        self.assertIsNone(self.hitmonchan.item)
        self.assertFalse(self.hitmonchan.has_effect(ITEM))
        self.assertEqual(self.hitmonchan.effect_handlers['on_modify_spd'], [])
        self.assertIsNone(self.hitmonchan.item_used_this_turn)

        self.handle('|switch|p2a: Arbok|Arbok, L83, F|100/100')
        self.handle('|-enditem|p2a: Arbok|Chesto Berry|[eat]')

        arbok = self.foe_side.active_pokemon
        self.assertIsNone(arbok.item)
        self.assertEqual(arbok.last_berry_used, itemdex['chestoberry'])
        self.assertEqual(arbok.item_used_this_turn, itemdex['chestoberry'])

        self.handle('|-enditem|p2a: Arbok|Focus Sash')
        self.assertIsNone(arbok.item)
        self.assertIsNone(arbok.last_berry_used)
        self.assertEqual(arbok.item_used_this_turn, itemdex['focussash'])

        self.handle('|turn|2')
        self.assertIsNone(arbok.item_used_this_turn)

    def test_handle_enditem_from_stealeat(self):
        self.handle('|-enditem|p1a: Hitmonchan|Sitrus Berry'
                    '|[from] stealeat|[move] Bug Bite|[of] p2a: Goodra')
        self.assertEqual(self.goodra.last_berry_used, itemdex['sitrusberry'])
        self.assertIsNone(self.hitmonchan.last_berry_used)
        self.assertIsNone(self.hitmonchan.item)

    def test_handle_ability(self):
        self.handle('|switch|p2a: Mewtwo|Mewtwo, L73|100/100')
        self.handle('|-ability|p1a: Hitmonchan|Moxie|boost')
        self.handle('|-ability|p2a: Mewtwo|Unnerve|p1: test-BillsPC')

        mewtwo = self.foe_side.active_pokemon
        self.assertEqual(self.hitmonchan.ability, abilitydex['moxie'])
        self.assertEqual(mewtwo.ability, abilitydex['unnerve'])
        self.assertIn(self.hitmonchan.get_effect(ABILITY).on_foe_faint,
                      self.hitmonchan.effect_handlers['on_foe_faint'])

    def test_handle_ability_trace(self):
        self.handle('|switch|p2a: Arbok|Arbok, L83, M|100/100')
        self.handle('|switch|p1a: Dunsparce|Dunsparce, L83, M|302/302')
        arbok = self.foe_side.active_pokemon
        dunsparce = self.my_side.active_pokemon
        self.handle('|-ability|p1a: Dunsparce|Shed Skin|[from] ability: Trace|[of] p2a: Arbok')

        self.assertEqual(dunsparce.base_ability, abilitydex['trace'])
        self.assertEqual(dunsparce.ability, abilitydex['shedskin'])
        self.assertEqual(arbok.base_ability, abilitydex['shedskin'])
        self.assertEqual(arbok.ability, abilitydex['shedskin'])

    def test_handle_move_with_foe_pressure(self):
        self.handle('|switch|p2a: Moltres|Moltres, L78|100/100')
        self.handle('|move|p1a: Hitmonchan|Mach Punch|p2a: Moltres')
        self.handle('|-ability|p2a: Moltres|Pressure')
        self.handle('|move|p1a: Hitmonchan|Mach Punch|p2a: Moltres')

        self.assertEqual(self.hitmonchan.pp[movedex['machpunch']], 48 - 3)

    def test_handle_move_with_my_pressure(self):
        self.handle('|-ability|p1a: Hitmonchan|Pressure')
        self.handle('|move|p2a: Goodra|Draco Meteor|p1a: Hitmonchan')

        self.assertEqual(self.goodra.pp[movedex['dracometeor']], 8 - 2)

    def test_handle_transform(self):
        self.handle('|switch|p1a: Ditto|Ditto, L83|215/215')
        ditto = self.my_side.active_pokemon
        self.bc.request = {"active":[{"moves": [{"move":"Dragon Tail","id":"dragontail","pp":5,"maxpp":5,"target":"normal","disabled":False},{"move":"Thunderbolt","id":"thunderbolt","pp":5,"maxpp":5,"target":"normal","disabled":False},{"move":"Fire Blast","id":"fireblast","pp":5,"maxpp":5,"target":"normal","disabled":False},{"move":"Earthquake","id":"earthquake","pp":5,"maxpp":5,"target":"normal","disabled":False}]}],"side":{"name":"test-BillsPC", "id":"p1","pokemon":[{"ident":"p2: Ditto","details":"Ditto, L83","condition":"215/215","active":True,"stats":{"atk":127,"def":127,"spa":127,"spd":127,"spe":127},"moves":["dragontail", "thunderbolt", "fireblast", "earthquake"],"baseAbility":"imposter","item":"choicescarf","pokeball":"pokeball"}]},"rqid":2}
        self.handle('|-transform|p1a: Ditto|p2a: Goodra|[from] ability: Imposter')
        self.handle('|turn|2')

        self.assertTrue(ditto.is_transformed)
        self.assertIn(movedex['dragontail'], ditto.moves)
        self.assertIn(movedex['dragontail'], self.goodra.moves)
        self.assertEqual(ditto.pp.get(movedex['thunderbolt']), 5)
        self.assertEqual(ditto.name, 'goodra')
        self.assertListEqual(ditto.types, [Type.DRAGON, None])
        self.assertEqual(ditto.base_ability, abilitydex['imposter'])
        self.assertEqual(ditto.ability, abilitydex['sapsipper']) # goodra only gets sapsipper

        ditto_stats = ditto.stats.copy()
        del ditto_stats['max_hp']
        self.assertDictContainsSubset(ditto_stats, self.goodra.stats)
        self.assertEqual(ditto.stats['max_hp'], 215)
        self.assertEqual(ditto.hp, 215)

        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')
        self.handle('|turn|3')

        self.assertFalse(ditto.is_transformed)
        self.assertEqual(ditto.stats['atk'], 127)
        self.assertEqual(ditto.name, 'ditto')
        self.assertListEqual(ditto.moves.keys(), [movedex['transform']])
        self.assertEqual(ditto.ability, abilitydex['imposter'])

    def base_ditto_scrafty(self):
        """ Starting point for the following 2 tests """
        self.handle('|switch|p1a: Ditto|Ditto, L83|215/215')
        self.handle('|switch|p2a: Scrafty|Scrafty, L79, F|100/100')
        self.bc.request = {"active":[{"moves": [{"move":"Dragon Dance","id":"dragondance","pp":5,"maxpp":5,"target":"normal","disabled":False},{"move":"High Jump Kick","id":"highjumpkick","pp":5,"maxpp":5,"target":"normal","disabled":False},{"move":"Knock Off","id":"knockoff","pp":5,"maxpp":5,"target":"normal","disabled":False},{"move":"Rest","id":"rest","pp":5,"maxpp":5,"target":"normal","disabled":False}]}],"side":{"name":"test-BillsPC", "id":"p1","pokemon":[{"ident":"p2: Ditto","details":"Ditto, L83","condition":"215/215","active":True,"stats":{"atk":127,"def":127,"spa":127,"spd":127,"spe":127},"moves":["dragondance", "highjumpkick", "knockoff", "rest"],"baseAbility":"imposter","item":"choicescarf","pokeball":"pokeball"}]},"rqid":3}
        self.handle('|-transform|p1a: Ditto|p2a: Scrafty|[from] ability: Imposter')
        self.handle('|turn|2')

        ditto = self.my_side.active_pokemon
        scrafty = self.foe_side.active_pokemon
        self.assertEqual(ditto.ability, abilitydex['_unrevealed_'])
        self.assertEqual(scrafty.ability, abilitydex['_unrevealed_'])

    def test_handle_transformed_copy_inferred_foe_ability(self):
        self.base_ditto_scrafty()
        ditto = self.my_side.active_pokemon
        scrafty = self.foe_side.active_pokemon

        self.handle('|-heal|p2a: Scrafty|100/100|[from] item: Leftovers')
        self.handle('|turn|3')

        # given (leftovers, rest), scrafty's ability must be shedskin
        self.assertEqual(scrafty.item, itemdex['leftovers'])
        self.assertEqual(scrafty.ability, abilitydex['shedskin'])
        self.assertEqual(ditto.ability, abilitydex['shedskin']) # update ditto as well
        self.assertEqual(ditto.base_ability, abilitydex['imposter'])

    def test_handle_infer_foe_ability_when_revealed_by_ditto(self):
        self.base_ditto_scrafty()
        ditto = self.my_side.active_pokemon
        scrafty = self.foe_side.active_pokemon

        self.handle('|-activate|p1a: Ditto|ability: Shed Skin')
        self.handle('|turn|3')

        self.assertEqual(scrafty.ability, abilitydex['shedskin']) # foe was updated
        self.assertEqual(ditto.ability, abilitydex['shedskin'])
        self.assertEqual(ditto.base_ability, abilitydex['imposter'])

    def test_handle_start_end_taunt(self):
        self.handle('|switch|p1a: Dunsparce|Dunsparce, L83, M|302/302')
        self.handle('|turn|2')
        self.handle('|-start|p1a: Dunsparce|move: Taunt')
        self.handle('|turn|3')
        dunsparce = self.my_side.active_pokemon
        self.assertTrue(dunsparce.has_effect(Volatile.TAUNT))
        self.assertEqual(set(dunsparce.get_move_choices()),
                         {movedex['rockslide'], movedex['headbutt']})
        # duration == 2, because dunsparce hadn't moved yet and next turn is started
        self.assertEqual(dunsparce.get_effect(Volatile.TAUNT).duration, 2)

        self.handle('|-end|p1a: Dunsparce|move: Taunt')
        self.handle('|turn|4')
        self.assertFalse(dunsparce.has_effect(Volatile.TAUNT))
        self.assertEqual(set(dunsparce.get_move_choices()),
                         {movedex['rockslide'], movedex['headbutt'],
                          movedex['roost'], movedex['coil']})

        self.handle('|move|p1a: Dunsparce|Headbutt|p2a: Goodra')
        self.handle('|-start|p1a: Dunsparce|move: Taunt')
        self.handle('|turn|5')
        # since dunsparce had moved, duration == 3
        self.assertEqual(dunsparce.get_effect(Volatile.TAUNT).duration, 3)

    def test_handle_start_activate_end_confusion(self):
        self.handle('|-start|p2a: Goodra|confusion|[fatigue]')
        self.assertTrue(self.goodra.has_effect(Volatile.CONFUSE))
        self.assertEqual(self.goodra.get_effect(Volatile.CONFUSE).turns_left, 4)

        self.handle('|-activate|p2a: Goodra|confusion')
        self.assertEqual(self.goodra.get_effect(Volatile.CONFUSE).turns_left, 3)

        self.handle('|-end|p2a: Goodra|confusion')
        self.assertFalse(self.goodra.has_effect(Volatile.CONFUSE))

    def test_handle_move_autotomize(self):
        self.handle('|move|p2a: Goodra|Autotomize|p2a: Goodra')
        self.assertTrue(self.goodra.has_effect(Volatile.AUTOTOMIZE))
        self.assertEqual(self.goodra.weight,
                         self.goodra.pokedex_entry.weight - 100)

        self.handle('|move|p2a: Goodra|Autotomize|p2a: Goodra')
        self.assertTrue(self.goodra.has_effect(Volatile.AUTOTOMIZE))
        self.assertEqual(self.goodra.weight, 0.1)

    def test_handle_start_end_substitute(self):
        self.handle('|-damage|p2a: Goodra|75/100')
        self.handle('|-start|p2a: Goodra|Substitute')

        sub = self.goodra.get_effect(Volatile.SUBSTITUTE)
        self.assertIsNotNone(sub)
        self.assertEqual(sub.hp, self.goodra.max_hp / 4)

        self.handle('|move|p1a: Hitmonchan|Mach Punch|p2a: Goodra')
        self.handle('|-end|p2a: Goodra|Substitute')

        self.assertFalse(self.goodra.has_effect(Volatile.SUBSTITUTE))
        self.assertEqual(self.goodra.hp, self.goodra.max_hp - self.goodra.max_hp / 4)

        self.handle('|-damage|p2a: Goodra|50/100')
        self.handle('|-start|p2a: Goodra|Substitute')

        sub = self.goodra.get_effect(Volatile.SUBSTITUTE)
        self.assertIsNotNone(sub)
        self.assertEqual(sub.hp, self.goodra.max_hp / 4)

        self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2a: Goodra')
        self.handle('|-activate|p2a: Goodra|Substitute|[damage]')

        self.assertTrue(self.goodra.has_effect(Volatile.SUBSTITUTE))
        # hitmonchan rapidspin vs goodra: best guess calc = 18
        self.assertEqual(sub.hp, (self.goodra.max_hp / 4) - 18)

        self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2a: Goodra')
        self.handle('|-crit|p2a: Goodra')
        self.handle('|-activate|p2a: Goodra|Substitute|[damage]')

        self.assertTrue(self.goodra.has_effect(Volatile.SUBSTITUTE))
        # hitmonchan rapidspin vs goodra on a crit: best guess calc = 27
        self.assertEqual(sub.hp, (self.goodra.max_hp / 4) - 18 - 27)

        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|move|p1a: Zekrom|Outrage|p2a: Goodra')
        self.handle('|-activate|p2a: Goodra|Substitute|[damage]')
        # somehow it didn't break goodra's sub

        self.assertTrue(self.goodra.has_effect(Volatile.SUBSTITUTE))
        self.assertEqual(sub.hp, 1)

    def test_handle_start_end_yawn(self):
        self.handle('|-start|p1a: Hitmonchan|move: Yawn|[of] p2a: Goodra')
        self.handle('|turn|2')
        self.assertTrue(self.hitmonchan.has_effect(Volatile.YAWN))
        self.assertEqual(self.hitmonchan.get_effect(Volatile.YAWN).duration, 1)

        self.handle('|-end|p1a: Hitmonchan|move: Yawn|[silent]')
        self.handle('|turn|3')
        self.assertFalse(self.hitmonchan.has_effect(Volatile.YAWN))

        self.handle('|-start|p1a: Hitmonchan|move: Yawn|[of] p2a: Goodra')
        self.handle('|turn|4')
        self.bc.engine.run_turn()

        self.assertEqual(self.hitmonchan.status, Status.SLP)
        self.assertFalse(self.hitmonchan.has_effect(Volatile.YAWN))

    def test_handle_start_end_leechseed(self):
        self.handle('|-start|p2a: Goodra|move: Leech Seed')
        self.assertTrue(self.goodra.has_effect(Volatile.LEECHSEED))
        self.assertIn(self.goodra.get_effect(Volatile.LEECHSEED).on_residual,
                      self.goodra.effect_handlers['on_residual'])

        self.handle('|-end|p2a: Goodra|Leech Seed|[from] move: Rapid Spin|[of] p2a: Goodra')
        self.assertFalse(self.goodra.has_effect(Volatile.LEECHSEED))
        self.assertListEqual(self.goodra.effect_handlers['on_residual'], [])

    def test_handle_start_end_encore(self):
        self.handle('|switch|p2a: Accelgor|Accelgor, L79, M|100/100')
        self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2a: Goodra')
        self.handle('|move|p2a: Accelgor|Encore|p1a: Hitmonchan')
        self.handle('|-start|p1a: Hitmonchan|Encore')
        self.assertTrue(self.hitmonchan.has_effect(Volatile.ENCORE))
        encore = self.hitmonchan.get_effect(Volatile.ENCORE)
        self.assertEqual(encore.move, movedex['rapidspin'])
        self.assertEqual(encore.duration, 4)

        self.handle('|turn|2')
        self.assertEqual(encore.duration, 3)

        self.handle('|-end|p1a: Hitmonchan|Encore')
        self.assertFalse(self.hitmonchan.has_effect(Volatile.ENCORE))

    def test_handle_start_perish(self):
        self.handle('|switch|p2a: Dewgong|Dewgong, L83, M|100/100')
        self.handle('|move|p2a: Dewgong|Perish Song|p2a: Dewgong')
        self.handle('|-start|p1a: Hitmonchan|perish3|[silent]')
        self.handle('|-start|p2a: Dewgong|perish3|[silent]')
        # self.handle('|-fieldactivate|move: Perish Song')
        self.handle('|-start|p1a: Hitmonchan|perish3')
        self.handle('|-start|p2a: Dewgong|perish3')
        self.handle('|turn|2')

        dewgong = self.foe_side.active_pokemon
        hperish = self.hitmonchan.get_effect(Volatile.PERISHSONG)
        gperish = dewgong.get_effect(Volatile.PERISHSONG)
        self.assertIsNotNone(hperish)
        self.assertIsNotNone(gperish)
        self.assertEqual(hperish.duration, 3)
        self.assertEqual(gperish.duration, 3)

        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|-start|p2a: Dewgong|perish2')
        self.handle('|turn|3')

        self.assertFalse(self.hitmonchan.has_effect(Volatile.PERISHSONG))
        self.assertFalse(self.my_side.active_pokemon.has_effect(Volatile.PERISHSONG))
        self.assertTrue(dewgong.has_effect(Volatile.PERISHSONG))
        self.assertEqual(gperish.duration, 2)

        self.handle('|-start|p2a: Dewgong|perish0')
        self.handle('|faint|p2a: Dewgong')
        self.handle('|turn|4')

        self.assertEqual(dewgong.status, Status.FNT)

    def test_handle_start_typechange(self):
        self.handle('|switch|p2a: Greninja|Greninja, L74, F|100/100')
        self.handle('|move|p2a: Greninja|Dark Pulse|p1a: Hitmonchan')
        self.handle('|-start|p2a: Greninja|typechange|Dark|[from] Protean')
        self.handle('|turn|2')

        greninja = self.foe_side.active_pokemon
        self.assertListEqual(greninja.types, [Type.DARK, None])

        self.handle('|move|p2a: Greninja|Ice Beam|p1a: Hitmonchan')
        self.handle('|-start|p2a: Greninja|typechange|Ice|[from] Protean')
        self.handle('|turn|3')

        self.assertListEqual(greninja.types, [Type.ICE, None])

        self.handle('|switch|p2a: Goodra|Goodra, L77, M|100/100')
        self.handle('|turn|4')
        self.handle('|switch|p2a: Greninja|Greninja, L74, F|100/100')
        self.handle('|turn|5')

        self.assertListEqual(greninja.types, [Type.WATER, Type.DARK])

    def test_handle_start_end_slowstart(self):
        self.handle('|switch|p2a: Regigigas|Regigigas, L83|100/100')
        self.handle('|-start|p2a: Regigigas|ability: Slow Start')
        self.handle('|turn|2')

        regigigas = self.foe_side.active_pokemon
        slowstart = regigigas.get_effect(Volatile.SLOWSTART)
        self.assertIsNotNone(slowstart)
        self.assertEqual(slowstart.duration, 4)

        self.handle('|turn|3')
        self.assertEqual(slowstart.duration, 3)

        self.handle('|-end|p2a: Regigigas|Slow Start|[silent]')
        self.assertFalse(regigigas.has_effect(Volatile.SLOWSTART))

    def test_handle_start_end_flashfire(self):
        self.handle('|switch|p2a: Heatmor|Heatmor, L83, F|100/100')
        self.handle('|-start|p2a: Heatmor|ability: Flash Fire')
        self.handle('|turn|2')

        heatmor = self.foe_side.active_pokemon
        self.assertTrue(heatmor.has_effect(Volatile.FLASHFIRE))
        self.assertEqual(heatmor.ability, abilitydex['flashfire'])

        self.handle('|switch|p2a: Goodra|Goodra, L77, M|100/100')
        self.handle('|turn|3')
        self.handle('|switch|p2a: Heatmor|Heatmor, L83, F|100/100')
        self.handle('|turn|4')

        self.assertFalse(heatmor.has_effect(Volatile.FLASHFIRE))
        self.assertEqual(heatmor.ability, abilitydex['flashfire'])

        self.handle('|-start|p2a: Heatmor|ability: Flash Fire')
        self.handle('|-end|p2a: Heatmor|ability: Flash Fire|[silent]')

        self.assertFalse(heatmor.has_effect(Volatile.FLASHFIRE))

    def test_handle_start_end_disable(self):
        self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2a: Goodra')
        self.handle('|-start|p1a: Hitmonchan|Disable|Rapid Spin')
        self.handle('|turn|2')

        disable = self.hitmonchan.get_effect(Volatile.DISABLE)
        self.assertIsNotNone(disable)
        self.assertEqual(disable.duration, 4)
        self.assertEqual(disable.move, movedex['rapidspin'])

        self.handle('|-end|p1a: Hitmonchan|Disable')
        self.handle('|turn|3')
        self.assertFalse(self.hitmonchan.has_effect(Volatile.DISABLE))

        self.handle('|-start|p1a: Hitmonchan|Disable|Rapid Spin')
        self.handle('|move|p1a: Hitmonchan|Mach Punch|p2a: Goodra')
        self.handle('|turn|4')

        self.assertEqual(self.hitmonchan.get_effect(Volatile.DISABLE).duration, 3)

    def test_handle_start_end_attract(self):
        self.handle('|switch|p2a: Lopunny|Lopunny, L75, F|100/100')
        self.handle('|-start|p1a: Hitmonchan|Attract|[from] ability: Cute Charm|[of] p2a: Lopunny')

        lopunny = self.foe_side.active_pokemon
        attract = self.hitmonchan.get_effect(Volatile.ATTRACT)
        self.assertIsNotNone(attract)
        self.assertEqual(attract.mate, lopunny)

        self.handle('|-end|p1a: Hitmonchan|Attract|[silent]')
        self.assertFalse(self.hitmonchan.has_effect(Volatile.ATTRACT))

    def test_handle_start_end_magnetrise(self):
        self.handle('|-start|p1a: Hitmonchan|Magnet Rise')
        self.assertTrue(self.hitmonchan.is_immune_to(Type.GROUND))

        self.handle('|-end|p1a: Hitmonchan|Magnet Rise')
        self.assertFalse(self.hitmonchan.is_immune_to(Type.GROUND))

    def test_handle_activate_end_infestation(self):
        self.handle('|-activate|p1a: Hitmonchan|move: Infestation|[of] p2a: Goodra')
        self.handle('|turn|2')

        ptrap = self.hitmonchan.get_effect(Volatile.PARTIALTRAP)
        self.assertIsNotNone(ptrap)
        self.assertEqual(ptrap.duration, 5)

        self.handle('|-end|p1a: Hitmonchan|Infestation|[partiallytrapped]')

        self.assertFalse(self.hitmonchan.has_effect(Volatile.PARTIALTRAP))

        self.handle('|-activate|p1a: Hitmonchan|move: Infestation|[of] p2a: Goodra')
        self.handle('|turn|3')
        self.handle('|switch|p2a: Lilligant|Lilligant, L81, F|100/100')
        self.handle('|turn|4')

        self.assertFalse(self.hitmonchan.has_effect(Volatile.PARTIALTRAP))

    def test_handle_move_lockedmove(self):
        self.handle('|switch|p2a: Lilligant|Lilligant, L81, F|100/100')
        self.handle('|move|p2a: Lilligant|Petal Dance|p1a: Hitmonchan')
        self.handle('|turn|2')

        lilligant = self.foe_side.active_pokemon
        lockedmove = lilligant.get_effect(Volatile.LOCKEDMOVE)
        self.assertIsNotNone(lockedmove)
        self.assertEqual(lockedmove.move, movedex['petaldance'])
        self.assertTrue(lockedmove.duration, 2)

        self.handle('|move|p2a: Lilligant|Petal Dance|p1a: Hitmonchan|[from]lockedmove')
        self.handle('|turn|3')
        self.assertTrue(lockedmove.duration, 1)
        self.assertEqual(lilligant.pp[movedex['petaldance']], 16 - 1)

        self.handle('|move|p2a: Lilligant|Petal Dance|p1a: Hitmonchan|[from]lockedmove')
        self.handle('|-immune|p2a: Lilligant|confusion')
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|turn|4')

        self.assertFalse(lilligant.has_effect(Volatile.LOCKEDMOVE))

        zekrom = self.my_side.active_pokemon
        self.handle('|move|p1a: Zekrom|Outrage|p2a: Lilligant')
        self.assertTrue(zekrom.has_effect(Volatile.LOCKEDMOVE))
        self.handle('|turn|5')
        self.handle('|move|p1a: Zekrom|Outrage|p2a: Lilligant')
        self.handle('|-start|p1a: Zekrom|confusion|[fatigue]')
        self.handle('|turn|6')

        self.assertFalse(zekrom.has_effect(Volatile.LOCKEDMOVE))

    def test_handle_activate_mummy(self):
        self.handle('|switch|p1a: Giratina|Giratina-Origin, L73|339/339')
        self.handle('|switch|p2a: Lilligant|Lilligant, L81, F|100/100')
        lilligant = self.foe_side.active_pokemon

        self.handle('|-activate|p1a: Giratina|ability: Mummy|Chlorophyll|[of] p2a: Lilligant')

        self.assertEqual(lilligant.base_ability, abilitydex['chlorophyll']) # revealed chlorophyll
        self.assertEqual(lilligant.ability, abilitydex['mummy'])            # then changed to mummy
        self.assertEqual(lilligant.get_effect(ABILITY).name, 'mummy')

        self.handle('|drag|p2a: Goodra|Goodra, L77, M|100/100')
        self.handle('|turn|2')
        self.handle('|switch|p2a: Lilligant|Lilligant, L81, F|100/100')

        self.assertEqual(lilligant.base_ability, abilitydex['chlorophyll'])
        self.assertEqual(lilligant.ability, abilitydex['chlorophyll'])
        self.assertEqual(lilligant.get_effect(ABILITY).name, 'chlorophyll')

    def test_handle_activate_revealed_ability(self):
        self.handle('|switch|p2a: Arbok|Arbok, L83, M|100/100')
        arbok = self.foe_side.active_pokemon

        self.handle('|-activate|p2a: Arbok|ability: Shed Skin')

        self.assertEqual(arbok.ability, abilitydex['shedskin'])
        self.assertEqual(arbok.base_ability, abilitydex['shedskin'])

    def test_handle_singleturn_protect(self):
        self.handle('|switch|p2a: Alomomola|Alomomola, L79, M|100/100')
        self.handle('|move|p2a: Alomomola|Protect|p2a: Alomomola')
        self.handle('|-singleturn|p2a: Alomomola|Protect')
        self.handle('|turn|2')

        alomomola = self.foe_side.active_pokemon
        stall = alomomola.get_effect(Volatile.STALL)
        self.assertIsNotNone(stall)
        self.assertEqual(stall.duration, 1)
        self.assertEqual(stall.denominator, 3)

        self.handle('|move|p2a: Alomomola|Protect|p2a: Alomomola')
        self.handle('|-singleturn|p2a: Alomomola|Protect')
        self.handle('|turn|3')

        self.assertEqual(stall.duration, 1)
        self.assertEqual(stall.denominator, 9)

        alomomola.moves.clear() # clear its moveset so that it doesn't try use protect again
        self.hitmonchan.moves = {movedex['machpunch']: 5}
        self.bc.engine.run_turn()

        self.assertFalse(alomomola.has_effect(Volatile.STALL))

        self.handle('|move|p2a: Alomomola|Protect|p2a: Alomomola')
        self.handle('|-singleturn|p2a: Alomomola|Protect')
        self.handle('|turn|5')
        self.handle('|turn|6')

        self.assertFalse(alomomola.has_effect(Volatile.STALL))

    def test_handle_singleturn_focuspunch(self):
        self.handle('|-singleturn|p2a: Goodra|move: Focus Punch')
        self.handle('|cant|p2a: Goodra|Focus Punch|Focus Punch')

        focuspunch = movedex['focuspunch']
        self.assertTrue(focuspunch in self.goodra.moves)
        self.assertEqual(self.goodra.pp[focuspunch], focuspunch.max_pp)

    def test_handle_singlemove_destinybond(self):
        self.handle('|-singlemove|p2a: Goodra|Destiny Bond')
        self.handle('|turn|2')

        self.assertTrue(self.goodra.has_effect(Volatile.DESTINYBOND))

    def test_handle_sidestart_sideend_screens(self):
        self.handle('|switch|p2a: Bronzong|Bronzong, L79|100/100')
        self.handle('|-item|p2a: Bronzong|Light Clay|[from] ability: Frisk|[of] p1a: Hitmonchan|[identify]')
        self.handle('|-sidestart|p1: test-BillsPC|Reflect')
        self.handle('|-sidestart|p2: other-player|move: Light Screen')
        self.handle('|turn|2')

        reflect = self.my_side.get_effect(SideCondition.REFLECT)
        self.assertIsNotNone(reflect)
        self.assertEqual(reflect.duration, 4)

        self.assertEqual(self.foe_side.get_effect(SideCondition.LIGHTSCREEN).duration, 7)

        self.handle('|-sideend|p1: test-BillsPC|Reflect')
        self.handle('|turn|3')

        self.assertFalse(self.my_side.has_effect(SideCondition.REFLECT))

    def test_handle_sidestart_sideend_hazards(self):
        self.handle('|-sidestart|p1: test-BillsPC|move: Stealth Rock')
        self.handle('|-sidestart|p2: other-player|Spikes')
        self.handle('|turn|2')

        self.assertTrue(self.my_side.has_effect(Hazard.STEALTHROCK))
        spikes = self.foe_side.get_effect(Hazard.SPIKES)
        self.assertIsNotNone(spikes)
        self.assertEqual(spikes.layers, 1)

        self.handle('|-sidestart|p1: test-BillsPC|move: Toxic Spikes')
        self.handle('|-sidestart|p2: other-player|Spikes')
        self.handle('|turn|3')

        toxicspikes = self.my_side.get_effect(Hazard.TOXICSPIKES)
        self.assertIsNotNone(toxicspikes)
        self.assertEqual(toxicspikes.layers, 1)
        self.assertEqual(spikes.layers, 2)

        self.handle('|-sidestart|p1: test-BillsPC|move: Toxic Spikes')
        self.handle('|-sidestart|p2: other-player|Spikes')
        self.handle('|turn|4')

        self.assertEqual(toxicspikes.layers, 2)
        self.assertEqual(spikes.layers, 3)

        self.handle('|-sideend|p1: test-BillsPC|move: Toxic Spikes')
        self.handle('|-sideend|p1: test-BillsPC|move: Stealth Rock')
        self.handle('|-sidestart|p2: other-player|Sticky Web')
        self.handle('|turn|5')

        self.assertFalse(self.my_side.has_effect(Hazard.TOXICSPIKES))
        self.assertFalse(self.my_side.has_effect(Hazard.STEALTHROCK))
        self.assertTrue(self.foe_side.has_effect(Hazard.STICKYWEB))

    def test_handle_sidestart_sideend_tailwind(self):
        self.handle('|-sidestart|p1: test-BillsPC|move: Tailwind')
        self.handle('|turn|2')

        self.assertTrue(self.my_side.has_effect(SideCondition.TAILWIND))
        self.assertEqual(self.my_side.get_effect(SideCondition.TAILWIND).duration, 3)

        self.handle('|-sideend|p1: test-BillsPC|move: Tailwind')
        self.handle('|turn|3')

        self.assertFalse(self.my_side.has_effect(SideCondition.TAILWIND))

    def test_handle_sidestart_sideend_safeguard(self):
        self.handle('|-sidestart|p1: test-BillsPC|move: Safeguard')
        self.handle('|turn|2')

        self.assertTrue(self.my_side.has_effect(SideCondition.SAFEGUARD))
        self.assertEqual(self.my_side.get_effect(SideCondition.SAFEGUARD).duration, 4)

        self.handle('|-sideend|p1: test-BillsPC|move: Safeguard')
        self.handle('|turn|3')

        self.assertFalse(self.my_side.has_effect(SideCondition.SAFEGUARD))

    def test_handle_fieldstart_fieldend_trickroom(self):
        self.handle('|-fieldstart|move: Trick Room|[of] p2a: Goodra')
        self.handle('|turn|2')

        self.assertTrue(self.battlefield.has_effect(PseudoWeather.TRICKROOM))
        self.assertEqual(self.battlefield.get_effect(PseudoWeather.TRICKROOM).duration, 4)

        self.handle('|-fieldend|move: Trick Room|[of] p2a: Goodra')
        self.handle('|turn|3')

        self.assertFalse(self.battlefield.has_effect(PseudoWeather.TRICKROOM))

    def test_handle_formechange(self):
        self.handle('|switch|p2a: Aegislash|Aegislash, L74, F|100/100')
        self.handle('|turn|2')
        self.handle('|-formechange|p2a: Aegislash|Aegislash-Blade|[from] ability: Stance Change')
        self.handle('|move|p2a: Aegislash|Shadow Sneak|p1a: Chimecho')
        self.handle('|turn|3')

        aegislash = self.foe_side.active_pokemon
        self.assertEqual(aegislash.stats['atk'], 265)
        self.assertEqual(aegislash.name, 'aegislashblade')

        self.handle('|-formechange|p2a: Aegislash|Aegislash|[from] ability: Stance Change')
        self.handle('|move|p2a: Aegislash|King\'s Shield|p1a: Chimecho')
        self.handle('|turn|4')

        self.assertEqual(aegislash.stats['atk'], 117)
        self.assertEqual(aegislash.name, 'aegislash')

    def test_handle_detailschange_mega(self):
        self.handle('|drag|p2a: Venusaur|Venusaur, L75, M|100/100')
        self.handle('|turn|2')
        self.handle('|detailschange|p2a: Venusaur|Venusaur-Mega, L75, M')
        self.handle('|-mega|p2a: Venusaur|Venusaur|Venusaurite')
        self.handle('|turn|3')

        venusaur = self.foe_side.active_pokemon
        self.assertEqual(venusaur.name, 'venusaurmega')
        self.assertEqual(venusaur.ability, abilitydex['thickfat'])
        self.assertEqual(venusaur.stats['spa'], 227)
        self.assertEqual(venusaur.item, itemdex['venusaurite'])
        self.assertTrue(venusaur.is_mega)
        self.assertTrue(self.foe_side.has_mega_evolved)

    def test_handle_detailschange_primal(self):
        self.handle('|switch|p2a: Kyogre|Kyogre, L73|100/100')
        self.handle('|detailschange|p2a: Kyogre|Kyogre-Primal, L73')

        kyogre = self.foe_side.active_pokemon
        self.assertEqual(kyogre.name, 'kyogreprimal')
        self.assertEqual(kyogre.ability, abilitydex['primordialsea'])
        self.assertEqual(kyogre.stats['spa'], 305)
        self.assertEqual(kyogre.item, itemdex['blueorb'])
        self.assertFalse(kyogre.is_mega)
        self.assertFalse(self.foe_side.has_mega_evolved)

    def test_deduce_foe_hiddenpower_when_one_possibility(self):
        self.handle('|drag|p2a: Virizion|Virizion, L79|100/100')
        self.handle('|move|p2a: Virizion|Hidden Power|p1a: Hitmonchan')
        self.handle('|turn|2')

        virizion = self.foe_side.active_pokemon
        self.assertIn(movedex['hiddenpowerice'], virizion.moves)

    def test_deduce_foe_hiddenpower_multiple_possibilities(self):
        # deduce from resisted
        self.handle('|switch|p2a: Cherrim|Cherrim, L83, M|100/100')
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|turn|2')
        self.handle('|move|p2a: Cherrim|Hidden Power|p1a: Hitmonchan')
        self.handle('|-resisted|p1a: Zekrom')
        self.handle('|turn|3')
        cherrim = self.foe_side.active_pokemon
        self.assertHiddenPowerType(cherrim, Type.FIRE)

        # deduce from supereffective
        self.handle('|switch|p2a: Floette|Floette-Eternal, L75, F|100/100')
        self.handle('|move|p2a: Floette|Hidden Power|p1a: Hitmonchan')
        self.handle('|-supereffective|p1a: Zekrom')
        self.handle('|turn|4')
        floette = self.foe_side.active_pokemon
        self.assertHiddenPowerType(floette, Type.GROUND)

        # deduce from immunity
        self.handle('|switch|p2a: Gothitelle|Gothitelle, L74, M|100/100')
        self.handle('|switch|p1a: Giratina|Giratina-Origin, L73|339/339')
        self.handle('|move|p2a: Gothitelle|Hidden Power|p1a: Giratina')
        self.handle('|-immune|p1a: Giratina|[msg]')
        self.handle('|turn|5')
        gothitelle = self.foe_side.active_pokemon
        self.assertHiddenPowerType(gothitelle, Type.FIGHTING)

        # deduce from normal damage
        self.handle('|switch|p2a: Thundurus|Thundurus-Therian, L76, M|100/100')
        self.handle('|move|p2a: Thundurus|Hidden Power|p1a: Giratina')
        self.handle('|-damage|p1a: Giratina|300/339')
        self.handle('|turn|6')
        thundurus = self.foe_side.active_pokemon
        self.assertHiddenPowerType(thundurus, Type.FLYING)

        # deduce ground from airballoon immunity
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')
        self.handle('|-item|p1a: Hitmonchan|Air Balloon')
        self.handle('|switch|p2a: Volcarona|Volcarona, L76, M|100/100')
        self.handle('|move|p2a: Volcarona|Hidden Power|p1a: Hitmonchan')
        self.handle('|-immune|p1a: Hitmonchan|[msg]')
        volcarona = self.foe_side.active_pokemon
        self.assertHiddenPowerType(volcarona, Type.GROUND)

    def test_foe_hiddenpower_multiple_possibilities_nondeduction(self):
        # undecidable
        self.handle('|switch|p2a: Cherrim|Cherrim, L83, M|100/100')
        self.handle('|move|p2a: Cherrim|Hidden Power|p1a: Hitmonchan')
        self.handle('|-damage|p1a: Hitmonchan|150/209')
        self.handle('|turn|2')
        cherrim = self.foe_side.active_pokemon
        self.assertHiddenPowerType(cherrim, Type.NOTYPE)

        # can still decide it later
        self.handle('|switch|p1a: Giratina|Giratina-Origin, L73|339/339')
        self.handle('|move|p2a: Cherrim|Hidden Power|p1a: Giratina')
        self.handle('|-supereffective|p1a: Giratina')
        self.handle('|turn|3')
        self.assertHiddenPowerType(cherrim, Type.ICE)

        # a miss is undecidable
        self.handle('|switch|p2a: Thundurus|Thundurus-Therian, L76, M|100/100')
        self.handle('|move|p2a: Thundurus|Hidden Power|p1a: Giratina')
        self.handle('|-miss|p2a: Thundurus|p1a: Giratina')
        self.handle('|turn|4')
        thundurus = self.foe_side.active_pokemon
        self.assertHiddenPowerType(thundurus, Type.NOTYPE)

    def test_foe_hiddenpower_multiple_possibilities_other_effects(self):
        # primordial sea
        self.handle('|switch|p2a: Gothitelle|Gothitelle, L74, M|100/100')
        self.handle('|move|p2a: Gothitelle|Hidden Power|p1a: Hitmonchan')
        self.handle('|-fail|p1a: Hitmonchan|Hidden Power|[from] Primordial Sea')
        self.handle('|turn|2')
        gothitelle = self.foe_side.active_pokemon
        self.assertHiddenPowerType(gothitelle, Type.FIRE)

        # flash fire
        self.handle('|switch|p2a: Cherrim|Cherrim, L83, M|100/100')
        self.handle('|-ability|p1a: Hitmonchan|Flash Fire')
        self.handle('|move|p2a: Cherrim|Hidden Power|p1a: Hitmonchan')
        self.handle('|-immune|p1a: Hitmonchan|[msg]|[from] ability: Flash Fire')
        self.handle('|turn|3')
        cherrim = self.foe_side.active_pokemon
        self.assertHiddenPowerType(cherrim, Type.FIRE)

        # volt absorb
        self.handle('|switch|p2a: Keldeo|Keldeo, L75|100/100')
        self.handle('|-ability|p1a: Hitmonchan|Volt Absorb')
        self.handle('|move|p2a: Keldeo|Hidden Power|p1a: Hitmonchan')
        self.handle('|-heal|p1a: Hitmonchan|209/209|[from] ability: Volt Absorb|[of] p2a: Keldeo')
        self.handle('|turn|4')
        keldeo = self.foe_side.active_pokemon
        self.assertHiddenPowerType(keldeo, Type.ELECTRIC)

        # hack in a shedinja for this test:
        shedinja = self.bc.my_pokemon_from_json(json.loads('{"ident":"p2: Shedinja","details":"Shedinja, L83","condition":"1/1","active":false,"stats":{"atk":197,"def":122,"spa":97,"spd":97,"spe":114},"moves":["swordsdance","batonpass","willowisp","xscissor"],"baseAbility":"wonderguard","item":"focussash","pokeball":"pokeball"}'))
        shedinja.side = self.my_side
        # replace zekrom with shedinja on the bench:
        self.my_side.team[1] = shedinja

        # wonder guard
        self.handle('|switch|p1a: Shedinja|Shedinja|1/1')
        self.handle('|switch|p2a: Floette|Floette-Eternal, L75, F|100/100')
        self.handle('|move|p2a: Floette|Hidden Power|p1a: Shedinja')
        self.handle('|-activate|p1a: Shedinja|ability: Wonder Guard')
        self.handle('|turn|5')
        floette = self.foe_side.active_pokemon
        self.assertHiddenPowerType(floette, Type.GROUND)

        self.handle('|switch|p2a: Thundurus|Thundurus-Therian, L76, M|100/100')
        self.handle('|switch|p1a: Altaria|Altaria, L75, M|236/236')
        self.handle('|move|p2a: Thundurus|Hidden Power|p1a: Altaria')
        self.handle('|-activate||deltastream')
        self.handle('|turn|6')
        thundurus = self.foe_side.active_pokemon
        self.assertHiddenPowerType(thundurus, Type.ICE)

    def test_cant_reveals_move(self):
        self.handle('|switch|p2a: Azelf|Azelf, L77|100/100')
        self.handle('|switch|p1a: Giratina|Giratina-Origin, L73|339/339')
        self.handle('|turn|2')
        self.handle('|move|p1a: Giratina|Taunt|p2a: Azelf')
        self.handle('|-start|p2a: Azelf|move: Taunt')
        self.handle('|cant|p2a: Azelf|move: Taunt|Taunt')
        self.handle('|turn|3')

        self.assertIn(movedex['taunt'], self.foe_side.active_pokemon.moves)

    def test_heal_reveals_item_ability(self):
        self.handle('|switch|p2a: Blastoise|Blastoise, L79, M|100/100')
        self.handle('|-heal|p2a: Blastoise|100/100|[from] ability: Rain Dish')
        self.handle('|-heal|p2a: Blastoise|100/100|[from] item: Leftovers')
        self.handle('|turn|2')

        blastoise = self.foe_side.active_pokemon
        self.assertEqual(blastoise.ability, abilitydex['raindish'])
        self.assertEqual(blastoise.item, itemdex['leftovers'])

    def test_status_reveals_item_ability(self):
        self.handle('|switch|p2a: Electrode|Electrode, L83|100/100')
        self.handle('|-status|p1a: Hitmonchan|par|[from] ability: Static|[of] p2a: Electrode')
        self.handle('|turn|2')

        electrode = self.foe_side.active_pokemon
        self.assertEqual(electrode.ability, abilitydex['static'])
        self.assertEqual(self.hitmonchan.status, Status.PAR)

        self.handle('|drag|p2a: Throh|Throh, L82, M|100/100')
        self.handle('|-status|p2a: Throh|tox|[from] item: Toxic Orb')

        throh = self.foe_side.active_pokemon
        self.assertEqual(throh.item, itemdex['toxicorb'])

    def test_damage_reveals_item_ability(self):
        self.handle('|switch|p2a: Electrode|Electrode, L83|100/100')
        self.handle('|-damage|p2a: Electrode|90/100|[from] item: Life Orb')
        self.handle('|-damage|p1a: Hitmonchan|100/209|[from] item: Black Sludge')
        self.handle('|-damage|p1a: Hitmonchan|35/209|[from] ability: Aftermath|[of] p2a: Electrode')
        self.handle('|turn|2')

        electrode = self.foe_side.active_pokemon
        self.assertEqual(electrode.ability, abilitydex['aftermath'])
        self.assertEqual(electrode.item, itemdex['lifeorb'])
        self.assertEqual(self.hitmonchan.item, itemdex['blacksludge'])
        self.assertEqual(self.hitmonchan.hp, 35)

    def test_client_turns_out(self):
        self.assertEqual(self.hitmonchan.turns_out, 1)
        self.assertEqual(self.goodra.turns_out, 1)
        self.handle('|turn|2')
        self.assertEqual(self.hitmonchan.turns_out, 2)
        self.assertEqual(self.goodra.turns_out, 2)

        self.handle('|switch|p2a: Electrode|Electrode, L83|100/100')
        self.handle('|turn|3')

        electrode = self.foe_side.active_pokemon
        self.assertEqual(self.hitmonchan.turns_out, 3)
        self.assertEqual(electrode.turns_out, 1)

    def test_enditem_sets_unburden(self):
        self.handle('|switch|p2a: Hawlucha|Hawlucha, L76, M|100/100')
        self.handle('|-ability|p2a: Hawlucha|Unburden')
        self.handle('|turn|2')
        self.handle('|-enditem|p2a: Hawlucha|Flying Gem|[from] gem|[move] Acrobatics')
        self.handle('|turn|3')

        hawlucha = self.foe_side.active_pokemon
        self.assertTrue(hawlucha.has_effect(Volatile.UNBURDEN))

    def test_fail_reveals_ability(self):
        self.handle('|-fail|p1a: Hitmonchan')
        self.handle('|-fail|p2a: Goodra|move: Substitute|[weak]')
        self.handle('|turn|2')
        self.handle('|switch|p2a: Kingler|Kingler, L83, F|100/100')
        self.handle('|-fail|p2a: Kingler|unboost|Attack|[from] ability: Hyper Cutter|[of] p2a: Kingler')
        self.handle('|turn|3')

        kingler = self.foe_side.active_pokemon
        self.assertEqual(kingler.ability, abilitydex['hypercutter'])

        self.handle('|-fail|p2a: Kingler|unboost|[from] ability: Clear Body|[of] p2a: Kingler')
        self.assertEqual(kingler.ability, abilitydex['clearbody'])

    def test_immune_reveals_ability(self):
        self.handle('|switch|p2a: Lanturn|Lanturn, L81, M|100/100')
        self.handle('|-immune|p2a: Lanturn|[msg]|[from] ability: Water Absorb')
        self.handle('|turn|2')

        lanturn = self.foe_side.active_pokemon
        self.assertEqual(lanturn.ability, abilitydex['waterabsorb'])

        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|drag|p2a: Beheeyem|Beheeyem, L83|100/100')
        self.handle('|-immune|p1a: Zekrom|[msg]|[from] ability: Synchronize|[of] p2a: Beheeyem')

        beheeyem = self.foe_side.active_pokemon
        self.assertEqual(beheeyem.ability, abilitydex['synchronize'])

    def test_handle_move_notarget(self):
        self.handle('|switch|p2a: Talonflame|Talonflame, L75, F|100/100')
        self.handle('|move|p2a: Talonflame|Brave Bird|p1a: Samurott')
        self.handle('|-damage|p1a: Hitmonchan|100/209')
        self.handle('|-damage|p2a: Talonflame|0 fnt|[from] recoil|[of] p1a: Hitmonchan')
        self.handle('|faint|p2a: Talonflame')
        self.handle('|move|p1a: Hitmonchan|Rapid Spin|p2: Talonflame|[notarget]')
        # |notarget
        self.handle('|switch|p2a: Trevenant|Trevenant, L79, M|100/100')
        self.handle('|turn|2')

        self.assertEqual(self.hitmonchan.pp[movedex['rapidspin']],
                         movedex['rapidspin'].max_pp - 1)

    def test_handle_curestatus_reveals_ability(self):
        self.handle('|switch|p2a: Corsola|Corsola, L83, M|100/100')
        self.handle('|-status|p2a: Corsola|tox')
        self.handle('|-curestatus|p2a: Corsola|tox|[from] ability: Natural Cure')

        corsola = self.foe_side.active_pokemon
        self.assertEqual(corsola.ability, abilitydex['naturalcure'])

    def test_handle_item_reveals_ability(self):
        self.handle('|switch|p2a: Weavile|Weavile, L75, F|100/100')
        self.handle('|-item|p2a: Weavile|Assault Vest|[from] ability: Pickpocket|[of] p1a: Hitmonchan')
        self.handle('|turn|2')

        weavile = self.foe_side.active_pokemon
        self.assertEqual(weavile.item, itemdex['assaultvest'])
        self.assertIsNone(self.hitmonchan.item)
        self.assertFalse(self.hitmonchan.has_effect(ITEM))

        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|switch|p2a: Dusknoir|Dusknoir, L83, F|100/100')
        self.handle('|-item|p1a: Zekrom|Choice Scarf|[from] ability: Frisk|[of] p2a: Dusknoir|[identify]')
        self.handle('|turn|3')

        zekrom = self.my_side.active_pokemon
        dusknoir = self.foe_side.active_pokemon
        self.assertEqual(dusknoir.ability, abilitydex['frisk'])
        self.assertEqual(zekrom.item, itemdex['choicescarf'])

    def test_deduce_foe_moves_when_only_one_moveset(self):
        self.handle('|switch|p2a: Linoone|Linoone, L82, F|100/100')

        linoone = self.foe_side.active_pokemon
        self.assertSetEqual(set(linoone.moves),
                            {movedex['shadowclaw'], movedex['bellydrum'],
                             movedex['extremespeed'], movedex['seedbomb']})

        self.handle('|switch|p2a: Sunflora|Sunflora, L83, F|100/100')
        sunflora = self.foe_side.active_pokemon
        self.assertSetEqual(set(sunflora.moves),
                            {movedex['sunnyday'], movedex['hiddenpowerfire'],
                             movedex['earthpower']})

    def test_deduce_foe_ability_when_only_one_possibility(self):
        self.handle('|switch|p2a: Mandibuzz|Mandibuzz, L77, F|100/100')

        mandibuzz = self.foe_side.active_pokemon
        self.assertEqual(mandibuzz.ability, abilitydex['overcoat'])

    def test_deduce_foe_item_when_only_one_moveset(self):
        self.handle('|switch|p2a: Chansey|Chansey, L75, F|100/100')

        chansey = self.foe_side.active_pokemon
        self.assertEqual(chansey.item, itemdex['eviolite'])

    def test_original_item_set(self):
        self.handle('|drag|p2a: Zapdos|Zapdos, L77|100/100')
        self.handle('|turn|2')
        zapdos = self.foe_side.active_pokemon
        self.assertEqual(zapdos.original_item, itemdex['_unrevealed_'])
        self.handle('|-heal|p2a: Zapdos|66/100|[from] item: Leftovers')
        self.handle('|turn|3')
        self.assertEqual(zapdos.original_item, itemdex['leftovers'])

        self.handle('|switch|p2a: Ampharos|Ampharos, L83, M|100/100')
        self.handle('|-item|p1a: Hitmonchan|Light Clay|[from] move: Trick')
        self.handle('|-item|p2a: Ampharos|Assault Vest|[from] move: Trick')
        self.handle('|turn|4')

        ampharos = self.foe_side.active_pokemon
        self.assertEqual(ampharos.original_item, itemdex['lightclay'])
        self.assertEqual(ampharos.item, itemdex['assaultvest'])

        self.handle('|switch|p2a: Ambipom|Ambipom, L79, M|100/100')
        self.handle('|-enditem|p2a: Ambipom|Choice Band|[from] move: Knock Off|[of] p1a: Hitmonchan')
        self.handle('|-item|p2a: Ambipom|Sitrus Berry|[from] ability: Pickup')
        self.handle('|turn|5')

        ambipom = self.foe_side.active_pokemon
        self.assertEqual(ambipom.original_item, itemdex['choiceband'])
        self.assertEqual(ambipom.item, itemdex['sitrusberry'])

        self.handle('|switch|p2a: Ferrothorn|Ferrothorn, L75, F|100/100')
        self.handle('|-item|p1a: Hitmonchan|Rocky Helmet|[from] ability: Pickpocket|[of] p2a: Ferrothorn')
        self.handle('|turn|6')

        ferrothorn = self.foe_side.active_pokemon
        self.assertEqual(ferrothorn.original_item, itemdex['rockyhelmet'])
        self.assertEqual(ferrothorn.item, None)

    def test_original_item_set_mega_primal(self):
        self.handle('|switch|p2a: Beedrill|Beedrill, L77, F|100/100')
        self.handle('|detailschange|p2a: Beedrill|Beedrill-Mega, L77, F')
        self.handle('|-mega|p2a: Beedrill|Beedrill|Beedrillite')
        self.handle('|turn|2')

        beedrill = self.foe_side.active_pokemon
        self.assertEqual(beedrill.original_item, itemdex['beedrillite'])

        self.handle('|switch|p2a: Kyogre|Kyogre, L73|100/100')
        self.handle('|detailschange|p2a: Kyogre|Kyogre-Primal, L73')
        self.handle('|turn|3')

        kyogre = self.foe_side.active_pokemon
        self.assertEqual(kyogre.original_item, itemdex['blueorb'])

    def test_update_foe_inferences(self):
        self.handle('|switch|p2a: Conkeldurr|Conkeldurr, L75, F|100/100')
        self.handle('|-status|p2a: Conkeldurr|brn|[from] item: Flame Orb')
        self.handle('|turn|2')

        conkeldurr = self.foe_side.active_pokemon
        self.assertEqual(conkeldurr.ability, abilitydex['guts']) # inferred from flameorb

        self.handle('|switch|p2a: Politoed|Politoed, L77, F|100/100')
        self.handle('|-item|p2a: Politoed|Chesto Berry|[from] ability: Frisk|[of] p1a: Hitmonchan|[identify]')
        self.handle('|turn|3')

        politoed = self.foe_side.active_pokemon
        self.assertIn(movedex['rest'], politoed.moves) # inferred from chestoberry

        self.handle('|switch|p2a: Barbaracle|Barbaracle, L81, F|100/100')
        self.handle('|cant|p2a: Barbaracle|move: Taunt|Shell Smash')
        self.handle('|turn|4')

        barbaracle = self.foe_side.active_pokemon
        self.assertEqual(barbaracle.original_item, itemdex['whiteherb'])
        self.assertEqual(barbaracle.item, itemdex['whiteherb'])

    def test_infer_info_from_level(self):
        self.handle('|switch|p2a: Xerneas|Xerneas, L71|100/100')
        self.handle('|turn|2')

        xerneas = self.foe_side.active_pokemon
        self.assertIn(movedex['geomancy'], xerneas.moves)
        self.assertEqual(xerneas.item, itemdex['powerherb'])

    def test_infer_megastone_from_level(self):
        self.handle('|switch|p2a: Ampharos|Ampharos, L77, F|100/100')
        self.handle('|turn|2')

        ampharos = self.foe_side.active_pokemon
        self.assertEqual(ampharos.item, itemdex['ampharosite'])

        self.handle('|switch|p2a: Blaziken|Blaziken, L77, F|100/100')
        self.handle('|turn|3')

        blaziken = self.foe_side.active_pokemon
        self.assertEqual(blaziken.item, itemdex['_unrevealed_'])

    def test_foe_transform(self):
        self.handle('|switch|p2a: Ditto|Ditto, L83|100/100')
        self.handle('|-damage|p2a: Ditto|87/100|[from] Stealth Rock')
        self.handle('|-transform|p2a: Ditto|p1a: Hitmonchan|[from] ability: Imposter')
        self.handle('|turn|2')

        ditto = self.foe_side.active_pokemon
        self.assertEqual(ditto.ability, abilitydex['ironfist'])
        self.assertEqual(ditto.base_ability, abilitydex['imposter'])
        self.assertEqual(ditto.item, itemdex['choicescarf'])
        self.assertIn(movedex['machpunch'], ditto.moves)
        self.assertIn(movedex['hiddenpowerdark'], ditto.moves)

        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|switch|p2a: Goodra|Goodra, L77, M|100/100')
        self.handle('|turn|3')
        self.assertFalse(ditto.is_transformed)
        self.assertListEqual(ditto.moves.keys(), [movedex['transform']])
        self.handle('|switch|p2a: Ditto|Ditto, L83|87/100')
        self.handle('|-transform|p2a: Ditto|p1a: Zekrom|[from] ability: Imposter')
        self.handle('|turn|4')

        self.assertTrue(ditto.is_transformed)
        self.assertSetEqual(set(ditto.moves), set(self.my_side.active_pokemon.moves))
        self.assertEqual(ditto.name, 'zekrom')

    def test_tox_stage_increases_each_turn(self):
        self.handle('|-status|p2a: Goodra|tox')
        self.handle('|-damage|p2a: Goodra|94/100 tox|[from] psn')
        self.handle('|turn|2')

        self.assertEqual(self.goodra.get_effect(Status.TOX).stage, 1)

        self.handle('|-damage|p2a: Goodra|82/100 tox|[from] psn')
        self.handle('|turn|3')

        self.assertEqual(self.goodra.get_effect(Status.TOX).stage, 2)

        self.handle('|switch|p2a: Ampharos|Ampharos, L77, F|100/100')
        self.handle('|turn|4')
        self.handle('|switch|p2a: Goodra|Goodra, L77, M|82/100 tox')
        self.handle('|-damage|p2a: Goodra|76/100 tox|[from] psn')
        self.handle('|turn|5')

        self.assertEqual(self.goodra.get_effect(Status.TOX).stage, 1)

    def test_choicelock(self):
        self.handle('|-item|p2a: Goodra|Choice Specs|[from] ability: Frisk|[of] p1a: Hitmonchan|[identify]')
        self.handle('|move|p2a: Goodra|Thunderbolt|p1a: Hitmonchan')
        self.handle('|turn|2')

        self.assertTrue(self.goodra.has_effect(Volatile.CHOICELOCK))
        self.assertEqual(self.goodra.get_effect(Volatile.CHOICELOCK).move, movedex['thunderbolt'])

        self.handle('|switch|p2a: Ampharos|Ampharos, L77, F|100/100')
        self.handle('|turn|3')
        self.handle('|switch|p2a: Goodra|Goodra, L77, M|100/100')
        self.handle('|turn|4')

        self.assertEqual(self.goodra.item, itemdex['choicespecs'])
        self.assertFalse(self.goodra.has_effect(Volatile.CHOICELOCK))

    def test_airlock_and_cloudnine(self):
        self.handle('|switch|p2a: Politoed|Politoed, L77, F|100/100')
        self.handle('|-weather|RainDance|[from] ability: Drizzle|[of] p2a: Politoed')
        self.handle('|turn|2')
        self.handle('|switch|p2a: Rayquaza|Rayquaza, L73|100/100')
        self.handle('|turn|3')

        self.assertTrue(self.battlefield._weather_suppressed)
        self.assertTrue(self.battlefield.get_effect(Weather.RAINDANCE).suppressed)

        self.handle('|switch|p2a: Politoed|Politoed, L77, F|100/100')
        self.handle('|turn|4')

        self.assertFalse(self.battlefield._weather_suppressed)
        self.assertFalse(self.battlefield.get_effect(Weather.RAINDANCE).suppressed)

    def test_aura_effects(self):
        self.handle('|switch|p2a: Zygarde|Zygarde, L76|100/100')
        self.handle('|-ability|p2a: Zygarde|Aura Break')
        self.handle('|turn|2')

        self.assertTrue(self.battlefield.has_effect(PseudoWeather.AURABREAK))

        self.handle('|switch|p2a: Xerneas|Xerneas, L73|100/100')
        self.handle('|-ability|p2a: Xerneas|Fairy Aura')
        self.handle('|turn|3')

        self.assertFalse(self.battlefield.has_effect(PseudoWeather.DARKAURA))
        self.assertTrue(self.battlefield.has_effect(PseudoWeather.FAIRYAURA))

    def test_handle_move_wish(self):
        self.handle('|switch|p2a: Blissey|Blissey, L77, F|100/100')
        self.handle('|move|p2a: Blissey|Wish|p2a: Blissey')
        self.handle('|turn|2')

        self.assertTrue(self.foe_side.has_effect(SideCondition.WISH))
        self.assertEqual(self.foe_side.get_effect(SideCondition.WISH).duration, 1)

        self.handle('|turn|3')

        self.assertFalse(self.foe_side.has_effect(SideCondition.WISH))

    def test_handle_move_healingwish(self):
        self.handle('|switch|p2a: Cherrim|Cherrim, L83, M|100/100')
        self.handle('|move|p2a: Cherrim|Healing Wish|p2a: Cherrim')
        self.assertTrue(self.foe_side.has_effect(SideCondition.HEALINGWISH))

        self.handle('|faint|p2a: Cherrim')
        self.handle('|switch|p2a: Latias|Latias, L75, F|100/100')
        self.handle('|-heal|p2a: Latias|100/100|[from] move: Healing Wish')
        self.handle('|turn|2')
        self.assertFalse(self.foe_side.has_effect(SideCondition.HEALINGWISH))

        self.handle('|move|p2a: Latias|Healing Wish|p2a: Latias')
        self.handle('|-fail|p2a: Latias')
        self.assertFalse(self.foe_side.has_effect(SideCondition.HEALINGWISH))

    def test_recalculate_pokemon_stats_when_hiddenpower_revealed(self):
        self.handle('|switch|p2a: Gothitelle|Gothitelle, L74, M|100/100')
        self.handle('|switch|p1a: Giratina|Giratina-Origin, L73|339/339')
        gothitelle = self.foe_side.active_pokemon
        self.assertDictEqual(gothitelle.stats, {'max_hp': 226, 'atk': 124, 'def': 184,
                                                'spa': 184, 'spd': 206, 'spe': 139})
        self.handle('|move|p2a: Gothitelle|Hidden Power|p1a: Giratina')
        self.handle('|-immune|p1a: Giratina|[msg]')
        self.handle('|turn|2')
        self.assertDictEqual(gothitelle.stats, {'max_hp': 226, 'atk': 124, 'def': 183,
                                                'spa': 183, 'spd': 205, 'spe': 138})

        self.handle('|switch|p2a: Xerneas|Xerneas, L71|100/100')
        xerneas = self.foe_side.active_pokemon
        self.handle('|move|p2a: Xerneas|Hidden Power|p1a: Giratina')
        self.assertDictEqual(xerneas.stats, {'max_hp': 296, 'atk': 227, 'def': 176,
                                             'spa': 227, 'spd': 181, 'spe': 181})

    def test_reveal_arceus_genesect_gourgeist(self):
        self.handle('|switch|p2a: Arceus|Arceus-Psychic, L73|100/100')
        self.handle('|turn|2')

        arceus = self.foe_side.active_pokemon
        self.assertEqual(arceus.types, [Type.PSYCHIC, None])
        self.assertEqual(arceus.item, itemdex['mindplate'])
        self.assertEqual(arceus.ability, abilitydex['multitype'])

        self.handle('|switch|p2a: Genesect|Genesect-Shock, L74|100/100')
        genesect = self.foe_side.active_pokemon
        self.assertEqual(genesect.item, itemdex['shockdrive'])

        self.handle('|switch|p2a: Gourgeist|Gourgeist-Small, L83, M|100/100')
        gourgeist = self.foe_side.active_pokemon
        self.assertEqual(gourgeist.name, 'gourgeistsmall')
        self.assertEqual(gourgeist.stats['spe'], 212)

    def test_unknown_item_assumes_lightclay_for_screen_duration(self):
        self.handle('|switch|p2a: Xatu|Xatu, L81, M|100/100')
        self.handle('|move|p2a: Xatu|Reflect|p2a: Xatu')
        self.handle('|-sidestart|p2: other-player|Reflect')
        self.assertEqual(self.foe_side.get_effect(SideCondition.REFLECT).duration, 8)

    def test_switch_out_regenerator(self):
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|turn|2')
        self.handle('|-damage|p1a: Zekrom|200/266')
        zekrom = self.my_side.active_pokemon
        self.handle('|switch|p1a: Hitmonchan|Hitmonchan, L79, M|209/209')

        self.assertEqual(zekrom.hp, zekrom.max_hp)

    def test_batonpass(self):
        self.handle('|switch|p2a: Gorebyss|Gorebyss, L83, M|100/100')
        self.handle('|turn|2')
        self.handle('|move|p2a: Gorebyss|Shell Smash|p2a: Omastar')
        self.handle('|-unboost|p2a: Gorebyss|def|1')
        self.handle('|-unboost|p2a: Gorebyss|spd|1')
        self.handle('|-boost|p2a: Gorebyss|atk|2')
        self.handle('|-boost|p2a: Gorebyss|spa|2')
        self.handle('|-boost|p2a: Gorebyss|spe|2')
        self.handle('|-enditem|p2a: Gorebyss|White Herb')
        self.handle('|-restoreboost|p2a: Gorebyss|[silent]')
        self.handle('|turn|3')
        self.handle('|move|p2a: Gorebyss|Substitute|p2a: Gorebyss')
        self.handle('|move|p2a: Gorebyss|Substitute|p2a: Gorebyss')
        self.handle('|-start|p2a: Gorebyss|Substitute')
        self.handle('|-damage|p2a: Gorebyss|75/100')
        self.handle('|move|p2a: Gorebyss|Baton Pass|p2a: Gorebyss')
        self.handle('|switch|p2a: Haxorus|Haxorus, L77, F|100/100')

        haxorus = self.foe_side.active_pokemon
        self.assertDictContainsSubset({'atk': 2, 'spa': 2, 'spe': 2, 'spd': 0, 'def': 0},
                                      haxorus.boosts)
        self.assertTrue(haxorus.has_effect(Volatile.SUBSTITUTE))

    @patch('bot.battleclient.BattleClient._validate_my_team', lambda _: None)
    @patch('bot.cheatsheetengine.CheatSheetEngine.show_my_moves', lambda *_: None)
    def test_maybe_trapped(self):
        self.handle('|switch|p2a: Wobbuffet|Wobbuffet, L74, M|100/100')
        self.handle('|turn|2')
        self.handle_request({"active":[{"moves": [], "maybeTrapped":True}], "rqid":2})

        wobbuffet = self.foe_side.active_pokemon
        self.assertTrue(self.hitmonchan.has_effect(Volatile.TRAPPED))

    def test_lockedmove_isnt_set_if_foe_is_immune(self):
        self.handle('|switch|p2a: Clefable|Clefable, L75, M|100/100')
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|turn|2')

        self.handle('|move|p1a: Zekrom|Outrage|p2a: Clefable')
        self.handle('|-immune|p2a: Clefable|[msg]')

        zekrom = self.my_side.active_pokemon
        self.assertFalse(zekrom.has_effect(Volatile.LOCKEDMOVE))

    def test_lockedmove_isnt_set_when_notarget(self):
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|turn|2')
        self.handle('|faint|p2a: Goodra')
        self.handle('|move|p1a: Zekrom|Outrage|p2: Goodra|[notarget]')

        zekrom = self.my_side.active_pokemon
        self.assertFalse(zekrom.has_effect(Volatile.LOCKEDMOVE))

    def test_rockyhelmet_damage_reveals_item_correctly(self):
        self.bc.set_item(self.hitmonchan, itemdex['rockyhelmet'])
        self.handle('|switch|p2a: Electivire|Electivire, L81, M|100/100')
        self.handle('|turn|2')
        self.handle('|move|p2a: Electivire|Ice Punch|p1a: Hitmonchan')
        self.handle('|-damage|p2a: Electivire|87/100|[from] item: Rocky Helmet|[of] p1a: Hitmonchan')

        electivire = self.foe_side.active_pokemon
        self.assertEqual(electivire.item, itemdex['_unrevealed_'])

    def test_battlefield_and_pokemon_last_move_used(self):
        self.handle('|switch|p2a: Stunfisk|Stunfisk, L83, M|100/100')
        stunfisk = self.foe_side.active_pokemon
        self.handle('|move|p2a: Stunfisk|Dragon Pulse|p1a: Hitmonchan|[from]Copycat')
        self.assertFalse(movedex['dragonpulse'] in self.goodra.moves)
        self.assertEqual(self.battlefield.last_move_used, movedex['dragonpulse'])
        self.assertEqual(stunfisk.last_move_used, movedex['dragonpulse'])

        self.handle('|turn|2')
        self.handle('|move|p2a: Stunfisk|Sleep Talk|p2a: Stunfisk')
        self.handle('|move|p2a: Stunfisk|Stealth Rock|p1a: Hitmonchan|[from]Sleep Talk')
        self.assertTrue(movedex['stealthrock'] in stunfisk.moves)
        self.assertEqual(self.battlefield.last_move_used, movedex['stealthrock'])
        self.assertEqual(stunfisk.last_move_used, movedex['sleeptalk'])

    def test_rbstats_has_only_one_level_for_zoroark(self):
        """
        BattleClient.detect_illusioned_foe currently depends on zoroark having only one possible
        level when generating a new zoroark
        """
        self.assertEqual(len(rbstats['zoroark']['level']), 1)

    def test_remove_lockedmove_on_confusion_damage(self):
        self.handle('|switch|p1a: Zekrom|Zekrom, L73|266/266')
        self.handle('|-start|p1a: Zekrom|confusion')
        self.handle('|turn|2')
        self.handle('|move|p1a: Zekrom|Outrage|p2a: Goodra')
        self.handle('|turn|3')
        zekrom = self.my_side.active_pokemon
        self.assertTrue(zekrom.has_effect(Volatile.LOCKEDMOVE))
        self.handle('|-activate|p1a: Zekrom|confusion')
        self.handle('|-damage|p1a: Zekrom|49/266|[from] confusion')
        self.assertFalse(zekrom.has_effect(Volatile.LOCKEDMOVE))


class TestBattleClientZoroark(TestBattleClientInitialRequestBase):
    def setUp(self):
        super(TestBattleClientZoroark, self).setUp()
        request = '|request|{"active":[{"moves":[{"move":"Avalanche","id":"avalanche","pp":16,"maxpp":16,"target":"normal","disabled":false},{"move":"Toxic","id":"toxic","pp":16,"maxpp":16,"target":"normal","disabled":false},{"move":"Roar","id":"roar","pp":32,"maxpp":32,"target":"normal","disabled":false},{"move":"Rapid Spin","id":"rapidspin","pp":64,"maxpp":64,"target":"normal","disabled":false}]}],"side":{"name":"0raichu","id":"p1","pokemon":[{"ident":"p1: Avalugg","details":"Avalugg, L83, F","condition":"293/293","active":true,"stats":{"atk":242,"def":353,"spa":121,"spd":124,"spe":94},"moves":["avalanche","toxic","roar","rapidspin"],"baseAbility":"sturdy","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Zoroark","details":"Zoroark, L78, M","condition":"222/222","active":false,"stats":{"atk":168,"def":139,"spa":232,"spd":139,"spe":209},"moves":["nastyplot","flamethrower","focusblast","darkpulse"],"baseAbility":"illusion","item":"lifeorb","pokeball":"pokeball"},{"ident":"p1: Klinklang","details":"Klinklang, L81","condition":"230/230","active":false,"stats":{"atk":209,"def":233,"spa":160,"spd":184,"spe":192},"moves":["wildcharge","shiftgear","substitute","geargrind"],"baseAbility":"clearbody","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Sandslash","details":"Sandslash, L81, M","condition":"254/254","active":false,"stats":{"atk":209,"def":225,"spa":120,"spd":136,"spe":152},"moves":["swordsdance","knockoff","rapidspin","earthquake"],"baseAbility":"sandrush","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Volcanion","details":"Volcanion, L75","condition":"243/243","active":false,"stats":{"atk":208,"def":223,"spa":239,"spd":179,"spe":149},"moves":["superpower","hiddenpowerice60","fireblast","substitute"],"baseAbility":"waterabsorb","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Wobbuffet","details":"Wobbuffet, L74, F","condition":"403/403","active":false,"stats":{"atk":53,"def":129,"spa":92,"spd":129,"spe":92},"moves":["mirrorcoat","destinybond","encore","counter"],"baseAbility":"shadowtag","item":"custapberry","pokeball":"pokeball"}]},"rqid":1}'
        self.initial_request(json.loads(request.split('|')[2]))
        self.turn_0()

    def turn_0(self):
        self.handle('|switch|p1a: Avalugg|Avalugg, L83, F|293/293')
        self.handle('|switch|p2a: Goodra|Goodra, L77, F|100/100')
        self.handle('|turn|1')

        self.avalugg = self.my_side.team[0]
        self.zoroark = self.my_side.team[1]
        self.wobbuffet = self.my_side.team[5]
        self.goodra = self.foe_side.team[0]
        self.assertEqual(self.avalugg.name, 'avalugg')
        self.assertEqual(self.zoroark.name, 'zoroark')
        self.assertEqual(self.wobbuffet.name, 'wobbuffet')
        self.assertEqual(self.goodra.name, 'goodra')

    def switch_in_zoroark_as_wobbuffet(self):
        self.bc.request = json.loads('{"active":[{"moves":[{"move":"Nasty Plot","id":"nastyplot","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Flamethrower","id":"flamethrower","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Focus Blast","id":"focusblast","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Dark Pulse","id":"darkpulse","pp":24,"maxpp":24,"target":"any","disabled":false}]}],"side":{"name":"test-BillsPC","id":"p1","pokemon":[{"ident":"p1: Zoroark","details":"Zoroark, L78, M","condition":"222/222","active":true,"stats":{"atk":168,"def":139,"spa":232,"spd":139,"spe":209},"moves":["nastyplot","flamethrower","focusblast","darkpulse"],"baseAbility":"illusion","item":"lifeorb","pokeball":"pokeball"},{"ident":"p1: Avalugg","details":"Avalugg, L83, F","condition":"293/293","active":false,"stats":{"atk":242,"def":353,"spa":121,"spd":124,"spe":94},"moves":["avalanche","toxic","roar","rapidspin"],"baseAbility":"sturdy","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Klinklang","details":"Klinklang, L81","condition":"230/230","active":false,"stats":{"atk":209,"def":233,"spa":160,"spd":184,"spe":192},"moves":["wildcharge","shiftgear","substitute","geargrind"],"baseAbility":"clearbody","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Sandslash","details":"Sandslash, L81, M","condition":"254/254","active":false,"stats":{"atk":209,"def":225,"spa":120,"spd":136,"spe":152},"moves":["swordsdance","knockoff","rapidspin","earthquake"],"baseAbility":"sandrush","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Volcanion","details":"Volcanion, L75","condition":"243/243","active":false,"stats":{"atk":208,"def":223,"spa":239,"spd":179,"spe":149},"moves":["superpower","hiddenpowerice60","fireblast","substitute"],"baseAbility":"waterabsorb","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Wobbuffet","details":"Wobbuffet, L74, F","condition":"403/403","active":false,"stats":{"atk":53,"def":129,"spa":92,"spd":129,"spe":92},"moves":["mirrorcoat","destinybond","encore","counter"],"baseAbility":"shadowtag","item":"custapberry","pokeball":"pokeball"}]},"rqid":2}')
        self.handle('|switch|p1a: Wobbuffet|Wobbuffet, L74, F|222/222')
        self.assertEqual(self.my_side.active_pokemon.base_species, 'zoroark')
        self.assertTrue(self.zoroark.illusion)
        self.assertTrue(self.zoroark.is_active)
        self.assertFalse(self.wobbuffet.is_active)

    def test_recognize_my_zoroark(self):
        """
        Switch to zoroark. This is only visible by looking at the current request. Zoroark will be
        in the first pokemon slot, and the active moves will be zoroark's.
        """
        self.switch_in_zoroark_as_wobbuffet()

        self.handle('|move|p1a: Wobbuffet|Dark Pulse|p2a: Goodra')
        self.assertEqual(self.zoroark.pp[movedex['darkpulse']], 24-1)
        self.handle('|-damage|p1a: Wobbuffet|72/222')
        self.assertEqual(self.zoroark.hp, 72)
        self.assertEqual(self.wobbuffet.hp, self.wobbuffet.max_hp)

    def test_replace_my_zoroark(self):
        self.switch_in_zoroark_as_wobbuffet()
        self.handle('|move|p2a: Goodra|Dragon Pulse|p1a: Wobbuffet')
        self.handle('|replace|p1a: Zoroark|Zoroark, L78, M|200/222')
        self.handle('|-end|p1a: Zoroark|Illusion')
        self.handle('|-damage|p1a: Zoroark|114/222')

        self.assertFalse(self.zoroark.illusion)
        self.assertEqual(self.zoroark.hp, 114)
        self.assertEqual(self.wobbuffet.hp, self.wobbuffet.max_hp)
        self.assertTrue(self.zoroark.is_active)
        self.assertFalse(self.wobbuffet.is_active)

    def test_switch_my_zoroark_for_its_decoy(self):
        self.switch_in_zoroark_as_wobbuffet()
        self.bc.request = json.loads('{"active":[{"moves":[{"move":"Mirror Coat","id":"mirrorcoat","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Destiny Bond","id":"destinybond","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Encore","id":"encore","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Counter","id":"counter","pp":32,"maxpp":32,"target":"self","disabled":false}]}],"side":{"name":"test-BillsPC","id":"p1","pokemon":[{"ident":"p1: Wobbuffet","details":"Wobbuffet, L74, F","condition":"403/403","active":true,"stats":{"atk":53,"def":129,"spa":92,"spd":129,"spe":92},"moves":["mirrorcoat","destinybond","encore","counter"],"baseAbility":"shadowtag","item":"custapberry","pokeball":"pokeball"},{"ident":"p1: Avalugg","details":"Avalugg, L83, F","condition":"293/293","active":false,"stats":{"atk":242,"def":353,"spa":121,"spd":124,"spe":94},"moves":["avalanche","toxic","roar","rapidspin"],"baseAbility":"sturdy","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Klinklang","details":"Klinklang, L81","condition":"230/230","active":false,"stats":{"atk":209,"def":233,"spa":160,"spd":184,"spe":192},"moves":["wildcharge","shiftgear","substitute","geargrind"],"baseAbility":"clearbody","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Sandslash","details":"Sandslash, L81, M","condition":"254/254","active":false,"stats":{"atk":209,"def":225,"spa":120,"spd":136,"spe":152},"moves":["swordsdance","knockoff","rapidspin","earthquake"],"baseAbility":"sandrush","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Volcanion","details":"Volcanion, L75","condition":"243/243","active":false,"stats":{"atk":208,"def":223,"spa":239,"spd":179,"spe":149},"moves":["superpower","hiddenpowerice60","fireblast","substitute"],"baseAbility":"waterabsorb","item":"leftovers","pokeball":"pokeball"},{"ident":"p1: Zoroark","details":"Zoroark, L78, M","condition":"222/222","active":false,"stats":{"atk":168,"def":139,"spa":232,"spd":139,"spe":209},"moves":["nastyplot","flamethrower","focusblast","darkpulse"],"baseAbility":"illusion","item":"lifeorb","pokeball":"pokeball"}]},"rqid":2}')
        self.handle('|move|p1a: Wobbuffet|Dark Pulse|p2a: Goodra')
        self.assertEqual(self.zoroark.pp[movedex['darkpulse']], 24-1)
        self.handle('|drag|p1a: Wobbuffet|Wobbuffet, L74, F|403/403')

        self.assertFalse(self.zoroark.is_active)
        self.assertTrue(self.wobbuffet.is_active)
        self.assertEqual(self.my_side.active_pokemon, self.wobbuffet)
        self.bc._validate_my_team()

    def test_replace_foe_zoroark(self):
        self.handle('|-damage|p2a: Goodra|50/100')
        self.handle('|move|p1a: Avalugg|Rapid Spin|p2a: Goodra')
        self.handle('|replace|p2a: Zoroark|Zoroark, L78, F|50/100')
        self.handle('|-end|p2a: Zoroark|Illusion')
        self.handle('|-damage|p2a: Zoroark|45/100')

        self.assertFalse(self.goodra.is_active)
        foe_zoroark = self.foe_side.active_pokemon
        self.assertEqual(foe_zoroark.name, 'zoroark')
        self.assertEqual(foe_zoroark.hp, round(222 * 0.45))
        self.assertEqual(self.goodra.hp, self.goodra.max_hp)

    def test_replace_foe_zoroark_with_effects(self):
        self.handle('|-status|p2a: Goodra|par')
        self.handle('|-boost|p2a: Goodra|atk|2')
        self.handle('|-start|p2a: Goodra|move: Yawn|[of] p1a: Avalugg')
        self.handle('|move|p1a: Avalugg|Rapid Spin|p2a: Goodra')
        self.handle('|replace|p2a: Zoroark|Zoroark, L78, F|100/100 par')
        self.handle('|-end|p2a: Zoroark|Illusion')
        self.handle('|-damage|p2a: Zoroark|95/100 par')

        self.assertFalse(self.goodra.is_active)
        self.assertNotEqual(self.foe_side.active_pokemon, self.goodra)
        self.assertIsNone(self.goodra.status)
        self.assertEqual(self.goodra.hp, self.goodra.max_hp)
        self.assertFalse(self.goodra.has_effect(Volatile.YAWN))
        self.assertFalse(self.goodra.boosts)

        foe_zoroark = self.foe_side.active_pokemon

        self.assertEqual(foe_zoroark.status, Status.PAR)
        self.assertTrue(foe_zoroark.has_effect(Status.PAR))
        self.assertTrue(foe_zoroark.has_effect(Volatile.YAWN))
        self.assertEqual(foe_zoroark.boosts['atk'], 2)
        self.assertEqual(foe_zoroark.hp, round(222 * 0.95))

    def test_detect_zoroark_based_on_move(self):
        self.handle('|switch|p2a: Wobbuffet|Wobbuffet, L74, M|100/100')
        self.handle('|-damage|p2a: Wobbuffet|40/100')
        self.handle('|turn|2')

        wobbuffet = self.foe_side.active_pokemon
        # using flamethrower should reveal that it's a zoroark
        self.handle('|move|p2a: Wobbuffet|Flamethrower|p1a: Avalugg')
        self.handle('|-miss|p2a: Wobbuffet|p1a: Avalugg')

        zoroark = self.foe_side.active_pokemon
        self.assertNotEqual(zoroark, wobbuffet)
        self.assertEqual(zoroark.name, 'zoroark')
        self.assertTrue(zoroark.illusion)
        self.assertEqual(wobbuffet.hp, wobbuffet.max_hp)
        self.assertTrue(zoroark.is_active)
        self.assertFalse(wobbuffet.is_active)
        self.assertEqual(zoroark.hp, round(222 * 0.40))

        self.handle('|-status|p2a: Wobbuffet|psn')
        self.handle('|-damage|p2a: Wobbuffet|28/100 psn|[from] psn')
        self.assertEqual(zoroark.hp, round(222 * 0.28))
        self.assertEqual(wobbuffet.hp, wobbuffet.max_hp)
        self.assertEqual(zoroark.status, Status.PSN)
        self.assertIsNone(wobbuffet.status)
        self.assertTrue(zoroark.illusion)

        self.handle('|replace|p2a: Zoroark|Zoroark, L78, F|28/100 psn')
        self.assertEqual(zoroark.hp, round(222 * 0.28))
        self.assertEqual(wobbuffet.hp, wobbuffet.max_hp)
        self.assertEqual(zoroark.status, Status.PSN)
        self.assertIsNone(wobbuffet.status)
        self.assertFalse(zoroark.illusion)

    def test_save_and_reset_pre_switch_state_on_reveal_illusion(self):
        self.handle('|-damage|p2a: Goodra|77/100')
        self.handle('|-status|p2a: Goodra|psn')
        self.handle('|switch|p2a: Stunfisk|Stunfisk, L83, M|100/100')
        self.handle('|turn|2')
        self.handle('|switch|p2a: Goodra|Goodra, L77, F|100/100')
        self.handle('|-damage|p2a: Goodra|66/100')
        self.handle('|-status|p2a: Goodra|par')
        self.handle('|replace|p2a: Zoroark|Zoroark, L78, F|66/100 par')

        zoroark = self.foe_side.active_pokemon
        self.assertNotEqual(zoroark, self.goodra)
        self.assertEqual(self.goodra.hp, round(self.goodra.max_hp * 0.77))
        self.assertEqual(self.goodra.status, Status.PSN)
        self.assertEqual(zoroark.hp, round(zoroark.max_hp * 0.66))
        self.assertEqual(zoroark.status, Status.PAR)

    def test_save_and_reset_learned_moves_on_reveal_illusion(self):
        self.handle('|switch|p2a: Yveltal|Yveltal, L73|100/100')
        yveltal = self.foe_side.active_pokemon
        self.handle('|move|p2a: Yveltal|Dark Pulse|p1a: Avalugg')
        self.handle('|turn|2')
        self.handle('|move|p2a: Yveltal|Roost|p2a: Yveltal')
        self.handle('|turn|3')
        self.handle('|switch|p2a: Goodra|Goodra, L77, F|100/100')
        self.handle('|turn|4')
        self.handle('|switch|p2a: Yveltal|Yveltal, L73|100/100')
        self.handle('|turn|5')
        self.handle('|move|p2a: Yveltal|U-turn|p1a: Avalugg')
        self.handle('|replace|p2a: Zoroark|Zoroark, L78, F|100/100')

        # Expected: all zoroark-possible moves are removed from yveltal, and only those moves
        # that zoroark used during this switch are added to zoroark's moveset. Even though in
        # this case we know that yveltal does have darkpulse, we could have added darkpulse to
        # yveltal's moveset during a separate switch-in when it was actually zoroark. Since we
        # may not be able to tell who actually tell who has darkpulse, nobody should have it.

        zoroark = self.foe_side.active_pokemon
        self.assertNotEqual(zoroark, yveltal)
        self.assertSetEqual(set(zoroark.moves), {movedex['uturn']})
        self.assertSetEqual(set(yveltal.moves), {movedex['roost']})

    def test_illusion_faints_without_being_revealed(self):
        self.handle('|switch|p2a: Illumise|Illumise, L83, F|100/100') # actually a zoroark
        illusion = self.foe_side.active_pokemon
        self.handle('|-status|p2a: Illumise|tox')
        self.handle('|-damage|p2a: Illumise|1/100')
        self.handle('|turn|2')
        self.handle('|-damage|p2a: Illumise|0 fnt')
        self.handle('|faint|p2a: Illumise')
        self.handle('|switch|p2a: Illumise|Illumise, L83, F|100/100') # the real illumise
        illumise = self.foe_side.active_pokemon
        self.handle('|turn|3')

        self.assertTrue(illusion.is_fainted())
        self.assertEqual(illumise.hp, illumise.max_hp)
        self.assertEqual(illumise.status, None)
        self.assertTrue(illumise.is_active)
        self.assertEqual(illumise, self.foe_side.active_pokemon)

        self.handle('|-damage|p2a: Illumise|50/100|')
        self.handle('|-status|p2a: Illumise|par')

        self.assertTrue(illusion.is_fainted())
        self.assertEqual(illumise.hp, round(illumise.max_hp * 0.5))
        self.assertEqual(illumise.status, Status.PAR)

        self.handle('|-damage|p2a: Illumise|0 fnt')
        self.handle('|-faint|p2a: Illumise')

        self.assertTrue(illusion.is_fainted())
        self.assertTrue(illumise.is_fainted())

    def get_fainted_pokemon(self, side):
        for pokemon in side.team:
            if pokemon.is_fainted():
                return pokemon

    def test_illusion_faints_after_both_being_damaged_and_revealed(self):
        self.handle('|switch|p2a: Vaporeon|Vaporeon, L77, F|100/100') # the real vaporeon
        self.handle('|-status|p2a: Vaporeon|tox')
        self.handle('|-damage|p2a: Vaporeon|1/100 tox')
        self.handle('|turn|2')
        self.handle('|switch|p2a: Vaporeon|Vaporeon, L77, F|100/100') # actually zoroark
        self.handle('|-damage|p2a: Vaporeon|0 fnt') # faint without |replace|
        self.handle('|faint|p2a: Vaporeon')
        self.handle('|switch|p2a: Vaporeon|Vaporeon, L77, F|1/100 tox')
        self.handle('|turn|3')

        vaporeon = self.foe_side.active_pokemon
        self.assertIsNotNone(self.get_fainted_pokemon(self.foe_side))
        self.assertEqual(vaporeon.hp, 1)
        self.assertEqual(vaporeon.status, Status.TOX)
        self.assertTrue(vaporeon.is_active, Status.TOX)
        self.assertEqual(vaporeon.name, 'vaporeon')

    @patch.dict(rbstats['yveltalL73'],
                {('darkpulse', 'hurricane', 'suckerpunch', 'uturn', 'darkaura', 'leftovers'): 1})
    def test_learn_fifth_move_because_of_illusion_shenanigans(self):
        self.handle('|switch|p2a: Yveltal|Yveltal, L73|100/100') # actually a zoroark
        self.handle('|move|p2a: Yveltal|Sucker Punch|p1a: Avalugg')
        self.handle('|turn|2')
        self.handle('|move|p2a: Yveltal|Dark Pulse|p1a: Avalugg')
        self.handle('|turn|3')
        self.handle('|move|p2a: Yveltal|U-turn|p1a: Avalugg')
        self.handle('|switch|p2a: Scrafty|Scrafty, L79, F|100/100')
        self.handle('|turn|4')
        self.handle('|switch|p2a: Yveltal|Yveltal, L73|100/100') # actually yveltal
        yveltal = self.foe_side.active_pokemon
        self.handle('|move|p2a: Yveltal|Hurricane|p1a: Avalugg')
        self.handle('|turn|5')
        self.handle('|move|p2a: Yveltal|Toxic|p1a: Avalugg') # 5th move
        self.handle('|turn|6')

        self.assertSetEqual(set(yveltal.moves), {movedex['hurricane'], movedex['toxic']})
