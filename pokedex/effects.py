"""
Volatile effects, as well as field and side conditions go here.

Effect duration, where not None, is decremented between turns. Effect is removed when duration hits
0 (No effect should start the turn at 0). Volatiles and their Effects are always removed upon switch
out. The on_end handler is always called when an effect is removed. Benched pokemon should never
have any effects (even if they are statused, the effect is removed on switch out and reapplied on
switch in).
"""
import random
import math
from itertools import chain

if __debug__: from _logging import log
from misc.functions import priority
from pokedex.baseeffect import BaseEffect
from pokedex.enums import (Volatile, FAIL, Type, Status, Cause, MoveCategory, SideCondition,
                           Hazard, PseudoWeather, ABILITY, ITEM)
from pokedex.stats import Boosts
from pokedex.types import effectiveness


class Attract(BaseEffect):
    source = Volatile.ATTRACT

    def __init__(self, mate):
        self.mate = mate

    @priority(2)
    def on_before_move(self, user, move, engine):
        if not self.mate == engine.get_foe(user):
            user.remove_effect(Volatile.ATTRACT)
            return

        if random.randrange(2):
            if __debug__: log.i('%s was immobolized by Attract!', user)
            return FAIL

class BaseAuraFieldEffect(BaseEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.type is self.aura_type:
            if __debug__: log.i("%s boosted %s's power!", self.source.name, move)
            if engine.battlefield.has_effect(PseudoWeather.AURABREAK):
                if __debug__: log.i('Aura Break broke the aura!')
                return 0.75 * base_power
            return float(0x1547) / 0x1000 * base_power
        return base_power

class DarkAuraFieldEffect(BaseAuraFieldEffect):
    source = PseudoWeather.DARKAURA
    aura_type = Type.DARK

class FairyAuraFieldEffect(BaseAuraFieldEffect):
    source = PseudoWeather.FAIRYAURA
    aura_type = Type.FAIRY

class AuraBreakFieldEffect(BaseEffect):
    source = PseudoWeather.AURABREAK

class TwoTurnMoveEffect(BaseEffect):
    source = Volatile.TWOTURNMOVE
    duration = 2

    def __init__(self, move):
        self.move = move

    def on_get_move_choices(self, pokemon, moves):
        return [self.move]

    def on_trap_check(self, pokemon):
        return True

class Bounce(TwoTurnMoveEffect):
    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        if ((move.name in ('thunder', 'hurricane') or
             'noguard' in (foe.ability.name, target.ability.name))):
            return None
        return 0

class PhantomForce(TwoTurnMoveEffect):
    """ Used for both phantomforce and shadowforce, since they have the same effect """
    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        if 'noguard' in (foe.ability.name, target.ability.name):
            return None
        return 0

class Autotomize(BaseEffect):
    source = Volatile.AUTOTOMIZE
    multiplier = 1
    # Weight modification is implemented in BattlePokemon.weight

NO_BATONPASS = frozenset({
    Volatile.FLASHFIRE, Volatile.AUTOTOMIZE, Volatile.DISABLE, Volatile.TRAPPER, Volatile.STALL,
    Volatile.TRAPPED, Volatile.IGNOREITEM, Volatile.IGNOREABILITY, Volatile.UNBURDEN, Volatile.YAWN,
    Volatile.SHEERFORCE, Volatile.BATONPASS, Volatile.TWOTURNMOVE, Volatile.LOCKEDMOVE,
    Volatile.ATTRACT, Volatile.TRANSFORMED, Volatile.FLINCH, Volatile.CHOICELOCK, Volatile.VANISHED,
    Volatile.MAGNETRISE, Volatile.PURSUIT, ABILITY, ITEM})

class BatonPass(BaseEffect):
    source = Volatile.BATONPASS

    def on_switch_out(self, pokemon, incoming, engine):
        if pokemon.has_effect(Volatile.BATONPASS):
            incoming.boosts = pokemon.boosts
            # TODO: test that this (just transferring the effect) works properly with each effect
            for source, effect in pokemon._effect_index.items():
                if source not in NO_BATONPASS:
                    incoming._effect_index[source] = effect
                    del pokemon._effect_index[source]

            if __debug__: log.i('Batonpassed %s to %s',
                                filter(None, chain([incoming.boosts], incoming.effects)) or None,
                                incoming)


class ChoiceLock(BaseEffect):
    source = Volatile.CHOICELOCK

    def __init__(self, move):
        self.move = move

    def on_get_move_choices(self, pokemon, moves):
        if self.move not in pokemon.moveset:
            pokemon.remove_effect(Volatile.CHOICELOCK)
            if __debug__: log.d("%s doesn't have the choiced move %s, removing choicelock",
                                pokemon, self.move)
            return moves

        if __debug__: log.d('%s is choicelocked into %s', pokemon, self.move)
        return [self.move] if self.move in moves else []

class Confuse(BaseEffect):
    source = Volatile.CONFUSE

    def __init__(self):
        self.turns_left = random.randint(1, 4) # not duration, since it's not checked between turns

    @priority(3)
    def on_before_move(self, user, move, engine):
        if self.turns_left == 0:
            user.remove_effect(Volatile.CONFUSE)
            if __debug__: log.i("%s's confused no more!", user)
            return

        if __debug__: log.i("%s's confusion: %d turns left", user, self.turns_left)
        self.turns_left -= 1

        if random.randrange(2) == 0:
            if __debug__: log.i('%s hurt itself in its confusion', user)
            engine.confusion_hit(user)
            return FAIL

class Flinch(BaseEffect):
    source = Volatile.FLINCH
    duration = 1

    @priority(8)
    def on_before_move(self, user, move, engine):
        if __debug__: log.i('FAIL: %s flinched', user)
        return FAIL

class DestinyBond(BaseEffect):
    source = Volatile.DESTINYBOND

    @priority(100)
    def on_before_move(self, user, move, engine):
        user.remove_effect(Volatile.DESTINYBOND)

    def on_faint(self, pokemon, cause, source, engine):
        if cause is Cause.MOVE:
            foe = engine.get_foe(pokemon)
            if foe is not None:
                if __debug__: log.i('%s took its foe along with it!', pokemon)
                engine.faint(engine.get_foe(pokemon), cause=Cause.DIRECT)

class Disable(BaseEffect):
    source = Volatile.DISABLE

    def __init__(self, move, duration):
        self.move = move
        self.duration = duration

    def on_get_move_choices(self, pokemon, moves):
        return [move for move in moves if move != self.move]

    @priority(7)
    def on_before_move(self, user, move, engine):
        if move == self.move:
            if __debug__: log.i("%s can't use %s because it was disabled this turn", user, move)
            return FAIL

class ElectricTerrain(BaseEffect):
    source = PseudoWeather.ELECTRICTERRAIN
    duration = 5

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.type is Type.ELECTRIC and not user.is_immune_to(Type.GROUND):
            if __debug__: log.i('Electric terrain boosting power of %s from %s', move, user)
            return 1.5 * base_power
        return base_power

    def on_set_status(self, status, pokemon, setter, engine):
        if status is Status.SLP and not pokemon.is_immune_to(Type.GROUND):
            if __debug__: log.i('Electric terrain blocking %s on %s', status, pokemon)
            return FAIL

class Encore(BaseEffect):
    source = Volatile.ENCORE

    def __init__(self, move, duration):
        self.move = move
        self.duration = duration

    def override_move_choice(self):
        """ Not an event; does not override BaseEffect """
        if __debug__: log.i('Encore overriding choice with %s', self.move)
        return self.move

    @priority(0)
    def on_residual(self, pokemon, foe, engine):
        if pokemon.pp[self.move] <= 0:
            pokemon.remove_effect(Volatile.ENCORE)
            if __debug__: log.i('Ending Encore on %s because %s has no pp left', pokemon, self.move)

    def on_get_move_choices(self, pokemon, moves):
        return [self.move] if self.move in moves else []

class HealingWish(BaseEffect):
    source = SideCondition.HEALINGWISH
    duration = 2

    @priority(1)
    def on_switch_in(self, pokemon, engine):
        if pokemon.is_fainted():
            if __debug__: log.w('%s fainted before HealingWish could heal it')
            return
        engine.heal(pokemon, pokemon.max_hp)
        pokemon.cure_status()
        pokemon.side.remove_effect(SideCondition.HEALINGWISH)

class PartialTrap(BaseEffect):
    source = Volatile.PARTIALTRAP

    def __init__(self, trapper):
        self.trapper = trapper
        # 4 or 5 turns of residual effects, plus one turn of trap then release
        self.duration = random.randint(5, 6)

    def on_trap_check(self, pokemon):
        return Type.GHOST not in pokemon.types

    @priority(-11)
    def on_residual(self, pokemon, foe, engine):
        if self.trapper.is_fainted() or not self.trapper.is_active:
            pokemon.remove_effect(Volatile.PARTIALTRAP)
            return
        if __debug__: log.i("%s was hurt by PartialTrap", pokemon)
        engine.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self)

    def on_end(self, pokemon, _):  # could end by e.g. uturn or roar
        self.trapper.remove_effect(Volatile.TRAPPER)

