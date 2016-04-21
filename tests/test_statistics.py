from random import randint
from unittest import TestCase

from mining import statistics
from tests.test_statistics_data import TEAM1, TEAM2, TEAM3

class TestRandbatsCounter(TestCase):
    def test_sample(self):
        counter = statistics.RandbatsStatistics()
        for pokemon in TEAM1:
            counter.sample(pokemon)
        self.assertIn('rotomwash', counter)
        self.assertEqual(counter['rotomwash']['number'], 1)
        self.assertIn('hydropump', counter['rotomwash']['moves'])
        self.assertEqual(counter['rotomwash']['moves']['hydropump'], 1)
        self.assertEqual(counter['rotomwash']['ability']['levitate'], 1)
        self.assertEqual(counter['rotomwash']['item']['leftovers'], 1)

        for pokemon in TEAM1:
            counter.sample(pokemon)
        for pokemon in TEAM2:
            counter.sample(pokemon)

        self.assertEqual(counter['glaceon']['number'], 1)
        self.assertEqual(counter['meloetta']['number'], 2)
        self.assertEqual(counter['starmie']['number'], 3)
        self.assertEqual(counter['starmie']['moves']['rapidspin'], 1)
        self.assertEqual(counter['starmie']['moves']['recover'], 2)
        self.assertEqual(counter['starmie']['moves']['thunderbolt'], 3)

        self.assertIn(74, counter['starmie']['level'])
        self.assertEqual(counter['starmie']['level'][74], 2)
        self.assertEqual(counter['starmie']['level'][71], 1)
        self.assertEqual(counter['starmieL74']['number'], 2)
        self.assertEqual(counter['starmieL71']['number'], 1)

        self.assertTrue(counter['steelixmega'])
        self.assertTrue(counter['steelix'])
        self.assertTrue(counter['steelixL82'])

    def test_update(self):
        counter = self.get_counter()

        def assert_moves():
            self.assertEqual(counter['starmie']['number'], 4)
            self.assertEqual(counter['starmie']['moves']['rapidspin'], 2)
            self.assertEqual(counter['starmie']['moves']['recover'], 2)
            self.assertEqual(counter['starmie']['moves']['thunderbolt'], 4)
            self.assertEqual(counter['entei']['number'], 1)
            self.assertEqual(counter['glaceon']['number'], 1)

        assert_moves()
        counter.probability
        assert_moves()

    def test_moves_index(self):
        counter = self.get_counter()

        self.assertIn('heatran', counter.moves_index['stealthrock'])
        self.assertIn('steelixmega', counter.moves_index['stealthrock'])
        self.assertIn('steelix', counter.moves_index['stealthrock'])
        self.assertIn('steelixL82', counter.moves_index['stealthrock'])
        self.assertEqual(counter.moves_index['thunderbolt']['starmie'], 1)
        self.assertEqual(counter.moves_index['rapidspin']['starmie'], 0.5)

    def test_attr_probability(self):
        starmie = {'ability': 'Natural Cure',
                   'evs': {'atk': 85, 'def': 85, 'hp': 85, 'spa': 85, 'spd': 85, 'spe': 85},
                   'item': 'Life Orb',
                   'ivs': {'atk': 31, 'def': 31, 'hp': 31, 'spa': 31, 'spd': 31, 'spe': 31},
                   'level': 74,
                   'moves': ['recover', 'psyshock', 'thunderbolt', 'scald'],
                   'name': 'Starmie',
                   'species': 'Starmie',
                   'shiny': False}
        counter = statistics.RandbatsStatistics()
        for _ in range(3):
            counter.sample(starmie)
        starmie['moves'][0] = 'rapidspin'
        counter.sample(starmie)
        starmie['moves'][1] = 'hydropump'
        for _ in range(5):
            counter.sample(starmie)
        starmie['moves'][2] = 'grassknot'
        counter.sample(starmie)

        self.assertEqual(0.7, counter.attr_probability('starmie', 'rapidspin', []))
        self.assertEqual(1, counter.attr_probability('starmie', 'rapidspin', ['hydropump']))
        self.assertEqual(6.0/7, counter.attr_probability('starmie', 'hydropump', ['rapidspin']))
        self.assertEqual(0, counter.attr_probability('starmie', 'grassknot', ['thunderbolt']))
        self.assertEqual(0, counter.attr_probability('starmie', 'darkvoid', []))

    def get_counter(self):
        """
        Double-sample TEAM1; sample TEAM3 in a separate counter and update from it
        """
        counter = statistics.RandbatsStatistics()
        for pokemon in TEAM1:
            counter.sample(pokemon)
            counter.sample(pokemon)
        for pokemon in TEAM2:
            counter.sample(pokemon)
        counter2 = statistics.RandbatsStatistics()
        for pokemon in TEAM3:
            counter2.sample(pokemon)
        counter.update(counter2)
        return counter


