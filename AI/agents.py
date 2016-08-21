import random
from AI.enums import Strategy


def Agent(strategy, *args, **kwargs): # factory function
    if strategy not in Strategy.values:
        raise TypeError('"%s" is not a valid Strategy' % strategy)

    return {
        Strategy.RANDOM: RandomAgent,
        Strategy.MATRIX: MatrixAgent,
    }[strategy](*args, **kwargs)


class BaseAgent(object):
    pass


class RandomAgent(BaseAgent):
    def __init__(self, switch_freq=0.1):
        self.switch_freq = switch_freq

    def __repr__(self):
        return '<RandomAgent:switch_freq=%s>' % self.switch_freq

    def select_action(self, _, moves, switches, can_mega):
        if not moves or (switches and random.random() < self.switch_freq):
            return random.choice(switches), False

        mega = can_mega and random.choice((True, False))
        return random.choice(moves), mega


class MatrixAgent(BaseAgent):
    pass
