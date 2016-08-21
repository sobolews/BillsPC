import math
import random
from bisect import insort
from collections import namedtuple
from itertools import chain
from functools import partial

from battle.battlefield import BattleField, BattleSide
from battle.battlepokemon import BattlePokemon
from battle.rolloutpolicy import RandomRolloutPolicy
from battle.events import MoveEvent, SwitchEvent, InstaSwitchEvent, ResidualEvent, MegaEvoEvent
from misc.functions import gf_round
from pokedex import effects, statuses
from pokedex.abilities import abilitydex
from pokedex.enums import MoveCategory, Volatile, Status, Cause, FAIL, Type, Decision, ABILITY
from pokedex.moves import movedex, Move
from pokedex.stats import Boosts

if __debug__: from _logging import log

STATUS, PHYSICAL, SPECIAL = MoveCategory.STATUS, MoveCategory.PHYSICAL, MoveCategory.SPECIAL
CRIT_ROLL = (16, 8, 2, 1)

STATUS_EFFECTS = {
    Status.PAR: statuses.Paralyze,
    Status.SLP: statuses.Sleep,
    Status.BRN: statuses.Burn,
    Status.PSN: statuses.Poison,
    Status.TOX: statuses.Toxic,
    Status.FRZ: statuses.Freeze
}

Residual = namedtuple('Residual', ['holder', 'effect', 'call'])