class TestStatisticsModule(TestCase):
    def test_distribute(self):
        N = randint(100, 10000)
        b = randint(2, 100)
        dist = statistics.distribute(N, b)
        self.assertEqual(sum(dist), N)
        self.assertTrue(all(t in (dist[0], dist[0] - 1) for t in dist))
        self.assertTrue(len(dist), b)

    def test_distributemax(self):
        self.assertEqual(statistics.distributemax(34, 10), [9, 9, 8, 8])

    def test_json_teams_format(self):
        """
        Test for any changes to the json output format of Showdown's Scripts.randomTeam()

        {u'ability': u'Teravolt',
         u'evs': {u'atk': 85, u'def': 85, u'hp': 85, u'spa': 85, u'spd': 85, u'spe': 85},
         u'item': u'Leftovers',
         u'ivs': {u'atk': 31, u'def': 31, u'hp': 31, u'spa': 31, u'spd': 31, u'spe': 31},
         u'level': 75,
         u'moves': [u'fusionbolt', u'outrage', u'roost', u'icebeam'],
         u'name': u'Kyurem',
         u'shiny': False,
         u'species': u'Kyurem-Black'},
        """
        statistics.copy_miner_file()
        json_team = statistics.get_json_teams(1)[0]
        self.assertEqual(len(json_team), 6)
        pokemon_dict = json_team[0]
        self.assertEqual(set(['ability', 'evs', 'item', 'ivs', 'level', 'moves', 'name', 'shiny',
                              'species']),
                         set(pokemon_dict.keys()))
        self.assertTrue(set(['atk', 'def', 'hp', 'spa', 'spd', 'spe']) ==
                        set(pokemon_dict['evs'].keys()) ==
                        set(pokemon_dict['ivs'].keys()))

        self.assertEqual(len(pokemon_dict['moves']), 1 if pokemon_dict['name'] == 'Ditto' else 4)

    # # These tests sometimes hang under nosetests due to the subprocess calls # TODO: fix
    # def test_collect_team_stats(self):
    #     counter = statistics.collect_team_stats(100, 4)
    #     self.assertEqual(sum(counter[pokemon]['number'] for pokemon in counter.counter), 100 * 6)
    #     pokemon = counter.counter.popitem()
    #     self.assertEqual(sum(pokemon[1]['item'].values()), pokemon[1]['number'], repr(pokemon))
    #     self.assertEqual(sum(pokemon[1]['ability'].values()), pokemon[1]['number'], repr(pokemon))

    # def test_collect_team_stats_1_proc(self):
    #     counter = statistics.collect_team_stats(100, 1)
    #     self.assertEqual(sum(counter[pokemon]['number'] for pokemon in counter.counter), 100 * 6)
    #     pokemon = counter.counter.popitem()
    #     self.assertEqual(sum(pokemon[1]['item'].values()), pokemon[1]['number'], repr(pokemon))
    #     self.assertEqual(sum(pokemon[1]['ability'].values()), pokemon[1]['number'], repr(pokemon))
