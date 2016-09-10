from AI.enums import Strategy
from AI.randomagent import RandomAgent
from AI.minimaxagent import MinimaxAgent


def Agent(strategy, *args, **kwargs):
    """ Factory function producing an agent according to the given Strategy. """
    if strategy not in Strategy.values:
        raise TypeError('"%s" is not a valid Strategy' % strategy)

    return {
        Strategy.RANDOM: RandomAgent,
        Strategy.MATRIX: MinimaxAgent,
    }[strategy](*args, **kwargs)
