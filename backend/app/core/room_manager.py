"""
Room & Matchmaking Manager for Sudoku Arena
Gère les salons de jeu, les codes d'invitation, les états et les modes de jeu (Race, Clash, AI).
Implémente le barème de points d'origine : POINTS, BONUS_THRESHOLDS, pénalités et alternance de tour.
"""

import copy
import random
import string
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.core.sudoku import SudokuEngine, Grid


class GameMode(str, Enum):
    RACE = "race"         # Course miroir (chacun sa grille)
    CLASH = "clash"       # Grille partagée avec tour par tour (Mode Signature)
    SOLO_AI = "solo_ai"   # Solo contre KI FRAID


class RoomState(str, Enum):
    WAITING = "waiting"       # En attente d'un adversaire
    STARTING = "starting"     # Décompte 3.. 2.. 1..
    IN_GAME = "in_game"       # Match en cours
    FINISHED = "finished"     # Partie terminée


# Barème exact issu du projet d'école d'origine
POINTS = {
    'easy': 1.0,
    'medium': 1.5,
    'hard': 2.0
}

BONUS_THRESHOLDS = {
    'easy': [(10.0, 1.0), (20.0, 0.5)],
    'medium': [(7.0, 1.0), (15.0, 0.5)],
    'hard': [(5.0, 1.0), (8.0, 0.5)]
}

TURN_TIMEOUTS = {
    'easy': 30.0,
    'medium': 20.0,
    'hard': 10.0
}


class Player:
    def __init__(self, player_id: str, name: str, is_host: bool = False):
        self.player_id = player_id
        self.name = name
        self.is_host = is_host
        self.is_connected = True
        self.grid: Optional[Grid] = None      # Grille personnelle (mode Race)
        self.score = 0.0
        self.mistakes = 0
        self.progress = 0.0                   # 0.0 à 100.0%
        self.finished = False
        self.finish_time: Optional[float] = None


class Room:
    def __init__(self, room_code: str, host: Player, mode: GameMode = GameMode.CLASH, difficulty: str = "medium", validation_mode: str = "simple"):
        self.room_code = room_code
        self.mode = mode
        self.difficulty = difficulty.lower() if difficulty.lower() in POINTS else "medium"
        self.validation_mode = validation_mode.lower() if validation_mode.lower() in ("simple", "strict") else "simple"
        self.state = RoomState.WAITING
        self.created_at = time.time()
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        self.players: Dict[str, Player] = {host.player_id: host}
        self.spectators: List[str] = []
        self.winner_id: Optional[str] = None

        # Gestion du tour par tour (Mode Clash & Solo AI)
        self.current_turn_player_id: Optional[str] = host.player_id
        self.turn_start_time: Optional[float] = None
        self.turn_timeout: float = TURN_TIMEOUTS.get(self.difficulty, 20.0)

        # Grilles
        self.initial_puzzle: Optional[Grid] = None
        self.solution: Optional[Grid] = None
        self.shared_grid: Optional[Grid] = None

    @property
    def player_list(self) -> List[Player]:
        return list(self.players.values())

    @property
    def is_full(self) -> bool:
        return len(self.players) >= 2

    def calculate_progress(self, current_grid: Grid) -> float:
        """Calcule le pourcentage de cases résolues (hors indices initiaux)."""
        if not self.initial_puzzle:
            return 0.0

        empty_initial = sum(row.count(0) for row in self.initial_puzzle)
        if empty_initial == 0:
            return 100.0

        empty_now = sum(row.count(0) for row in current_grid)
        filled = empty_initial - empty_now
        return round((filled / empty_initial) * 100.0, 1)

    def switch_turn(self) -> str:
        """Passe la main au joueur suivant et réinitialise le chrono de tour."""
        players = self.player_list
        if len(players) >= 2:
            current_idx = next((i for i, p in enumerate(players) if p.player_id == self.current_turn_player_id), 0)
            next_idx = (current_idx + 1) % len(players)
            self.current_turn_player_id = players[next_idx].player_id
        self.turn_start_time = time.time()
        return self.current_turn_player_id

    def calculate_points_and_bonus(self, time_taken: float) -> Tuple[float, float]:
        """Calcule points de base et bonus selon la formule d'origine."""
        base = POINTS.get(self.difficulty, 1.0)
        bonus = 0.0
        thresholds = BONUS_THRESHOLDS.get(self.difficulty, [])
        for threshold, bonus_pts in thresholds:
            if time_taken < threshold:
                bonus = bonus_pts
                break
        return base, bonus


