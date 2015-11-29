from pokedex.enums import Decision
import random

class BaseDecisionMaker(object):
    def __init__(self, side):
        self.index = side

    def make_move_decision(self, choices, battlefield):
        raise NotImplementedError

    def make_switch_decision(self, choices, battlefield):
        raise NotImplementedError

class RandomDecisionMaker(BaseDecisionMaker):
    def make_move_decision(self, choices, battlefield):
        return random.choice([choice for choice in choices if choice.type is Decision.MOVE])

    def make_switch_decision(self, choices, battlefield):
        return random.choice(choices)

class ScriptedDecisionMaker(BaseDecisionMaker):
    def __init__(self, side, decisions):
        BaseDecisionMaker.__init__(self, side)
        self.decisions = decisions
        self._counter = 0

    def make_move_decision(self, choices, battlefield):
        decision = self.decisions[self._counter]
        self._counter += 1
        return decision

    make_switch_decision = make_move_decision

class AutoDecisionMaker(BaseDecisionMaker):
    """ Always return the first choice """
    def make_move_decision(self, choices, battlefield):
        return choices[0]

    def make_switch_decision(self, choices, battlefield):
        return choices[0]
