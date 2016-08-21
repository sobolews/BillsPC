import random
from collections import Counter
from copy import deepcopy

from battle.battleengine import Battle
from battle.battlepokemon import BattlePokemon
from battle.rolloutpolicy import RandomRolloutPolicy
from bot.unrevealedpokemon import UNREVEALED
from showdowndata import pokedex, type_index
from showdowndata.rbstats import rbstats, rbstats_key
from battle.items import itemdex
from battle.abilities import abilitydex
from battle.moves import movedex
from battle.enums import Type
from battle.stats import Boosts
from _logging import log, no_console_log


class BattleRoller(object):
    def __init__(self, my_player):
        self._cache = {}
        self.my_player = my_player

    def rollout_battles(self, battlefield, num_rollouts, turn_initialized):
        clone = deepcopy(battlefield)
        self.fill_in_unrevealed(clone)

        # sanitize state for Battle assumptions
        for side in clone.sides:
            if side.active_pokemon.is_fainted():
                side.active_pokemon = None
            for pokemon in side.team:
                if pokemon.is_fainted():
                    if pokemon._effect_index:
                        pokemon._effect_index.clear()
                        pokemon.effect_handlers = {key: list() for key in pokemon.effect_handlers}
                    pokemon.boosts = Boosts()
                    pokemon.is_active = False

        log.i('Rolling out battle: my_player=%d, turn_initialized=%s, turn=%d',
              self.my_player, turn_initialized, battlefield.turns)

        wins = Counter()
        for _ in range(num_rollouts):
            winner = self.rollout_one_battle(clone, turn_initialized)
            wins[winner] += 1

        log.i('rollout results: %s', sorted(wins.items()))
        return wins

    @no_console_log
    def rollout_one_battle(self, battlefield, turn_initialized):
        """
        Create a Battle from the client's battlefield, and run the game forward.
        If turn_initialized, then skip running Battle.init_turn for the next turn.
        """
        clone = deepcopy(battlefield)
        battle = Battle.from_battlefield(clone, *[RandomRolloutPolicy(i) for i in range(2)])

        if turn_initialized:
            battle.run_initialized_turn() # run the next turn without initializing it
        return battle.run_battle()        # complete the battle and return the winner

    def fill_in_unrevealed(self, battlefield):
        """
        Fill in the unrevealed moves/abilities/item of known foe pokemon with their most probable
        values (based on rbstats). Generate remaining unrevealed foe pokemon with a type that
        balances the foe's team.
        """
        foe_side = battlefield.sides[not self.my_player]
        foe_team = foe_side.team
        foe_names = tuple(foe.name for foe in foe_side.team)
        cached = self._cache.get(foe_names)

        for i, foe in enumerate(foe_team):
            if foe.is_fainted():
                continue
            if foe.name == UNREVEALED:
                if cached:
                    foe_team[i] = deepcopy(cached[i])
                    foe_team[i].side = foe_side
                else:
                    foe_team[i] = create_foe_for_rollout(foe_side)
            else:
                fill_in_unrevealed_attrs(foe)

        if not cached:
            self._cache.clear()
            self._cache[foe_names] = deepcopy(foe_team)


def fill_in_unrevealed_attrs(foe):
    attrs, all_known = foe.known_attrs()
    if all_known:
        return

    log.d("Filling in %s's attrs: %s", foe, attrs)
    rb_index = rbstats_key(foe)

    if foe.item == itemdex['_unrevealed_']:
        probability = {rbstats.attr_probability(rb_index, item, attrs): item
                       for item in rbstats[rb_index]['item']}
        item = itemdex[probability[max(probability)]]
        foe.item = item
        if foe.is_active:
            foe.set_effect(item())
        attrs.append(item.name)

    if foe.ability == abilitydex['_unrevealed_']:
        probability = {rbstats.attr_probability(rb_index, ability, attrs): ability
                       for ability in rbstats[rb_index]['ability']}
        ability = abilitydex[probability[max(probability)]]
        foe.base_ability = foe.ability = ability
        if foe.is_active:
            foe.set_effect(ability())
        attrs.append(ability.name)

    while len(foe.moves) < 4:
        probability = {rbstats.attr_probability(rb_index, move, attrs): move
                       for move in rbstats[rb_index]['moves'] if not movedex[move] in foe.moves}
        move = movedex[probability[max(probability)]]
        foe.moves[move] = move.max_pp
        attrs.append(move.name)

    log.d("Filled in: %s", attrs)

