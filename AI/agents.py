import random
from AI.enums import Policy


def Agent(policy, *args, **kwargs): # factory function
    if policy not in Policy.values:
        raise TypeError('"%s" is not a valid policy' % policy)

    return {
        Policy.RANDOM: RandomAgent,
        Policy.MATRIX: MatrixAgent,
    }[policy](*args, **kwargs)


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
