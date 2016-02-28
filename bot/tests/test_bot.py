from __future__ import absolute_import
from unittest import TestCase

from mock import patch

from bot.bot import Bot
from pokedex.enums import Status
from pokedex.moves import movedex

def raise_(*_): raise

@patch('__builtin__.raw_input', lambda _: '2')
@patch('bot.battleclient.log.exception', raise_)
@patch('bot.bot.log.exception', raise_)
@patch('bot.bot.WebSocketClient.__init__', lambda self: None)
@patch('bot.bot.WebSocketClient.send', lambda *_: None)
class TestBot(TestCase):
    def _init_battle(self, bot):
        bot.received_message('>battle-randombattle-245152194\n'
                             '|init|battle\n'
                             '|title|BingsF vs. opponent\n'
                             '|join|BingsF')

    def _turn_0(self, bot):
        bot.received_message('>battle-randombattle-245152194\n'
                             '|title|opponent vs. BingsF')
        bot.received_message('>battle-randombattle-245152194\n'
                             '|join|opponent')
        bot.received_message('>battle-randombattle-245152194\n'
                             '|player|p1|opponent|151')
        bot.received_message('>battle-randombattle-245152194\n'
                             '|request|{"side":{"name":"BingsF","id":"p2","pokemon":[{"ident":"p2: Haxorus","details":"Haxorus, L77, M","condition":"244/244","active":true,"stats":{"atk":271,"def":183,"spa":137,"spd":152,"spe":194},"moves":["earthquake","poisonjab","outrage","substitute"],"baseAbility":"moldbreaker","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Grumpig","details":"Grumpig, L83, F","condition":"268/268","active":false,"stats":{"atk":79,"def":156,"spa":197,"spd":230,"spe":180},"moves":["toxic","healbell","lightscreen","psychic"],"baseAbility":"thickfat","item":"lightclay","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Doublade","details":"Doublade, L77, F","condition":"217/217","active":false,"stats":{"atk":214,"def":276,"spa":114,"spd":120,"spe":98},"moves":["shadowclaw","ironhead","swordsdance","sacredsword"],"baseAbility":"noguard","item":"eviolite","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Togekiss","details":"Togekiss, L76, M","condition":"254/254","active":false,"stats":{"atk":81,"def":188,"spa":226,"spd":219,"spe":166},"moves":["airslash","nastyplot","batonpass","healbell"],"baseAbility":"serenegrace","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Ninjask","details":"Ninjask, L83, M","condition":"237/237","active":false,"stats":{"atk":197,"def":122,"spa":131,"spd":131,"spe":313},"moves":["substitute","batonpass","protect","xscissor"],"baseAbility":"speedboost","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Spiritomb","details":"Spiritomb, L79, F","condition":"209/209","active":false,"stats":{"atk":191,"def":216,"spa":191,"spd":216,"spe":101},"moves":["pursuit","darkpulse","willowisp","shadowsneak"],"baseAbility":"infiltrator","item":"lifeorb","pokeball":"pokeball","canMegaEvo":false}]}}')
        bot.received_message('>battle-randombattle-245152194\n'
                             '|request|{"active":[{"moves":[{"move":"Earthquake","id":"earthquake","pp":16,"maxpp":16,"target":"allAdjacent","disabled":false},{"move":"Poison Jab","id":"poisonjab","pp":32,"maxpp":32,"target":"normal","disabled":false},{"move":"Outrage","id":"outrage","pp":16,"maxpp":16,"target":"randomNormal","disabled":false},{"move":"Substitute","id":"substitute","pp":16,"maxpp":16,"target":"self","disabled":false}]}],"side":{"name":"BingsF","id":"p2","pokemon":[{"ident":"p2: Haxorus","details":"Haxorus, L77, M","condition":"244/244","active":true,"stats":{"atk":271,"def":183,"spa":137,"spd":152,"spe":194},"moves":["earthquake","poisonjab","outrage","substitute"],"baseAbility":"moldbreaker","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Grumpig","details":"Grumpig, L83, F","condition":"268/268","active":false,"stats":{"atk":79,"def":156,"spa":197,"spd":230,"spe":180},"moves":["toxic","healbell","lightscreen","psychic"],"baseAbility":"thickfat","item":"lightclay","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Doublade","details":"Doublade, L77, F","condition":"217/217","active":false,"stats":{"atk":214,"def":276,"spa":114,"spd":120,"spe":98},"moves":["shadowclaw","ironhead","swordsdance","sacredsword"],"baseAbility":"noguard","item":"eviolite","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Togekiss","details":"Togekiss, L76, M","condition":"254/254","active":false,"stats":{"atk":81,"def":188,"spa":226,"spd":219,"spe":166},"moves":["airslash","nastyplot","batonpass","healbell"],"baseAbility":"serenegrace","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Ninjask","details":"Ninjask, L83, M","condition":"237/237","active":false,"stats":{"atk":197,"def":122,"spa":131,"spd":131,"spe":313},"moves":["substitute","batonpass","protect","xscissor"],"baseAbility":"speedboost","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Spiritomb","details":"Spiritomb, L79, F","condition":"209/209","active":false,"stats":{"atk":191,"def":216,"spa":191,"spd":216,"spe":101},"moves":["pursuit","darkpulse","willowisp","shadowsneak"],"baseAbility":"infiltrator","item":"lifeorb","pokeball":"pokeball","canMegaEvo":false}]},"rqid":1}')
        bot.received_message('>battle-randombattle-245152194\n'
                             '|player|p2|BingsF|146\n'
                             '|gametype|singles\n'
                             '|gen|6\n'
                             '|tier|Random Battle\n'
                             '|rated\n'
                             '|rule|Sleep Clause Mod: Limit one foe put to sleep\n'
                             '|rule|HP Percentage Mod: HP is shown in percentages\n'
                             '|start\n'
                             '|switch|p1a: Beautifly|Beautifly, L83, M|100/100\n'
                             '|switch|p2a: Haxorus|Haxorus, L77, M|244/244\n'
                             '|-ability|p2a: Haxorus|Mold Breaker\n'
                             '|turn|1')
        # TODO: patch out the decision making process and go right to handling further messages

    def test_trigger_request_after_next_message(self):
        bot = Bot(username='BingsF', password='password')
        self._init_battle(bot)
        battleclient = bot.battleclient
        self.assertEqual(battleclient.name, 'BingsF')
        self._turn_0(bot)


        self.assertEqual(battleclient.foe_name, 'opponent')
        self.assertEqual(battleclient.my_player, 1)
        self.assertEqual(battleclient.foe_player, 0)
        self.assertEqual(battleclient.battlefield.turns, 1)
        self.assertEqual(battleclient.my_side.active_pokemon.name, 'haxorus')
        self.assertEqual(battleclient.foe_side.active_pokemon.name, 'beautifly')
        battleclient._validate_my_team() # just in case it didn't get validated after processing the request

    def test_validate_full_turn(self):
        bot = Bot(username='BingsF', password='password')
        self._init_battle(bot)
        bc = bot.battleclient
        self.assertEqual(bc.name, 'BingsF')
        self._turn_0(bot)
        bot.received_message('>battle-randombattle-245152194\n'
                             '|request|{"forceSwitch":[true],"side":{"name":"BingsF","id":"p2","pokemon":[{"ident":"p2: Haxorus","details":"Haxorus, L77, M","condition":"0 fnt","active":true,"stats":{"atk":271,"def":183,"spa":137,"spd":152,"spe":194},"moves":["earthquake","poisonjab","outrage","substitute"],"baseAbility":"moldbreaker","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Grumpig","details":"Grumpig, L83, F","condition":"268/268","active":false,"stats":{"atk":79,"def":156,"spa":197,"spd":230,"spe":180},"moves":["toxic","healbell","lightscreen","psychic"],"baseAbility":"thickfat","item":"lightclay","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Doublade","details":"Doublade, L77, F","condition":"217/217","active":false,"stats":{"atk":214,"def":276,"spa":114,"spd":120,"spe":98},"moves":["shadowclaw","ironhead","swordsdance","sacredsword"],"baseAbility":"noguard","item":"eviolite","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Togekiss","details":"Togekiss, L76, M","condition":"254/254","active":false,"stats":{"atk":81,"def":188,"spa":226,"spd":219,"spe":166},"moves":["airslash","nastyplot","batonpass","healbell"],"baseAbility":"serenegrace","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Ninjask","details":"Ninjask, L83, M","condition":"237/237","active":false,"stats":{"atk":197,"def":122,"spa":131,"spd":131,"spe":313},"moves":["substitute","batonpass","protect","xscissor"],"baseAbility":"speedboost","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Spiritomb","details":"Spiritomb, L79, F","condition":"209/209","active":false,"stats":{"atk":191,"def":216,"spa":191,"spd":216,"spe":101},"moves":["pursuit","darkpulse","willowisp","shadowsneak"],"baseAbility":"infiltrator","item":"lifeorb","pokeball":"pokeball","canMegaEvo":false}]},"rqid":2,"noCancel":true}')

        bot.received_message('>battle-randombattle-245152194\n'
                             '|move|p2a: Haxorus|Outrage|p1a: Beautifly\n'
                             '|-damage|p1a: Beautifly|11/100\n'
                             '|move|p1a: Beautifly|Bug Buzz|p2a: Haxorus\n'
                             '|-crit|p2a: Haxorus\n'
                             '|-damage|p2a: Haxorus|0 fnt\n'
                             '|-damage|p1a: Beautifly|1/100|[from] item: Life Orb\n'
                             '|faint|p2a: Haxorus')
        self.assertEqual(bc.foe_side.active_pokemon.name, 'beautifly')
        beautifly = bc.foe_side.active_pokemon
        self.assertEqual(beautifly.hp, 1)
        self.assertListEqual(beautifly.moveset, [movedex['bugbuzz']])
        self.assertEqual(beautifly.pp[movedex['bugbuzz']], movedex['bugbuzz'].max_pp - 1)
        haxorus = bc.my_side.active_pokemon
        self.assertEqual(haxorus.hp, 0)
        self.assertEqual(haxorus.status, Status.FNT)
        self.assertTrue(haxorus.is_active)

        bot.received_message('>battle-randombattle-245152194\n'
                             '|request|{"active":[{"moves":[{"move":"Substitute","id":"substitute","pp":16,"maxpp":16,"target":"self","disabled":false},{"move":"Baton Pass","id":"batonpass","pp":64,"maxpp":64,"target":"self","disabled":false},{"move":"Protect","id":"protect","pp":16,"maxpp":16,"target":"self","disabled":false},{"move":"X-Scissor","id":"xscissor","pp":24,"maxpp":24,"target":"normal","disabled":false}]}],"side":{"name":"BingsF","id":"p2","pokemon":[{"ident":"p2: Ninjask","details":"Ninjask, L83, M","condition":"237/237","active":true,"stats":{"atk":197,"def":122,"spa":131,"spd":131,"spe":313},"moves":["substitute","batonpass","protect","xscissor"],"baseAbility":"speedboost","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Grumpig","details":"Grumpig, L83, F","condition":"268/268","active":false,"stats":{"atk":79,"def":156,"spa":197,"spd":230,"spe":180},"moves":["toxic","healbell","lightscreen","psychic"],"baseAbility":"thickfat","item":"lightclay","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Doublade","details":"Doublade, L77, F","condition":"217/217","active":false,"stats":{"atk":214,"def":276,"spa":114,"spd":120,"spe":98},"moves":["shadowclaw","ironhead","swordsdance","sacredsword"],"baseAbility":"noguard","item":"eviolite","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Togekiss","details":"Togekiss, L76, M","condition":"254/254","active":false,"stats":{"atk":81,"def":188,"spa":226,"spd":219,"spe":166},"moves":["airslash","nastyplot","batonpass","healbell"],"baseAbility":"serenegrace","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Haxorus","details":"Haxorus, L77, M","condition":"0 fnt","active":false,"stats":{"atk":271,"def":183,"spa":137,"spd":152,"spe":194},"moves":["earthquake","poisonjab","outrage","substitute"],"baseAbility":"moldbreaker","item":"leftovers","pokeball":"pokeball","canMegaEvo":false},{"ident":"p2: Spiritomb","details":"Spiritomb, L79, F","condition":"209/209","active":false,"stats":{"atk":191,"def":216,"spa":191,"spd":216,"spe":101},"moves":["pursuit","darkpulse","willowisp","shadowsneak"],"baseAbility":"infiltrator","item":"lifeorb","pokeball":"pokeball","canMegaEvo":false}]},"rqid":3}')
        bot.received_message('>battle-randombattle-245152194\n'
                             '|switch|p2a: Ninjask|Ninjask, L83, M|237/237\n'
                             '|turn|2')
        self.assertEqual(bc.battlefield.turns, 2)
        ninjask = bc.my_side.active_pokemon
        self.assertEqual(ninjask.name, 'ninjask')
        self.assertTrue(ninjask.is_active)
        self.assertFalse(haxorus.is_active)
