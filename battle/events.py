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
import random
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

    def __init__(self, pokemon, spe):
        self.pokemon = pokemon
        self.priority = (self.priority, spe, random.random())

    def __eq__(self, other):
        return self.priority == other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def run_event(self, engine, queue):
        raise NotImplementedError

class MoveEvent(BaseEvent):
    type = Decision.MOVE
    priority = 100 # + move.priority

    def __init__(self, pokemon, spe, priority_modifier, move):
        self.priority = self.priority + move.priority + (priority_modifier or 0)
        super(MoveEvent, self).__init__(pokemon, spe)
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
    priority = 300

    def __init__(self, pokemon, spe, incoming):
        super(SwitchEvent, self).__init__(pokemon, spe)
        self.incoming = incoming

    def run_event(self, engine, queue):
        engine.run_switch(self.pokemon, self.incoming)
        insort(queue, PostSwitchInEvent(self.incoming, engine.effective_spe(self.incoming)))

    def __repr__(self):
        return 'SwitchEvent(pokemon=%s, incoming=%s)' % (self.pokemon, self.incoming)

class InstaSwitchEvent(SwitchEvent):
    priority = 400

class PostSwitchInEvent(BaseEvent):
    type = Decision.POSTSWITCH
    priority = 350

    def __init__(self, pokemon, spe):
        super(PostSwitchInEvent, self).__init__(pokemon, spe)

    def run_event(self, engine, queue):
        engine.post_switch_in(self.pokemon)

    def __repr__(self):
        return 'PostSwitchInEvent(pokemon=%s)' % self.pokemon

class MegaEvoEvent(BaseEvent):
    type = Decision.MEGAEVO
    priority = 200

    def __init__(self, pokemon, spe):
        super(MegaEvoEvent, self).__init__(pokemon, spe)

    def run_event(self, engine, queue):
        engine.run_mega_evo(self.pokemon)

    def __repr__(self):
        return 'MegaEvoEvent(pokemon=%s)' % self.pokemon

class ResidualEvent(BaseEvent):
    type = Decision.RESIDUAL
    priority = -1

    def __init__(self):
        super(ResidualEvent, self).__init__(None, 0)

    def run_event(self, engine, queue):
        engine.run_residual()

    def __repr__(self):
        return 'ResidualEvent()'
