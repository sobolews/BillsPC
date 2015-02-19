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

    def on_modify_spe(self, pokemon, engine, spe):
        if pokemon.ability.name != 'quickfeet':
            return spe / 4

    @priority(1)
    def on_before_move(self, user, move, engine):
        if random.randrange(4) == 0:
            if __debug__: log.i("%s is paralyzed; it can't move!" % user)
            return FAIL

class Freeze(BaseStatusEffect):
    source = Status.FRZ

    @priority(10)
    def on_before_move(self, user, move, engine):
        assert user.status is Status.FRZ
        if random.randrange(5) == 0 or move.thaw_user:
            user.cure_status()
        else:
            if __debug__: log.i("%s is frozen!" % user)
            return FAIL

    def on_foe_hit(self, foe, move, target, engine):
        if move.type is Type.FIRE or move.thaw_target:
            target.cure_status()

class Sleep(BaseStatusEffect):
    source = Status.SLP
    # no duration; uses turns_left (because pokemon wakes up before move, not between turns)

    def __init__(self, pokemon, turns=None):
        if pokemon.sleep_turns is None:
            pokemon.sleep_turns = turns or random.randint(1, 3) # 1-3 turns
        self.turns_left = pokemon.sleep_turns

    @priority(10)
    def on_before_move(self, user, move, engine):
        assert user.status is Status.SLP
        assert user.sleep_turns == self.turns_left
        if self.turns_left <= 0:
            user.cure_status()
            user.sleep_turns = None
            if __debug__: log.i('%s woke up!' % user)
            return
        if __debug__: log.i("%s is sleeping: %d turns left" % (user, self.turns_left))
        self.turns_left -= 1
        user.sleep_turns -= 1
        return None if move.name == 'sleeptalk' else FAIL

class Burn(BaseStatusEffect):
    source = Status.BRN

    def on_modify_damage(self, user, move, damage):
        if (move.category is MoveCategory.PHYSICAL and
            move.name != 'facade' and
            user.ability.name != 'guts'):
            return damage / 2
        return damage

    @priority(9)
    def on_residual(self, pokemon, foe, engine):
        engine.damage(pokemon, pokemon.max_hp / 8, Cause.RESIDUAL, self)

class Poison(BaseStatusEffect):
    source = Status.PSN

    @priority(9)
    def on_residual(self, pokemon, foe, engine):
        engine.damage(pokemon, pokemon.max_hp / 8, Cause.RESIDUAL, self)

class Toxic(BaseStatusEffect):
    source = Status.TOX
    stage = 0

    def on_switch_out(self, pokemon, engine):
        self.stage = 0

    @priority(9)
    def on_residual(self, pokemon, foe, engine):
        self.stage += 1
        engine.damage(pokemon, ((pokemon.max_hp / 16) * self.stage) or 1, Cause.RESIDUAL, self)
