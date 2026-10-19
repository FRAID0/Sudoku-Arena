import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.room_manager import RoomManager, RoomState, GameMode


class TestRoomManagerClash(unittest.TestCase):

    def setUp(self):
        self.manager = RoomManager()

    def test_create_clash_room(self):
        room = self.manager.create_room("p1_id", "Alice", GameMode.CLASH, "easy")
        self.assertEqual(len(room.room_code), 4)
        self.assertEqual(room.state, RoomState.WAITING)
        self.assertEqual(room.mode, GameMode.CLASH)
        self.assertIn("p1_id", room.players)
        self.assertIsNotNone(room.shared_grid)

    def test_turn_alternation_on_mistake(self):
        room = self.manager.create_room("p1_id", "Alice", GameMode.CLASH, "hard")
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

        # Timeout d'Alice
        res = self.manager.timeout_turn(code)
        self.assertIsNotNone(res)
        self.assertTrue(res["timeout"])
        self.assertEqual(res["timed_out_player_id"], "p1_id")
        self.assertEqual(res["score"], 4.0)
        self.assertEqual(res["current_turn"], "p2_id")
        self.assertEqual(room.current_turn_player_id, "p2_id")


if __name__ == "__main__":
    unittest.main()