class Trapper(BaseEffect):
    source = Volatile.TRAPPER

    def __init__(self, duration, trappee):
        self.duration = duration
        self.trappee = trappee

    def on_end(self, pokemon, _):
        """ When the trapper leaves, the trappee is no longer trapped """
        self.trappee.remove_effect(Volatile.PARTIALTRAP)
        self.trappee.remove_effect(Volatile.TRAPPED)

    @priority(0)
    def on_residual(self, pokemon, foe, engine):
        """ Handle foe batonpassing partialtrap effect """
        if (not self.trappee == foe and
            foe.has_effect(Volatile.PARTIALTRAP) and
            foe.get_effect(Volatile.PARTIALTRAP).trapper == pokemon
        ):
            self.trappee = foe

class Trapped(BaseEffect):
    source = Volatile.TRAPPED

    def __init__(self, trapper):
        self.trapper = trapper

    def on_trap_check(self, pokemon):
        return Type.GHOST not in pokemon.types

    def on_end(self, pokemon, _):  # could end by e.g. uturn or roar
        self.trapper.remove_effect(Volatile.TRAPPER)

class StallCounter(BaseEffect):
    """
    This effect is attached to a pokemon when it uses a stall move (protect, kingsshield,
    spikyshield). These moves have geometrically decreasing success probability when used in
    succession: 1/(3**n) where n is the number of times the move has succeeded consecutively.
    """
    source = Volatile.STALL
    duration = 2
    denominator = 3    # denominator of 1/X success probability

    def check_stall_success(self):
        if random.randrange(self.denominator) > 0:
            return FAIL
        self.duration = 2       # reset expiry
        self.denominator *= 3   # 3x less likely to succeed consecutively

