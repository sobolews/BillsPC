from __future__ import absolute_import
from battle.battlefield import BattleSide
from battle.battlepokemon import BattlePokemon
from bot.unrevealedpokemon import UNREVEALED
from pokedex.items import itemdex

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
        for i in range(len(self.team)):
            if self.team[i].name == UNREVEALED:
                self.team[i] = pokemon
                return
        assert False, ("Tried to reveal a 7th pokemon on a fully revealed foe's team?!"
                       "\nTeam=\n%r\n\npokemon=\n%r") % (self, pokemon)

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
