from itertools import izip_longest
from subprocess import check_output

from pokedex import effects, weather
from pokedex.enums import FAIL, Status, Hazard, Weather

if __debug__: from _logging import log

class BattleField(object):
    """
    Encapsulates the entire state of a battle. At any point in the battle (but only at the decision
    points in between turns), it should be possible to (de)serialize a BattleField, inject it into a
    BattleEngine, and continue the battle.

    Note: the BattleEngine does maintain some intra-turn state.
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

    WEATHER_EFFECTS = {
        Weather.RAINDANCE: weather.RainDanceWeather,
        Weather.PRIMORDIALSEA: weather.PrimordialSeaWeather,
        Weather.SUNNYDAY: weather.SunnyDayWeather,
        Weather.DESOLATELAND: weather.DesolateLandWeather,
        Weather.HAIL: weather.HailWeather,
        Weather.SANDSTORM: weather.SandstormWeather,
        Weather.DELTASTREAM: weather.DeltaStreamWeather
    }

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

    def set_weather(self, weather):
        if self._weather in Weather.TRIO and not weather in Weather.TRIO:
            return FAIL
        if self._weather is not None:
            self.remove_effect(self._weather)
        if __debug__: log.i('The weather became %s', weather.name)
        self._weather = weather
        w_effect = self.WEATHER_EFFECTS[weather]()
        if self._weather_suppressed:
            w_effect.suppressed = True
        self.set_effect(w_effect)

    def clear_weather(self):
        self.remove_effect(self._weather)
        self._weather = None

    def set_effect(self, effect):
        if effect.source in self._effect_index:
            if __debug__: log.i('Tried to set effect %s but it %s already has it', effect, self)
            return FAIL

        self._effect_index[effect.source] = effect

    def get_effect(self, source):
        return self._effect_index.get(source)

    def has_effect(self, source):
        return source in self._effect_index

    def remove_effect(self, source, _=None):
        effect = self._effect_index.pop(source, None)
        if effect is None:
            if __debug__: log.d("Tried to remove nonexistent %s from battlefield", source)
            return

        effect.on_end() # TODO: will any battlefield effects use on_end?
        if source in Weather:
            self._weather = None
        if __debug__: log.i('Removed %s from battlefield', effect)

    def __repr__(self):
        cols = int(check_output(['stty', 'size']).split()[1]) or 80
        header = '\n'.join(('Battlefield'.center(cols),
                            ('effects: %s    turns: %d    win: %s' %
                            (' ,'.join(str(effect) for effect in self.effects).join(('[', ']')),
                             self.turns, self.win)).center(cols)))
        teams = '\n'.join((''.join((line[0].ljust(cols/2), line[1].rjust(cols/2))) for line in
                           izip_longest(repr(self.sides[0]).splitlines(),
                                        repr(self.sides[1]).splitlines(), fillvalue='')))
        return '\n\n'.join((header, teams))


class BattleSide(object):
    def __init__(self, team, index, username=None):
        """ :param team: 6-element list of BattlePokemon """
        assert index in (0, 1)
        self._effect_index = {}

        self.active_pokemon = team[0]
        self.active_pokemon.is_active = True
        self.index = index
        self.team = team
        self.last_fainted_on_turn = set() # for retaliate # TODO: does this need to track any but
                                          # the last turn?
        self.username = username or '<side-%d>' % index

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

    def set_effect(self, effect):
        if effect.source in self._effect_index:
            if __debug__: log.i('Tried to set condition %s but it %s already has it', effect, self)
            return FAIL

        self._effect_index[effect.source] = effect

    def has_effect(self, source):
        return source in self._effect_index

    def get_effect(self, source):
        return self._effect_index.get(source)

    def remove_effect(self, source, _=None):
        effect = self._effect_index.pop(source, None)
        if effect is None:
            if __debug__: log.d("Tried to remove nonexistent %s from side %d" %
                                (source, self.index))
            return

        effect.on_end() # TODO: will any battleside effects use on_end?
        if __debug__: log.i('Removed %s from side %d', effect, self.index)

    def clear_hazards(self):
        for hazard in Hazard:
            self.remove_effect(hazard)

    def update(self, engine):
        pokemon = self.active_pokemon
        if pokemon is not None:
            for effect in pokemon.effects:
                effect.on_update(pokemon, engine)

    def __str__(self):
        return 'Side %d: [%s]' % (self.index, ', '.join(str(p) for p in self.team))

    def __repr__(self):
        return '\n'.join(['Side %d   name: %s' % (self.index, self.username),
                          repr([effect for effect in self.effects]) + '\n',
                          '\n\n'.join(repr(pokemon) for pokemon in self.team)])
