from battle.enums import Decision
from battle.events import MoveEvent, SwitchEvent, MegaEvoEvent
from battle.moves import movedex

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

    def make_events(self, user, side, battle):
        events = []
        move = movedex[self.move_name]
        events.append(MoveEvent(user, battle.effective_spe(user),
                                battle.modify_priority(user, move), move))
        if user.can_mega_evolve:
            events.append(MegaEvoEvent(user, battle.effective_spe(user)))

        return events

    def __repr__(self):
        return '<move: %s>' % self.move_name

class SwitchAction(Action):
    action_type = Decision.SWITCH

    def __init__(self, incoming_name, index):
        self.incoming_name = incoming_name
        self.index = index

    @property
    def command_string(self):
        return '/choose switch %d' % self.index

    def make_events(self, active, side, battle, check_spe=True):
        incoming = next(teammate for teammate in side.team if teammate.name == self.incoming_name)
        assert not incoming.is_fainted()

        event = SwitchEvent(active, battle.effective_spe(active) if check_spe else 0, incoming)
        return [event]

    def __repr__(self):
        return '<switch: %s>' % self.incoming_name
