# pylint: disable=bad-whitespace
"""
Pokemon type chart
"""

from pokedex.enums import Type

_TYPE_MATRIX = (                                                                     # v Attack
#   Nor Fig Fly Poi Gro Roc Bug Gho Ste Fir Wat Gra Ele Psy Ice Dra Dar Fai ??? None # < Defend
    (1,  1,  1,  1,  1, .5,  1,  0, .5,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1), # NORMAL
    (2,  1, .5, .5,  1,  2, .5,  0,  2,  1,  1,  1,  1, .5,  2,  1,  2, .5,  1,  1), # FIGHTING
    (1,  2,  1,  1,  1, .5,  2,  1, .5,  1,  1,  2, .5,  1,  1,  1,  1,  1,  1,  1), # FLYING
    (1,  1,  1, .5, .5, .5,  1, .5,  0,  1,  1,  2,  1,  1,  1,  1,  1,  2,  1,  1), # POISON
    (1,  1,  0,  2,  1,  2, .5,  1,  2,  2,  1, .5,  2,  1,  1,  1,  1,  1,  1,  1), # GROUND
    (1, .5,  2,  1, .5,  1,  2,  1, .5,  2,  1,  1,  1,  1,  2,  1,  1,  1,  1,  1), # ROCK
    (1, .5, .5, .5,  1,  1,  1, .5, .5, .5,  1,  2,  1,  2,  1,  1,  2, .5,  1,  1), # BUG
    (0,  1,  1,  1,  1,  1,  1,  2,  1,  1,  1,  1,  1,  2,  1,  1, .5,  1,  1,  1), # GHOST
    (1,  1,  1,  1,  1,  2,  1,  1, .5, .5, .5,  1, .5,  1,  2,  1,  1,  2,  1,  1), # STEEL
    (1,  1,  1,  1,  1, .5,  2,  1,  2, .5, .5,  2,  1,  1,  2, .5,  1,  1,  1,  1), # FIRE
    (1,  1,  1,  1,  2,  2,  1,  1,  1,  2, .5, .5,  1,  1,  1, .5,  1,  1,  1,  1), # WATER
    (1,  1, .5, .5,  2,  2, .5,  1, .5, .5,  2, .5,  1,  1,  1, .5,  1,  1,  1,  1), # GRASS
    (1,  1,  2,  1,  0,  1,  1,  1,  1,  1,  2, .5, .5,  1,  1, .5,  1,  1,  1,  1), # ELECTRIC
    (1,  2,  1,  2,  1,  1,  1,  1, .5,  1,  1,  1,  1, .5,  1,  1,  0,  1,  1,  1), # PSYCHIC
    (1,  1,  2,  1,  2,  1,  1,  1, .5, .5, .5,  2,  1,  1, .5,  2,  1,  1,  1,  1), # ICE
    (1,  1,  1,  1,  1,  1,  1,  1, .5,  1,  1,  1,  1,  1,  1,  2,  1,  0,  1,  1), # DRAGON
    (1, .5,  1,  1,  1,  1,  1,  2,  1,  1,  1,  1,  1,  2,  1,  1, .5, .5,  1,  1), # DARK
    (1,  2,  1, .5,  1,  1,  1,  1, .5, .5,  1,  1,  1,  1,  1,  2,  2,  1,  1,  1), # FAIRY
    (1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1), # ???
#   Nor Fig Fly Poi Gro Roc Bug Gho Ste Fir Wat Gra Ele Psy Ice Dra Dar Fai ??? None # < Defend
)                                                                                    # ^ Attack

def effectiveness(move_type, pokemon):
    assert isinstance(move_type, Type)

    # Subtract one from each enum value because enums count from 1
    row = _TYPE_MATRIX[move_type.value - 1]
    type1 = pokemon.types[0].value - 1
    type2 = pokemon.types[1].value - 1 if (pokemon.types[1] is not None) else len(Type)

    return row[type1] * row[type2]

def type_effectiveness(move_type, pokemon_type):
    return _TYPE_MATRIX[move_type.value - 1][pokemon_type.value - 1]
