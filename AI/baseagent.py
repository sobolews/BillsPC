from abc import ABCMeta, abstractmethod

class BaseAgent(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.my_player = None

    def set_my_player(self, player):
        self.my_player = player

    @abstractmethod
    def select_action(self, battlefield, moves, switches, can_mega):
        pass
