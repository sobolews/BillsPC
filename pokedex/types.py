# pylint: disable=bad-whitespace
"""
Pokemon type chart
"""

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
    (1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1), # NOTYPE
#   Nor Fig Fly Poi Gro Roc Bug Gho Ste Fir Wat Gra Ele Psy Ice Dra Dar Fai ??? None # < Defend
)                                                                                    # ^ Attack

_INDEXES = {'NORMAL': 0, 'FIGHTING': 1, 'FLYING': 2, 'POISON': 3, 'GROUND': 4,
            'ROCK': 5, 'BUG': 6, 'GHOST': 7, 'STEEL': 8, 'FIRE': 9, 'WATER': 10,
            'GRASS': 11, 'ELECTRIC': 12, 'PSYCHIC': 13, 'ICE': 14, 'DRAGON': 15,
            'DARK': 16, 'FAIRY': 17, 'NOTYPE': 18}

def effectiveness(move_type, pokemon):
    assert move_type in _INDEXES

    row = _TYPE_MATRIX[_INDEXES[move_type]]
    type1 = _INDEXES[pokemon.types[0]]
    type2 = _INDEXES[pokemon.types[1]] if (pokemon.types[1] is not None) else 19

    return row[type1] * row[type2]

def type_effectiveness(move_type, pokemon_type):
    return _TYPE_MATRIX[_INDEXES[move_type]][_INDEXES[pokemon_type]]
