from battle.enums import Decision

class Action(object):
    @property
    def command_string(self):
        raise NotImplementedError

class MoveAction(Action):
    action_type = Decision.MOVE

    def __init__(self, move, index):
        self.move_name = move
        self.index = index

    @property
    def command_string(self):
        return '/choose move %d' % self.index

    def __repr__(self):
        return '(move: %s)' % self.move_name

class SwitchAction(Action):
    action_type = Decision.SWITCH

    def __init__(self, pokemon, index):
        self.pokemon_name = pokemon
        self.index = index

    @property
    def command_string(self):
        return '/choose switch %d' % self.index

    def __repr__(self):
        return '(switch: %s)' % self.pokemon_name
