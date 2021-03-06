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
from battle.baseeffect import BaseEffect
from battle import effects
from battle.enums import (Volatile, FAIL, Type, Status, Cause, MoveCategory, PseudoWeather,
                          ABILITY, Weather, POWDER)
from battle.secondaryeffect import SecondaryEffect
from battle.stats import Boosts
from battle.types import type_effectiveness


class BaseAbility(object):
    source = ABILITY
    started = False

    def on_start(self, pokemon, battle):
        """ Called when the effect is set (abilities only) """

    def start(self, pokemon, battle):
        if not self.started:
            self.on_start(pokemon, battle)
            self.started = True

class AbilityEffect(BaseAbility, BaseEffect):
    pass

class Adaptability(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        move.stab = 2
        if __debug__:
            if move.type in user.types:
                log.i('%s was boosted by Adaptability!', move)

class Aftermath(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        # not using pokemon.is_fainted() as Battle.faint hasn't run yet
        if pokemon.hp <= 0 and move.makes_contact and not foe.is_fainted():
            if __debug__: log.i("%s was damaged by %s's Aftermath", foe, pokemon)
            battle.damage(foe, foe.max_hp / 4.0, Cause.OTHER)

class Aerilate(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.type is Type.NORMAL:
            move.type = Type.FLYING
            move.type_changed = True

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.type_changed and move.type is Type.FLYING:
            if __debug__: log.i('%s boosted by Aerilate!', move)
            return base_power * 1.3
        return base_power

class AirLock(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.suppress_weather()

    def on_end(self, pokemon, battle):
        battle.battlefield.unsuppress_weather()

class Analytic(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if not target.will_move_this_turn:
            if __debug__: log.i('%s boosted by Analytic!', move)
            return base_power * 1.3
        return base_power

class AngerPoint(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if move.crit:
            if __debug__: log.i("Anger Point maximized %s's atk!", pokemon)
            pokemon.boosts['atk'] = 6

class ArenaTrap(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if not foe.is_immune_to(Type.GROUND) and not foe.has_effect(Volatile.TRAPPED):
            foe.set_effect(effects.Trapped())

class AromaVeil(AbilityEffect):
    BLOCKS = {'attract', 'disable', 'encore', 'healblock', 'taunt', 'torment'}

    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.name in self.BLOCKS:
            if __debug__: log.i('%s was blocked by AromaVeil', move)
            return FAIL

class AuraBreak(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_effect(effects.AuraBreakFieldEffect())

    def on_end(self, pokemon, battle):
        battle.battlefield.remove_effect(PseudoWeather.AURABREAK)

class BadDreams(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, battle):
        if pokemon.is_fainted() or foe is None:
            return

        if foe.status is Status.SLP:
            if __debug__: log.i("%s is hurt by %s's BadDreams", foe, pokemon)
            battle.damage(foe, foe.max_hp / 8.0, Cause.OTHER)

class BattleArmor(AbilityEffect):
    pass # implemented in Battle.modify_critical_hit

class Blaze(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        if move.type is Type.FIRE and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Blaze!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, battle, spa):
        if move.type is Type.FIRE and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Blaze!', move)
            return spa * 1.5
        return spa

class BulletProof(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.is_bullet:
            if __debug__: log.i('%s was blocked by BulletProof!', move)
            return FAIL

class CheekPouch(AbilityEffect):
    def on_use_item(self, pokemon, item, battle):
        if item.is_berry:
            if __debug__: log.i("%s is healed by its CheekPouch", pokemon)
            battle.heal(pokemon, pokemon.max_hp / 3)

class Chlorophyll(AbilityEffect):
    def on_modify_spe(self, pokemon, battle, spe):
        if battle.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.d("Chlorophyll boosted %s's speed!", pokemon)
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
    on_start = AirLock.on_start.__func__
    on_end = AirLock.on_end.__func__

class Competitive(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            for stat, val in boosts.items():
                if val < 0:
                    boosts['spa'] += 2
                    if __debug__: log.i('Competitive boost! (from %s %s)', stat, val)
        return boosts

class CompoundEyes(AbilityEffect):
    def on_modify_move(self, move, user, battle):
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
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if not foe.is_fainted() and random.randrange(10) < 3: # 30% chance
            if foe.pp.get(move):
                if __debug__: log.i('CursedBody activated!')
                foe.set_effect(effects.Disable(move, 5))

class CuteCharm(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if (not move.makes_contact or
            foe.has_effect(Volatile.ATTRACT) or
            foe.is_fainted() or
            foe.ability.name in ('oblivious', 'aromaveil') or
            not ((foe.gender == 'M' and pokemon.gender == 'F') or
                 (foe.gender == 'F' and pokemon.gender == 'M')) or
            random.randrange(10) >= 3
        ):
            return

        if __debug__: log.i('CuteCharm caused %s to be attracted to %s!', foe, pokemon)
        foe.set_effect(effects.Attract(pokemon))

class DarkAura(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_effect(effects.DarkAuraFieldEffect())

    def on_end(self, pokemon, battle):
        battle.battlefield.remove_effect(PseudoWeather.DARKAURA)

class Defeatist(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        if pokemon.hp <= pokemon.max_hp / 2:
            return 0.5 * atk
        return atk

    def on_modify_spa(self, pokemon, move, battle, spa):
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
    def on_start(self, pokemon, battle):
        battle.battlefield.set_weather(Weather.DELTASTREAM)

    def on_end(self, pokemon, battle):
        if battle.battlefield.weather is not Weather.DELTASTREAM:
            return
        foe = battle.get_foe(pokemon)
        if foe is not None and foe.ability is not DeltaStream:
            battle.battlefield.clear_weather()

class DesolateLand(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_weather(Weather.DESOLATELAND)

    def on_end(self, pokemon, battle):
        if battle.battlefield.weather is not Weather.DESOLATELAND:
            return
        foe = battle.get_foe(pokemon)
        if foe is not None and foe.ability is not DesolateLand:
            battle.battlefield.clear_weather()

class Download(AbilityEffect):
    def on_start(self, pokemon, battle):
        foe = battle.get_foe(pokemon)
        if foe is not None:
            # foe stat calculation: boosted but not modified
            boosts = (Boosts(spa=1) if foe.calculate_stat('def') >= foe.calculate_stat('spd') else
                      Boosts(atk=1))
            if __debug__: log.i("%s is boosted by its Download!", pokemon)
            pokemon.apply_boosts(boosts, self_induced=True)

class Drizzle(AbilityEffect):
    def on_start(self, pokemon, battle):
        duration = 8 if (pokemon.item is not None and pokemon.item.name == 'damprock') else 5
        battle.battlefield.set_weather(Weather.RAINDANCE, duration)

class Drought(AbilityEffect):
    def on_start(self, pokemon, battle):
        duration = 8 if (pokemon.item is not None and pokemon.item.name == 'heatrock') else 5
        battle.battlefield.set_weather(Weather.SUNNYDAY, duration)

class DrySkin(AbilityEffect):
    # Fire vulnerability implemented in Battle.modify_base_power
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.WATER:
            if __debug__: log.i('%s was healed by its DrySkin', target)
            battle.heal(target, target.max_hp / 4)
            return FAIL

    def on_weather(self, pokemon, weather, battle):
        if weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            battle.heal(pokemon, pokemon.max_hp / 8)
        elif weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            battle.damage(pokemon, pokemon.max_hp / 8.0, Cause.OTHER)

class EarlyBird(AbilityEffect):
    @priority(11)
    def on_before_move(self, user, move, battle):
        if user.status == Status.SLP:
            user.turns_slept += 1

class EffectSpore(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if (move.makes_contact and
            foe.status is None and
            not foe.is_fainted() and
            not foe.is_immune_to(POWDER)
        ):
            rand = random.randrange(100)
            if __debug__:
                if rand < 30: log.i("%s's EffectSpore activated!", pokemon)
            if rand < 11:   # 11% chance
                battle.set_status(foe, Status.SLP, pokemon)
            elif rand < 21: # 10% chance
                battle.set_status(foe, Status.PAR, pokemon)
            elif rand < 30: # 9% chance
                battle.set_status(foe, Status.PSN, pokemon)

class FairyAura(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_effect(effects.FairyAuraFieldEffect())

    def on_end(self, pokemon, battle):
        battle.battlefield.remove_effect(PseudoWeather.FAIRYAURA)

class Filter(AbilityEffect):
    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if effectiveness > 1:
            if __debug__: log.i('Damage reduced by Filter!')
            return damage * 0.75
        return damage

class FlameBody(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if (move.makes_contact and
            not foe.is_fainted() and
            random.randrange(10) < 3
        ):
            if __debug__: log.i("%s was burned by %s's FlameBody", foe, pokemon)
            battle.set_status(foe, Status.BRN, pokemon)

class FlashFire(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.FIRE:
            target.set_effect(effects.FlashFireVolatile())
            return FAIL

class FlowerGift(AbilityEffect):
    # NOTE: there is no difference between the cherrim formes, so forme change is ignored
    def on_modify_atk(self, pokemon, move, battle, atk):
        if battle.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.i('%s boosted by FlowerGift!', move)
            return atk * 1.5
        return atk

    def on_modify_spd(self, pokemon, move, battle, spd):
        if battle.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.i("%s's spd boosted by FlowerGift", pokemon)
            return spd * 1.5
        return spd

class FlowerVeil(AbilityEffect): # no effect in randbats
    pass

class Forecast(AbilityEffect):
    FORMES = {
        Weather.SUNNYDAY: 'castformsunny',
        Weather.DESOLATELAND: 'castformsunny',
        Weather.RAINDANCE: 'castformrainy',
        Weather.PRIMORDIALSEA: 'castformrainy',
        Weather.HAIL: 'castformsnowy',
        Weather.SANDSTORM: 'castform',
        None: 'castform'
    }

    def on_update(self, pokemon, battle):
        if pokemon.base_species != 'castform':
            return

        new_forme = self.FORMES[battle.battlefield.weather]
        if pokemon.name != new_forme:
            pokemon.forme_change(new_forme)
            pokemon.set_effect(effects.ForecastForme())

class Frisk(AbilityEffect): # client only
    pass

class FurCoat(AbilityEffect):
    def on_modify_def(self, pokemon, move, battle, def_):
        return def_ * 2

class GaleWings(AbilityEffect):
    def on_modify_priority(self, pokemon, move, battle, priority):
        if move.type is Type.FLYING:
            return priority + 1
        return priority

class Guts(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        if pokemon.status not in (None, Status.FNT):
            if __debug__: log.i("%s's atk boosted by Guts!", pokemon)
            return atk * 1.5
        return atk

class Harvest(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, battle):
        if (pokemon.item is None and
            pokemon.last_berry_used is not None and
            (battle.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND) or
             random.randrange(2) == 0)
        ):
            if __debug__: log.i("%s harvested a %s!", pokemon, pokemon.last_berry_used)
            pokemon.set_item(pokemon.last_berry_used)

class Healer(AbilityEffect):
    pass # no effect

class HugePower(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        return atk * 2

class Hustle(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.accuracy is not None and move.category is MoveCategory.PHYSICAL:
            move.accuracy *= 0.8
            if __debug__: log.d("%s's accuracy decreased to %s by Hustle",
                                move, move.accuracy)

    def on_modify_atk(self, pokemon, move, battle, atk):
        if move.category is MoveCategory.PHYSICAL:
            if __debug__: log.i("%s's atk boosted by Hustle!", pokemon)
            return atk * 1.5
        return atk

class Hydration(AbilityEffect):
    @priority(-5.1)
    def on_residual(self, pokemon, foe, battle):
        if battle.battlefield.weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
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

    def on_weather(self, pokemon, weather, battle):
        if weather is Weather.HAIL:
            if __debug__: log.i("%s was healed by its IceBody", pokemon)
            battle.heal(pokemon, pokemon.max_hp / 16)

class Illusion(AbilityEffect):  # only used to block transform for now
    def on_start(self, pokemon, battle):
        pokemon.illusion = True

    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        pokemon.illusion = False

    def on_end(self, pokemon, battle):
        pokemon.illusion = False

class Immunity(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing in (Status.PSN, Status.TOX):
            return True

    def on_update(self, pokemon, battle):
        if pokemon.status in (Status.PSN, Status.TOX):
            pokemon.cure_status()

class Imposter(AbilityEffect):
    def on_start(self, pokemon, battle):
        foe = battle.get_foe(pokemon)
        if foe is None:
            if __debug__: log.d("%s's Imposter: couldn't transform", pokemon)
            return FAIL

        if pokemon.transform_into(foe, battle) is not FAIL:
            pokemon.set_effect(effects.Transformed())

class Infiltrator(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        move.infiltrates = True

class InnerFocus(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Volatile.FLINCH:
            return True

class Insomnia(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Status.SLP:
            return True

    def on_update(self, pokemon, battle):
        if pokemon.status is Status.SLP:
            pokemon.cure_status()

class Intimidate(AbilityEffect):
    def on_start(self, pokemon, battle):
        foe = battle.get_foe(pokemon)
        if foe is not None:
            if __debug__: log.i("%s intimidates its foe!", pokemon)
            foe.apply_boosts(Boosts(atk=-1), self_induced=False)

class IronBarbs(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if move.makes_contact and not foe.is_fainted():
            if __debug__: log.i("%s was damaged by %s's IronBarbs", foe, pokemon)
            battle.damage(foe, foe.max_hp / 8.0, Cause.OTHER)

class IronFist(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.is_punch:
            return base_power * 1.2
        return base_power

class Justified(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if move.type is Type.DARK and pokemon.hp > 0: # not using pokemon.is_fainted()
            if __debug__: log.i("%s's Justified raises its atk!", pokemon)
            pokemon.apply_boosts(Boosts(atk=1), self_induced=True)

class KeenEye(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        if not self_induced:
            if boosts['acc'] < 0:
                boosts['acc'] = 0
                if __debug__: log.i("%s's acc drop was blocked by KeenEye!", pokemon)
        return boosts

    def on_modify_move(self, move, user, battle):
        move.ignore_evasion_boosts = True

class Klutz(AbilityEffect):
    pass

class Levitate(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Type.GROUND:
            return True

class LightningRod(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.ELECTRIC:
            if __debug__: log.i("%s's LightningRod raises its SpA!", target)
            target.apply_boosts(Boosts(spa=1), self_induced=True)
            return FAIL

class Limber(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Status.PAR:
            return True

    def on_update(self, pokemon, battle):
        if pokemon.status is Status.PAR:
            pokemon.cure_status()

class LiquidOoze(AbilityEffect):
    def on_foe_heal(self, foe, hp, cause, battle):
        if cause is Cause.DRAIN:
            if __debug__: log.i('%s was hurt by LiquidOoze', foe)
            battle.damage(foe, hp, Cause.OTHER)
            return FAIL

class MagicBounce(effects.BaseMagicBounce, BaseAbility):
    source = ABILITY

class MagicGuard(AbilityEffect):
    @priority(0)
    def on_damage(self, pokemon, cause, source, battle, damage):
        if cause not in (Cause.MOVE, Cause.CONFUSE):
            if __debug__: log.i('Damage from (%s, %s) was prevented by MagicGuard',
                                cause, source)
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
            foe.set_effect(effects.Trapped())

class MarvelScale(AbilityEffect):
    def on_modify_def(self, pokemon, move, battle, def_):
        if pokemon.status is not None:
            if __debug__: log.i("%s's defense was boosted by MarvelScale", pokemon)
            return def_ * 1.5
        return def_

class MegaLauncher(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.is_pulse:
            if __debug__: log.i('%s was boosted by MegaLauncher!', move)
            return base_power * 1.5
        return base_power

class MoldBreaker(AbilityEffect):
    suppressed = None

    def on_break_mold(self, target, battle):
        if target.ability.name in MOLDS:
            self.suppressed = True
            target.suppress_ability(battle)
            if __debug__: log.d("%s's %s was suppressed by moldbreaker", target, target.ability)
        else:
            self.suppressed = False

    def on_unbreak_mold(self, target):
        if self.suppressed and target is not None:
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
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.ELECTRIC:
            if __debug__: log.i("%s's MotorDrive raises its speed!", target)
            target.apply_boosts(Boosts(spe=1), self_induced=True)
            return FAIL

class Moxie(AbilityEffect):
    def on_foe_faint(self, pokemon, cause, source, foe, battle):
        if cause is Cause.MOVE:
            if __debug__: log.i("%s's Moxie boosts its attack!", pokemon)
            pokemon.apply_boosts(Boosts(atk=1), self_induced=True)

class Multiscale(AbilityEffect):
    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if target.hp == target.max_hp:
            if __debug__: log.i('Damage reduced by Multiscale!')
            return damage * 0.5
        return damage

class Multitype(AbilityEffect):
    def on_start(self, pokemon, battle):
        if pokemon.item is not None:
            pokemon.types = [pokemon.item.plate_type or Type.NORMAL, None]

class Mummy(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if move.makes_contact and not foe.is_fainted():
            if __debug__: log.i("%s's ability was changed to Mummy!", foe)
            foe.change_ability(Mummy, battle)

class NaturalCure(AbilityEffect):
    @priority(0)
    def on_switch_out(self, pokemon, incoming, battle):
        pokemon.cure_status()

class NoGuard(AbilityEffect):
    def on_accuracy(self, foe, move, target, battle, accuracy):
        return None

    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        return None

class Overcoat(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing in (Weather.HAIL, Weather.SANDSTORM, POWDER):
            if __debug__: log.d('%s damage prevented by Overcoat', thing)
            return True

    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.is_powder:
            if __debug__: log.i('%s was blocked by Overcoat!', move)
            return FAIL

class Overgrow(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        if move.type is Type.GRASS and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Overgrow!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, battle, spa):
        if move.type is Type.GRASS and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Overgrow!', move)
            return spa * 1.5
        return spa

class OwnTempo(AbilityEffect):
    def on_update(self, pokemon, battle):
        if pokemon.has_effect(Volatile.CONFUSE):
            if __debug__: log.i("%s's OwnTempo cured its confusion!", pokemon)
            pokemon.remove_effect(Volatile.CONFUSE)

    def on_get_immunity(self, thing):
        if thing is Volatile.CONFUSE:
            if __debug__: log.i("OwnTempo prevented confusion!")
            return True

class ParentalBond(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if (move.category is not MoveCategory.STATUS and
            not move.is_two_turn and
            not move.multihit and
            not move.selfdestruct
        ):
            move.multihit = (2,)
            user.set_effect(effects.ParentalBondVolatile())

class Pickpocket(AbilityEffect):
    def on_after_foe_move_secondary(self, foe, move, target, battle):
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
    def on_residual(self, pokemon, foe, battle):
        if foe is None:
            return
        foe_item = foe.item_used_this_turn
        if (foe_item is not None and
            pokemon.item is None and
            foe_item.name != 'airballoon'
        ):
            if __debug__: log.i("%s found a %s!", pokemon, foe_item)
            pokemon.set_item(foe_item)

class Pixilate(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.type is Type.NORMAL:
            move.type = Type.FAIRY
            move.type_changed = True

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.type_changed and move.type is Type.FAIRY:
            if __debug__: log.i('%s boosted by Pixilate!', move)
            return base_power * 1.3
        return base_power

class PoisonHeal(AbilityEffect):
    @priority(0)
    def on_damage(self, pokemon, cause, source, battle, damage):
        if cause is Cause.RESIDUAL and source.source in (Status.PSN, Status.TOX):
            if __debug__: log.i("%s was healed by its PoisonHeal", pokemon)
            battle.heal(pokemon, pokemon.max_hp / 8)
            return FAIL
        return damage

class PoisonTouch(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.makes_contact:
            move.secondary_effects += SecondaryEffect(30, status=Status.PSN),

class Prankster(AbilityEffect):
    def on_modify_priority(self, pokemon, move, battle, priority):
        if move.category is MoveCategory.STATUS:
            return priority + 1
        return priority

class Pressure(AbilityEffect):
    pass # implemented in BattlePokemon.deduct_pp

class PrimordialSea(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_weather(Weather.PRIMORDIALSEA)

    def on_end(self, pokemon, battle):
        if battle.battlefield.weather is not Weather.PRIMORDIALSEA:
            return
        foe = battle.get_foe(pokemon)
        if foe is not None and foe.ability is not PrimordialSea:
            battle.battlefield.clear_weather()

class Protean(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.type is not Type.NOTYPE:
            if __debug__: log.i("%s's type changed to %s", user, move.type)
            user.types = [move.type, None]

class PurePower(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        return atk * 2

class QuickFeet(AbilityEffect):
    # ignorance of paralysis speed drop implemented in statuses.Paralyze
    def on_modify_spe(self, pokemon, battle, spe):
        if pokemon.status is not None:
            if __debug__: log.d("%s's QuickFeet boosted its speed!", pokemon)
            return spe * 1.5
        return spe

class RainDish(AbilityEffect):
    def on_weather(self, pokemon, weather, battle):
        if weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            if __debug__: log.i('%s was healed by its RainDish!')
            battle.heal(pokemon, pokemon.max_hp / 16)

class Reckless(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.recoil:
            if __debug__: log.i('%s boosted by Reckless!', move)
            return base_power * 1.2
        return base_power

class Refrigerate(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.type is Type.NORMAL:
            move.type = Type.ICE
            move.type_changed = True

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.type_changed and move.type is Type.ICE:
            if __debug__: log.i('%s boosted by Refrigerate!', move)
            return base_power * 1.3
        return base_power

class Regenerator(AbilityEffect):
    @priority(0)
    def on_switch_out(self, pokemon, incoming, battle):
        if not pokemon.is_fainted(): # from pursuit
            if __debug__: log.i("%s was healed by its Regenerator!", pokemon)
            battle.heal(pokemon, pokemon.max_hp / 3)

class RockHead(AbilityEffect):
    @priority(0)
    def on_damage(self, pokemon, cause, source, battle, damage):
        if cause is Cause.RECOIL:
            return FAIL
        return damage

class RoughSkin(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if move.makes_contact and not foe.is_fainted():
            if __debug__: log.i("%s was damaged by %s's RoughSkin", foe, pokemon)
            battle.damage(foe, foe.max_hp / 8.0, Cause.OTHER)

class SandForce(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Weather.SANDSTORM:
            return True

    def on_modify_base_power(self, user, move, target, battle, base_power):
        if (battle.battlefield.weather is Weather.SANDSTORM and
            move.type in (Type.ROCK, Type.GROUND, Type.STEEL)
        ):
            if __debug__: log.d('%s was boosted by SandForce!', move)
            return base_power * 1.3
        return base_power

class SandRush(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Weather.SANDSTORM:
            return True

    def on_modify_spe(self, pokemon, battle, spe):
        if battle.battlefield.weather is Weather.SANDSTORM:
            if __debug__: log.d("%s's SandRush boosted its speed!", pokemon)
            return spe * 2
        return spe

class SandStream(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_weather(Weather.SANDSTORM)

class SandVeil(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Weather.SANDSTORM:
            return True

    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        if accuracy is None:
            return accuracy
        if battle.battlefield.weather is Weather.SANDSTORM:
            return accuracy * 0.8
        return accuracy

class SapSipper(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.GRASS:
            if __debug__: log.i("%s's SapSipper raises its atk!", target)
            target.apply_boosts(Boosts(atk=1), self_induced=True)
            return FAIL

class Scrappy(AbilityEffect):
    def on_modify_effectiveness(self, user, move, target, effectiveness):
        if move.type in (Type.FIGHTING, Type.NORMAL) and Type.GHOST in target.types:
            return type_effectiveness(
                move.type, target.types[not target.types.index(Type.GHOST)] or Type.NOTYPE)
        return effectiveness

class SereneGrace(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        for s_effect in move.secondary_effects:
            s_effect.chance *= 2

class ShadowTag(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if not foe.has_effect(Volatile.TRAPPED) and foe.ability is not ShadowTag:
            foe.set_effect(effects.Trapped())

class ShedSkin(AbilityEffect):
    @priority(-5.1)
    def on_residual(self, pokemon, foe, battle):
        if random.randrange(3) == 0:
            if __debug__:
                if pokemon.status is not None: log.i("%s was healed by ShedSkin!", pokemon)
            pokemon.cure_status()

class SheerForce(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if move.secondary_effects:
            move.secondary_effects = ()
            user.set_effect(effects.SheerForceVolatile())

    def on_end(self, pokemon, battle):
        pokemon.remove_effect(Volatile.SHEERFORCE)

class ShellArmor(AbilityEffect):
    pass # implemented in Battle.modify_critical_hit

class ShieldDust(AbilityEffect):
    pass # implemented in Battle.apply_secondary_effect

class Simple(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_induced):
        for stat, val in boosts.items():
            boosts[stat] = val * 2
        return boosts

class SkillLink(AbilityEffect):
    pass # implemented in Battle.try_move_hit

class SlowStart(AbilityEffect):
    def on_start(self, pokemon, battle):
        pokemon.set_effect(effects.SlowStartVolatile())

class Sniper(AbilityEffect):
    def on_modify_damage(self, user, move, effectiveness, damage):
        if move.crit:
            if __debug__: log.i("%s was boosted by %s's Sniper!", move, user)
            return damage * 1.5
        return damage

class SnowCloak(AbilityEffect):
    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        if accuracy is None:
            return accuracy
        if battle.battlefield.weather is Weather.HAIL:
            return accuracy * 0.8
        return accuracy

    def on_get_immunity(self, thing):
        if thing is Weather.HAIL:
            return True

class SnowWarning(AbilityEffect):
    def on_start(self, pokemon, battle):
        battle.battlefield.set_weather(Weather.HAIL)

class SolarPower(AbilityEffect):
    def on_weather(self, pokemon, weather, battle):
        if weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            if __debug__: log.i('%s was hurt by its SolarPower!')
            battle.damage(pokemon, pokemon.max_hp / 8.0, Cause.OTHER)

    def on_modify_spa(self, pokemon, move, battle, spa):
        if battle.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
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
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.is_sound:
            if __debug__: log.i('%s was blocked by Soundproof!', move)
            return FAIL

class SpeedBoost(AbilityEffect):
    @priority(-26.1)
    def on_residual(self, pokemon, foe, battle):
        if pokemon.turns_out > 0:
            pokemon.apply_boosts(Boosts(spe=1))

class StanceChange(AbilityEffect):
    @priority(11)
    def on_before_move(self, user, move, battle):
        assert user.base_species == 'aegislash'

        if move.name == 'kingsshield' and user.name == 'aegislashblade':
            user.forme_change('aegislash')
        elif move.category is not MoveCategory.STATUS and user.name == 'aegislash':
            user.forme_change('aegislashblade')

    @priority(0)
    def on_switch_out(self, pokemon, incoming, battle):
        if pokemon.name == 'aegislashblade':
            pokemon.forme_change('aegislash')

class Static(AbilityEffect):
    def on_after_move_damage(self, battle, pokemon, damage, move, foe):
        if (move.makes_contact and
            foe is not None and
            not foe.is_fainted() and
            random.randrange(10) < 3
        ):
            if __debug__: log.i("%s's Static activated!", pokemon)
            battle.set_status(foe, Status.PAR, pokemon)

class Steadfast(AbilityEffect):
    @priority(8.1) # must be higher than Flinch
    def on_before_move(self, user, move, battle):
        if user.has_effect(Volatile.FLINCH):
            user.apply_boosts(Boosts(spe=1), self_induced=True)

class StickyHold(AbilityEffect):
    pass # Implemented in BattlePokemon.take_item

class StormDrain(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.WATER:
            if __debug__: log.i("%s's StormDrain raises its SpA!", target)
            target.apply_boosts(Boosts(spa=1), self_induced=True)
            return FAIL

class StrongJaw(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.is_bite:
            if __debug__: log.i("%s was boosted by StrongJaw!", move)
            return base_power * 1.5
        return base_power

class Sturdy(AbilityEffect):
    @priority(-100)
    def on_damage(self, pokemon, cause, source, battle, damage):
        if (pokemon.hp == pokemon.max_hp and
            damage >= pokemon.hp and
            cause is Cause.MOVE
        ):
            if __debug__: log.i("%s held on with Sturdy!", pokemon)
            return pokemon.hp - 1
        return damage

class SuctionCups(AbilityEffect):
    pass # Implemented in Battle.force_random_switch

class SuperLuck(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        move.crit_ratio += 1

class Swarm(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        if move.type is Type.BUG and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Swarm!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, battle, spa):
        if move.type is Type.BUG and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Swarm!', move)
            return spa * 1.5
        return spa

class SweetVeil(AbilityEffect):
    on_get_immunity = Insomnia.on_get_immunity.__func__

    on_update = Insomnia.on_update.__func__

class SwiftSwim(AbilityEffect):
    def on_modify_spe(self, pokemon, battle, spe):
        if battle.battlefield.weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            if __debug__: log.d("%s's SwiftSwim boosted its speed!", pokemon)
            return spe * 2
        return spe

class Symbiosis(AbilityEffect): # no effect in randbats
    pass

class Synchronize(AbilityEffect):
    def on_after_set_status(self, status, pokemon, setter, battle):
        if (setter is not None and
            setter != pokemon and
            status not in (Status.FRZ, Status.SLP) and
            setter.hp > 0
        ):
            if __debug__: log.i("%s's Synchronize activated!", pokemon)
            battle.set_status(setter, status, pokemon)

class TangledFeet(AbilityEffect):
    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        if accuracy is None:
            return accuracy
        if target.has_effect(Volatile.CONFUSE):
            if __debug__: log.i("%s's TangledFeet raised its evasion!", target)
            return accuracy * 0.5
        return accuracy

class Technician(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        # call move.get_base_power() to ensure the original base_power is checked
        if move.get_base_power(user, target, battle) <= 60:
            if __debug__: log.i("%s's power was boosted by Technician!", move)
            return base_power * 1.5
        return base_power

class Teravolt(AbilityEffect):
    on_break_mold = MoldBreaker.on_break_mold.__func__
    on_unbreak_mold = MoldBreaker.on_unbreak_mold.__func__

class ThickFat(AbilityEffect):
    def on_modify_def(self, pokemon, move, battle, def_):
        if move.type in (Type.FIRE, Type.ICE):
            if __debug__: log.i("Damage to %s was weakened by ThickFat", pokemon)
            return def_ * 2
        return def_

    def on_modify_spd(self, pokemon, move, battle, spd):
        if move.type in (Type.FIRE, Type.ICE):
            if __debug__: log.i("Damage to %s was weakened by ThickFat", pokemon)
            return spd * 2
        return spd

class TintedLens(AbilityEffect):
    def on_modify_damage(self, user, move, effectiveness, damage):
        if effectiveness < 1:
            return damage * 2
        return damage

class Torrent(AbilityEffect):
    def on_modify_atk(self, pokemon, move, battle, atk):
        if move.type is Type.WATER and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Torrent!', move)
            return atk * 1.5
        return atk

    def on_modify_spa(self, pokemon, move, battle, spa):
        if move.type is Type.WATER and pokemon.hp <= pokemon.max_hp / 3:
            if __debug__: log.i('%s boosted by Torrent!', move)
            return spa * 1.5
        return spa

class ToughClaws(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if move.makes_contact:
            if __debug__: log.i("%s's power was boosted by ToughClaws!", move)
            return base_power * 1.3
        return base_power

class ToxicBoost(AbilityEffect):
    def on_modify_base_power(self, user, move, target, battle, base_power):
        if (user.status in (Status.PSN, Status.TOX) and
            move.category is MoveCategory.PHYSICAL
        ):
            if __debug__: log.i("%s's power was boosted by ToxicBoost!", move)
            return base_power * 1.5
        return base_power

class Trace(AbilityEffect):
    def on_update(self, pokemon, battle):
        foe = battle.get_foe(pokemon)
        if foe is not None and foe.ability.name not in NO_TRACE:
            if __debug__: log.i("%s traced %s's %s!", pokemon, foe, foe.ability)
            pokemon.change_ability(foe.ability, battle)
            pokemon.get_effect(ABILITY).on_update(pokemon, battle)

NO_TRACE = {'flowergift', 'forecast', 'illusion', 'imposter',
            'multitype', 'stancechange', 'trace', 'zenmode'}

class Truant(AbilityEffect):
    @priority(9)
    def on_before_move(self, user, move, battle):
        if user.has_effect(Volatile.TRUANT):
            if __debug__: log.i('%s is loafing around!', user)
            return FAIL
        user.set_effect(effects.TruantVolatile())

class TurboBlaze(AbilityEffect):
    on_break_mold = MoldBreaker.on_break_mold.__func__
    on_unbreak_mold = MoldBreaker.on_unbreak_mold.__func__

class Unaware(AbilityEffect):
    def on_modify_move(self, move, user, battle):
        if __debug__: log.d("%s ignores the foe's def/spd/evn boosts", user)
        move.ignore_defensive_boosts = True
        move.ignore_evasion_boosts = True

    def on_modify_foe_move(self, move, user, battle):
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
    def on_modify_move(self, move, user, battle):
        if move.accuracy is not None:
            move.accuracy *= 1.1
            if __debug__: log.d("%s's accuracy increased to %s by VictoryStar",
                                move, move.accuracy)

class VitalSpirit(AbilityEffect):
    on_get_immunity = Insomnia.on_get_immunity.__func__

    on_update = Insomnia.on_update.__func__

class VoltAbsorb(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.ELECTRIC:
            if __debug__: log.i('%s was healed by its VoltAbsorb', target)
            battle.heal(target, target.max_hp / 4)
            return FAIL

class WaterAbsorb(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if move.type is Type.WATER:
            if __debug__: log.i('%s was healed by its WaterAbsorb', target)
            battle.heal(target, target.max_hp / 4)
            return FAIL

class WaterVeil(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Status.BRN:
            return True

    def on_update(self, pokemon, battle):
        if pokemon.status is Status.BRN:
            pokemon.cure_status()

class WhiteSmoke(AbilityEffect):
    on_boost = ClearBody.on_boost.__func__

class WonderGuard(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, battle):
        if (move.category is not MoveCategory.STATUS and
            battle.get_effectiveness(foe, move, target) <= 1 and
            move.type is not Type.NOTYPE and
            foe is not target
        ):
            if __debug__: log.i("WonderGuard makes %s immune to %s!", target, move)
            return FAIL

class WonderSkin(AbilityEffect):
    def on_foe_accuracy(self, foe, move, target, battle, accuracy):
        if accuracy is None:
            return accuracy
        if move.category is MoveCategory.STATUS and accuracy is not None:
            if __debug__: log.i("%s's accuracy is reduced by WonderSkin", move)
            return accuracy * 0.5
        return accuracy

class _suppressed_(AbilityEffect):
    pass

class _none_(AbilityEffect):
    pass

class _unrevealed_(AbilityEffect):
    def __repr__(self):
        return '(ability)'

abilitydex = {obj.__name__.lower(): obj for obj in vars().values() if
              inspect.isclass(obj) and
              issubclass(obj, BaseAbility) and
              obj is not AbilityEffect and
              'Base' not in obj.__name__}
