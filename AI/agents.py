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
    pass


class MatrixAgent(BaseAgent):
    pass
