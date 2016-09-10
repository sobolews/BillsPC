from AI.matrixtree import (BreakpointBattle, new_node, BreakNewTurn, MatrixNodeNewTurn,
                           MatrixNodeMustSwitch, MatrixNodePostFaintSwitch,
                           MatrixNodeDoublePostFaintSwitch)
from AI.actions import SwitchAction
from bot.battleclient import BattleClient
from bot.foeside import FoeBattleSide, UnrevealedPokemon
from battle import effects
from battle.battlefield import BattleField
from battle.enums import Decision, Hazard
from tests.common import TestCaseCommon


MY_TEAM = {
    "rqid":1,
    "active": [{"moves":[
        {"move":"Gunk Shot","id":"gunkshot","pp":8,"maxpp":8,"target":"normal","disabled":False},
        {"move":"Knock Off","id":"knockoff","pp":32,"maxpp":32,"target":"normal","disabled":False},
        {"move":"Superpower","id":"superpower","pp":8,"maxpp":8,"target":"normal","disabled":False},
        {"move":"Parting Shot","id":"partingshot","pp":32,"maxpp":32,"target":"normal","disabled":False}
    ]}],
    "side":{"name":"0raichu","id":"p1","pokemon":
            [{"ident":"p1: Pangoro","active":True,
              "details":"Pangoro, L78, M","condition":"276/276",
              "stats":{"atk":239,"def":167,"spa":153,"spd":156,"spe":136},
              "moves":["gunkshot","knockoff","superpower","partingshot"],
              "baseAbility":"scrappy",
              "item":"lifeorb"},
             {"ident":"p1: Zoroark","active":False,
              "details":"Zoroark, L78, M","condition":"222/222",
              "stats":{"atk":209,"def":139,"spa":232,"spd":139,"spe":209},
              "moves":["darkpulse","uturn","knockoff","trick"],
              "baseAbility":"illusion",
              "item":"choicescarf"},
             {"ident":"p1: Dewgong","active":False,
              "details":"Dewgong, L83, M","condition":"285/285",
              "stats":{"atk":121,"def":180,"spa":164,"spd":205,"spe":164},
              "moves":["encore","toxic","surf","icebeam"],
              "baseAbility":"thickfat",
              "item":"leftovers"},
             {"ident":"p1: Wormadam","active":False,
              "details":"Wormadam-Trash, L83, F","condition":"235/235",
              "stats":{"atk":162,"def":205,"spa":162,"spd":205,"spe":64},
              "moves":["toxic","protect","stealthrock","gyroball"],
              "baseAbility":"overcoat",
              "item":"leftovers"},
             {"ident":"p1: Infernape","active":False,
              "details":"Infernape, L77, M","condition":"244/244",
              "stats":{"atk":205,"def":154,"spa":205,"spd":154,"spe":211},
              "moves":["fireblast","grassknot","uturn","closecombat"],
              "baseAbility":"blaze",
              "item":"expertbelt"},
             {"ident":"p1: Talonflame","active":False,
              "details":"Talonflame, L75, F","condition":"241/241",
              "stats":{"atk":165,"def":150,"spa":155,"spd":147,"spe":233},
              "moves":["swordsdance","roost","bravebird","flareblitz"],
              "baseAbility":"galewings",
              "item":"sharpbeak"}]}
}