class RoomManager:
    CODE_CHARACTERS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    CODE_LENGTH = 4

    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def _generate_unique_code(self) -> str:
        for _ in range(100):
            code = "".join(random.choices(self.CODE_CHARACTERS, k=self.CODE_LENGTH))
            if code not in self.rooms:
                return code
        raise RuntimeError("Impossible de générer un code de salon unique")

    def create_room(self, host_id: str, host_name: str, mode: GameMode = GameMode.CLASH, difficulty: str = "medium", validation_mode: str = "simple") -> Room:
        code = self._generate_unique_code()
        host = Player(player_id=host_id, name=host_name, is_host=True)
        room = Room(room_code=code, host=host, mode=mode, difficulty=difficulty, validation_mode=validation_mode)

        # Générer le puzzle
        puzzle, solution = SudokuEngine.generate_puzzle(difficulty)
        room.initial_puzzle = puzzle
        room.solution = solution
        room.shared_grid = copy.deepcopy(puzzle)
        host.grid = copy.deepcopy(puzzle)

        # Si mode Solo AI, inscrire automatiquement le bot comme Joueur 2
        if mode == GameMode.SOLO_AI:
            bot_player = Player(player_id="bot_ki_fraid", name="KI FRAID 🤖", is_host=False)
            bot_player.grid = copy.deepcopy(puzzle)
            room.players[bot_player.player_id] = bot_player

        self.rooms[code] = room
        return room

    def join_room(self, room_code: str, player_id: str, player_name: str) -> Tuple[Room, str]:
        code = room_code.upper().strip()
        room = self.rooms.get(code)
        if not room:
            raise ValueError(f"Salon '{code}' introuvable.")

        if player_id in room.players:
            room.players[player_id].is_connected = True
            return room, "player"

        if not room.is_full and room.state == RoomState.WAITING:
            new_player = Player(player_id=player_id, name=player_name, is_host=False)
            new_player.grid = copy.deepcopy(room.initial_puzzle)
            room.players[player_id] = new_player
            return room, "player"

        if player_id not in room.spectators:
            room.spectators.append(player_id)
        return room, "spectator"

    def start_game(self, room_code: str) -> Room:
        room = self.rooms.get(room_code)
        if not room:
            raise ValueError("Salon introuvable.")

        room.state = RoomState.IN_GAME
        room.start_time = time.time()
        room.turn_start_time = time.time()
        # Le premier joueur actif est l'hôte
        room.current_turn_player_id = room.player_list[0].player_id
        return room

    def play_move(self, room_code: str, player_id: str, row: int, col: int, value: int) -> Dict:
        """
        Valide et applique un coup soumis par un joueur avec arbitrage du tour et du score.
        Supporte deux modes : 'simple' (règles locales) et 'strict' (solution finale unique).
        """
        room = self.rooms.get(room_code)
        if not room:
            raise ValueError("Salon introuvable.")
        if room.state != RoomState.IN_GAME:
            raise ValueError("La partie n'est pas en cours.")

        player = room.players.get(player_id)
        if not player:
            raise ValueError("Joueur non autorisé dans ce salon.")

        # Sécurisation des types et bornes
        try:
            row, col, value = int(row), int(col), int(value)
        except (ValueError, TypeError):
            return {"valid": False, "rejected": True, "reason": "Coordonnées ou valeur non numériques."}

        if not (0 <= row < 9 and 0 <= col < 9 and 1 <= value <= 9):
            return {"valid": False, "rejected": True, "reason": "Coordonnées (0-8) ou chiffre (1-9) hors limites."}

        # En mode Clash ou Solo AI : vérifier impérativement si c'est son tour
        if room.mode in (GameMode.CLASH, GameMode.SOLO_AI):
            if player_id != room.current_turn_player_id:
                return {
                    "valid": False,
                    "rejected": True,
                    "reason": "Ce n'est pas votre tour !",
                    "current_turn": room.current_turn_player_id
                }

        target_grid = room.shared_grid if room.mode in (GameMode.CLASH, GameMode.SOLO_AI) else player.grid

        # Case déjà remplie
        if target_grid[row][col] != 0:
            return {"valid": False, "rejected": True, "reason": "Cette case est déjà remplie."}

        time_taken = time.time() - (room.turn_start_time or time.time())

        # Validation selon le mode choisi :
        # - Mode 'strict' (Casse-Tête) : doit correspondre à la solution finale unique
        # - Mode 'simple' (Règles locales) : doit respecter la ligne, la colonne et le bloc 3x3 actuel
        if room.validation_mode == "strict":
            is_valid = SudokuEngine.validate_move(room.solution, row, col, value)
            error_reason = "Chiffre incorrect (ne correspond pas à la solution finale du casse-tête)."
        else:
            is_valid = SudokuEngine.is_valid_placement(target_grid, row, col, value)
            error_reason = "Conflit : ce chiffre est déjà présent sur la même ligne, colonne ou bloc 3x3 !"

        if is_valid:
            target_grid[row][col] = value
            base_pts, bonus_pts = room.calculate_points_and_bonus(time_taken)
            points_gained = base_pts + bonus_pts
            player.score += points_gained
            player.progress = room.calculate_progress(target_grid)

            # En mode Clash/Solo AI, chaque coup joué passe la main pour un vrai duel interactif tour par tour
            next_player = room.switch_turn() if room.mode in (GameMode.CLASH, GameMode.SOLO_AI) else room.current_turn_player_id

            # Vérifier si la grille est totalement complétée
            is_completed = (player.progress >= 100.0) or all(cell != 0 for r in target_grid for cell in r)
            if is_completed:
                room.state = RoomState.FINISHED
                room.end_time = time.time()
                # En mode Clash, le gagnant est celui qui a le plus haut score !
                scores = {p.player_id: p.score for p in room.player_list}
                highest_score = max(scores.values())
                winners = [pid for pid, sc in scores.items() if sc == highest_score]
                room.winner_id = winners[0] if len(winners) == 1 else "DRAW"

            return {
                "valid": True,
                "row": row,
                "col": col,
                "value": value,
                "player_id": player_id,
                "score": player.score,
                "points_gained": points_gained,
                "bonus_gained": bonus_pts,
                "progress": player.progress,
                "current_turn": next_player,
                "turn_switched": (room.mode in (GameMode.CLASH, GameMode.SOLO_AI)),
                "shared_grid": target_grid,
                "game_over": room.state == RoomState.FINISHED,
                "winner_id": room.winner_id
            }
        else:
            # ERREUR : pénalité de 1 point et PASSAGE DE TOUR IMMÉDIAT
            player.mistakes += 1
            player.score = max(0.0, player.score - 1.0)
            next_player = room.switch_turn() if room.mode in (GameMode.CLASH, GameMode.SOLO_AI) else room.current_turn_player_id

            return {
                "valid": False,
                "row": row,
                "col": col,
                "value": value,
                "player_id": player_id,
                "score": player.score,
                "mistakes": player.mistakes,
                "current_turn": next_player,
                "turn_switched": True,
                "game_over": False,
                "reason": error_reason
            }

    def timeout_turn(self, room_code: str) -> Optional[Dict]:
        """Déclenché quand le chrono du tour expire."""
        room = self.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME:
            return None

        current_player = room.players.get(room.current_turn_player_id)
        if current_player:
            current_player.score = max(0.0, current_player.score - 1.0)
            current_player.mistakes += 1

        next_player = room.switch_turn()
        return {
            "timeout": True,
            "timed_out_player_id": current_player.player_id if current_player else None,
            "score": current_player.score if current_player else 0.0,
            "current_turn": next_player
        }

    def leave_room(self, room_code: str, player_id: str):
        room = self.rooms.get(room_code)
        if not room:
            return

        if player_id in room.players:
            room.players[player_id].is_connected = False
            if room.state == RoomState.WAITING and room.players[player_id].is_host:
                del self.rooms[room_code]
        elif player_id in room.spectators:
            room.spectators.remove(player_id)
