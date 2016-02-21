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
        switches, moves = [], []
        for choice in choices:
            (switches if choice.type is Decision.SWITCH else moves).append(choice)

        if switches and random.randrange(10) == 0:
            return random.choice(switches)
        return random.choice(moves)


class AutoDecisionMaker(BaseDecisionMaker):
    """ Always return the first choice """
    def make_move_decision(self, choices, battlefield):
        return choices[0]

    def make_switch_decision(self, choices, battlefield):
        return choices[0]

    def make_mega_evo_decision(self, battlefield):
        return True
