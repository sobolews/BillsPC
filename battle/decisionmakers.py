import random

class BaseDecisionMaker(object):
    def __init__(self, side):
        self.index = side

    def make_move_decision(self, moves, switches, battlefield):
        raise NotImplementedError

    def make_switch_decision(self, choices, battlefield):
        raise NotImplementedError

    def make_mega_evo_decision(self, battlefield):
        raise NotImplementedError

class RandomDecisionMaker(BaseDecisionMaker):
    def make_move_decision(self, moves, switches, battlefield):
        return random.choice(moves), True

    def make_switch_decision(self, choices, battlefield):
        return random.choice(choices)

    def make_mega_evo_decision(self, battlefield):
        return random.choice((True, False))

class RandomDecisionMakerWithSwitches(RandomDecisionMaker):
    def make_move_decision(self, moves, switches, battlefield):
        if switches and random.randrange(10) == 0:
            return random.choice(switches), False
        return random.choice(moves), True

class AutoDecisionMaker(BaseDecisionMaker):
    """ Always return the first choice """
    def make_move_decision(self, moves, switches, battlefield):
        return moves[0], True

    def make_switch_decision(self, choices, battlefield):
        return choices[0]

    def make_mega_evo_decision(self, battlefield):
        return True
