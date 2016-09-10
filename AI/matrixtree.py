from bisect import insort
from copy import deepcopy

from AI.actions import MoveAction, SwitchAction
from AI.enums import BattleState
from battle.battleengine import Battle
from bot.foeside import UNREVEALED


class Breakpoint(Exception):
    pass

class BreakNewTurn(Breakpoint):
    state = BattleState.NEW_TURN

class BreakMustSwitch(Breakpoint):
    state = BattleState.MUST_SWITCH

    def __init__(self, side_index):
        self.side_index = side_index

class BreakPostFaintSwitch(Breakpoint):
    state = BattleState.POST_FAINT_SWITCH

    def __init__(self, side_index):
        self.side_index = side_index

class BreakDoublePostFaintSwitch(Breakpoint):
    state = BattleState.DOUBLE_POST_FAINT_SWITCH

class BreakChanceAccuracy(Breakpoint):
    state = BattleState.CHANCE_ACCURACY

class BreakChanceSecondary(Breakpoint):
    state = BattleState.CHANCE_SECONDARY


class BreakpointBattle(Battle):
    def get_instaswitches(self, sides):
        assert any(sides), sides
        if sides[0] is None:
            raise BreakPostFaintSwitch(1)
        elif sides[1] is None:
            raise BreakPostFaintSwitch(0)
        else:
            raise BreakDoublePostFaintSwitch

    def get_move_decisions(self):
        raise BreakNewTurn

    def run_must_switch(self, side):
        raise BreakMustSwitch(side.index)

    @staticmethod
    def get_critical_hit(crit_ratio):
        return crit_ratio >= 3

    @staticmethod
    def damage_randomizer():
        return 100 - 7 # average damage


class MatrixCell(object):
    """
    Representation of potential actions leading to a new state. Once expanded via a call to
    BaseMatrixNode.expand_cell, this holds the
    """
    def __init__(self, row_action, col_action, node, win):
        self.row_action = row_action
        self.col_action = col_action
        self.node = node
        self.win = win

    def __repr__(self):
        return 'Cell(row=%s, col=%s, %s)' % (self.row_action, self.col_action,
            ('node=%s' % self.node) if not self.win else ('win=%s' % self.win))


class BaseMatrixNode(object):
    """
    Representation of a battle state with its associated possible actions as a one- or
    two-dimensional list of MatrixCells.
    """
    state = None
    matrix = None
    value = None
    simultaneous = None # True for nodes that require simultaneous decisions from both sides.

    def __init__(self, battle, depth, breakpoint=None):
        self.depth = depth
        self.battle = battle

        self.populate_matrix(battle, depth, breakpoint)

    def __repr__(self):
        return '<%s:depth=%s%s>' % (self.__class__.__name__, self.depth,
                                    '' if self.value is None else ', value=%s' % self.value)

    def populate_matrix(self, battle, depth, breakpoint):
        raise NotImplementedError

    def evaluate(self, max_depth):
        if self.depth == max_depth:
            return self.approximate()

        for row in self.matrix:
            for cell in row:
                self.expand_cell(cell)

        self.calculate_value()

    def expand_cell(self, cell):
        child_battle = deepcopy(self.battle)
        try:
            self.run_actions(child_battle, row_action=cell.row_action, col_action=cell.col_action)
        except Breakpoint as bp:
            cell.node = new_node(bp.state)(child_battle, self.depth+1, bp)
        else:
            cell.win = child_battle.win

    def run_actions(self, child_battle, row_action, col_action):
        """
        Run the actions set in child on child_battle until a breakpoint is encountered.
        Overridden by each node type to resume the battle execution at the correct place.
        """

    def calculate_value(self):
        """
        Called once all child nodes have been evaluated. Sets this node's value based on the value
        of its children.
        """
        raise NotImplementedError

    def approximate(self):
        """
        Called for a node at the maximum depth. Sets this node's value based on the state of the
        battlefield.
        """
        assert self.__class__.__name__ == 'MatrixNodeNewTurn' # TODO: something better
        # TODO: approximate


