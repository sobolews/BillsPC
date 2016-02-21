from battle.effecthandler import EffectHandlerMixin
from mining import create_pokedex
from pokedex import effects, abilities
from pokedex.abilities import abilitydex
from pokedex.baseeffect import BaseEffect
from pokedex.enums import (Volatile, FAIL, Status, MoveCategory, Type, Weather, ABILITY, POWDER,
                           SideCondition, ITEM)
from pokedex.items import itemdex
from pokedex.stats import Boosts, PokemonStats
from pokedex.types import effectiveness
from pokedex.moves import movedex

if __debug__: from _logging import log

POKEDEX = create_pokedex()

class BattlePokemon(object, EffectHandlerMixin):
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
        self.evs = evs
        self.ivs = ivs
        self.hp = self.max_hp = self.stats['max_hp']
        self._weight = pokedex_entry.weight
        self.ability = self.base_ability = ability
        self.status = None
        self.boosts = Boosts()

        self.is_mega = False
        self.has_moved_this_turn = False
        self.will_move_this_turn = False
        self.damage_done_this_turn = 0
        self.was_attacked_this_turn = None # when set, should be dict with keys "move" and "damage"
        self.turns_out = 0 # for fakeout and speedboost
        self.last_move_used = None
        self.is_switching_out = False # for pursuit
        self.is_active = False
        self.must_switch = None
        self.is_resting = False
        self.sleep_turns = None
        self.is_transformed = False
        self.illusion = False
        self.item_used_this_turn = None
        self.last_berry_used = None
        self.base_data = {}     # for transform
        self._suppressed_ability = None
        self._effect_index = {}
        self.effect_handlers = {key: list() for key in BaseEffect.handler_names}

    @property
    def can_mega_evolve(self):
        return (self.item is not None and
                self.item.is_mega_stone and
                not self.side.has_mega_evolved and
                not self.is_mega and
                self.item.forme in self.pokedex_entry.mega_formes)

    def mega_evolve(self, engine):
        if __debug__: log.i('%s is mega-evolving!', self)
        forme = self.item.forme
        self.forme_change(forme, engine)
        self.side.has_mega_evolved = True
        self.is_mega = True

    def forme_change(self, forme, engine=None):
        assert not self.is_transformed

        self.pokedex_entry = new_forme = POKEDEX[forme]
        self.name = new_forme.name
        self._weight = new_forme.weight
        self.stats = self.calculate_initial_stats(self.evs, self.ivs)
        self.types = list(new_forme.types)
        new_ability = abilitydex[new_forme.abilities[0]]
        if new_ability != self.ability:
            self.change_ability(new_ability, engine)
            self.base_ability = new_ability
        if __debug__: log.i('%s changed forme to %s!', self.base_species, self.name)

    @property
    def effects(self):
        return self._effect_index.values()

    def set_effect(self, effect, override_immunity=False):
        assert not self.is_fainted()

        if effect.source in self._effect_index:
            if __debug__: log.d('Tried to set effect %s but %s already has it', effect, self)
            return FAIL

        if self.is_immune_to(effect.source) and not override_immunity:
            if __debug__: log.i('%s is immune to %s!', self, effect.source.name)
            return FAIL

        self._effect_index[effect.source] = effect
        self._set_handlers(effect)

        if __debug__: log.i('Set effect %s on %s', effect, self)

    def confuse(self, infiltrates=False):
        if not infiltrates and self.side.has_effect(SideCondition.SAFEGUARD):
            return FAIL

        return self.set_effect(effects.Confuse())

    def has_effect(self, source):
        return source in self._effect_index

    def get_effect(self, source):
        return self._effect_index.get(source)

    def remove_effect(self, source, engine=None, batonpassed=False):
        """
        `engine` must be passed if there is a possibility that `source`'s effect has an on_end
        method that uses engine.

        `engine` may be omitted if `source` is known to be a move or status, but must be included
        for abilities in general.

        Return True if effect was removed
        """
        effect = self._effect_index.pop(source, None)
        if effect is None:
            if __debug__: log.d("Trying to remove %s from %s, but it wasn't found!", source, self)
            return False
        self._remove_handlers(effect)

        if __debug__: log.i('Removed %s from %s', effect, self)
        if not batonpassed and 'on_end' in effect.handler_names:
            effect.on_end(self, engine)
        if source is self.status:
            self.status = None

        return True

    def clear_effects(self, engine):
        self.activate_effect('on_end', self, engine)

        self._effect_index.clear()
        self.effect_handlers = {key: list() for key in self.effect_handlers}

    def suppress_ability(self, engine):
        if __debug__: log.d("Suppressing %s's ability", self)
        self.remove_effect(ABILITY, engine)
        self._suppressed_ability = self.ability
        self.ability = abilitydex['_suppressed_']
        self.set_effect(abilitydex['_suppressed_']())

    def unsuppress_ability(self):
        assert self.ability == abilitydex['_suppressed_']
        if __debug__: log.d("Unsuppressing %s's ability", self)
        self.remove_effect(ABILITY)
        self.ability = self._suppressed_ability
        self._suppressed_ability = None
        self.set_effect(self.ability())

    def cure_status(self):
        if self.status in (None, Status.FNT):
            if __debug__: log.d("Tried to cure %s's status but it was %s", self, self.status)
        else:
            if __debug__: log.i("%s's status (%s) was cured", self, self.status.name)
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

        if (movedex['bellydrum'] in self.moveset and
            self.item is itemdex['sitrusberry'] and
            hp % 2 == 1
        ):
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

    def is_immune_to_move(self, user, move):
        """Return True if self is immune to move"""
        for on_get_immunity in self.effect_handlers['on_get_immunity']:
            immune = on_get_immunity(move.type) # check type immunity first, then move
            if immune is None:
                immune = on_get_immunity(move) # for bulletproof, overcoat, etc.
            if immune is not None:
                return immune

        if Type.GRASS in self.types and (move.is_powder or move == movedex['leechseed']):
            return True
        if move.category is MoveCategory.STATUS and move != movedex['thunderwave']:
            return False

        if user.ability is abilitydex['scrappy'] and move.type in (Type.FIGHTING, Type.NORMAL):
            return False

        return effectiveness(move.type, self) == 0

    def is_immune_to(self, thing):
        """ `thing` may be a move Type, Status, Weather, POWDER, or Volatile """
        for on_get_immunity in self.effect_handlers['on_get_immunity']:
            immune = on_get_immunity(thing)
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
        if (item is None or
            not item.removable or
            self.ability == abilitydex['stickyhold']
        ):
            return FAIL

        self.activate_effect('on_lose_item', self, item)

        if __debug__: log.i('Removed %s from %s', self.item, self)
        self.remove_effect(ITEM)
        self.item = None
        self.last_berry_used = None
        return item

    def set_item(self, item):
        assert self.item is None

        self.item = item
        self.set_effect(item())
        self.remove_effect(Volatile.UNBURDEN)

    def use_item(self, engine):
        """
        Use the item held by this pokemon.
        Return FAIL if item was not used successfully. It is assumed that the item can be used.
        """
        item = self.item
        assert item is not None and item.removable and item.single_use

        if item.is_berry:
            if self.eat_berry(engine, item) is FAIL:
                return FAIL
        else:
            if __debug__: log.i("%s used its %s", self, item)
            self.last_berry_used = None

        self.activate_effect('on_use_item', self, item, engine)
        self.activate_effect('on_lose_item', self, item)
        self.remove_effect(ITEM)
        self.item = None
        self.item_used_this_turn = item

    def eat_berry(self, engine, berry, stolen=False):
        """
        Eat a berry, which may be held by this pokemon or stolen from another (via bugbite or pluck)
        """
        assert berry.is_berry

        if not stolen:
            foe = engine.get_foe(self)
            if foe is not None and foe.ability is abilitydex['unnerve']:
                return FAIL

        if __debug__: log.i("%s ate the %s", self, berry)
        berry.on_eat(self, engine)
        self.last_berry_used = berry

    @property
    def weight(self):
        weight = self._weight

        autotomize = self.get_effect(Volatile.AUTOTOMIZE)
        if autotomize is not None:
            weight -= autotomize.multiplier * 100
            return weight if weight >= 0.1 else 0.1

        return weight

    def transform_into(self, other, engine):
        if ((other.is_fainted() or
             other.has_effect(Volatile.SUBSTITUTE) or
             self.is_transformed or
             other.is_transformed or
             other.ability == abilitydex['illusion'])):
            return FAIL
        if __debug__: log.i('%s transformed into %s!', self, other)

        self.is_transformed = True

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
        self.pp = {move: 5 for move in self.moveset}
        self.types = list(other.types)
        self.gender = other.gender
        self.stats = other.stats.copy()
        self.stats['max_hp'] = self.max_hp
        self._weight = other.weight

        self.boosts = Boosts()
        self.boosts.update(other.boosts, self.name)
        if __debug__:
            if self.boosts: log.i('%s copied %r', self, self.boosts)

        if other.ability.name not in ('stancechange', 'multitype', 'illusion'):
            self.remove_effect(ABILITY, engine)
            self.ability = other.ability
            ability_effect = self.ability()
            self.set_effect(ability_effect)
            ability_effect.start(self, engine)

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

    def change_ability(self, new_ability, engine):
        """
        Change this pokemon's ability. This effect will only last while the pokemon is active.
        This pokemon's original ability remains saved in self.base_ability.
        """
        assert self.is_active, "Tried to change inactive pokemon's ability"
        assert issubclass(new_ability, abilities.BaseAbility)

        if ((new_ability.name in ('illusion', 'stancechange', 'multitype') or
             self.ability.name in ('stancechange', 'multitype'))):
            if __debug__: log.d("Failed to change %s's %s to %s", self, self.ability, new_ability)
            return FAIL

        self.remove_effect(ABILITY, engine)
        self.ability = new_ability
        self.set_effect(new_ability())
        self.get_effect(ABILITY).start(self, engine)

    def deduct_pp(self, move, target):
        deduction = (2 if (target is not None and
                           target.ability is abilitydex['pressure'] and
                           not move.targets_user)
                     else 1)
        self.pp[move] -= deduction

    def get_switch_choices(self, forced=False):
        return self.side.get_switch_choices(pokemon=self, forced=forced)

    def get_move_choices(self):
        move_choices = self.accumulate_effect('on_get_move_choices', self,
                                              [move for move in self.moveset if self.pp[move] > 0])
        return move_choices or [movedex['struggle']]

    def apply_boosts(self, boosts, self_induced=True):
        assert not self.is_fainted()
        assert self.is_active

        # Only abilities have on_boost
        boosts = self.get_effect(ABILITY).on_boost(self, boosts, self_induced)

        return self.boosts.update(boosts, self.name)

    def __str__(self):
        if self.name == self.base_species or self.is_mega:
            return self.name
        else:
            return '%s (%s)' % (self.name, self.base_species)

    def __repr__(self):
        return '\n'.join([
            '%s %d/%d   L%d (side %d)' % (self.name, self.hp, self.max_hp, self.level,
                                            self.side.index),
            'moves: [%s]' % ', '.join(move.name for move in self.moveset),
            'status: %s   ability: %s   item: %s' % (self.status and self.status.name, self.ability,
                                                     self.item),
            ('Active effects: %r  %s' % ([e for e in self.effects], self.boosts or '')
             if self.is_active else '')
        ])

    def debug_sanity_check(self, engine):
        for effect in self._effect_index.values():
            if effect not in self.effects:
                log.wtf('%s: %s in _effect_index but not in effects', effect, self)
                raise AssertionError

        for effect in self.effects:
            if effect not in self._effect_index.values():
                log.wtf('%s: %s in effects but not indexed in _effect_index', effect, self)
                raise AssertionError

        if self.is_active and self.status not in (None, Status.FNT):
            assert self.has_effect(self.status), repr(self)

        if self.is_active and self.status is None:
            for status in Status:
                assert not self.has_effect(status)

        if self.is_active:
            assert engine.battlefield.sides[self.side.index].active_pokemon is self
            assert self.side.active_pokemon is self
        else:
            assert engine.battlefield.sides[self.side.index].active_pokemon is not self
            assert self in self.side.team
            assert not any([handler_list for handler_list in self.effect_handlers.values()])

        assert self.hp <= self.max_hp
