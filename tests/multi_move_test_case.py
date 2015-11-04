"""
Most tests of the core battling mechanics, including moves, items, abilities, effects, and the
complex interactions between them should use the MultiMoveTestCase and associated helper functions
and classes.
"""
from collections import defaultdict, deque
from unittest import TestCase

from battle.battleengine import BattleEngine
from battle.battlepokemon import BattlePokemon
from battle.decisionmakers import AutoDecisionMaker
from battle.events import MoveEvent, SwitchEvent
from mining import create_pokedex
from pokedex.abilities import abilitydex
from pokedex.items import itemdex
from pokedex.enums import Status, ABILITY, ITEM
from pokedex.moves import movedex

pokedex = create_pokedex()


class AnyMovePokemon(BattlePokemon):
    """
    A convenience specialization of BattlePokemon that can use any move without having it in its
    moveset. Tests for mechanics related to disablement or locking of moves, or PP, should supply a
    moveset to the constructor and choose only moves from that moveset.
    """
    def __init__(self, *args, **kwargs):
        super(AnyMovePokemon, self).__init__(*args, **kwargs)
        self.pp = defaultdict(lambda: 100, **{move: move.max_pp for move in self.moveset})

class LoggingFaintQueue(list):
    """
    For convenience, this engine.faint_queue stores an ordered history of all pokemon that fainted
    during the battle (instead of losing this information at the end of each turn).
    """
    def __init__(self, *args, **kwargs):
        super(LoggingFaintQueue, self).__init__(*args, **kwargs)
        self.log = []
    def insert(self, pos, obj, *args, **kwargs):
        super(LoggingFaintQueue, self).insert(pos, obj, *args, **kwargs)
        self.log.append(obj)

class TestingEngine(BattleEngine):
    """
    Overrides get_move_decisions to allow the test to inject decisions for each player between
    turns.
    """
    def __init__(self, *args, **kwargs):
        super(TestingEngine, self).__init__(*args, **kwargs)
        self.testing_decisions = []
        self.faint_queue = LoggingFaintQueue()

    def get_move_decisions(self):
        decisions = []
        for decision_type, pokemon, action in self.testing_decisions:
            spe = self.effective_spe(pokemon)

            if decision_type == 'move':
                move = action
                priority = self.modify_priority(pokemon, move)
                decisions.append(MoveEvent(pokemon, spe, priority, move))
            elif decision_type == 'switch':
                incoming = action
                decisions.append(SwitchEvent(pokemon, spe, incoming))

        return decisions

    def init_turn(self):
        super(TestingEngine, self).init_turn()
        self.testing_decisions = []

class TestingDecisionMaker(AutoDecisionMaker):
    """
    Return None from make_move_decision so that no events are added to the queue during
    engine.start_turn. Tests should add MoveEvents/SwitchEvents to the event_queue manually or
    via choose_move or choose_switch.
    """
    def make_move_decision(self, *args):
        pass

