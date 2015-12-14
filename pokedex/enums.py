from enum import Enum

Type = Enum(
    'Type', ('NORMAL', 'FIGHTING', 'FLYING', 'POISON', 'GROUND', 'ROCK', 'BUG', 'GHOST', 'STEEL',
             'FIRE', 'WATER', 'GRASS', 'ELECTRIC', 'PSYCHIC', 'ICE', 'DRAGON', 'DARK', 'FAIRY',
             '???')) # '???' type used for confusion damage and struggle

Status = Enum(
    'Status', ('BRN', 'FNT', 'FRZ', 'PAR', 'PSN', 'SLP', 'TOX'))

Volatile = Enum(
    'Volatile', ('ATTRACT', 'AUTOTOMIZE', 'BATONPASS', 'CHOICELOCK', 'CONFUSE', 'DESTINYBOND',
                 'DISABLE', 'ENCORE', 'FLASHFIRE', 'FLINCH', 'FORECAST', 'GEM', 'KINGSSHIELD',
                 'LEECHSEED', 'LOCKEDMOVE', 'MAGICCOAT', 'MAGNETRISE', 'PARENTALBOND',
                 'PARTIALTRAP', 'PERISHSONG', 'PIROUETTE', 'PROTECT', 'PURSUIT', 'ROOST',
                 'SHEERFORCE', 'SLOWSTART', 'SPIKYSHIELD', 'STALL', 'SUBSTITUTE', 'TAUNT',
                 'TRANSFORMED', 'TRAPPED', 'TRAPPER', 'TRUANT', 'TWOTURNMOVE', 'UNBURDEN',
                 'VANISHED', 'YAWN'))

SideCondition = Enum(
    'SideCondition', ('HEALINGWISH', 'LIGHTSCREEN', 'REFLECT', 'SAFEGUARD', 'TAILWIND', 'WISH'))

Hazard = Enum(
    'Hazard', ('TOXICSPIKES', 'SPIKES', 'STEALTHROCK', 'STICKYWEB'))

PseudoWeather = Enum(
    'PseudoWeather', ('AURABREAK', 'DARKAURA', 'ELECTRICTERRAIN', 'FAIRYAURA', 'TRICKROOM'))

Weather = Enum(
    'Weather', ('DELTASTREAM', 'DESOLATELAND', 'HAIL', 'PRIMORDIALSEA', 'RAINDANCE', 'SANDSTORM',
                'SUNNYDAY'))
Weather.TRIO = (Weather.PRIMORDIALSEA, Weather.DESOLATELAND, Weather.DELTASTREAM)

Cause = Enum(
    'Cause', ('CONFUSE', 'CRASH', 'DIRECT', 'DRAIN', 'HAZARD', 'MOVE', 'OTHER', 'RECOIL',
              'RESIDUAL', 'SELFDESTRUCT', 'WEATHER'))

Decision = Enum(
    'Decision', ('MOVE', 'MEGAEVO', 'POSTSWITCH', 'RESIDUAL', 'SWITCH'))

MoveCategory = Enum(
    'MoveCategory', ('PHYSICAL', 'SPECIAL', 'STATUS'))
STATUS, PHYSICAL, SPECIAL = MoveCategory.STATUS, MoveCategory.PHYSICAL, MoveCategory.SPECIAL

FAIL = type('', (object,), {'__repr__': lambda _: '<FAIL>'})()
ABILITY = type('', (object,), {'__repr__': lambda _: '<ABILITY>'})()
ITEM = type('', (object,), {'__repr__': lambda _: '<ITEM>'})()
POWDER = type('', (object,), {'__repr__': lambda _: '<POWDER>'})()
