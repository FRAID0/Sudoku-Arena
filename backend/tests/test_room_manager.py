import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.room_manager import RoomManager, RoomState, GameMode


class TestRoomManager(unittest.TestCase):

    def setUp(self):
        self.manager = RoomManager()

    def test_create_room(self):
        room = self.manager.create_room("p1_id", "Alice", GameMode.RACE, "easy")
        self.assertIsNotNone(room.room_code)
        self.assertEqual(len(room.room_code), 4)
        self.assertEqual(room.state, RoomState.WAITING)
        self.assertIn("p1_id", room.players)
        self.assertTrue(room.players["p1_id"].is_host)
        self.assertIsNotNone(room.initial_puzzle)

    def test_join_room_as_player_and_spectator(self):
        room = self.manager.create_room("p1_id", "Alice")
        code = room.room_code

        # Joueur 2 rejoint -> devient player
        _, role2 = self.manager.join_room(code, "p2_id", "Bob")
        self.assertEqual(role2, "player")
        self.assertEqual(len(room.players), 2)
        self.assertTrue(room.is_full)

        # Joueur 3 rejoint -> devient spectator
        _, role3 = self.manager.join_room(code, "p3_id", "Charlie")
        self.assertEqual(role3, "spectator")
        self.assertIn("p3_id", room.spectators)

    def test_play_move_and_scoring(self):
        room = self.manager.create_room("p1_id", "Alice")
        code = room.room_code
        self.manager.join_room(code, "p2_id", "Bob")
        self.manager.start_game(code)

        self.assertEqual(room.state, RoomState.IN_GAME)

        # Trouver deux cases vides distinctes
        empty_cells = []
        for r in range(9):
            for c in range(9):
                if room.initial_puzzle[r][c] == 0:
                    empty_cells.append((r, c))
                    if len(empty_cells) == 2:
                        break
            if len(empty_cells) == 2:
                break

        (r1, c1), (r2, c2) = empty_cells
        correct_val_1 = room.solution[r1][c1]
        correct_val_2 = room.solution[r2][c2]
        wrong_val_2 = (correct_val_2 % 9) + 1

        # 1. Bon coup d'abord (+10 pts) -> score = 10
        res_correct = self.manager.play_move(code, "p1_id", r1, c1, correct_val_1)
        self.assertTrue(res_correct["valid"])
        self.assertEqual(res_correct["score"], 10)
        self.assertGreater(res_correct["progress"], 0.0)

        # 2. Mauvais coup ensuite (-5 pts de pénalité) -> score = 5
        res_wrong = self.manager.play_move(code, "p1_id", r2, c2, wrong_val_2)
        self.assertFalse(res_wrong["valid"])
        self.assertEqual(res_wrong["mistakes"], 1)
        self.assertEqual(res_wrong["score"], 5)


if __name__ == "__main__":
    unittest.main()