FOE_TEAM = {
    "rqid":1,
    "active":[{"moves":[
        {"move":"Earthquake","id":"earthquake","pp":16,"maxpp":16,"target":"allAdjacent","disabled":False},
        {"move":"Stone Edge","id":"stoneedge","pp":8,"maxpp":8,"target":"normal","disabled":False},
        {"move":"Stealth Rock","id":"stealthrock","pp":32,"maxpp":32,"target":"normal","disabled":False},
        {"move":"Double-Edge","id":"doubleedge","pp":24,"maxpp":24,"target":"normal","disabled":False}]}],
    "side":{"name":"0raichu","id":"p1","pokemon":
            [{"ident":"p1: Marowak","active":True,
              "details":"Marowak, L83, M","condition":"235/235",
              "stats":{"atk":180,"def":230,"spa":131,"spd":180,"spe":122},
              "moves":["earthquake","stoneedge","stealthrock","doubleedge"],
              "baseAbility":"rockhead",
              "item":"thickclub"},
             {"ident":"p1: Probopass","active":False,
              "details":"Probopass, L83, M","condition":"235/235",
              "stats":{"atk":96,"def":288,"spa":172,"spd":297,"spe":114},
              "moves":["toxic","painsplit","stealthrock","flashcannon"],
              "baseAbility":"magnetpull",
              "item":"airballoon"},
             {"ident":"p1: Registeel","active":False,
              "details":"Registeel, L79","condition":"256/256",
              "stats":{"atk":164,"def":283,"spa":164,"spd":283,"spe":125},
              "moves":["ironhead","protect","toxic","thunderwave"],
              "baseAbility":"clearbody",
              "item":"leftovers"},
             {"ident":"p1: Azumarill","active":False,
              "details":"Azumarill, L75, F","condition":"274/274",
              "stats":{"atk":119,"def":164,"spa":134,"spd":164,"spe":119},
              "moves":["aquajet","waterfall","superpower","knockoff"],
              "baseAbility":"hugepower",
              "item":"choiceband"},
             {"ident":"p1: Ho-Oh","active":False,
              "details":"Ho-Oh, L73","condition":"275/275",
              "stats":{"atk":232,"def":174,"spa":203,"spd":267,"spe":174},
              "moves":["earthquake","roost","bravebird","sacredfire"],
              "baseAbility":"regenerator",
              "item":"leftovers"},
             {"ident":"p1: Infernape","active":False,
              "details":"Infernape, L77, F","condition":"244/244",
              "stats":{"atk":205,"def":154,"spa":205,"spd":154,"spe":211},
              "moves":["machpunch","closecombat","swordsdance","flareblitz"],
              "baseAbility":"ironfist",
              "item":"lifeorb"}]}
}


class TestMatrixTree(TestCaseCommon):
    # borrow BattleClient for its team-generation functions
    bc = BattleClient('test-player', 'test-room', lambda: None)
    revealed_foes = 2

    def setUp(self):
        self.my_side = self.bc.build_my_side(MY_TEAM)

        self.original_foe_side = self.bc.build_my_side(FOE_TEAM)
        foe_team = [UnrevealedPokemon() for _ in range(6)]
        foe_team[:self.revealed_foes] = self.original_foe_side.team[:self.revealed_foes]

        self.foe_side = FoeBattleSide(foe_team, 1, 'test-foe')

        self.battlefield = BattleField(self.my_side, self.foe_side)
        # pass empty tuples to cause error if the battle tries to make its own rollout decisions
        self.battle = BreakpointBattle.from_battlefield(self.battlefield, (), ())

        with self.assertRaises(BreakNewTurn) as ex:
            self.battle.run_new_battle()
        self.breakpoint = ex.exception
        self.root = new_node(ex.exception.state)(self.battle, depth=0, breakpoint=ex.exception)

    def find_cell(self, parent, p0=None, p1=None):
        matrix = parent.matrix
        if parent.simultaneous:
            row = next(row for row in matrix if p0 is None or
                       p0 == self.get_action_id(row[0].row_action))
            cell = next(col for col in row if p1 is None or
                        p1 == self.get_action_id(col.col_action))
        elif p0:
            cell = next(cell for cell in matrix[0] if
                        p0 == self.get_action_id(cell.row_action))
        else:
            assert p1
            cell = next(cell for cell in matrix[0] if
                        p1 == self.get_action_id(cell.col_action))
        return cell

    def find_and_expand_cell(self, parent, p0=None, p1=None):
        cell = self.find_cell(parent, p0, p1)
        parent.expand_cell(cell)
        return cell

    def get_action_id(self, action):
        return action.move_name if action.action_type == Decision.MOVE else action.incoming_name

    def get_field(self, node):
        return node.battle.battlefield

    def get_side(self, node, index):
        return self.get_field(node).sides[index]

    def get_active(self, node, index):
        return self.get_side(node, index).active_pokemon

    def get_pokemon(self, node, name):
        return next(pokemon for pokemon in
                    self.get_side(node, 0).team + self.get_side(node, 1).team if
                    pokemon.name == name)

    def child_battlefield(self, parent, p0=None, p1=None):
        cell = self.find_cell(parent, p0, p1)
        return cell.node.battle.battlefield


