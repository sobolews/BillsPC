from misc.functions import priority
from pokedex.baseeffect import BaseEffect
from pokedex.enums import Type, Weather, Status, FAIL, MoveCategory, Cause
from pokedex.types import type_effectiveness

if __debug__: from _logging import log

class BaseWeatherEffect(BaseEffect):
    suppressed = False

    def __init__(self, duration=5):
        self.duration = duration

    @priority(-1)
    def on_residual(self, pokemon0, pokemon1, engine):
        if not self.suppressed:
            for pokemon in filter(None, (pokemon0, pokemon1)):
                for effect in pokemon.effects:
                    effect.on_weather(pokemon, self.source, engine)

    def weather_modify_damage(self, _, damage):
        return damage

class SunnyDayWeather(BaseWeatherEffect):
    source = Weather.SUNNYDAY

    def weather_modify_damage(self, move, damage):
        if not self.suppressed:
            if move.type is Type.FIRE:
                if __debug__: log.i("%s boosted %s's power!", self, move)
                return 1.5 * damage
            if move.type is Type.WATER:
                if __debug__: log.i("%s suppressed %s's power!", self, move)
                return 0.5 * damage
        return damage

    def on_set_status(self, status, pokemon, setter, engine):
        if not self.suppressed and status is Status.FRZ:
            return FAIL

class DesolateLandWeather(BaseWeatherEffect):
    source = Weather.DESOLATELAND

    def __init__(self, duration):
        self.duration = None

    def weather_modify_damage(self, move, damage):
        if not self.suppressed and move.type is Type.FIRE:
            if __debug__: log.i("%s boosted %s's power!", self, move)
            return 1.5 * damage
        return damage

    def on_try_hit(self, user, move, target, engine):
        if (not self.suppressed and
            move.category is not MoveCategory.STATUS and
            move.type is Type.WATER
        ):
            if __debug__: log.i('But the water move evaporated!')
            return FAIL

    on_set_status = SunnyDayWeather.on_set_status.__func__

class RainDanceWeather(BaseWeatherEffect):
    source = Weather.RAINDANCE

    def weather_modify_damage(self, move, damage):
        if not self.suppressed:
            if move.type is Type.WATER:
                if __debug__: log.i("%s boosted %s's power!", self, move)
                return 1.5 * damage
            if move.type is Type.FIRE:
                if __debug__: log.i("%s suppressed %s's power!", self, move)
                return 0.5 * damage
        return damage

class PrimordialSeaWeather(BaseWeatherEffect):
    source = Weather.PRIMORDIALSEA

    def __init__(self, duration):
        self.duration = None

    def weather_modify_damage(self, move, damage):
        if not self.suppressed and move.type is Type.WATER:
            if __debug__: log.i("%s boosted %s's power!", self, move)
            return 1.5 * damage
        return damage

    def on_try_hit(self, user, move, target, engine):
        if (not self.suppressed and
            move.category is not MoveCategory.STATUS and
            move.type is Type.FIRE
        ):
            if __debug__: log.i('But the fire move fizzled out!')
            return FAIL

class HailWeather(BaseWeatherEffect):
    source = Weather.HAIL

    @priority(-1)
    def on_residual(self, pokemon0, pokemon1, engine):
        super(HailWeather, self).on_residual(pokemon0, pokemon1, engine)
        if not self.suppressed:
            for pokemon in sorted(filter(None, (pokemon0, pokemon1)),
                                  key=lambda p: -engine.effective_spe(p)):
                engine.damage(pokemon, (pokemon.max_hp / 16) or 1, Cause.WEATHER, Weather.HAIL)

class SandstormWeather(BaseWeatherEffect):
    source = Weather.SANDSTORM

    @priority(-1)
    def on_residual(self, pokemon0, pokemon1, engine):
        super(SandstormWeather, self).on_residual(pokemon0, pokemon1, engine)
        if not self.suppressed:
            for pokemon in sorted(filter(None, (pokemon0, pokemon1)),
                                  key=lambda p: -engine.effective_spe(p)):
                engine.damage(pokemon, (pokemon.max_hp / 16) or 1, Cause.WEATHER, Weather.SANDSTORM)

    def on_modify_spd(self, pokemon, move, engine, spd):
        if not self.suppressed and Type.ROCK in pokemon.types:
            if __debug__: log.i("Sandstorm boosted %s's spd!", pokemon)
            return 1.5 * spd
        return spd

class DeltaStreamWeather(BaseWeatherEffect):
    source = Weather.DELTASTREAM

    def __init__(self, duration):
        self.duration = None

    def on_modify_effectiveness(self, user, move, target, effectiveness):
        if not self.suppressed:
            if Type.FLYING in target.types and type_effectiveness(move.type, Type.FLYING) == 2:
                if __debug__:
                    log.i("DeltaStream suppressed %s's %s type move", user, move.type.name)
                return effectiveness * 0.5
        return effectiveness

WEATHER_EFFECTS = {
    Weather.RAINDANCE: RainDanceWeather,
    Weather.PRIMORDIALSEA: PrimordialSeaWeather,
    Weather.SUNNYDAY: SunnyDayWeather,
    Weather.DESOLATELAND: DesolateLandWeather,
    Weather.HAIL: HailWeather,
    Weather.SANDSTORM: SandstormWeather,
    Weather.DELTASTREAM: DeltaStreamWeather
}
