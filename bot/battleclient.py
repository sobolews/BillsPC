from __future__ import absolute_import
import string
import traceback

import AI
from AI.actions import MoveAction, SwitchAction
from battle.battlefield import BattleSide, BattleField
from battle.battlepokemon import BattlePokemon
from bot.foeside import FoeBattleSide, FoePokemon
from bot.unrevealedpokemon import UnrevealedPokemon, UNREVEALED
from bot.battlecalculator import BattleCalculator
from showdowndata import pokedex
from showdowndata.rbstats import rbstats, rbstats_key
from misc.functions import normalize_name, clamp_int
from battle import effects, statuses
from battle.abilities import abilitydex
from battle.enums import (Status, Weather, Volatile, ITEM, ABILITY, Type, SideCondition, Hazard,
                          PseudoWeather, Decision)
from battle.items import itemdex
from battle.moves import movedex
from battle.types import type_effectiveness, HPivs
from battle.stats import Boosts, PokemonStats
from _logging import log


class BattleClient(object):
    """
    Maintains a model of a battle (self.battlefield) and handles Showdown messages that modify
    the state of the battle. Responds to |request| messages via its send method.

    See PROTOCOL.md in the Showdown repo for documentation on the client/server communication
    protocol.

    Purposefully unimplemented message types (because they don't occur in randbats):
    {-swapboost, -copyboost, -invertboost, -ohko, -mustrecharge}
    """
    def __init__(self, name, room, send, show_calcs=False, ai_strategy=None):
        """
        name: (str) client's username
        room: (str) the showdown room that battle messages should be sent to
        send: a callable that takes a str param, and sends messages to the showdown server
        """
        self.name = name        # str
        self.room = room        # str
        self.foe_name = None    # str
        self.my_side = None     # BattleSide
        self.foe_side = None    # FoeBattleSide
        self.battlefield = None # BattleField
        self.is_active = True
        self.last_sent = None
        self.request = None
        self.rqid = None
        self.crit = False
        self.hiddenpower_trigger = None
        self.previous_msg = ['']
        self.switch_choice = None

        self.show_calcs = show_calcs
        self.battle = BattleCalculator.from_battlefield(None)
        self.AI = AI.Agent(ai_strategy) if ai_strategy else None

        def _send(msg):
            self.last_sent = msg
            send(msg)
        self.send = _send

    @property
    def win(self):
        return None if self.battlefield is None else self.battlefield.win

    def get_side_from_msg(self, msg, index=1):
        """
        All `POKEMON` in messages are formatted 'p2a: Goodra' or '[of] p2a: Goodra'
        e.g. |-unboost|p2a: Goodra|spa|2
        """
        identifier = msg[index].replace('[of] ', '')
        side = self.my_side if int(identifier[1]) - 1 == self.my_side.index else self.foe_side
        assert side is not None, side
        return side

    def get_pokemon_from_msg(self, msg, index=1):
        """
        All `POKEMON` in messages are formatted 'p2a: Vaporeon'
        Returning None is allowed when the pokemon is one of the foe's unrevealed pokemon

        A different index may be passed, e.g. index=3 to get Weezing from
        `|-sethp|p2a: Emboar|55/100|p1a: Weezing|166/238|[from] move: Pain Split`

        If getting a foe pokemon and foe_side.active_illusion is set, then return the foe's
        zoroark instead of that pokemon.
        """
        side = self.get_side_from_msg(msg, index)
        name = normalize_name(msg[index])

        # is it referring to an illusioned zoroark?
        if side == self.my_side:
            if msg[0] == 'switch':
                if self.switch_choice is None:
                    if self.get_zoroark(side) is not None and self.battlefield.turns > 0:
                        log.w('My switch choice was not recorded and I have a zoroark')
                else:
                    name = self.switch_choice
            elif msg[0] == 'drag':
                my_zoroark = self.get_zoroark(side)
                if (my_zoroark is not None and
                    not my_zoroark.is_fainted() and
                    side.remaining_pokemon > 1 and
                    normalize_name(self.request['side']['pokemon'][0]['ident']) == 'zoroark'
                ):
                    name = 'zoroark'
            else:
                active = side.active_pokemon
                if active is not None and active.base_species == 'zoroark':
                    name = 'zoroark'

        elif side.active_illusion:
            return self.get_zoroark(side)

        for pokemon in side.team:
            if pokemon.base_species.startswith(name):
                if pokemon.is_fainted():
                    continue
                return pokemon

    def get_move(self, move_name, pokemon):
        """
        Get the move object corresponding to a name sent by the server. If it's a hiddenpower move,
        then return the correct one for the pokemon or hiddenpowernotype if the type can't be
        determined.
        """
        move_name = normalize_name(move_name)
        if move_name == 'hiddenpower':
            hp_moves = [hp_move for hp_move in pokemon.moves if hp_move.is_hiddenpower]
            if hp_moves:
                assert len(hp_moves) == 1, (hp_moves, pokemon)
                move = hp_moves[0]
            else:
                assert pokemon.side == self.foe_side, pokemon
                move, _ = self.get_possible_hiddenpowers(pokemon)
        else:
            move = movedex[move_name]
        return move

    def is_ally(self, pokemon):
        return pokemon.side == self.my_side

    def is_foe(self, pokemon):
        return pokemon.side == self.foe_side

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
            else:
                status = self.STATUS_MAP[msg[1]][0]
                if not pokemon.has_effect(status):
                    self.set_status(pokemon, status)
        else:
            pokemon.status = None

        hp, max_hp = map(int, msg[0].split('/'))
        if self.is_foe(pokemon):
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
        index = int(json['side']['id'][1]) - 1
        j_team = json['side']['pokemon']
        team = [self.my_pokemon_from_json(j_pokemon) for j_pokemon in j_team]
        self.my_side = BattleSide(team, index, self.name)
        return self.my_side

    def my_pokemon_from_json(self, j_pokemon):
        details = j_pokemon['details'].split(', ')
        species = normalize_name(details[0])
        level = int(details[1].lstrip('L'))
        gender = details[2] if len(details) > 2 else None
        hp, max_hp = map(int, j_pokemon['condition'].split('/'))
        stats = j_pokemon['stats']
        stats['max_hp'] = max_hp
        moves = [movedex[move.rstrip(string.digits)] for move in j_pokemon['moves']]
        ability = abilitydex[j_pokemon['baseAbility']]
        item = itemdex[j_pokemon['item']]

        pokemon = BattlePokemon(pokedex[species], level, moves, ability, item, gender)
        pokemon.hp, pokemon.max_hp = hp, max_hp
        self._warn_if_stats_discrepancy(pokemon, stats)
        pokemon.stats = PokemonStats.from_dict(stats)

        return pokemon

    def handle(self, msg_type, msg):
        handle_method = 'handle_%s' % msg_type.lstrip('-')

        if self.hiddenpower_trigger is not None:
            self.deduce_hiddenpower(self.hiddenpower_trigger, msg)

        log.d('%s called with %s', handle_method, msg)
        getattr(self, handle_method)(msg)

        if self.crit and msg_type != '-crit':
            self.crit = False

        self.previous_msg = msg

    handle_supereffective = handle_resisted = handle_miss = lambda self, msg: None

    def deduce_hiddenpower(self, trigger, msg):
        """
        Try to deduce, from the message following a move, what type of hiddenpower `pokemon` has.
        e.g.:
        |move|p2a: Gothitelle|Hidden Power|p1a: Ambipom
        |-supereffective|p1a: Ambipom                       <-- called for this message

        Since Gothitelle gets either fire-type or fighting-type hiddenpower, we can deduce that this
        gothitelle has hiddenpowerfighting, and so we adjust its moveset and IVs.

        The possible messages following a |move||Hidden Power| are:

        Typical:
            |-supereffective|p2a: Graveler
            |-resisted|p2a: Azumarill
            |-immune|p2a: Haunter|[msg]
            |-damage|p2a: Grovyle|161/241
            |-miss|p2a: Durant|p1a: Yveltal

        Ability-based: flashfire,voltabsorb/waterabsorb/dryskin,lightningrod/motordrive/stormdrain,
                       levitate,primordialsea,desolateland,wonderguard,protean,deltastream
            |-start|p2a: Caterpie|ability: Flash Fire
            |-immune|p2a: Caterpie|[msg]|[from] ability: Flash Fire
            |-heal|p2a: Azumarill|341/341|[from] ability: Volt Absorb|[of] p1a: Clefable
            |-immune|p2a: Azumarill|[msg]|[from] ability: Volt Absorb
            |-ability|p2a: Plusle|Lightning Rod|boost
            |-ability|p2a: Leafeon|Storm Drain|boost
            |-ability|p2a: Electivire|Motor Drive|boost
            |-immune|p2a: Eelektross|[msg]|[from] ability: Levitate
            |-fail|p2a: Caterpie|Hidden Power|[from] Primordial Sea
            |-activate|p1a: Shedinja|ability: Wonder Guard
            |-start|p1a: Kecleon|typechange|Rock|[from] Protean
            |-activate||deltastream
        """
        if msg[0] in ('-crit', 'replace', '-end'):
            return              # expect information in the next message instead

        self.hiddenpower_trigger = None
        if msg[0] == '-miss':   # no information
            return

        pokemon, possible = trigger
        hiddenpower = None
        hp_notype = movedex['hiddenpowernotype']
        pp = pokemon.pp[hp_notype]
        del pokemon.moves[hp_notype]

        if msg[0] == '-start' and msg[2] == 'typechange': # reveals type in msg[3]
            pokemon.moves['hiddenpower' + normalize_name(msg[3])] = pp
            return

        defender = self.get_pokemon_from_msg(msg, 1) if msg[1] else None

        msg_to_eff = {'-supereffective': (2, 4),
                      '-resisted': (0.5, 0.25),
                      '-immune': (0,),
                      '-damage': (1,)}
        if msg[0] in msg_to_eff and len(msg) <= 3:
            reduced = [move for move in possible if
                       (self.battle.get_effectiveness(pokemon, move, defender) *
                        (not defender.is_immune_to_move(pokemon, move))) in msg_to_eff[msg[0]]]
            if len(reduced) == 1:
                hiddenpower = reduced[0]
            elif len(reduced) == 0:
                log.w('Error deducing hiddenpower type (no candidates): '
                      '%s, %s: %s', pokemon, possible, msg)

        # handle all the abilities and other effects that could reveal the hiddenpower type
        elif msg[0] == '-start' and normalize_name(msg[2]) == 'flashfire':
            hiddenpower = movedex['hiddenpowerfire']
        elif msg[0] == '-immune':
            effect = normalize_name(msg[3])
            if effect == 'flashfire':
                hiddenpower = movedex['hiddenpowerfire']
            elif effect == 'voltabsorb':
                hiddenpower = movedex['hiddenpowerelectric']
            elif effect in ('waterabsorb', 'dryskin'):
                hiddenpower = movedex['hiddenpowerwater']
            elif effect == 'levitate':
                hiddenpower = movedex['hiddenpowerground']
        elif msg[0] == '-heal':
            effect = normalize_name(msg[3])
            if effect == 'voltabsorb':
                hiddenpower = movedex['hiddenpowerelectric']
            elif effect in ('waterabsorb', 'dryskin'):
                hiddenpower = movedex['hiddenpowerwater']
        elif msg[0] == '-ability':
            effect = normalize_name(msg[3])
            if effect in ('lightningrod', 'motordrive'):
                hiddenpower = movedex['hiddenpowerelectric']
            elif effect == 'stormdrain':
                hiddenpower = movedex['hiddenpowerwater']
        elif msg[0] == '-fail':
            effect = normalize_name(msg[3])
            if effect == 'primordialsea':
                hiddenpower = movedex['hiddenpowerfire']
            if effect == 'desolateland':
                hiddenpower = movedex['hiddenpowerwater']
        elif msg[0] == '-activate':
            effect = normalize_name(msg[2])
            if effect == 'wonderguard':
                reduced = [move for move in possible if
                           self.battle.get_effectiveness(pokemon, move, defender) < 2]
                if len(reduced) == 1:
                    hiddenpower = reduced[0]
            elif effect == 'deltastream':
                reduced = [move for move in possible if
                           type_effectiveness(move.type, Type.FLYING) > 1]
                if len(reduced) == 1:
                    hiddenpower = reduced[0]
        else:
            log.e('Unhandled deduce_hiddenpower message for %s: %s', pokemon, msg)

        if hiddenpower is None:
            pokemon.moves[hp_notype] = pp
        else:
            pokemon.moves[hiddenpower] = pp
            self.recalculate_stats_hiddenpower(pokemon, hiddenpower.type)

        if hiddenpower is None:
            log.i("Unable to deduce %s's hiddenpower type vs %s from %s",
                  pokemon, defender, msg)
        elif hiddenpower in possible:
            log.i("Deduced %s's hiddenpower type to be %s", pokemon, hiddenpower)
        else:
            log.w("Setting %s's hiddenpower type to %s: "
                  "but possible choices were %s", pokemon, hiddenpower, possible)

    def recalculate_stats_hiddenpower(self, pokemon, hp_type):
        log.i("Recalculating %s's stats for hp_type=%s", pokemon, hp_type)
        pokemon.ivs = HPivs[hp_type]
        pokemon.stats = pokemon.calculate_initial_stats(pokemon.evs, pokemon.ivs)

    def handle_inactive(self, msg):
        if self.last_sent is not None:
            self.send(self.last_sent)

    def handle_turn(self, msg):
        """
        |turn|1

        This is the last message that will be received before a move must be chosen. Will be sent
        after a fainted pokemon is replaced.
        """
        assert self.battlefield.turns == int(msg[1]) - 1, (self.battlefield.turns, msg)
        self.battlefield.turns = turn = int(msg[1])
        my_active = self.my_side.active_pokemon
        foe_active = self.foe_side.active_pokemon
        assert (my_active and foe_active), (my_active, foe_active)

        my_active.item_used_this_turn = None
        my_active.will_move_this_turn = True
        my_active.turns_out += 1
        foe_active.item_used_this_turn = None
        foe_active.will_move_this_turn = True
        foe_active.turns_out += 1

        if turn > 1:
            for thing in filter(None, (my_active, foe_active, my_active.side, foe_active.side,
                                       self.battlefield)):
                for effect in thing.effects:
                    if effect.duration is not None and effect.source not in Weather.values:
                        if (effect.duration <= 1 and effect.source in (
                                SideCondition.WISH, Volatile.STALL, Volatile.TWOTURNMOVE,
                                Volatile.LOCKEDMOVE)):
                            # remove automatically, since there's no notification in protocol
                            thing.remove_effect(effect.source)
                            continue
                        elif effect.duration == 0:
                            log.w("%s's effect %s has a duration of 0, cannot "
                                  "decrement", thing, effect)
                            continue
                        effect.duration -= 1

        self.update_foe_inferences()

        abilities = (my_active.ability, foe_active.ability)

        # update ability-based field effects
        if abilitydex['airlock'] in abilities or abilitydex['cloudnine'] in abilities:
            self.battlefield.suppress_weather()
        else:
            self.battlefield.unsuppress_weather()
        if abilitydex['darkaura'] in abilities:
            self.battlefield.set_effect(effects.DarkAuraFieldEffect())
        elif self.battlefield.has_effect(PseudoWeather.DARKAURA):
            self.battlefield.remove_effect(PseudoWeather.DARKAURA)
        if abilitydex['fairyaura'] in abilities:
            self.battlefield.set_effect(effects.FairyAuraFieldEffect())
        elif self.battlefield.has_effect(PseudoWeather.FAIRYAURA):
            self.battlefield.remove_effect(PseudoWeather.FAIRYAURA)
        if abilitydex['aurabreak'] in abilities:
            self.battlefield.set_effect(effects.AuraBreakFieldEffect())
        elif self.battlefield.has_effect(PseudoWeather.AURABREAK):
            self.battlefield.remove_effect(PseudoWeather.AURABREAK)

    def update_foe_inferences(self):
        for pokemon in self.foe_side.team:
            if pokemon.is_fainted() or pokemon.name == UNREVEALED or pokemon.is_transformed:
                continue
            log.d("Updating foe: %s" % pokemon)

            known_attrs, all_known = pokemon.known_attrs()
            if all_known:
                continue

            rb_index = rbstats_key(pokemon)
            if pokemon.item == itemdex['_unrevealed_']:
                for item in rbstats[rb_index]['item']:
                    if rbstats.attr_probability(rb_index, item, known_attrs) == 1:
                        log.i("%s must have %s, given %s", pokemon.name, item, known_attrs)
                        self.reveal_foe_original_item(pokemon, itemdex[item])
                        self.set_item(pokemon, itemdex[item])

            if pokemon.ability == abilitydex['_unrevealed_']:
                for ability in rbstats[rb_index]['ability']:
                    if rbstats.attr_probability(rb_index, ability, known_attrs) == 1:
                        log.i("%s must have %s, given %s", pokemon.name, ability, known_attrs)
                        self.set_ability(pokemon, abilitydex[ability])

            if len(pokemon.moves) < 4:
                for move in rbstats[rb_index]['moves']:
                    if (move not in known_attrs and
                        rbstats.attr_probability(rb_index, move, known_attrs) == 1
                    ):
                        log.i("%s must have %s, given %s", pokemon.name, move, known_attrs)
                        self.reveal_move(pokemon, movedex[move])
                        assert len(pokemon.moves) <= 4, (pokemon, pokemon.moves)

        active = self.my_side.active_pokemon
        foe = self.foe_side.active_pokemon
        if active.is_transformed and active.name == foe.name:
            if (foe.ability != abilitydex['_unrevealed_'] and
                active.ability == abilitydex['_unrevealed_']):
                self.set_ability(active, foe.ability)
            elif (active.ability != abilitydex['_unrevealed_'] and
                  foe.ability == abilitydex['_unrevealed_']):
                self.set_ability(foe, active.ability)

    def handle_player(self, msg):
        """
        `|player|PLAYER|USERNAME|AVATAR`   e.g. `|player|p1|1BillsPC|294`
        """
        if len(msg) > 2: # ignore msgs of the form `|player|p1`
            if msg[2] != self.name:
                if self.foe_name is None:
                    foe_index = int(msg[1][1]) - 1
                    if self.my_side is not None:
                        assert foe_index != self.my_side.index
                    self.foe_name = msg[2]
                    self.foe_side = FoeBattleSide([UnrevealedPokemon() for _ in range(6)],
                                                  foe_index, self.foe_name)
                else:
                    log.w('Received a second (foe) player registration (%s); '
                          'foe already named as (%s)', msg[2], self.foe_name)

        if self.battlefield is None and self.my_side and self.foe_side:
            self.battlefield = BattleField(*sorted([self.my_side, self.foe_side],
                                                   key=lambda side: side.index))
            self.battle.battlefield = self.battlefield
            if self.AI is not None:
                self.AI.set_my_player(self.my_side.index)

    def handle_request(self, request):
        """
        |request|
        {"active":[{"moves":[1-4 moves], "maybeTrapped":true, "trapped":true}],
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

        or
        {"forceSwitch": [true],
         "side"...,
         "rqid": 2}

        If this is the first request (beginning of game), "active" and "rqid" are omitted
        """
        self.rqid = request.get('rqid')

        my_active = self.my_side.active_pokemon
        foe_active = self.foe_side.active_pokemon
        req_active = request.get('active')
        if req_active is not None:
            if req_active[0].get('maybeTrapped'):
                my_active.set_effect(effects.Trapped())
            if len(req_active[0]['moves']) > 1 and my_active.has_effect(Volatile.LOCKEDMOVE):
                my_active.remove_effect(Volatile.LOCKEDMOVE)

        self._validate_my_team()

        log.i('\n'+repr(self.battlefield))

        if request.get('wait'): # The opponent has more decisions to make
            return

        if self.show_calcs and not my_active.is_fainted() and not foe_active.is_fainted():
            self.battle.show_my_moves(my_active, foe_active)
            self.battle.show_foe_moves(my_active, foe_active)

        if self.AI:
            self.make_move(request)
        else:
            self.bench_order = [normalize_name(p['ident']) for p in self.request['side']['pokemon']]

        self.request = request

    def make_move(self, request, switch_rejected=False):
        moves, switches, can_mega = self.get_action_choices(request, switch_rejected)
        action, mega = self.AI.select_action(self.battlefield, moves, switches, can_mega)

        log.i('Selected action: %s%s', action, ' + mega' if mega else '')
        if mega and action.action_type == Decision.SWITCH:
            log.w("%s chose to switch and mega-evolve on the same turn; removing 'mega'", self.AI)
            mega = False

        command = '%s|%s%s' % (self.room, action.command_string, ' mega' if mega else '')
        if self.rqid:
            command += '|%d' % self.rqid
        self.send(command)

        if action.action_type == Decision.SWITCH:
            self.switch_choice = action.pokemon_name
        else:
            self.switch_choice = None

    def get_action_choices(self, request, switch_rejected):
        moves = None
        switches = []
        can_mega = False
        force_switch = request.get('forceSwitch', False)
        if not switch_rejected and (force_switch or
                                    self.my_side.active_pokemon.get_switch_choices()):
            switches = [SwitchAction(normalize_name(p['ident']), i)
                        for i, p in enumerate(request['side']['pokemon'], 1)
                        if not p['condition'] == '0 fnt' and not p['active']]
        if not force_switch:
            can_mega = bool(request['active'][0].get('canMegaEvo'))
            moves = [MoveAction(normalize_name(move['move']), i)
                     for i, move in enumerate(request['active'][0]['moves'], 1)
                     if not move.get('disabled')]

        log.d('Choosing from: %s %s, can_mega=%s', moves, switches, can_mega)
        assert moves or switches, (request, self.my_side.active_pokemon.get_switch_choices())
        return moves, switches, can_mega

    def handle_choice(self, msg):
        """
        In case moves are being made manually, we need to watch for |choice| messages to know what
        switch was requested by the player. This is required if the player has a zoroark to
        determine whether the zoroark or its decoy is being switched in.

        If the move was made by the AI module via self.make_move, then we already track this choice.
        |choice|switch 2|
        """
        if self.AI:
            return

        if msg[1].startswith('switch'):
            bench_index = int(msg[1][-1]) - 1
            self.switch_choice = self.bench_order[bench_index]
            log.i('set switch = %s', self.switch_choice)

    def handle_move(self, msg):
        """
        `|move|POKEMON|MOVE|TARGET[|FROM]`

        |move|p1a: Groudon|Aerial Ace|p2a: Fraxure|[from]Copycat
        |move|p1a: Kyurem|Outrage|p2a: Glalie|[from]lockedmove
        |move|p2a: Stunfisk|Earth Power|p1a: Swalot|[from]Sleep Talk
        |move|p1a: Haxorus|Outrage|p2: Zoroark|[notarget]

        Just subtract pp for MOVE from POKEMON
        Start autotomize from here, since there's no -start message when incrementing the multiplier
        """
        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.is_active, pokemon
        foe = (self.foe_side.active_pokemon if self.is_ally(pokemon)
               else self.my_side.active_pokemon)

        if len(msg) > 4 and msg[4].startswith('[from]'):
            # if hiddenpower is used, then for the purposes of copycat (the consumer of
            # battlefield.last_move_used), it is the default hiddenpowerdark
            called_move = movedex['hiddenpowerdark' if msg[2] == 'Hidden Power' else
                                  normalize_name(msg[2])]
            self.battlefield.last_move_used = called_move
            if msg[4].endswith('Sleep Talk'):
                self.reveal_move(pokemon, called_move)
            else:
                pokemon.last_move_used = called_move
            return          # this move is called by another (copycat, sleeptalk, lockedmove)

        if msg[2] == 'Hidden Power':
            hp_moves = [move for move in pokemon.moves if
                        move.is_hiddenpower and move != movedex['hiddenpowernotype']]
            if hp_moves:
                assert len(hp_moves) == 1, hp_moves
                move = hp_moves[0]
            else:
                assert pokemon.side == self.foe_side, (pokemon, pokemon.side)
                move, possible = self.get_possible_hiddenpowers(pokemon)
                if len(possible) > 1:
                    self.hiddenpower_trigger = (pokemon, possible)
        else:
            move = movedex[normalize_name(msg[2])]

        if move != movedex['struggle']:
            if (not foe.is_fainted() and
                foe.ability == abilitydex['pressure'] and
                not move.targets_user):
                pp_sub = 2
            else:
                pp_sub = 1
            if move in pokemon.pp:
                pokemon.pp[move] -= pp_sub
            elif self.is_foe(pokemon): # Add move to foe's moveset
                if (move.name not in rbstats[rbstats_key(pokemon)]['moves'] and
                    move.name in rbstats['zoroark']['moves']
                ):
                    log.i('Detected zoroark based on move %s', move)
                    pokemon = self.detect_illusioned_foe(pokemon, break_illusion=False)
                else:
                    if self.reveal_move(pokemon, move):
                        pokemon.pp[move] = max(0, move.max_pp - pp_sub)
            else:
                log.w("Handling a move (%s) not in %r's moveset", normalize_name(msg[2]), pokemon)

        pokemon.last_move_used = move
        self.battlefield.last_move_used = move
        pokemon.will_move_this_turn = False
        if pokemon.has_effect(Volatile.TWOTURNMOVE):
            pokemon.remove_effect(Volatile.TWOTURNMOVE, force=True)

        if move in (movedex['outrage'], movedex['petaldance']) and not msg[-1] == '[notarget]':
            pokemon.set_effect(effects.LockedMove(move))
        elif move == movedex['autotomize']:
            effect = pokemon.get_effect(Volatile.AUTOTOMIZE)
            if effect is None:
                pokemon.set_effect(effects.Autotomize())
            else:
                effect.multiplier += 1
        elif move == movedex['wish']:
            pokemon.side.set_effect(effects.Wish(pokemon.max_hp / 2))
        elif move == movedex['healingwish']:
            pokemon.side.set_effect(effects.HealingWish())
        elif move == movedex['batonpass']:
            pokemon.set_effect(effects.BatonPass())

        if pokemon.item in (itemdex['choiceband'], itemdex['choicescarf'], itemdex['choicespecs']):
            pokemon.set_effect(effects.ChoiceLock(move))

    def get_possible_hiddenpowers(self, pokemon):
        possible = [movedex[move] for move in rbstats[rbstats_key(pokemon)]['moves']
                    if move.startswith('hiddenpower')]
        move = possible[0] if len(possible) == 1 else movedex['hiddenpowernotype']
        return move, possible

    def reveal_move(self, pokemon, move):
        """
        Reveal a move that a foe pokemon definitely has (i.e. was not called via copycat, etc.)
        Return success.
        """
        if (move in pokemon.moves or
            move == movedex['struggle'] or
            (move.is_hiddenpower and any(known.is_hiddenpower for known in pokemon.moves))):
            return False

        if len(pokemon.moves) >= 4:
            log.i('Revealing %s when %s already has a full moveset: %s',
                  move, pokemon, pokemon.moves)
            for name in rbstats['zoroark']['moves']:
                known_move = movedex[name]
                if known_move in pokemon.moves:
                    log.i('Forgetting possible zoroark move: %s', known_move)
                    del pokemon.moves[known_move]
            # reset assumed item, because item could have been revealed due to faulty assumptions
            pokemon.item = itemdex['_unrevealed_']
            pokemon.original_item = itemdex['_unrevealed_']
            if move.name in rbstats['zoroark']['moves']:
                log.i('Rejected learning %s due to possibility of zoroark', move)
                return False
        if len(pokemon.moves) >= 4: # if the above handling didn't fix it, something's gone wrong
            log.w("%s's moveset %s is full; cannot reveal %s. Clearing moveset as a last resort.",
                  pokemon, pokemon.moves, move)
            pokemon.moves.clear()

        pokemon.moves[move] = move.max_pp
        log.i("%s's %s was revealed!", pokemon, move)
        if move.is_hiddenpower and move.type != Type.NOTYPE:
            self.recalculate_stats_hiddenpower(pokemon, move.type)

        return True

    def handle_fail(self, msg):
        """
        Ignore:
        |-fail|p1a: Hitmontop
        |-fail|p2a: Accelgor|tox
        |-fail|p2a: Kyogre|Flare Blitz|[from] Primordial Sea
        |-fail|p1a: Kyurem|move: Substitute|[weak]

        Reveal ability:
        |-fail|p2a: Registeel|unboost|[from] ability: Clear Body|[of] p2a: Registeel
        |-fail|p2a: Graveler|unboost|Attack|[from] ability: Hyper Cutter|[of] p2a: Graveler
        |-fail|p2a: Haunter|unboost|accuracy|[from] ability: Keen Eye|[of] p2a: Haunter

        Fail - Healing Wish
        |move|p2a: Latias|Healing Wish|p2a: Latias
        |-fail|p2a: Latias
        """
        for i in range(3, len(msg)):
            if msg[i].startswith('[from] ability:'):
                pokemon = self.get_pokemon_from_msg(msg, i+1)
                ability = abilitydex[normalize_name(msg[i])]
                self.set_ability(pokemon, ability)
        failmon = self.get_pokemon_from_msg(msg)
        if failmon is not None:
            failmon.remove_effect(Volatile.BATONPASS)
            if failmon.last_move_used == movedex['healingwish']:
                failmon.side.remove_effect(SideCondition.HEALINGWISH)

    def handle_immune(self, msg):
        """
        |-immune|p2a: Drifblim|[msg]

        |-immune|p2a: Quagsire|[msg]|[from] ability: Water Absorb
        |-immune|p1a: Uxie|[msg]|[from] ability: Levitate
        etc.

        |-immune|p2a: Muk|[msg]|[from] ability: Synchronize|[of] p1a: Umbreon
        """
        pokemon = self.get_pokemon_from_msg(msg)
        if len(msg) > 3:
            ability = normalize_name(msg[3])
            if ability == 'synchronize':
                pokemon = self.get_pokemon_from_msg(msg, 4)
            self.set_ability(pokemon, abilitydex[ability])

        attacker = self.battlefield.get_foe(pokemon)
        if (attacker is not None and
            attacker.last_move_used in (movedex['outrage'], movedex['petaldance'])
        ):
            attacker.remove_effect(Volatile.LOCKEDMOVE)

        foe = self.foe_side.active_pokemon
        if pokemon is foe:
            if (self.previous_msg[0] == 'move' and
                self.battlefield.last_move_used.type == Type.PSYCHIC and
                not Type.DARK in foe.types and
                not foe.ability == abilitydex['wonderguard']
            ):
                log.i('Detected foe zoroark based on psychic immunity')
                self.detect_illusioned_foe(foe, break_illusion=False)


    def handle_damage(self, msg):
        """
        `|-damage|POKEMON|HP STATUS`, with optionally `|[from] EFFECT|[of] SOURCE`,
        `|[still]` (suppress animation), `|[silent]` (suppress message).

        |-damage|p2a: Goodra|62/100 brn|[from] brn
        |-damage|p1a: Phione|252/268 tox|[from] psn

        |-damage|p1a: Garchomp|35/286|[from] ability: Iron Barbs|[of] p2a: Ferrothorn
        |-damage|p2a: Gengar|50/208 slp|[from] ability: Bad Dreams|[of] p1a: Darkrai
        |-damage|p2a: Mightyena|136/252|[from] ability: Aftermath|[of] p1a: Electrode
        |-damage|p2a: Cresselia|311/381|[from] ability: Dry Skin|[of] p2a: Cresselia
        |-damage|p1a: Arceus|350/381|[from] ability: Liquid Ooze|[of] p2a: Graveler
        |-damage|p2a: Porygon-Z|30/100|[from] item: Life Orb
        |-damage|p2a: Electivire|35/100|[from] item: Rocky Helmet|[of] p1a: Ferrothorn
        |-damage|p2a: Cresselia|264/381|[from] item: Black Sludge
        |-damage|p1a: Throh|169/331|[from] Leech Seed|[of] p2a: Venusaur
        |-damage|p1a: Haxorus|119/244|[from] confusion
        """
        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.is_active, pokemon

        if len(msg) > 3:
            if msg[3].startswith('[from] item'):
                item = itemdex[normalize_name(msg[3])]
                holder = self.get_pokemon_from_msg(msg, 4) if len(msg) > 4 else pokemon
                if holder is not None: # may be fainted e.g. from move that triggered rockyhelmet
                    self.reveal_foe_original_item(holder, item)
                    self.set_item(holder, item)
            elif msg[3].startswith('[from] ability'):
                who = self.get_pokemon_from_msg(msg, 4)
                self.set_ability(who, abilitydex[normalize_name(msg[3])])
            elif normalize_name(msg[3]) == 'leechseed':
                if not pokemon.has_effect(Volatile.LEECHSEED):
                    log.e("%s damaged by leechseed; no Volatile.LEECHSEED present", pokemon, msg)
            elif msg[2].endswith('tox') and msg[3] == '[from] psn':
                tox = pokemon.get_effect(Status.TOX)
                if tox is None:
                    log.e("%s damaged by tox but has no Status.TOX effect: %s", pokemon, msg)
                else:
                    tox.stage += 1
            elif msg[3].endswith('confusion'):
                pokemon.remove_effect(Volatile.LOCKEDMOVE)

        self.set_hp_status(pokemon, msg[2])

    def handle_heal(self, msg):
        """
        Same as damage; check for revealed abilities/items first

        |-heal|p2a: Tyranitar|330/341|[from] ability: Rain Dish
        |-heal|p2a: Moltres|253/267|[from] item: Leftovers
        |-heal|p2a: Blissey|87/100 tox|[from] move: Wish|[wisher] Blissey
        |-heal|p1a: Tyranitar|341/341|[from] move: Healing Wish

        |-enditem|p1a: Exeggutor|Sitrus Berry|[eat]
        |-heal|p1a: Exeggutor|205/288|[from] item: Sitrus Berry
        """
        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.is_active, pokemon

        if len(msg) > 3:
            if msg[3].startswith('[from] item') and 'Berry' not in msg[3]:
                item = itemdex[normalize_name(msg[3])]
                self.reveal_foe_original_item(pokemon, item)
                self.set_item(pokemon, item)
            elif msg[3].startswith('[from] ability'):
                self.set_ability(pokemon, abilitydex[normalize_name(msg[3])])
            elif msg[3] == '[from] move: Wish':
                pokemon.side.remove_effect(SideCondition.WISH)
            elif msg[3] == '[from] move: Healing Wish':
                pokemon.side.remove_effect(SideCondition.HEALINGWISH)

        self.set_hp_status(pokemon, msg[2])

    def handle_faint(self, msg):
        """
        `|faint|POKEMON`

        |faint|p1a: Hitmonchan
        """
        pokemon = self.get_pokemon_from_msg(msg)
        if pokemon is None:
            return # pokemon was already fainted, probably from `|-damage|POKEMON|0 fnt|`
        pokemon.hp = 0
        pokemon.status = Status.FNT

    def handle_status(self, msg):
        """
        `|-status|POKEMON|STATUS[|FROM]`
        |-status|p2a: Goodra|brn
        |-status|p2a: Stunfisk|slp|[from] move: Rest

        |-status|p1a: Raticate|tox|[from] item: Toxic Orb
        |-status|p2a: Blissey|tox|[from] ability: Synchronize|[of] p1a: Musharna
        """
        pokemon = self.get_pokemon_from_msg(msg)

        pokemon.cure_status()

        if len(msg) > 3 and msg[3] == '[from] move: Rest':
            pokemon.is_resting = True
            pokemon.status = Status.SLP
            pokemon.set_effect(statuses.Sleep(pokemon, rest=True))
            return

        self.set_status(pokemon, msg[2])

        if len(msg) > 3:
            if msg[3].startswith('[from] item'):
                item = itemdex[normalize_name(msg[3])]
                self.reveal_foe_original_item(pokemon, item)
                self.set_item(pokemon, item)
            elif msg[3].startswith('[from] ability'):
                other = self.get_pokemon_from_msg(msg, 4)
                self.set_ability(other, abilitydex[normalize_name(msg[3])])
            else:
                log.w('Unhandled part of -status msg: %s', msg)

    def handle_cant(self, msg):
        """
        `|cant|POKEMON|REASON` or `|cant|POKEMON|REASON|MOVE`

        |cant|p2a: Omastar|flinch

        Increment pokemon.turns_slept if its sleeping:
        |cant|p2a: Alomomola|slp

        Reveal a move if shown:
        |cant|p2a: Corsola|move: Taunt|Recover
        |cant|p2a: Ditto|Disable|Bug Bite
        |cant|p2a: Aerodactyl|Focus Punch|Focus Punch
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.remove_effect(Volatile.LOCKEDMOVE)
        if msg[2] == 'slp':
            assert pokemon.status is Status.SLP, (pokemon, pokemon.status)
            if pokemon.turns_slept < 3:
                pokemon.turns_slept += 1

        elif len(msg) > 3:
            self.reveal_move(pokemon, self.get_move(msg[3], pokemon))

    def handle_curestatus(self, msg):
        """
        `|-curestatus|POKEMON|STATUS`
        |-curestatus|p1a: Regirock|slp
        |-curestatus|p1a: Chansey|tox|[from] ability: Natural Cure
        """
        pokemon = self.get_pokemon_from_msg(msg)
        assert pokemon.status is not None, (pokemon, pokemon.status)

        if len(msg) > 3 and msg[3].startswith('[from] ability:'):
            if msg[3] == '[from] ability: Natural Cure':
                self.set_ability(pokemon, abilitydex['naturalcure'])
            else:
                log.e('Unhandled -curestatus msg: %s', msg)

        pokemon.cure_status()

    def handle_cureteam(self, msg):
        """
        `|-cureteam|POKEMON`
        |-cureteam|p1a: Granbull|[from] move: HealBell

        After -cureteam, -curestatus is now sent for every pokemon that was actually cured, so there
        is nothing to do for this message.
        """
        pass

    def set_status(self, pokemon, status):
        assert status in self.STATUS_MAP, status
        pokemon.status = self.STATUS_MAP[status][0]
        pokemon.set_effect(self.STATUS_MAP[status][1](pokemon), override_immunity=True)

    STATUS_MAP = {
        'brn': (Status.BRN, statuses.Burn),
        'slp': (Status.SLP, statuses.Sleep),
        'frz': (Status.FRZ, statuses.Freeze),
        'psn': (Status.PSN, statuses.Poison),
        'tox': (Status.TOX, statuses.Toxic),
        'par': (Status.PAR, statuses.Paralyze),
        Status.BRN: (Status.BRN, statuses.Burn),
        Status.SLP: (Status.SLP, statuses.Sleep),
        Status.FRZ: (Status.FRZ, statuses.Freeze),
        Status.PSN: (Status.PSN, statuses.Poison),
        Status.TOX: (Status.TOX, statuses.Toxic),
        Status.PAR: (Status.PAR, statuses.Paralyze),
    }

    def handle_weather(self, msg):
        """
        `|-weather|WEATHER`
        |-weather|RainDance or |-weather|RainDance|[upkeep] or |-weather|none

        |-weather|Sandstorm|[from] ability: Sand Stream|[of] p2a: Tyranitar
        """
        if msg[1] == 'none':
            self.battlefield.clear_weather()
            return

        weather = Weather.values[msg[1].upper()]

        pokemon = None
        if len(msg) > 2 and msg[2] == '[upkeep]':
            if msg[1].lower() not in ('desolateland', 'primordialsea', 'deltastream'):
                assert self.battlefield._weather is not None, \
                    'Handling upkeep (%s) but _weather is None' % msg[1]
                self.battlefield.get_effect(weather).duration -= 1
        else:
            if len(msg) > 2 and msg[2].startswith('[from] ability'):
                pokemon = self.get_pokemon_from_msg(msg, 3)
                self.set_ability(pokemon, abilitydex[normalize_name(msg[2])])

            self.battlefield.set_weather(weather)

            # if setter is holding damprock/heatrock or item is unrevealed, use 8 turns
            msg1 = msg[1].lower()
            if msg1 in ('sunnyday', 'raindance'):
                if pokemon is None:
                    for active in (self.my_side.active_pokemon, self.foe_side.active_pokemon):
                        if (not active.will_move_this_turn and
                            active.last_move_used == movedex[msg1]
                        ):
                            pokemon = active
                if (pokemon is None or
                    pokemon.item == itemdex['_unrevealed_'] or
                    pokemon.item == itemdex['heatrock' if msg1 == 'sunnyday' else 'damprock']
                ):
                    self.battlefield.get_effect(weather).duration = 8

    def handle_switch(self, msg):
        """
        `|switch|POKEMON|SPECIES|HP STATUS` or `|drag|POKEMON|SPECIES|HP STATUS`

        |switch|p1a: Whiscash|Whiscash, L83, F|318/318
        """
        side = self.get_side_from_msg(msg)
        if side == self.foe_side:
            side.active_illusion = False
        pokemon = self.get_pokemon_from_msg(msg)

        if pokemon is None:     # we are revealing a foe's pokemon
            pokemon = self.create_foe_pokemon_from_msg(side, msg)
            self.reveal_foe_pokemon(pokemon)

        outgoing = side.active_pokemon
        if outgoing is not None:
            bp = outgoing.get_effect(Volatile.BATONPASS)
            if bp is not None:
                bp.on_switch_out(outgoing, incoming=pokemon, battle=None)
            foe = self.battlefield.get_foe(pokemon)
            if foe is not None:
                foe.remove_effect(Volatile.PARTIALTRAP, force=True)
                foe.remove_effect(Volatile.TRAPPED, force=True)
            if outgoing.ability == abilitydex['regenerator'] and not outgoing.is_fainted():
                outgoing.hp = min(outgoing.max_hp, outgoing.hp + outgoing.max_hp / 3)
            outgoing.is_active = False
            outgoing._effect_index.clear()
            outgoing.effect_handlers = {key: list() for key in outgoing.effect_handlers}
            outgoing.boosts = Boosts()
            outgoing.types = list(outgoing.pokedex_entry.types) # protean etc. may have changed type
            outgoing.ability = outgoing.base_ability
            outgoing.illusion = False
            if outgoing.is_transformed:
                outgoing.revert_transform()
            elif not outgoing.is_fainted():
                if outgoing.name == 'aegislashblade':
                    self.forme_change(outgoing, 'aegislash')
                elif (outgoing.base_species == 'castform' and
                      outgoing.name != 'castform'):
                    self.forme_change(outgoing, 'castform')
                elif outgoing.name == 'meloettapirouette':
                    self.forme_change(outgoing, 'meloetta')

        side.active_pokemon = pokemon
        pokemon.is_active = True
        pokemon.last_move_used = None
        pokemon.turns_out = 0
        pokemon.will_move_this_turn = False
        pokemon.item_used_this_turn = None
        pokemon.ability = pokemon.base_ability
        if self.is_foe(pokemon):
            pokemon.save_pre_switch_state()

        self.set_hp_status(pokemon, msg[3])
        if pokemon.status is not None:
            self.set_status(pokemon, pokemon.status)

        pokemon.set_effect(pokemon.ability())

        if pokemon.item is not None:
            self.set_item(pokemon, pokemon.item, reset=True)

        if pokemon.name == 'zoroark' and not msg[1].endswith('Zoroark'):
            pokemon.illusion = True

    handle_drag = handle_switch

    def create_foe_pokemon_from_msg(self, side, msg):
        assert side == self.foe_side, (side.index, self.foe_side)
        details = msg[2].split(', ')
        if 'shiny' in details:
            details.remove('shiny')
        name = normalize_name(details[0])
        level = int(details[1].lstrip('L'))
        assert 1 <= level <= 100, 'level=%r' % level
        gender = details[2] if len(details) > 2 else None
        assert gender in ('M', 'F', None), gender
        return FoePokemon(pokedex[name], level, moves=[],
                          side=side, ability=abilitydex['_unrevealed_'],
                          item=itemdex['_unrevealed_'], gender=gender)

    def reveal_foe_pokemon(self, pokemon):
        # reveal item/ability/moves that are known from statistics
        rb_index = rbstats_key(pokemon)
        stats = rbstats[rb_index]
        if len(stats['item']) == 1:
            pokemon.item = pokemon.original_item = itemdex[tuple(stats['item'])[0]]
        if len(stats['ability']) == 1 and pokemon.ability == abilitydex['_unrevealed_']:
            pokemon.ability = abilitydex[tuple(stats['ability'])[0]]
            self.set_base_ability(pokemon, pokemon.ability)
        for move, pmove in rbstats.probability[rb_index]['moves'].items():
            if pmove == 1.0:
                self.reveal_move(pokemon, movedex[move])

        self.foe_side.reveal(pokemon)

    def handle_replace(self, msg):
        """
        |replace|p1a: Zoroark|Zoroark, L78, F|53/100 par
        """
        if not msg[1].endswith('Zoroark'):
            log.e('Got replace msg for non-Zoroark pokemon', msg)

        side = self.get_side_from_msg(msg)

        if side == self.my_side:
            pokemon = side.active_pokemon
            assert pokemon.name == 'zoroark', pokemon
            pokemon.illusion = False
        elif side.active_illusion:
            foe = side.active_pokemon
            assert foe.name == 'zoroark', foe
            foe.illusion = False
            side.active_illusion = False
        else:
            self.detect_illusioned_foe(side.active_pokemon, break_illusion=True)

    def get_zoroark(self, side):
        for pokemon in side.team:
            if pokemon.base_species == 'zoroark':
                return pokemon
        log.d("No zoroark found on side %s", side.index)
        return None

    def detect_illusioned_foe(self, decoy, break_illusion):
        """
        Called upon the revelation that the foe is actually an illusioned zoroark.

        Swap out the current active pokemon for the foe's zoroark, possibly newly revealing
        it. All effects are transferred from the current pokemon to zoroark, and the active
        pokemon is placed on the bench and rolled back to its previous state as though it never
        had been sent out.
        """
        assert self.is_foe(decoy), decoy
        assert decoy.is_active, decoy
        assert decoy == self.foe_side.active_pokemon, self.foe_side
        assert not (not break_illusion and decoy.name == 'zoroark'), decoy

        foe_side = self.foe_side
        foe_zoroark = self.get_zoroark(foe_side)
        if foe_zoroark is None:
            log.i("Revealing foe's zoroark for the first time")
            foe_zoroark = FoePokemon(pokedex['zoroark'], rbstats['zoroark']['level'].keys()[0],
                                     moves=[], side=foe_side, ability=abilitydex['illusion'],
                                     item=itemdex['_unrevealed_'], gender='M')
            self.reveal_foe_pokemon(foe_zoroark)
        log.i("%s was a decoy for foe's zoroark", decoy)

        decoy.is_active = False
        foe_side.active_pokemon = foe_zoroark
        foe_zoroark.is_active = True
        foe_zoroark.last_move_used = decoy.last_move_used
        foe_zoroark.turns_out = decoy.turns_out
        foe_zoroark.will_move_this_turn = decoy.will_move_this_turn
        foe_zoroark.item_used_this_turn = decoy.item_used_this_turn

        decoy.remove_effect(ITEM, force=True)
        decoy.remove_effect(ABILITY, force=True)

        foe_zoroark._effect_index = decoy._effect_index
        decoy._effect_index = {}
        foe_zoroark.effect_handlers = decoy.effect_handlers
        decoy.effect_handlers = {key: list() for key in decoy.effect_handlers}
        foe_zoroark.status = decoy.status
        foe_zoroark.turns_slept = decoy.turns_slept
        foe_zoroark.boosts = decoy.boosts
        decoy.boosts = Boosts()
        foe_zoroark.hp = int(round((float(decoy.hp) / decoy.max_hp) * foe_zoroark.max_hp))
        foe_zoroark.illusion = not break_illusion
        foe_zoroark.set_effect(foe_zoroark.ability())
        self.foe_side.active_illusion = not break_illusion

        for move in decoy.moves:
            if (move not in decoy.pre_switch_state.moves and
                move.name in rbstats['zoroark']['moves']):
                self.reveal_move(foe_zoroark, move)

        decoy.ability = decoy.base_ability
        decoy.reset_pre_switch_state()
        # forget any possibly false moves that could have been revealed from a previous illusion
        for move in decoy.moves.copy():
            if move.name in rbstats['zoroark']['moves']:
                del decoy.moves[move]

        return foe_zoroark

    def handle_item(self, msg):
        """
        `|-item|POKEMON|ITEM`

        |-item|p1a: Magnezone|Air Balloon
        |-item|p2a: Butterfree|Choice Scarf|[from] move: Trick
        |-item|p1a: Exeggutor|Sitrus Berry|[from] ability: Harvest
        |-item|p2a: Ambipom|Sitrus Berry|[from] ability: Pickup

        |-item|p1a: Weavile|Leftovers|[from] ability: Pickpocket|[of] p2a: Malamar
        |-item|p2a: Delphox|Sitrus Berry|[from] ability: Magician|[of] p1a: Azumarill
          (need to enditem on the victim, this isn't shown as a separate message)

        |-item|p2a: Suicune|Leftovers|[from] ability: Frisk|[of] p1a: Dusknoir|[identify]

        Identifies a currently held item
        """
        pokemon = self.get_pokemon_from_msg(msg)
        item = itemdex[normalize_name(msg[2])]

        # Tricking some items e.g. airballoon triggers two -item messages:
        #   |-activate|p1a: Zoroark|move: Trick|[of] p2a: Rotom
        #   |-item|p2a: Rotom|Choice Scarf|[from] move: Trick
        #   |-item|p1a: Zoroark|Air Balloon
        #   |-item|p1a: Zoroark|Air Balloon|[from] move: Trick
        # We need to detect that it's being tricked in the first airballoon message
        trick = 'Trick' in ' '.join(self.previous_msg)

        if len(msg) > 3 or trick:
            if msg[3].startswith('[from] ability:'):
                ability = normalize_name(msg[3])

                if ability == 'frisk':
                    frisker = self.get_pokemon_from_msg(msg, 4)
                    self.set_ability(frisker, abilitydex['frisk'])
                    self.reveal_foe_original_item(pokemon, item)
                else:
                    self.set_ability(pokemon, abilitydex[ability])
                    if ability in ('pickpocket', 'magician'):
                        victim = self.get_pokemon_from_msg(msg, 4)
                        self.reveal_foe_original_item(victim, item)
                        self.remove_item(victim)
            elif msg[3].endswith('Trick') or trick:
                trick = True
                foe = self.battlefield.get_foe(pokemon)
                self.reveal_foe_original_item(foe, item)
            else:
                log.w('Unhandled part of -item msg: %s', msg)

        elif item == itemdex['airballoon']:
            self.reveal_foe_original_item(pokemon, item)
        else:
            log.w('Unhandled part of -item msg: %s', msg)

        self.set_item(pokemon, item, reset=trick)

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
        if pokemon is None:
            return
        item = itemdex[normalize_name(msg[2])]

        self.reveal_foe_original_item(pokemon, item)

        self.remove_item(pokemon)
        pokemon.last_berry_used = None

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

    def set_item(self, pokemon, item, reset=False):
        """
        reset=True re-sets the item even if the pokemon already holds that item
        """
        if pokemon.item == item and not reset:
            return

        self.remove_item(pokemon)
        pokemon.item = item
        if pokemon.is_active:
            pokemon.set_effect(item())
        pokemon.remove_effect(Volatile.UNBURDEN, force=True)
        pokemon.remove_effect(Volatile.CHOICELOCK, force=True)

    def remove_item(self, pokemon):
        pokemon.remove_effect(ITEM, force=True)
        pokemon.remove_effect(Volatile.CHOICELOCK, force=True)
        pokemon.item = None
        if pokemon.ability == abilitydex['unburden']:
            pokemon.set_effect(effects.UnburdenVolatile())

    def reveal_foe_original_item(self, pokemon, item):
        if (self.is_foe(pokemon) and
            itemdex['_unrevealed_'] in (pokemon.item, pokemon.original_item)):
            pokemon.original_item = item

    def handle_ability(self, msg):
        """
        |-ability|p2a: Rayquaza|Air Lock
        |-ability|p1a: Granbull|Intimidate|boost
        |-ability|p1a: Kyurem|Teravolt
        |-ability|p1a: Pyroar|Unnerve|p2: 1-BillsPC
        |-ability|p1a: Alakazam|Levitate|[from] ability: Trace|[of] p2a: Eelektross
        """
        pokemon = self.get_pokemon_from_msg(msg)
        ability = abilitydex[normalize_name(msg[2])]

        if len(msg) > 3 and msg[3].split()[-1] == 'Trace':
            self.set_ability(pokemon, abilitydex['trace'])
            foe = self.battlefield.get_foe(pokemon)
            self.set_ability(foe, ability)

        self.set_ability(pokemon, ability)

    def set_ability(self, pokemon, ability):
        """
        Changes the current ability, e.g. from mummy or trace, or a revealing message like -activate

        If the base ability was unrevealed, set it.
        """
        if pokemon is None:
            return
        if pokemon.ability == ability:
            log.d("%s's ability is already %s", pokemon, ability)
            return
        else:
            log.d("%s's ability was changed from %s", pokemon, pokemon.ability)

        pokemon.remove_effect(ABILITY, force=True)
        pokemon.ability = ability
        if pokemon.is_active:
            pokemon.set_effect(ability())

        if pokemon.base_ability == abilitydex['_unrevealed_'] and not pokemon.is_transformed:
            self.set_base_ability(pokemon, ability)

    def set_base_ability(self, pokemon, ability, formechange=False):
        """
        Used when a foe's base_ability is discovered/revealed.
        Sets only the base_ability, not current ability.
        """
        if pokemon.base_ability == ability:
            log.w("%s's base_ability is already %s", pokemon, ability)
            return
        else:
            if (not formechange and
                pokemon.base_ability != abilitydex['_unrevealed_'] and
                len(pokemon.pokedex_entry.abilities) == 1 and
                ability != pokemon.pokedex_entry.abilities[0]
            ):
                log.w("Overwriting %s's base_ability %s with %s!:\n%r",
                      pokemon, pokemon.base_ability, ability, pokemon)
            if ability.name not in pokemon.pokedex_entry.abilities:
                log.w("Giving %s a base_ability %s that it shouldn't get:\n%r",
                      pokemon, ability, pokemon)

            pokemon.base_ability = ability

    def handle_boost(self, msg):
        """
        `|-boost|POKEMON|STAT|AMOUNT`
        e.g. |-boost|p2a: Hawlucha|atk|2
        """
        pokemon = self.get_pokemon_from_msg(msg)
        boost = self.BOOST_MAP.get(msg[2], msg[2])
        pokemon.boosts[boost] += int(msg[3])
        if pokemon.boosts[boost] > 6:
            pokemon.boosts[boost] = 6

    def handle_unboost(self, msg):
        pokemon = self.get_pokemon_from_msg(msg)
        boost = self.BOOST_MAP.get(msg[2], msg[2])
        pokemon.boosts[boost] -= int(msg[3])
        if pokemon.boosts[boost] < -6:
            pokemon.boosts[boost] = -6

    BOOST_MAP = {'evasion': 'evn', 'accuracy': 'acc'}

    def handle_setboost(self, msg):
        """
        Only used by bellydrum, angerpoint
        |-setboost|p2a: Azumarill|atk|6|[from] move: Belly Drum
        |-setboost|p2a: Primeape|atk|12|[from] ability: Anger Point
        """
        pokemon = self.get_pokemon_from_msg(msg)
        pokemon.boosts[msg[2]] = clamp_int(int(msg[3]), -6, 6)

        if len(msg) > 4 and msg[4].startswith('[from] ability'):
            self.set_ability(pokemon, abilitydex[normalize_name(msg[4])])

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
        if pokemon is None:
            return

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

        |-activate|p2a: Goodra|confusion
        |-activate|p1a: Dusknoir|Substitute|[damage]
        |-activate|p1a: Chansey|move: Infestation|[of] p2a: Fraxure
        |-activate|p2a: Aerodactyl|ability: Mummy|Snow Warning|[of] p1a: Chansey
        |-activate|p2a: Chesnaught|Protect (protect blocked an attack - remove LOCKEDMOVE)

        Reveal only:
        |-activate|p2a: Seviper|ability: Shed Skin
        |-activate|p1a: Machoke|ability: Aroma Veil|[of] p1a: Machoke
        |-activate|p2a: Aerodactyl|ability: Hydration
        |-activate|p1a: Fraxure|ability: {Immunity, Limber, Insomnia, Sweet Veil,
          Vital Spirit, Water Veil} (only when statused via Mold Breaker or ability Traced, etc.)
        |-activate|p1a: Shedinja|ability: Wonder Guard
        |-activate|p2a: Groudon|ability: Sticky Hold
        |-activate|p2a: Charizard|ability: Suction Cups
        |-activate|p1a: Musharna|ability: Synchronize

        Ignored:
        |-activate|p1a: Banette|Destiny Bond (destinybond's on_faint activated)
        |-activate|p2a: Rotom-Fan|move: Trick|[of] p1a: Chimecho (trick was successful)
        |-activate|p1a: Exeggutor|move: Sticky Web (stickyweb lowered spe on switch in)
        |-activate|p2a: Leafeon|Attract|[of] p1a: Fraxure (attract roll)
        |-activate|p1a: Machoke|Custap Berry
        |-activate|p1a: Bastiodon|move: Pursuit (Bastiodon is switching out and gets caught)
        |-activate|p2a: Aerodactyl|move: Struggle (about to use struggle)
        |-activate||deltastream (deltastream reduced the effectiveness of a move)
        """
        effect = normalize_name(msg[2])
        if effect in ('destinybond', 'trick', 'stickyweb', 'attract', 'custapberry',
                      'pursuit', 'struggle', 'trapped', 'deltastream'):
            return
        pokemon = self.get_pokemon_from_msg(msg)
        if pokemon is None:
            log.i('No pokemon for msg: %s', msg)
            return

        if effect in ('shedskin', 'aromaveil', 'hydration', 'immunity', 'limber', 'insomnia',
                      'sweetveil', 'vitalspirit', 'waterveil', 'wonderguard', 'stickyhold',
                      'suctioncups', 'synchronize'):
            self.set_ability(pokemon, abilitydex[effect])
        elif effect == 'confusion':
            assert pokemon.has_effect(Volatile.CONFUSE), pokemon
            pokemon.get_effect(Volatile.CONFUSE).turns_left -= 1
        elif effect == 'substitute':
            # The substitute took damage, but did not break
            sub = pokemon.get_effect(Volatile.SUBSTITUTE)
            assert sub is not None, pokemon
            foe = self.battlefield.get_foe(pokemon)
            assert foe is not None, pokemon
            move = foe.last_move_used
            assert move is not None, foe
            expected_damage = self.battle.calculate_expected_damage(foe, move, pokemon, self.crit)
            if expected_damage is None or expected_damage > sub.hp:
                sub.hp = 1      # this normally shouldn't happen
                log.i("Expected damage for %r attacking %r with %s was %s, "
                      "but did not break its substitute", foe, pokemon, move, expected_damage)
            else:
                sub.hp -= expected_damage
        elif effect == 'infestation':
            # The infestation effect is starting
            foe = self.battlefield.get_foe(pokemon)
            assert foe is not None, pokemon
            pokemon.set_effect(effects.PartialTrap())
        elif effect == 'mummy':
            self.set_ability(pokemon, abilitydex['mummy'])
            foe = self.battlefield.get_foe(pokemon)
            self.set_ability(foe, abilitydex[normalize_name(msg[3])]) # old ability was revealed
            self.set_ability(foe, abilitydex['mummy'])
        elif effect == 'protect':
            foe = self.battlefield.get_foe(pokemon)
            assert foe is not None
            foe.remove_effect(Volatile.LOCKEDMOVE, force=True)
        else:
            log.e('Unhandled -activate msg: %s', msg)

    def handle_crit(self, msg):
        """
        |-crit|p2a: Cresselia

        Used by handle_activate for estimating damage to a substitute that does not break
        """
        self.crit = True

    def handle_singleturn(self, msg):
        """
        |-singleturn|p1a: Florges|Protect
        |-singleturn|p2a: Deoxys|move: Magic Coat
        |-singleturn|p2a: Aerodactyl|move: Focus Punch
        """
        pokemon = self.get_pokemon_from_msg(msg)
        move = normalize_name(msg[2])

        if move == 'protect':
            stall = pokemon.get_effect(Volatile.STALL)
            if stall is None:
                pokemon.set_effect(effects.StallCounter())
            else:
                stall.duration = 2       # reset expiry
                stall.denominator *= 3   # 3x less likely to succeed consecutively
        elif move == 'focuspunch':
            # this is safe because focuspunch is exempt from copycat, sleeptalk, etc.
            self.reveal_move(pokemon, movedex['focuspunch'])
        elif move != 'magiccoat': # ignore magiccoat
            log.e('Unhandled -singleturn msg: %s', msg)

    def handle_singlemove(self, msg):
        """
        |-singlemove|p1a: Banette|Destiny Bond
        """
        pokemon = self.get_pokemon_from_msg(msg)
        move = normalize_name(msg[2])

        if move == 'destinybond':
            pokemon.set_effect(effects.DestinyBond())
        else:
            log.e('Unhandled -singlemove msg: %s', msg)

    def handle_start(self, msg):
        """
        |-start|p2a: Suicune|move: Taunt
        |-start|p1a: Kyurem|confusion|[fatigue]
        |-start|p2a: Goodra|confusion
        |-start|p1a: Aggron|Autotomize (no end, handled in |move|)
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
        |-start|p1a: Heatmor|ability: Flash Fire
        |-start|p2a: Ditto|Disable|Bug Bite
        |-start|p2a: Leafeon|Attract|[from] ability: Cute Charm|[of] p1a: Fraxure
        |-start|p1a: Fraxure|Magnet Rise
        """
        pokemon = self.get_pokemon_from_msg(msg)
        effect = normalize_name(msg[2])
        if effect == 'taunt':
            duration = 3 if pokemon.will_move_this_turn else 4
            pokemon.set_effect(effects.Taunt(duration))
        elif effect == 'confusion':
            pokemon.set_effect(effects.Confuse())
            if len(msg) > 3 and msg[3] == '[fatigue]':
                pokemon.remove_effect(Volatile.LOCKEDMOVE)
        elif effect == 'autotomize':
            effect = pokemon.get_effect(Volatile.AUTOTOMIZE)
            if effect is None:
                pokemon.set_effect(effects.Autotomize())
            else:
                effect.multiplier += 1
        elif effect == 'substitute':
            pokemon.set_effect(effects.Substitute(pokemon.max_hp / 4))
            pokemon.remove_effect(Volatile.PARTIALTRAP)
        elif effect == 'yawn':
            pokemon.set_effect(effects.Yawn())
        elif effect == 'leechseed':
            pokemon.set_effect(effects.LeechSeed())
        elif effect == 'encore':
            duration = 3 if pokemon.will_move_this_turn else 4
            move = pokemon.last_move_used
            if move is None:
                log.w('%s got encored, but its last move was None!', pokemon)
                return
            pokemon.set_effect(effects.Encore(move, duration))
        elif effect.startswith('perish'):
            stage = int(effect[-1])
            if stage == 3 and not pokemon.has_effect(Volatile.PERISHSONG):
                pokemon.set_effect(effects.PerishSong())
            else:
                perishsong = pokemon.get_effect(Volatile.PERISHSONG)
                if perishsong is None:
                    log.w("%s: %s has no PerishSong effect!", msg, pokemon)
                    perishsong = effects.PerishSong()
                    pokemon.set_effect(perishsong)
                perishsong.duration = stage + 1 # it will get decremented at the next |turn|
        elif effect == 'typechange':
            type = Type.values[msg[3].upper()]
            pokemon.types = [type, None]
        elif effect == 'slowstart':
            pokemon.set_effect(effects.SlowStartVolatile())
        elif effect == 'flashfire':
            self.set_ability(pokemon, abilitydex['flashfire'])
            pokemon.set_effect(effects.FlashFireVolatile())
        elif effect == 'disable':
            duration = 4 if pokemon.will_move_this_turn else 5
            move = self.get_move(msg[3], pokemon)
            if move not in pokemon.moves:
                log.w("%s: %s isn't in %s's moveset: %s", msg, move, pokemon, pokemon.moves)
            pokemon.set_effect(effects.Disable(move, duration))
        elif effect == 'attract':
            foe = self.battlefield.get_foe(pokemon)
            self.set_ability(foe, abilitydex['cutecharm'])
            pokemon.set_effect(effects.Attract(foe))
        elif effect == 'magnetrise':
            pokemon.set_effect(effects.MagnetRise())
        else:
            log.e('Unhandled -start msg: %s', msg)

    def handle_end(self, msg):
        """
        |-end|p1a: Cacturne|move: Taunt
        |-end|p2a: Goodra|confusion
        |-end|p1a: Jirachi|Substitute
        |-end|p2a: Ho-Oh|move: Yawn|[silent]
        |-end|p1a: Fraxure|Leech Seed|[from] move: Rapid Spin|[of] p1a: Fraxure
        |-end|p2a: Quagsire|Encore
        |-end|p2a: Regigigas|Slow Start|[silent]
        |-end|p2a: Heatran|ability: Flash Fire|[silent]
        |-end|p1a: Zoroark|Illusion
        |-end|p2a: Ditto|Disable
        |-end|p2a: Leafeon|Attract|[silent]
        |-end|p2a: Ditto|Magnet Rise
        |-end|p2a: Chansey|Infestation|[partiallytrapped]
        |-end|p2a: Zoroark|Illusion
        """
        if msg[2] == 'Illusion':
            return

        pokemon = self.get_pokemon_from_msg(msg)
        if pokemon is None:
            return

        effect = self.END_EFFECT_MAP.get(normalize_name(msg[2]))
        if effect is not None:
            pokemon.remove_effect(effect, force=True)
        else:
            log.e('Unhandled -end msg: %s', msg)

    END_EFFECT_MAP = {
        'taunt': Volatile.TAUNT,
        'confusion': Volatile.CONFUSE,
        'substitute': Volatile.SUBSTITUTE,
        'yawn': Volatile.YAWN,
        'leechseed': Volatile.LEECHSEED,
        'encore': Volatile.ENCORE,
        'slowstart': Volatile.SLOWSTART,
        'flashfire': Volatile.FLASHFIRE,
        'disable': Volatile.DISABLE,
        'attract': Volatile.ATTRACT,
        'magnetrise': Volatile.MAGNETRISE,
        'infestation': Volatile.PARTIALTRAP,
    }

    def handle_sidestart(self, msg):
        """
        |-sidestart|p2: 1-BillsPC|Reflect
        |-sidestart|p2: 1-BillsPC|move: Light Screen
        |-sidestart|p1: 1-BillsPC|move: Stealth Rock
        |-sidestart|p1: 1-BillsPC|move: Toxic Spikes
        |-sidestart|p1: 1-BillsPC|Spikes
        |-sidestart|p1: 1-BillsPC|move: Sticky Web
        |-sidestart|p2: 1-BillsPC|move: Tailwind
        |-sidestart|p1: 1-BillsPC|Safeguard
        """
        side = self.get_side_from_msg(msg)
        effect = normalize_name(msg[2])

        if effect in ('reflect', 'lightscreen'):
            user = side.active_pokemon
            assert user is not None, user
            duration = 8 if user.item in (itemdex['lightclay'], itemdex['_unrevealed_']) else 5
            if effect == 'reflect':
                side.set_effect(effects.Reflect(duration))
            else:
                side.set_effect(effects.LightScreen(duration))
        elif effect == 'stealthrock':
            if side.has_effect(Hazard.STEALTHROCK):
                log.w('%s already has stealthrock: %s', side, msg)
            side.set_effect(effects.StealthRock())
        elif effect == 'toxicspikes':
            toxicspikes = side.get_effect(Hazard.TOXICSPIKES)
            if toxicspikes is None:
                side.set_effect(effects.ToxicSpikes())
            else:
                if toxicspikes.layers >= 2:
                    log.w('%s already has 2 layers of toxicspikes (%s): %s', side, toxicspikes, msg)
                    return
                toxicspikes.layers += 1
        elif effect == 'spikes':
            spikes = side.get_effect(Hazard.SPIKES)
            if spikes is None:
                side.set_effect(effects.Spikes())
            else:
                if spikes.layers >= 3:
                    log.w('%s already has 3 layers of spikes (%s): %s', side, spikes, msg)
                    return
                spikes.layers += 1
        elif effect == 'stickyweb':
            if side.has_effect(Hazard.STICKYWEB):
                log.w('%s already has stickyweb: %s', side, msg)
            side.set_effect(effects.StickyWeb())
        elif effect == 'tailwind':
            if side.has_effect(SideCondition.TAILWIND):
                log.w('%s already has tailwind: %s', side, msg)
            side.set_effect(effects.Tailwind())
        elif effect == 'safeguard':
            if side.has_effect(SideCondition.SAFEGUARD):
                log.w('%s already has tailwind: %s', side, msg)
            side.set_effect(effects.Safeguard())
        else:
            log.e('Unhandled -sidestart msg: %s', msg)

    def handle_sideend(self, msg):
        """
        |-sideend|p1: Oafkiedawg|Reflect
        |-sideend|p1: 1-BillsPC|Stealth Rock|[from] move: Defog|[of] p1a: Togekiss
        ... (same as sidestart)
        """
        side = self.get_side_from_msg(msg)
        effect = self.SIDEEND_EFFECT_MAP.get(normalize_name(msg[2]))
        if effect is not None:
            side.remove_effect(effect)
        else:
            log.e('Unhandled -sideend msg: %s', msg)

    SIDEEND_EFFECT_MAP = {
        'reflect': SideCondition.REFLECT,
        'lightscreen': SideCondition.LIGHTSCREEN,
        'stealthrock': Hazard.STEALTHROCK,
        'toxicspikes': Hazard.TOXICSPIKES,
        'spikes': Hazard.SPIKES,
        'stickyweb': Hazard.STICKYWEB,
        'tailwind': SideCondition.TAILWIND,
        'safeguard': SideCondition.SAFEGUARD,
    }

    def handle_fieldstart(self, msg):
        """
        |-fieldstart|move: Trick Room|[of] p1a: Spinda
        """
        effect = normalize_name(msg[1])

        if effect == 'trickroom':
            if self.battlefield.has_effect(PseudoWeather.TRICKROOM):
                log.w('Battlefield already has trickroom: %s', msg)
            self.battlefield.set_effect(effects.TrickRoom())
        else:
            log.e('Unhandled -fieldstart msg: %s', msg)

    def handle_fieldend(self, msg):
        """
        |-fieldend|move: Trick Room
        """
        effect = normalize_name(msg[1])

        if effect == 'trickroom':
            self.battlefield.remove_effect(PseudoWeather.TRICKROOM)
        else:
            log.e('Unhandled -fieldstart msg: %s', msg)

    def handle_prepare(self, msg):
        """
        Marks the initial usage of a two-turn move.
        |-prepare|p1a: Castform|Solar Beam|p2a: Corsola
        """
        pokemon = self.get_pokemon_from_msg(msg)
        move = self.get_move(msg[2], pokemon)
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

        pokemon.transform_into(foe, battle=None, client=True)

        if self.is_ally(pokemon):
            # The moves might be in the wrong order, so reset them according to the current request.
            # Set any of the foe's moves that are revealed by transforming.
            pokemon.moves = {}

            jditto = self.request['side']['pokemon'][0]
            if normalize_name(jditto['ident']) != pokemon.base_species:
                # A different pokemon ends up active (probably due to a |drag|), so we can't peek at
                # the opponent's moves
                return

            for move in jditto['moves']:
                my_move = movedex[normalize_name(move.rstrip(string.digits))]
                pokemon.moves[my_move] = 5

                if my_move.is_hiddenpower:
                    foe_move, _ = self.get_possible_hiddenpowers(foe)
                else:
                    foe_move = my_move
                self.reveal_move(foe, foe_move)

    def handle_formechange(self, msg):
        """
        |-formechange|p1a: Castform|Castform-Rainy|[msg]
        |-formechange|p2a: Meloetta|Meloetta|[msg]
        |-formechange|p2a: Meloetta|Meloetta-Pirouette|[msg]
        |-formechange|p2a: Aegislash|Aegislash-Blade|[from] ability: Stance Change
        |-formechange|p1a: Aegislash|Aegislash|[from] ability: Stance Change
        |-formechange|p1a: Cherrim|Cherrim-Sunshine|[msg]
        |-formechange|p1a: Shaymin|Shaymin|[msg]
        """
        pokemon = self.get_pokemon_from_msg(msg)
        forme = normalize_name(msg[2])

        self.forme_change(pokemon, forme)

    def handle_detailschange(self, msg):
        """
        |detailschange|p1a: Mewtwo|Mewtwo-Mega-X, L73
        |detailschange|p2a: Medicham|Medicham-Mega, L75, M
        |detailschange|p2a: Kyogre|Kyogre-Primal, L73
        """
        pokemon = self.get_pokemon_from_msg(msg)
        forme = normalize_name(msg[2].split(',')[0])

        self.forme_change(pokemon, forme)
        if forme == 'kyogreprimal' and pokemon.item != itemdex['blueorb']:
            self.reveal_foe_original_item(pokemon, itemdex['blueorb'])
            self.set_item(pokemon, itemdex['blueorb'])
        if forme == 'groudonprimal' and pokemon.item != itemdex['redorb']:
            self.reveal_foe_original_item(pokemon, itemdex['redorb'])
            self.set_item(pokemon, itemdex['redorb'])

    def forme_change(self, pokemon, forme):
        pokemon.forme_change(forme, client=True)
        new_ability = abilitydex[pokemon.pokedex_entry.abilities[0]]
        self.set_ability(pokemon, new_ability)
        if pokemon.base_ability != new_ability:
            self.set_base_ability(pokemon, new_ability, formechange=True)

    def handle_mega(self, msg):
        """
        |-mega|p1a: Mewtwo|Mewtwo|Mewtwonite X

        The actual tranformation is handled by -detailschange
        """
        pokemon = self.get_pokemon_from_msg(msg)
        megastone = itemdex[normalize_name(msg[3])]

        pokemon.side.has_mega_evolved = True
        pokemon.is_mega = True

        self.reveal_foe_original_item(pokemon, megastone)
        if pokemon.item != megastone:
            self.set_item(pokemon, megastone)

    def handle_callback(self, msg):
        """
        |callback|trapped|0
        """
        if msg[1] == 'trapped':
            log.e("Tried to switch out while trapped: switch choice was rejected")
            if self.AI:
                self.make_move(self.request, switch_rejected=True)
        else:
            log.e("Unhandled |callback| message: %s", msg)

    def handle_win(self, msg):
        """
        |win|1-BillsPC
        """
        if msg[1] == self.name:
            log.i('I win!')
            self.battlefield.win = self.my_side.index
        elif msg[1] == self.foe_name:
            log.i('I lost.')
            self.battlefield.win = self.foe_side.index
        else:
            log.w("The game is over, but I don't know who won: %s", msg)
            self.battlefield.win = -1

    def handle_tie(self, msg):
        """
        |tie
        """
        log.i('We tied?')

    def handle_prematureend(self, msg):
        """
        |prematureend
        """
        log.i('Game over... what happened?')

    def _validate_my_team(self):
        """
        Validate that the current team state matching what is being sent from the server.
        Correct the state if it doesn't match.
        """
        request = self.request

        # strip digits from moves (e.g. hiddenpowerfire60)
        if request.get('active') is not None:
            for move in request['active'][0]['moves']:
                move['id'] = move['id'].rstrip(string.digits)
        for reqmon in request['side']['pokemon']:
            reqmon['moves'] = [move_.rstrip(string.digits) for move_ in reqmon['moves']]

        active = self.my_side.active_pokemon
        check(active.is_active, "Active pokemon %s is not active", active)
        if request.get('active') is not None:
            can_mega_evo = request['active'][0].get('canMegaEvo', False)
            check(can_mega_evo == active.can_mega_evolve,
                  "%s's mega-evolution state is incorrect", active)

            reqmoves = sorted(request['active'][0]['moves'], key=lambda move: move['id'])
            if len(reqmoves) == 1:
                check(active.has_effect(Volatile.TWOTURNMOVE) or
                      active.has_effect(Volatile.LOCKEDMOVE) or
                      reqmoves[0]['id'] in ('struggle', 'transform'),
                      '%s has one move available but it appears invalid?', active)
            else:
                choices = active.get_move_choices()
                reset_moves_needed = False
                for i, move in enumerate(sorted(active.moves, key=lambda move: move.name)):
                    if not check(reqmoves[i]['id'] == move.name or
                                 (reqmoves[i]['id'] == 'hiddenpower' and
                                  move.name.startswith('hiddenpower')),
                                 "%s: request moves %s don't match %s", active, reqmoves, move):
                        reset_moves_needed = True
                        break
                    active.pp[move] = reqmoves[i].get('pp', move.max_pp)
                if reset_moves_needed:
                    for jmove in request['active'][0]['moves']:
                        move = movedex[normalize_name(jmove['move'])]
                        active.moves[move] = jmove.get('pp', move.max_pp)

                for i, move in enumerate(sorted(active.moves, key=lambda move: move.name)):
                    if reqmoves[i]['disabled']:
                        check(move not in choices,
                              "%s's %s should be disabled, but it isn't", active, move)
                    else:
                        check(move in choices,
                              "%s's %s should be selectable, but it isn't", active, move)

            if (request['active'][0].get('trapped') or
                request['active'][0].get('maybeTrapped')):
                check(not active.get_switch_choices(),
                      "%s has available switch choices, but should be trapped", active)

        for pokemon in self.my_side.team:
            if not pokemon.is_active:
                check(not pokemon.effects, '%s has effects but is benched' % pokemon)

            if pokemon.status not in (None, Status.FNT) and pokemon.is_active:
                if not check(pokemon.has_effect(pokemon.status),
                             '%s\n has status but no effect', pokemon):
                    self.set_status(pokemon, pokemon.status)

            reqteam = request['side']['pokemon']
            reqmon = [p for p in reqteam
                      if pokemon.base_species.startswith(normalize_name(p['ident']))]
            check(len(reqmon) > 0,
                  "%s didn't match with any: %s", pokemon, [p['ident'] for p in reqteam])
            check(len(reqmon) == 1,
                  "%s matched with more than 1: %s", pokemon, [p['ident'] for p in reqteam])
            reqmon = reqmon[0]

            condition = reqmon['condition'].split()
            if condition == '0 fnt':
                if not check(pokemon.status is Status.FNT, '%s should be fainted', pokemon):
                    pokemon.status = Status.FNT
                if not check(pokemon.hp == 0, "%s's hp=%s; should be 0", pokemon, pokemon.hp):
                    pokemon.hp = 0

            check(pokemon.level == int(reqmon['details'].split(', ')[1][1:]), pokemon.level)
            check(pokemon.is_active == reqmon['active'],
                  "%s.is_active is %s, should be %s", pokemon, pokemon.is_active, reqmon['active'])

            if not pokemon.is_fainted():
                hp, max_hp = map(int, reqmon['condition'].split()[0].split('/'))
                status = condition[-1]
                if status in self.STATUS_MAP:
                    if not check(self.STATUS_MAP[status][0] == pokemon.status,
                                 '%s has the wrong status' % pokemon):
                        pokemon.status = self.STATUS_MAP[status][0]
                if not check(pokemon.hp == hp,
                             '%s has the wrong hp: %s %s', pokemon, pokemon.hp, hp):
                    pokemon.hp = hp
                if not check(pokemon.max_hp == max_hp,
                             '%s has the wrong max_hp: %s %s', pokemon, pokemon.max_hp, max_hp):
                    pokemon.max_hp = max_hp

                if not pokemon.is_transformed:
                    if not check(all(pokemon.stats[stat] == val
                                     for stat, val in reqmon['stats'].items()),
                                 "%s's stats: %s\nshould be %s",
                                 pokemon, pokemon.stats, reqmon['stats']):
                        stats = reqmon['stats'].copy()
                        stats['max_hp'] = max_hp
                        pokemon.stats = PokemonStats.from_dict(stats)

                    if not pokemon.ability.name.startswith('_'):
                        reqability = reqmon['baseAbility']
                        if not check(pokemon.base_ability.name == reqability,
                                     "%s's base_ability %s should be %s",
                                     pokemon, pokemon.ability.name, reqability):
                            pokemon.base_ability = abilitydex[reqability]

                reqmoves = sorted(reqmon['moves'])
                for i, move in enumerate(reqmoves):
                    if not check(len(pokemon.moves) > i, "%s is missing moves starting at index %d:"
                                 "\nmoves: %s\nrequest: %s", pokemon, i, pokemon.moves, reqmoves):
                        break
                    check(sorted(pokemon.moves)[i].name == move,
                          "%s's move %s doesn't match the request's %s",
                          pokemon, sorted(pokemon.moves)[i].name, move)

                if pokemon.item is None:
                    check(reqmon['item'] == '', "%s should have %s", pokemon, reqmon['item'])
                else:
                    check(reqmon['item'] == pokemon.item.name,
                          "%s's %s should be %s", pokemon, pokemon.item, reqmon['item'])

            check(int(request['side']['id'][1]) - 1 == self.my_side.index, str(self.my_side.index))
            check(request['side']['name'] == self.name, self.name)

    def _warn_if_stats_discrepancy(self, pokemon, stats):
        """
        Warn if the calculated stat for a pokemon is different from what is being sent by the
        Showdown server. A mismatch between these values indicates that we may be calculating
        the opponents' pokemon's stats incorrectly, which would throw off damage calculations.
        """
        for stat, val in stats.items():
            if not val == pokemon.stats[stat]:
                log.w("%s lvl %d's %s: Showdown=%d, calculated=%d",
                      pokemon, pokemon.level, stat, val, pokemon.stats[stat])


def check(condition, msg, *fmt):
    """
    Check that condition is True and warn msg if not. Return value of condition.
    """
    if not condition:
        lineno = traceback.extract_stack(limit=2)[0][1]
        log.w('At battleclient.py:%d: team validation failed:\n%s' % (lineno, msg % fmt))
    return condition
