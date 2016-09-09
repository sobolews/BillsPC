from __future__ import absolute_import
from battle.battlefield import BattleSide
from battle.battlepokemon import BattlePokemon
from battle.enums import Type
from battle.abilities import abilitydex
from battle.items import itemdex
from _logging import log


UNREVEALED = '<unrevealed>'

class UnrevealedPokemon(BattlePokemon):
    """
    A placeholder Pokemon object representing an unknown pokemon on the foe's bench.
    """
    def __init__(self):
        self.name = self.base_species = UNREVEALED
        self.is_active = False
        self.status = None

    def not_implemented(self, *args, **kwargs):
        raise AssertionError('This pokemon has not been revealed yet')

    set_effect = has_effect = get_effect = remove_effect = clear_effects = \
    suppress_ability = unsuppress_ability = \
    calculate_stat = calculate_initial_stats = _calc_hp = calculate_evs_ivs = \
    is_immune_to_move = is_immune_to = take_item = set_item = use_item = not_implemented

    def _debug_sanity_check(self, battle):
        pass

    def cure_status(self):
        pass

    def is_fainted(self):
        return False

    def __repr__(self):
        return '(unrevealed pokemon)'


class FoeBattleSide(BattleSide):
    """
    Specialization of the BattleSide used for representing a real opponent with unrevealed
    pokemon.
    """
    def __init__(self, *args, **kwargs):
        super(FoeBattleSide, self).__init__(*args, **kwargs)
        self.active_pokemon.is_active = False
        if self.team[0].name == UNREVEALED:
            self.active_pokemon = None
        self.active_illusion = False

    @property
    def num_unrevealed(self):
        return len([pokemon for pokemon in self.team if pokemon.name == UNREVEALED])

    def reveal(self, pokemon):
        for i, foe in enumerate(self.team):
            if foe.name == UNREVEALED:
                self.team[i] = pokemon
                return

        # all 6 slots are filled; zoroark shenanigans can cause this
        log.i("All 6 slots on foe's side are full... attempting to resolve")
        for i in range(len(self.team)):
            # remove revealed zoroark
            if self.team[i].name == 'zoroark':
                self.team[i] = UnrevealedPokemon()
            else:
                # remove duplicate pokemon
                for j in range(i+1, len(self.team)):
                    if self.team[j].base_species == self.team[i].base_species != UNREVEALED:
                        self.team[j] = UnrevealedPokemon()

        # try again, if there's still no available slots then something else is wrong
        for i, foe in enumerate(self.team):
            if foe.name == UNREVEALED:
                self.team[i] = pokemon
                return

        raise AssertionError("Tried to reveal a 7th pokemon on a fully revealed foe's team?!"
                             "\nTeam=\n%r\n\npokemon=\n%r" % (self, pokemon))

class FoePokemon(BattlePokemon):
    def __init__(self, *args, **kwargs):
        super(FoePokemon, self).__init__(*args, **kwargs)
        self.original_item = itemdex['_unrevealed_']
        self.pre_switch_state = None

    def save_pre_switch_state(self):
        self.pre_switch_state = FoePreSwitchState(self.hp, self.status, self.turns_slept,
                                                  self.moves, self.item, self.original_item)

    def reset_pre_switch_state(self):
        self.hp = self.pre_switch_state.hp
        self.status = self.pre_switch_state.status
        self.turns_slept = self.pre_switch_state.turns_slept
        self.moves = self.pre_switch_state.moves
        self.item = self.pre_switch_state.item
        self.original_item = self.pre_switch_state.original_item
        self.pre_switch_state = None

    def known_attrs(self):
        """
        Return the names of the known move/item/ability attributes of this foe pokemon:
        [moves..., ability, item]

        Do not return the base_ability of a mega/primal pokemon, since rbstats only tracks the
        base_ability of the pre-formechange pokemon, so lookups will fail using the post-change
        ability. This doesn't reduce the accuracy of lookups, since if the pokemon is mega/primal
        this is seen uniquely in the item.
        """
        attrs = [move.name for move in self.moves if move.type != Type.NOTYPE]
        if self.original_item != itemdex['_unrevealed_']:
            attrs.append(self.original_item.name)
        if (self.base_ability != abilitydex['_unrevealed_'] and not
            (self.is_mega or self.name.endswith('primal'))):
            attrs.append(self.base_ability.name)
        log.d("attrs: %s", attrs)

        all_known = (len(attrs) == 6 or
                     (len(attrs) == 5 and (self.is_mega or self.name.endswith('primal'))) or
                     (len(attrs) == 3 and self.base_species == 'ditto'))

        return attrs, all_known

class FoePreSwitchState(object):
    def __init__(self, hp, status, turns_slept, moves, item, original_item):
        self.hp = hp
        self.status = status
        self.turns_slept = turns_slept
        self.moves = moves.copy()
        self.item = item
        self.original_item = original_item
