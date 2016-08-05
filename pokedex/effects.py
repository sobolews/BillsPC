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
                           Hazard, PseudoWeather, Decision)
from pokedex.stats import Boosts
from pokedex.types import effectiveness


class Attract(BaseEffect):
    source = Volatile.ATTRACT

    def __init__(self, mate):
        self.mate = mate

    @priority(2)
    def on_before_move(self, user, move, battle):
        if not self.mate == battle.get_foe(user):
            user.remove_effect(Volatile.ATTRACT)
            return

        if random.randrange(2):
            if __debug__: log.i('%s was immobolized by Attract!', user)
            return FAIL

class BaseAuraFieldEffect(BaseEffect):
    aura_type = None

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.type is self.aura_type:
            if __debug__: log.i("%s boosted %s's power!", self.source, move)
            if battle.battlefield.has_effect(PseudoWeather.AURABREAK):
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

    @priority(-1) # run last so that disable doesn't override
    def on_get_move_choices(self, pokemon, moves):
        return [self.move]

    def on_trap_check(self, pokemon):
        return True

class Bounce(TwoTurnMoveEffect):
    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        if ((move.name in ('thunder', 'hurricane') or
             'noguard' in (foe.ability.name, target.ability.name))):
            return None
        return 0

class PhantomForce(TwoTurnMoveEffect):
    """ Used for both phantomforce and shadowforce, since they have the same effect """
    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        if 'noguard' in (foe.ability.name, target.ability.name):
            return None
        return 0

class Autotomize(BaseEffect):
    source = Volatile.AUTOTOMIZE
    multiplier = 1
    # Weight modification is implemented in BattlePokemon.weight

CAN_BATONPASS = frozenset({
    Volatile.CONFUSE,
    Volatile.LEECHSEED,
    Volatile.MAGNETRISE,
    Volatile.PARTIALTRAP,
    Volatile.PERISHSONG,
    Volatile.SUBSTITUTE,
    Volatile.TAUNT,
})

class BatonPass(BaseEffect):
    source = Volatile.BATONPASS
    duration = 1

    @priority(0)
    def on_switch_out(self, pokemon, incoming, battle):
        incoming.boosts = pokemon.boosts
        for source, effect in pokemon._effect_index.items():
            if source in CAN_BATONPASS:
                pokemon.remove_effect(source, force=True)
                incoming.set_effect(effect, override_immunity=True)

        if __debug__: log.i('Batonpassed %s to %s',
                            filter(None, chain([incoming.boosts], incoming.effects)) or None,
                            incoming)

class ChoiceLock(BaseEffect):
    source = Volatile.CHOICELOCK

    def __init__(self, move):
        self.move = move

    @priority(0)
    def on_get_move_choices(self, pokemon, moves):
        if self.move not in pokemon.moves:
            pokemon.remove_effect(Volatile.CHOICELOCK)
            if __debug__: log.d("%s doesn't have the choiced move %s, removing choicelock",
                                pokemon, self.move)
            return moves

        if __debug__: log.d('%s is choicelocked into %s', pokemon, self.move)
        return [self.move] if self.move in moves else []

CONFUSE_PROB = [(0.5, 0.5, 0),
                (0.375, 0.375, 0.25),
                (1/3.0, 1/3.0, 1/3.0),
                (0.25, 0.25, 0.5),
                (0, 0, 1)]

class Confuse(BaseEffect):
    """
    Turn  p(hit) p(fail) p(end)
    0     0.5    0.5     0
    1     0.375  0.375   0.25
    2     0.333  0.333   0.333
    3     0.25   0.25    0.5
    4     0      0       1
    """
    source = Volatile.CONFUSE

    def __init__(self):
        self.turns_left = 4

    @priority(3)
    def on_before_move(self, user, move, battle):
        turn = 4 - self.turns_left
        if __debug__: log.i("%s's confusion: %d turns left", user, self.turns_left)
        self.turns_left -= 1

        prob = CONFUSE_PROB[turn]
        roll = random.random()
        if roll <= prob[0]:
            return
        elif roll <= prob[0] + prob[1]:
            if __debug__: log.i('%s hurt itself in its confusion', user)
            battle.confusion_hit(user)
            return FAIL
        else:
            user.remove_effect(Volatile.CONFUSE)
            if __debug__: log.i("%s's confused no more!", user)
            return

class Flinch(BaseEffect):
    source = Volatile.FLINCH
    duration = 1

    @priority(8)
    def on_before_move(self, user, move, battle):
        if __debug__: log.i('FAIL: %s flinched', user)
        return FAIL

