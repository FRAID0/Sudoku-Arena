"""
Sudoku Arena Core Engine
- Algorithme de Backtracking optimisé
- Générateur de grilles valides à solution unique
- Validateur serveur autoritaire (anti-triche)
"""

import copy
import random
from typing import List, Optional, Tuple

Grid = List[List[int]]


class SudokuEngine:
    GRID_SIZE = 9
    BOX_SIZE = 3

    # Nombre d'indices visibles selon la difficulté
    CLUES_COUNT = {
        "easy": 40,      # ~40 chiffres révélés
        "medium": 32,    # ~32 chiffres révélés
        "hard": 26,      # ~26 chiffres révélés
        "expert": 22     # ~22 chiffres révélés
    }

    @staticmethod
    def create_empty_grid() -> Grid:
        """Crée une grille 9x9 vide."""
        return [[0 for _ in range(SudokuEngine.GRID_SIZE)] for _ in range(SudokuEngine.GRID_SIZE)]

    @staticmethod
    def is_valid_placement(grid: Grid, row: int, col: int, num: int) -> bool:
        """
        Vérifie si placer 'num' à (row, col) respecte les règles du Sudoku standard.
        """
        # Vérifier la ligne
        for c in range(SudokuEngine.GRID_SIZE):
            if c != col and grid[row][c] == num:
                return False

        # Vérifier la colonne
        for r in range(SudokuEngine.GRID_SIZE):
            if r != row and grid[r][col] == num:
                return False

        # Vérifier le bloc 3x3
        box_row = (row // SudokuEngine.BOX_SIZE) * SudokuEngine.BOX_SIZE
        box_col = (col // SudokuEngine.BOX_SIZE) * SudokuEngine.BOX_SIZE
        for r in range(box_row, box_row + SudokuEngine.BOX_SIZE):
            for c in range(box_col, box_col + SudokuEngine.BOX_SIZE):
                if (r != row or c != col) and grid[r][c] == num:
                    return False

        return True

    @staticmethod
    def find_empty_cell(grid: Grid) -> Optional[Tuple[int, int]]:
        """Trouve la première case vide (valeur 0)."""
        for r in range(SudokuEngine.GRID_SIZE):
            for c in range(SudokuEngine.GRID_SIZE):
                if grid[r][c] == 0:
                    return r, c
        return None

    @classmethod
    def solve(cls, grid: Grid) -> bool:
        """
        Résout la grille en place par backtracking.
        Renvoie True si une solution existe, False sinon.
        """
        empty = cls.find_empty_cell(grid)
        if not empty:
            return True  # Grille complètement résolue
        row, col = empty

        for num in range(1, 10):
            if cls.is_valid_placement(grid, row, col, num):
                grid[row][col] = num
                if cls.solve(grid):
                    return True
                grid[row][col] = 0

        return False

    @classmethod
    def count_solutions(cls, grid: Grid, limit: int = 2) -> int:
        """
        Compte le nombre de solutions possibles (s'arrête dès que limit est atteint).
        Permet de garantir l'unicité de la solution sans gaspiller de CPU.
        """
        empty = cls.find_empty_cell(grid)
        if not empty:
            return 1

        row, col = empty
        count = 0

        for num in range(1, 10):
            if cls.is_valid_placement(grid, row, col, num):
                grid[row][col] = num
                count += cls.count_solutions(grid, limit)
                grid[row][col] = 0
                if count >= limit:
                    break

        return count

    @classmethod
    def generate_full_grid(cls) -> Grid:
        """
        Génère une grille 9x9 complète, valide et aléatoire.
        """
        grid = cls.create_empty_grid()

        def fill_randomly(g: Grid) -> bool:
            empty = cls.find_empty_cell(g)
            if not empty:
                return True
            row, col = empty
            numbers = list(range(1, 10))
            random.shuffle(numbers)

            for num in numbers:
                if cls.is_valid_placement(g, row, col, num):
                    g[row][col] = num
                    if fill_randomly(g):
                        return True
                    g[row][col] = 0
            return False

        fill_randomly(grid)
        return grid

    @classmethod
    def generate_puzzle(cls, difficulty: str = "medium") -> Tuple[Grid, Grid]:
        """
        Génère une paire (puzzle, solution).
        Le puzzle est garanti d'avoir UNE SEULE SOLUTION unique.
        """
        diff = difficulty.lower()
        target_clues = cls.CLUES_COUNT.get(diff, cls.CLUES_COUNT["medium"])

        # 1. Générer une grille résolue complète
        solution = cls.generate_full_grid()
        puzzle = copy.deepcopy(solution)

        # 2. Retirer des cases de manière symétrique ou aléatoire tout en conservant l'unicité
        cells = [(r, c) for r in range(cls.GRID_SIZE) for c in range(cls.GRID_SIZE)]
        random.shuffle(cells)

        current_clues = cls.GRID_SIZE * cls.GRID_SIZE

        for r, c in cells:
            if current_clues <= target_clues:
                break

            temp = puzzle[r][c]
            puzzle[r][c] = 0

            # Vérifier l'unicité
            grid_copy = copy.deepcopy(puzzle)
            if cls.count_solutions(grid_copy, limit=2) != 1:
                # Si retirer ce chiffre crée plus d'une solution, on le remet
                puzzle[r][c] = temp
            else:
                current_clues -= 1

        return puzzle, solution

    @classmethod
    def validate_move(cls, solution: Grid, row: int, col: int, value: int) -> bool:
        """
        Vérification autoritaire côté serveur :
        Le chiffre soumis correspond-il exactement à la solution finale ?
        """
        if not (0 <= row < cls.GRID_SIZE and 0 <= col < cls.GRID_SIZE):
            return False
        if not (1 <= value <= 9):
            return False
        return solution[row][col] == value