class KingsShield(BaseEffect):
    source = Volatile.KINGSSHIELD
    duration = 1

    @priority(3)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.category is MoveCategory.STATUS or not move.is_protectable:
            return

        if move.makes_contact:
            foe.apply_boosts(Boosts(atk=-2), self_induced=False)
        return FAIL

class LeechSeed(BaseEffect):
    source = Volatile.LEECHSEED

    @priority(-8)
    def on_residual(self, pokemon, foe, engine):
        if foe is None or foe.is_fainted():
            return
        engine.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self, foe, 100)

class LightScreen(BaseEffect):
    source = SideCondition.LIGHTSCREEN

    def __init__(self, duration):
        self.duration = duration

    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if (move.category is MoveCategory.SPECIAL and
            not crit and
            not move.infiltrates and
            foe != target
        ):
            if __debug__: log.i('Light Screen halving damage from %s', move)
            return damage * 0.5
        return damage

class Reflect(BaseEffect):
    source = SideCondition.REFLECT

    def __init__(self, duration):
        self.duration = duration

    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if (move.category is MoveCategory.PHYSICAL and
            not crit and
            not move.infiltrates and
            foe != target and
            move.name != 'brickbreak'
        ):
            if __debug__: log.i('Reflect halving %s damage from %s', damage, move)
            return damage * 0.5
        return damage

