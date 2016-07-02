class EnumMeta(type):
    """ Enum metaclass. Creates a values dictionary with the attribute name as its own value """
    def __new__(mcs, name, bases, dct):
        for val in dct:
            dct[val] = val
        dct['values'] = {k: v for k, v in dct.items() if not k.startswith('__')}
        return type.__new__(mcs, name, bases, dct)

class Type(object):
    __metaclass__ = EnumMeta
    (NORMAL, FIGHTING, FLYING, POISON, GROUND, ROCK,
     BUG, GHOST, STEEL, FIRE, WATER, GRASS, ELECTRIC,
     PSYCHIC, ICE, DRAGON, DARK, FAIRY, NOTYPE) = [()]*19

class Status(object):
    __metaclass__ = EnumMeta
    BRN, FNT, FRZ, PAR, PSN, SLP, TOX = [()]*7

class Volatile(object):
    __metaclass__ = EnumMeta
    (ATTRACT, AUTOTOMIZE, BATONPASS, CHOICELOCK, CONFUSE, DESTINYBOND,
     DISABLE, ENCORE, FLASHFIRE, FLINCH, FORECAST, GEM, KINGSSHIELD,
     LEECHSEED, LOCKEDMOVE, MAGICCOAT, MAGNETRISE, PARENTALBOND,
     PARTIALTRAP, PERISHSONG, PIROUETTE, PROTECT, PURSUIT, ROOST,
     SHEERFORCE, SLOWSTART, SPIKYSHIELD, STALL, SUBSTITUTE, TAUNT,
     TRANSFORMED, TRAPPED, TRUANT, TWOTURNMOVE, UNBURDEN, VANISHED, YAWN) = [()]*37

class SideCondition(object):
    __metaclass__ = EnumMeta
    HEALINGWISH, LIGHTSCREEN, REFLECT, SAFEGUARD, TAILWIND, WISH = [()]*6

class Hazard(object):
    __metaclass__ = EnumMeta
    TOXICSPIKES, SPIKES, STEALTHROCK, STICKYWEB = [()]*4

class PseudoWeather(object):
    __metaclass__ = EnumMeta
    AURABREAK, DARKAURA, ELECTRICTERRAIN, FAIRYAURA, TRICKROOM = [()]*5

class Weather(object):
    __metaclass__ = EnumMeta
    (DELTASTREAM, DESOLATELAND, HAIL, PRIMORDIALSEA,
     RAINDANCE, SANDSTORM, SUNNYDAY) = [()]*7
Weather.TRIO = (Weather.PRIMORDIALSEA, Weather.DESOLATELAND, Weather.DELTASTREAM)

class Cause(object):
    __metaclass__ = EnumMeta
    (CONFUSE, CRASH, DIRECT, DRAIN, HAZARD, MOVE,
     OTHER, RECOIL, RESIDUAL, SELFDESTRUCT, WEATHER) = [()]*11

class Decision(object):
    __metaclass__ = EnumMeta
    MOVE, MEGAEVO, POSTSWITCH, RESIDUAL, SWITCH = [()]*5

class MoveCategory(object):
    __metaclass__ = EnumMeta
    PHYSICAL, SPECIAL, STATUS = [()]*3
STATUS, PHYSICAL, SPECIAL = MoveCategory.STATUS, MoveCategory.PHYSICAL, MoveCategory.SPECIAL

FAIL = type('', (object,), {'__repr__': lambda _: '<FAIL>'})()
ABILITY = type('', (object,), {'__repr__': lambda _: '<ABILITY>'})()
ITEM = type('', (object,), {'__repr__': lambda _: '<ITEM>'})()
POWDER = type('', (object,), {'__repr__': lambda _: '<POWDER>'})()
