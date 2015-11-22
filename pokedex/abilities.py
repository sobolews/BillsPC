"""
All abilities are implemented here, and gathered in to the `abilitydex` dictionary.
Abilities are named in CamelCase, but their .name attribute is lowercasenospaces.  All ability
effects call on_start when the ability is activated (i.e. by switching in) or re-activated
(i.e. through transform, trace, etc.).
"""
import inspect
import random

if __debug__: from _logging import log
from misc.functions import priority
from pokedex.baseeffect import BaseEffect
from pokedex import effects
from pokedex.enums import (Volatile, FAIL, Type, Status, Cause, MoveCategory, PseudoWeather,
                           ABILITY, Weather, POWDER)
from pokedex.secondaryeffect import SecondaryEffect
from pokedex.stats import Boosts
from pokedex.types import type_effectiveness


class BaseAbility(object):
    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            dct['name'] = name.lower()
            return type.__new__(cls, name, bases, dct)

        def __repr__(self):
            return self.__name__

    source = ABILITY
    started = False

    def on_start(self, pokemon, engine):
        """ Called when the effect is set (abilities only) """

    def start(self, pokemon, engine):
        if not self.started:
            self.on_start(pokemon, engine)
            self.started = True

    @staticmethod
    def trap(pokemon, foe):
        """ Cause `foe` to be trapped by `pokemon` """
        trap_effect = effects.Trapped(pokemon)
        foe.set_effect(trap_effect)
        pokemon.set_effect(effects.Trapper(duration=None, trappee=foe))

class AbilityEffect(BaseAbility, BaseEffect):
    pass

