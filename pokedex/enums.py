from enum import Enum

Type = Enum(
    'Type', ('NORMAL', 'FIGHTING', 'FLYING', 'POISON', 'GROUND', 'ROCK', 'BUG', 'GHOST', 'STEEL',
             'FIRE', 'WATER', 'GRASS', 'ELECTRIC', 'PSYCHIC', 'ICE', 'DRAGON', 'DARK', 'FAIRY',
             '???')) # '???' type used for confusion damage and struggle

Status = Enum(
    'Status', ('BRN', 'FRZ', 'PAR', 'PSN', 'TOX', 'SLP', 'FNT'))

Volatile = Enum(
    'Volatile', ('CONFUSE', 'FLINCH', 'PARTIALTRAP', 'TRAPPED', 'TRAPPER', 'TWOTURNMOVE',
                 'CHOICELOCK', 'PROTECT', 'LOCKEDMOVE', 'DISABLE', 'ENCORE', 'PERISHSONG',
                 'LEECHSEED', 'YAWN', 'MAGICCOAT', 'SUBSTITUTE', 'VANISHED', 'AUTOTOMIZE',
                 'FLASHFIRE', 'TAUNT', 'IGNOREABILITY', 'IGNOREITEM', 'UNBURDEN', 'DESTINYBOND',
                 'SHEERFORCE', 'KINGSSHIELD', 'SPIKYSHIELD', 'STALL', 'MAGNETRISE', 'ROOST',
                 'BATONPASS', 'PURSUIT', 'ATTRACT', 'TRANSFORMED'))

SideCondition = Enum(
    'SideCondition', ('LIGHTSCREEN', 'REFLECT', 'TAILWIND', 'HEALINGWISH', 'WISH', 'SAFEGUARD'))

Hazard = Enum(
    'Hazard', ('SPIKES', 'TOXICSPIKES', 'STEALTHROCK', 'STICKYWEB'))

PseudoWeather = Enum(
    'PseudoWeather', ('ELECTRICTERRAIN', 'TRICKROOM', 'DARKAURA', 'FAIRYAURA', 'AURABREAK'))

Weather = Enum(
    'Weather', ('RAINDANCE', 'PRIMORDIALSEA', 'SUNNYDAY', 'DESOLATELAND', 'HAIL', 'SANDSTORM',
                'DELTASTREAM'))
Weather.TRIO = (Weather.PRIMORDIALSEA, Weather.DESOLATELAND, Weather.DELTASTREAM)

Cause = Enum(
    'Cause', ('MOVE', 'RESIDUAL', 'WEATHER', 'HAZARD', 'RECOIL', 'SELFDESTRUCT', 'OTHER',
              'CONFUSE', 'DIRECT', 'DRAIN'))

Decision = Enum(
    'Decision', ('MOVE', 'SWITCH', 'MEGAEVO', 'RESIDUAL', 'POSTSWITCH'))

MoveCategory = Enum(
    'MoveCategory', ('STATUS', 'PHYSICAL', 'SPECIAL'))
STATUS, PHYSICAL, SPECIAL = MoveCategory.STATUS, MoveCategory.PHYSICAL, MoveCategory.SPECIAL

FAIL = type('', (object,), {'__repr__': lambda _: '<FAIL>'})()
ABILITY = type('', (object,), {'__repr__': lambda _: '<ABILITY>'})()
ITEM = type('', (object,), {'__repr__': lambda _: '<ITEM>'})()
POWDER = type('', (object,), {'__repr__': lambda _: '<POWDER>'})()
