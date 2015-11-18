import json
import pickle
import shlex
import subprocess
from os.path import dirname, abspath, join
from pprint import pformat

from misc.exceptions import NotAPokedexError
from pokedex.stats import PokemonStats
from pokedex.enums import Type

SHOWDOWN_DIR = abspath(join(dirname(__file__), 'Pokemon-Showdown'))
POKEDEX_JS_PATH = join(SHOWDOWN_DIR, 'data', 'pokedex.js')

def create_pokedex():
    return PokedexDataMiner().make_pokedex()

class PokedexDataMiner(object):
    """
    Make a pokedex: PokedexDataMiner().make_pokedex()
    """
    def __init__(self):
        self.pokedex = Pokedex()

    def make_pokedex(self):
        self.parse_pokedex_js()
        return self.pokedex

    def _js_file_to_dict(self, path):
        """
        Parse a javascript data file and return the data as a dict.
        """
        json_data = subprocess.check_output(shlex.split(
            'nodejs -p "JSON.stringify(require(\'%s\'));"' % path))
        return json.loads(json_data)

    def parse_pokedex_js(self):
        """
        Parse Pokemon-Showdown/data/pokedex.js and get name, types, base stats, and abilities for
        all pokemon
        """
        data = self._js_file_to_dict(POKEDEX_JS_PATH)['BattlePokedex']
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

            self.pokedex[pokemon] = self.pokedex[species] = PokedexEntry(
                pokemon, species, weight, mega_formes, fully_evolved, types, base_stats)
            self.pokedex[pokemon[:18]] = self.pokedex[pokemon] # workaround: the showdown server
                                                               # cuts names off at 18 chars


class Pokedex(dict):
    @classmethod
    def from_pickle(cls, pickle_path='mining/pokedex.pkl'):
        with open(pickle_path) as fin:
            self = pickle.load(fin)
        if not isinstance(self, cls):
            raise NotAPokedexError
        return self

    def to_pickle(self, pickle_path='mining/pokedex.pkl'):
        with open(pickle_path, 'w') as fout:
            pickle.dump(self, fout)


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
