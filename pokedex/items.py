"""
All items are implemented here, and gathered in to the `itemdex` dictionary.
Items are named in CamelCase, but their .name attribute is lowercasenospaces.
"""
import inspect

from misc.functions import priority
from pokedex import effects
from pokedex.baseeffect import BaseEffect
from pokedex.enums import ITEM, Type, Cause, MoveCategory, Status, Volatile

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
    is_removable = True
    source = ITEM

    def __repr__(self):
        return "%s()" % self.__class__.__name__

class ItemEffect(BaseItem, BaseEffect):
    pass

class AirBalloon(ItemEffect):
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




class LightClay(ItemEffect):
    pass
class PowerHerb(ItemEffect):
    pass

itemdex = {obj.__name__.lower(): obj for obj in vars().values() if
           inspect.isclass(obj) and
           issubclass(obj, BaseItem) and
           obj not in (BaseItem, ItemEffect) and
           'Base' not in obj.__name__}
