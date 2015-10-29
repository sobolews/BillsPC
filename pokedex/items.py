"""
All items are implemented here, and gathered in to the `itemdex` dictionary.
Items are named in CamelCase, but their .name attribute is lowercasenospaces.
"""
import inspect

from misc.functions import priority
from pokedex.baseeffect import BaseEffect
from pokedex.enums import ITEM, Type, Cause, MoveCategory

class BaseItem(object):
    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            dct['name'] = name.lower()
            return type.__new__(cls, name, bases, dct)

        def __repr__(self):
            return self.__name__

    choicelock = False
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
            pokemon.use_item()

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




class LightClay(ItemEffect):
    pass
class PowerHerb(ItemEffect):
    pass

itemdex = {obj.__name__.lower(): obj for obj in vars().values() if
           inspect.isclass(obj) and
           issubclass(obj, BaseItem) and
           obj not in (BaseItem, ItemEffect) and
           'Base' not in obj.__name__}
