"""
Each Effect class that inherits from BaseEffect typically overrides a few (about 1-3) methods in
order to cause an effect or interrupt execution at certain points in the battle loop.

The 'effects' attribute of BattlePokemon, BattleSide, and BattleField contains a set of these
Effects. At certain points in the battle, the BattleEngine will call a handler on each** of these
effects; for example (during damage calculation):

    for effect in chain(pokemon.effects, self.battlefield.effects):
        base_power = effect.on_modify_base_power(user, move, target, self, base_power)

In this example, for each effect on the pokemon and the battlefield, if it is an effect that affects
the base power of a move, it may modify the value of base_power that it returns. BaseEffect's
default implementation of each handler is a no-op. This allows each Effect to only override the
methods that correspond to battle events related to the Effect.

In cases such as the on_before_move handler, the order in which the handlers are called is
important. The @priority decorator assigns a number to the handler, and when multiple effects are
present on the pokemon, they run in order of priority (highest first). For example:

    for effect in sorted(pokemon.effects, key=lambda e: e.on_before_move.priority, reverse=True):
        if effect.on_before_move(user, move, self) is FAIL:
            return

Each effect has a `source`, which is an enum that uniquely identifies the effect on the pokemon,
side, or battlefield to which it is attached. (Note that each effect class is not necessarily
identified uniqely by its source though, for example all Abilities have the same source enum,
but only one ability at a time is ever in effect on a pokemon.)

Effects inheriting from BaseEffect are in the effects, abilities, statuses and weather modules.

**This results in the vast majority of handler calls being no-ops. Once the prototype is complete,
some optimizations may be in order, such as registering only methods that aren't no-ops.
"""
from misc.functions import priority
from pokedex.enums import ABILITY