class MagicBounceBase(BaseEffect):
    @priority(2)
    def on_foe_try_hit(self, foe, move, target, engine):
        if not move.is_bounceable or target == foe:
            return
        if __debug__: log.i('%s was bounced back!', move)

        suppress = (foe.ability.name == 'magicbounce')
        if suppress:
            foe.suppress_ability(engine) # Prevent infinite magicbouncing loop

        engine.use_move(target, move, foe) # Reflect the move back at the user

        if suppress:
            foe.unsuppress_ability()

        return FAIL

class MagicCoat(MagicBounceBase):
    source = Volatile.MAGICCOAT
    duration = 1

class MagnetRise(BaseEffect):
    source = Volatile.MAGNETRISE
    duration = 5

    def on_get_immunity(self, thing):
        if thing is Type.GROUND:
            return True

class LockedMove(BaseEffect):       # outrage, petaldance, etc.
    source = Volatile.LOCKEDMOVE

    def __init__(self, move):
        self.move = move
        self.duration = random.randint(2, 3) # 2 or 3 turns

    def on_get_move_choices(self, pokemon, moves):
        return [self.move]

    def on_trap_check(self, pokemon):
        return True

    @priority(0)
    def on_residual(self, pokemon, foe, engine):
        if pokemon.status is Status.SLP:
            pokemon.remove_effect(Volatile.LOCKEDMOVE)

    def on_end(self, pokemon, _):
        if (self.duration <= 1 and
            pokemon.status is not Status.SLP
            and not pokemon.is_fainted()
        ):
            pokemon.confuse(infiltrates=True)

class PerishSong(BaseEffect):
    source = Volatile.PERISHSONG
    duration = 4       # 3 moves excluding this turn

    @priority(0)
    def on_timeout(self, pokemon, engine):
        engine.faint(pokemon, Cause.DIRECT)

class Protect(BaseEffect):
    source = Volatile.PROTECT
    duration = 1

    @priority(3)
    def on_foe_try_hit(self, foe, move, target, engine):
        if not move.is_protectable:
            return
        return FAIL

class Pursuit(BaseEffect):
    source = Volatile.PURSUIT
    duration = 1

    def __init__(self, pursuiter, move):
        self.pursuiter = pursuiter
        self.move = move

    def on_switch_out(self, pokemon, incoming, engine):
        assert self.pursuiter.is_active or self.pursuiter.is_fainted()

        if not self.pursuiter.is_fainted() and not pokemon.has_effect(Volatile.BATONPASS):
            if __debug__: log.i('%s caught %s switching out with pursuit!', self.pursuiter, pokemon)
            engine.run_move(self.pursuiter, self.move, pokemon)

class Roost(BaseEffect):
    source = Volatile.ROOST
    lost_type = False
    duration = 1       # until end of turn only

    def __init__(self, pokemon):
        if Type.FLYING in pokemon.types:
            pokemon.types.remove(Type.FLYING)
            pokemon.types.append(None)
            self.lost_type = True

    def on_end(self, pokemon, _):
        if self.lost_type:
            pokemon.types[1] = Type.FLYING

class Safeguard(BaseEffect):
    source = SideCondition.SAFEGUARD
    duration = 5

    def on_set_status(self, status, pokemon, setter, engine):
        if (setter is None or
            setter != pokemon and
            setter.ability.name != 'infiltrator'
        ):
            return FAIL

    def on_foe_try_hit(self, user, move, target, engine):
        if move.name == 'yawn' and not move.infiltrates:
            return FAIL

    # confusion blocking implemented in BattlePokemon.confuse

