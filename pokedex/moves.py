"""
All moves are implemented here, and gathered in to the `movedex` dictionary.
Moves are named with lowercasenospaces to allow direct comparison with Showdown's moves
"""
import inspect
import random

if __debug__: from _logging import log
from misc.functions import clamp_int
from pokedex import effects, statuses
from pokedex.enums import (Type, Status, Volatile, SideCondition, STATUS, PHYSICAL, SPECIAL,
                           FAIL, PseudoWeather, Cause, Weather, Hazard, Decision, ABILITY, ITEM)
from pokedex.items import itemdex
from pokedex.stats import Boosts
from pokedex.secondaryeffect import SecondaryEffect
from pokedex.types import effectiveness

_MAX_PP = {
    5: 8,
    10: 16,
    15: 24,
    20: 32,
    25: 40,
    30: 48,
    35: 56,
    40: 64
}

_WEATHER_HEAL_FACTOR = {
    Weather.SUNNYDAY: 0.667,    # yes, Showdown uses exactly float(0.667)
    Weather.DESOLATELAND: 0.667,
    Weather.RAINDANCE: 0.25,
    Weather.PRIMORDIALSEA: 0.25,
    Weather.SANDSTORM: 0.25,
    Weather.HAIL: 0.25,
    None: 0.5
}

class Move(object):
    max_pp = None
    category = None
    base_power = None
    makes_contact = False
    priority = 0
    type = None
    type_changed = False
    accuracy = None    # does not check accuracy
    crit_ratio = 0     # stages are 0, 1, 2, 3; should be just 0 or 1 for a move
    is_protectable = True
    is_punch = False
    is_sound = False
    is_bullet = False
    is_pulse = False
    is_bite = False
    is_powder = False
    is_bounceable = False
    ignore_substitute = False   # will bypass foe's substitute
    targets_user = False        # will ignore foe's substitute and can be used against an empty foe
    multihit = None    # tuple of number of hits that can be random.choice()'d
    secondary_effects = ()
    always_crit = False
    never_crit = False
    crit = False
    switch_user = False
    defensive_category = None # psyshock, psystrike, secretsword
    ignore_offensive_boosts = False  # unaware
    ignore_defensive_boosts = False  # sacredsword, unaware
    ignore_accuracy_boosts = False   # unaware
    ignore_evasion_boosts = False  # sacredsword, keeneye, unaware
    is_two_turn = False       # needed for sleeptalk
    recoil = 0 # percent of 100, or -1 to indicate recoil handled elsewhere (jumpkick etc.)
    user_boosts = None
    target_status = None
    drain = None                # percent of 100
    thaw_user = False
    thaw_target = False
    use_opponent_attack = False
    selfdestruct = False         # for explosion
    calls_other_moves = False    # sleeptalk, copycat
    on_success_ignores_substitute = False # struggle, rapidspin, brickbreak
    stab = 1.5
    is_hiddenpower = False
    infiltrates = False
    has_damage_callback = False

    def __init__(self):
        self.name = self.__class__.__name__.rstrip('_')

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self.name == other.name

    def __hash__(self):
        return hash(self.name) ^ hash(self.__class__)

    def get_base_power(self, user, target, engine):
        """ Override to return base power dynamically, else self.base_power will be used. """
        return self.base_power

    def on_success(self, user, target, engine):
        """
        Does NOT assume that user has not fainted.

        Assumes that the move has executed successfully, including doing any normal damage it would
        do. Return FAIL for move failure. WILL NOT execute if the move hits a substitute unless
        any(ignore_substitute, targets_user, on_success_ignores_substitute).

        If self.targets_user, `target` will be None.
        """

    def check_success(self, user, target, engine):
        """
        Return FAIL for move failure. If self.targets_user, `target` will be None.
        """

    def damage_callback(self, user, target): # nightshade, etc.
        """ Return exact hp damage, or None to run move normally """

    def get_effectiveness(self, target):
        """ Return a number in {0.25, 0.5, 1, 2, 4}: effectiveness multipler against target """
        return effectiveness(self.type, target)

    def on_after_move_secondary(self, user, target, engine):
        """
        A secondary effect that isn't representable by the SecondaryEffect class
        """

    def on_move_fail(self, user, engine):
        """
        Called after BattleEngine.try_move_hit fails
        """

    def on_modify_move(self, user, target, engine):
        """
        Modifies attributes of self. This should only ever be called on a copy of the move object.
        """

    def on_try_hit(self, target):
        """
        Called immediately before the immunity check and after success check in
        BattleEngine.try_move_hit.
        """

    def __repr__(self):
        return self.name

# Moves are implemented alphabetically starting here.

