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
            "delay_range": (6.0, 14.0),     # Plus long, hésitant (chrono 30s)
            "error_range": (0.28, 0.40),    # Plus d'erreurs (~35%)
            "name": "KI FRAID (Novice)"
        },
        "medium": {
            "delay_range": (4.5, 9.5),      # Ni trop rapide, ni trop long (chrono 20s)
            "error_range": (0.15, 0.22),    # Moins d'erreurs (~18%)
            "name": "KI FRAID (Tactique)"
        },
        "hard": {
            "delay_range": (3.0, 6.0),      # Réactif mais réfléchit visiblement (chrono 10s)
            "error_range": (0.0, 0.0),      # Grand Maître
            "name": "KI FRAID (Grand Maître)"
        }
    }

    def __init__(self, difficulty: str = "medium"):
        self.difficulty = difficulty.lower() if difficulty.lower() in self.LEVELS else "medium"
        self.config = self.LEVELS[self.difficulty]

    def get_thinking_delay(self) -> float:
        """Calcule un délai de réflexion pseudo-humain dynamique dans le range prévu."""
        min_d, max_d = self.config["delay_range"]
        base_delay = random.uniform(min_d, max_d)
        jitter = random.uniform(-0.35, 0.35)
        return max(2.0, round(base_delay + jitter, 2))

    def get_error_rate(self) -> float:
        """Calcule dynamiquement le taux d'erreur dans le range prévu."""
        min_e, max_e = self.config["error_range"]
        return random.uniform(min_e, max_e)

    def choose_move(self, current_grid: Grid, solution: Grid) -> Optional[Dict]:
        """
        Choisit le prochain coup de l'IA avec tirage aléatoire varié et marge d'erreur stochastique.
        """
        # Trouver toutes les cases encore vides
        empty_cells = []
        for r in range(SudokuEngine.GRID_SIZE):
            for c in range(SudokuEngine.GRID_SIZE):
                if current_grid[r][c] == 0:
                    empty_cells.append((r, c))

        if not empty_cells:
            return None  # Plus de case à jouer

        # Mélange aléatoire complet pour éviter les patterns fixes
        random.shuffle(empty_cells)
        row, col = random.choice(empty_cells)
        correct_value = solution[row][col]

        # Décider si l'IA simule une erreur selon son range dynamique
        make_mistake = random.random() < self.get_error_rate()

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
