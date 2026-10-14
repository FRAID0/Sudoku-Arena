"""
Intelligence Artificielle "KI FRAID"
Simule un adversaire humain pour le mode solo / entraînement.
Niveaux :
- Easy : réflexion lente (2-4s), ~15% de chances de commettre une erreur
- Medium : réflexion moyenne (1.5-3s), ~5% de chances d'erreur
- Hard/Expert : réflexion vive (0.8-1.5s), 0% d'erreur
"""

import random
from typing import Dict, Optional, Tuple
from app.core.sudoku import SudokuEngine, Grid


class KIFraidBot:
    LEVELS = {
        "easy": {
            "delay_range": (2.0, 4.0),
            "error_rate": 0.15,
            "name": "KI FRAID (Novice)"
        },
        "medium": {
            "delay_range": (1.5, 3.0),
            "error_rate": 0.05,
            "name": "KI FRAID (Tactique)"
        },
        "hard": {
            "delay_range": (0.8, 1.8),
            "error_rate": 0.0,
            "name": "KI FRAID (Grand Maître)"
        }
    }

    def __init__(self, difficulty: str = "medium"):
        self.difficulty = difficulty.lower() if difficulty.lower() in self.LEVELS else "medium"
        self.config = self.LEVELS[self.difficulty]

    def get_thinking_delay(self) -> float:
        """Calcule un délai de réflexion pseudo-humain."""
        min_d, max_d = self.config["delay_range"]
        return round(random.uniform(min_d, max_d), 2)

    def choose_move(self, current_grid: Grid, solution: Grid) -> Optional[Dict]:
        """
        Choisit le prochain coup de l'IA.
        Renvoie un dictionnaire avec {row, col, value, delay, is_intentional_error}.
        """
        # Trouver toutes les cases encore vides
        empty_cells = []
        for r in range(SudokuEngine.GRID_SIZE):
            for c in range(SudokuEngine.GRID_SIZE):
                if current_grid[r][c] == 0:
                    empty_cells.append((r, c))

        if not empty_cells:
            return None  # Plus de case à jouer

        # Sélection d'une case vide
        row, col = random.choice(empty_cells)
        correct_value = solution[row][col]

        # Décider si l'IA simule une erreur selon son taux
        make_mistake = random.random() < self.config["error_rate"]

        if make_mistake:
            wrong_numbers = [n for n in range(1, 10) if n != correct_value]
            chosen_value = random.choice(wrong_numbers)
        else:
            chosen_value = correct_value

        return {
            "row": row,
            "col": col,
            "value": chosen_value,
            "delay": self.get_thinking_delay(),
            "is_correct": chosen_value == correct_value,
            "bot_name": self.config["name"]
        }
