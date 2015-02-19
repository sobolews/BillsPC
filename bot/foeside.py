from __future__ import absolute_import
from battle.battlefield import BattleSide
from bot.unrevealedpokemon import UNREVEALED

class FoeBattleSide(BattleSide):
    """
    Specialization of the BattleSide used for representing a real opponent with unrevealed
    pokemon.
    """
    def __init__(self, *args, **kwargs):
        super(FoeBattleSide, self).__init__(*args, **kwargs)
        self.active_pokemon.is_active = False
        self.active_pokemon = None

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
