from misc.enum import EnumBase, NoCopy

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

class SingletonEnum(NoCopy):
    def __repr__(self):
        return self.__class__.__name__.join(('<', '>'))

FAIL = type('FAIL', (SingletonEnum,), {})()
ABILITY = type('ABILITY', (SingletonEnum,), {})()
ITEM = type('ITEM', (SingletonEnum,), {})()
POWDER = type('POWDER', (SingletonEnum,), {})()