class Spikes(BaseEffect):
    source = Hazard.SPIKES

    def __init__(self):
        self.layers = 1

    @priority(0)
    def on_switch_in(self, pokemon, engine):
        # 1, 2, 3 layers of spikes do 1/8, 1/6, 1/4 damage respectively
        if not pokemon.is_immune_to(Type.GROUND):
            if __debug__: log.i("%s was damaged by Spikes", pokemon)
            engine.damage(pokemon, pokemon.max_hp / (None, 8.0, 6.0, 4.0)[self.layers],
                          Cause.HAZARD, self)

class SpikyShield(BaseEffect):
    source = Volatile.SPIKYSHIELD
    duration = 1

    @priority(3)
    def on_foe_try_hit(self, foe, move, target, engine):
        if not move.is_protectable:
            return

        if move.makes_contact:
            engine.damage(foe, foe.max_hp / 8.0, Cause.OTHER)
        return FAIL

class StealthRock(BaseEffect):
    source = Hazard.STEALTHROCK

    @priority(0)
    def on_switch_in(self, pokemon, engine):
        if __debug__: log.i("%s was damaged by StealthRock", pokemon)
        engine.damage(pokemon, int(pokemon.max_hp / (8.0 / effectiveness(Type.ROCK, pokemon))),
                      Cause.HAZARD, self)

class StickyWeb(BaseEffect):
    source = Hazard.STICKYWEB

    @priority(0)
    def on_switch_in(self, pokemon, engine):
        if not pokemon.is_immune_to(Type.GROUND):
            if __debug__: log.i("%s was caught in the StickyWeb", pokemon)
            pokemon.apply_boosts(Boosts(spe=-1), self_induced=False)

class Substitute(BaseEffect):
    source = Volatile.SUBSTITUTE

    def __init__(self, hp):
        self.hp = hp

    def on_hit_substitute(self, foe, move, target, engine): # not an override
        """
        - Return FAIL to fail the move.
        - Return None to continue as though there was no substitute.
        - Return 0 to indicate move hit the substitute (0 damage to pokemon). In this case,
          recoil/drain is taken care of here, so move_hit can exit fast (with None damage).
        """
        if move.is_sound or move.ignore_substitute or move.infiltrates or foe is target:
            return None

        damage = engine.calculate_damage(foe, move, target)
        if damage is FAIL:
            return FAIL

        if damage is None:
            return 0

        if damage > self.hp:
            damage = self.hp
        self.hp -= damage
        if __debug__: log.i("%s's substitute took %d damage (hp=%d)", target, damage, self.hp)
        if self.hp == 0:
            if __debug__: log.i("%s's substitute faded!", target)
            target.remove_effect(Volatile.SUBSTITUTE)

        # Run the remaining relevant effects of move_hit and damage so that move_hit can exit fast
        if move.user_boosts:
            foe.apply_boosts(move.user_boosts, self_induced=True)
        elif move.recoil > 0:
            engine.damage(foe, damage * move.recoil / 100, Cause.RECOIL)
        elif move.drain:
            engine.heal(foe, int(math.ceil(damage * move.drain / 100.0)), Cause.DRAIN, move, target)
        elif move.on_success_ignores_substitute:
            move.on_success(foe, target, engine)

        if target.item is not None and target.item.name == 'airballoon':
            target.use_item(engine)

        for s_effect in move.secondary_effects:
            if s_effect.affects_user:
                engine.apply_secondary_effect(foe, s_effect, foe)

        foe.damage_done_this_turn = damage
        foe.must_switch = move.switch_user
        target.was_attacked_this_turn = {'move': move, 'damage': 0}

        return 0

class Tailwind(BaseEffect):
    source = SideCondition.TAILWIND
    duration = 4

    def on_modify_spe(self, pokemon, engine, spe):
        return 2 * spe

class Taunt(BaseEffect):
    source = Volatile.TAUNT

    def __init__(self, duration):
        self.duration = duration

    def on_get_move_choices(self, pokemon, moves):
        return [move for move in moves if move.category != MoveCategory.STATUS]

    @priority(5)
    def on_before_move(self, user, move, engine):
        if move.category == MoveCategory.STATUS:
            if __debug__: log.i("%s can't use %s because it was taunted this turn", user, move)
            return FAIL

