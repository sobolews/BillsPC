from pokedex.enums import FAIL
from misc.functions import clamp_int

class PokemonStats(dict):
    def __init__(self, max_hp, atk, def_, spa, spd, spe):
        super(PokemonStats, self).__init__(
            **{'max_hp':max_hp, 'atk':atk, 'def':def_, 'spa':spa, 'spd':spd, 'spe':spe})

    def __setitem__(self, key, value):
        raise KeyError("A BattlePokemon's stats cannot change")

    @classmethod
    def from_dict(cls, dct):
        self = cls(*(None,)*6)
        self.update(dct)
        assert all(stat in self for stat in ('max_hp', 'atk', 'def', 'spa', 'spd', 'spe'))
        return self

class Boosts(dict):
    def __init__(self, atk=0, def_=0, spa=0, spd=0, spe=0, acc=0, evn=0):
        super(Boosts, self).__init__(
            **{'atk':atk, 'def':def_, 'spa':spa, 'spd':spd, 'spe':spe, 'acc':acc, 'evn':evn})

    def update(self, other):
        prev = dict(self)

        for stat in other:
            self[stat] = clamp_int(self[stat] + other[stat], -6, 6)

        if prev == self:
            return FAIL

    def __repr__(self):
        return (', '.join('%s=%s' % (stat, val) for stat, val in self.items() if val)
                .join(['Boosts(', ')']))

    def __nonzero__(self):
        return any(val for val in self.values())
