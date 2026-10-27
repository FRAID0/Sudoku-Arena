import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.room_manager import RoomManager, RoomState, GameMode, ClashRule
from app.core.sudoku import SudokuEngine


class TestRoomManagerClash(unittest.TestCase):

    def setUp(self):
        self.manager = RoomManager()

    def test_create_clash_room(self):
        room = self.manager.create_room("p1_id", "Alice", GameMode.CLASH, "easy")
        self.assertEqual(len(room.room_code), 4)
        self.assertEqual(room.state, RoomState.WAITING)
        self.assertEqual(room.mode, GameMode.CLASH)
        self.assertEqual(room.clash_rule, ClashRule.COMBO_CAPPED)
        self.assertIn("p1_id", room.players)
        self.assertIsNotNone(room.shared_grid)

    def test_turn_alternation_on_mistake(self):
        room = self.manager.create_room("p1_id", "Alice", GameMode.CLASH, "hard", validation_mode="strict", clash_rule=ClashRule.STRICT)
        code = room.room_code
        self.manager.join_room(code, "p2_id", "Bob")
        self.manager.start_game(code)

        # Au départ, c'est le tour de p1 (l'hôte)
        self.assertEqual(room.current_turn_player_id, "p1_id")

        # p2 essaie de jouer alors que ce n'est pas son tour -> Rejeté
        res_reject = self.manager.play_move(code, "p2_id", 0, 0, 5)
        self.assertTrue(res_reject.get("rejected"))

        # Trouver une case vide
        empty_cell = None
        for r in range(9):
            for c in range(9):
                if room.shared_grid[r][c] == 0:
                    empty_cell = (r, c)
                    break
            if empty_cell:
                break

        r, c = empty_cell
        correct_val = room.solution[r][c]
        wrong_val = (correct_val % 9) + 1

        # p1 fait une erreur -> Pénalité et PASSAGE DE TOUR IMMÉDIAT à p2
        res_err = self.manager.play_move(code, "p1_id", r, c, wrong_val)
        self.assertFalse(res_err["valid"])
        self.assertTrue(res_err["turn_switched"])
        self.assertEqual(room.current_turn_player_id, "p2_id")

        # Maintenant, c'est à p2 de jouer !
        res_ok = self.manager.play_move(code, "p2_id", r, c, correct_val)
        self.assertTrue(res_ok["valid"])
        self.assertGreater(res_ok["points_gained"], 0)
        self.assertTrue(res_ok["turn_switched"])  # En duel interactif, la main passe à p1
        self.assertEqual(room.current_turn_player_id, "p1_id")

    def test_scoring_and_bonus_calculation(self):
        room_easy = self.manager.create_room("p1", "Alice", GameMode.CLASH, "easy")
        # Easy: base 1.0, <10s -> +1.0, <20s -> +0.5, >=20s -> 0.0
        self.assertEqual(room_easy.calculate_points_and_bonus(5.0), (1.0, 1.0))
        self.assertEqual(room_easy.calculate_points_and_bonus(15.0), (1.0, 0.5))
        self.assertEqual(room_easy.calculate_points_and_bonus(25.0), (1.0, 0.0))

        room_med = self.manager.create_room("p1", "Alice", GameMode.CLASH, "medium")
        # Medium: base 1.5, <7s -> +1.0, <15s -> +0.5
        self.assertEqual(room_med.calculate_points_and_bonus(3.0), (1.5, 1.0))
        self.assertEqual(room_med.calculate_points_and_bonus(10.0), (1.5, 0.5))
        self.assertEqual(room_med.calculate_points_and_bonus(18.0), (1.5, 0.0))

        room_hard = self.manager.create_room("p1", "Alice", GameMode.CLASH, "hard")
        # Hard: base 2.0, <5s -> +1.0, <8s -> +0.5
        self.assertEqual(room_hard.calculate_points_and_bonus(2.0), (2.0, 1.0))
        self.assertEqual(room_hard.calculate_points_and_bonus(6.0), (2.0, 0.5))
        self.assertEqual(room_hard.calculate_points_and_bonus(9.0), (2.0, 0.0))

    def test_timeout_turn(self):
        room = self.manager.create_room("p1_id", "Alice", GameMode.CLASH, "medium")
        code = room.room_code
        self.manager.join_room(code, "p2_id", "Bob")
        self.manager.start_game(code)

        # Alice a 5 points
        room.players["p1_id"].score = 5.0

        # Timeout d'Alice : score conservé (pas de pénalité sur chrono), tour passe
        res = self.manager.timeout_turn(code)
        self.assertIsNotNone(res)
        self.assertTrue(res["timeout"])
        self.assertEqual(res["timed_out_player_id"], "p1_id")
        self.assertEqual(res["score"], 5.0)
        self.assertEqual(res["current_turn"], "p2_id")
        self.assertEqual(room.current_turn_player_id, "p2_id")

    def test_dual_validation_mode(self):
        # 1. Mode Simple : accepte tout placement valide localement
        room_simple = self.manager.create_room("p1", "Alice", GameMode.CLASH, "medium", validation_mode="simple")
        code_s = room_simple.room_code
        self.manager.start_game(code_s)
        empty_r, empty_c = SudokuEngine.find_empty_cell(room_simple.shared_grid)
        
        # Trouver un chiffre valide pour les règles locales (ligne/colonne/carré)
        valid_local = None
        for n in range(1, 10):
            if SudokuEngine.is_valid_placement(room_simple.shared_grid, empty_r, empty_c, n):
                valid_local = n
                break
        self.assertIsNotNone(valid_local)
        res_s = self.manager.play_move(code_s, "p1", empty_r, empty_c, valid_local)
        self.assertTrue(res_s["valid"])
        self.assertEqual(room_simple.shared_grid[empty_r][empty_c], valid_local)

        # 2. Mode Strict : rejette si ce n'est pas la solution unique finale
        room_strict = self.manager.create_room("p2", "Bob", GameMode.CLASH, "medium", validation_mode="strict")
        code_st = room_strict.room_code
        self.manager.start_game(code_st)
        empty_r2, empty_c2 = SudokuEngine.find_empty_cell(room_strict.shared_grid)
        correct_sol = room_strict.solution[empty_r2][empty_c2]
        wrong_sol = (correct_sol % 9) + 1
        
        res_st = self.manager.play_move(code_st, "p2", empty_r2, empty_c2, wrong_sol)
        self.assertFalse(res_st["valid"])
        self.assertIn("reason", res_st)

    def test_leave_room_waiting(self):
        room = self.manager.create_room("p1", "Alice", GameMode.CLASH)
        code = room.room_code
        self.manager.join_room(code, "p2", "Bob")

        # Bob quitte en salle d'attente
        res = self.manager.leave_room(code, "p2")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("player_left"))
        self.assertEqual(len(res["remaining_players"]), 1)
        self.assertNotIn("p2", room.players)

        # Alice (l'hôte) quitte -> Le salon est supprimé
        res_host = self.manager.leave_room(code, "p1")
        self.assertTrue(res_host.get("room_deleted"))
        self.assertNotIn(code, self.manager.rooms)

    def test_leave_room_in_game_forfeit(self):
        room = self.manager.create_room("p1", "Alice", GameMode.CLASH)
        code = room.room_code
        self.manager.join_room(code, "p2", "Bob")
        self.manager.start_game(code)
        self.assertEqual(room.state, RoomState.IN_GAME)

        # Bob se déconnecte pendant la partie -> Alice gagne par forfait !
        res = self.manager.leave_room(code, "p2")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("forfeit"))
        self.assertEqual(res["winner_id"], "p1")
        self.assertEqual(res["left_player_id"], "p2")
        self.assertEqual(room.state, RoomState.FINISHED)
        self.assertEqual(room.winner_id, "p1")

    def test_clash_combo_capped_variant(self):
        """Option C : Un coup valide donne droit à 1 coup bonus (max 2 d'affilée), puis passage."""
        room = self.manager.create_room("p1", "Alice", GameMode.CLASH, "medium", validation_mode="strict", clash_rule=ClashRule.COMBO_CAPPED)
        code = room.room_code
        self.manager.join_room(code, "p2", "Bob")
        self.manager.start_game(code)

        # Trouver deux cases vides
        empty_cells = []
        for r in range(9):
            for c in range(9):
                if room.shared_grid[r][c] == 0:
                    empty_cells.append((r, c))
                    if len(empty_cells) == 2:
                        break
            if len(empty_cells) == 2:
                break

        (r1, c1), (r2, c2) = empty_cells
        val1 = room.solution[r1][c1]
        val2 = room.solution[r2][c2]

        # Coup 1 d'Alice (valide) -> Gagne le tour bonus (ne passe PAS la main)
        res1 = self.manager.play_move(code, "p1", r1, c1, val1)
        self.assertTrue(res1["valid"])
        self.assertFalse(res1["turn_switched"])
        self.assertTrue(res1["is_combo"])
        self.assertEqual(res1["combo_streak"], 1)
        self.assertEqual(room.current_turn_player_id, "p1")

        # Coup 2 d'Alice (valide, 2ème d'affilée) -> Limite de combo atteinte, passe la main à Bob !
        res2 = self.manager.play_move(code, "p1", r2, c2, val2)
        self.assertTrue(res2["valid"])
        self.assertTrue(res2["turn_switched"])
        self.assertFalse(res2["is_combo"])
        self.assertEqual(res2["combo_streak"], 2)
        self.assertEqual(room.current_turn_player_id, "p2")

    def test_clash_unlimited_variant(self):
        """Option B : Série illimitée tant que les coups sont valides."""
        room = self.manager.create_room("p1", "Alice", GameMode.CLASH, "medium", validation_mode="strict", clash_rule=ClashRule.UNLIMITED)
        code = room.room_code
        self.manager.join_room(code, "p2", "Bob")
        self.manager.start_game(code)

        empty_cells = []
        for r in range(9):
            for c in range(9):
                if room.shared_grid[r][c] == 0:
                    empty_cells.append((r, c))
                    if len(empty_cells) == 4:
                        break
            if len(empty_cells) == 4:
                break

        (r1, c1), (r2, c2), (r3, c3), (r4, c4) = empty_cells

        # Coups 1, 2, 3 consécutifs valides -> Alice garde la main
        for i, (r, c) in enumerate([(r1, c1), (r2, c2), (r3, c3)], start=1):
            res = self.manager.play_move(code, "p1", r, c, room.solution[r][c])
            self.assertTrue(res["valid"])
            self.assertFalse(res["turn_switched"])
            self.assertEqual(res["combo_streak"], i)
            self.assertEqual(room.current_turn_player_id, "p1")

        # Coup 4 d'Alice invalide -> Bris de combo immédiat et la main passe à Bob !
        wrong_val = (room.solution[r4][c4] % 9) + 1
        res_err = self.manager.play_move(code, "p1", r4, c4, wrong_val)
        self.assertFalse(res_err["valid"])
        self.assertTrue(res_err["turn_switched"])
        self.assertEqual(res_err["combo_streak"], 0)
        self.assertEqual(room.current_turn_player_id, "p2")


if __name__ == "__main__":
    unittest.main()

