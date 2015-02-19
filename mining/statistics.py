"""
The statistics module is for gathering stats on Showdown's team generation for the randombattle
format. By running Showdown's randomTeam() function many times and collecting the output, we can
answer questions like:

- If my opponent's first pokemon is a Gengar, what is the probability that it knows Protect?
- If my opponent's Gengar Mega-Evolves and uses Disable, what is the new probability that it knows
  Protect? (it's more likely that it will have Disable and Protect together than Disable alone)
- If my opponent's Charizard uses Flare Blitz, how likely is it to be holding Leftovers vs
  Charizardite X or Y?
- What are the odds my opponent's Lanturn's ability is Volt Absorb vs Water Absorb?

Useful functions:
stats = collect_team_stats(10000) : return a RandbatsStatistics sampling 10000 teams
stats.to_pickle() : pickle it
RandbatsStatistics.from_pickle() : return the latest one, if it exists
"""
import json
import pickle
import shlex
import shutil
import subprocess
from collections import Counter
from copy import deepcopy
from itertools import repeat, izip_longest
from math import ceil
from multiprocessing import cpu_count
from functools import partial
from os.path import dirname, abspath, join, exists

from concurrent.futures import ProcessPoolExecutor, as_completed

from mining.pokedexmaker import SHOWDOWN_DIR, create_pokedex

if __debug__: from _logging import log

MINER_FILE = 'getNRandomTeams.js'
SHOWDOWN_MINER_LOCAL = abspath(join(dirname(__file__), 'js', MINER_FILE))
SHOWDOWN_MINER = join(SHOWDOWN_DIR, MINER_FILE)
MAX_TEAMS_PER_PROCESS = 1000

class RandbatsStatistics(object):
    def __init__(self):
        self.counter = {}
        self._probability = None
        self._moves_index = None
        self._ability_index = None
        self._item_index = None
        self.pokedex = create_pokedex()

    def __getitem__(self, index):
        """
        Return a pokemon of the format:

        {'ability': Counter({'Sticky Hold': 10, 'Poison Touch': 8}),
         'item': Counter({'Life Orb': 9, 'Black Sludge': 8, 'Choice Band': 1}),
         'level': Counter({86: 18}),
         'moves': Counter({'shadowsneak': 14, 'gunkshot': 13, 'icepunch': 12, 'firepunch': 11}),
         'movesets' Counter({(<tuple of four sorted moves>): 10, (...)})
         'number': 18}
        """
        return self.counter[index]

    def __contains__(self, index):
        return index in self.counter

    @classmethod
    def from_pickle(cls, path='mining/rbstats.pkl'):
        if not exists(path):
            if __debug__:
                log.w('%s does not exist. Creating one with 1000 teams. For better results, you '
                      'should mine for at least 100,000 teams', path)
            count_teams(1000).to_pickle(path)
        with open(path) as fin:
            self = pickle.load(fin)
        if not isinstance(self, cls):
            print "WARNING: Unpickled type does not match RandbatsStatistics"
        return self

    def to_pickle(self, path='mining/rbstats.pkl'):
        with open(path, 'w') as fout:
            pickle.dump(self, fout)

    @property
    def probability(self):
        """
        Dictionary {pokemon: value} where value is the same format as __getitem__
        Integer counts are float probabilities instead (except pokemon['number'])
        """
        if not self._probability:
            self._probability = deepcopy(self.counter)
            for pokemon in self._probability:
                stats = self._probability[pokemon]
                for ability in stats['ability']:
                    stats['ability'][ability] /= float(stats['number'])
                for move in stats['moves']:
                    stats['moves'][move] /= float(stats['number'])
                for item in stats['item']:
                    stats['item'][item] /= float(stats['number'])
        return self._probability

    @property
    def moves_index(self):
        """
        Return a move of the format:

        >>> rbstats.moves_index['boltstrike']
            {'Victini': 0.5622274003704367, 'Zekrom': 0.8625382983737921}
        """
        if not self._moves_index:
            self._moves_index = {}
            for pokemon in self.probability:
                for move, prob in self.probability[pokemon]['moves'].items():
                    if move not in self._moves_index:
                        self._moves_index[move] = {pokemon: prob}
                    else:
                        self._moves_index[move][pokemon] = prob
        return self._moves_index

    @property
    def ability_index(self):
        if not self._ability_index:
            self._ability_index = {}
            for pokemon in self.probability:
                for ability, prob in self.probability[pokemon]['ability'].items():
                    if ability not in self._ability_index:
                        self._ability_index[ability] = {pokemon: prob}
                    else:
                        self._ability_index[ability][pokemon] = prob
        return self._ability_index

    @property
    def item_index(self):
        if not self._item_index:
            self._item_index = {}
            for pokemon in self.probability:
                for item, prob in self.probability[pokemon]['item'].items():
                    if item not in self._item_index:
                        self._item_index[item] = {pokemon: prob}
                    else:
                        self._item_index[item][pokemon] = prob
        return self._item_index

    def sample(self, pokemon):
        """
        Add the data from this pokemon to self.counter.
        `pokemon` is one of the 6 JSON dict members of Scripts.randomTeam()
        """
        name = self.pokedex[pokemon['name']].name
        item = pokemon['item']
        if (((item.endswith('ite') and item != 'Eviolite')
             or item.endswith('ite X') or item.endswith('ite Y'))):
            forme = 0 if not item.endswith('Y') else 1
            name = str(self.pokedex[pokemon['name']].mega_formes[forme])
        if name not in self.counter:
            self.counter[name] = self.new_entry()

        self.counter[name]['number'] += 1
        for move in pokemon['moves']:
            self.counter[name]['moves'][str(move)] += 1
        self.counter[name]['ability'][str(pokemon['ability'])] += 1
        self.counter[name]['item'][str(pokemon['item'])] += 1
        self.counter[name]['level'][pokemon['level']] += 1
        self.counter[name]['movesets'][tuple(sorted(pokemon['moves']))] += 1

    def new_entry(self):
        return {'number': 0, 'moves': Counter(), 'ability': Counter(), 'item': Counter(),
                'level': Counter(), 'movesets': Counter()}

    def update(self, other):
        """
        Combine my data with another counter's data (possibly from another thread)
        """
        for name in other.counter:
            if name not in self.counter:
                self.counter[name] = self.new_entry()
            self.counter[name]['number'] += other.counter[name]['number']
            self.counter[name]['moves'].update(other.counter[name]['moves'])
            self.counter[name]['ability'].update(other.counter[name]['ability'])
            self.counter[name]['item'].update(other.counter[name]['item'])
            self.counter[name]['level'].update(other.counter[name]['level'])
            self.counter[name]['movesets'].update(other.counter[name]['movesets'])

    def move_probability(self, pokemon, move, known_moves):
        """
        Return the probability [0.0, 1.0] that pokemon knows move, given that it knows [known_moves]
        pokemon: str, move: str, known_moves: list<str>
        """
        moveset_counter = self.counter[pokemon]['movesets']
        possible_movesets = [moveset for moveset in moveset_counter if
                             all(move_ in moveset for move_ in known_moves)]

        if not possible_movesets:
            if __debug__:
                log.e("%s's known_moves %s does not correspond to any known moveset in rbstats. "
                      "Cannot calculate move probabilities; returning 0.5", pokemon, known_moves)
            return 0.5

        target_movesets = [moveset for moveset in possible_movesets if
                           move in moveset]

        probability = (float(sum(moveset_counter[moveset] for moveset in target_movesets)) /
                       sum(moveset_counter[moveset] for moveset in possible_movesets))
        return probability

    def item_probability(self, item, pokemon):
        """ Return the probability [0.0, 1.0] that `pokemon` is holding `item` """
        return self.counter[pokemon]['item'].get(item, 0) / float(self.counter[pokemon]['number'])

    def ability_probability(self, ability, pokemon):
        """ Return the probability [0.0, 1.0] that `pokemon` has `ability` """
        return (self.counter[pokemon]['ability'].get(ability, 0) /
                float(self.counter[pokemon]['number']))