class TrickRoom(BaseEffect):
    source = PseudoWeather.TRICKROOM
    duration = 5

    def on_modify_spe(self, pokemon, engine, spe):
        return -spe

class ToxicSpikes(BaseEffect):
    source = Hazard.TOXICSPIKES

    def __init__(self):
        self.layers = 1

    @priority(0)
    def on_switch_in(self, pokemon, engine):
        assert self.layers in (1, 2)

        if not pokemon.is_immune_to(Type.GROUND): # if pokemon is grounded
            if Type.POISON in pokemon.types:
                pokemon.side.remove_effect(Hazard.TOXICSPIKES)
                if __debug__: log.i('The toxicspikes disappeared!')
            else:
                if __debug__: log.i("%s was poisoned by ToxicSpikes", pokemon)
                engine.set_status(pokemon, Status.PSN if self.layers == 1 else Status.TOX,
                                  setter=None)

class Wish(BaseEffect):
    source = SideCondition.WISH
    duration = 2

    def __init__(self, hp):
        self.hp = hp

    @priority(-4)
    def on_timeout(self, side, engine):
        pokemon = side.active_pokemon
        if pokemon is not None and pokemon.hp < pokemon.max_hp:
            engine.heal(pokemon, self.hp)
        elif __debug__:
            log.i('Wish failed')

class Yawn(BaseEffect):
    source = Volatile.YAWN
    duration = 2

    @priority(0)
    def on_timeout(self, pokemon, engine):
        engine.set_status(pokemon, Status.SLP, setter=pokemon) # unaffected by Safeguard

class SheerForceVolatile(BaseEffect):
    """
    Acts as a flag indicating that abilitydex['sheerforce'] suppressed secondary effects this turn.
    Used in BattleEngine.use_move to detect whether to suppress after_move_secondary* handlers.
    """
    source = Volatile.SHEERFORCE
    duration = 1

    def on_modify_base_power(self, user, move, target, engine, base_power):
        return base_power * 1.3

class FlashFireVolatile(BaseEffect):
    source = Volatile.FLASHFIRE

    def on_modify_atk(self, pokemon, move, engine, atk):
        if move.type is Type.FIRE:
            if __debug__: log.i('%s boosted by FlashFire!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, engine, spa):
        if move.type is Type.FIRE:
            if __debug__: log.i('%s boosted by FlashFire!', move)
            return spa * 1.5
        return spa

class ParentalBondVolatile(BaseEffect):
    source = Volatile.PARENTALBOND
    duration = 1

    def __init__(self):
        self.first_hit = False

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if not self.first_hit:
            self.first_hit = True
            return base_power
        else:
            return base_power * 0.5

class SlowStartVolatile(BaseEffect):
    source = Volatile.SLOWSTART
    duration = 5

    def on_modify_atk(self, pokemon, move, engine, atk):
        if __debug__: log.i("%s's atk was halved by SlowStart", pokemon)
        return atk * 0.5

    def on_modify_spe(self, pokemon, engine, spe):
        if __debug__: log.d("%s's spe was halved by SlowStart", pokemon)
        return spe * 0.5

class TruantVolatile(BaseEffect):
    source = Volatile.TRUANT
    duration = 2

class GemVolatile(BaseEffect):
    source = Volatile.GEM
    duration = 1

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if __debug__: log.i("%s's power was boosted by the %s gem", move, move.type.name)
        return base_power * 1.3

class UnburdenVolatile(BaseEffect):
    source = Volatile.UNBURDEN

    def on_modify_spe(self, pokemon, engine, spe):
        if __debug__: log.d("%s's speed is boosted by Unburden", pokemon)
        return spe * 2

class Transformed(BaseEffect):
    """ Used for transform and imposter """
    source = Volatile.TRANSFORMED

    def on_end(self, pokemon, _):
        pokemon.revert_transform()