class DestinyBond(BaseEffect):
    source = Volatile.DESTINYBOND

    @priority(100)
    def on_before_move(self, user, move, battle):
        user.remove_effect(Volatile.DESTINYBOND)

    def on_faint(self, pokemon, cause, source, battle):
        if cause is Cause.MOVE:
            foe = battle.get_foe(pokemon)
            if foe is not None:
                if __debug__: log.i('%s took its foe along with it!', pokemon)
                battle.faint(battle.get_foe(pokemon), cause=Cause.DIRECT)

class Disable(BaseEffect):
    source = Volatile.DISABLE

    def __init__(self, move, duration):
        self.move = move
        self.duration = duration

    @priority(0)
    def on_get_move_choices(self, pokemon, moves):
        return [move for move in moves if move != self.move]

    @priority(7)
    def on_before_move(self, user, move, battle):
        if move == self.move:
            if __debug__: log.i("%s can't use %s because it was disabled this turn", user, move)
            return FAIL

class ElectricTerrain(BaseEffect):
    source = PseudoWeather.ELECTRICTERRAIN
    duration = 5

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.type is Type.ELECTRIC and not user.is_immune_to(Type.GROUND):
            if __debug__: log.i('Electric terrain boosting power of %s from %s', move, user)
            return 1.5 * base_power
        return base_power

    def on_set_status(self, status, pokemon, setter, battle):
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
    def on_residual(self, pokemon, foe, battle):
        if pokemon.pp[self.move] <= 0:
            pokemon.remove_effect(Volatile.ENCORE)
            if __debug__: log.i('Ending Encore on %s because %s has no pp left', pokemon, self.move)

    @priority(0)
    def on_get_move_choices(self, pokemon, moves):
        return [self.move] if self.move in moves else []

class HealingWish(BaseEffect):
    source = SideCondition.HEALINGWISH
    duration = 2

    @priority(1)
    def on_switch_in(self, pokemon, battle):
        if pokemon.is_fainted():
            if __debug__: log.w('%s fainted before HealingWish could heal it')
            return
        battle.heal(pokemon, pokemon.max_hp)
        pokemon.cure_status()
        pokemon.side.remove_effect(SideCondition.HEALINGWISH)

class PartialTrap(BaseEffect):
    source = Volatile.PARTIALTRAP

    def __init__(self):
        # 4 or 5 turns of residual effects, plus one turn of trap then release
        # 4 turns case is handled in on_residual
        self.duration = 6

    def on_trap_check(self, pokemon):
        return Type.GHOST not in pokemon.types

    @priority(-11)
    def on_residual(self, pokemon, foe, battle):
        if __debug__: log.i("%s was hurt by PartialTrap", pokemon)
        battle.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self)
        if self.duration == 2 and random.randrange(2) == 0:
            self.duration = 1   # 4 turns

class Trapped(BaseEffect):
    source = Volatile.TRAPPED

    def on_trap_check(self, pokemon):
        return Type.GHOST not in pokemon.types

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
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.category is MoveCategory.STATUS or not move.is_protectable:
            return

        if move.makes_contact:
            foe.apply_boosts(Boosts(atk=-2), self_induced=False)
        return FAIL

class LeechSeed(BaseEffect):
    source = Volatile.LEECHSEED

    @priority(-8)
    def on_residual(self, pokemon, foe, battle):
        if foe is None or foe.is_fainted():
            return
        battle.damage(pokemon, pokemon.max_hp / 8.0, Cause.RESIDUAL, self, foe, 100)

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
    def on_foe_try_hit(self, foe, move, target, battle):
        if not move.is_bounceable or target == foe:
            return
        if __debug__: log.i('%s was bounced back!', move)

        suppress = (foe.ability.name == 'magicbounce')
        if suppress:
            foe.suppress_ability(battle) # Prevent infinite magicbouncing loop

        battle.use_move(target, move, foe) # Reflect the move back at the user

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
        self.duration = 3 # 2 or 3 turns: handled in on_residual

    @priority(-1) # must run last so that disable can't prevent prevent selection
    def on_get_move_choices(self, pokemon, moves):
        return [self.move]

    def on_trap_check(self, pokemon):
        return True

    @priority(0)
    def on_residual(self, pokemon, foe, battle):
        if pokemon.status is Status.SLP:
            pokemon.remove_effect(Volatile.LOCKEDMOVE)
        if self.duration == 2 and random.randrange(2) == 0:
            self.duration = 1   # 2 turns

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
    def on_timeout(self, pokemon, battle):
        battle.faint(pokemon, Cause.DIRECT)

class Protect(BaseEffect):
    source = Volatile.PROTECT
    duration = 1

    @priority(3)
    def on_foe_try_hit(self, foe, move, target, battle):
        if not move.is_protectable:
            return
        return FAIL

