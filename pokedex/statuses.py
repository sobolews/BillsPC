"""
The major status ailments are implemented here as Effects.
"""
import random

from misc.functions import priority
from pokedex.baseeffect import BaseEffect
from pokedex.enums import FAIL, Type, Status, Cause, MoveCategory

if __debug__: from _logging import log

class BaseStatusEffect(BaseEffect):
    def __init__(self, pokemon):
        pass

class Paralyze(BaseStatusEffect):
    source = Status.PAR

    def on_modify_spe(self, pokemon, battle, spe):
        if pokemon.ability.name != 'quickfeet':
            return spe * 0.25
        return spe

    @priority(1)
    def on_before_move(self, user, move, battle):
        if random.randrange(4) == 0:
            if __debug__: log.i("%s is paralyzed; it can't move!", user)
            return FAIL

class Freeze(BaseStatusEffect):
    source = Status.FRZ

    @priority(10)
    def on_before_move(self, user, move, battle):
        assert user.status is Status.FRZ
        if random.randrange(5) == 0 or move.thaw_user:
            user.cure_status()
        else:
            if __debug__: log.i("%s is frozen!", user)
            return FAIL

    def on_after_foe_hit(self, foe, move, target, battle):
        if move.type is Type.FIRE or move.thaw_target:
            target.cure_status()

    def on_after_set_status(self, status, pokemon, setter, battle):
        if pokemon.name == 'shayminsky' and pokemon.base_species == 'shayminsky':
            pokemon.forme_change('shaymin')

class Sleep(BaseStatusEffect):
    source = Status.SLP
    # no duration; uses turns_slept (because pokemon wakes up before move, not between turns)

    def __init__(self, pokemon, rest=False):
        if pokemon.turns_slept is None:
            pokemon.turns_slept = 0
        self.rest = rest

    @priority(10)
    def on_before_move(self, user, move, battle):
        assert user.status is Status.SLP

        turns_slept = user.turns_slept
        if ((self.rest and turns_slept >= 2) or
            (not self.rest and (turns_slept >= 3 or
                                (turns_slept == 2 and random.randrange(2) == 0) or
                                (turns_slept == 1 and random.randrange(3) == 0)))):
            user.cure_status()
            if __debug__: log.i('%s woke up!', user)
            return

        user.turns_slept += 1
        if __debug__: log.i("%s is sleeping: max %d turns left",
                            user, (2 if self.rest else 3) - turns_slept)

        return None if move.name == 'sleeptalk' else FAIL

class Burn(BaseStatusEffect):
    source = Status.BRN

    def on_modify_damage(self, user, move, effectiveness, damage):
        if (move.category is MoveCategory.PHYSICAL and
            move.name != 'facade' and
            user.ability.name != 'guts'
        ):
            return damage * 0.5
        return damage

    @priority(-9)
    def on_residual(self, pokemon, foe, battle):
        battle.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self)

class Poison(BaseStatusEffect):
    source = Status.PSN

    @priority(-9)
    def on_residual(self, pokemon, foe, battle):
        battle.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self)

class Toxic(BaseStatusEffect):
    source = Status.TOX
    stage = 0

    @priority(0)
    def on_switch_out(self, pokemon, incoming, battle):
        self.stage = 0

    @priority(-9)
    def on_residual(self, pokemon, foe, battle):
        self.stage += 1
        battle.damage(pokemon, ((pokemon.max_hp / 16) * self.stage) or 1, Cause.RESIDUAL, self)
