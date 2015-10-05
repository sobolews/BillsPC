"""
All abilities are implemented here, and gathered in to the `abilitydex` dictionary.
Abilities are named in CamelCase, but their .name attribute is lowercasenospaces.
"""
import inspect
import random

if __debug__: from _logging import log
from misc.functions import priority
from pokedex.baseeffect import BaseEffect
from pokedex import effects
from pokedex.enums import (Volatile, FAIL, Type, Status, Cause, MoveCategory, PseudoWeather,
                           ABILITY, Weather, POWDER)
from pokedex.stats import Boosts


class BaseAbility(object):
    class __metaclass__(type):
        def __new__(cls, name, bases, dct):
            dct['name'] = name.lower()
            return type.__new__(cls, name, bases, dct)

        def __repr__(self):
            return self.__name__

    source = ABILITY

class AbilityEffect(BaseAbility, BaseEffect):
    pass

class Adaptability(AbilityEffect):
    def on_modify_move(self, move, user, engine):
        move.stab = 2
        if __debug__:
            if move.type in user.types:
                log.i('%s was boosted by Adaptability!', move)

class Aftermath(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if ((pokemon.hp <= 0 and # not pokemon.is_fainted() (BattleEngine.faint hasn't run yet)
             cause is Cause.MOVE and
             source.makes_contact and
             foe is not None)):
            if __debug__: log.i("%s was damaged by %s's aftermath", foe, pokemon)
            engine.damage(foe, foe.max_hp / 4, Cause.OTHER)

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
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if cause is Cause.MOVE and source.crit:
            if __debug__: log.i("Anger Point maximized %s's atk!", pokemon)
            pokemon.boosts['atk'] = 6

class ArenaTrap(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if not foe.is_immune_to(Type.GROUND) and not foe.has_effect(Volatile.TRAPPED):
            trap_effect = effects.Trapped(pokemon)
            foe.set_effect(trap_effect)
            pokemon.set_effect(effects.Trapper(duration=None, trappee=foe))

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
    @priority(26.1)
    def on_residual(self, pokemon, foe, engine):
        if pokemon.is_fainted():
            return

        if foe.status is Status.SLP:
            engine.damage(foe, foe.max_hp / 8, Cause.OTHER)

class BattleArmor(AbilityEffect):
    pass # implemented in BattleEngine.modify_critical_hit # TODO: use effect instead?

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

# class CheekPouch(AbilityEffect):
#     pass # TODO: berries

class Chlorophyll(AbilityEffect):
    def on_modify_spe(self, pokemon, engine, spe):
        if __debug__: log.i("Chlorophyll boosted %s's speed!", pokemon)
        if engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            return spe * 2
        return spe

class ClearBody(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_imposed):
        if not self_imposed:
            for stat, val in boosts.items():
                if val < 0:
                    boosts[stat] = 0
                    if __debug__: log.i("%s's %s drop was blocked by ClearBody!", pokemon, stat)
        return boosts

class CloudNine(AbilityEffect):
    on_start = AirLock.on_start
    on_end = AirLock.on_end

class Competitive(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_imposed):
        if not self_imposed:
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
    def on_boost(self, pokemon, boosts, self_imposed):
        for stat, val in boosts.items():
            boosts[stat] = -val
        return boosts

class CursedBody(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if cause is Cause.MOVE and random.randrange(10) < 3: # 30% chance
            if foe.pp.get(source):
                if __debug__: log.i('CursedBody activated!')
                foe.set_effect(effects.Disable(source, 5))

class CuteCharm(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if foe.has_effect(Volatile.ATTRACT) or foe.ability.name in ('oblivious', 'aromaveil'):
            return

        if ((foe.gender == 'M' and pokemon.gender == 'F') or
            (foe.gender == 'F' and pokemon.gender == 'M')):
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
    def on_boost(self, pokemon, boosts, self_imposed):
        if not self_imposed:
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
            engine.apply_boosts(pokemon, boosts, self_imposed=True)

class Drizzle(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.RAINDANCE)

class Drought(AbilityEffect):
    def on_start(self, pokemon, engine):
        engine.battlefield.set_weather(Weather.SUNNYDAY)

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
            engine.damage(pokemon, pokemon.max_hp / 8, Cause.OTHER)

class EarlyBird(AbilityEffect):
    @priority(11)
    def on_before_move(self, user, move, engine):
        sleep_effect = user.get_effect(Status.SLP)
        if sleep_effect is not None:
            sleep_effect.turns_left -= 1
            user.sleep_turns -= 1

class EffectSpore(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if ((cause is Cause.MOVE and
             source.makes_contact and
             foe.status is None and
             not foe.is_immune_to(POWDER))):
            rand = random.randrange(100)
            if __debug__:
                if rand < 30: log.i("%s's EffectSpore activated!", pokemon)
            if rand < 11:   # 11% chance
                engine.set_status(foe, Status.SLP)
            elif rand < 21: # 10% chance
                engine.set_status(foe, Status.PAR)
            elif rand < 30: # 9% chance
                engine.set_status(foe, Status.PSN)

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
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if ((cause is Cause.MOVE and
             source.makes_contact and
             foe.status is None and
             random.randrange(10) < 3)):
            engine.set_status(foe, Status.BRN)

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

    def on_modify_spd(self, pokemon, engine, spd):
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
    def on_modify_def(self, pokemon, engine, def_):
        return def_ * 2

class GaleWings(AbilityEffect):
    def on_modify_priority(self, pokemon, move):
        if move.type is Type.FLYING:
            return 1

class Guts(AbilityEffect):
    def on_modify_atk(self, pokemon, move, engine, atk):
        if pokemon.status not in (None, Status.FNT):
            if __debug__: log.i("%s's atk boosted by Guts!", pokemon)
            return atk * 1.5
        return atk

# class Harvest(AbilityEffect):
#     pass # TODO: berries

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
    @priority(5.1)
    def on_residual(self, pokemon, foe, engine):
        if engine.battlefield.weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            if __debug__:
                if pokemon.status is not None: log.i("%s was healed by Hydration!", pokemon)
            pokemon.cure_status()

class HyperCutter(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_imposed):
        if not self_imposed:
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
            engine.heal(pokemon, pokemon.max_hp / 16)

class Illusion(AbilityEffect):  # only used to block transform for now
    def on_start(self, pokemon, engine):
        pokemon.illusion = True

    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if cause is Cause.MOVE and pokemon is not foe:
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
            engine.apply_boosts(foe, Boosts(atk=-1), self_imposed=False)

class IronBarbs(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if ((cause is Cause.MOVE and
             source.makes_contact and
             foe is not None)):
            if __debug__: log.i("%s was damaged by %s's IronBarbs", foe, pokemon)
            engine.damage(foe, foe.max_hp / 8, Cause.OTHER)

class IronFist(AbilityEffect):
    def on_modify_base_power(self, user, move, target, engine, base_power):
        if move.is_punch:
            return base_power * 1.2
        return base_power

class Justified(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if (cause is Cause.MOVE and source.type is Type.DARK):
            engine.apply_boosts(pokemon, Boosts(atk=1), self_imposed=True)

class KeenEye(AbilityEffect):
    def on_boost(self, pokemon, boosts, self_imposed):
        if not self_imposed:
            if boosts['acc'] < 0:
                boosts['acc'] = 0
                if __debug__: log.i("%s's acc drop was blocked by KeenEye!", pokemon)
        return boosts

    def on_modify_move(self, move, user, engine):
        move.ignore_evasion = True

class Klutz(AbilityEffect):
    pass # TODO when: implement items

class Levitate(AbilityEffect):
    def on_get_immunity(self, thing):
        if thing is Type.GROUND:
            return True

class LightningRod(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.ELECTRIC:
            engine.apply_boosts(target, Boosts(spa=1), self_imposed=True)
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
    def on_damage(self, damage, cause, source):
        if cause is not Cause.MOVE:
            if __debug__: log.i('Damage from (%s, %s) was prevented by MagicGuard',
                                cause.name, source)
            return FAIL
        return damage

class Magician(AbilityEffect):
    pass # TODO when: implement items

class MagnetPull(AbilityEffect):
    def on_before_turn(self, pokemon, foe):
        if Type.STEEL in foe.types and not foe.has_effect(Volatile.TRAPPED):
            trap_effect = effects.Trapped(pokemon)
            foe.set_effect(trap_effect)
            pokemon.set_effect(effects.Trapper(duration=None, trappee=foe))

class MarvelScale(AbilityEffect):
    def on_modify_def(self, pokemon, engine, def_):
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
        if self.suppressed and not target.is_fainted() and target.is_active:
            target.unsuppress_ability()
            if __debug__: log.d("%s's %s was restored", target, target._ability)
        self.suppressed = False

MOLDS = {'aromaveil', 'battlearmor', 'bigpecks', 'bulletproof', 'clearbody', 'contrary', 'damp',
         'dryskin', 'filter', 'flashfire', 'flowergift', 'flowerveil', 'friendguard', 'furcoat',
         'heatproof', 'heavymetal', 'hypercutter', 'immunity', 'innerfocus', 'insomnia', 'keeneye',
         'leafguard', 'levitate', 'lightmetal', 'lightningrod', 'limber', 'magicbounce',
         'magmaarmor', 'marvelscale', 'motordrive', 'multiscale', 'oblivious', 'overcoat',
         'owntempo', 'sandveil', 'sapsipper', 'shellarmor', 'shielddust', 'simple', 'snowcloak',
         'solidrock', 'soundproof', 'stickyhold', 'stormdrain', 'sturdy', 'suctioncups', 'sweetveil'
         'tangledfeet', 'telepathy', 'thickfat', 'unaware', 'vitalspirit', 'voltabsorb',
         'waterabsorb', 'waterveil', 'whitesmoke', 'wonderguard', 'wonderskin'}

class MotorDrive(AbilityEffect):
    @priority(0)
    def on_foe_try_hit(self, foe, move, target, engine):
        if move.type is Type.ELECTRIC:
            engine.apply_boosts(target, Boosts(spe=1), self_imposed=True)
            return FAIL

class Moxie(AbilityEffect):
    def on_foe_faint(self, pokemon, cause, source, foe, engine):
        if cause is Cause.MOVE:
            if __debug__: log.i("%s's Moxie boosts its attack!", pokemon)
            engine.apply_boosts(pokemon, Boosts(atk=1), self_imposed=True)

class Multiscale(AbilityEffect):
    def on_modify_foe_damage(self, foe, move, target, crit, effectiveness, damage):
        if target.hp == target.max_hp:
            if __debug__: log.i('Damage reduced by Multiscale!')
            return damage * 0.5
        return damage

class Multitype(AbilityEffect):
    pass # TODO when: implement plates

class Mummy(AbilityEffect):
    def on_after_damage(self, engine, pokemon, damage, cause, source, foe):
        if ((cause is Cause.MOVE and
             source.makes_contact and
             foe is not None)):
            if __debug__: log.i("%s's ability was changed to Mummy!", foe)
            foe.change_ability(Mummy)

class NaturalCure(AbilityEffect):
    def on_switch_out(self, pokemon, engine):
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
        if ((move.category is not MoveCategory.STATUS and
             not move.is_two_turn and
             not move.multihit and
             not move.selfdestruct)):
            move.multihit = (2,)
            user.set_effect(effects.ParentalBondVolatile())

class Pickpocket(AbilityEffect):
    pass




class Oblivious(AbilityEffect):
    pass

class Pressure(AbilityEffect):
    pass

class QuickFeet(AbilityEffect):
    pass

class Scrappy(AbilityEffect):
    pass # TODO: see BattleEngine.ignore_immunity

class ShellArmor(AbilityEffect):
    pass

class SkillLink(AbilityEffect):
    pass

class Sniper(AbilityEffect):
    pass

class Steadfast(AbilityEffect):
    @priority(20) # must be higher than Flinch
    def on_before_move(self, user, move, engine):
        if user.has_effect(Volatile.FLINCH):
            engine.apply_boosts(user, Boosts(spe=1), self_imposed=False)

class StickyHold(AbilityEffect):
    pass # TODO: on_try_take_item event

class SuperLuck(AbilityEffect):
    pass

class Unaware(AbilityEffect):
    pass

class Unburden(AbilityEffect):
    pass


class _suppressed_(AbilityEffect):
    pass

class _none_(AbilityEffect):
    pass

abilitydex = {obj.__name__.lower(): obj for obj in vars().values() if
              inspect.isclass(obj) and
              issubclass(obj, BaseAbility) and
              obj not in (AbilityEffect, AbilityEffect) and
              'Base' not in obj.__name__}
