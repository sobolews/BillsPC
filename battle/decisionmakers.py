from pokedex.enums import Decision
import random

class BaseDecisionMaker(object):
    def __init__(self, side):
        self.index = side

    def make_move_decision(self, choices, battlefield):
        raise NotImplementedError

    def make_switch_decision(self, choices, battlefield):
        raise NotImplementedError

    def make_mega_evo_decision(self, battlefield):
        raise NotImplementedError

class RandomDecisionMaker(BaseDecisionMaker):
    def make_move_decision(self, choices, battlefield):
        return random.choice([choice for choice in choices if choice.type is Decision.MOVE])

    def make_switch_decision(self, choices, battlefield):
        return random.choice(choices)

    def make_mega_evo_decision(self, battlefield):
        return random.choice((True, False))

class RandomDecisionMakerWithSwitches(RandomDecisionMaker):
    def make_move_decision(self, choices, battlefield):
        switches = [choice for choice in choices if choice.type is Decision.SWITCH]
        if switches and random.randrange(10) == 0:
            return random.choice(switches)
        return random.choice([choice for choice in choices if choice.type is Decision.MOVE])

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

    def make_mega_evo_decision(self, battlefield):
        return True

class AutoDecisionMaker(BaseDecisionMaker):
    """ Always return the first choice """
    def make_move_decision(self, choices, battlefield):
        return choices[0]

    def make_switch_decision(self, choices, battlefield):
        return choices[0]

    def make_mega_evo_decision(self, battlefield):
        return True
