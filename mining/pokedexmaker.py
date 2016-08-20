"""
Create a pokedex, which is a dict mapping each pokemon/species name to PokedexEntry, which
contains information such as the types and base stats of the pokemon.
"""
import json
import shlex
import subprocess
from distutils.spawn import find_executable
from os.path import dirname, abspath, join
from pprint import pformat

from pokedex.stats import PokemonStats
from pokedex.enums import Type
from misc.functions import normalize_name

NODE_EXECUTABLE = 'node' if find_executable('nodejs') is None else 'nodejs'
SHOWDOWN_DIR = abspath(join(dirname(__file__), 'Pokemon-Showdown'))
POKEDEX_JS_PATH = join(SHOWDOWN_DIR, 'data', 'pokedex.js')

def _js_file_to_dict(path):
    """
    Parse a javascript data file and return the data as a dict.
    """
    json_data = subprocess.check_output(shlex.split(
        '%s -p "JSON.stringify(require(\'%s\'));"' % (NODE_EXECUTABLE, path)))
    return json.loads(json_data)

def parse_pokedex_js(path=POKEDEX_JS_PATH):
    """
    Parse Pokemon-Showdown/data/pokedex.js and get name, types, base stats, and abilities for
    all pokemon. Return the pokedex dict and a type-based index.
    """
    pokedex = {}
    type_index = {}
    data = _js_file_to_dict(path)['BattlePokedex']
    for pokemon, attrs in data.items():
        if attrs['num'] <= 0: # This excludes missingno and CAP pokemon
            continue
        pokemon = str(pokemon)
        species = str(attrs['species'])
        weight = attrs['weightkg']
        mega_formes = [str(forme) for forme in attrs.get('otherFormes', ()) if 'mega' in forme]
        types = (Type.values[attrs['types'][0].upper()],
                 Type.values[attrs['types'][1].upper()] if len(attrs['types']) > 1 else None)
        base_stats = PokemonStats(
            attrs['baseStats']['hp'],
            attrs['baseStats']['atk'],
            attrs['baseStats']['def'],
            attrs['baseStats']['spa'],
            attrs['baseStats']['spd'],
            attrs['baseStats']['spe'])
        fully_evolved = (attrs.get('evos') is None)
        abilities = [normalize_name(str(ability)) for ability in attrs['abilities'].values()]

        pokedex[pokemon] = pokedex[species] = PokedexEntry(
            pokemon, species, weight, mega_formes, fully_evolved, types, base_stats, abilities)
        pokedex[pokemon[:18]] = pokedex[pokemon] # workaround: the showdown server
                                                 # cuts names off at 18 chars
        types = sorted(types)
        type_index.setdefault(tuple(types), []).append(pokemon)
        type_index.setdefault(tuple(reversed(types)), []).append(pokemon)

    return pokedex, type_index


class PokedexEntry(object):
    def __init__(self, name, species, weight, mega_formes, fully_evolved,
                 types, base_stats, abilities):
        self.name = name
        self.species = species
        self.weight = weight
        self.mega_formes = mega_formes
        self.fully_evolved = fully_evolved
        self.types = types
        self.base_stats = base_stats
        self.abilities = abilities

    def __repr__(self):
        return pformat(self.__dict__)


pokedex, type_index = parse_pokedex_js()
