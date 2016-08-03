class EnumMeta(type):
    """ Enum metaclass. Creates a values dictionary with the attribute name as its own value """
    def __new__(mcs, name, bases, dct):
        for val in dct:
            dct[val] = val
        dct['values'] = {k: v for k, v in dct.items() if not k.startswith('__')}
        return type.__new__(mcs, name, bases, dct)

class EnumBase(object):
    __metaclass__ = EnumMeta

class Type(EnumBase):
    (NORMAL, FIGHTING, FLYING, POISON, GROUND, ROCK,
     BUG, GHOST, STEEL, FIRE, WATER, GRASS, ELECTRIC,
     PSYCHIC, ICE, DRAGON, DARK, FAIRY, NOTYPE) = [()]*19

class Status(EnumBase):
    BRN, FNT, FRZ, PAR, PSN, SLP, TOX = [()]*7

class Volatile(EnumBase):
    (ATTRACT, AUTOTOMIZE, BATONPASS, CHOICELOCK, CONFUSE, DESTINYBOND,
     DISABLE, ENCORE, FLASHFIRE, FLINCH, FORECAST, GEM, KINGSSHIELD,
     LEECHSEED, LOCKEDMOVE, MAGICCOAT, MAGNETRISE, PARENTALBOND,
     PARTIALTRAP, PERISHSONG, PIROUETTE, PROTECT, PURSUIT, ROOST,
     SHEERFORCE, SLOWSTART, SPIKYSHIELD, STALL, SUBSTITUTE, TAUNT,
     TRANSFORMED, TRAPPED, TRUANT, TWOTURNMOVE, UNBURDEN, VANISHED, YAWN) = [()]*37

class SideCondition(EnumBase):
    HEALINGWISH, LIGHTSCREEN, REFLECT, SAFEGUARD, TAILWIND, WISH = [()]*6

class Hazard(EnumBase):
    TOXICSPIKES, SPIKES, STEALTHROCK, STICKYWEB = [()]*4

class PseudoWeather(EnumBase):
    AURABREAK, DARKAURA, ELECTRICTERRAIN, FAIRYAURA, TRICKROOM = [()]*5

class Weather(EnumBase):
    (DELTASTREAM, DESOLATELAND, HAIL, PRIMORDIALSEA,
     RAINDANCE, SANDSTORM, SUNNYDAY) = [()]*7
Weather.TRIO = (Weather.PRIMORDIALSEA, Weather.DESOLATELAND, Weather.DELTASTREAM)

class Cause(EnumBase):
    (CONFUSE, CRASH, DIRECT, DRAIN, HAZARD, MOVE,
     OTHER, RECOIL, RESIDUAL, SELFDESTRUCT, WEATHER) = [()]*11

class Decision(EnumBase):
    MOVE, MEGAEVO, POSTSWITCH, RESIDUAL, SWITCH = [()]*5

class MoveCategory(EnumBase):
    PHYSICAL, SPECIAL, STATUS = [()]*3
STATUS, PHYSICAL, SPECIAL = MoveCategory.STATUS, MoveCategory.PHYSICAL, MoveCategory.SPECIAL

FAIL = type('', (object,), {'__repr__': lambda _: '<FAIL>'})()
ABILITY = type('', (object,), {'__repr__': lambda _: '<ABILITY>'})()
ITEM = type('', (object,), {'__repr__': lambda _: '<ITEM>'})()
POWDER = type('', (object,), {'__repr__': lambda _: '<POWDER>'})()
