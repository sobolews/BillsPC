from __future__ import absolute_import
import string
import random
from functools import partial

from battle.battlefield import BattleSide, BattleField
from battle.battlepokemon import BattlePokemon
from bot.foeside import FoeBattleSide
from bot.unrevealedpokemon import UnrevealedPokemon
from bot.cheatsheetengine import CheatSheetEngine
from mining import create_pokedex
from misc.functions import normalize_name
from pokedex import effects, statuses
from pokedex.abilities import abilitydex
from pokedex.enums import Status, Weather, Volatile, ITEM, ABILITY
from pokedex.items import itemdex
from pokedex.moves import movedex
from pokedex.stats import Boosts, PokemonStats

pokedex = create_pokedex()

if __debug__: from _logging import log

class BattleClient(object):
    """
    Maintains a model of a battle (self.battlefield) and handles Showdown messages that modify
    the state of the battle. Responds to |request| messages via its send method.

    See PROTOCOL.md in the Showdown repo for documentation on the client/server communication
    protocol.

    Purposefully unimplemented message types (because they don't occur in randbats):
    {-swapboost, -copyboost, -invertboost, -ohko, -mustrecharge}
    """
    def __init__(self, name, room, send):
        """
        name: (str) client's username
        room: (str) the showdown room that battle messages should be sent to
        send: a callable that takes a str param, and sends messages to the showdown server
        """
        self.name = name        # str
        self.room = room        # str
        self.foe_name = None    # str
        self.my_player = None   # 0 or 1
        self.foe_player = None  # 1 or 0
        self.my_side = None     # BattleSide
        self.foe_side = None    # FoeBattleSide
        self.battlefield = None # BattleField
        self.is_active = True
        self.last_sent = None
        self.request = None
        self.rqid = None

        self.make_moves = False # set to True to have the bot make random choices (TODO: use an AI
                                # module for choices)
        self.cheatsheetengine = CheatSheetEngine.from_battlefield(None)

        def _send(msg):
            self.last_sent = msg
            send(msg)
        self.send = _send

    def get_side_from_msg(self, msg, index=1):
        """
        All `POKEMON` in messages are formatted 'p2a: Goodra'
        e.g. |-unboost|p2a: Goodra|spa|2
        """
        side = self.my_side if int(msg[index][1]) - 1 == self.my_player else self.foe_side
        assert side is not None, side
        return side

    def get_pokemon_from_msg(self, msg, index=1):
        """
        All `POKEMON` in messages are formatted 'p2a: Vaporeon'
        Returning None is allowed when the pokemon is one of the foe's unrevealed pokemon

        A different index may be passed, e.g. index=3 to get Weezing from
        `|-sethp|p2a: Emboar|55/100|p1a: Weezing|166/238|[from] move: Pain Split`
        """
        for pokemon in self.get_side_from_msg(msg, index).team:
            if pokemon.name.startswith(normalize_name(msg[index])):
                return pokemon

    def set_hp_status(self, pokemon, hp_msg):
        """
        hp_msg is a str of the form "201/219" (my pokemon) or "76/100" (foe pokemon).
        It may also have a status, e.g. "88/100 brn".
        If the pokemon is fainted, it will be "0 fnt"
        """
        msg = hp_msg.split()
        if len(msg) > 1:
            if msg[1] == 'fnt':
                pokemon.hp = 0
                pokemon.status = Status.FNT
                return

        hp, max_hp = map(int, msg[0].split('/'))
        if pokemon.side.index == self.foe_player:
            # We do some estimation here, since information on the opponent's HP is always a
            # percentage.
            assert max_hp == 100, max_hp
            if hp == 100:
                pokemon.hp = pokemon.max_hp # probably
            elif hp == 1:
                pokemon.hp = 1  # probably, because of focus sash, sturdy, etc.
            else:
                pokemon.hp = int(round(pokemon.max_hp * hp / 100.0)) # best estimate
        else:
            assert max_hp == pokemon.max_hp != 100, (max_hp, pokemon.max_hp)
            pokemon.hp = hp

    def build_my_side(self, json):
        side = int(json['side']['id'][1]) - 1
        assert self.my_player == side, (self.my_player, side)
        j_team = json['side']['pokemon']
        team = [self.my_pokemon_from_json(j_pokemon) for j_pokemon in j_team]
        self.my_side = BattleSide(team, side, self.name)

    def my_pokemon_from_json(self, j_pokemon):
        details = j_pokemon['details'].split(', ')
        species = normalize_name(details[0])
        level = int(details[1].lstrip('L'))
        hp, max_hp = map(int, j_pokemon['condition'].split('/'))
        stats = j_pokemon['stats']
        stats['max_hp'] = max_hp
        moveset = [movedex[move.rstrip(string.digits)] for move in j_pokemon['moves']]
        ability = abilitydex[j_pokemon['baseAbility']]
        item = itemdex[j_pokemon['item']]

        pokemon = BattlePokemon(pokedex[species], level, moveset, ability, item)
        pokemon.hp, pokemon.max_hp = hp, max_hp
        if __debug__: self._warn_if_stats_discrepancy(pokemon, stats)
        pokemon.stats = PokemonStats.from_dict(stats)

        return pokemon

    def handle(self, msg_type, msg):
        handle_method = 'handle_%s' % msg_type.lstrip('-')
        getattr(self, handle_method)(msg)

    def handle_inactive(self, msg):
        if self.last_sent is not None:
            self.send(self.last_sent)

    def handle_turn(self, msg):
        """
        |turn|1
        """
        assert self.battlefield.turns == int(msg[1]) - 1, (self.battlefield.turns, msg)
        self.battlefield.turns = int(msg[1])
        my_active = self.my_side.active_pokemon
        foe_active = self.foe_side.active_pokemon

        my_active.item_used_this_turn = None
        my_active.will_move_this_turn = True
        foe_active.item_used_this_turn = None
        foe_active.will_move_this_turn = True

    def handle_player(self, msg):
        """
        `|player|PLAYER|USERNAME|AVATAR`   e.g. `|player|p1|1BillsPC|294`
        """
        if len(msg) > 2: # ignore msgs of the form `|player|p1`
            if msg[2] == self.name:
                if self.my_player is None:
                    self.my_player = int(msg[1][1]) - 1
                    self.foe_player = int(not self.my_player)
                else:
                    assert self.my_player == int(msg[1][1]) - 1, self.my_player
                    assert self.foe_player == int(not self.my_player), (self.foe_player,
                                                                        self.my_player)
            else:
                if __debug__:
                    if self.foe_name is not None:
                        log.w('Received a second (foe) player registration (%s); '
                              'foe already named as (%s)', msg[2], self.foe_name)
                if self.foe_name is None:
                    if self.my_player is None:
                        self.foe_player = int(msg[1][1]) - 1
                        self.my_player = int(not self.foe_player)
                    else:
                        assert self.foe_player == int(msg[1][1]) - 1, (self.foe_player, msg)
                        assert self.my_player == int(not self.foe_player), (self.my_player,
                                                                            self.foe_player)

                    self.foe_name = msg[2]
                    self.foe_side = FoeBattleSide([UnrevealedPokemon() for _ in range(6)],
                                                  self.foe_player, self.foe_name)


        if self.battlefield is None and self.my_side and self.foe_side:
            self.battlefield = BattleField(*sorted([self.my_side, self.foe_side],
                                                   key=lambda side: side.index))

    def handle_request(self, request):
        """
        |request|
        {"active":[{"moves":[4 moves]}],
         "rqid": 1
         "wait": true (or undefined)
         "side": {
            "name": str
            "id": "p1"
            "pokemon": [{
              "ident": "p1: Vaporeon"
              "details": "Vaporeon, L77, M[, shiny]"
              "condition": "401/401"
              "active": true
              "stats": {"atk", "def", "spa", "spd", "spe"}
              "moves": ["scald", "toxic", "wish", "protect"]
              "baseAbility": "waterabsorb"
              "item": "leftovers"
              "canMegaEvo": false
            } ... ]}}

        If this is the first request (beginning of game), "active" and "rqid" are omitted
        """
        self.request = request
        self.rqid = request.get('rqid')
        if __debug__:
            self._validate_my_team()
        # else:         # TODO
        #     self._match_request() # change any invalidated data to match request
        # # (ideally, this should never be called, but defer to the server for any discrepancies)

        print repr(self.battlefield)

        if request.get('wait'): # The opponent has more decisions to make
            return

        if not any([self.my_side.active_pokemon.is_fainted(),
                    self.foe_side.active_pokemon.is_fainted()]):
            self.cheatsheetengine.battlefield = self.battlefield
            self.cheatsheetengine.show_my_moves(self.my_side.active_pokemon,
                                                self.foe_side.active_pokemon)
            self.cheatsheetengine.show_foe_moves(self.my_side.active_pokemon,
                                                 self.foe_side.active_pokemon)

        if self.make_moves:     # naive implementation for testing interaction with server:
            if request.get('forceSwitch') or random.randrange(10) == 0:
                choice = int(raw_input(
                    '\n'.join(['choose switch:',
                               '\n'.join(normalize_name(p['ident'].split(None, 1)[-1]) for i, p in
                                         enumerate(request['side']['pokemon'], 1)),
                               '> '])))
                choices = [i for i, p in enumerate(request['side']['pokemon'], 1)
                           if not p['condition'] == '0 fnt']
                choice = random.choice(choices)
                self.send('|'.join([self.room, '/choose switch %d' % choice] +
                                   filter(None, [str(self.rqid)])))
            else:
                move = random.randint(1, 4)
                self.send('%s|/choose move %d|%d' % (self.room, move, self.request['rqid']))

    # TODO: handle zoroark/illusion
    def handle_move(self, msg):
        """
        `|move|POKEMON|MOVE|TARGET[|FROM]`

        |move|p1a: Groudon|Aerial Ace|p2a: Fraxure|[from]Copycat

        Just subtract pp for MOVE from POKEMON
        """
        if len(msg) > 4:
            if msg[4].startswith('[from]'):
                return # this move is called by another (copycat, sleeptalk, lockedmove)

        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.is_active, pokemon
        foe = (self.foe_side.active_pokemon if pokemon.side.index == self.my_player
               else self.my_side.active_pokemon)
        pp_sub = 2 if not foe.is_fainted() and foe.ability is abilitydex['pressure'] else 1

        if msg[2] == 'Hidden Power':
            hp_moves = [move for move in pokemon.moveset if move.is_hiddenpower]
            if hp_moves:
                assert len(hp_moves) == 1, hp_moves
                move = hp_moves[0]
            else:
                # TODO: deal with guessing foe's hiddenpower type properly
                move = movedex['hiddenpowernotype']
        else:
            move = movedex[normalize_name(msg[2])]

        if move in pokemon.pp:
            pokemon.pp[move] -= pp_sub
        elif pokemon.side.index == self.foe_player: # Add move to foe's moveset
            assert (len(pokemon.moveset) < 4 or  # TODO: test raises assertion
                    move == movedex['struggle']), \
                '%s used %s but already has a full moveset:\n %r' % (pokemon, move, pokemon)
            if move != movedex['struggle']:
                pokemon.moveset.append(move)
                pokemon.pp[move] = move.max_pp - pp_sub

        elif __debug__:
            log.w("Handling a move (%s) not in %r's moveset", normalize_name(msg[2]), pokemon)

        pokemon.last_move_used = move
        pokemon.will_move_this_turn = False
        pokemon.remove_effect(Volatile.TWOTURNMOVE, force=True)

    def handle_damage(self, msg):
        """
        `|-damage|POKEMON|HP STATUS`, with optionally `|[from] EFFECT|[of] SOURCE`,
        `|[still]` (suppress animation), `|[silent]` (suppress message).

        |-damage|p2a: Goodra|62/100 brn|[from] brn

        We only care about msg[0], [1], [2].
        """
        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.is_active, pokemon

        self.set_hp_status(pokemon, msg[2])

    handle_heal = handle_damage

    def handle_faint(self, msg):
        """
        `|faint|POKEMON`

        |faint|p1a: Hitmonchan
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.hp = 0
        pokemon.status = Status.FNT

    def handle_status(self, msg):
        """
        `|-status|POKEMON|STATUS[|FROM]`
        |-status|p2a: Goodra|brn
        |-status|p2a: Stunfisk|slp|[from] move: Rest
        """
        pokemon = self.get_pokemon_from_msg(msg)

        pokemon.cure_status()
        self.set_status(pokemon, msg[2])
        if len(msg) > 3 and msg[3] == '[from] move: Rest':
            pokemon.is_resting = True

    def handle_cant(self, msg):
        """
        Decrement pokemon.sleep_turns if its sleeping
        |cant|p2a: Alomomola|slp
        """
        pokemon = self.get_pokemon_from_msg(msg)
        if msg[2] == 'slp':
            assert pokemon.status is Status.SLP, (pokemon, pokemon.status)
            if pokemon.sleep_turns > 0:
                pokemon.sleep_turns -= 1

    def handle_curestatus(self, msg):
        """
        `|-curestatus|POKEMON|STATUS`
        |-curestatus|p1a: Regirock|slp
        """
        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.status is not None, (pokemon, pokemon.status)
        pokemon.cure_status()

    def handle_cureteam(self, msg):
        """
        `|-cureteam|POKEMON`
        |-cureteam|p1a: Granbull|[from] move: HealBell
        """
        side = self.get_side_from_msg(msg)
        for pokemon in side.team:
            pokemon.cure_status()

    def set_status(self, pokemon, status):
        assert status in self.STATUS_MAP, status
        pokemon.status = self.STATUS_MAP[status][0]
        pokemon.set_effect(self.STATUS_MAP[status][1](pokemon), override_immunity=True)

    STATUS_MAP = {
        'brn': (Status.BRN, statuses.Burn),
        'slp': (Status.SLP, partial(statuses.Sleep, turns=2)), # best guess; sleep is randint(1, 3)
        'frz': (Status.FRZ, statuses.Freeze),
        'psn': (Status.PSN, statuses.Poison),
        'tox': (Status.TOX, statuses.Toxic),
        'par': (Status.PAR, statuses.Paralyze),
        Status.BRN: (Status.BRN, statuses.Burn),
        Status.SLP: (Status.SLP, partial(statuses.Sleep, turns=2)),
        Status.FRZ: (Status.FRZ, statuses.Freeze),
        Status.PSN: (Status.PSN, statuses.Poison),
        Status.TOX: (Status.TOX, statuses.Toxic),
        Status.PAR: (Status.PAR, statuses.Paralyze),
    }

    def handle_weather(self, msg):
        """
        `|-weather|WEATHER`
        |-weather|RainDance or |-weather|RainDance|[upkeep] or |-weather|none
        """
        if msg[1] == 'none':
            self.battlefield.clear_weather()
            return

        weather = Weather.values[msg[1].upper()]

        if len(msg) > 2 and msg[2] == '[upkeep]':
            if msg[1].lower() not in ('desolateland', 'primordialsea', 'deltastream'):
                assert self.battlefield.weather is not None, \
                    'Handling upkeep (%s) but weather is None' % msg[1]
                self.battlefield.get_effect(weather).duration -= 1
        else:
            self.battlefield.set_weather(weather)
            if msg[1].lower() in ('sunnyday', 'raindance'): # usually has heatrock/damprock boost
                                                            # TODO: use rbstats to determine
                                                            # likelihood of 5 vs 8 turns.
                self.battlefield.get_effect(weather).duration = 8

    def handle_switch(self, msg):
        """
        `|switch|POKEMON|SPECIES|HP STATUS` or `|drag|POKEMON|SPECIES|HP STATUS`

        |switch|p1a: Whiscash|Whiscash, L83, F|318/318
        """
        pokemon = self.get_pokemon_from_msg(msg)
        side = self.get_side_from_msg(msg)

        if pokemon is None:     # we are revealing a foe's pokemon
            assert side.index == self.foe_player, (side.index, self.foe_player)
            assert side.num_unrevealed > 0, side.num_unrevealed
            assert msg[3] == '100/100', msg[3]
            level = int(msg[2].split(', ')[1].lstrip('L'))
            assert 1 <= level <= 100, 'level=%r' % level
            pokemon = BattlePokemon(pokedex[normalize_name(msg[2].split(', ')[0])],
                                    level, moveset=[], side=side)
            self.foe_side.reveal(pokemon)

        outgoing = side.active_pokemon
        if outgoing is not None:
            outgoing.is_active = False
            outgoing._effect_index.clear()
            outgoing.effect_handlers = {key: list() for key in outgoing.effect_handlers}
            outgoing.boosts = Boosts()
            if outgoing.is_transformed:
                outgoing.revert_transform()

        # TODO: do any of the other flags from BattleEngine.switch_in need to be set here?
        side.active_pokemon = pokemon
        pokemon.is_active = True
        pokemon.last_move_used = None
        pokemon.turns_out = 0
        pokemon.will_move_this_turn = False

        self.set_hp_status(pokemon, msg[3])
        if pokemon.status is not None:
            self.set_status(pokemon, pokemon.status)

        pokemon.set_effect(pokemon.ability())

        if pokemon.item is not None:
            self.set_item(pokemon, pokemon.item)

    handle_drag = handle_switch
    handle_replace = handle_switch

    def handle_item(self, msg):
        """
        `|-item|POKEMON|ITEM`

        |-item|p1a: Magnezone|Air Balloon
        |-item|p2a: Butterfree|Choice Scarf|[from] move: Trick
        |-item|p1a: Exeggutor|Sitrus Berry|[from] ability: Harvest
        |-item|p2a: Suicune|Leftovers|[from] ability: Frisk|[of] p1a: Dusknoir|[identify]

        Identifies a currently held item
        """
        pokemon = self.get_pokemon_from_msg(msg)
        self.set_item(pokemon, itemdex[normalize_name(msg[2])])

    def handle_enditem(self, msg):
        """
        `|-enditem|POKEMON|ITEM`

        |-enditem|p2a: Pachirisu|Air Balloon
        |-enditem|p1a: Regirock|Chesto Berry|[eat]
        |-enditem|p2a: Jumpluff|Flying Gem|[from] gem|[move] Acrobatics
        |-enditem|p1a: Gothitelle|Leftovers|[from] move: Knock Off|[of] p2a: Venusaur
        |-enditem|p1a: Leafeon|Sitrus Berry|[from] stealeat|[move] Bug Bite|[of] p2a: Aerodactyl
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.remove_effect(ITEM, force=True)
        pokemon.item = None
        pokemon.last_berry_used = None
        item = itemdex[normalize_name(msg[2])]

        if len(msg) > 3:
            if msg[3] == '[eat]':
                pokemon.last_berry_used = item
                pokemon.item_used_this_turn = item
            elif msg[3] == '[from] stealeat':
                attacker = self.get_pokemon_from_msg([msg[5][5:]], 0)
                attacker.last_berry_used = item
                return
            elif msg[3] == '[from] move: Knock Off':
                return
        pokemon.item_used_this_turn = item

    def set_item(self, pokemon, item):
        pokemon.remove_effect(ITEM, force=True)
        pokemon.item = item
        pokemon.set_effect(item())
        pokemon.remove_effect(Volatile.UNBURDEN, force=True)

    def handle_ability(self, msg):
        """
        |-ability|p1a: Granbull|Intimidate|boost
        |-ability|p1a: Kyurem|Teravolt
        |-ability|p1a: Pyroar|Unnerve|p2: 1-BillsPC
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.remove_effect(ABILITY, force=True)
        pokemon.ability = ability = abilitydex[normalize_name(msg[2])]
        pokemon.set_effect(ability())

    def handle_boost(self, msg):
        """
        `|-boost|POKEMON|STAT|AMOUNT`
        e.g. |-boost|p2a: Hawlucha|atk|2
        """
        pokemon = self.get_pokemon_from_msg(msg)
        boost = self.BOOST_MAP.get(msg[2], msg[2])
        pokemon.boosts[boost] += int(msg[3])

    def handle_unboost(self, msg):
        pokemon = self.get_pokemon_from_msg(msg)
        boost = self.BOOST_MAP.get(msg[2], msg[2])
        pokemon.boosts[boost] -= int(msg[3])

    BOOST_MAP = {'evasion': 'evn', 'accuracy': 'acc'}

    def handle_setboost(self, msg):
        """
        Only used by bellydrum, angerpoint
        |-setboost|p2a: Azumarill|atk|6|[from] move: Belly Drum
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.boosts[msg[2]] = int(msg[3])

    def handle_restoreboost(self, msg):
        """
        Only used by whiteherb
        |-restoreboost|p1a: Hitmonchan|[silent]
        """
        pokemon = self.get_pokemon_from_msg(msg)
        for stat, val in pokemon.boosts.items():
            if val < 0:
                pokemon.boosts[stat] = 0

    def handle_clearboost(self, msg):
        """
        Only used by clearsmog
        |-clearboost|p1a: Volcarona
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.boosts = Boosts()

    def handle_clearallboost(self, msg):
        """
        Only used by haze
        `|-clearallboost`
        """
        self.my_side.active_pokemon.boosts = Boosts()
        self.foe_side.active_pokemon.boosts = Boosts()

    def handle_sethp(self, msg):
        """
        Only used by painsplit
        |-sethp|p2a: Hitmonlee|92/209 brn|p1a: Rotom|43/100|[from] move: Pain Split
        """
        self.set_hp_status(self.get_pokemon_from_msg(msg, index=1), msg[2])
        self.set_hp_status(self.get_pokemon_from_msg(msg, index=3), msg[4])

    def handle_activate(self, msg):
        """
        Activate is used for misc effects:

        |-activate|p1a: Banette|Destiny Bond -- destinybond took the foe down with it
        |-activate|p2a: Rotom-Fan|move: Trick|[of] p1a: Chimecho
        |-activate|p2a: Chesnaught|Protect -- ignore (existing effect stopped attack)

        TODO: WIP
        """

    def handle_singleturn(self, msg):
        """
        |-singleturn|p1a: Florges|Protect -- successfully applied a Protect-like effect
        ...

        TODO: WIP
        """

    def handle_singlemove(self, msg):
        """
        |-singlemove|p1a: Banette|Destiny Bond -- sets the destiny bond effect
        ...

        TODO: WIP
        """

    def handle_start(self, msg):
        """
        |-start|p2a: Suicune|move: Taunt
        |-start|p1a: Kyurem|confusion|[fatigue]
        |-start|p2a: Goodra|confusion
        |-start|p1a: Aggron|Autotomize (no end)
        |-start|p2a: Kyurem|Substitute
        |-start|p2a: Ho-Oh|move: Yawn|[of] p1a: Uxie
        |-start|p1a: Throh|move: Leech Seed
        |-start|p2a: Zekrom|Encore
        |-start|p1a: Politoed|perish3|[silent] (then) |-start|p1a: Politoed|perish3 (no end)
        |-start|p2a: Latios|perish2
        |-start|p2a: Latios|perish1
        |-start|p2a: Latios|perish0 (then) |faint|p2a: Latios
        |-start|p1a: Greninja|typechange|Dark|[from] Protean (no end)
        |-start|p2a: Regigigas|ability: Slow Start
        |-start|p1a: Heatmor|ability: Flash Fire (no end)
        |-start|p2a: Ditto|Disable|Bug Bite
        |-start|p2a: Leafeon|Attract|[from] ability: Cute Charm|[of] p1a: Fraxure
        |-start|p1a: Fraxure|Magnet Rise
        """


    def handle_end(self, msg):
        """
        |-end|p1a: Cacturne|move: Taunt
        |-end|p2a: Goodra|confusion
        |-end|p1a: Jirachi|Substitute
        |-end|p2a: Ho-Oh|move: Yawn|[silent]
        |-end|p1a: Fraxure|Leech Seed|[from] move: Rapid Spin|[of] p1a: Fraxure
        |-end|p2a: Quagsire|Encore
        |-end|p2a: Regigigas|Slow Start|[silent]
        |-end|p1a: Zoroark|Illusion
        |-end|p2a: Ditto|Disable
        |-end|p2a: Leafeon|Attract|[silent]
        |-end|p2a: Ditto|Magnet Rise
        |-end|p2a: Chansey|Infestation|[partiallytrapped]
        """


    def handle_prepare(self, msg):
        """
        Marks the initial usage of a two-turn move.
        |-prepare|p1a: Castform|Solar Beam|p2a: Corsola
        """
        pokemon = self.get_pokemon_from_msg(msg)
        move = movedex[normalize_name(msg[2])]
        if move.name == 'bounce':
            effect = effects.Bounce
        elif move.name in ('phantomforce', 'shadowforce'):
            effect = effects.PhantomForce
        else:
            effect = effects.TwoTurnMoveEffect
        pokemon.set_effect(effect(move))

    def handle_anim(self, msg):
        """
        When a two-turn move succeeds on the first turn (e.g. powerherb-geomancy or
        sunnyday-solarbeam), the easiest way I can see to detect this is the -anim message
        immediately following the -prepare message. Otherwise Volatile.TWOTURNMOVE will be
        removed the next time the pokemon makes a |move| (or switches).

        |-prepare|p1a: Castform|Solar Beam|p2a: Corsola
        |-anim|p1a: Castform|Solar Beam|p2a: Corsola
        |-weather|SunnyDay|[upkeep]
        """
        pokemon = self.get_pokemon_from_msg(msg)
        if pokemon.has_effect(Volatile.TWOTURNMOVE):
            pokemon.remove_effect(Volatile.TWOTURNMOVE, force=True)

    def handle_transform(self, msg):
        """
        |-transform|p2a: Ditto|p1a: Dedenne
        |-transform|p2a: Ditto|p1a: Zoroark|[from] ability: Imposter
        """
        pokemon = self.get_pokemon_from_msg(msg)
        foe = self.get_pokemon_from_msg(msg, 2)

        for move in self.request['active'][0]['moves']:
            id = move['id']
            if movedex[id] not in foe.moveset:
                foe.moveset.append(movedex[id])

        pokemon.transform_into(foe, engine=None, force=True)

    def _validate_my_team(self):
        """
        Validate that the current team state matching what is being sent from the server.
        This should only ever be called in __debug__ mode. It will fail otherwise.
        """
        request = self.request
        if request.get('active') is not None:
            for move in request['active'][0]['moves']:
                move['id'] = move['id'].rstrip(string.digits)

        for reqmon in request['side']['pokemon']:
            reqmon['moves'] = [move_.rstrip(string.digits)
                               for move_ in reqmon['moves']]

        for pokemon in self.my_side.team:
            try:
                if pokemon.status not in (None, Status.FNT):
                    if pokemon.is_active:
                        assert pokemon.has_effect(pokemon.status), \
                            '%s\n has status but no effect' % pokemon
                    else:
                        assert not pokemon.effects, \
                            '%s has effects but is benched' % pokemon

                if pokemon.is_active and request.get('active') is not None:
                    can_mega_evo = request['active'][0].get('canMegaEvo', False)
                    assert can_mega_evo == pokemon.can_mega_evolve, \
                        "%s's mega-evolution state is incorrect" % pokemon

                    active_moves = request['active'][0]['moves']
                    if len(active_moves) == 1:
                        assert (pokemon.has_effect(Volatile.TWOTURNMOVE) or
                                active_moves[0]['id'] in ('struggle', 'transform')), \
                            '%s has one move available but it appears invalid?' % pokemon
                    else:
                        for i, move in enumerate(pokemon.moveset):
                            assert (active_moves[i]['id'] == move.name or
                                    (active_moves[i]['id'] == 'hiddenpower' and
                                     move.name.startswith('hiddenpower'))), \
                                ("%s: request %s doesn't match %s" %
                                 (pokemon, active_moves[i]['id'], move))
                            assert active_moves[i]['pp'] == pokemon.pp[move], \
                                '%s: %s has %d pp' % (pokemon, move, pokemon.pp[move])
                            choices = pokemon.get_move_choices()
                            if not active_moves[i]['disabled']:
                                assert move in choices, \
                                    "%s's %s should be disabled, but it isn't" % (pokemon, move)

                # TODO: test/validate request['active'][0].get('trapped')

                reqmon = [p for p in self.request['side']['pokemon']
                          if pokemon.name.startswith(normalize_name(p['ident'].split(None, 1)[-1]))]
                assert reqmon, ("%s didn't match with any: %s" % (
                    pokemon, [normalize_name(p['ident'].split(None, 1)[-1])
                              for p in self.request['side']['pokemon']]))
                reqmon = reqmon[0]
                condition = reqmon['condition'].split()
                if condition[-1] == 'fnt':
                    assert pokemon.status is Status.FNT, '%s should be fainted' % pokemon
                    assert pokemon.hp == 0, "%s's hp should be 0" % pokemon
                elif condition[-1] in self.STATUS_MAP:
                    assert self.STATUS_MAP[condition[-1]][0] is pokemon.status, \
                        '%s has the wrong status' % pokemon
                else: # no status
                    hp, max_hp = map(int, condition[0].split('/'))
                    assert pokemon.hp == hp, '%s has the wrong hp' % pokemon
                    assert pokemon.max_hp == max_hp, '%s has the wrong max_hp' % pokemon
                if not pokemon.is_transformed:
                    for stat, val in reqmon['stats'].items():
                        assert pokemon.stats[stat] == val, "%s's %s is wrong" % (pokemon, stat)
                for i, move in enumerate(reqmon['moves']):
                    assert pokemon.moveset[i].name == move, \
                        ("%s's move %s doesn't match the request's %s" %
                         (pokemon, pokemon.moveset[i].name, move))
                assert pokemon.level == int(reqmon['details'].split(', ')[1][1:])
                assert pokemon.is_active == reqmon['active']
                if not pokemon.ability.name.startswith('_') and not pokemon.is_transformed:
                    assert pokemon.ability.name == reqmon['baseAbility'], (pokemon.ability.name,
                                                                           reqmon['baseAbility'])
                if pokemon.item is None:
                    assert reqmon['item'] == ''
                else:
                    assert reqmon['item'] == pokemon.item.name
                assert int(request['side']['id'][1]) - 1 == self.my_player, self.my_player
                assert request['side']['name'] == self.name, self.name

            except AssertionError:
                # mocked in tests to raise exception instead
                log.e('My team is invalid/out of sync with the server.\n'
                      'My team: %r\n Latest request msg: %r', self.my_side, self.request)
                log.exception('Assertion failed: ')
            except Exception:
                log.exception('Exception during team validation: ')
                log.e('%r\n%r' % (self.my_side, self.request))

    def _warn_if_stats_discrepancy(self, pokemon, stats):
        """
        Warn if the calculated stat for a pokemon is different from what is being sent by the
        Showdown server. A mismatch between these values indicates that we may be calculating
        the opponents' pokemon's stats incorrectly, which would throw off damage calculations.

        TODO: Known issue: Pokemon that will mega-evolve are handled incorrectly (off-by-one). Fix
        when mega-evolution is implemented.
        """
        for stat, val in stats.items():
            if not val == pokemon.stats[stat]:
                log.w("%s lvl %d's %s: Showdown=%d, calculated=%d",
                      pokemon, pokemon.level, stat, val, pokemon.stats[stat])
