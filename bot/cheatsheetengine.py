from battle.battleengine import BattleEngine
from mining.statistics import RandbatsStatistics
from pokedex.enums import FAIL
from pokedex.moves import movedex

from tabulate import tabulate

from misc.multitabulate import multitabulate

if __debug__: from _logging import log

rbstats = RandbatsStatistics.from_pickle()
TABLEFMT = 'psql'

class CheatSheetEngine(BattleEngine):
    """
    Adds some methods to BattleEngine for performing and reporting basic damage calcs for the
    current active pokemon.
    """
    def describe_my_moves(self, my_active, foe):
        """ :type my_active BattlePokemon """
        if __debug__:
            for move in my_active.moveset:
                if move.name not in rbstats.probability[my_active.name]['moves']:
                    log.w('%s not in rbstats for %s: Stale mining data?', move.name, my_active)

        return [(move.name, self.calculate_damage_range(my_active, move, foe))
                for move in my_active.moveset]

    def show_my_moves(self, my_active, foe):
        print tabulate([(move, self.format_damage_range(dmg_range, foe))
                        for move, dmg_range in self.describe_my_moves(my_active, foe)],
                       ('My Moves', 'damage'), tablefmt=TABLEFMT)

    def describe_known_foe_moves(self, my_active, foe):
        if not foe.moveset:
            return []

        return [(move.name, self.calculate_damage_range(foe, move, my_active))
                for move in foe.moveset]

    def describe_possible_foe_moves(self, my_active, foe):
        if __debug__:
            for move in foe.moveset:
                if move.name not in rbstats.probability[foe.name]['moves']:
                    log.w('%s not in rbstats for %s: Stale mining data?', move.name, foe)

        if len(foe.moveset) >= 4:
            return ''

        possible_moves = [movedex[move] for move in rbstats[foe.name]['moves']
                          if movedex[move] not in foe.moveset]
        data = []
        for move in possible_moves[:]:
            prob = rbstats.attr_probability(foe.name, move.name,
                                            [move_.name for move_ in foe.moveset])
            if not prob:
                possible_moves.remove(move)
                continue

            dmg_range = self.calculate_damage_range(foe, move, my_active)
            data.append((move.name, prob, dmg_range))

        return sorted(data, key=lambda x: -x[1])

    def show_foe_moves(self, my_active, foe):
        known_rows = [('Known Moves', 'damage')]
        for name, dmg_range in self.describe_known_foe_moves(my_active, foe):
            pct_range = self.format_damage_range(dmg_range, my_active)
            known_rows.append((name, pct_range))

        possible_rows = [('Other Moves', 'p', 'damage')]
        for name, prob, dmg_range in self.describe_possible_foe_moves(my_active, foe):
            pct_range = self.format_damage_range(dmg_range, my_active)
            possible_rows.append((name, '{:.0%}'.format(prob), pct_range))

        print multitabulate((known_rows, possible_rows))

    def format_damage_range(self, dmg_range, pokemon):
        if dmg_range is None:
            return ''

        if FAIL in dmg_range:
            return 'FAIL'

        minpct, maxpct = [float(dmg) / pokemon.max_hp for dmg in dmg_range]
        pct_range = '{:.0%}-{:.0%} ({}-{})'.format(minpct, maxpct,
                                                   *dmg_range).replace('%', '', 1)
        return pct_range

    def calculate_damage_range(self, foe, move, my_active):
        """ Return a tuple (mindamage, maxdamage) or None """
        if move in (movedex['mirrorcoat'], movedex['counter'], movedex['metalburst']):
            return None
        self.get_critical_hit = lambda crit: False
        self.damage_randomizer = lambda: 85 # min damage
        mindamage = self.calculate_damage(foe, move, my_active)
        if mindamage is None:
            return None

        self.damage_randomizer = lambda: 100 # max damage
        maxdamage = self.calculate_damage(foe, move, my_active)

        self.get_critical_hit = BattleEngine.get_critical_hit
        self.damage_randomizer = BattleEngine.damage_randomizer

        return mindamage, maxdamage