class MultiMoveTestCase(TestCase):
    """
    Tests may call reset_leads, with two pokemon names, to change the default leads. Additional
    (benched) pokemon are added with add_pokemon(). The test may simulate the battle by populating
    the event_queue then calling run_turn, or by calling individual methods like use_move. Any
    forced switch decisions will be handled automatically unless a custom DecisionMaker is
    injected.
    """
    def setUp(self):
        """ By default, start with vaporeon vs. flareon with no moveset """
        self.reset_leads('vaporeon', 'leafeon', tearDown=False)

    def reset_leads(self, p0_name='vaporeon', p1_name='leafeon',
                    p0_moves=(), p1_moves=(),
                    p0_item=None, p1_item=None,
                    p0_ability='_none_', p1_ability='_none_',
                    p0_level=100, p1_level=100,
                    p0_gender=None, p1_gender=None,
                    tearDown=True):
        """
        `name` is the species name of a pokemon in the pokedex.
        `moves` is a list of up to four moves
        `item` is the name of an item in the itemdex.
        `ability` is the name of an ability in the abilitydex.
        `level` is an int in [1..100]
        `gender` is in [None, 'M', 'F']
        """
        if tearDown:
            self.tearDown()
        self._names = [p0_name, p1_name]
        p0_moves = [movedex[move] if isinstance(move, str) else move for move in p0_moves]
        p1_moves = [movedex[move] if isinstance(move, str) else move for move in p1_moves]

        setattr(self, p0_name, AnyMovePokemon(pokedex[p0_name], side=None,
                                              ability=abilitydex[p0_ability],
                                              evs=(0,)*6, moveset=p0_moves,
                                              item=itemdex.get(p0_item),
                                              level=p0_level, gender=p0_gender))
        setattr(self, p1_name, AnyMovePokemon(pokedex[p1_name], side=None,
                                              ability=abilitydex[p1_ability],
                                              evs=(0,)*6, moveset=p1_moves,
                                              item=itemdex.get(p1_item),
                                              level=p1_level, gender=p1_gender))
        self.engine = TestingEngine([getattr(self, p0_name)],
                                    [getattr(self, p1_name)],
                                    dm0=TestingDecisionMaker(0),
                                    dm1=TestingDecisionMaker(1))

        # for determinism:
        self.engine.get_critical_hit = lambda crit: False # no crits
        self.engine.damage_randomizer = lambda: 100 # max damage

        self.engine.init_battle()

    def reset_items(self, p0_item=None, p1_item=None):
        self.reset_leads(p0_item=p0_item, p1_item=p1_item)

    def add_pokemon(self, name, side, ability='_none_', item=None, moves=()):
        """
        `side` is 0 or 1.
        Other params are like self.reset_leads
        """
        moves = [movedex[move] if isinstance(move, str) else move for move in moves]
        battle_side = self.engine.battlefield.sides[side]
        pokemon = AnyMovePokemon(pokedex[name], side=battle_side, evs=(0,)*6,
                                 moveset=moves, ability=abilitydex[ability],
                                 item=itemdex.get(item))
        setattr(self, name, pokemon)
        battle_side.team.append(pokemon)
        self._names.append(name)

    def choose_move(self, pokemon, move):
        """
        `pokemon` will use `move` next turn.
        """
        self.engine.testing_decisions.append(('move', pokemon, move))

    def choose_switch(self, outgoing, incoming):
        """
        `outgoing` will switch out for `incoming` next turn.
        """
        self.engine.testing_decisions.append(('switch', outgoing, incoming))

    def run_turn(self):
        self.engine.run_turn()

    def tearDown(self):
        for name in self._names:
            delattr(self, name)
        del self.engine

    def assertDamageTaken(self, pokemon, damage):
        self.assertEqual(pokemon.hp, pokemon.max_hp - damage)

    def assertStatus(self, pokemon, status):
        self.assertEqual(pokemon.status, status)
        if status not in (None, Status.FNT):
            self.assertTrue(pokemon.has_effect(status))

    def assertFainted(self, pokemon):
        self.assertEqual(pokemon.status, Status.FNT)
        self.assertLessEqual(pokemon.hp, 0)
        self.assertTrue(pokemon.is_fainted())

    def assertBoosts(self, pokemon, boosts):
        self.assertDictContainsSubset(boosts, pokemon.boosts)

    def assertMoveChoices(self, pokemon, moves):
        moves = set([movedex[move] if isinstance(move, str) else move for move in moves])
        self.assertSetEqual(set(self.engine.get_move_choices(pokemon)), moves)

    def assertSwitchChoices(self, pokemon, choices):
        self.assertSetEqual(set(self.engine.get_switch_choices(pokemon.side, pokemon)), choices)

    def assertAbility(self, pokemon, ability):
        ability = abilitydex[ability]
        self.assertEqual(pokemon.ability, ability)
        self.assertEqual(pokemon.get_effect(ABILITY).name, ability.name)

    def assertPpUsed(self, pokemon, move, pp):
        move = movedex[move]
        self.assertEqual(pokemon.pp[move], move.max_pp - pp)

    def assertItem(self, pokemon, item):
        self.assertEqual(pokemon.item, itemdex.get(item))
        if item is None:
            self.assertFalse(pokemon.has_effect(ITEM))
        elif pokemon.is_active:
            held = pokemon.get_effect(ITEM)
            self.assertIsNotNone(held)
            self.assertEqual(held.name, item)

    def assertActive(self, pokemon):
        self.assertTrue(pokemon.is_active)
        for teammate in pokemon.side.team:
            if teammate is not pokemon:
                self.assertFalse(teammate.is_active)

        self.assertIs(pokemon.side.active_pokemon, pokemon)

    @property
    def battlefield(self):
        return self.engine.battlefield

    @property
    def faint_log(self):
        return self.engine.faint_queue.log

class MultiMoveTestCaseWithoutSetup(MultiMoveTestCase):
    """
    Note: overrides MultiMoveTestCase's default setUp, so self.reset_leads must be called in
    each test.
    """
    def __init__(self, *args, **kwargs):
        self._names = []
        self.engine = None
        super(MultiMoveTestCaseWithoutSetup, self).__init__(*args, **kwargs)

    def setUp(self):
        pass