class Battle(object):
    """
    Encapsulates the logic required to run each turn of a full battle. All battle state is
    encapsulated within the BattleField (except for intra-turn state), so it is possible to swap out
    battlefields provided they are in-between turns.

    The event_queue and faint_queue are the only members with state besides the battlefield, and
    they are always empty lists between turns.
    """
    def __init__(self, team0, team1, policy0=None, policy1=None):
        """
        team is a list of up to 6 BattlePokemon.
        policy is a RolloutPolicy
        """
        assert 0 < len(team0) <= 6
        assert 0 < len(team1) <= 6
        self.battlefield = BattleField(BattleSide(team0, 0), BattleSide(team1, 1))
        self.rollout_policies = (RandomRolloutPolicy(0) if policy0 is None else policy0,
                                 RandomRolloutPolicy(1) if policy1 is None else policy1)
        self.event_queue = []   # pop from right
        self.faint_queue = []   # pop from right

    @classmethod
    def from_battlefield(cls, battlefield, policy0=None, policy1=None):
        """ Alternate constructor from an existing battlefield. """
        battle = cls.__new__(cls)
        battle.battlefield = battlefield
        battle.rollout_policies = (RandomRolloutPolicy(0) if policy0 is None else policy0,
                                   RandomRolloutPolicy(1) if policy1 is None else policy1)
        battle.event_queue = []
        battle.faint_queue = []
        return battle

    def get_foe(self, pokemon):
        """ Return the foe opposite to `pokemon`. If the foe is fainted, return None. """
        return self.battlefield.sides[not pokemon.side.index].active_pokemon

    def get_foe_side(self, pokemon):
        """ Return the side opposite to `pokemon`. """
        return self.battlefield.sides[not pokemon.side.index]

    def run_move(self, user, move, target):
        """
        run_move should be called 0 or 1 times for each pokemon, each turn. There should always be
        two run_move/run_switch calls in the queue at the beginning of each turn.
        """
        assert not user.is_fainted()
        assert not user.has_moved_this_turn
        assert user.will_move_this_turn
        assert user.is_active
        assert (move == movedex['struggle'] or
                user.pp.get(move, -1) > 0 or
                move.max_pp == 0 or
                user.has_effect(Volatile.LOCKEDMOVE) or
                user.has_effect(Volatile.TWOTURNMOVE))

        user.has_moved_this_turn = True
        user.will_move_this_turn = False

        if user.has_effect(Volatile.ENCORE) and move != movedex['struggle']:
            move = user.get_effect(Volatile.ENCORE).override_move_choice()

        if user.activate_effect('on_before_move', user, move, self, failfast=True) is FAIL:
            user.remove_effect(Volatile.TWOTURNMOVE) # remove bounce etc.'s invulnerability
            return

        if (move != movedex['struggle'] and
            not user.has_effect(Volatile.LOCKEDMOVE) and
            not user.has_effect(Volatile.TWOTURNMOVE)
        ):
            user.deduct_pp(move, target)

        self.use_move(user, move, target)

        user.last_move_used = move
        if not move.calls_other_moves:
            self.battlefield.last_move_used = move

    def use_move(self, user, move, target):
        """
        Wrap _use_move in moldbreaker handling
        """
        if target is not None:
            ability = user.get_effect(ABILITY)
            ability.on_break_mold(target, self)

        result = self._use_move(user, move, target)

        if target is not None:
            ability.on_unbreak_mold(self.get_foe(user)) # roar, etc. could have changed the foe

        return result

    def _use_move(self, user, move, target):
        """ Return value not used (except for testing) """
        assert not user.is_fainted()
        assert user.is_active
        if __debug__: log.i('%s used %s! (target=%s)', user, move, target)

        # copy the move, so that modify_move doesn't modify the global copy in movedex
        move = move.__class__()

        move.on_modify_move(user, target, self)
        user.activate_effect('on_modify_move', move, user, self)
        if target is not None:
            target.activate_effect('on_modify_foe_move', move, user, self)

        if move.targets_user or move.targets_field:
            return self.fast_use_move(user, move) # fast path for moves not targeting opponent

        if target is None or target.is_fainted():
            if __debug__: log.i('But it failed: No target')
            if move.selfdestruct:
                self.faint(user, Cause.SELFDESTRUCT, move)
            return FAIL

        damage = self.try_move_hit(user, move, target)

        if (user.hp == 0 or move.selfdestruct) and not user.status is Status.FNT:
            if __debug__: log.d('User has no HP after using move, fainting')
            self.faint(user, Cause.SELFDESTRUCT, move)

        if damage is FAIL:
            if __debug__:
                if not user.has_effect(Volatile.TWOTURNMOVE):
                    log.i('%s: But it failed', move)
            move.on_move_fail(user, self)
            return FAIL

        if not user.has_effect(Volatile.SHEERFORCE):
            target.activate_effect('on_after_foe_move_secondary', user, move, target, self)
            user.activate_effect('on_after_move_secondary', user, move, target, self)

        return damage # for testing only

    def try_move_hit(self, user, move, target):
        assert target is not None

        if move.check_success(user, target, self) is FAIL:
            return FAIL # moves are responsible for logging their own failure

        if self.battlefield.activate_effect('on_try_hit',
                                            user, move, target, self, failfast=True) is FAIL:
            return FAIL

        for effector in (target, target.side):
            if effector.activate_effect('on_foe_try_hit', user, move, target, self,
                                        failfast=True) is FAIL:
                return FAIL

        if target.is_immune_to_move(user, move):
            if __debug__: log.i('%s is immune to %s', target, move)
            return FAIL

        if self.check_accuracy(user, move, target) is FAIL:
            return FAIL

        if move.multihit:
            hits = (move.multihit[-1] if user.ability is abilitydex['skilllink'] else
                    random.choice(move.multihit))

            total_damage = 0
            hit = 0
            for hit in range(hits):
                damage = self.move_hit(user, move, target)
                if damage is FAIL:
                    if __debug__: log.i('Hit %d times, and failed', hit)
                    return FAIL
                total_damage += damage or 0

                if target.hp <= 0 or user.hp <= 0 or user.status is Status.SLP:
                    break
                else:
                    self.run_update()

            if __debug__: log.i('Hit %d times!', hit+1)

        else:
            damage = total_damage = self.move_hit(user, move, target)

        if damage not in (FAIL, None, 0):
            if move.recoil > 0 and not user.is_fainted():
                self.damage(user, int(round(total_damage * move.recoil / 100.0)) or 1,
                            Cause.RECOIL, move)

            target.was_attacked_this_turn = {'move': move, 'damage': damage}

        return total_damage

    def move_hit(self, user, move, target):
        assert target is not None

        user.activate_effect('on_move_hit', user, move, self)

        substitute = target.get_effect(Volatile.SUBSTITUTE)
        if substitute is not None:
            result = substitute.on_hit_substitute(user, move, target, self)
            if result is not None:
                if __debug__: log.d('Hit substitute: result=%s', result)
                return result
            elif __debug__: log.d('Bypassed substitute')

        damage = self.calculate_damage(user, move, target)
        if damage is FAIL:
            return FAIL

        if damage is not None:
            damage = self.damage(target, damage, Cause.MOVE, move, user, move.drain)
            if damage is FAIL:
                if __debug__: log.i('Move failed in Battle.damage: returned %s', damage)
                return FAIL

        user.damage_done_this_turn = damage

        if move.target_status is not None:
            if self.set_status(target, move.target_status, user) is FAIL:
                return FAIL     # all target_status moves do nothing else, so fail fast

        if move.user_boosts is not None and not user.is_fainted():
            user.apply_boosts(move.user_boosts, True)

        user.activate_effect('on_move_success', user, move, target)

        if move.on_success(user, target, self) is FAIL:
            if __debug__: log.i('Move "%s" failed in on_success', move)
            return FAIL

        target = self.get_foe(user) # roar, etc. could have changed the active foe

        if target is not None:
            target.activate_effect('on_after_foe_hit', user, move, target, self)

        for s_effect in move.secondary_effects:
            self.apply_secondary_effect(user if s_effect.affects_user else target,
                                        s_effect, user)

        user.must_switch = move.switch_user

        if __debug__: log.d('returning damage=%s', damage)
        return damage

    def check_accuracy(self, user, move, target):
        """
        Return FAIL if the move misses.
        An accuracy value of None means to skip the accuracy check, i.e. it always hits.
        """
        accuracy = move.accuracy
        accuracy = user.accumulate_effect('on_accuracy', user, move, target, self, accuracy)
        accuracy = target.accumulate_effect('on_foe_accuracy', user, move, target, self, accuracy)
        if accuracy is None:
            return

        boost_factor = (1.0, 4.0/3.0, 5.0/3.0, 2.0, 7.0/3.0, 8.0/3.0, 3.0)
        if not move.ignore_accuracy_boosts:
            acc_boost = user.boosts['acc']
            if acc_boost > 0:
                accuracy *= boost_factor[acc_boost]
            elif acc_boost < 0:
                accuracy /= boost_factor[-acc_boost]

        if not move.ignore_evasion_boosts:
            evn_boost = target.boosts['evn']
            if evn_boost > 0:
                accuracy /= boost_factor[evn_boost]
            elif evn_boost < 0:
                accuracy *= boost_factor[-evn_boost]

        if __debug__: log.d('Using accuracy of %s', accuracy)
        if random.randrange(100) >= int(accuracy):
            if __debug__: log.i('But it missed!')
            return FAIL

    def fast_use_move(self, user, move):
        """
        Fast path optimization out of self.use_move for moves not targeting an opponent
        (move.targets_user or move.targets_field). Replaces try_move_hit and move_hit and allows
        them to skip (if target is None) checks.

        Specifically skips on_foe_try_hit, {immunity,accuracy,multihit,substitute} checks,
        calculate_damage, drain check, move.target_status, move.secondary_effects,
        move.on_move_fail, move.on_after_move_secondary.
        """
        if __debug__: log.d('%s: Fast path', move)
        if move.check_success(user, None, self) is FAIL:
            if __debug__: log.i('(check_success) But it failed')
            return FAIL

        user.damage_done_this_turn = 0

        if move.user_boosts is not None:
            if user.apply_boosts(move.user_boosts, True) is FAIL:
                if __debug__: log.i('(apply_boosts) But it failed')
                return FAIL

        if move.on_success(user, None, self) is FAIL:
            if __debug__: log.i('(on_success) But it failed')
            return FAIL

        if not move.calls_other_moves: # don't override switch moves called via copycat/sleeptalk
            user.must_switch = move.switch_user

        if (user.hp == 0 or move.selfdestruct) and not user.status is Status.FNT:
            if __debug__: log.d('User has no HP after using move, fainting')
            self.faint(user, Cause.SELFDESTRUCT, move)

    def apply_secondary_effect(self, pokemon, s_effect, user):
        if (random.randrange(100) >= s_effect.chance or
            pokemon is None or
            pokemon.is_fainted() or
            (pokemon.ability is abilitydex['shielddust'] and not s_effect.affects_user)):
            return

        if __debug__: log.d('Applying %s to %s', s_effect, pokemon)

        if s_effect.boosts is not None:
            pokemon.apply_boosts(s_effect.boosts, s_effect.affects_user)
        elif s_effect.status is not None:
            self.set_status(pokemon, s_effect.status, user)
        elif s_effect.volatile is Volatile.FLINCH:
            pokemon.set_effect(effects.Flinch())
        elif s_effect.volatile is Volatile.CONFUSE:
            pokemon.confuse(user.ability is abilitydex['infiltrator'])
        elif s_effect.callback is not None:
            s_effect.callback(pokemon, user, self)
        else:
            assert False, 'Tried to apply secondary effect with no boosts, volatile, or status'

    def confusion_hit(self, pokemon):
        """ Cause a pokemon to hurt itself in confusion """
        assert pokemon.is_active

        damage = self.calculate_damage(pokemon, movedex['confusiondamage'], pokemon)
        self.damage(pokemon, damage, Cause.CONFUSE, movedex['confusiondamage'])

    def calculate_damage(self, user, move, target):
        """
        Return FAIL: "But it failed!"
        Return None: Move did not attempt to do damage
        Return int: Amount of damage dealt (returning 0 still means damage for Static etc.)
        """
        if target.is_immune_to_move(user, move):
            if __debug__: log.i('FAIL: %s is immune to %s', target, move)
            return FAIL

        if __debug__: log.d('Calculating damage for %s attacking %s with %s', user, target, move)

        damage = move.damage_callback(user, target)
        if damage is not None:
            if __debug__: log.i("Using %s damage from %s's damage_callback", damage, move)
            return damage

        base_power = move.get_base_power(user, target, self)
        if base_power is not None:
            base_power = self.modify_base_power(user, move, target, base_power)
        if not base_power:
            if __debug__: log.d('base_power=%s, returning damage=None', base_power)
            return None

        assert move.category in (PHYSICAL, SPECIAL)

        base_power = int(max(gf_round(base_power), 1))
        if __debug__: log.d('Using base_power of %s', base_power)

        crit = move.crit = ((move.always_crit or self.get_critical_hit(move.crit_ratio)) and not
                            (move.never_crit or target.ability in (abilitydex['battlearmor'],
                                                                   abilitydex['shellarmor'])))
        if __debug__:
            if crit: log.i('Critical hit!')

        defensive_category = move.defensive_category or move.category
        attacking_stat = 'atk' if move.category is PHYSICAL else 'spa'
        defending_stat = 'def' if defensive_category is PHYSICAL else 'spd'
        attack_stat_source = user if not move.use_opponent_attack else target

        attack_boosts = attack_stat_source.boosts[attacking_stat]
        defense_boosts = target.boosts[defending_stat]

        if move.ignore_offensive_boosts or (crit and attack_boosts < 0):
            attack_boosts = 0
        if move.ignore_defensive_boosts or (crit and defense_boosts > 0):
            defense_boosts = 0

        attack = attack_stat_source.calculate_stat(attacking_stat, attack_boosts)
        defense = target.calculate_stat(defending_stat, defense_boosts)

        attack = int(user.accumulate_effect('on_modify_' + attacking_stat,
                                            user, move, self, attack))

        modify = self.modify_def if defending_stat == 'def' else self.modify_spd
        defense = int(modify(defense, target, move))

        damage = int(int(int(2 * user.level / 5 + 2) * base_power * attack / defense) / 50) + 2

        if crit:
            damage = int(damage * 1.5)

        damage = int(damage * self.damage_randomizer() / 100)

        if move.type in user.types:
            damage = int(damage * move.stab)

        weather_mod = self.battlefield.get_effect(self.battlefield.weather)
        if weather_mod is not None:
            damage = gf_round(weather_mod.weather_modify_damage(move, damage))

        effectiveness = self.get_effectiveness(user, move, target)

        damage *= effectiveness
        if __debug__:
            if effectiveness != 1:
                log.i("It's %s effective", {0.25: 'barely', 0.5: 'not very',
                                            2: 'super', 4: 'super duper'}[effectiveness])

        damage = self.modify_damage(damage, user, move, target, crit, effectiveness)
        damage = gf_round(damage) or 1

        if __debug__: log.d('Returning damage=%s', damage)
        return damage

    def modify_base_power(self, user, move, target, base_power):
        for effector in (user, self.battlefield):
            base_power = effector.accumulate_effect('on_modify_base_power',
                                                    user, move, target, self, base_power)
        if target.ability is abilitydex['dryskin'] and move.type is Type.FIRE:
            base_power *= 1.25
        return base_power

    @staticmethod # for duck punching
    def get_critical_hit(crit_ratio):
        return random.randrange(CRIT_ROLL[min(crit_ratio, 3)]) == 0

    @staticmethod # for duck punching
    def damage_randomizer():
        return 100 - random.randrange(16)

    def modify_damage(self, damage, user, move, target, crit, effectiveness):
        for effector in (user, user.side, self.battlefield):
            damage = effector.accumulate_effect('on_modify_damage',
                                                user, move, effectiveness, damage)
        for effector in (target, target.side):
            damage = effector.accumulate_effect('on_modify_foe_damage',
                                                user, move, target, crit, effectiveness, damage)
        return damage

    def get_effectiveness(self, user, move, target):
        effectiveness = move.get_effectiveness(target)
        for effector in (user, self.battlefield):
            effectiveness = effector.accumulate_effect('on_modify_effectiveness',
                                                       user, move, target, effectiveness)
        return effectiveness

    def modify_def(self, def_, target, move):
        return target.accumulate_effect('on_modify_def', target, move, self, def_)

    def modify_spd(self, spd, target, move):
        for effector in (target, self.battlefield):
            spd = effector.accumulate_effect('on_modify_spd', target, move, self, spd)
        return spd

    def modify_spe(self, spe, pokemon):
        for effector in (pokemon, pokemon.side, self.battlefield):
            spe = effector.accumulate_effect('on_modify_spe', pokemon, self, spe)
        return spe

    def effective_spe(self, pokemon):
        return self.modify_spe(pokemon.calculate_stat('spe'), pokemon)

    def damage(self, pokemon, damage, cause, source=None, attacker=None, drain_pct=None):
        """
        Return FAIL or int amount of damage done.
        If the damage is caused directly by a move then source and attacker must be set.
        Draining effects (drain moves or leechseed) pass a percent of damage to drain to attacker.
        """
        if pokemon.is_fainted():
            if __debug__:
                log.w('Tried to damage fainted pokemon %s: cause: %s, source: %s, attacker: %s',
                      pokemon, cause, source, attacker)
            return 0

        assert pokemon is not attacker
        assert pokemon.side.active_pokemon is pokemon
        assert pokemon.is_active
        assert damage >= 0
        assert ((isinstance(attacker, BattlePokemon) and isinstance(source, Move)) if
                cause is Cause.MOVE else True)

        if damage == 0:
            if __debug__: log.w('Battle.damage called with damage=0') # this shouldn't happen
            return 0

        if cause is Cause.WEATHER and pokemon.is_immune_to(source):
            if __debug__: log.i('Weather immunity: %s / %s', pokemon, source)
            return 0

        if damage < 1:
            damage = 1 # always do at least 1 damage
        else:
            damage = int(damage)

        damage = pokemon.accumulate_effect('on_damage',
                                           pokemon, cause, source, self, damage, failfast=True)
        if damage is FAIL:
            return FAIL

        pokemon.hp -= damage
        if __debug__: log.i('%s took %s (%.1f%%) damage from %s: %s; hp=%d/%d' %
                            (pokemon, damage, 100*float(damage)/pokemon.max_hp, cause, source,
                             pokemon.hp, pokemon.max_hp))
        if pokemon.hp <= 0:
            damage += pokemon.hp

        if drain_pct and not attacker.is_fainted():
            self.heal(attacker, int(math.ceil(damage * drain_pct / 100.0)), cause=Cause.DRAIN,
                      foe=pokemon)

        if cause is Cause.MOVE:
            pokemon.activate_effect('on_after_move_damage', self, pokemon, damage, source, attacker)

        if pokemon.hp <= 0:
            self.faint(pokemon, cause, source, attacker)

        return damage

    def heal(self, pokemon, hp, cause=None, source=None, foe=None):
        if pokemon.is_fainted():
            if __debug__: log.e('Tried to heal fainted pokemon: %s, cause=%s, source=%s, foe=%s',
                                pokemon, cause, source, foe)
            return

        assert isinstance(hp, int)
        assert hp >= 0

        if foe is not None and foe.activate_effect('on_foe_heal',
                                                   pokemon, hp, cause, self, failfast=True) is FAIL:
            return FAIL

        if __debug__: prev_hp = pokemon.hp
        pokemon.hp = min(hp + pokemon.hp, pokemon.max_hp)
        if __debug__: log.i('%s healed %d damage; hp=%d', pokemon, pokemon.hp - prev_hp, pokemon.hp)

    def faint(self, pokemon, cause, source=None, attacker=None):
        if pokemon.status is Status.FNT:
            if __debug__: log.w('Tried to faint %s twice!', pokemon)
            return
        pokemon.hp = 0
        pokemon.status = Status.FNT # This should be the only way to assign Status.FNT
        pokemon.side.last_fainted_on_turn = self.battlefield.turns
        pokemon.side.active_pokemon = None
        pokemon.is_active = False

        if __debug__: log.i('%s fainted: %s (source=%s)', pokemon, cause, source)
        self.faint_queue.insert(0, pokemon)

        pokemon.activate_effect('on_faint', pokemon, cause, source, self)

        if attacker is not None and not attacker.is_fainted():
            attacker.activate_effect('on_foe_faint', attacker, cause, source, pokemon, self)

        foe = self.get_foe(pokemon)
        if foe is not None:
            foe.remove_trap_effects()

        pokemon.clear_effects(self)
        pokemon.boosts = Boosts()

    def direct_damage(self, pokemon, damage):
        """
        Bypasses on_damage; is 'cause-less'.
        {substitute, bellydrum, painsplit, struggle recoil} are direct damage
        """
        if damage < 1:
            damage = 1 # always do at least 1 damage
        else:
            damage = int(damage)

        pokemon.hp -= damage
        if pokemon.hp <= 0:
            self.faint(pokemon, Cause.DIRECT)

    def force_random_switch(self, pokemon, forcer):
        if (pokemon.is_fainted() or
            forcer.is_fainted() or
            pokemon.ability.name == 'suctioncups'
        ):
            return FAIL

        team_members = pokemon.get_switch_choices(forced=True)
        if team_members:
            incoming = random.choice(team_members)
            if __debug__: log.d('Force switching %s for %s', pokemon, incoming)
            self.run_switch(pokemon, incoming)
            forcer.get_effect(ABILITY).on_break_mold(incoming, self)
            self.post_switch_in(incoming)
        elif __debug__:
            log.i('Tried to force random switch; %s has no remaining teammates', pokemon)

    def set_status(self, pokemon, status, setter):
        """
        Set `status` (enums.Status) on `pokemon`.

        Fails if the pokemon is already statused, Sleep Clause activates, or if an effect or
        immunity prevents it.

        `setter` should be the pokemon causing the status (usually the foe). `setter` == `pokemon`
        in the case of rest, toxicorb, etc., or None in the case of toxicspikes, etc.
        """
        assert not pokemon.is_fainted()
        assert setter is None or isinstance(setter, BattlePokemon)

        if status is Status.SLP and any(teammate.status is Status.SLP and not teammate.is_resting
                                        for teammate in pokemon.side.team
                                        if teammate is not pokemon):
            if __debug__: log.i('Sleep Clause Mod!')
            return FAIL

        if pokemon.status is not None or pokemon.is_immune_to(status):
            if __debug__: log.i('Failed to set status %s: ' % status +
                                ('%%s is already statused (%s)' % pokemon.status
                                 if pokemon.status is not None else
                                 '%s is immune') % pokemon)
            return FAIL

        for effector in (pokemon, pokemon.side, self.battlefield):
            if effector.activate_effect('on_set_status',
                                        status, pokemon, setter, self, failfast=True) is FAIL:
                return FAIL

        pokemon.status = status
        pokemon.set_effect(STATUS_EFFECTS[status](pokemon))
        pokemon.activate_effect('on_after_set_status', status, pokemon, setter, self)

    def run_residual(self):
        if __debug__: log.i('Between turns')
        sides = self.battlefield.sides
        actives = sorted([sides[0].active_pokemon, sides[1].active_pokemon],
                         key=lambda p: 0 if p is None else (-self.effective_spe(p),
                                                            random.random()))

        residuals = []

        # First pass: decrement duration of all residual effects, and add their on_timeout handler
        # if they time out
        for thing in filter(None, (actives[0], actives[1], sides[0], sides[1], self.battlefield)):
            for effect in thing.effects:
                if effect.duration is not None:
                    assert effect.duration > 0
                    effect.duration -= 1

                    if effect.duration == 0:
                        if __debug__: log.i('%s timed out', effect)
                        if 'on_timeout' in effect.handler_names:
                            # No holder/effect for timed out effects, because they are removed so
                            # they cannot be checked for existence
                            residuals.append(Residual(None, None,
                                                      partial(effect.on_timeout, thing, self)))
                        thing.remove_effect(effect.source, self)

        # Second pass: gather all non-timed-out effects' on_residual handlers
        for pokemon, foe in ((actives[0], actives[1]), (actives[1], actives[0])):
            if pokemon is not None:
                residuals.extend(Residual(pokemon, on_residual.__self__.source,
                                          partial(on_residual, pokemon, foe, self))
                                 for on_residual in pokemon.effect_handlers['on_residual'])

        residuals.extend(Residual(self.battlefield, on_residual.__self__.source,
                                  partial(on_residual, actives[0], actives[1], self))
                         for on_residual in self.battlefield.effect_handlers['on_residual'])

        # For each residual, check first if its effect still exists on the holder, because another
        # residual may have removed it (e.g. shedskin and poison).
        for residual in sorted(residuals, key=lambda r: r.call.func.priority, reverse=True):
            if residual.holder is None or residual.holder.has_effect(residual.effect):
                if __debug__:
                    if residual.call.func.__func__ not in (effects.BaseEffect.on_residual.__func__,
                                                           effects.BaseEffect.on_timeout.__func__,):
                        log.i('Residual effect: %s', residual.call.func.__self__)
                residual.call()

    def run_update(self):
        actives = (side.active_pokemon for side in self.battlefield.sides if
                   side.active_pokemon is not None)

        for pokemon in sorted(actives, key=lambda p: (-self.effective_spe(p), random.random())):
            pokemon.activate_effect('on_update', pokemon, self)

    def run_switch(self, outgoing, incoming):
        assert outgoing is None or outgoing.side == incoming.side
        assert outgoing != incoming
        assert not incoming.is_active
        assert outgoing is None or outgoing.is_active
        assert not incoming.is_fainted()
        assert outgoing is None or not outgoing.is_fainted()
        if __debug__: log.i('Switching %s for %s', outgoing, incoming)

        if outgoing is not None:
            self.switch_out(outgoing, incoming)

        # outgoing could have fainted during self.switch_out from pursuit
        if outgoing is None or not outgoing.is_fainted():
            self.switch_in(incoming)

    def switch_out(self, outgoing, incoming):
        outgoing.is_switching_out = True

        outgoing.activate_effect('on_switch_out', outgoing, incoming, self)

        outgoing.clear_effects(self)
        outgoing.boosts = Boosts()
        outgoing.types = list(outgoing.pokedex_entry.types) # protean etc. may have changed type
        outgoing.is_active = False
        outgoing.side.active_pokemon = None
        outgoing.is_switching_out = False
        outgoing.turns_out = 0

        foe = self.get_foe(outgoing)
        if foe is not None:
            foe.remove_trap_effects()

    @staticmethod
    def switch_in(pokemon):
        assert pokemon in pokemon.side.team
        assert (not pokemon.is_fainted()) and pokemon.hp > 0

        pokemon.side.active_pokemon = pokemon
        pokemon.is_active = True
        pokemon.has_moved_this_turn = False
        pokemon.will_move_this_turn = False
        pokemon.damage_done_this_turn = 0
        pokemon.was_attacked_this_turn = None
        pokemon.last_move_used = None
        pokemon.turns_out = 0
        pokemon.must_switch = False
        pokemon.ability = pokemon.base_ability
        pokemon.item_used_this_turn = None
        if __debug__: log.i('Switched in %s on side %s', pokemon, pokemon.side.index)

        pokemon.set_effect(pokemon.ability())
        if pokemon.item is not None:
            pokemon.set_effect(pokemon.item())

        if pokemon.status is not None:
            pokemon.set_effect(STATUS_EFFECTS[pokemon.status](pokemon), override_immunity=True)

    def post_switch_in(self, pokemon):
        """
        Foe may be None (e.g. was KO'd with voltswitch)
        """
        # Assumes that all side-based on_switch_in handlers have higher priority than the
        # pokemon-based ones
        for on_switch_in in chain(pokemon.side.effect_handlers['on_switch_in'][:],
                                  pokemon.effect_handlers['on_switch_in'][:]):
            on_switch_in(pokemon, self)
            if pokemon.is_fainted():
                return

        pokemon.get_effect(ABILITY).start(pokemon, self)

    def get_move_decisions(self):
        decisions = []
        for policy in self.rollout_policies:
            side = self.battlefield.sides[policy.index]
            pokemon = side.active_pokemon
            assert pokemon is not None
            assert not pokemon.is_fainted()

            spe = self.effective_spe(pokemon)
            choice, is_move = policy.make_move_decision(pokemon.get_move_choices(),
                                                        pokemon.get_switch_choices(),
                                                        self.battlefield)
            if is_move:
                event = MoveEvent(pokemon, spe, self.modify_priority(pokemon, choice), choice)
                if choice == movedex['pursuit']:
                    self.get_foe(pokemon).set_effect(effects.Pursuit(pokemon, choice))
            else:
                event = SwitchEvent(pokemon, spe, choice)
            decisions.append(event)

            if (pokemon.can_mega_evolve and
                is_move and
                policy.make_mega_evo_decision(self.battlefield)
            ):
                decisions.append(MegaEvoEvent(pokemon, spe))

        return decisions

    def modify_priority(self, pokemon, move):
        return pokemon.accumulate_effect('on_modify_priority', pokemon, move, self, move.priority)

    def get_switch_decision(self, side, forced=False):
        choices = side.get_switch_choices(forced=forced)
        return self.rollout_policies[side.index].make_switch_decision(choices, self.battlefield)

    def init_battle(self):
        if self.battlefield.turns > 0:
            if __debug__: log.e('Trying to initialize battle already in progress:\n\n%r',
                                self.battlefield)
            return

        sides = self.battlefield.sides
        if __debug__: log.i('Starting battle: %s %s', sides[0], sides[1])
        leads = sorted([side.active_pokemon for side in sides],
                       key=lambda p: (-p.calculate_stat('spe'), random.random()))
        for lead in leads:
            self.switch_in(lead)
        for lead in leads:
            self.post_switch_in(lead)
        self.run_update()

    def run_new_battle(self):
        """ Return winner's side (0 or 1) """
        self.init_battle()
        return self.run_battle()

    def run_battle(self):
        while self.battlefield.win is None:
            self.run_turn()

        return self.battlefield.win

    def run_turn(self):
        self.init_turn()
        if self.battlefield.win is not None:
            return
        self.run_initialized_turn()

    def run_initialized_turn(self):
        self.queue_events_for_turn()
        self.run_queued_events()

    def queue_events_for_turn(self):
        self.event_queue.extend(self.get_move_decisions())
        self.event_queue.append(ResidualEvent())
        self.event_queue.sort()

    def run_queued_events(self):
        while self.event_queue:
            if __debug__: log.d('Event Queue: %r', self.event_queue)
            if __debug__: log.d('Next event: %s', self.event_queue[-1])
            event = self.event_queue.pop()
            event.run_event(self, self.event_queue)
            if event.type is not Decision.SWITCH:
                self.run_update()

            for side in self.battlefield.sides:
                if (side.active_pokemon is not None and
                    side.active_pokemon.must_switch and # e.g. from voltswitch
                    side.remaining_pokemon_on_bench > 0
                ):
                    if __debug__:
                        log.d('%s must switch: requesting switch decision', side.active_pokemon)
                    insort(self.event_queue, SwitchEvent(
                        side.active_pokemon,
                        0, # spe calculation is unnecessary; this can't run for both sides at once
                        self.get_switch_decision(side, forced=True)))

            self.resolve_faint_queue()

    def init_turn(self):
        """
        Get switches if pokemon fainted, and increment turn counts
        """
        sides = self.battlefield.sides
        # Loop until both sides have an active pokemon: (needs a loop because of the possibility of
        # having multiple pokemon faint from entry hazards in quick succession)
        while True:
            switch_queue = []
            for side in sides:
                pokemon = side.active_pokemon
                if pokemon is None:
                    if side.remaining_pokemon_on_bench == 0:
                        assert self.battlefield.win is not None
                        return

                    if __debug__: log.i('No active pokemon on side %d; requesting switch' %
                                        side.index)
                    event = InstaSwitchEvent(None, 0, self.get_switch_decision(side, forced=True))
                    insort(switch_queue, event)

                else:
                    assert pokemon.is_active
                    assert not pokemon.is_fainted()
                    pokemon.has_moved_this_turn = False
                    pokemon.damage_done_this_turn = 0
                    pokemon.was_attacked_this_turn = None
                    pokemon.item_used_this_turn = None

            while switch_queue:
                event = switch_queue.pop()
                event.run_event(self, switch_queue)
                if event.type is Decision.SWITCH:
                    self.get_foe_side(event.incoming).update(self)

            self.resolve_faint_queue()

            if sides[0].active_pokemon is None or sides[1].active_pokemon is None:
                continue
            break

        pokemon0, pokemon1 = sides[0].active_pokemon, sides[1].active_pokemon
        pokemon0.will_move_this_turn = True
        pokemon0.turns_out += 1
        pokemon0.activate_effect('on_before_turn', pokemon0, pokemon1)
        pokemon1.turns_out += 1
        pokemon1.will_move_this_turn = True
        pokemon1.activate_effect('on_before_turn', pokemon1, pokemon0)

        self.battlefield.turns += 1
        if __debug__:
            log.i('\nTurn %d', self.battlefield.turns)
            self._debug_sanity_check()

    def resolve_faint_queue(self):
        while self.faint_queue:
            pokemon = self.faint_queue.pop()
            assert pokemon.is_fainted() and pokemon.status is Status.FNT

            if pokemon.side.remaining_pokemon_on_bench == 0 and self.battlefield.win is None:
                self.battlefield.win = int(not pokemon.side.index)
                if __debug__: log.i('Side %d wins!', self.battlefield.win)

            if __debug__:
                if pokemon.effects:
                    log.w('Post-fainted pokemon has effects: %r', pokemon)

    def _debug_sanity_check(self):
        if self.battlefield.win is None:
            for side in self.battlefield.sides:
                assert not side.active_pokemon.is_fainted()
                for pokemon in side.team:
                    if pokemon.name == '<unrevealed>':
                        continue
                    if pokemon.hp == 0 or pokemon.status == Status.FNT:
                        assert pokemon.hp == 0
                        assert pokemon.status == Status.FNT
                        assert not pokemon.effects
                        assert not pokemon.is_active
                        assert not pokemon.boosts
                    else:
                        for effect in chain(pokemon.effects, pokemon.side.effects,
                                            self.battlefield.effects):
                            assert effect.duration > 0 or effect.duration is None
                    pokemon.debug_sanity_check(self)
