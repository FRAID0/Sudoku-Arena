import unittest
import sys
import os

# Ajouter le dossier backend au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.sudoku import SudokuEngine


class TestSudokuEngine(unittest.TestCase):

    def test_create_empty_grid(self):
        grid = SudokuEngine.create_empty_grid()
        self.assertEqual(len(grid), 9)
        self.assertTrue(all(len(row) == 9 for row in grid))
        self.assertTrue(all(cell == 0 for row in grid for cell in row))

    def test_is_valid_placement(self):
        grid = SudokuEngine.create_empty_grid()
        grid[0][0] = 5

        # Conflit sur la même ligne
        self.assertFalse(SudokuEngine.is_valid_placement(grid, 0, 5, 5))
        # Conflit sur la même colonne
        self.assertFalse(SudokuEngine.is_valid_placement(grid, 7, 0, 5))
        # Conflit dans le même bloc 3x3
        self.assertFalse(SudokuEngine.is_valid_placement(grid, 1, 1, 5))

        # Placement valide ailleurs
        self.assertTrue(SudokuEngine.is_valid_placement(grid, 0, 5, 3))
        self.assertTrue(SudokuEngine.is_valid_placement(grid, 5, 5, 5))

    def test_solve_and_unique_solution(self):
        puzzle = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]

        # Doit avoir exactement 1 solution
        self.assertEqual(SudokuEngine.count_solutions(puzzle), 1)

        # Résolution en place
        success = SudokuEngine.solve(puzzle)
        self.assertTrue(success)
        # Toutes les cases doivent être remplies et valides
        self.assertTrue(all(cell != 0 for row in puzzle for cell in row))
        for r in range(9):
            for c in range(9):
                val = puzzle[r][c]
                self.assertTrue(SudokuEngine.is_valid_placement(puzzle, r, c, val))

    def test_generate_full_grid(self):
        grid = SudokuEngine.generate_full_grid()
        self.assertEqual(len(grid), 9)
        self.assertTrue(all(cell in range(1, 10) for row in grid for cell in row))
        for r in range(9):
            for c in range(9):
                val = grid[r][c]
                self.assertTrue(SudokuEngine.is_valid_placement(grid, r, c, val))

    def test_generate_puzzle_has_single_solution(self):
        puzzle, solution = SudokuEngine.generate_puzzle("easy")
        # Vérifier que la solution est valide
        self.assertTrue(all(cell != 0 for row in solution for cell in row))

        # Vérifier que le puzzle n'a qu'une seule solution
        self.assertEqual(SudokuEngine.count_solutions(puzzle), 1)

        # Vérifier que le puzzle a bien des cases vides
        empty_cells = sum(row.count(0) for row in puzzle)
        self.assertGreater(empty_cells, 0)

    def test_validate_move(self):
        _, solution = SudokuEngine.generate_puzzle("medium")
        correct_val = solution[2][3]
        wrong_val = (correct_val % 9) + 1

        self.assertTrue(SudokuEngine.validate_move(solution, 2, 3, correct_val))
        self.assertFalse(SudokuEngine.validate_move(solution, 2, 3, wrong_val))
        self.assertFalse(SudokuEngine.validate_move(solution, -1, 0, correct_val))
        self.assertFalse(SudokuEngine.validate_move(solution, 0, 9, correct_val))
        self.assertFalse(SudokuEngine.validate_move(solution, 0, 0, 10))


if __name__ == "__main__":
    unittest.main()
