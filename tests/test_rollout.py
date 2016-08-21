from copy import deepcopy

from AI.rollout import BattleRoller
from bot.tests.test_battleclient import BaseTestBattleClient
from battle.battlepokemon import BattlePokemon
from battle.items import itemdex
from battle.abilities import abilitydex
from battle.moves import movedex
from battle.enums import ITEM, ABILITY

class TestRollout(BaseTestBattleClient):
    def setUp(self):
        super(TestRollout, self).setUp()
        self.set_up_turn_0()
        self.roller = BattleRoller(self.my_player)

    def test_fill_in_foe_team(self):
        clone = deepcopy(self.battlefield)
        goodra = clone.sides[1].active_pokemon
        self.assertEqual(goodra.name, 'goodra')
        self.roller.fill_in_unrevealed(clone)

        self.assertIsNotNone(goodra.item)
        self.assertNotEqual(goodra.item, itemdex['_unrevealed_'])
        self.assertTrue(goodra.has_effect(ITEM))
        self.assertEqual(len(goodra.moves), 4)

        team = clone.sides[1].team
        foe1 = team[1]
        self.assertEqual(type(foe1), BattlePokemon)
        self.assertIsNotNone(foe1.item)
        self.assertNotEqual(foe1.item, itemdex['_unrevealed_'])
        self.assertFalse(foe1.has_effect(ITEM))
        self.assertEqual(len(foe1.moves), 4)
        self.assertIn(foe1.moves.keys()[0], movedex.values())
        self.assertIsNotNone(foe1.ability)
        self.assertNotEqual(foe1.ability, abilitydex['_unrevealed_'])
        self.assertFalse(foe1.has_effect(ABILITY))

        # only zero or one mega:
        self.assertIn(len([pokemon for pokemon in team if
                           pokemon.item and pokemon.item.is_mega_stone]), [0, 1])

    def test_fill_in_foe_team_caching(self):
        turn1 = deepcopy(self.battlefield)
        self.roller.fill_in_unrevealed(turn1)

        self.handle('|move|p1a: Hitmonchan|Mach Punch|p2a: Goodra')
        self.handle('|-damage|p2a: Goodra|55/100')
        self.handle('|turn|2')
        turn2 = deepcopy(self.battlefield)
        self.roller.fill_in_unrevealed(turn2)

        team1 = turn1.sides[1].team
        team2 = turn2.sides[1].team
        for i in range(6):
            # The foe's team didn't change, so use the same one cached from before
            self.assertEqual(team1[i].name, team2[i].name)
            self.assertListEqual(sorted([move.name for move in team1[i].moves]),
                                 sorted([move.name for move in team2[i].moves]))
            self.assertEqual(team1[i].item.name, team2[i].item.name)
            self.assertEqual(team1[i].ability.name, team2[i].ability.name)

        self.handle('|switch|p2a: Ludicolo|Ludicolo, L81, M|100/100')
        self.handle('|turn|3')
        turn3 = deepcopy(self.battlefield)
        team3 = turn3.sides[1].team
        self.roller.fill_in_unrevealed(turn3)

        # don't use the cached foe team now that the real one has changed
        self.assertFalse(all(team2[i].name == team3[i].name for i in range(1, 6)))