def copy_miner_file():
    shutil.copyfile(SHOWDOWN_MINER_LOCAL, SHOWDOWN_MINER)

def distributemax(N, cap):
    """ Distribute N tasks into buckets of capacity cap: distributemax(34, 10) --> [9, 9, 8, 8] """
    return distribute(N, int(ceil(float(N) / cap)))


def distribute(N, b):
    """Distribute N tasks into b buckets. Return a list of the number of tasks in each bucket"""
    return [div + mod for div, mod in izip_longest(repeat(N//b, b), repeat(1, N%b), fillvalue=0)]


def collect_team_stats(n_teams, max_workers=cpu_count()):
    """
    Sample n_teams teams, or 6 * n_teams pokemon. Return a RandbatsStatistics.

    WARNING: Running this under nosetests can produce a deadlock (nose doesn't play well with
    multiprocessing). For now, test manually or just use the single-process count_teams().
    """
    copy_miner_file()
    counter = RandbatsStatistics()
    if n_teams < max_workers * MAX_TEAMS_PER_PROCESS:
        tasks = distribute(n_teams, max_workers)
    else:
        tasks = distributemax(n_teams, MAX_TEAMS_PER_PROCESS)

    with ProcessPoolExecutor(max_workers) as pool:
        futures = map(partial(pool.submit, count_teams), tasks)
        for future in as_completed(futures):
            counter.update(future.result())

    return counter


def count_teams(n_teams):
    counter = RandbatsStatistics()
    for team in get_json_teams(n_teams):
        for pokemon in team:
            counter.sample(pokemon)
    del counter.pokedex
    return counter


def get_json_teams(n_teams):
    """
    Use node + our custom entry point (getNRandomTeams.js) into Showdown to call Showdown's
    Scripts.randomTeam().  Return a list of random teams.

    NOTE: Showdown's battle engine occasionally crashes upon requiring repl.js when doing this
    concurrently due to the other process(es) removing ./logs/repl/battle-engine-XXXX, where XXXX is
    the node process id. In this case just try again.
    """
    node_cmd = 'nodejs %s %d' % (SHOWDOWN_MINER, n_teams)
    while True:
        json_teams = subprocess.check_output(shlex.split(node_cmd))
        try:
            return json.loads(json_teams)
        except ValueError:
            if not json_teams.startswith('\nCRASH: Error: ENOENT'):
                raise
