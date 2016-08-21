from battle.battleengine import Battle
from showdowndata.miner import RandbatsStatistics, rbstats_key
from pokedex import effects
from pokedex.enums import FAIL, Volatile, Type
from pokedex.abilities import abilitydex
from pokedex.moves import movedex

from tabulate import tabulate

from misc.multitabulate import multitabulate

from _logging import log, no_console_log

rbstats = RandbatsStatistics.from_pickle()
TABLEFMT = 'psql'

class BattleCalculator(Battle):
    """
    Adds some methods to Battle for performing and reporting basic damage calcs for the
    current active pokemon.
    """
    def describe_my_moves(self, my_active, foe):
        """ :type my_active BattlePokemon """
        if not my_active.is_transformed:
            active = rbstats_key(my_active)
            for move in my_active.moves:
                if move.name not in rbstats.probability[active]['moves']:
                    log.w('%s not in rbstats for %s: Stale showdown data?', move.name, my_active)

        return [(move.name, self.calculate_damage_range(my_active, move, foe))
                for move in my_active.moves]

    def show_my_moves(self, my_active, foe):
        log.i('\n' + (tabulate([(move, self.format_damage_range(dmg_range, foe))
                                for move, dmg_range in self.describe_my_moves(my_active, foe)],
                               ('My Moves', 'damage'), tablefmt=TABLEFMT)))

    def describe_known_foe_moves(self, my_active, foe):
        if not foe.moves:
            return []

        return [(move.name, self.calculate_damage_range(foe, move, my_active))
                for move in foe.moves]

    def describe_possible_foe_moves(self, my_active, foe):
        if len(foe.moves) >= 4 or foe.base_species == 'ditto':
            return ''

        foe_index = rbstats_key(foe)

        for move in foe.moves:
            if (move.name not in rbstats.probability[foe_index]['moves'] and
                move.type != Type.NOTYPE):
                log.w('%s not in rbstats for %s: Stale showdown data?', move.name, foe)

        possible_moves = [movedex[move] for move in rbstats[foe_index]['moves']
                          if movedex[move] not in foe.moves]
        data = []
        known_attrs = [move_.name for move_ in foe.moves if move_.type != Type.NOTYPE]
        if not rbstats.possible_sets(foe_index, known_attrs):
            log.w("%s's move probabilities cannot be calculated: unexpected attribute in %s",
                  foe_index, known_attrs)
            calculate_prob = False
        else:
            calculate_prob = True

        for move in possible_moves[:]:
            if calculate_prob:
                prob = rbstats.attr_probability(foe_index, move.name, known_attrs)
                if not prob:
                    possible_moves.remove(move)
                    continue
            else:
                prob = 0.5

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

        log.i('\n' + multitabulate((known_rows, possible_rows)))

    def format_damage_range(self, dmg_range, pokemon):
        if dmg_range is None:
            return ''

        if FAIL in dmg_range:
            return 'FAIL'

        minpct, maxpct = [float(dmg) / pokemon.max_hp for dmg in dmg_range]
        pct_range = '{:.0%}-{:.0%} ({}-{})'.format(minpct, maxpct,
                                                   *dmg_range).replace('%', '', 1)
        return pct_range

    @no_console_log
    def calculate_damage_range(self, attacker, move, defender):
        """ Return a tuple (mindamage, maxdamage) or None """
        if move in (movedex['mirrorcoat'], movedex['counter'], movedex['metalburst']):
            return None

        if attacker.ability == abilitydex['sheerforce'] and move.secondary_effects:
            attacker.set_effect(effects.SheerForceVolatile())
        self.get_critical_hit = lambda crit: False

        self.damage_randomizer = lambda: 85 # min damage
        mindamage = self.calculate_damage(attacker, move, defender)
        self.damage_randomizer = lambda: 100 # max damage
        maxdamage = self.calculate_damage(attacker, move, defender)

        self.get_critical_hit = Battle.get_critical_hit
        self.damage_randomizer = Battle.damage_randomizer
        if attacker.has_effect(Volatile.SHEERFORCE):
            attacker.remove_effect(Volatile.SHEERFORCE)

        if mindamage is None:
            return None
        return mindamage, maxdamage

    @no_console_log
    def calculate_expected_damage(self, attacker, move, defender, crit=False):
        if move in (movedex['mirrorcoat'], movedex['counter'], movedex['metalburst']):
            return (defender.max_hp - defender.hp) * 2 # upper bound

        if attacker.ability == abilitydex['sheerforce'] and move.secondary_effects:
            attacker.set_effect(effects.SheerForceVolatile())
        self.get_critical_hit = lambda _: crit

        self.damage_randomizer = lambda: 93 # average damage
        damage = self.calculate_damage(attacker, move, defender)

        self.get_critical_hit = Battle.get_critical_hit
        self.damage_randomizer = Battle.damage_randomizer
        attacker.remove_effect(Volatile.SHEERFORCE)

        return damage
