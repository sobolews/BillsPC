from pokedex import effects
from pokedex.abilities import abilitydex
from pokedex.enums import Volatile, FAIL, Status, MoveCategory, Type, Weather, ABILITY, POWDER
from pokedex.items import itemdex
from pokedex.stats import Boosts, PokemonStats
from pokedex.types import effectiveness
from pokedex.moves import movedex
if __debug__: from _logging import log

class BattlePokemon(object):
    """
    Represents a pokemon in a battle.
    """
    def __init__(self, pokedex_entry, level=100, moveset=(), ability=abilitydex['_none_'],
                 item=None, gender=None, evs=None, ivs=None, side=None):
        """
        Note: If evs/ivs are not specified, they will be calculated according to randbats (see
        calculate_initial_stats)
        """
        self.pokedex_entry = pokedex_entry
        self.name = self.base_species = pokedex_entry.name # base_species for transform etc.
        self.side = side
        self.level = level
        self.moveset = moveset
        self.pp = {move: move.max_pp for move in moveset}
        self.types = list(pokedex_entry.types)
        self.item = item
        self.gender = gender    # None, 'M', or 'F'
        self.stats = self.calculate_initial_stats(evs, ivs)
        self.hp = self.max_hp = self.stats['max_hp']
        self._weight = pokedex_entry.weight
        self.ability = self._ability = ability
        self.status = None
        self.boosts = Boosts()

        self.is_mega = False
        self.has_moved_this_turn = False
        self.will_move_this_turn = False
        self.damage_done_this_turn = 0
        self.was_attacked_this_turn = None # when set, should be dict with keys "move" and "damage"
        self.first_turn_out = False # for fakeout and speedboost
        self.last_move_used = None
        self.is_switching_out = False # for pursuit
        self.is_active = False
        self.must_switch = None
        self.is_resting = False
        self.sleep_turns = None
        self.is_transformed = False
        self.illusion = False
        self.base_data = {}     # for transform
        self._effect_index = {}

    @property
    def effects(self):
        return self._effect_index.values()

    def set_effect(self, effect):
        if effect.source in self._effect_index:
            if __debug__: log.d('Tried to set effect %s but %s already has it', effect, self)
            return FAIL

        if self.is_immune_to(effect.source):
            if __debug__: log.i('%s is immune to %s!', self, effect.source.name)
            return FAIL

        self._effect_index[effect.source] = effect
        if __debug__: log.i('Set effect %s on %s', effect, self)

    def has_effect(self, source):
        return source in self._effect_index

    def get_effect(self, source):
        return self._effect_index.get(source)

    def remove_effect(self, source, engine=None):
        """
        `engine` must be passed if there is a possibility that `source`'s effect has an on_end
        method that uses engine.

        `engine` may be omitted if `source` is known to be a move or status, but must be included
        for abilities in general.

        Return True if effect was removed
        """
        effect = self._effect_index.pop(source, None)
        if effect is None:
            if __debug__: log.d("Trying to remove %s from %s, but it wasn't found!" , source, self)
            return False

        effect.on_end(self, engine)
        if source is self.status:
            self.status = None

        if __debug__: log.i('Removed %s from %s' % (source, self))
        return True

    def clear_effects(self, engine):
        for effect in self.effects:
            effect.on_end(self, engine)

        self._effect_index.clear()

    def suppress_ability(self, engine):
        assert self._ability == self.ability
        self.remove_effect(ABILITY, engine)
        self.ability = abilitydex['_suppressed_']

    def unsuppress_ability(self):
        self.set_effect(self._ability())
        self.ability = self._ability

    def cure_status(self):
        if self.status in (None, Status.FNT):
            if __debug__: log.d("Tried to cure %s's status but it was %s" % (self, self.status))
        else:
            if __debug__: log.i("%s's status (%s) was cured" % (self, self.status.name))
            self.remove_effect(self.status)
            self.status = None
            self.is_resting = False
            self.sleep_turns = None

    def calculate_stat(self, which_stat, override_boost=None):
        stat = self.stats[which_stat]
        if override_boost is not None:
            boost = override_boost
        else:
            boost = self.boosts[which_stat]
        boost_factor = (1, 1.5, 2, 2.5, 3, 3.5, 4)

        if boost > 0:
            stat = int(stat * boost_factor[boost])
        elif boost < 0:
            stat = int(stat / boost_factor[-boost])

        return stat

    def is_fainted(self):
        assert (self.hp <= 0) if (self.status is Status.FNT) else True
        assert (self.status is Status.FNT) if (self.hp <= 0) else True

        return self.status is Status.FNT

    def calculate_initial_stats(self, evs, ivs):
        """
        ivs = (31,...), evs = (85,...) except for:
        gyroball: ivs.spe=0, evs.spe=0, evs.atk+=85
        trickroom: ivs.spe=0, evs.spe=0, evs.hp+=85
        shedinja: evs.atk=252 evs.hp,def,spd=0
        """
        evs_, ivs_ = self.calculate_evs_ivs()
        self.evs = evs = evs or evs_
        self.ivs = ivs = ivs or ivs_

        max_hp = self._calc_hp(evs[0], ivs[0])

        stats = [int(int(2 * self.pokedex_entry.base_stats[stat] + iv + int(ev / 4)) *
                     self.level / 100 + 5)
                 for stat, ev, iv
                 in zip(('atk', 'def', 'spa', 'spd', 'spe'), evs[1:], ivs[1:])]

        return PokemonStats(max_hp, *stats)

    def _calc_hp(self, ev, iv):
        base_hp = self.pokedex_entry.base_stats['max_hp']
        return (1 if base_hp == 1 else # shedinja
                int(int(2 * base_hp + iv + int(ev / 4) + 100) * self.level / 100 + 10))

    def calculate_evs_ivs(self):
        if self.base_species == 'shedinja':
            evs = [0, 252, 0, 85, 0, 85]
            ivs = [31, 31, 31, 31, 31, 31]
            return evs, ivs

        if movedex['gyroball'] in self.moveset:
            evs = [85, 170, 85, 85, 85, 0]
            ivs = [31, 31, 31, 31, 31, 0]

        elif movedex['trickroom'] in self.moveset:
            evs = [170, 85, 85, 85, 85, 0]
            ivs = [31, 31, 31, 31, 31, 0]

        else:
            evs = [85, 85, 85, 85, 85, 85]
            ivs = [31, 31, 31, 31, 31, 31]

        HP, ATK, SPA = 0, 1, 3
        hp = self._calc_hp(evs[HP], ivs[HP])

        if (movedex['bellydrum'] in self.moveset and self.item is itemdex['sitrusberry'] and
            hp % 2 == 1):
            evs[HP] -= 4
            evs[ATK] += 4
        else:
            eff = effectiveness(Type.ROCK, self)
            if ((eff == 2 and hp % 4 == 0) or
                (eff == 4 and hp % 2 == 0)):
                physical = special = 0
                for move in self.moveset:
                    if move.category is MoveCategory.PHYSICAL:
                        physical += 1
                    elif move.category is MoveCategory.SPECIAL:
                        special += 1
                evs[HP] -= 4
                evs[ATK if physical > special else SPA] += 4

        return evs, ivs

    def is_immune_to_move(self, move):
        """Return True if self is immune to move"""
        for effect in self.effects:
            immune = effect.on_get_immunity(move.type) # check type immunity first, then move
            if immune is None:
                immune = effect.on_get_immunity(move) # for bulletproof, overcoat, etc.
            if immune is not None:
                return immune

        if Type.GRASS in self.types and (move.is_powder or move == movedex['leechseed']):
            return True
        if move.category is MoveCategory.STATUS and move != movedex['thunderwave']:
            return False

        return effectiveness(move.type, self) == 0

    def is_immune_to(self, thing):
        """ `thing` may be a move Type, Status, Weather, POWDER, or Volatile """
        for effect in self.effects:
            immune = effect.on_get_immunity(thing)
            if immune is not None:
                return immune

        if thing in Type:
            return effectiveness(thing, self) == 0

        if thing in self.STATUS_IMMUNITIES:
            return any(type in self.STATUS_IMMUNITIES[thing]
                       for type in self.types)

        if thing is Weather.SANDSTORM:
            return any(type in (Type.GROUND, Type.ROCK, Type.STEEL)
                       for type in self.types)

        if thing is POWDER:
            return Type.GRASS in self.types

        if thing is Weather.HAIL:
            return Type.ICE in self.types

        return False

    STATUS_IMMUNITIES = {
        Status.BRN: (Type.FIRE,),
        Status.PAR: (Type.ELECTRIC,),
        Status.PSN: (Type.POISON, Type.STEEL),
        Status.TOX: (Type.POISON, Type.STEEL),
        Status.FRZ: (Type.ICE,)
    }

    def take_item(self): # by force, e.g. from bugbite, knockoff, magician, trick etc.
        item = self.item
        if (item is None or item.is_mega_stone or item.is_plate or item.is_drive or
            self.ability == abilitydex['stickyhold']):
            return FAIL
        if self.ability == abilitydex['unburden']:
            self.set_effect(effects.Unburden())
        if __debug__: log.i('Removed %s from %s' % (self.item, self))
        self.item = None
        return item

    def set_item(self, item):   # TODO: implement items
        self.remove_effect(Volatile.UNBURDEN)

    def use_item(self, item):   # TODO: implement items
        """ Return FAIL if item was not used successfully """
        pass

    @property
    def weight(self):
        weight = self._weight
        for effect in self.effects: # TODO: just look for Autotomize instead?
            weight = effect.on_get_weight(weight)
        return weight

    def transform_into(self, other, engine):
        if ((other.is_fainted() or
             other.has_effect(Volatile.SUBSTITUTE) or
             self.is_transformed or
             other.ability == abilitydex['illusion'])):
            return FAIL
        if __debug__: log.i('%s transformed into %s!', self, other)

        self.base_data['moveset'] = self.moveset
        self.base_data['pp'] = self.pp
        self.base_data['types'] = self.types
        self.base_data['gender'] = self.gender
        self.base_data['stats'] = self.stats
        self.base_data['ability'] = self.ability
        self.base_data['weight'] = self._weight

        self.name = other.name
        self.moveset = [movedex['hiddenpowerdark'] if move.is_hiddenpower else move
                        for move in other.moveset] # TODO: do iv calc?
        self.pp = {move: 5 for move in other.moveset}
        self.types = list(other.types)
        self.gender = other.gender
        self.stats = other.stats.copy()
        self.stats['max_hp'] = self.max_hp
        self._weight = other.weight

        self.boosts = Boosts()
        self.boosts.update(other.boosts)
        if __debug__:
            if self.boosts: log.i('%s copied %r', self, self.boosts)

        if other.ability.name not in ('stancechange', 'multitype', 'illusion'):
            self.ability = other.ability
            ability_effect = self.ability()
            self.set_effect(ability_effect)
            ability_effect.on_start(self, engine)

        self.is_transformed = True

    def revert_transform(self):
        """ This should only be done on switch out or on faint """
        assert self.is_transformed
        self.name = self.base_species
        self.moveset = self.base_data['moveset']
        self.pp = self.base_data['pp']
        self.types = self.base_data['types']
        self.gender = self.base_data['gender']
        self.stats = self.base_data['stats']
        self.ability = self.base_data['ability']
        self._weight = self.base_data['weight']
        self.is_transformed = False
        if __debug__: log.i("%s's transform reverted", self)

    def __str__(self):
        if self.name == self.base_species:
            return self.name
        else:
            return '%s (%s)' % (self.name, self.base_species)

    def __repr__(self):
        return '\n'.join([
            '%s %d/%d   L%d (side %d%s)' % (self.name, self.hp, self.max_hp, self.level,
                                            self.side.index, ', active' if self.is_active else ''),
            'moves: [%s]' % ', '.join(move.name for move in self.moveset),
            'status: %s   ability: %s   item: %s' % (self.status and self.status.name, self.ability,
                                                     self.item),
            'effects: %r  %s' % ([e for e in self.effects], self.boosts or '')
        ])

    def _debug_sanity_check(self, engine):
        for effect in self._effect_index.values():
            if effect not in self.effects:
                log.wtf('%s: %s in _effect_index but not in effects' % effect, self)
                raise AssertionError

        for effect in self.effects:
            if effect not in self._effect_index.values():
                log.wtf('%s: %s in effects but not indexed in _effect_index', effect, self)
                raise AssertionError

        if self.is_active and self.status not in (None, Status.FNT):
            assert self.has_effect(self.status), repr(self)

        if self.is_active:
            assert engine.battlefield.sides[self.side.index].active_pokemon is self
            assert self.side.active_pokemon is self
        else:
            assert engine.battlefield.sides[self.side.index].active_pokemon is not self
            assert self in self.side.team

        assert self.hp <= self.max_hp
