from copy import deepcopy

from AI.baseagent import BaseAgent
from AI.rollout import BattleRoller, sanitize_battle_state
from AI.matrixtree import (BreakpointBattle, BreakNewTurn, BreakMustSwitch, BreakPostFaintSwitch,
                           BreakDoublePostFaintSwitch, new_node)
from _logging import log


class MinimaxAgent(BaseAgent, BattleRoller):
    max_fill_in = 1

    def __init__(self, *args, **kwargs):
        super(MinimaxAgent, self).__init__(*args, **kwargs)

    def my_side(self, battlefield):
        return battlefield.sides[self.my_player]

    def foe_side(self, battlefield):
        return battlefield.sides[not self.my_player]

    def set_my_player(self, player):
        self.my_player = player

    def select_action(self, battlefield, moves, switches, can_mega):
        root_field = deepcopy(battlefield)
        self.fill_in_unrevealed(root_field, max_fill=1)
        sanitize_battle_state(root_field)

        if moves is None: # force-switch
            if self.my_side(battlefield).active_pokemon.is_fainted():
                if self.foe_side(battlefield).active_pokemon.is_fainted():
                    breakpoint = BreakDoublePostFaintSwitch
                    log.i('Requesting switch action for a double-switch-in')
                else:
                    breakpoint = BreakPostFaintSwitch(self.my_player)
                    log.i('Requesting switch action for a single switch-in after a faint')
            else:
                breakpoint = BreakMustSwitch(self.my_player)
                log.i('Requesting switch action after a switch move/item took effect')
        else:
            breakpoint = BreakNewTurn
            log.i('Action requested for turn %d', battlefield.turns)

        battle = BreakpointBattle.from_battlefield(root_field, (), ())
        # pylint: disable=unused-variable
        root_node = new_node(breakpoint.state)(battle, depth=0, breakpoint=breakpoint)

        # TODO: return mixed-strategy selection from solved probability distribution
