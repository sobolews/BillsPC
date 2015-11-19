"""
Create a pokedex, which is a dict mapping each pokemon/species name to PokedexEntry, which
contains information such as the types and base stats of the pokemon.
"""
import json
import shlex
import subprocess
from os.path import dirname, abspath, join
from pprint import pformat

from pokedex.stats import PokemonStats
from pokedex.enums import Type

SHOWDOWN_DIR = abspath(join(dirname(__file__), 'Pokemon-Showdown'))
POKEDEX_JS_PATH = join(SHOWDOWN_DIR, 'data', 'pokedex.js')

_pokedex = {}

def create_pokedex():
    if not _pokedex:
        parse_pokedex_js(_pokedex)
    return _pokedex

def _js_file_to_dict(path):
    """
    Parse a javascript data file and return the data as a dict.
    """
    json_data = subprocess.check_output(shlex.split(
        'nodejs -p "JSON.stringify(require(\'%s\'));"' % path))
    return json.loads(json_data)

def parse_pokedex_js(pokedex):
    """
    Parse Pokemon-Showdown/data/pokedex.js and get name, types, base stats, and abilities for
    all pokemon
    """
    data = _js_file_to_dict(POKEDEX_JS_PATH)['BattlePokedex']
    for pokemon, attrs in data.items():
        if attrs['num'] <= 0: # This excludes missingno and CAP pokemon
            continue
        pokemon = str(pokemon)
        species = str(attrs['species'])
        weight = attrs['weightkg']
        mega_formes = [forme for forme in attrs.get('otherFormes', ()) if 'mega' in forme]
        types = (Type[attrs['types'][0].upper()],
                 Type[attrs['types'][1].upper()] if len(attrs['types']) > 1 else None)
        base_stats = PokemonStats(
            attrs['baseStats']['hp'],
            attrs['baseStats']['atk'],
            attrs['baseStats']['def'],
            attrs['baseStats']['spa'],
            attrs['baseStats']['spd'],
            attrs['baseStats']['spe'])
        fully_evolved = (attrs.get('evos') is None)

        pokedex[pokemon] = pokedex[species] = PokedexEntry(
            pokemon, species, weight, mega_formes, fully_evolved, types, base_stats)
        pokedex[pokemon[:18]] = pokedex[pokemon] # workaround: the showdown server
                                                 # cuts names off at 18 chars


class PokedexEntry(object):
    def __init__(self, name, species, weight, mega_formes, fully_evolved, types, base_stats):
        self.name = name
        self.species = species
        self.weight = weight
        self.mega_formes = mega_formes
        self.fully_evolved = fully_evolved
        self.types = types
        self.base_stats = base_stats

    def __repr__(self):
        return pformat(self.__dict__)
