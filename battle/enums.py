from misc.enum import BaseEnum, NoCopy

class Type(BaseEnum):
    NORMAL = ()
    FIGHTING = ()
    FLYING = ()
    POISON = ()
    GROUND = ()
    ROCK = ()
    BUG = ()
    GHOST = ()
    STEEL = ()
    FIRE = ()
    WATER = ()
    GRASS = ()
    ELECTRIC = ()
    PSYCHIC = ()
    ICE = ()
    DRAGON = ()
    DARK = ()
    FAIRY = ()
    NOTYPE = ()

class Status(BaseEnum):
    BRN = ()
    FNT = ()
    FRZ = ()
    PAR = ()
    PSN = ()
    SLP = ()
    TOX = ()

class Volatile(BaseEnum):
    ATTRACT = ()
    AUTOTOMIZE = ()
    BATONPASS = ()
    CHOICELOCK = ()
    CONFUSE = ()
    DESTINYBOND = ()
    DISABLE = ()
    ENCORE = ()
    FLASHFIRE = ()
    FLINCH = ()
    FORECAST = ()
    GEM = ()
    KINGSSHIELD = ()
    LEECHSEED = ()
    LOCKEDMOVE = ()
    MAGICCOAT = ()
    MAGNETRISE = ()
    PARENTALBOND = ()
    PARTIALTRAP = ()
    PERISHSONG = ()
    PIROUETTE = ()
    PROTECT = ()
    PURSUIT = ()
    ROOST = ()
    SHEERFORCE = ()
    SLOWSTART = ()
    SPIKYSHIELD = ()
    STALL = ()
    SUBSTITUTE = ()
    TAUNT = ()
    TRANSFORMED = ()
    TRAPPED = ()
    TRUANT = ()
    TWOTURNMOVE = ()
    UNBURDEN = ()
    VANISHED = ()
    YAWN = ()

class SideCondition(BaseEnum):
    HEALINGWISH = ()
    LIGHTSCREEN = ()
    REFLECT = ()
    SAFEGUARD = ()
    TAILWIND = ()
    WISH = ()

class Hazard(BaseEnum):
    TOXICSPIKES = ()
    SPIKES = ()
    STEALTHROCK = ()
    STICKYWEB = ()

class PseudoWeather(BaseEnum):
    AURABREAK = ()
    DARKAURA = ()
    ELECTRICTERRAIN = ()
    FAIRYAURA = ()
    TRICKROOM = ()

class Weather(BaseEnum):
    DELTASTREAM = ()
    DESOLATELAND = ()
    HAIL = ()
    PRIMORDIALSEA = ()
    RAINDANCE = ()
    SANDSTORM = ()
    SUNNYDAY = ()
Weather.TRIO = (Weather.PRIMORDIALSEA, Weather.DESOLATELAND, Weather.DELTASTREAM)

class Cause(BaseEnum):
    CONFUSE = ()
    CRASH = ()
    DIRECT = ()
    DRAIN = ()
    HAZARD = ()
    MOVE = ()
    OTHER = ()
    RECOIL = ()
    RESIDUAL = ()
    SELFDESTRUCT = ()
    WEATHER = ()

class Decision(BaseEnum):
    MOVE = ()
    MEGAEVO = ()
    SWITCH = ()

class MoveCategory(BaseEnum):
    PHYSICAL = ()
    SPECIAL = ()
    STATUS = ()
STATUS, PHYSICAL, SPECIAL = MoveCategory.STATUS, MoveCategory.PHYSICAL, MoveCategory.SPECIAL

class SingletonEnum(NoCopy):
    def __repr__(self):
        return self.__class__.__name__.join(('<', '>'))

FAIL = type('FAIL', (SingletonEnum,), {})()
ABILITY = type('ABILITY', (SingletonEnum,), {})()
ITEM = type('ITEM', (SingletonEnum,), {})()
POWDER = type('POWDER', (SingletonEnum,), {})()