class Pursuit(BaseEffect):
    source = Volatile.PURSUIT
    duration = 1

    def __init__(self, pursuer, move):
        self.pursuer = pursuer
        self.move = move

    @priority(1)
    def on_switch_out(self, pokemon, incoming, battle):
        assert self.pursuer.is_active or self.pursuer.is_fainted()

        if (not self.pursuer.is_fainted() and
            not pokemon.has_effect(Volatile.BATONPASS) and
            not self.pursuer.has_moved_this_turn
        ):
            if __debug__: log.i('%s caught %s switching out with pursuit!', self.pursuer, pokemon)

            # mega evolve before attacking
            for event in battle.event_queue:
                if event.pokemon is self.pursuer and event.type is Decision.MEGAEVO:
                    self.pursuer.mega_evolve(battle)
                    break

            battle.run_move(self.pursuer, self.move, pokemon)
            # Don't let the pursuer move again afterwards
            battle.event_queue = [event for event in battle.event_queue
                                  if not event.pokemon is self.pursuer]

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

    def on_set_status(self, status, pokemon, setter, battle):
        if (setter is None or
            setter != pokemon and
            setter.ability.name != 'infiltrator'
        ):
            return FAIL

    def on_foe_try_hit(self, user, move, target, battle):
        if move.name == 'yawn' and not move.infiltrates:
            return FAIL

    # confusion blocking implemented in BattlePokemon.confuse

class Spikes(BaseEffect):
    source = Hazard.SPIKES

    def __init__(self):
        self.layers = 1

    @priority(0)
    def on_switch_in(self, pokemon, battle):
        # 1, 2, 3 layers of spikes do 1/8, 1/6, 1/4 damage respectively
        if not pokemon.is_immune_to(Type.GROUND):
            if __debug__: log.i("%s was damaged by Spikes", pokemon)
            battle.damage(pokemon, pokemon.max_hp / (None, 8.0, 6.0, 4.0)[self.layers],
                          Cause.HAZARD, self)

class SpikyShield(BaseEffect):
    source = Volatile.SPIKYSHIELD
    duration = 1

    @priority(3)
    def on_foe_try_hit(self, foe, move, target, battle):
        if not move.is_protectable:
            return

        if move.makes_contact:
            battle.damage(foe, foe.max_hp / 8.0, Cause.OTHER)
        return FAIL

class StealthRock(BaseEffect):
    source = Hazard.STEALTHROCK

    @priority(0)
    def on_switch_in(self, pokemon, battle):
        if __debug__: log.i("%s was damaged by StealthRock", pokemon)
        battle.damage(pokemon, pokemon.max_hp / (8.0 / effectiveness(Type.ROCK, pokemon)),
                      Cause.HAZARD, self)

class StickyWeb(BaseEffect):
    source = Hazard.STICKYWEB

    @priority(0)
    def on_switch_in(self, pokemon, battle):
        if not pokemon.is_immune_to(Type.GROUND):
            if __debug__: log.i("%s was caught in the StickyWeb", pokemon)
            pokemon.apply_boosts(Boosts(spe=-1), self_induced=False)

class Substitute(BaseEffect):
    source = Volatile.SUBSTITUTE

    def __init__(self, hp):
        self.hp = hp

    def on_hit_substitute(self, foe, move, target, battle):
        """
        - Return FAIL to fail the move.
        - Return None to continue as though there was no substitute.
        - Return 0 to indicate move hit the substitute (0 damage to pokemon). In this case,
          recoil/drain is taken care of here, so move_hit can exit fast (with None damage).
        """
        if move.is_sound or move.ignore_substitute or move.infiltrates or foe is target:
            return None

        damage = battle.calculate_damage(foe, move, target)
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
            recoil = round(damage * move.recoil / 100.0)
            if recoil > 0:
                battle.damage(foe, recoil, Cause.RECOIL)
        elif move.drain:
            battle.heal(foe, int(math.ceil(damage * move.drain / 100.0)), Cause.DRAIN, move, target)
        elif move.on_success_ignores_substitute:
            move.on_success(foe, target, battle)

        if target.item is not None and target.item.name == 'airballoon':
            target.use_item(battle)

        for s_effect in move.secondary_effects:
            if s_effect.affects_user:
                battle.apply_secondary_effect(foe, s_effect, foe)

        foe.damage_done_this_turn = damage
        foe.must_switch = move.switch_user
        target.was_attacked_this_turn = {'move': move, 'damage': 0}

        return 0

class Tailwind(BaseEffect):
    source = SideCondition.TAILWIND
    duration = 4

    def on_modify_spe(self, pokemon, battle, spe):
        return 2 * spe