class MatrixNodeNewTurn(BaseMatrixNode):
    simultaneous = True

    def populate_matrix(self, battle, depth, breakpoint):
        sides = battle.battlefield.sides
        row_active = sides[0].active_pokemon
        col_active = sides[1].active_pokemon
        row_actions = []
        col_actions = []

        for active, actions in ((row_active, row_actions), (col_active, col_actions)):
            # TODO: if depth==0, pass index to action
            for move in active.get_move_choices():
                actions.append(MoveAction(move.name, None))
            for teammate in active.get_switch_choices():
                if teammate.name != UNREVEALED:
                    actions.append(SwitchAction(teammate.name, None))

        self.rows = len(row_actions)
        self.cols = len(col_actions)

        # create a matrix representing the product of each players' possible actions
        self.matrix = [[MatrixCell(p0, p1, node=None, win=None)
                        for p1 in col_actions] for p0 in row_actions]

    def run_actions(self, battle, row_action, col_action):
        events = []
        p0_side = battle.battlefield.sides[0]
        p0_pokemon = p0_side.active_pokemon
        events.extend(row_action.make_events(p0_pokemon, p0_side, battle))
        p1_side = battle.battlefield.sides[1]
        p1_pokemon = p1_side.active_pokemon
        events.extend(col_action.make_events(p1_pokemon, p1_side, battle))

        battle.queue_events_for_turn(events)
        battle.run_queued_events()
        battle.run_battle()

    def calculate_value(self):
        pass # TODO


def make_switch_event(battle, action, index, check_spe):
    side = battle.battlefield.sides[index]
    [event] = action.make_events(side.active_pokemon, side, battle, check_spe)
    return event


class MatrixNodeMustSwitch(BaseMatrixNode):
    """
    Represents a decision node in which a side must perform a mid-turn switch.
    This would be caused by moves like uturn or partingshot, or other effects like redcard.
    """
    side_index = None
    simultaneous = False

    def populate_matrix(self, battle, depth, breakpoint):
        self.side_index = index = breakpoint.side_index

        side = battle.battlefield.sides[index]
        actions = (SwitchAction(teammate.name, None)
                   for teammate in side.get_switch_choices(forced=True)
                   if teammate.name != UNREVEALED)

        if index == 0:
            self.matrix = [MatrixCell(p0, None, None, None) for p0 in actions],
        else:
            self.matrix = [MatrixCell(None, p1, None, None) for p1 in actions],

    def run_actions(self, battle, row_action, col_action):
        assert [row_action, col_action].count(None) == 1
        assert row_action if self.side_index == 0 else col_action

        action = row_action or col_action
        event = make_switch_event(battle, action, self.side_index, check_spe=False)

        insort(battle.event_queue, event)
        battle.resolve_faint_queue()
        battle.run_queued_events()
        battle.run_battle()

    def calculate_value(self):
        pass # TODO


class MatrixNodePostFaintSwitch(MatrixNodeMustSwitch): # use the same populate_matrix
    """
    Represents a decision node in which one side must switch in a new pokemon to replace a fainted
    one before the next turn starts.
    """
    # TODO: don't consider post-faint switchins that would be KOd by hazards

    def run_actions(self, battle, row_action, col_action):
        assert [row_action, col_action].count(None) == 1
        assert row_action if self.side_index == 0 else col_action

        action = row_action or col_action
        switch_queue = [make_switch_event(battle, action, self.side_index, check_spe=False)]

        battle.resolve_switch_queue(switch_queue)
        battle.resolve_faint_queue()
        battle.run_turn()


class MatrixNodeDoublePostFaintSwitch(BaseMatrixNode):
    simultaneous = True

    def populate_matrix(self, battle, depth, breakpoint):
        row_side = battle.battlefield.sides[0]
        col_side = battle.battlefield.sides[1]
        assert row_side.active_pokemon is None
        assert col_side.active_pokemon is None
        row_actions = []
        col_actions = []

        for side, actions in ((row_side, row_actions), (col_side, col_actions)):
            # TODO: if depth==0, pass index to action
            for teammate in side.get_switch_choices(forced=True):
                if teammate.name != UNREVEALED:
                    actions.append(SwitchAction(teammate.name, None))

        assert row_actions
        assert col_actions
        self.rows = len(row_actions)
        self.cols = len(col_actions)

        self.matrix = [[MatrixCell(p0, p1, node=None, win=None)
                        for p1 in col_actions] for p0 in row_actions]

    def run_actions(self, battle, row_action, col_action):
        assert row_action and col_action

        switch_queue = sorted((
            make_switch_event(battle, row_action, 0, check_spe=False),
            make_switch_event(battle, col_action, 1, check_spe=False)
        ))

        battle.resolve_switch_queue(switch_queue)
        battle.resolve_faint_queue()
        battle.run_turn()

    def calculate_value(self):
        pass # TODO


def new_node(state):
    return {
        BattleState.NEW_TURN: MatrixNodeNewTurn,
        BattleState.MUST_SWITCH: MatrixNodeMustSwitch,
        BattleState.POST_FAINT_SWITCH: MatrixNodePostFaintSwitch,
        BattleState.DOUBLE_POST_FAINT_SWITCH: MatrixNodeDoublePostFaintSwitch,
        # TODO:
        # BattleState.CHANCE_ACCURACY: MatrixNodeChanceAccuracy,
        # BattleState.CHANCE_SECONDARY: MatrixNodeChanceSecondary,
    }[state]