class BaseEffect(object):
    class __metaclass__(type):
        def __init__(cls, name, bases, dct):
            cls.name = name.lower()

            # search through the class and its bases for all handler methods. classes using multiple
            # inheritance must inherit from the class defining handlers first.
            cls.handler_names = ()
            search_cls = cls
            while True:
                cls.handler_names += tuple(hname for hname in search_cls.__dict__
                                           if hname.startswith('on_') and
                                           hname not in cls.handler_names)
                if search_cls is object:
                    break
                search_cls = search_cls.__bases__[0]
                if search_cls.__name__ == 'BaseEffect':
                    break

        def __repr__(cls):
            return cls.__name__

    source = None   # must be overriden
    duration = None # default: effect does not expire

    def on_end(self, pokemon, engine):
        """ Called when an effect ends, regardless of cause """

    def on_start(self, pokemon, engine):
        """ Called on abilities only when they activate """

    @priority(0)
    def on_timeout(self, pokemon, engine):
        """ Called when the effect wears off (by self.duration hitting 0) """

    def on_get_move_choices(self, pokemon, moves):
        """ Return a modified list of valid move choices """
        return moves

    def on_before_turn(self, pokemon, foe):
        """ Called just before each player makes decisions for the turn """

    @priority(0)
    def on_before_move(self, user, move, engine):
        """ Called before a move is attempted. Return FAIL to cause move to fail. """

    def on_after_move_secondary(self, user, move, target, engine):
        """ This executes only if the move was successful, and is negated by Volatile.SHEERFORCE """

    def on_after_foe_move_secondary(self, foe, move, target, engine):
        """
        This executes only if the foe's move was successful, and is negated by
        Volatile.SHEERFORCE.
        """

    def on_try_hit(self, user, move, target, engine):
        """ Called before hitting the opponent with a move. Return FAIL to fail the move """

    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        """
        Called when the foe tries to hit this effect's pokemon with a move.
        Return FAIL to fail the move.
        """

    def on_move_hit(self, user, move, engine):
        """
        Called at the beginning of move_hit, immediately before substitute check and damage
        calculation, and after success, try_hit, accuracy, and immunity checks.
        """

    def on_move_success(self, user, move, target):
        """
        Called if user successfully hits target with a move.
        """

    def on_after_foe_hit(self, foe, move, target, engine):
        """ Called when the foe sucessfully hits this effect's pokemon with a move """

    def on_modify_move(self, move, user, engine):
        """
        Called when a move is about to be used. `move` is a copy; modifications to it will persist
        until the end of run_move
        """

    def on_modify_foe_move(self, move, user, engine):
        """
        Called when the foe's move is about to be used. `move` is a copy; modifications to it will
        persist until the end of run_move
        """

    def on_modify_base_power(self, user, move, target, engine, base_power):
        """
        Return a value calculated from `base_power`. Do not round float results, as this value may
        be passed into other effects' on_modify_base_power handlers.
        """
        return base_power

    def on_faint(self, pokemon, cause, source, engine):
        """
        Called when a pokemon faints, after it is put in the faint queue.
        """

    def on_foe_faint(self, pokemon, cause, source, foe, engine):
        """
        Called when `pokemon`s foe faints
        """

    def on_accuracy(self, user, move, target, engine, accuracy):
        """
        Called when user is attacking foe.  Return accuracy in [0, 100] or None to skip accuracy
        check.
        """
        return accuracy

    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        """
        Called when pokemon (target) with this effect is being attacked by foe.
        Return accuracy in [0, 100] or None to skip accuracy check.
        """
        return accuracy

    def on_modify_effectiveness(self, user, move, target, effectiveness):
        return effectiveness

    def on_modify_spe(self, pokemon, engine, spe):
        """ Return modified spe """
        return spe

    def on_modify_spd(self, pokemon, move, engine, spd):
        """ Return modified spd """
        return spd

    def on_modify_spa(self, pokemon, move, engine, spa):
        """ Return modified spa """
        return spa

    def on_modify_atk(self, pokemon, move, engine, atk):
        """ Return modified atk """
        return atk

    def on_modify_def(self, pokemon, move, engine, def_):
        """ Return modified def """
        return def_

    @priority(0)
    def on_switch_in(self, pokemon, engine):
        """
        Called when a pokemon or side with this effect switches in a new pokemon for any reason.
        The pokemon passed in is the new one.
        The foe may be None when this runs.
        """

    @priority(0)
    def on_switch_out(self, pokemon, incoming, engine):
        """ Called immediately before a pokemon clears its volatiles/boosts and switches out """

    def on_trap_check(self, pokemon):
        """ Return True to trap the pokemon """
        return False

    @priority(0)
    def on_residual(self, pokemon, foe, engine):
        """
        Called during the residual stage of each turn (between turns).

        - When this effect is attached to a pokemon or side, foe is the opponent (may be None)
        - When this effect is attached to the battlefield, "pokemon" is side0.active_pokemon and
          "foe" is side1.active_pokemon, and either may be None
        """

    def on_modify_damage(self, user, move, effectiveness, damage):
        """ Modify the final result about to be returned from a damage calculation """
        return damage

    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        """ Modify the final result about to be returned from a foe's damage calculation """
        return damage

    def on_get_immunity(self, thing):
        """
        `thing` may be a Move, Type, Status, Volatile, Weather, or POWDER

        return True if target (the pokemon this is attached to) is immune to `thing`
        return False if target is definitely NOT immune (to override standard type-based immunity)
        return None to default to standard immunity
        """

    @priority(0)
    def on_damage(self, pokemon, cause, source, engine, damage):
        """ Return a modified amount of damage, or FAIL """
        return damage

    def on_boost(self, pokemon, boosts, self_induced):
        """
        Return a modified set of boosts. The order here doesn't matter because currently the
        on_boost effects are abilities, so it can be assumed that only one on_boost is in effect.
        """
        return boosts

    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        """
        Called after pokemon is damaged by a foe's move.

        NOTE: pokemon.is_fainted() should not be called here, as this method run during the only
        time that it is valid for hp <= 0 but status != FNT.
        """

    def on_foe_heal(self, foe, hp, cause, engine):
        """
        Called before the foe heals. Return FAIL to prevent healing.
        """

    def on_set_status(self, status, pokemon, setter, engine):
        """
        Called before `status` is set on `pokemon`. Return FAIL to prevent it.
        """

    def on_after_set_status(self, status, pokemon, setter, engine):
        """
        Called after `status is successfully set on `pokemon`
        """

    def on_weather(self, pokemon, weather, engine):
        """ Called by weather effects in their on_residual handler """

    def on_modify_priority(self, pokemon, move, engine):
        """
        Return a number to increase or decrease the priority of a move, else 0.
        e.g. GaleWings returns +1 for flying moves
        """
        return 0

    def on_update(self, pokemon, engine):
        """
        Called after each event from engine.event_queue is run, and immediately before
        on_switch_out.
        """

    def on_break_mold(self, target, engine):
        """
        Called whenever a move is used, and when an opponent is being forced to switch in. target is
        guaranteed not None.
        """

    def on_unbreak_mold(self, target):
        """
        Called when use_move returns. target is guaranteed not None.
        """

    @staticmethod
    def on_eat(pokemon, engine):
        """
        Called when an item is used/consumed by a pokemon.
        """

    def on_use_item(self, pokemon, item, engine):
        """
        Called when a pokemon uses its item
        """

    def on_lose_item(self, pokemon, item):
        """
        Called when a pokemon loses its item, by using it or by theft.
        """

    def on_hit_substitute(self, foe, move, target, engine):
        """
        Called on the Substitute effect when it is hit by a move
        """

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ', '.join(['%s=%s' % (attr, getattr(self, attr))
                                      for attr in dir(self) if
                                      not self.source is ABILITY and
                                      not attr.startswith('__') and
                                      not (attr == 'suppressed' and not getattr(self, attr)) and
                                      not isinstance(getattr(self, attr), type(self.__repr__)) and
                                      ((attr == 'duration' and self.duration is not None)
                                       or attr not in dir(BaseEffect))]))