class Taunt(BaseEffect):
    source = Volatile.TAUNT

    def __init__(self, duration):
        self.duration = duration

    @priority(0)
    def on_get_move_choices(self, pokemon, moves):
        return [move for move in moves if move.category != MoveCategory.STATUS]

    @priority(5)
    def on_before_move(self, user, move, battle):
        if move.category == MoveCategory.STATUS:
            if __debug__: log.i("%s can't use %s because it was taunted this turn", user, move)
            return FAIL

class TrickRoom(BaseEffect):
    source = PseudoWeather.TRICKROOM
    duration = 5

    def on_modify_spe(self, pokemon, battle, spe):
        return -spe

class ToxicSpikes(BaseEffect):
    source = Hazard.TOXICSPIKES

    def __init__(self):
        self.layers = 1

    @priority(0)
    def on_switch_in(self, pokemon, battle):
        assert self.layers in (1, 2)

        if not pokemon.is_immune_to(Type.GROUND): # if pokemon is grounded
            if Type.POISON in pokemon.types:
                pokemon.side.remove_effect(Hazard.TOXICSPIKES)
                if __debug__: log.i('The toxicspikes disappeared!')
            else:
                if __debug__: log.i("%s was poisoned by ToxicSpikes", pokemon)
                battle.set_status(pokemon, Status.PSN if self.layers == 1 else Status.TOX,
                                  setter=None)

class Wish(BaseEffect):
    source = SideCondition.WISH
    duration = 2

    def __init__(self, hp):
        self.hp = hp

    @priority(-4)
    def on_timeout(self, side, battle):
        pokemon = side.active_pokemon
        if pokemon is not None and pokemon.hp < pokemon.max_hp:
            battle.heal(pokemon, self.hp)
        elif __debug__:
            log.i('Wish failed')

class Yawn(BaseEffect):
    source = Volatile.YAWN
    duration = 2

    @priority(0)
    def on_timeout(self, pokemon, battle):
        if not pokemon.is_fainted():
            battle.set_status(pokemon, Status.SLP, setter=pokemon) # unaffected by Safeguard

class SheerForceVolatile(BaseEffect):
    """
    Acts as a flag indicating that abilitydex['sheerforce'] suppressed secondary effects this turn.
    Used in BattleEngine.use_move to detect whether to suppress after_move_secondary* handlers.
    """
    source = Volatile.SHEERFORCE
    duration = 1

    def on_modify_base_power(self, user, move, target, battle, base_power):
        return base_power * 1.3

class FlashFireVolatile(BaseEffect):
    source = Volatile.FLASHFIRE

    def on_modify_atk(self, pokemon, move, battle, atk):
        if move.type is Type.FIRE:
            if __debug__: log.i('%s boosted by FlashFire!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, battle, spa):
        if move.type is Type.FIRE:
            if __debug__: log.i('%s boosted by FlashFire!', move)
            return spa * 1.5
        return spa

class ParentalBondVolatile(BaseEffect):
    source = Volatile.PARENTALBOND
    duration = 1

    def __init__(self):
        self.first_hit = False

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if not self.first_hit:
            self.first_hit = True
            return base_power
        else:
            return base_power * 0.5

class SlowStartVolatile(BaseEffect):
    source = Volatile.SLOWSTART
    duration = 5

    def on_modify_atk(self, pokemon, move, battle, atk):
        if __debug__: log.i("%s's atk was halved by SlowStart", pokemon)
        return atk * 0.5

    def on_modify_spe(self, pokemon, battle, spe):
        if __debug__: log.d("%s's spe was halved by SlowStart", pokemon)
        return spe * 0.5

class TruantVolatile(BaseEffect):
    source = Volatile.TRUANT
    duration = 2

class GemVolatile(BaseEffect):
    source = Volatile.GEM
    duration = 1

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if __debug__: log.i("%s's power was boosted by the %s gem", move, move.type)
        return base_power * 1.3

class UnburdenVolatile(BaseEffect):
    source = Volatile.UNBURDEN

    def on_modify_spe(self, pokemon, battle, spe):
        if __debug__: log.d("%s's speed is boosted by Unburden", pokemon)
        return spe * 2

class Transformed(BaseEffect):
    """ Used for transform and imposter """
    source = Volatile.TRANSFORMED

    def on_end(self, pokemon, _):
        pokemon.revert_transform()

class PirouetteForme(BaseEffect):
    source = Volatile.PIROUETTE

    def on_end(self, pokemon, _):
        assert pokemon.base_species == 'meloetta'

        if pokemon.name == 'meloettapirouette' and not pokemon.is_fainted():
            pokemon.forme_change('meloetta')

class ForecastForme(BaseEffect):
    source = Volatile.FORECAST

    def on_end(self, pokemon, _):
        assert pokemon.base_species == 'castform'

        if pokemon.name != 'castform' and not pokemon.is_fainted():
            pokemon.forme_change('castform')
