from __future__ import absolute_import
from battle.battlefield import BattleSide
from battle.battlepokemon import BattlePokemon
from bot.unrevealedpokemon import UNREVEALED, UnrevealedPokemon
from pokedex.items import itemdex
from _logging import log

class FoeBattleSide(BattleSide):
    """
    Specialization of the BattleSide used for representing a real opponent with unrevealed
    pokemon.
    """
    def __init__(self, *args, **kwargs):
        super(FoeBattleSide, self).__init__(*args, **kwargs)
        self.active_pokemon.is_active = False
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
        self.pre_switch_state = FoePreSwitchState(self.hp, self.status,
                                                  self.turns_slept, self.pp, self.item)

    def reset_pre_switch_state(self):
        self.hp = self.pre_switch_state.hp
        self.status = self.pre_switch_state.status
        self.turns_slept = self.pre_switch_state.turns_slept
        self.pp = self.pre_switch_state.pp_moves
        self.moveset = self.pre_switch_state.pp_moves.keys()
        self.item = self.pre_switch_state.item
        self.pre_switch_state = None

class FoePreSwitchState(object):
    def __init__(self, hp, status, turns_slept, pp_moves, item):
        self.hp = hp
        self.status = status
        self.turns_slept = turns_slept
        self.pp_moves = pp_moves.copy()
        self.item = item
