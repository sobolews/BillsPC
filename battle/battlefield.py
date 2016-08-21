from itertools import izip_longest
from subprocess import check_output

from battle.effecthandler import EffectHandlerMixin
from misc.bashcolors import strip_ANSI
from battle.baseeffect import BaseEffect
from battle.enums import FAIL, Status, Hazard, Weather
from battle.weather import WEATHER_EFFECTS

if __debug__: from _logging import log

class BattleField(object, EffectHandlerMixin):
    """
    Encapsulates the entire state of a battle. At any point in the battle (but only at the decision
    points in between turns), it should be possible to (de)serialize a BattleField, inject it into a
    Battle, and continue the battle.

    Note: the Battle does maintain some intra-turn state.
    """
    def __init__(self, side0=None, side1=None):
        self._weather = None
        self.terrain = None

        self._effect_index = {}

        self.sides = (BattleSide((), 0) if side0 is None else side0,
                      BattleSide((), 1) if side1 is None else side1)
        self.last_move_used = None # for copycat
        self._weather_suppressed = False
        self.win = None            # set to 0 or 1 when one side wins
        self.turns = 0
        self.effect_handlers = {key: list() for key in BaseEffect.handler_names}

    def get_foe(self, pokemon):
        return self.sides[not pokemon.side.index].active_pokemon

    @property
    def effects(self):
        return self._effect_index.values()

    @property
    def weather(self):
        if self._weather_suppressed:
            return None
        return self._weather

    def suppress_weather(self):
        self._weather_suppressed = True
        if self._weather is not None:
            self._effect_index[self._weather].suppressed = True

    def unsuppress_weather(self):
        self._weather_suppressed = False
        if self._weather is not None:
            self._effect_index[self._weather].suppressed = False

    def set_weather(self, weather, duration=5):
        if self._weather in Weather.TRIO and not weather in Weather.TRIO:
            return FAIL
        if self._weather is not None:
            self.remove_effect(self._weather)
        if __debug__: log.i('The weather became %s', weather)
        self._weather = weather
        w_effect = WEATHER_EFFECTS[weather](duration)
        if self._weather_suppressed:
            w_effect.suppressed = True
        self.set_effect(w_effect)

    def clear_weather(self):
        self.remove_effect(self._weather)
        self._weather = None

    def set_effect(self, effect):
        if effect.source in self._effect_index:
            if __debug__: log.i('Tried to set effect %s but it is already on the field', effect)
            return FAIL

        self._effect_index[effect.source] = effect
        self._set_handlers(effect)

    def get_effect(self, source):
        return self._effect_index.get(source)

    def has_effect(self, source):
        return source in self._effect_index

    def remove_effect(self, source, _=None):
        effect = self._effect_index.pop(source, None)
        if effect is None:
            if __debug__: log.d("Tried to remove nonexistent %s from battlefield", source)
            return
        self._remove_handlers(effect)

        if source in Weather.values:
            self._weather = None
        if __debug__: log.i('Removed %s from battlefield', effect)

    def __repr__(self):
        cols = min((int(check_output(['stty', 'size']).split()[1]) or 80), 102)
        header = '\n'.join(('Battlefield'.center(cols),
                            ('effects: %s    turns: %d    win: %s' %
                            (' ,'.join(str(effect) for effect in self.effects).join(('[', ']')),
                             self.turns, self.win)).center(cols)))
        teams = '\n'.join((split_justify(line[0], line[1], cols) for line in
                           izip_longest(repr(self.sides[0]).splitlines(),
                                        repr(self.sides[1]).splitlines(), fillvalue='')))
        return '\n\n'.join((header, teams))


def split_justify(lline, rline, cols):
    """
    Left- and right-justify lline and rline respectively within cols,
    properly adjusting for ANSI escape codes.
    """
    pad = cols - len(strip_ANSI(lline)) - len(strip_ANSI(rline))
    return lline + ' '*pad + rline


class BattleSide(object, EffectHandlerMixin):
    def __init__(self, team, index, username=None):
        """ :param team: 6-element list of BattlePokemon """
        assert index in (0, 1)
        self._effect_index = {}

        self.active_pokemon = team[0]
        self.active_pokemon.is_active = True
        self.index = index
        self.team = team
        self.last_fainted_on_turn = None
        self.username = username or '<side-%d>' % index
        self.has_mega_evolved = False
        self.effect_handlers = {key: list() for key in BaseEffect.handler_names}

        for pokemon in self.team:
            pokemon.side = self # ! circular reference; BattleSide owns BattlePokemon

    @property
    def effects(self):
        return self._effect_index.values()

    @property
    def bench(self):
        return [pokemon for pokemon in self.team if pokemon is not self.active_pokemon]

    @property
    def remaining_pokemon_on_bench(self):
        return len([pokemon for pokemon in self.bench if not pokemon.status is Status.FNT])

    @property
    def remaining_pokemon(self):
        return len([pokemon for pokemon in self.team if not pokemon.status is Status.FNT])

    def set_effect(self, effect):
        if effect.source in self._effect_index:
            if __debug__: log.i('Tried to set condition %s but it %s already has it', effect, self)
            return FAIL

        self._effect_index[effect.source] = effect
        self._set_handlers(effect)

    def has_effect(self, source):
        return source in self._effect_index

    def get_effect(self, source):
        return self._effect_index.get(source)

    def remove_effect(self, source, _=None):
        effect = self._effect_index.pop(source, None)
        if effect is None:
            if __debug__: log.d("Tried to remove nonexistent %s from side %d",
                                source, self.index)
            return

        self._remove_handlers(effect)
        if __debug__: log.i('Removed %s from side %d', effect, self.index)

    def clear_hazards(self):
        for hazard in Hazard.values:
            self.remove_effect(hazard)

    def update(self, battle):
        pokemon = self.active_pokemon
        if pokemon is not None:
            pokemon.activate_effect('on_update', pokemon, battle)

    def get_switch_choices(self, pokemon=None, forced=False):
        if not forced and pokemon is not None:
            for on_trap_check in pokemon.effect_handlers['on_trap_check']:
                if on_trap_check(pokemon):
                    return []

        return [team_member for team_member in self.team if
                not team_member.is_fainted() and not team_member.is_active]

    def __str__(self):
        return 'Side %d: [%s]' % (self.index, ', '.join(str(p) for p in self.team))

    def __repr__(self):
        return '\n'.join(['Side %d   name: %s' % (self.index, self.username),
                          repr([effect for effect in self.effects]) + '\n',
                          '\n\n'.join(repr(pokemon) for pokemon in self.team)])