class acidspray(Move):
    def __init__(self):
        super(acidspray, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.base_power = 40
        self.type = Type.POISON
        self.accuracy = 100
        self.secondary_effects = SecondaryEffect(100, Boosts(spd=-2)),

class acrobatics(Move):
    def __init__(self):
        super(acrobatics, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        return 110 if user.item is None else 55

class aerialace(Move):
    def __init__(self):
        super(aerialace, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.base_power = 60
        self.makes_contact = True
        self.type = Type.FLYING

class aeroblast(Move):
    def __init__(self):
        super(aeroblast, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.base_power = 100
        self.type = Type.FLYING
        self.accuracy = 95
        self.crit_ratio = 1

class agility(Move):
    def __init__(self):
        super(agility, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spe=2)

class aircutter(Move):
    def __init__(self):
        super(aircutter, self).__init__()
        self.max_pp = _MAX_PP[25]
        self.category = SPECIAL
        self.base_power = 60
        self.type = Type.FLYING
        self.accuracy = 95
        self.crit_ratio = 1

class airslash(Move):
    def __init__(self):
        super(airslash, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.base_power = 75
        self.type = Type.FLYING
        self.accuracy = 95
        self.secondary_effects = SecondaryEffect(chance=30, volatile=Volatile.FLINCH),

class ancientpower(Move):
    def __init__(self):
        super(ancientpower, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.base_power = 60
        self.type = Type.ROCK
        self.accuracy = 100
        self.secondary_effects = SecondaryEffect(10, Boosts(atk=1, spa=1, def_=1, spd=1, spe=1),
                                                  affects_user=True),

class aquajet(Move):
    def __init__(self):
        super(aquajet, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.base_power = 40
        self.makes_contact = True
        self.priority = 1
        self.type = Type.WATER
        self.accuracy = 100

class aquatail(Move):
    def __init__(self):
        super(aquatail, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.base_power = 90
        self.makes_contact = 90
        self.type = Type.WATER
        self.accuracy = 90

class aromatherapy(Move):
    def __init__(self):
        super(aromatherapy, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.GRASS
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        for pokemon in user.side.team:
            pokemon.cure_status()

class attackorder(Move):
    def __init__(self):
        super(attackorder, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.BUG
        self.base_power = 90
        self.accuracy = 100
        self.crit_ratio = 1

class aurasphere(Move):
    def __init__(self):
        super(aurasphere, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.FIGHTING
        self.base_power = 80
        self.is_pulse = True
        self.is_bullet = True

class autotomize(Move):
    def __init__(self):
        super(autotomize, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.STEEL
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spe=2)

    def on_success(self, user, _, engine):
        effect = user.get_effect(Volatile.AUTOTOMIZE)
        if effect is None:
            user.set_effect(effects.Autotomize())
        else:
            effect.multiplier += 1

class avalanche(Move):
    def __init__(self):
        super(avalanche, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.ICE
        self.priority = -4
        self.makes_contact = True
        self.accuracy = 100

    def get_base_power(self, user, target, engine):
         # TODO: test this more thoroughly! (esp. with tricky abilities)
        if (user.was_attacked_this_turn is not None and
            user.was_attacked_this_turn['damage'] > 0
        ):
            return 120
        return 60

class batonpass(Move):
    def __init__(self):
        super(batonpass, self).__init__()
        self.max_pp = _MAX_PP[40]
        self.category = STATUS
        self.type = Type.NORMAL
        self.switch_user = True
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if not engine.get_switch_choices(user.side, user, forced=True):
            return FAIL # no possible switches

    def on_success(self, user, _, engine):
        user.set_effect(effects.BatonPass())

class bellydrum(Move):
    def __init__(self):
        super(bellydrum, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if not (user.hp > user.max_hp // 2 and
                user.boosts['atk'] < 6 and
                user.max_hp > 1):
            return FAIL

    def on_success(self, user, _, engine):
        if __debug__: log.i('%s cut its hp and maximized its attack!', user)
        engine.direct_damage(user, user.max_hp // 2)
        user.boosts['atk'] = 6

class bite(Move):
    def __init__(self):
        super(bite, self).__init__()
        self.max_pp = _MAX_PP[25]
        self.accuracy = 100
        self.base_power = 60
        self.category = PHYSICAL
        self.type = Type.DARK
        self.makes_contact = True
        self.is_bite = True
        self.secondary_effects = SecondaryEffect(30, volatile=Volatile.FLINCH),

class blazekick(Move):
    def __init__(self):
        super(blazekick, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 85
        self.secondary_effects = SecondaryEffect(10, status=Status.BRN),
        self.crit_ratio = 1

class blizzard(Move):
    def __init__(self):
        super(blizzard, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.ICE
        self.base_power = 110
        self.secondary_effects = SecondaryEffect(10, status=Status.FRZ),

    def on_modify_move(self, user, target, engine):
        if engine.battlefield.weather is Weather.HAIL:
            self.accuracy = None
        else:
            self.accuracy = 70

class blueflare(Move):
    def __init__(self):
        super(blueflare, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 85
        self.base_power = 130
        self.secondary_effects = SecondaryEffect(20, status=Status.BRN),

class bodyslam(Move):
    def __init__(self):
        super(bodyslam, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 85
        self.secondary_effects = SecondaryEffect(30, status=Status.PAR),

class boltstrike(Move):
    def __init__(self):
        super(boltstrike, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.ELECTRIC
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 130
        self.secondary_effects = SecondaryEffect(20, status=Status.PAR),

class bonemerang(Move):
    def __init__(self):
        super(bonemerang, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GROUND
        self.accuracy = 90
        self.base_power = 50
        self.multihit = (2,)

class boomburst(Move):
    def __init__(self):
        super(boomburst, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 140
        self.is_sound = True

class bounce(Move):
    def __init__(self):
        super(bounce, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FLYING
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 85
        self.is_two_turn = True
        self.secondary_effects = SecondaryEffect(30, status=Status.PAR),

    def check_success(self, user, target, engine):
        if user.remove_effect(Volatile.TWOTURNMOVE):
            return
        else:
            if user.item is itemdex['powerherb'] and user.use_item(engine) is not FAIL:
                return
            user.set_effect(effects.Bounce(self))
            return FAIL

class bravebird(Move):
    def __init__(self):
        super(bravebird, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.recoil = 33

class brickbreak(Move):
    def __init__(self):
        super(brickbreak, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 75

    def on_try_hit(self, target):
        target.side.remove_effect(SideCondition.REFLECT)
        target.side.remove_effect(SideCondition.LIGHTSCREEN)

class bugbite(Move):
    def __init__(self):
        super(bugbite, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.BUG
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 60

    def on_success(self, user, target, engine):
        item = target.item
        if item and item.is_berry and not user.is_fainted() and target.take_item() is not FAIL:
            user.eat_berry(engine, item, stolen=True)

class bugbuzz(Move):
    def __init__(self):
        super(bugbuzz, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.BUG
        self.accuracy = 100
        self.base_power = 90
        self.is_sound = True
        self.secondary_effects = SecondaryEffect(10, Boosts(spd=-1)),

class bulkup(Move):
    def __init__(self):
        super(bulkup, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.is_protectable = False
        self.targets_user = True
        self.type = Type.FIGHTING
        self.user_boosts = Boosts(atk=1, def_=1)

class bulldoze(Move):
    def __init__(self):
        super(bulldoze, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.GROUND
        self.accuracy = 100
        self.base_power = 60
        self.secondary_effects = SecondaryEffect(100, Boosts(spe=-1)),

class bulletpunch(Move):
    def __init__(self):
        super(bulletpunch, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 40
        self.priority = 1

class bulletseed(Move):
    def __init__(self):
        super(bulletseed, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.base_power = 25
        self.multihit = (2, 2, 3, 3, 4, 5)

class calmmind(Move):
    def __init__(self):
        super(calmmind, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spa=1, spd=1)

class chargebeam(Move):
    def __init__(self):
        super(chargebeam, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.ELECTRIC
        self.accuracy = 90
        self.base_power = 50
        self.secondary_effects = SecondaryEffect(70, Boosts(spa=1), affects_user=True),

class chatter(Move):
    def __init__(self):
        super(chatter, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.base_power = 65
        self.secondary_effects = SecondaryEffect(100, volatile=Volatile.CONFUSE),
        self.is_sound = True

class circlethrow(Move):
    def __init__(self):
        super(circlethrow, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 60
        self.priority = -6

    def on_success(self, user, target, engine):
        engine.force_random_switch(target, user)

class clearsmog(Move):
    def __init__(self):
        super(clearsmog, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.POISON
        self.base_power = 50

    def on_success(self, user, target, engine):
        target.boosts = Boosts() # not affected by clearbody or any Showdown "onBoost" events

class closecombat(Move):
    def __init__(self):
        super(closecombat, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.user_boosts = Boosts(def_=-1, spd=-1)

class coil(Move):
    def __init__(self):
        super(coil, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.POISON
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=1, def_=1, acc=1)

class confusiondamage(Move):
    def __init__(self):
        super(confusiondamage, self).__init__()
        self.max_pp = 0
        self.category = PHYSICAL
        self.type = Type['???']
        self.never_crit = True
        self.targets_user = True
        self.ignore_substitute = True
        self.base_power = 40
        self.is_protectable = False

class confuseray(Move):
    def __init__(self):
        super(confuseray, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.GHOST
        self.accuracy = 100
        self.is_bounceable = True

    def on_success(self, user, target, engine):
        target.confuse(self.infiltrates)

class copycat(Move):
    def __init__(self):
        super(copycat, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False # copycatting the move is not protectable, however the move
                                    # copycatted may be protectable
        self.targets_user = True    # same as above
        self.calls_other_moves = True

    NO_COPYCAT = {'assist', 'bestow', 'chatter', 'circlethrow', 'copycat', 'counter', 'covet',
                  'destinybond', 'detect', 'dragontail', 'endure', 'feint', 'focuspunch',
                  'followme', 'helpinghand', 'mefirst', 'metronome', 'mimic', 'mirrorcoat',
                  'mirrormove', 'naturepower', 'protect', 'ragepowder', 'roar', 'sketch',
                  'sleeptalk', 'snatch', 'struggle', 'switcheroo', 'thief', 'transform', 'trick',
                  'whirlwind'}

    def on_success(self, user, _, engine): # TODO: how far back can it get a move?
        move = engine.battlefield.last_move_used
        if move is None or move.name in self.NO_COPYCAT:
            if __debug__:
                log.i('Copycat failed because the last move (%s) is in NO_COPYCAT or is None', move)
            return FAIL

        if __debug__: log.i('Using %s via copycat', move)
        if move.targets_user:
            engine.fast_use_move(user, move)
        else:
            # don't use target; copycat gets executed by fast_use_move so target is None
            engine.use_move(user, move, engine.get_foe(user))
        user.last_move_used = move

class cosmicpower(Move):
    def __init__(self):
        super(cosmicpower, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(def_=1, spd=1)

class cottonguard(Move):
    def __init__(self):
        super(cottonguard, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.GRASS
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(def_=3)

class counter(Move):
    def __init__(self):
        super(counter, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.priority = -5
        self.has_damage_callback = True

    def check_success(self, user, target, engine):
        if not (user.was_attacked_this_turn and
                user.was_attacked_this_turn['damage'] > 0 and
                user.was_attacked_this_turn['move'].category is PHYSICAL):
            return FAIL

    def damage_callback(self, user, target):
        assert self.check_success(user, None, None) is not FAIL
        return 2 * user.was_attacked_this_turn['damage'] or 1

class crabhammer(Move):
    def __init__(self):
        super(crabhammer, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.WATER
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 100
        self.crit_ratio = 1

class crosschop(Move):
    def __init__(self):
        super(crosschop, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 80
        self.makes_contact = True
        self.base_power = 100
        self.crit_ratio = 1

class crunch(Move):
    def __init__(self):
        super(crunch, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80
        self.is_bite = True
        self.secondary_effects = SecondaryEffect(20, Boosts(def_=-1)),

class curse(Move):              # NOTE: currently deliberately excluding GHOST effect of curse
    def __init__(self):         # because no ghost in randbats gets it
        super(curse, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.GHOST
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=1, def_=1, spe=-1)

class darkpulse(Move):
    def __init__(self):
        super(darkpulse, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.DARK
        self.accuracy = 100
        self.base_power = 80
        self.is_pulse = True
        self.secondary_effects = SecondaryEffect(20, volatile=Volatile.FLINCH),

class darkvoid(Move):
    def __init__(self):
        super(darkvoid, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.DARK
        self.accuracy = 80
        self.is_bounceable = True
        self.target_status = Status.SLP

class dazzlinggleam(Move):
    def __init__(self):
        super(dazzlinggleam, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FAIRY
        self.accuracy = 100
        self.base_power = 80

class defendorder(Move):
    def __init__(self):
        super(defendorder, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.BUG
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(def_=1, spd=1)

class defog(Move):
    def __init__(self):
        super(defog, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.FLYING
        self.is_bounceable = True
        self.ignore_substitute = True # substitute doesn't block hazard-clearing, but does
                                      # block evasion drop
    def on_success(self, user, target, engine):
        if not target.has_effect(Volatile.SUBSTITUTE) or user.ability.name == 'infiltrator':
            engine.apply_boosts(target, Boosts(evn=-1), False)

        target.side.remove_effect(SideCondition.REFLECT)
        target.side.remove_effect(SideCondition.LIGHTSCREEN)
        target.side.remove_effect(SideCondition.SAFEGUARD)
        target.side.clear_hazards()
        user.side.clear_hazards()

class destinybond(Move):
    def __init__(self):
        super(destinybond, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.GHOST
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        user.set_effect(effects.DestinyBond())

class diamondstorm(Move):
    def __init__(self):
        super(diamondstorm, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.ROCK
        self.accuracy = 95
        self.base_power = 100

class disable(Move):
    def __init__(self):
        super(disable, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL
        self.accuracy = 100
        self.ignore_substitute = True
        self.is_bounceable = True

    def check_success(self, user, target, engine):
        move = target.last_move_used
        if move is None:
            if __debug__: log.i('Disable failed because %s has not used a move', target)
            return FAIL
        if not target.pp.get(move):
            if __debug__: log.i('Disable failed because %s has no pp for %s', target, move)
            return FAIL
        if target.has_effect(Volatile.DISABLE):
            if __debug__: log.i('Disable failed because %s is already disabled', target)
            return FAIL

    def on_success(self, user, target, engine):
        move = target.last_move_used
        # lasts 4 turns from the pokemon's perspective: increase to 5 if target won't move this turn
        # because then this turn doesn't count.
        duration = 4 if target.will_move_this_turn else 5
        target.set_effect(effects.Disable(move, duration))

class discharge(Move):
    def __init__(self):
        super(discharge, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(30, status=Status.PAR),

class doubleedge(Move):
    def __init__(self):
        super(doubleedge, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.recoil = 33

class dracometeor(Move):
    def __init__(self):
        super(dracometeor, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.DRAGON
        self.accuracy = 90
        self.base_power = 130
        self.user_boosts = Boosts(spa=-2)

class dragonascent(Move):
    def __init__(self):
        super(dragonascent, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.user_boosts = Boosts(def_=-1, spd=-1)

class dragonclaw(Move):
    def __init__(self):
        super(dragonclaw, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.DRAGON
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80

class dragondance(Move):
    def __init__(self):
        super(dragondance, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.DRAGON
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=1, spe=1)

class dragonpulse(Move):
    def __init__(self):
        super(dragonpulse, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.DRAGON
        self.accuracy = 100
        self.base_power = 85
        self.is_pulse = True

class dragontail(Move):
    def __init__(self):
        super(dragontail, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.DRAGON
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 60
        self.priority = -6

    def on_success(self, user, target, engine):
        engine.force_random_switch(target, user)

class drainingkiss(Move):
    def __init__(self):
        super(drainingkiss, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FAIRY
        self.accuracy = 100
        self.base_power = 50
        self.drain = 75

class drainpunch(Move):
    def __init__(self):
        super(drainpunch, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 75
        self.is_punch = True
        self.drain = 50

class drillpeck(Move):
    def __init__(self):
        super(drillpeck, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80

class drillrun(Move):
    def __init__(self):
        super(drillrun, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GROUND
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 80
        self.crit_ratio = 1

class dynamicpunch(Move):
    def __init__(self):
        super(dynamicpunch, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 50
        self.makes_contact = True
        self.base_power = 100
        self.is_punch = True
        self.secondary_effects = SecondaryEffect(100, volatile=Volatile.CONFUSE),

class earthpower(Move):
    def __init__(self):
        super(earthpower, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.GROUND
        self.accuracy = 100
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(10, Boosts(spd=-1)),

class earthquake(Move):
    def __init__(self):
        super(earthquake, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GROUND
        self.accuracy = 100
        self.base_power = 100

class electricterrain(Move):
    def __init__(self):
        super(electricterrain, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.ELECTRIC
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if engine.battlefield.terrain is not None:
            if __debug__: log.i('Failing electricterrain because terrain is %s' %
                                engine.battlefield.terrain)
            return FAIL

    def on_success(self, user, _, engine):
        engine.battlefield.terrain = PseudoWeather.ELECTRICTERRAIN
        engine.battlefield.set_effect(effects.ElectricTerrain())

class encore(Move):
    def __init__(self):
        super(encore, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.NORMAL
        self.accuracy = 100
        self.is_bounceable = True
        self.ignore_substitute = True

    NO_ENCORE = {'encore', 'mimic', 'mirrormove', 'sketch', 'struggle', 'transform'}

    def check_success(self, user, target, engine):
        last_move = target.last_move_used
        if (last_move is None or
            last_move.name in self.NO_ENCORE or
            target.pp.get(last_move, 0) <= 0
        ):
            return FAIL

    def on_success(self, user, target, engine):
        duration = 3 if target.will_move_this_turn else 4
        target.set_effect(effects.Encore(target.last_move_used, duration))

class endeavor(Move):
    def __init__(self):
        super(endeavor, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.has_damage_callback = True

    def check_success(self, user, target, engine):
        return True if target.hp > user.hp else FAIL

    def damage_callback(self, user, target):
        return target.hp - user.hp

class energyball(Move):
    def __init__(self):
        super(energyball, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.base_power = 90
        self.is_bullet = True
        self.secondary_effects = SecondaryEffect(10, Boosts(spd=-1)),

class eruption(Move):
    def __init__(self):
        super(eruption, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 100

    def get_base_power(self, user, target, engine):
        return (150 * user.hp // user.max_hp) or 1

class explosion(Move):
    def __init__(self):
        super(explosion, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 250
        self.selfdestruct = True

class extrasensory(Move):
    def __init__(self):
        super(extrasensory, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 100
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(10, volatile=Volatile.FLINCH),

class extremespeed(Move):
    def __init__(self):
        super(extremespeed, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80
        self.priority = 2

class facade(Move):
    def __init__(self):
        super(facade, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        return 70 if user.status in (None, Status.SLP) else 140
    # Negation of power-loss from burn is handled in statuses.Burn.on_base_power

class fakeout(Move):
    def __init__(self):
        super(fakeout, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 40
        self.priority = 3
        self.secondary_effects = SecondaryEffect(100, volatile=Volatile.FLINCH),

    def check_success(self, user, target, engine):
        if user.turns_out > 1:
            return FAIL

class fierydance(Move):
    def __init__(self):
        super(fierydance, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(50, Boosts(spa=1), affects_user=True),

class fireblast(Move):
    def __init__(self):
        super(fireblast, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 85
        self.base_power = 110
        self.secondary_effects = SecondaryEffect(10, status=Status.BRN),

class firefang(Move):
    def __init__(self):
        super(firefang, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 65
        self.is_bite = True
        self.secondary_effects = (SecondaryEffect(10, status=Status.BRN),
                                  SecondaryEffect(10, volatile=Volatile.FLINCH))

class firepunch(Move):
    def __init__(self):
        super(firepunch, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 75
        self.is_punch = True
        self.secondary_effects = SecondaryEffect(10, status=Status.BRN),

class flamecharge(Move):
    def __init__(self):
        super(flamecharge, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 50
        self.secondary_effects = SecondaryEffect(100, Boosts(spe=1), affects_user=True),

class flamewheel(Move):
    def __init__(self):
        super(flamewheel, self).__init__()
        self.max_pp = _MAX_PP[25]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 60
        self.thaw_user = True

class flamethrower(Move):
    def __init__(self):
        super(flamethrower, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(10, status=Status.BRN),

class flareblitz(Move):
    def __init__(self):
        super(flareblitz, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.thaw_user = True
        self.recoil = 33
        self.secondary_effects = SecondaryEffect(10, status=Status.BRN),

class flashcannon(Move):
    def __init__(self):
        super(flashcannon, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.STEEL
        self.accuracy = 100
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(10, Boosts(spd=-1)),

class flyingpress(Move):
    def __init__(self):
        super(flyingpress, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 80

    def get_effectiveness(self, target):
        return effectiveness(Type.FIGHTING, target) * effectiveness(Type.FLYING, target)

class focusblast(Move):
    def __init__(self):
        super(focusblast, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FIGHTING
        self.accuracy = 70
        self.base_power = 120
        self.is_bullet = True
        self.secondary_effects = SecondaryEffect(10, Boosts(spd=-1)),

class focuspunch(Move):
    def __init__(self):
        super(focuspunch, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 150
        self.is_punch = True
        self.priority = -3

    def check_success(self, user, target, engine):
        if (user.was_attacked_this_turn and
            user.was_attacked_this_turn['move'].category is not STATUS and
            user.was_attacked_this_turn['damage'] > 0
        ):
            return FAIL

class foulplay(Move):
    def __init__(self):
        super(foulplay, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 95
        self.use_opponent_attack = True

class freezedry(Move):
    def __init__(self):
        super(freezedry, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.ICE
        self.accuracy = 100
        self.base_power = 70
        self.secondary_effects = SecondaryEffect(10, status=Status.FRZ),

    def get_effectiveness(self, target):
        return effectiveness(Type.ICE, target) * (4 if Type.WATER in target.types else 1)

class fusionbolt(Move):
    def __init__(self):
        super(fusionbolt, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.base_power = 100

class fusionflare(Move):
    def __init__(self):
        super(fusionflare, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.base_power = 100
        self.thaw_user = True

class geargrind(Move):
    def __init__(self):
        super(geargrind, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 50
        self.multihit = (2,)

class geomancy(Move):
    def __init__(self):
        super(geomancy, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.FAIRY
        self.is_protectable = False
        self.is_two_turn = True
        self.targets_user = True
        self.user_boosts = Boosts(spa=2, spd=2, spe=2)

    def check_success(self, user, _, engine):
        if user.remove_effect(Volatile.TWOTURNMOVE):
            return
        else:
            if user.item is itemdex['powerherb'] and user.use_item(engine) is not FAIL:
                return
            user.set_effect(effects.TwoTurnMoveEffect(self))
            return FAIL

class gigadrain(Move):
    def __init__(self):
        super(gigadrain, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.base_power = 75
        self.drain = 50

class glare(Move):
    def __init__(self):
        super(glare, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = STATUS
        self.type = Type.NORMAL
        self.accuracy = 100
        self.target_status = Status.PAR
        self.is_bounceable = True

class grassknot(Move):
    def __init__(self):
        super(grassknot, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        weight = target.weight
        if weight >= 200:
            return 120
        if weight >= 100:
            return 100
        if weight >= 50:
            return 80
        if weight >= 25:
            return 60
        if weight >= 10:
            return 40
        return 20

class growth(Move):
    def __init__(self):
        super(growth, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        boost = (2 if engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND)
                 else 1)
        engine.apply_boosts(user, Boosts(atk=boost, spa=boost), True)

class gunkshot(Move):
    def __init__(self):
        super(gunkshot, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.POISON
        self.accuracy = 80
        self.base_power = 120
        self.secondary_effects = SecondaryEffect(30, status=Status.PSN),

class gyroball(Move):
    def __init__(self):
        super(gyroball, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 100
        self.makes_contact = True
        self.is_bullet = True

    def get_base_power(self, user, target, engine):
        power = int(target.calculate_stat('spe') * 25 / user.calculate_stat('spe'))
        return clamp_int(power, 1, 150)

class hammerarm(Move):
    def __init__(self):
        super(hammerarm, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 100
        self.is_punch = True
        self.user_boosts = Boosts(spe=-1)

class haze(Move):
    def __init__(self):
        super(haze, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = STATUS
        self.type = Type.ICE
        self.targets_user = True
        self.is_protectable = False

    def on_success(self, user, _, engine):
        if __debug__: log.i('All stats were reset!')
        user.boosts = Boosts()
        foe = engine.get_foe(user)
        if foe is not None:
            foe.boosts = Boosts()

class headbutt(Move):
    def __init__(self):
        super(headbutt, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 70
        self.secondary_effects = SecondaryEffect(30, volatile=Volatile.FLINCH),

class headcharge(Move):
    def __init__(self):
        super(headcharge, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.recoil = 25

class headsmash(Move):
    def __init__(self):
        super(headsmash, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.ROCK
        self.accuracy = 80
        self.makes_contact = True
        self.base_power = 150
        self.recoil = 50

class healbell(Move):
    def __init__(self):
        super(healbell, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    on_success = aromatherapy.on_success.__func__

class healingwish(Move):
    def __init__(self):
        super(healingwish, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, target, engine):
        if user.side.remaining_pokemon_on_bench == 0:
            return FAIL

    def on_success(self, user, _, engine):
        user.side.set_effect(effects.HealingWish())
        user.hp = 0

class healorder(Move):
    def __init__(self):
        super(healorder, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.BUG
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        engine.heal(user, int(round(user.max_hp * 0.5)))

class heatwave(Move):
    def __init__(self):
        super(heatwave, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 90
        self.base_power = 95
        self.secondary_effects = SecondaryEffect(10, status=Status.BRN),

class heavyslam(Move):
    def __init__(self):
        super(heavyslam, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        user_weight = user.weight
        target_weight = target.weight
        if user_weight > target_weight * 5:
            return 120
        if user_weight > target_weight * 4:
            return 100
        if user_weight > target_weight * 3:
            return 80
        if user_weight > target_weight * 2:
            return 60
        return 40

class hiddenpower(Move):
    def __init__(self):
        super(hiddenpower, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.DARK   # default type for (31,)*6 IVs
        self.accuracy = 100
        self.base_power = 60
        self.is_hiddenpower = True

class hiddenpowerelectric(hiddenpower):
    def __init__(self):
        super(hiddenpowerelectric, self).__init__()
        self.type = Type.ELECTRIC

class hiddenpowerfighting(hiddenpower):
    def __init__(self):
        super(hiddenpowerfighting, self).__init__()
        self.type = Type.FIGHTING

class hiddenpowerfire(hiddenpower):
    def __init__(self):
        super(hiddenpowerfire, self).__init__()
        self.type = Type.FIRE

class hiddenpowerflying(hiddenpower):
    def __init__(self):
        super(hiddenpowerflying, self).__init__()
        self.type = Type.FLYING

class hiddenpowergrass(hiddenpower):
    def __init__(self):
        super(hiddenpowergrass, self).__init__()
        self.type = Type.GRASS

class hiddenpowerground(hiddenpower):
    def __init__(self):
        super(hiddenpowerground, self).__init__()
        self.type = Type.GROUND

class hiddenpowerice(hiddenpower):
    def __init__(self):
        super(hiddenpowerice, self).__init__()
        self.type = Type.ICE

class hiddenpowerpsychic(hiddenpower):
    def __init__(self):
        super(hiddenpowerpsychic, self).__init__()
        self.type = Type.PSYCHIC

class hiddenpowerrock(hiddenpower):
    def __init__(self):
        super(hiddenpowerrock, self).__init__()
        self.type = Type.ROCK

class hiddenpowerdark(hiddenpower):
    def __init__(self):
        super(hiddenpowerdark, self).__init__()
        self.type = Type.DARK

class highjumpkick(Move):
    def __init__(self):
        super(highjumpkick, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 130
        self.recoil = -1

    def on_move_fail(self, user, engine):
        engine.damage(user, user.max_hp / 2.0, Cause.CRASH, self)

class honeclaws(Move):
    def __init__(self):
        super(honeclaws, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.DARK
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=1, acc=1)

class hornleech(Move):
    def __init__(self):
        super(hornleech, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 75
        self.drain = 50

class hurricane(Move):
    def __init__(self):
        super(hurricane, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FLYING
        self.base_power = 110
        self.secondary_effects = SecondaryEffect(30, volatile=Volatile.CONFUSE),

    def accuracy_callback(self, user, target, engine):
        weather = engine.battlefield.weather
        if weather in (Weather.RAINDANCE, Weather.PRIMORDIALSEA):
            self.accuracy = None
        elif weather in (Weather.SUNNYDAY, Weather.DESOLATELAND):
            self.accuracy = 50
        else:
            self.accuracy = 70

class hydropump(Move):
    def __init__(self):
        super(hydropump, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 80
        self.base_power = 110

class hyperspacefury(Move):
    def __init__(self):
        super(hyperspacefury, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.base_power = 100
        self.ignore_substitute = True
        self.is_protectable = False
        self.user_boosts = Boosts(def_=-1)

    def check_success(self, user, target, engine):
        if user.base_species != 'hoopaunbound':
            if __debug__: log.i('hyperspacefury failed because %s is not hoopaunbound', user)
            return FAIL

class hypervoice(Move):
    def __init__(self):
        super(hypervoice, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 90
        self.is_sound = True

class hypnosis(Move):
    def __init__(self):
        super(hypnosis, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.accuracy = 60
        self.target_status = Status.SLP
        self.is_bounceable = True

class icebeam(Move):
    def __init__(self):
        super(icebeam, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.ICE
        self.accuracy = 100
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(10, status=Status.FRZ),

class icefang(Move):
    def __init__(self):
        super(icefang, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.ICE
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 65
        self.is_bite = True
        self.secondary_effects = (SecondaryEffect(10, status=Status.FRZ),
                                  SecondaryEffect(10, volatile=Volatile.FLINCH))

class icepunch(Move):
    def __init__(self):
        super(icepunch, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.ICE
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 75
        self.is_punch = True
        self.secondary_effects = SecondaryEffect(10, status=Status.FRZ),

class iceshard(Move):
    def __init__(self):
        super(iceshard, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.ICE
        self.accuracy = 100
        self.base_power = 40
        self.priority = 1

class iciclecrash(Move):
    def __init__(self):
        super(iciclecrash, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.ICE
        self.accuracy = 90
        self.base_power = 85
        self.secondary_effects = SecondaryEffect(30, volatile=Volatile.FLINCH),

class iciclespear(Move):
    def __init__(self):
        super(iciclespear, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.ICE
        self.accuracy = 100
        self.base_power = 25
        self.multihit = (2, 2, 3, 3, 4, 5)

class icywind(Move):
    def __init__(self):
        super(icywind, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.ICE
        self.accuracy = 95
        self.base_power = 55
        self.secondary_effects = SecondaryEffect(100, Boosts(spe=-1)),

class infestation(Move):
    def __init__(self):
        super(infestation, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.BUG
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 20

    def on_success(self, user, target, engine):
        if not target.is_fainted() and not user.is_fainted():
            trap_effect = effects.PartialTrap(user)
            target.set_effect(trap_effect)
            user.set_effect(effects.Trapper(trap_effect.duration, target))

class ironhead(Move):
    def __init__(self):
        super(ironhead, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(30, volatile=Volatile.FLINCH),

class irontail(Move):
    def __init__(self):
        super(irontail, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 75
        self.makes_contact = True
        self.base_power = 100
        self.secondary_effects = SecondaryEffect(30, Boosts(def_=-1)),

class judgment(Move):
    def __init__(self):
        super(judgment, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 100

    def on_modify_move(self, user, target, engine):
        if user.item is not None:
            self.type = user.item.plate_type or Type.NORMAL

class jumpkick(Move):
    def __init__(self):
        super(jumpkick, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 100
        self.recoil = -1

    def on_move_fail(self, user, engine):
        engine.damage(user, user.max_hp / 2.0, Cause.CRASH, self)

class kingsshield(Move):
    def __init__(self):
        super(kingsshield, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.STEEL
        self.is_protectable = False
        self.targets_user = True
        self.priority = 4

    def check_success(self, user, _, engine):
        target = engine.get_foe(user)
        if target is None or not target.will_move_this_turn:
            return FAIL
        if user.has_effect(Volatile.STALL):
            return user.get_effect(Volatile.STALL).check_stall_success()

    def on_success(self, user, _, engine):
        user.set_effect(effects.KingsShield())
        user.set_effect(effects.StallCounter())

class knockoff(Move):
    def __init__(self):
        super(knockoff, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        item = target.item
        if item is not None and item.removable:
            return 1.5 * 65
        return 65

    def on_success(self, user, target, engine):
        if not user.is_fainted():
            target.take_item()

class lavaplume(Move):
    def __init__(self):
        super(lavaplume, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 100
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(30, status=Status.BRN),

class leafblade(Move):
    def __init__(self):
        super(leafblade, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 90
        self.crit_ratio = 1

class leafstorm(Move):
    def __init__(self):
        super(leafstorm, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 90
        self.base_power = 130
        self.user_boosts = Boosts(spa=-2)

class leechseed(Move):
    def __init__(self):
        super(leechseed, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.GRASS
        self.accuracy = 90
        self.is_bounceable = True

    def on_success(self, user, target, engine):
        target.set_effect(effects.LeechSeed())

class lightofruin(Move):
    def __init__(self):
        super(lightofruin, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FAIRY
        self.accuracy = 90
        self.base_power = 140
        self.recoil = 50

class lightscreen(Move):
    def __init__(self):
        super(lightscreen, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.targets_user = True
        self.is_protectable = False

    def check_success(self, user, _, engine):
        if user.side.has_effect(SideCondition.LIGHTSCREEN):
            return FAIL

    def on_success(self, user, _, engine):
        duration = 8 if user.item is itemdex['lightclay'] else 5
        user.side.set_effect(effects.LightScreen(duration))

class lovelykiss(Move):
    def __init__(self):
        super(lovelykiss, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.accuracy = 75
        self.is_bounceable = True
        self.target_status = Status.SLP

class lowkick(Move):
    def __init__(self):
        super(lowkick, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True

    get_base_power = grassknot.get_base_power.__func__

class machpunch(Move):
    def __init__(self):
        super(machpunch, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 40
        self.is_punch = True
        self.priority = 1

class magiccoat(Move):
    def __init__(self):
        super(magiccoat, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True
        self.priority = 4

    def on_success(self, user, _, engine):
        user.set_effect(effects.MagicCoat())

class magnetrise(Move):
    def __init__(self):
        super(magnetrise, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.ELECTRIC
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        user.set_effect(effects.MagnetRise())

class megahorn(Move):
    def __init__(self):
        super(megahorn, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.BUG
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 120

class memento(Move):
    def __init__(self):
        super(memento, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.DARK
        self.accuracy = 100

    def on_success(self, user, target, engine):
        engine.apply_boosts(target, Boosts(atk=-2, spa=-2), False)
        user.hp = 0

class metalburst(Move):
    def __init__(self):
        super(metalburst, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 100
        self.has_damage_callback = True

    def check_success(self, user, target, engine):
        if not (user.was_attacked_this_turn and
                user.was_attacked_this_turn['damage'] > 0 and
                user.was_attacked_this_turn['move'].category in (PHYSICAL, SPECIAL)):
            return FAIL

    def damage_callback(self, user, target):
        assert self.check_success(user, None, None) is not FAIL
        return int(1.5 * user.was_attacked_this_turn['damage']) or 1

class meteormash(Move):
    def __init__(self):
        super(meteormash, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.STEEL
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 90
        self.is_punch = True
        self.secondary_effects = SecondaryEffect(20, Boosts(atk=1)),

class milkdrink(Move):
    def __init__(self):
        super(milkdrink, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        engine.heal(user, int(round(user.max_hp * 0.5)))

class mirrorcoat(Move):
    def __init__(self):
        super(mirrorcoat, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 100
        self.priority = -5
        self.has_damage_callback = True

    def check_success(self, user, target, engine):
        if not (user.was_attacked_this_turn and
                user.was_attacked_this_turn['damage'] > 0 and
                user.was_attacked_this_turn['move'].category is SPECIAL):
            return FAIL

    def damage_callback(self, user, target):
        assert self.check_success(user, None, None) is not FAIL
        return 2 * user.was_attacked_this_turn['damage'] or 1

class moonblast(Move):
    def __init__(self):
        super(moonblast, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.FAIRY
        self.accuracy = 100
        self.base_power = 95
        self.secondary_effects = SecondaryEffect(30, Boosts(spa=-1)),

class moonlight(Move):
    def __init__(self):
        super(moonlight, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.FAIRY
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        engine.heal(user, int(round(user.max_hp *
                                    _WEATHER_HEAL_FACTOR[engine.battlefield.weather])))

class morningsun(Move):
    def __init__(self):
        super(morningsun, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    on_success = moonlight.on_success.__func__

class nastyplot(Move):
    def __init__(self):
        super(nastyplot, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.DARK
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spa=2)

class nightshade(Move):
    def __init__(self):
        super(nightshade, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.GHOST
        self.accuracy = 100
        self.has_damage_callback = True

    def damage_callback(self, user, target):
        return user.level

class nightslash(Move):
    def __init__(self):
        super(nightslash, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 70
        self.crit_ratio = 1

class nuzzle(Move):
    def __init__(self):
        super(nuzzle, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 20
        self.secondary_effects = SecondaryEffect(100, status=Status.PAR),

class oblivionwing(Move):
    def __init__(self):
        super(oblivionwing, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.base_power = 80
        self.drain = 75

class originpulse(Move):
    def __init__(self):
        super(originpulse, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 85
        self.base_power = 110
        self.is_pulse = True

class outrage(Move):
    def __init__(self):
        super(outrage, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.DRAGON
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120

    def on_success(self, user, target, engine):
        if not user.is_fainted():
            user.set_effect(effects.LockedMove(self))

    def on_move_fail(self, user, engine):
        user.remove_effect(Volatile.LOCKEDMOVE)

class overheat(Move):
    def __init__(self):
        super(overheat, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.FIRE
        self.accuracy = 90
        self.base_power = 130
        self.user_boosts = Boosts(spa=-2)

class painsplit(Move):
    def __init__(self):
        super(painsplit, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL

    def on_success(self, user, target, engine):
        average_hp = ((user.hp + target.hp) // 2) or 1
        user.hp = min(user.max_hp, average_hp)
        target.hp = min(target.max_hp, average_hp)
        if __debug__: log.i("Set %s's and %s's hp to %s", user, target, average_hp)

class partingshot(Move):
    def __init__(self):
        super(partingshot, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.DARK
        self.accuracy = 100
        self.switch_user = True
        self.is_sound = True
        self.is_bounceable = True

    def on_success(self, user, target, engine):
        engine.apply_boosts(target, Boosts(atk=-1, spa=-1), False)

class perishsong(Move):
    def __init__(self):
        super(perishsong, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.is_sound = True

    def on_success(self, user, target, engine):
        user.set_effect(effects.PerishSong())
        target.set_effect(effects.PerishSong())

class petaldance(Move):
    def __init__(self):
        super(petaldance, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120

    on_success = outrage.on_success.__func__
    on_move_fail = outrage.on_success.__func__

class phantomforce(Move):
    def __init__(self):
        super(phantomforce, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GHOST
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 90
        self.is_protectable = False
        self.is_two_turn = True

    def check_success(self, user, target, engine):
        if user.remove_effect(Volatile.TWOTURNMOVE):
            return
        else:
            if user.item is itemdex['powerherb'] and user.use_item(engine) is not FAIL:
                return
            user.set_effect(effects.PhantomForce(self))
            return FAIL

class pinmissile(Move):
    def __init__(self):
        super(pinmissile, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.BUG
        self.accuracy = 95
        self.base_power = 25
        self.multihit = (2, 2, 3, 3, 4, 5)

class playrough(Move):
    def __init__(self):
        super(playrough, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FAIRY
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(10, Boosts(atk=-1)),

class pluck(Move):
    def __init__(self):
        super(pluck, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FLYING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 60

    on_success = bugbite.on_success.__func__

class poisonjab(Move):
    def __init__(self):
        super(poisonjab, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.POISON
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(30, status=Status.PSN),

class powergem(Move):
    def __init__(self):
        super(powergem, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.ROCK
        self.accuracy = 100
        self.base_power = 80

class poweruppunch(Move):
    def __init__(self):
        super(poweruppunch, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 40
        self.is_punch = True
        self.secondary_effects = SecondaryEffect(100, Boosts(atk=1), affects_user=True),

class powerwhip(Move):
    def __init__(self):
        super(powerwhip, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GRASS
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 120

class precipiceblades(Move):
    def __init__(self):
        super(precipiceblades, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.GROUND
        self.accuracy = 85
        self.base_power = 120

class protect(Move):
    def __init__(self):
        super(protect, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True
        self.priority = 4

    def check_success(self, user, _, engine):
        target = engine.get_foe(user)
        if target is None or not target.will_move_this_turn:
            return FAIL
        if user.has_effect(Volatile.STALL):
            return user.get_effect(Volatile.STALL).check_stall_success()

    def on_success(self, user, _, engine):
        user.set_effect(effects.Protect())
        user.set_effect(effects.StallCounter())

class psychic(Move):
    def __init__(self):
        super(psychic, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 100
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(10, Boosts(spd=-1)),

class psychoboost(Move):
    def __init__(self):
        super(psychoboost, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 90
        self.base_power = 140
        self.user_boosts = Boosts(spa=-2)

class psychocut(Move):
    def __init__(self):
        super(psychocut, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.PSYCHIC
        self.accuracy = 100
        self.base_power = 70
        self.crit_ratio = 1

class psychoshift(Move):
    def __init__(self):
        super(psychoshift, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.accuracy = 100

    def check_success(self, user, target, engine):
        if user.status is None or target.status is not None:
            return FAIL

    def on_success(self, user, target, engine): # TODO: make sure blocked by substitute
        if engine.set_status(target, user.status, user) is not FAIL:
            user.cure_status()

class psyshock(Move):
    def __init__(self):
        super(psyshock, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 100
        self.base_power = 80
        self.defensive_category = PHYSICAL

class psystrike(Move):
    def __init__(self):
        super(psystrike, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 100
        self.base_power = 100
        self.defensive_category = PHYSICAL

class pursuit(Move):
    def __init__(self):
        super(pursuit, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.accuracy = 100
        self.makes_contact = True

    def on_success(self, user, target, engine): # don't hit twice
        # if hitting opponent mid-switch, remove regularly scheduled attack from queue
        engine.event_queue = [event for event in engine.event_queue if not event.pokemon is user]

        # if hitting opponent normally (with faster speed): prevent another hit on a foe uturn
        target.remove_effect(Volatile.PURSUIT)

    def on_modify_move(self, user, target, engine):
        if target.is_switching_out:
            self.accuracy = None

    def get_base_power(self, user, target, engine):
        return 80 if target.is_switching_out else 40

class quickattack(Move):
    def __init__(self):
        super(quickattack, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 40
        self.priority = 1

class quiverdance(Move):
    def __init__(self):
        super(quiverdance, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.BUG
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spa=1, spd=1, spe=1)

class raindance(Move):
    def __init__(self):
        super(raindance, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.WATER
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if engine.battlefield.weather is Weather.RAINDANCE:
            return FAIL

    def on_success(self, user, _, engine):
        duration = 8 if user.item is itemdex['damprock'] else 5
        engine.battlefield.set_weather(Weather.RAINDANCE, duration)

class rapidspin(Move):
    def __init__(self):
        super(rapidspin, self).__init__()
        self.max_pp = _MAX_PP[40]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 20
        self.on_success_ignores_substitute = True

    def on_success(self, user, target, engine):
        if not user.is_fainted():
            user.remove_effect(Volatile.LEECHSEED)
            user.remove_effect(Volatile.PARTIALTRAP)
            user.side.clear_hazards()

class razorshell(Move):
    def __init__(self):
        super(razorshell, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.WATER
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 75
        self.secondary_effects = SecondaryEffect(50, Boosts(def_=-1)),

class recover(Move):
    def __init__(self):
        super(recover, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        engine.heal(user, int(round(user.max_hp * 0.5)))

class reflect(Move):
    def __init__(self):
        super(reflect, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if user.side.has_effect(SideCondition.REFLECT):
            return FAIL

    def on_success(self, user, _, engine):
        duration = 8 if user.item is itemdex['lightclay'] else 5
        user.side.set_effect(effects.Reflect(duration))

class relicsong(Move):
    def __init__(self):
        super(relicsong, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 75
        self.is_sound = True
        self.secondary_effects = SecondaryEffect(10, status=Status.SLP),

    def on_after_move_secondary(self, user, target, engine):
        if not user.is_fainted() and user.base_species == 'meloetta':
            user.change_forme('meloettapirouette' if user.name == 'meloetta' else 'meloetta')

class rest(Move):
    def __init__(self):
        super(rest, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if (user.hp == user.max_hp or
            user.status is Status.SLP or
            user.is_immune_to(Status.SLP)
        ):
            return FAIL

    def on_success(self, user, _, engine):
        assert user.hp > 0
        user.cure_status()
        user.status = Status.SLP
        user.set_effect(statuses.Sleep(user, 2))
        user.is_resting = True  # needed for Sleep Clause
        engine.heal(user, user.max_hp)

class retaliate(Move):
    def __init__(self):
        super(retaliate, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        if (engine.battlefield.turns - 1) == user.side.last_fainted_on_turn:
            if __debug__: log.i("Doubling retaliate's base power: a teammate fainted last turn")
            return 140
        return 70

class return_(Move):
    def __init__(self):
        super(return_, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 102

class reversal(Move):
    def __init__(self):
        super(reversal, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        ratio = user.hp * 48 / user.max_hp
        if ratio < 2:
            return 200
        if ratio < 5:
            return 150
        if ratio < 10:
            return 100
        if ratio < 17:
            return 80
        if ratio < 33:
            return 40
        return 20

class roar(Move):
    def __init__(self):
        super(roar, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.is_sound = True
        self.is_bounceable = True
        self.priority = -6

    def on_success(self, user, target, engine):
        return engine.force_random_switch(target, user)

class rockblast(Move):
    def __init__(self):
        super(rockblast, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.ROCK
        self.accuracy = 90
        self.base_power = 25
        self.multihit = (2, 2, 3, 3, 4, 5)

class rockclimb(Move):
    def __init__(self):
        super(rockclimb, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(20, volatile=Volatile.CONFUSE),

class rockpolish(Move):
    def __init__(self):
        super(rockpolish, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.ROCK
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spe=2)

class rockslide(Move):
    def __init__(self):
        super(rockslide, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.ROCK
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 75
        self.secondary_effects = SecondaryEffect(30, volatile=Volatile.FLINCH),

class rocktomb(Move):
    def __init__(self):
        super(rocktomb, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.ROCK
        self.accuracy = 95
        self.base_power = 60
        self.secondary_effects = SecondaryEffect(100, Boosts(spe=-1)),

class roost(Move):
    def __init__(self):
        super(roost, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.FLYING
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, target, engine):
        if user.hp == user.max_hp:
            return FAIL

    def on_success(self, user, target, engine):
        engine.heal(user, int(round(user.max_hp * 0.5)))
        user.set_effect(effects.Roost(user))

class sacredfire(Move):
    def __init__(self):
        super(sacredfire, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 100
        self.secondary_effects = SecondaryEffect(50, status=Status.BRN),

class sacredsword(Move):
    def __init__(self):
        super(sacredsword, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 90
        self.ignore_defensive_boosts = True
        self.ignore_evasion_boosts = True

class safeguard(Move):
    def __init__(self):
        super(safeguard, self).__init__()
        self.max_pp = _MAX_PP[25]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if user.side.has_effect(SideCondition.SAFEGUARD):
            return FAIL

    def on_success(self, user, _, engine):
        user.side.set_effect(effects.Safeguard())

class scald(Move):
    def __init__(self):
        super(scald, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 100
        self.base_power = 80
        self.thaw_user = True
        self.thaw_target = True
        self.secondary_effects = SecondaryEffect(30, status=Status.BRN),

class secretsword(Move):
    def __init__(self):
        super(secretsword, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.base_power = 85
        self.defensive_category = PHYSICAL

class seedbomb(Move):
    def __init__(self):
        super(seedbomb, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.base_power = 80
        self.is_bullet = True

class seedflare(Move):
    def __init__(self):
        super(seedflare, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 85
        self.base_power = 120
        self.secondary_effects = SecondaryEffect(40, Boosts(spd=-2)),

class seismictoss(Move):
    def __init__(self):
        super(seismictoss, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.has_damage_callback = True

    def damage_callback(self, user, target):
        return user.level

class shadowball(Move):
    def __init__(self):
        super(shadowball, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.GHOST
        self.accuracy = 100
        self.base_power = 80
        self.is_bullet = True
        self.secondary_effects = SecondaryEffect(20, Boosts(spd=-1)),

class shadowclaw(Move):
    def __init__(self):
        super(shadowclaw, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.GHOST
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 70
        self.crit_ratio = True

class shadowforce(Move):
    def __init__(self):
        super(shadowforce, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.GHOST
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.is_protectable = False
        self.is_two_turn = True

    check_success = phantomforce.check_success.__func__

class shadowpunch(Move):
    def __init__(self):
        super(shadowpunch, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.GHOST
        self.makes_contact = True
        self.base_power = 60
        self.is_punch = True

class shadowsneak(Move):
    def __init__(self):
        super(shadowsneak, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = PHYSICAL
        self.type = Type.GHOST
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 40
        self.priority = 1

class shellsmash(Move):
    def __init__(self):
        super(shellsmash, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=2, spa=2, spe=2, def_=-1, spd=-1)

class shiftgear(Move):
    def __init__(self):
        super(shiftgear, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.STEEL
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=1, spe=2)

class signalbeam(Move):
    def __init__(self):
        super(signalbeam, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.BUG
        self.accuracy = 100
        self.base_power = 75
        self.secondary_effects = SecondaryEffect(10, volatile=Volatile.CONFUSE),

class slackoff(Move):
    def __init__(self):
        super(slackoff, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        engine.heal(user, int(round(user.max_hp * 0.5)))

class sleeppowder(Move):
    def __init__(self):
        super(sleeppowder, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.GRASS
        self.accuracy = 75
        self.target_status = Status.SLP
        self.is_bounceable = True
        self.is_powder = True

class sleeptalk(Move):
    def __init__(self):
        super(sleeptalk, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False # but the move it calls may be
        self.targets_user = True    # but the move it calls may not be
        self.calls_other_moves = True

    NO_SLEEP_TALK = {'assist', 'bide', 'chatter', 'copycat', 'focuspunch', 'mefirst', 'metronome',
                     'mimic', 'mirrormove', 'naturepower', 'sketch', 'sleeptalk', 'uproar'}

    def check_success(self, user, target, engine):
        if user.status is not Status.SLP:
            return FAIL

    def on_success(self, user, _, engine):
        moves = [move for move in user.moveset if
                 move.name not in self.NO_SLEEP_TALK and not move.is_two_turn]
        if __debug__: log.i('sleeptalk choosing randomly from %s', moves)

        if moves:
            move = random.choice(moves)
            engine.use_move(user, move, engine.get_foe(user))
            engine.battlefield.last_move_used = move
        else:
            return FAIL

class sludgebomb(Move):
    def __init__(self):
        super(sludgebomb, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.POISON
        self.accuracy = 100
        self.base_power = 90
        self.is_bullet = True
        self.secondary_effects = SecondaryEffect(30, status=Status.PSN),

class sludgewave(Move):
    def __init__(self):
        super(sludgewave, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.POISON
        self.accuracy = 100
        self.base_power = 95
        self.secondary_effects = SecondaryEffect(10, status=Status.PSN),

class softboiled(Move):
    def __init__(self):
        super(softboiled, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def on_success(self, user, _, engine):
        engine.heal(user, int(round(user.max_hp * 0.5)))

class solarbeam(Move):
    def __init__(self):
        super(solarbeam, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.base_power = 120

    def check_success(self, user, target, engine):
        if user.remove_effect(Volatile.TWOTURNMOVE):
            return
        else:
            if (engine.battlefield.weather in (Weather.SUNNYDAY, Weather.DESOLATELAND) or
                (user.item == itemdex['powerherb'] and user.use_item(engine) is not FAIL)):
                return
            user.set_effect(effects.TwoTurnMoveEffect(self))
            return FAIL

class spacialrend(Move):
    def __init__(self):
        super(spacialrend, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.DRAGON
        self.accuracy = 95
        self.base_power = 100
        self.crit_ratio = 1

class spikes(Move):
    def __init__(self):
        super(spikes, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.GROUND
        self.is_protectable = False
        self.is_bounceable = True
        self.ignore_substitute = True
        self.targets_user = True

    def on_success(self, user, _, engine):
        foe_side = engine.get_foe_side(user)
        spikes_ = foe_side.get_effect(Hazard.SPIKES)
        if spikes_ is None:
            if __debug__: log.i("Set spikes(layers=1) on %s's side", foe_side.active_pokemon)
            foe_side.set_effect(effects.Spikes())
        else:
            if spikes_.layers == 3:
                return FAIL
            spikes_.layers += 1
            if __debug__: log.i("Set %s on %s's side", spikes_, foe_side.active_pokemon)

class spikyshield(Move):
    def __init__(self):
        super(spikyshield, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.GRASS
        self.is_protectable = False
        self.targets_user = True
        self.priority = 4

    def check_success(self, user, _, engine):
        target = engine.get_foe(user)
        if target is None or not target.will_move_this_turn:
            return FAIL
        if user.has_effect(Volatile.STALL):
            return user.get_effect(Volatile.STALL).check_stall_success()

    def on_success(self, user, target, engine):
        user.set_effect(effects.SpikyShield())
        user.set_effect(effects.StallCounter())

class splash(Move):
    def __init__(self):
        super(splash, self).__init__()
        self.max_pp = _MAX_PP[40]
        self.category = STATUS
        self.type = Type.WATER
        self.is_protectable = False
        self.targets_user = True

class spore(Move):
    def __init__(self):
        super(spore, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.GRASS
        self.accuracy = 100
        self.target_status = Status.SLP
        self.is_powder = True
        self.is_bounceable = True

class stealthrock(Move):
    def __init__(self):
        super(stealthrock, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.ROCK
        self.is_protectable = False
        self.is_bounceable = True
        self.ignore_substitute = True
        self.targets_user = True

    def on_success(self, user, _, engine):
        foe_side = engine.get_foe_side(user)
        if not foe_side.has_effect(Hazard.STEALTHROCK):
            if __debug__: log.i('Set up StealthRock on side %d', foe_side.index)
            foe_side.set_effect(effects.StealthRock())
        else:
            return FAIL

class steameruption(Move):
    def __init__(self):
        super(steameruption, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 95
        self.base_power = 110
        self.thaw_user = True
        self.thaw_target = True
        self.secondary_effects = SecondaryEffect(30, status=Status.BRN),

class stickyweb(Move):
    def __init__(self):
        super(stickyweb, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.BUG
        self.is_protectable = False
        self.is_bounceable = True
        self.ignore_substitute = True
        self.targets_user = True

    def on_success(self, user, _, engine):
        foe_side = engine.get_foe_side(user)
        if not foe_side.has_effect(Hazard.STICKYWEB):
            if __debug__: log.i('Set up StickyWeb on side %d', foe_side.index)
            foe_side.set_effect(effects.StickyWeb())
        else:
            return FAIL

class stoneedge(Move):
    def __init__(self):
        super(stoneedge, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.ROCK
        self.accuracy = 80
        self.base_power = 100
        self.crit_ratio = True

class storedpower(Move):
    def __init__(self):
        super(storedpower, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.PSYCHIC
        self.accuracy = 100

    def get_base_power(self, user, target, engine):
        if __debug__: log.i("storedpower's power is %d" %
                            (20+20*sum(boost for boost in user.boosts.values() if boost > 0)))
        return 20 + 20 * sum(boost for boost in user.boosts.values() if boost > 0)

class stormthrow(Move):
    def __init__(self):
        super(stormthrow, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 60
        self.always_crit = True

class struggle(Move):
    def __init__(self):
        super(struggle, self).__init__()
        self.max_pp = 0
        self.category = PHYSICAL
        self.type = Type['???']
        self.makes_contact = True
        self.base_power = 50
        self.on_success_ignores_substitute = True

    def on_success(self, user, target, engine):
        if not user.is_fainted():
            engine.direct_damage(user, user.max_hp / 4.0)

class stunspore(Move):
    def __init__(self):
        super(stunspore, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = STATUS
        self.type = Type.GRASS
        self.accuracy = 75
        self.is_powder = True
        self.is_bounceable = True
        self.target_status = Status.PAR

class substitute(Move):
    def __init__(self):
        super(substitute, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if user.has_effect(Volatile.SUBSTITUTE) or user.hp <= user.max_hp / 4 or user.hp == 1:
           return FAIL

    def on_success(self, user, _, engine):
        engine.direct_damage(user, user.max_hp / 4.0)
        user.set_effect(effects.Substitute(user.max_hp / 4))

class suckerpunch(Move):
    def __init__(self):
        super(suckerpunch, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.DARK
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80
        self.priority = 1

    def check_success(self, user, target, engine):
        if not target.will_move_this_turn:
            return FAIL
        for event in engine.event_queue:
            if (event.type is Decision.MOVE and
                event.pokemon is target and
                event.move.category is not STATUS
            ):
                return
        return FAIL

class sunnyday(Move):
    def __init__(self):
        super(sunnyday, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.FIRE
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if engine.battlefield.weather is Weather.SUNNYDAY:
            return FAIL

    def on_success(self, user, _, engine):
        duration = 8 if user.item is itemdex['heatrock'] else 5
        engine.battlefield.set_weather(Weather.SUNNYDAY, duration)

class superfang(Move):
    def __init__(self):
        super(superfang, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 90
        self.makes_contact = True
        self.has_damage_callback = True

    def damage_callback(self, user, target):
        return (target.hp / 2) or 1

class superpower(Move):
    def __init__(self):
        super(superpower, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.base_power = 120
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True
        self.user_boosts = Boosts(atk=-1, def_=-1)

class surf(Move):
    def __init__(self):
        super(surf, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 100
        self.base_power = 90

class sweetkiss(Move):
    def __init__(self):
        super(sweetkiss, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.FAIRY
        self.accuracy = 75
        self.is_bounceable = True

    def on_success(self, user, target, engine):
        target.confuse(self.infiltrates)

class switcheroo(Move):
    def __init__(self):
        super(switcheroo, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.DARK
        self.accuracy = 100

    def check_success(self, user, target, engine):
        if ((user.item is not None and not user.item.removable) or
            (target.item is not None and not target.item.removable) or
            target.ability.name == 'stickyhold'
        ):
            return FAIL

    def on_success(self, user, target, engine):
        user_item = None if user.item is None else user.take_item()
        target_item = None if target.item is None else target.take_item()
        assert FAIL not in (user_item, target_item)

        if target_item is not None:
            user.set_item(target_item)
        if user_item is not None:
            target.set_item(user_item)

        if __debug__: log.i('%s got a %s and %s got a %s' %
                            (user, target_item, target, user_item))

class swordsdance(Move):
    def __init__(self):
        super(swordsdance, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(atk=2)

class synthesis(Move):
    def __init__(self):
        super(synthesis, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.GRASS
        self.is_protectable = False
        self.targets_user = True

    on_success = moonlight.on_success.__func__

class tailglow(Move):
    def __init__(self):
        super(tailglow, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.BUG
        self.is_protectable = False
        self.targets_user = True
        self.user_boosts = Boosts(spa=3)

class tailslap(Move):
    def __init__(self):
        super(tailslap, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.NORMAL
        self.accuracy = 85
        self.makes_contact = True
        self.base_power = 25
        self.multihit = (2, 2, 3, 3, 4, 5)

class tailwind(Move):
    def __init__(self):
        super(tailwind, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.FLYING
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if user.side.has_effect(SideCondition.TAILWIND):
            return FAIL

    def on_success(self, user, _, engine):
        user.side.set_effect(effects.Tailwind())

class taunt(Move):
    def __init__(self):
        super(taunt, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.DARK
        self.is_bounceable = True
        self.ignore_substitute = True
        self.accuracy = 100

    def check_success(self, user, target, engine):
        if target.has_effect(Volatile.TAUNT):
            return FAIL

    def on_success(self, user, target, engine):
        duration = 3 if target.will_move_this_turn else 4
        target.set_effect(effects.Taunt(duration))

class technoblast(Move):
    def __init__(self):
        super(technoblast, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 120

    def on_modify_move(self, user, target, engine):
        if user.item is not None:
            self.type = user.item.drive_type or Type.NORMAL

class thunder(Move):
    def __init__(self):
        super(thunder, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.ELECTRIC
        self.base_power = 110
        self.secondary_effects = SecondaryEffect(30, status=Status.PAR),

    on_modify_move = hurricane.on_modify_move.__func__

class thunderbolt(Move):
    def __init__(self):
        super(thunderbolt, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = SPECIAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.base_power = 90
        self.secondary_effects = SecondaryEffect(10, status=Status.PAR),

class thunderpunch(Move):
    def __init__(self):
        super(thunderpunch, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 75
        self.is_punch = True
        self.secondary_effects = SecondaryEffect(10, status=Status.PAR),

class thunderwave(Move):
    def __init__(self):
        super(thunderwave, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.is_bounceable = True
        self.target_status = Status.PAR
        # TODO: verify exception to "status -> ignore immunity" rule

class toxic(Move):
    def __init__(self):
        super(toxic, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.POISON
        self.is_bounceable = True
        self.target_status = Status.TOX

    def on_modify_move(self, user, target, engine):
        if Type.POISON in user.types:
            self.accuracy = None
        else:
            self.accuracy = 90

class toxicspikes(Move):
    def __init__(self):
        super(toxicspikes, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.POISON
        self.is_protectable = False
        self.is_bounceable = True
        self.ignore_substitute = True
        self.targets_user = True

    def on_success(self, user, _, engine):
        foe_side = engine.get_foe_side(user)
        toxicspikes_ = foe_side.get_effect(Hazard.TOXICSPIKES)
        if toxicspikes_ is None:
            if __debug__: log.i('Set up ToxicSpikes(layers=1) on side %d', foe_side.index)
            foe_side.set_effect(effects.ToxicSpikes())
        else:
            if toxicspikes_.layers == 2:
                return FAIL
            if __debug__: log.i('Set up ToxicSpikes(layers=2) on side %d', foe_side.index)
            toxicspikes_.layers = 2

class transform(Move):
    def __init__(self):
        super(transform, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False

    def on_success(self, user, foe, engine):
        user.transform_into(foe, engine)
        user.set_effect(effects.Transformed())

class triattack(Move):
    def __init__(self):
        super(triattack, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(20, callback=self.secondary),

    STATUS = [Status.BRN, Status.PAR, Status.FRZ]

    def secondary(self, target, user, engine):
        roll = random.randrange(3)
        engine.apply_secondary_effect(target, SecondaryEffect(100, status=self.STATUS[roll]),
                                      user)

class trick(Move):
    def __init__(self):
        super(trick, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.accuracy = 100

    check_success = switcheroo.check_success.__func__
    on_success = switcheroo.on_success.__func__

class trickroom(Move):
    def __init__(self):
        super(trickroom, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = STATUS
        self.type = Type.PSYCHIC
        self.is_protectable = False
        self.targets_user = True
        self.priority = -7

    def on_success(self, user, _, engine):
        battlefield = engine.battlefield
        if battlefield.has_effect(PseudoWeather.TRICKROOM):
            battlefield.remove_effect(PseudoWeather.TRICKROOM)
        else:
            battlefield.set_effect(effects.TrickRoom())

class uturn(Move):
    def __init__(self):
        super(uturn, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = PHYSICAL
        self.type = Type.BUG
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 70
        self.switch_user = True

class vacuumwave(Move):
    def __init__(self):
        super(vacuumwave, self).__init__()
        self.max_pp = _MAX_PP[30]
        self.category = SPECIAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.base_power = 40
        self.priority = 1

class vcreate(Move):
    def __init__(self):
        super(vcreate, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = PHYSICAL
        self.type = Type.FIRE
        self.accuracy = 95
        self.makes_contact = True
        self.base_power = 180
        self.user_boosts = Boosts(def_=-1, spd=-1, spe=-1)

class voltswitch(Move):
    def __init__(self):
        super(voltswitch, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.base_power = 70
        self.switch_user = True

class wakeupslap(Move):
    def __init__(self):
        super(wakeupslap, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = PHYSICAL
        self.type = Type.FIGHTING
        self.accuracy = 100
        self.makes_contact = True

    def get_base_power(self, user, target, engine):
        if target.status is Status.SLP:
            return 140
        return 70

    def on_success(self, user, target, engine):
        if target.status is Status.SLP:
            target.cure_status()

class waterfall(Move):
    def __init__(self):
        super(waterfall, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.WATER
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(20, volatile=Volatile.FLINCH),

class waterpulse(Move):
    def __init__(self):
        super(waterpulse, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 100
        self.base_power = 60
        self.is_pulse = True
        self.secondary_effects = SecondaryEffect(20, volatile=Volatile.CONFUSE),

class waterspout(Move):
    def __init__(self):
        super(waterspout, self).__init__()
        self.max_pp = _MAX_PP[5]
        self.category = SPECIAL
        self.type = Type.WATER
        self.accuracy = 100

    def get_base_power(self, user, target, engine):
        return (150 * float(user.hp) / user.max_hp) or 1

class weatherball(Move):
    def __init__(self):
        super(weatherball, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = SPECIAL
        self.type = Type.NORMAL
        self.accuracy = 100
        self.is_bullet = True

    WEATHER_TYPE = {Weather.SUNNYDAY: Type.FIRE,
                    Weather.DESOLATELAND: Type.FIRE,
                    Weather.RAINDANCE: Type.WATER,
                    Weather.PRIMORDIALSEA: Type.WATER,
                    Weather.SANDSTORM: Type.ROCK,
                    Weather.HAIL: Type.ICE,
                    None: Type.NORMAL}

    def get_base_power(self, user, target, engine):
        if engine.battlefield.weather:
            return 100
        return 50

    def on_modify_move(self, user, target, engine):
        self.type = self.WEATHER_TYPE[engine.battlefield.weather]

class whirlwind(Move):
    def __init__(self):
        super(whirlwind, self).__init__()
        self.max_pp = _MAX_PP[20]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.is_bounceable = True
        self.ignore_substitute = True
        self.priority = -6

    def on_success(self, user, target, engine):
        return engine.force_random_switch(target, user)

class wildcharge(Move):
    def __init__(self):
        super(wildcharge, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.ELECTRIC
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 90
        self.recoil = 25

class willowisp(Move):
    def __init__(self):
        super(willowisp, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = STATUS
        self.type = Type.FIRE
        self.accuracy = 85
        self.is_bounceable = True
        self.target_status = Status.BRN

class wish(Move):
    def __init__(self):
        super(wish, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = False
        self.targets_user = True

    def check_success(self, user, _, engine):
        if user.side.has_effect(SideCondition.WISH):
            return FAIL

    def on_success(self, user, _, engine):
        user.side.set_effect(effects.Wish(user.max_hp / 2))

class woodhammer(Move):
    def __init__(self):
        super(woodhammer, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.GRASS
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 120
        self.recoil = 33

class xscissor(Move):
    def __init__(self):
        super(xscissor, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.BUG
        self.accuracy = 100
        self.makes_contact = True
        self.base_power = 80

class yawn(Move):
    def __init__(self):
        super(yawn, self).__init__()
        self.max_pp = _MAX_PP[10]
        self.category = STATUS
        self.type = Type.NORMAL
        self.is_protectable = True
        self.is_bounceable = True

    def check_success(self, user, target, engine):
        if target.status is not None or target.is_immune_to(Status.SLP):
            return FAIL

    def on_success(self, user, target, engine):
        target.set_effect(effects.Yawn())

class zenheadbutt(Move):
    def __init__(self):
        super(zenheadbutt, self).__init__()
        self.max_pp = _MAX_PP[15]
        self.category = PHYSICAL
        self.type = Type.PSYCHIC
        self.accuracy = 90
        self.makes_contact = True
        self.base_power = 80
        self.secondary_effects = SecondaryEffect(20, volatile=Volatile.FLINCH),

movedex = {name.rstrip('_'): obj() for name, obj in vars().items()
           if not name.startswith('_') and
           inspect.isclass(obj) and
           issubclass(obj, Move) and
           obj not in (Move, hiddenpower)}

for name, move in movedex.items():
    if name.startswith('hiddenpower'):
        movedex['%s60' % name] = move # Showdown likes to call them e.g. hiddenpowerice60 in some
                                      # contexts, because in previous gens they had different power