class Adaptability(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        move.stab = 2
        if __debug__:
            if move.type in user.types:
                log.i('%s was boosted by Adaptability!', move)

class Aftermath(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        # not using pokemon.is_fainted() as BattleEngine.faint hasn't run yet
        if pokemon.hp <= 0 and move.makes_contact:
            if __debug__: log.i("%s was damaged by %s's Aftermath", foe, pokemon)
            engine.damage(foe, foe.max_hp / 4.0, Cause.OTHER)

class Aerilate(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.type is Type.NORMAL:
            move.type = Type.FLYING
            move.type_changed = True

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.type_changed and move.type is Type.FLYING:
            if __debug__: log.i('%s boosted by Aerilate!', move)
            return base_power * 1.3
        return base_power

class AirLock(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.suppress_weather()

    def on_end(self, pokemon, engine):
        engine.battlefield.unsuppress_weather()

class Analytic(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if not target.will_move_this_turn:
            if __debug__: log.i('%s boosted by Analytic!', move)
            return base_power * 1.3
        return base_power

class AngerPoint(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if move.crit:
            if __debug__: log.i("Anger Point maximized %s's atk!", pokemon)
            pokemon.boosts['atk'] = 6

class ArenaTrap(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if not foe.is_immune_to(Type.GROUND) and not foe.has_effect(Volatile.TRAPPED):
            self.trap(pokemon, foe)

class AromaVeil(AbilityEffect):
    BLOCKS = {'attract', 'disable', 'encore', 'healblock', 'taunt', 'torment'}

    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.name in self.BLOCKS:
            if __debug__: log.i('%s was blocked by AromaVeil', move)
            return FAIL

class AuraBreak(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_effect(effects.AuraBreakFieldEffect())

    def on_end(self, pokemon, engine):
        engine.battlefield.remove_effect(PseudoWeather.AURABREAK)

class BadDreams(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, engine):
        if pokemon.is_fainted():
            return

        if foe.status is Status.SLP:
            if __debug__: log.i("%s is hurt by %s's BadDreams", foe, pokemon)
            engine.damage(foe, foe.max_hp / 8.0, Cause.OTHER)

class BattleArmor(AbilityEffect):
    pass # implemented in BattleEngine.modify_critical_hit

class Blaze(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if move.type is Type.FIRE and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Blaze!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, engine, spa):
        if move.type is Type.FIRE and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Blaze!', move)
            return spa * 1.5
        return spa

class BulletProof(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.is_bullet:
            if __debug__: log.i('%s was blocked by BulletProof!', move)
            return FAIL

class CheekPouch(AbilityEffect):
    def on_use_item(self, pokemon, item, engine):
        if item.is_berry:
            if __debug__: log.i("%s is healed by its CheekPouch", pokemon)
            engine.heal(pokemon, pokemon.max_hp / 3)

class Chlorophyll(AbilityEffect):
    def on_modify_spe(self, pokemon, engine, spe):
        if __debug__: log.i("Chlorophyll boosted %s's speed!", pokemon)
        if engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            return spe * 2
        return spe

class ClearBody(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            for stat, val in boosts.items():
                if val < 0:
                    boosts[stat] = 0
                    if __debug__: log.i("%s's %s drop was blocked by ClearBody!", pokemon, stat)
        return boosts

class CloudNine(AbilityEffect):
    on_start = AirLock.on_start
    on_end = AirLock.on_end

class Competitive(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            for stat, val in boosts.items():
                if val < 0:
                    boosts['spa'] += 2
                    if __debug__: log.i('Competitive boost! (from %s %s)', stat, val)
        return boosts

class CompoundEyes(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.accuracy is not None:
            move.accuracy *= 1.3
            if __debug__: log.d("%s's accuracy increased to %s by CompoundEyes",
                                move, move.accuracy)

class Contrary(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        for stat, val in boosts.items():
            boosts[stat] = -val
        return boosts

class CursedBody(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if random.randrange(10) < 3: # 30% chance
            if foe.pp.get(move):
                if __debug__: log.i('CursedBody activated!')
                foe.set_effect(effects.Disable(move, 5))

class CuteCharm(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if (not move.makes_contact or
            foe.has_effect(Volatile.ATTRACT) or
            foe.ability.name in ('oblivious', 'aromaveil') or
            not ((foe.gender == 'M' and pokemon.gender == 'F') or
                 (foe.gender == 'F' and pokemon.gender == 'M')) or
            random.randrange(10) >= 3
        ):
            return

        if __debug__: log.i('CuteCharm caused %s to be attracted to %s!', foe, pokemon)
        foe.set_effect(effects.Attract(pokemon))

class DarkAura(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_effect(effects.DarkAuraFieldEffect())

    def on_end(self, pokemon, engine):
        engine.battlefield.remove_effect(PseudoWeather.DARKAURA)

class Defeatist(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if pokemon.hp <= pokemon.max_hp / 2:
            return 0.5 * atk
        return atk

    def on_modify_spa(self, pokemon, move, engine, spa):
        if pokemon.hp <= pokemon.max_hp / 2:
            return 0.5 * spa
        return spa

class Defiant(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            for stat, val in boosts.items():
                if val < 0:
                    boosts['atk'] += 2
                    if __debug__: log.i('Defiant boost! (from %s %s)', stat, val)
        return boosts

class DeltaStream(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.DELTASTREAM)

    def on_end(self, pokemon, engine):
        if engine.battlefield.weather is not Weather.DELTASTREAM:
            return
        foe = engine.get_foe(pokemon)
        if foe is not None and foe.ability is not DeltaStream:
            engine.battlefield.clear_weather()

class DesolateLand(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.DESOLATELAND)

    def on_end(self, pokemon, engine):
        if engine.battlefield.weather is not Weather.DESOLATELAND:
            return
        foe = engine.get_foe(pokemon)
        if foe is not None and foe.ability is not DesolateLand:
            engine.battlefield.clear_weather()

class Download(AbilityEffect):
    def on_start(self, pokemon, engine):
        foe = engine.get_foe(pokemon)
        if foe is not None:
            # foe stat calculation: boosted but not modified
            boosts = (Boosts(spa=1) if foe.calculate_stat('def') >= foe.calculate_stat('spd') else
                      Boosts(atk=1))
            if __debug__: log.i("%s is boosted by its Download!", pokemon)
            engine.apply_boosts(pokemon, boosts, self_induced=True)

class Drizzle(AbilityEffect):
    def on_start(self, pokemon, engine):
        duration = 8 if (pokemon.item is not None and pokemon.item.name == 'damprock') else 5
        engine.battlefield.set_weather(Weather.RAINDANCE, duration)

class Drought(AbilityEffect):
    def on_start(self, pokemon, engine):
        duration = 8 if (pokemon.item is not None and pokemon.item.name == 'heatrock') else 5
        engine.battlefield.set_weather(Weather.SUNNYDAY, duration)

class DrySkin(AbilityEffect):
    # Fire vulnerability implemented in BattleEngine.modify_base_power
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.WATER:
            if __debug__: log.i('%s was healed by its DrySkin', target)
            engine.heal(target, target.max_hp / 4)
            return FAIL

    def on_weather(self, pokemon, weather, engine):
        if weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            engine.heal(pokemon, pokemon.max_hp / 8)
        elif weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            engine.damage(pokemon, pokemon.max_hp / 8.0, Cause.OTHER)

class EarlyBird(AbilityEffect):
    @priority(11)
    def on_before_move(self, user, move, engine):
        sleep_effect = user.get_effect(Status.SLP)
        if sleep_effect is not None:
            sleep_effect.turns_left -= 1
            user.sleep_turns -= 1

class EffectSpore(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if (move.makes_contact and
            foe.status is None and
            not foe.is_immune_to(POWDER)
        ):
            rand = random.randrange(100)
            if __debug__:
                if rand < 30: log.i("%s's EffectSpore activated!", pokemon)
            if rand < 11:   # 11% chance
                engine.set_status(foe, Status.SLP, pokemon)
            elif rand < 21: # 10% chance
                engine.set_status(foe, Status.PAR, pokemon)
            elif rand < 30: # 9% chance
                engine.set_status(foe, Status.PSN, pokemon)

class FairyAura(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_effect(effects.FairyAuraFieldEffect())

    def on_end(self, pokemon, engine):
        engine.battlefield.remove_effect(PseudoWeather.FAIRYAURA)

class Filter(AbilityEffect):
    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if effectiveness > 1:
            if __debug__: log.i('Damage reduced by Filter!')
            return damage * 0.75
        return damage

class FlameBody(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if (move.makes_contact and
            foe is not None and
            random.randrange(10) < 3
        ):
            if __debug__: log.i("%s was burned by %s's FlameBody", foe, pokemon)
            engine.set_status(foe, Status.BRN, pokemon)

class FlashFire(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.FIRE:
            target.set_effect(effects.FlashFireVolatile())
            return FAIL

class FlowerGift(AbilityEffect):
    # NOTE: there is no difference between the cherrim formes, so forme change is ignored
    def on_modify_atk(self, pokemon, move, engine, atk):
        if engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.i('%s boosted by FlowerGift!', move)
            return atk * 1.5
        return atk

    def on_modify_spd(self, pokemon, move, engine, spd):
        if engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.i("%s's spd boosted by FlowerGift", pokemon)
            return spd * 1.5
        return spd

class FlowerVeil(AbilityEffect): # no effect in randbats
    pass

class Forecast(AbilityEffect):
    pass # TODO: formechange

class Frisk(AbilityEffect): # client only
    pass

class FurCoat(AbilityEffect):
    def on_modify_def(self, pokemon, move, engine, def_):
        return def_ * 2

class GaleWings(AbilityEffect):
    def on_modify_priority(self, pokemon, move, engine):
        if move.type is Type.FLYING:
            return 1
        return 0

class Guts(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if pokemon.status not in (None, Status.FNT):
            if __debug__: log.i("%s's atk boosted by Guts!", pokemon)
            return atk * 1.5
        return atk

class Harvest(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, engine):
        if (pokemon.item is None and
            pokemon.last_berry_used is not None and
            (engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND) or
             random.randrange(2) == 0)
        ):
            if __debug__: log.i("%s harvested a %s!", pokemon, pokemon.last_berry_used)
            pokemon.set_item(pokemon.last_berry_used)

class HugePower(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        return atk * 2

class Hustle(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.accuracy is not None and move.category is MoveCategory.PHYSICAL:
            move.accuracy *= 0.8
            if __debug__: log.d("%s's accuracy decreased to %s by Hustle",
                                move, move.accuracy)

    def on_modify_atk(self, pokemon, move, engine, atk):
        if move.category is MoveCategory.PHYSICAL:
            if __debug__: log.i("%s's atk boosted by Hustle!", pokemon)
            return atk * 1.5
        return atk

class Hydration(AbilityEffect):
    @priority(-5.1)
    def on_residual(self, pokemon, foe, engine):
        if engine.battlefield.weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            if __debug__:
                if pokemon.status is not None: log.i("%s was healed by Hydration!", pokemon)
            pokemon.cure_status()

class HyperCutter(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            if boosts['atk'] < 0:
                if __debug__: log.i("%s's atk drop was blocked by HyperCutter!", pokemon)
                boosts['atk'] = 0
        return boosts

class IceBody(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Weather.HAIL:
            return True

    def on_weather(self, pokemon, weather, engine):
        if weather is Weather.HAIL:
            if __debug__: log.i("%s was healed by its IceBody", pokemon)
            engine.heal(pokemon, pokemon.max_hp / 16)

class Illusion(AbilityEffect):  # only used to block transform for now
    def on_start(self, pokemon, engine):
        pokemon.illusion = True

    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        pokemon.illusion = False

    def on_end(self, pokemon, engine):
        pokemon.illusion = False

class Immunity(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing in (Status.PSN, Status.TOX):
            return True

    def on_update(self, pokemon, engine):
        if pokemon.status in (Status.PSN, Status.TOX):
            pokemon.cure_status()

class Imposter(AbilityEffect):
    def on_start(self, pokemon, engine):
        foe = engine.get_foe(pokemon)
        if foe is None:
            return FAIL
        pokemon.transform_into(foe, engine)
        pokemon.set_effect(effects.Transformed())

class Infiltrator(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        move.infiltrates = True

class InnerFocus(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Volatile.FLINCH:
            return True

class Insomnia(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Status.SLP:
            return True

    def on_update(self, pokemon, engine):
        if pokemon.status is Status.SLP:
            pokemon.cure_status()

class Intimidate(AbilityEffect):
    def on_start(self, pokemon, engine):
        foe = engine.get_foe(pokemon)
        if foe is not None:
            if __debug__: log.i("%s intimidates its foe!", pokemon)
            engine.apply_boosts(foe, Boosts(atk=-1), self_induced=False)

class IronBarbs(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if move.makes_contact:
            if __debug__: log.i("%s was damaged by %s's IronBarbs", foe, pokemon)
            engine.damage(foe, foe.max_hp / 8.0, Cause.OTHER)

class IronFist(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.is_punch:
            return base_power * 1.2
        return base_power

class Justified(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if move.type is Type.DARK:
            if __debug__: log.i("%s's Justified raises its atk!", pokemon)
            engine.apply_boosts(pokemon, Boosts(atk=1), self_induced=True)

class KeenEye(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            if boosts['acc'] < 0:
                boosts['acc'] = 0
                if __debug__: log.i("%s's acc drop was blocked by KeenEye!", pokemon)
        return boosts

    def on_modify_move(self, move, user, engine):
        move.ignore_evasion_boosts = True

class Klutz(AbilityEffect):
    pass

class Levitate(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Type.GROUND:
            return True

class LightningRod(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.ELECTRIC:
            if __debug__: log.i("%s's LightningRod raises its SpA!", target)
            engine.apply_boosts(target, Boosts(spa=1), self_induced=True)
            return FAIL

class Limber(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Status.PAR:
            return True

    def on_update(self, pokemon, engine):
        if pokemon.status is Status.PAR:
            pokemon.cure_status()

class LiquidOoze(AbilityEffect):
    def on_foe_heal(self, foe, hp, cause, engine):
        if cause is Cause.DRAIN:
            if __debug__: log.i('%s was hurt by LiquidOoze', foe)
            engine.damage(foe, hp, Cause.OTHER)
            return FAIL

class MagicBounce(BaseAbility, effects.MagicBounceBase):
    pass

class MagicGuard(AbilityEffect):
    @priority(0)
    def on_damage(self, pokemon, damage, cause, source, engine):
        if cause not in (Cause.MOVE, Cause.CONFUSE):
            if __debug__: log.i('Damage from (%s, %s) was prevented by MagicGuard',
                                cause.name, source)
            return FAIL
        return damage

class Magician(AbilityEffect):
    def on_move_success(self, user, move, target):
        if move.category is not MoveCategory.STATUS and user.item is None:
            item = target.take_item()
            if item is not FAIL:
                if __debug__: log.i("%s stole %s's item!", user, target)
                user.set_item(item)

class MagnetPull(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if Type.STEEL in foe.types and not foe.has_effect(Volatile.TRAPPED):
            self.trap(pokemon, foe)

class MarvelScale(AbilityEffect):
    def on_modify_def(self, pokemon, move, engine, def_):
        if pokemon.status is not None:
            if __debug__: log.i("%s's defense was boosted by MarvelScale", pokemon)
            return def_ * 1.5
        return def_

class MegaLauncher(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.is_pulse:
            if __debug__: log.i('%s was boosted by MegaLauncher!', move)
            return base_power * 1.5
        return base_power

class MoldBreaker(AbilityEffect):
    def on_break_mold(self, target, engine):
        if target.ability.name in MOLDS:
            self.suppressed = True
            target.suppress_ability(engine)
            if __debug__: log.d("%s's %s was suppressed by moldbreaker", target, target.ability)
        else:
            self.suppressed = False

    def on_unbreak_mold(self, target):
        if self.suppressed and target is not None and target.is_active:
            target.unsuppress_ability()
            if __debug__: log.d("%s's %s was restored", target, target.ability)
        self.suppressed = False

MOLDS = {'aromaveil', 'battlearmor', 'bigpecks', 'bulletproof', 'clearbody', 'contrary', 'damp',
         'dryskin', 'filter', 'flashfire', 'flowergift', 'flowerveil', 'friendguard', 'furcoat',
         'heatproof', 'heavymetal', 'hypercutter', 'immunity', 'innerfocus', 'insomnia', 'keeneye',
         'leafguard', 'levitate', 'lightmetal', 'lightningrod', 'limber', 'magicbounce',
         'magmaarmor', 'marvelscale', 'motordrive', 'multiscale', 'oblivious', 'overcoat',
         'owntempo', 'sandveil', 'sapsipper', 'shellarmor', 'shielddust', 'simple', 'snowcloak',
         'solidrock', 'soundproof', 'stickyhold', 'stormdrain', 'sturdy', 'suctioncups',
         'sweetveil', 'tangledfeet', 'telepathy', 'thickfat', 'unaware', 'vitalspirit',
         'voltabsorb', 'waterabsorb', 'waterveil', 'whitesmoke', 'wonderguard', 'wonderskin'}

class MotorDrive(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.ELECTRIC:
            if __debug__: log.i("%s's MotorDrive raises its speed!", target)
            engine.apply_boosts(target, Boosts(spe=1), self_induced=True)
            return FAIL

class Moxie(AbilityEffect):
    def on_foe_faint(self, pokemon, cause, source, foe, engine):
        if cause is Cause.MOVE:
            if __debug__: log.i("%s's Moxie boosts its attack!", pokemon)
            engine.apply_boosts(pokemon, Boosts(atk=1), self_induced=True)

class Multiscale(AbilityEffect):
    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if target.hp == target.max_hp:
            if __debug__: log.i('Damage reduced by Multiscale!')
            return damage * 0.5
        return damage

class Multitype(AbilityEffect):
    def on_start(self, pokemon, engine):
        if pokemon.item is not None:
            pokemon.types = [pokemon.item.plate_type or Type.NORMAL, None]

class Mummy(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if move.makes_contact:
            if __debug__: log.i("%s's ability was changed to Mummy!", foe)
            foe.change_ability(Mummy, engine)

class NaturalCure(AbilityEffect):
    def on_switch_out(self, pokemon, incoming, engine):
        pokemon.cure_status()

class NoGuard(AbilityEffect):
    def on_accuracy(self, foe, move, target, engine, accuracy):
        return None

    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        return None

class Overcoat(AbilityEffect):
    def on_get_immunity(self, thing):
        if any(thing is source for source in (Weather.HAIL, Weather.SANDSTORM, POWDER)):
            if __debug__: log.d('%s damage prevented by Overcoat', thing)
            return True

    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.is_powder:
            if __debug__: log.i('%s was blocked by Overcoat!', move)
            return FAIL

class Overgrow(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if move.type is Type.GRASS and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Overgrow!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, engine, spa):
        if move.type is Type.GRASS and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Overgrow!', move)
            return spa * 1.5
        return spa

class OwnTempo(AbilityEffect):
    def on_update(self, pokemon, engine):
        if pokemon.has_effect(Volatile.CONFUSE):
            if __debug__: log.i("%s's OwnTempo cured its confusion!", pokemon)
            pokemon.remove_effect(Volatile.CONFUSE)

    def on_get_immunity(self, thing):
        if thing is Volatile.CONFUSE:
            if __debug__: log.i("OwnTempo prevented confusion!")
            return True

class ParentalBond(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if (move.category is not MoveCategory.STATUS and
            not move.is_two_turn and
            not move.multihit and
            not move.selfdestruct
        ):
            move.multihit = (2,)
            user.set_effect(effects.ParentalBondVolatile())

class Pickpocket(AbilityEffect):
    def on_after_foe_move_secondary(self, foe, move, target, engine):
        if (move.makes_contact and
            target.item is None and
            foe.item is not None
        ):
            item = foe.take_item()
            if item is not FAIL:
                if __debug__: log.i("%s stole %s's item!", target, foe)
                target.set_item(item)

class Pickup(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, engine):
        foe_item = foe.item_used_this_turn
        if (foe_item is not None and
            pokemon.item is None and
            foe_item.name != 'airballoon'
        ):
            if __debug__: log.i("%s found a %s!", pokemon, foe_item)
            pokemon.set_item(foe_item)

class Pixilate(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.type is Type.NORMAL:
            move.type = Type.FAIRY
            move.type_changed = True

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.type_changed and move.type is Type.FAIRY:
            if __debug__: log.i('%s boosted by Pixilate!', move)
            return base_power * 1.3
        return base_power

class PoisonHeal(AbilityEffect):
    @priority(0)
    def on_damage(self, pokemon, damage, cause, source, engine):
        if cause is Cause.RESIDUAL and source.source in (Status.PSN, Status.TOX):
            if __debug__: log.i("%s was healed by its PoisonHeal", pokemon)
            engine.heal(pokemon, pokemon.max_hp / 8)
            return FAIL
        return damage

class PoisonTouch(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.makes_contact:
            move.secondary_effects += SecondaryEffect(30, status=Status.PSN),

class Prankster(AbilityEffect):
    def on_modify_priority(self, pokemon, move, engine):
        if move.category is MoveCategory.STATUS:
            return 1
        return 0

class Pressure(AbilityEffect):
    pass # implemented in BattleEngine.deduct_pp

class PrimordialSea(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.PRIMORDIALSEA)

    def on_end(self, pokemon, engine):
        if engine.battlefield.weather is not Weather.PRIMORDIALSEA:
            return
        foe = engine.get_foe(pokemon)
        if foe is not None and foe.ability is not PrimordialSea:
            engine.battlefield.clear_weather()

class Protean(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.type is not Type['???']:
            if __debug__: log.i("%s's type changed to %s", user, move.type.name)
            user.types = [move.type, None]

class PurePower(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        return atk * 2

class QuickFeet(AbilityEffect):
    # ignorance of paralysis speed drop implemented in statuses.Paralyze
    def on_modify_spe(self, pokemon, engine, spe):
        if pokemon.status is not None:
            if __debug__: log.d("%s's QuickFeet boosted its speed!", pokemon)
            return spe * 1.5
        return spe

class RainDish(AbilityEffect):
    def on_weather(self, pokemon, weather, engine):
        if weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            if __debug__: log.i('%s was healed by its RainDish!')
            engine.heal(pokemon, pokemon.max_hp / 16)

class Reckless(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.recoil:
            if __debug__: log.i('%s boosted by Reckless!', move)
            return base_power * 1.2
        return base_power

class Refrigerate(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.type is Type.NORMAL:
            move.type = Type.ICE
            move.type_changed = True

    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.type_changed and move.type is Type.ICE:
            if __debug__: log.i('%s boosted by Refrigerate!', move)
            return base_power * 1.3
        return base_power

class Regenerator(AbilityEffect):
    def on_switch_out(self, pokemon, incoming, engine):
        if __debug__: log.i("%s was healed by its Regenerator!", pokemon)
        engine.heal(pokemon, pokemon.max_hp / 3)

class RockHead(AbilityEffect):
    @priority(0)
    def on_damage(self, pokemon, damage, cause, source, engine):
        if cause is Cause.RECOIL:
            return FAIL
        return damage

class RoughSkin(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if move.makes_contact:
            if __debug__: log.i("%s was damaged by %s's RoughSkin", foe, pokemon)
            engine.damage(foe, foe.max_hp / 8.0, Cause.OTHER)

class SandRush(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Weather.SANDSTORM:
            return True

    def on_modify_spe(self, pokemon, engine, spe):
        if engine.battlefield.weather is Weather.SANDSTORM:
            if __debug__: log.d("%s's SandRush boosted its speed!", pokemon)
            return spe * 2
        return spe

class SandStream(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.SANDSTORM)

class SandVeil(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Weather.SANDSTORM:
            return True

    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        if accuracy is None:
            return accuracy
        if engine.battlefield.weather is Weather.SANDSTORM:
            return accuracy * 0.8
        return accuracy

class SapSipper(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.GRASS:
            if __debug__: log.i("%s's SapSipper raises its atk!", target)
            engine.apply_boosts(target, Boosts(atk=1), self_induced=True)
            return FAIL

class Scrappy(AbilityEffect):
    def on_modify_effectiveness(self, user, move, target, effectiveness):
        if move.type in (Type.FIGHTING, Type.NORMAL) and Type.GHOST in target.types:
            return type_effectiveness(
                move.type, target.types[not target.types.index(Type.GHOST)] or Type['???'])
        return effectiveness

class SereneGrace(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        for s_effect in move.secondary_effects:
            s_effect.chance *= 2

class ShadowTag(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if not foe.has_effect(Volatile.TRAPPED) and foe.ability is not ShadowTag:
            self.trap(pokemon, foe)

class ShedSkin(AbilityEffect):
    @priority(-5.1)
    def on_residual(self, pokemon, foe, engine):
        if random.randrange(3) == 0:
            if __debug__:
                if pokemon.status is not None: log.i("%s was healed by ShedSkin!", pokemon)
            pokemon.cure_status()

class SheerForce(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.secondary_effects:
            move.secondary_effects = ()
            user.set_effect(effects.SheerForceVolatile())

class ShellArmor(AbilityEffect):
    pass # implemented in BattleEngine.modify_critical_hit

class ShieldDust(AbilityEffect):
    pass # implemented in BattleEngine.apply_secondary_effect

class Simple(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        for stat, val in boosts.items():
            boosts[stat] = val * 2
        return boosts

class SkillLink(AbilityEffect):
    pass # implemented in BattleEngine.try_move_hit

class SlowStart(AbilityEffect):
    def on_start(self, pokemon, engine):
        pokemon.set_effect(effects.SlowStartVolatile())

class Sniper(AbilityEffect):
    def on_modify_damage(self, user, move, damage, effectiveness):
        if move.crit:
            if __debug__: log.i("%s was boosted by %s's Sniper!", move, user)
            return damage * 1.5
        return damage

class SnowCloak(AbilityEffect):
    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        if accuracy is None:
            return accuracy
        if engine.battlefield.weather is Weather.HAIL:
            return accuracy * 0.8
        return accuracy

    def on_get_immunity(self, thing):
        if thing is Weather.HAIL:
            return True

class SnowWarning(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.HAIL)

class SolarPower(AbilityEffect):
    def on_weather(self, pokemon, weather, engine):
        if weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.i('%s was hurt by its SolarPower!')
            engine.damage(pokemon, pokemon.max_hp / 8.0, Cause.OTHER)

    def on_modify_spa(self, pokemon, move, engine, spa):
        if engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            return spa * 1.5
        return spa

class SolidRock(AbilityEffect):
    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if effectiveness > 1:
            if __debug__: log.i('Damage reduced by SolidRock!')
            return damage * 0.75
        return damage

class Soundproof(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.is_sound:
            if __debug__: log.i('%s was blocked by Soundproof!', move)
            return FAIL

class SpeedBoost(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, engine):
        if pokemon.turns_out > 0:
            engine.apply_boosts(pokemon, Boosts(spe=1))

class StanceChange(AbilityEffect):
    pass # TODO when: implement forme change

class Static(AbilityEffect):
    def on_after_move_damage(self, engine, pokemon, damage, move, foe):
        if (move.makes_contact and
            foe is not None and
            random.randrange(10) < 3
        ):
            if __debug__: log.i("%s's Static activated!", pokemon)
            engine.set_status(foe, Status.PAR, pokemon)

class Steadfast(AbilityEffect):
    @priority(20) # must be higher than Flinch
    def on_before_move(self, user, move, engine):
        if user.has_effect(Volatile.FLINCH):
            engine.apply_boosts(user, Boosts(spe=1), self_induced=False)

class StickyHold(AbilityEffect):
    pass # Implemented in BattlePokemon.take_item

class StormDrain(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.WATER:
            if __debug__: log.i("%s's StormDrain raises its SpA!", target)
            engine.apply_boosts(target, Boosts(spa=1), self_induced=True)
            return FAIL

class StrongJaw(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.is_bite:
            if __debug__: log.i("%s was boosted by StrongJaw!", move)
            return base_power * 1.5
        return base_power

class Sturdy(AbilityEffect):
    @priority(-100)
    def on_damage(self, pokemon, damage, cause, source, engine):
        if (pokemon.hp == pokemon.max_hp and
            damage >= pokemon.hp and
            cause is Cause.MOVE
        ):
            if __debug__: log.i("%s held on with Sturdy!", pokemon)
            return pokemon.hp - 1
        return damage

class SuctionCups(AbilityEffect):
    pass # Implemented in BattleEngine.force_random_switch

class SuperLuck(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        move.crit_ratio += 1

class Swarm(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if move.type is Type.BUG and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Swarm!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, engine, spa):
        if move.type is Type.BUG and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Swarm!', move)
            return spa * 1.5
        return spa

class SweetVeil(AbilityEffect):
    on_get_immunity = Insomnia.on_get_immunity.__func__

    on_update = Insomnia.on_update.__func__

class SwiftSwim(AbilityEffect):
    def on_modify_spe(self, pokemon, engine, spe):
        if engine.battlefield.weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            if __debug__: log.d("%s's SwiftSwim boosted its speed!", pokemon)
            return spe * 2
        return spe

class Symbiosis(AbilityEffect): # no effect in randbats
    pass

class Synchronize(AbilityEffect):
    def on_after_set_status(self, status, pokemon, setter, engine):
        if (setter is not None and
            setter != pokemon and
            status not in (Status.FRZ, Status.SLP)
        ):
            if __debug__: log.i("%s's Synchronize activated!", pokemon)
            engine.set_status(setter, status, pokemon)

class TangledFeet(AbilityEffect):
    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        if target.has_effect(Volatile.CONFUSE):
            if __debug__: log.i("%s's TangledFeet raised its evasion!", target)
            return accuracy * 0.5
        return accuracy

class Technician(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        # call move.get_base_power() to ensure the original base_power is checked
        if move.get_base_power(user, target, engine) <= 60:
            if __debug__: log.i("%s's power was boosted by Technician!", move)
            return base_power * 1.5
        return base_power

class Teravolt(AbilityEffect):
    on_break_mold = MoldBreaker.on_break_mold.__func__
    on_unbreak_mold = MoldBreaker.on_unbreak_mold.__func__

class ThickFat(AbilityEffect):
    def on_modify_def(self, pokemon, move, engine, def_):
        if move.type in (Type.FIRE, Type.ICE):
            if __debug__: log.i("Damage to %s was weakened by ThickFat", pokemon)
            return def_ * 2
        return def_

    def on_modify_spd(self, pokemon, move, engine, spd):
        if move.type in (Type.FIRE, Type.ICE):
            if __debug__: log.i("Damage to %s was weakened by ThickFat", pokemon)
            return spd * 2
        return spd

class TintedLens(AbilityEffect):
    def on_modify_damage(self, user, move, damage, effectiveness):
        if effectiveness < 1:
            return damage * 2
        return damage

class Torrent(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if move.type is Type.WATER and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Torrent!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, engine, spa):
        if move.type is Type.WATER and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Torrent!', move)
            return spa * 1.5
        return spa

class ToughClaws(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.makes_contact:
            if __debug__: log.i("%s's power was boosted by ToughClaws!", move)
            return base_power * 1.3
        return base_power

class ToxicBoost(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if (user.status in (Status.PSN, Status.TOX) and
            move.category is MoveCategory.PHYSICAL
        ):
            if __debug__: log.i("%s's power was boosted by ToxicBoost!", move)
            return base_power * 1.5
        return base_power

class Trace(AbilityEffect):
    def on_update(self, pokemon, engine):
        foe = engine.get_foe(pokemon)
        if foe is not None and foe.ability.name not in NO_TRACE:
            if __debug__: log.i("%s traced %s's %s!", pokemon, foe, foe.ability)
            pokemon.change_ability(foe.ability, engine)
            pokemon.get_effect(ABILITY).on_update(pokemon, engine)

NO_TRACE = {'flowergift', 'forecast', 'illusion', 'imposter',
            'multitype', 'stancechange', 'trace', 'zenmode'}

class Truant(AbilityEffect):
    @priority(9)
    def on_before_move(self, user, move, engine):
        if user.has_effect(Volatile.TRUANT):
            if __debug__: log.i('%s is loafing around!', user)
            return FAIL
        user.set_effect(effects.TruantVolatile())

class TurboBlaze(AbilityEffect):
    on_break_mold = MoldBreaker.on_break_mold.__func__
    on_unbreak_mold = MoldBreaker.on_unbreak_mold.__func__

class Unaware(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if __debug__: log.d("%s ignores the foe's def/spd/evn boosts", user)
        move.ignore_defensive_boosts = True
        move.ignore_evasion_boosts = True

    def on_modify_foe_move(self, move, user, engine):
        if __debug__: log.d("The foe ignores %s's atk/spa/acc boosts", user)
        move.ignore_offensive_boosts = True
        move.ignore_accuracy_boosts = True

class Unburden(AbilityEffect):
    def on_lose_item(self, pokemon, item):
        if __debug__: log.d("%s's Unburden activated!", pokemon)
        pokemon.set_effect(effects.UnburdenVolatile())

class Unnerve(AbilityEffect):
    pass

class VictoryStar(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        if move.accuracy is not None:
            move.accuracy *= 1.1
            if __debug__: log.d("%s's accuracy increased to %s by VictoryStar",
                                move, move.accuracy)

class VitalSpirit(AbilityEffect):
    on_get_immunity = Insomnia.on_get_immunity.__func__

    on_update = Insomnia.on_update.__func__

class VoltAbsorb(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.ELECTRIC:
            if __debug__: log.i('%s was healed by its VoltAbsorb', target)
            engine.heal(target, target.max_hp / 4)
            return FAIL

class WaterAbsorb(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.WATER:
            if __debug__: log.i('%s was healed by its WaterAbsorb', target)
            engine.heal(target, target.max_hp / 4)
            return FAIL

class WaterVeil(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Status.BRN:
            return True

    def on_update(self, pokemon, engine):
        if pokemon.status is Status.BRN:
            pokemon.cure_status()

class WhiteSmoke(AbilityEffect):
    on_boost = ClearBody.on_boost.__func__

class WonderGuard(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if (move.category is not MoveCategory.STATUS and
            engine.get_effectiveness(foe, move, target) <= 1 and
            move.type is not Type['???'] and
            foe is not target
        ):
            if __debug__: log.i("WonderGuard makes %s immune to %s!", target, move)
            return FAIL

class WonderSkin(AbilityEffect):
    def on_foe_accuracy(self, foe, move, target, engine, accuracy):
        if move.category is MoveCategory.STATUS and accuracy is not None:
            if __debug__: log.i("%s's accuracy is reduced by WonderSkin", move)
            return accuracy * 0.5
        return accuracy

class _suppressed_(AbilityEffect):
    pass

class _none_(AbilityEffect):
    pass

abilitydex = {obj.__name__.lower(): obj for obj in vars().values() if
              inspect.isclass(obj) and
              issubclass(obj, BaseAbility) and
              obj not in (AbilityEffect, AbilityEffect) and
              'Base' not in obj.__name__}
