"""
All items are implemented here, and gathered in to the `itemdex` dictionary.
Items are named in CamelCase, but their .name attribute is lowercasenospaces.
"""
import inspect

if __debug__: from _logging import log
from misc.functions import priority
from pokedex import effects
from pokedex.baseeffect import BaseEffect
from pokedex.enums import ITEM, Type, Cause, MoveCategory, Status, Volatile, FAIL

class BaseItem(object):
    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            dct['name'] = name.lower()
            return type.__new__(cls, name, bases, dct)

        def __repr__(self):
            return self.__name__

    is_mega_stone = False
    is_berry = False
    is_plate = False
    is_drive = False
    removable = True
    single_use = False
    source = ITEM

    def __repr__(self):
        return "%s()" % self.__class__.__name__

class ItemEffect(BaseItem, BaseEffect):
    pass

class AirBalloon(ItemEffect):
    single_use = True

    def on_get_immunity(self, thing):
        if thing is Type.GROUND:
            return True

    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if cause is Cause.MOVE and pokemon is not foe:
            pokemon.use_item(engine)

class AssaultVest(ItemEffect):
    def on_get_move_choices(self, pokemon, moves):
        return [move for move in moves if not move.category is MoveCategory.STATUS]

    def on_modify_spd(self, pokemon, move, engine, spd):
        return spd * 1.5

class BlackSludge(ItemEffect):
    @priority(-5.2)
    def on_residual(self, pokemon, foe, engine):
        if Type.POISON in pokemon.types:
            engine.heal(pokemon, pokemon.max_hp / 16)
        else:
            engine.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self)

# class BlueOrb(ItemEffect):
#     pass # TODO when: implement forme changes

class ChestoBerry(ItemEffect):
    is_berry = True
    single_use = True

    def on_update(self, pokemon, engine):
        if pokemon.status is Status.SLP:
            pokemon.use_item(engine)

    def on_use_item(self, pokemon, item, engine):
        if pokemon.status is Status.SLP:
            pokemon.cure_status()

class ChoiceBand(ItemEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        return atk * 1.5

    def on_modify_move(self, move, user, engine):
        user.set_effect(effects.ChoiceLock(move))

    def on_lose_item(self, pokemon, item):
        pokemon.remove_effect(Volatile.CHOICELOCK)

class ChoiceScarf(ItemEffect):
    def on_modify_spe(self, pokemon, engine, spe):
        return spe * 1.5

    on_modify_move = ChoiceBand.on_modify_move.__func__
    on_lose_item = ChoiceBand.on_lose_item.__func__

class ChoiceSpecs(ItemEffect):
    def on_modify_spa(self, pokemon, move, engine, spa):
        return spa * 1.5

    on_modify_move = ChoiceBand.on_modify_move.__func__
    on_lose_item = ChoiceBand.on_lose_item.__func__

class CustapBerry(ItemEffect):
    is_berry = True
    single_use = True

    def on_modify_priority(self, pokemon, move, engine):
        if (pokemon.hp <= pokemon.max_hp / 4.0 and
            pokemon.use_item(engine) is not FAIL):
            return 0.1
        return 0

class DampRock(ItemEffect):
    # Implemented in drizzle and raindance
    pass

class Eviolite(ItemEffect):
    def on_modify_def(self, pokemon, move, engine, def_):
        if not pokemon.pokedex_entry.fully_evolved:
            return def_ * 1.5
        return def_

    def on_modify_spd(self, pokemon, move, engine, spd):
        if not pokemon.pokedex_entry.fully_evolved:
            return spd * 1.5
        return spd

class ExpertBelt(ItemEffect):
    def on_modify_damage(self, user, move, damage, effectiveness):
        if effectiveness > 1:
            if __debug__: log.i("%s's damage was boosted by %s's ExpertBelt!", move, user)
            return damage * 1.2
        return damage

class BaseGem(ItemEffect):
    gem_type = None
    single_use = True

    def on_move_hit(self, user, move, engine):
        if (move.type is self.gem_type and
            move.category is not MoveCategory.STATUS and
            user.use_item(engine) is not FAIL
        ):
            user.set_effect(effects.GemVolatile())

class FightingGem(BaseGem):
    gem_type = Type.FIGHTING

class FlameOrb(ItemEffect):
    @priority(-26.2)
    def on_residual(self, pokemon, foe, engine):
        engine.set_status(pokemon, Status.BRN, pokemon)

class FlyingGem(BaseGem):
    gem_type = Type.FLYING

class FocusSash(ItemEffect):
    single_use = True

    @priority(0)
    def on_damage(self, pokemon, damage, cause, source, engine):
        if (pokemon.hp == pokemon.max_hp and
            damage >= pokemon.hp and
            cause is Cause.MOVE and
            pokemon.use_item(engine) is not FAIL
        ):
            if __debug__: log.i("%s held on with FocusSash!", pokemon)
            return pokemon.hp - 1
        return damage

class GriseousOrb(ItemEffect):
    removable = False

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.type in (Type.GHOST, Type.DRAGON):
            return base_power * 1.2
        return base_power

class HeatRock(ItemEffect):
    # Implemented in drought and sunnyday
    pass

class Leftovers(ItemEffect):
    @priority(-5.2)
    def on_residual(self, pokemon, foe, engine):
        if __debug__: log.i('%s restored a little HP using its Leftovers!', pokemon)
        engine.heal(pokemon, pokemon.max_hp / 16)



class LightClay(ItemEffect):
    pass
class PowerHerb(ItemEffect):
    pass

itemdex = {obj.__name__.lower(): obj for obj in vars().values() if
           inspect.isclass(obj) and
           issubclass(obj, BaseItem) and
           obj not in (BaseItem, ItemEffect) and
           'Base' not in obj.__name__}