def create_foe_for_rollout(foe_side):
    foe_team = [foe for foe in foe_side.team if foe.name != UNREVEALED]
    foe_types = filter(None, [type for foe in foe_team for type in foe.types])
    allow_mega = not any(foe.item is not None and foe.item.is_mega_stone for foe in foe_team)
    name = get_balancing_pokemon(foe_types)

    stats = rbstats[name]
    level = max(stats['level'], key=stats['level'].get) if allow_mega else max(stats['level'])
    if allow_mega:
        attrs = max(stats['sets'], key=stats['sets'].get)
    else:
        attrs = next(attrs for attrs, _ in stats['sets'].most_common()
                     if not itemdex[attrs[5]].is_mega_stone)
    moves = [movedex[move] for move in attrs[:4]]
    ability = abilitydex[attrs[4]]
    item = itemdex[attrs[5]]
    pokemon = BattlePokemon(pokedex[name], level, moves, ability, item, side=foe_side)

    log.d("Created foe: %s (%s, %s, %s)", pokemon, moves, ability, item)
    return pokemon

COMPLEMENT = {
    Type.NORMAL: (Type.FIGHTING, Type.GHOST, Type.STEEL, Type.ROCK),
    Type.FIGHTING: (Type.NORMAL, Type.GHOST, Type.PSYCHIC, Type.DRAGON),
    Type.FLYING: (Type.ELECTRIC, Type.ICE, Type.GROUND, Type.ROCK),
    Type.POISON: (Type.GROUND, Type.FAIRY, Type.PSYCHIC, Type.DARK),
    Type.GROUND: (Type.ELECTRIC, Type.FLYING, Type.ICE, Type.POISON),
    Type.ROCK: (Type.GRASS, Type.BUG, Type.FLYING, Type.WATER),
    Type.BUG: (Type.FIRE, Type.FLYING, Type.ROCK, Type.GHOST),
    Type.GHOST: (Type.NORMAL, Type.DARK, Type.PSYCHIC, Type.BUG),
    Type.STEEL: (Type.FIRE, Type.GROUND, Type.FAIRY, Type.POISON),
    Type.FIRE: (Type.WATER, Type.GRASS, Type.STEEL, Type.ROCK),
    Type.WATER: (Type.FIRE, Type.GRASS, Type.ELECTRIC, Type.STEEL),
    Type.GRASS: (Type.FIRE, Type.WATER, Type.DRAGON, Type.ELECTRIC),
    Type.ELECTRIC: (Type.GROUND, Type.FLYING, Type.WATER, Type.POISON),
    Type.PSYCHIC: (Type.DARK, Type.GHOST, Type.BUG, Type.NORMAL),
    Type.ICE: (Type.STEEL, Type.FIGHTING, Type.DRAGON, Type.GRASS),
    Type.DRAGON: (Type.ICE, Type.FAIRY, Type.NORMAL, Type.BUG),
    Type.DARK: (Type.FIGHTING, Type.PSYCHIC, Type.FAIRY, Type.ICE),
    Type.FAIRY: (Type.DRAGON, Type.DARK, Type.FIGHTING, Type.POISON),
}

EXCLUDED = frozenset(pokemon for pokemon in pokedex if
                     (pokemon.endswith('mega') or
                      pokemon.endswith('megax') or
                      pokemon.endswith('megay') or
                      pokemon.endswith('primal') or
                      pokemon == 'ditto' or
                      pokemon == 'zoroark') and not
                     pokemon.lower() == 'yanmega')

# Create type index excluding megas, primals, ditto, and zoroark.
# megas/primals are included in the base formes via the megastone/orb,
# and ditto/zoroark are excluded for simplicity.
ROLLOUT_TYPE_INDEX = {}
for types, values in type_index.items():
    for pokemon in values:
        if pokemon in rbstats and pokemon not in EXCLUDED:
            ROLLOUT_TYPE_INDEX.setdefault(types, []).append(pokemon)

def get_balancing_pokemon(foe_types):
    preferred = get_balancing_types(foe_types)
    type1 = preferred[0]
    for type2 in preferred[1:]:
        match = ROLLOUT_TYPE_INDEX.get((type1, type2))
        if match:
            break
    else:
        match = ROLLOUT_TYPE_INDEX.get((type1, None))
    assert match, foe_types
    return random.choice(match)

EMPTY_COUNTER = Counter(dict.fromkeys(Type.values, 0)) # initialized to 0
def get_balancing_types(types):
    votes = EMPTY_COUNTER.copy()
    for type in types:
        votes[type] -= 100
        for other_type in COMPLEMENT[type]:
            votes[other_type] += 1

    sorted_votes = votes.most_common()
    log.d("votes=%s", [(k, v) for k, v in sorted_votes if v != 0])
    max_votes = sorted_votes[0][1]
    i = -1
    for i, item in enumerate(sorted_votes):
        if max_votes - item[1] > 1:
            break
    return [vote[0] for vote in sorted_votes[:i]]