class TestFromRootNode(TestMatrixTree):
    def test_initial_breakpoint(self):
        self.assertIsInstance(self.root, MatrixNodeNewTurn)

        self.assertEqual(len(self.root.matrix), 9) # 4 moves + 5 switches
        for row in self.root.matrix:
            self.assertEqual(len(row), 5) # 4 moves, 1 switch

        self.assertEqual(4, sum(row[0].row_action.action_type == Decision.MOVE
                                for row in self.root.matrix)) # 4 moves
        self.assertEqual(5, sum(row[0].row_action.action_type == Decision.SWITCH
                                for row in self.root.matrix)) # 5 switches

        self.assertEqual(4, sum(node.col_action.action_type == Decision.MOVE
                                for node in self.root.matrix[0])) # 4 foe moves
        self.assertEqual(1, sum(node.col_action.action_type == Decision.SWITCH
                                for node in self.root.matrix[0])) # 1 foe switch

    def test_expand_cell_two_moves(self):
        cell = self.find_and_expand_cell(self.root, 'knockoff', 'earthquake')

        self.assertIsInstance(cell.node, MatrixNodeNewTurn)
        self.assertEqual(self.root.depth, 0)
        self.assertEqual(cell.node.depth, 1)

        root_pangoro = self.get_active(self.root, 0)
        cell_pangoro = self.get_active(cell.node, 0)
        self.assertPpUsed(root_pangoro, 'knockoff', 0)
        self.assertPpUsed(cell_pangoro, 'knockoff', 1)

        self.assertDamageTaken(cell_pangoro, 27 + 106) # lifeorb + earthquake

    def test_expand_all_children(self):
        self.root.evaluate(-1)

        field  = self.child_battlefield(self.root, 'dewgong', 'earthquake')
        dewgong = field.sides[0].active_pokemon
        self.assertEqual(dewgong.name, 'dewgong')
        self.assertDamageTaken(dewgong, 198 - dewgong.max_hp / 16)

        field = self.child_battlefield(self.root, 'superpower', 'stealthrock')
        self.assertTrue(field.sides[0].has_effect(Hazard.STEALTHROCK))

    def test_expand_grandchild(self):
        self.root.evaluate(-1)
        cell = self.find_cell(self.root, 'wormadamtrash', 'probopass')
        cell.node.evaluate(-1)
        cell2 = self.find_cell(cell.node, 'protect', 'flashcannon')

        self.assertPpUsed(self.get_active(cell.node, 0), 'protect', 0)
        self.assertPpUsed(self.get_active(cell2.node, 0), 'protect', 1)


class TestMustSwitchNode(TestMatrixTree):
    def setUp(self):
        super(TestMustSwitchNode, self).setUp()

        cell = self.find_and_expand_cell(self.root, 'partingshot', 'earthquake')
        self.msnode = cell.node

    def test_expand_cell_with_must_switch(self):
        self.assertIsInstance(self.msnode, MatrixNodeMustSwitch)
        self.assertEqual(self.msnode.side_index, 0)

        self.assertEqual(len(self.msnode.matrix[0]), 5)
        self.assertTrue(all(isinstance(cell.row_action, SwitchAction)
                            for cell in self.msnode.matrix[0]))

    def test_evaluate_must_switch_node(self):
        cell = self.find_and_expand_cell(self.msnode, p0='dewgong')

        self.assertIsInstance(cell.node, MatrixNodeNewTurn)
        self.assertEqual(cell.node.battle.battlefield.turns, 2)
        dewgong = self.get_pokemon(cell.node, 'dewgong')
        self.assertActive(dewgong)
        self.assertDamageTaken(dewgong)

        cell2 = self.find_and_expand_cell(self.msnode, 'zoroark')

        self.assertIsInstance(cell2.node, MatrixNodeNewTurn)
        self.assertEqual(cell2.node.battle.battlefield.turns, 2)
        zoroark = self.get_pokemon(cell2.node, 'zoroark')
        self.assertActive(zoroark)
        self.assertDamageTaken(zoroark)

    def test_run_moves_after_switch_node(self):
        self.msnode.evaluate(-1)
        node2 = self.find_cell(self.msnode, p0='dewgong').node
        node2.evaluate(-1)
        node3 = self.find_cell(node2, p0='encore', p1='stealthrock').node

        self.assertEqual(self.get_field(node3).turns, 3)
        marowak = self.get_pokemon(node3, 'marowak')
        self.assertPpUsed(marowak, 'earthquake', 2)
        self.assertPpUsed(marowak, 'stealthrock', 0)


