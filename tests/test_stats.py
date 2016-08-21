from unittest import TestCase

from battle.stats import PokemonStats, Boosts

class TestStats(TestCase):
    def test_PokemonStats(self):
        stats = PokemonStats(100, 90, 80, 70, 110, 140)
        assert stats['max_hp'] == 100
        assert stats['atk'] == 90
        assert stats['def'] == 80
        assert stats['spa'] == 70
        assert stats['spd'] == 110
        assert stats['spe'] == 140
        with self.assertRaises(KeyError):
            stats['spd'] = 111

    def test_Boosts(self):
        boosts = Boosts(1, 2, 3, 4, 5, 6, -5)
        assert boosts['atk'] == 1
        assert boosts['def'] == 2
        assert boosts['spa'] == 3
        assert boosts['spd'] == 4
        assert boosts['spe'] == 5
        assert boosts['acc'] == 6
        assert boosts['evn'] == -5

        kw_boosts = Boosts(atk=1, spe=2)
        assert kw_boosts['atk'] == 1
        assert kw_boosts['spe'] == 2
        assert kw_boosts['spa'] == 0

        other = Boosts(atk=-1, spd=1, evn=-3, spe=2, acc=2)
        boosts.update(other)
        assert boosts['atk'] == 0
        assert boosts['spd'] == 5
        assert boosts['evn'] == -6
        assert boosts['spe'] == 6
        assert boosts['acc'] == 6
