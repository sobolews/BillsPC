from abc import ABCMeta, abstractmethod

class BaseAgent(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def select_action(self, battlefield, moves, switches, can_mega):
        pass