class TestPostFaintSwitchNode(TestMatrixTree):
    revealed_foes = 4

    def setUp(self):
        super(TestPostFaintSwitchNode, self).setUp()
        cell = self.find_and_expand_cell(self.root, 'superpower', 'probopass')
        self.pfsnode = cell.node

    def test_expand_cell_with_post_faint_switch(self):
        self.assertIsInstance(self.pfsnode, MatrixNodePostFaintSwitch)
        self.assertEqual(self.pfsnode.side_index, 1)

        self.assertEqual(len(self.pfsnode.matrix[0]), 3)
        self.assertTrue(all(isinstance(cell.col_action, SwitchAction)
                            for cell in self.pfsnode.matrix[0]))
        self.assertTrue(all(cell.row_action is None
                            for cell in self.pfsnode.matrix[0]))
        self.assertEqual(self.get_field(self.pfsnode).turns, 1)

    def test_evaluate_post_faint_switch_node(self):
        cell = self.find_and_expand_cell(self.pfsnode, p1='azumarill')

        self.assertIsInstance(cell.node, MatrixNodeNewTurn)
        self.assertEqual(self.get_field(cell.node).turns, 2)
        self.assertEqual(self.get_active(cell.node, 1).name, 'azumarill')

    def test_evaluate_two_post_faint_switch_nodes_due_to_hazard(self):
        cell = self.find_and_expand_cell(self.root, 'knockoff', 'stealthrock')
        self.get_pokemon(cell.node, 'pangoro').hp = 1
        self.get_pokemon(cell.node, 'dewgong').hp = 1
        cell2 = self.find_and_expand_cell(cell.node, 'knockoff', 'earthquake')

        self.assertIsInstance(cell2.node, MatrixNodePostFaintSwitch)
        cell3 = self.find_and_expand_cell(cell2.node, p0='dewgong')
        self.assertIsInstance(cell3.node, MatrixNodePostFaintSwitch)
        cell4 = self.find_and_expand_cell(cell3.node, p0='talonflame')

        self.assertDamageTaken(self.get_active(cell4.node, 0))
        self.assertEqual(self.get_side(cell4.node, 0).remaining_pokemon, 4)
        self.assertEqual(self.get_field(cell4.node).turns, 3)

    def test_run_moves_after_post_faint_switch(self):
        self.pfsnode.evaluate(-1)
        node2 = self.find_cell(self.pfsnode, p1='marowak').node
        node2.evaluate(-1)

        cell = self.find_cell(node2, 'dewgong', 'earthquake')
        pangoro = self.get_active(cell.node, 0)
        self.assertDamageTaken(pangoro)


class TestDoublePostFaintSwitchNode(TestMatrixTree):
    revealed_foes = 4

    def setUp(self):
        super(TestDoublePostFaintSwitchNode, self).setUp()
        self.get_active(self.root, 0).hp = 1
        self.get_active(self.root, 1).hp = 1

        # double k.o. due to pangoro's lifeorb
        cell = self.find_and_expand_cell(self.root, 'superpower', 'earthquake')
        self.dpfsnode = cell.node

    def test_expand_cell_with_double_post_faint_switch(self):
        self.assertIsInstance(self.dpfsnode, MatrixNodeDoublePostFaintSwitch)
        self.assertEqual(len(self.dpfsnode.matrix), 5)
        self.assertEqual(len(self.dpfsnode.matrix[0]), 3)

        self.assertTrue(all(isinstance(cell.row_action, SwitchAction) and
                            isinstance(cell.col_action, SwitchAction)
                            for row in self.dpfsnode.matrix
                            for cell in row))
        self.assertEqual(self.get_field(self.dpfsnode).turns, 1)

    def test_evaluate_double_post_switch_node(self):
        self.dpfsnode.evaluate(-1)

        cell = self.find_cell(self.dpfsnode, 'dewgong', 'probopass')
        cell2 = self.find_and_expand_cell(cell.node, 'surf', 'stealthrock')

        self.assertDamageTaken(self.get_active(cell2.node, 1))
        self.assertTrue(self.get_side(cell2.node, 0).has_effect(Hazard.STEALTHROCK))
