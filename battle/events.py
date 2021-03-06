"""
The event classes in this module are used by the Battle to organize discrete parts of a
turn. (Note: a turn has begun once Battle.init_turn has been called)

Generally, a turn proceeds in this order:
- Hard switches
  - pursuit may run here
- Post-switch-ins
- Mega Evolutions
- Moves
  - any Switches (uturn, roar, etc.) caused by moves
  - post-switch-ins
- Residuals (the "between turns" effects such as poison or speedboost)
- if any pokemon are fainted, then InstaSwitch+PostSwitch until the side has an active pokemon
"""
from random import random
from bisect import insort
from functools import total_ordering

from battle.enums import Decision

if __debug__: from _logging import log

@total_ordering
class BaseEvent(object):
    priority = 0
    pokemon = None
    move = None
    type = None

    def __eq__(self, other):
        return self.priority == other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def run_event(self, battle, queue):
        raise NotImplementedError

class MoveEvent(BaseEvent):
    type = Decision.MOVE

    def __init__(self, pokemon, spe, priority, move):
        self.pokemon = pokemon
        self.priority = (100 + priority, spe, random())
        self.move = move

    def run_event(self, battle, queue):
        if self.pokemon.is_fainted() or not self.pokemon.is_active:
            if __debug__: log.i('Skipping move because %s is either fainted or inactive' %
                                self.pokemon)
            return
        battle.run_move(self.pokemon, self.move, battle.get_foe(self.pokemon))

    def __repr__(self):
        return 'MoveEvent(pokemon=%s, move=%s)' % (self.pokemon, self.move)

class SwitchEvent(BaseEvent):
    type = Decision.SWITCH
    _priority = 300

    def __init__(self, pokemon, spe, incoming):
        self.pokemon = pokemon
        self.priority = (self._priority, spe, random())
        self.incoming = incoming

    def run_event(self, battle, queue):
        battle.run_switch(self.pokemon, self.incoming)
        insort(queue, PostSwitchInEvent(self.incoming, battle.effective_spe(self.incoming)))

    def __repr__(self):
        return 'SwitchEvent(pokemon=%s, incoming=%s)' % (self.pokemon, self.incoming)

class InstaSwitchEvent(SwitchEvent):
    _priority = 400

class PostSwitchInEvent(BaseEvent):
    def __init__(self, pokemon, spe):
        self.pokemon = pokemon
        self.priority = (350, spe, random())

    def run_event(self, battle, queue):
        battle.post_switch_in(self.pokemon)

    def __repr__(self):
        return 'PostSwitchInEvent(pokemon=%s)' % self.pokemon

class MegaEvoEvent(BaseEvent):
    type = Decision.MEGAEVO

    def __init__(self, pokemon, spe):
        self.pokemon = pokemon
        self.priority = (200, spe, random())

    def run_event(self, battle, queue):
        self.pokemon.mega_evolve(battle)

    def __repr__(self):
        return 'MegaEvoEvent(pokemon=%s)' % self.pokemon

class ResidualEvent(BaseEvent):
    def __init__(self):
        self.priority = (-1, 0, 0)

    def run_event(self, battle, queue):
        battle.run_residual()

    def __repr__(self):
        return 'ResidualEvent()'
