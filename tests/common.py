from unittest import TestCase

from battle.enums import Status, ABILITY, ITEM
from battle.abilities import abilitydex
from battle.items import itemdex
from battle.moves import movedex


class TestCaseCommon(TestCase):
    """
    Test case base class providing helper methods for testing
    """
    def assertDamageTaken(self, pokemon, damage=None):
        if damage is None:
            self.assertLess(pokemon.hp, pokemon.max_hp)
        else:
            self.assertEqual(pokemon.hp, pokemon.max_hp - damage)

    def assertStatus(self, pokemon, status):
        self.assertEqual(pokemon.status, status)
        if status not in (None, Status.FNT):
            self.assertTrue(pokemon.has_effect(status))
        if status is None:
            for status in Status.values:
                self.assertFalse(pokemon.has_effect(status))

    def assertFainted(self, pokemon):
        self.assertEqual(pokemon.status, Status.FNT)
        self.assertLessEqual(pokemon.hp, 0)
        self.assertTrue(pokemon.is_fainted())

    def assertBoosts(self, pokemon, boosts):
        self.assertDictContainsSubset(boosts, pokemon.boosts)

    def assertMoveChoices(self, pokemon, moves):
        moves = set([movedex[move] if isinstance(move, str) else move for move in moves])
        self.assertSetEqual(set(pokemon.get_move_choices()), moves)

    def assertSwitchChoices(self, pokemon, choices):
        self.assertSetEqual(set(pokemon.get_switch_choices()), choices)

    def assertAbility(self, pokemon, ability):
        ability = abilitydex[ability]
        self.assertEqual(pokemon.ability, ability)
        self.assertEqual(pokemon.get_effect(ABILITY).name, ability.name)

    def assertPpUsed(self, pokemon, move, pp):
        move = movedex[move]
        self.assertEqual(pokemon.pp[move], move.max_pp - pp)

    def assertItem(self, pokemon, item):
        self.assertEqual(pokemon.item, itemdex.get(item))
        if item is None:
            self.assertFalse(pokemon.has_effect(ITEM))
        elif pokemon.is_active:
            held = pokemon.get_effect(ITEM)
            self.assertIsNotNone(held)
            self.assertEqual(held.name, item)

    def assertActive(self, pokemon):
        self.assertTrue(pokemon.is_active)
        for teammate in pokemon.side.team:
            if teammate is not pokemon:
                self.assertFalse(teammate.is_active)

        self.assertIs(pokemon.side.active_pokemon, pokemon)
