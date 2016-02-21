"""
The event classes in this module are used by the BattleEngine to organize discrete parts of a
turn. (Note: a turn has begun once BattleEngine.init_turn has been called)

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

from pokedex.enums import Decision

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

    def run_event(self, engine, queue):
        raise NotImplementedError

class MoveEvent(BaseEvent):
    type = Decision.MOVE

    def __init__(self, pokemon, spe, priority_modifier, move):
        self.pokemon = pokemon
        self.priority = (100 + move.priority + priority_modifier, spe, random())
        self.move = move

    def run_event(self, engine, queue):
        if self.pokemon.is_fainted() or not self.pokemon.is_active:
            if __debug__: log.i('Skipping move because %s is either fainted or inactive' %
                                self.pokemon)
            return
        engine.run_move(self.pokemon, self.move, engine.get_foe(self.pokemon))

    def __repr__(self):
        return 'MoveEvent(pokemon=%s, move=%s)' % (self.pokemon, self.move)

class SwitchEvent(BaseEvent):
    type = Decision.SWITCH
    _priority = 300

    def __init__(self, pokemon, spe, incoming):
        self.pokemon = pokemon
        self.priority = (self._priority, spe, random())
        self.incoming = incoming

    def run_event(self, engine, queue):
        engine.run_switch(self.pokemon, self.incoming)
        insort(queue, PostSwitchInEvent(self.incoming, engine.effective_spe(self.incoming)))

    def __repr__(self):
        return 'SwitchEvent(pokemon=%s, incoming=%s)' % (self.pokemon, self.incoming)

class InstaSwitchEvent(SwitchEvent):
    _priority = 400

class PostSwitchInEvent(BaseEvent):
    type = Decision.POSTSWITCH

    def __init__(self, pokemon, spe):
        self.pokemon = pokemon
        self.priority = (350, spe, random())

    def run_event(self, engine, queue):
        engine.post_switch_in(self.pokemon)

    def __repr__(self):
        return 'PostSwitchInEvent(pokemon=%s)' % self.pokemon

class MegaEvoEvent(BaseEvent):
    type = Decision.MEGAEVO

    def __init__(self, pokemon, spe):
        self.pokemon = pokemon
        self.priority = (200, spe, random())

    def run_event(self, engine, queue):
        self.pokemon.mega_evolve(engine)

    def __repr__(self):
        return 'MegaEvoEvent(pokemon=%s)' % self.pokemon

class ResidualEvent(BaseEvent):
    type = Decision.RESIDUAL

    def __init__(self):
        self.priority = (-1, 0, 0)

    def run_event(self, engine, queue):
        engine.run_residual()

    def __repr__(self):
        return 'ResidualEvent()'
