import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.sudoku import SudokuEngine
from app.ai.bot import KIFraidBot


class TestKIFraidBot(unittest.TestCase):

    def setUp(self):
        self.puzzle, self.solution = SudokuEngine.generate_puzzle("easy")

    def test_bot_initialization(self):
        bot_easy = KIFraidBot("easy")
        bot_hard = KIFraidBot("hard")
        bot_default = KIFraidBot("unknown")

        self.assertEqual(bot_easy.difficulty, "easy")
        self.assertEqual(bot_hard.difficulty, "hard")
        self.assertEqual(bot_default.difficulty, "medium")

    def test_bot_chooses_empty_cell(self):
        bot = KIFraidBot("hard")
        move = bot.choose_move(self.puzzle, self.solution)

        self.assertIsNotNone(move)
        r, c = move["row"], move["col"]
        # Doit choisir une case qui était vide
        self.assertEqual(self.puzzle[r][c], 0)
        self.assertIn(move["value"], range(1, 10))
        self.assertGreater(move["delay"], 0)

    def test_hard_bot_always_plays_correctly(self):
        bot = KIFraidBot("hard")
        for _ in range(15):
            move = bot.choose_move(self.puzzle, self.solution)
            self.assertTrue(move["is_correct"])
            self.assertEqual(move["value"], self.solution[move["row"]][move["col"]])

    def test_bot_handles_full_grid(self):
        bot = KIFraidBot("medium")
        # Grille déjà résolue
        move = bot.choose_move(self.solution, self.solution)
        self.assertIsNone(move)


if __name__ == "__main__":
    unittest.main()
