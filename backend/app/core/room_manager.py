"""
Room & Matchmaking Manager for Sudoku Arena
Gère les salons de jeu, les codes d'invitation, les états et les modes de jeu (Race, Clash, AI).
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
    CLASH = "clash"       # Grille partagée avec capture de cases
    SOLO_AI = "solo_ai"   # Solo contre KI FRAID


class RoomState(str, Enum):
    WAITING = "waiting"       # En attente d'un adversaire
    STARTING = "starting"     # Décompte 3.. 2.. 1..
    IN_GAME = "in_game"       # Match en cours
    FINISHED = "finished"     # Partie terminée


class Player:
    def __init__(self, player_id: str, name: str, is_host: bool = False):
        self.player_id = player_id
        self.name = name
        self.is_host = is_host
        self.is_connected = True
        self.grid: Optional[Grid] = None      # Grille personnelle (mode Race)
        self.score = 0
        self.mistakes = 0
        self.progress = 0.0                   # 0.0 à 100.0%
        self.finished = False
        self.finish_time: Optional[float] = None


class Room:
    def __init__(self, room_code: str, host: Player, mode: GameMode = GameMode.RACE, difficulty: str = "medium"):
        self.room_code = room_code
        self.mode = mode
        self.difficulty = difficulty
        self.state = RoomState.WAITING
        self.created_at = time.time()
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        self.players: Dict[str, Player] = {host.player_id: host}
        self.spectators: List[str] = []
        self.winner_id: Optional[str] = None

        # Puzzles générés
        self.initial_puzzle: Optional[Grid] = None
        self.solution: Optional[Grid] = None
        # Grille partagée pour le mode Clash
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


class RoomManager:
    # Alphabet lisible excluant les caractères ambigus (0, O, 1, I)
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

    def create_room(self, host_id: str, host_name: str, mode: GameMode = GameMode.RACE, difficulty: str = "medium") -> Room:
        code = self._generate_unique_code()
        host = Player(player_id=host_id, name=host_name, is_host=True)
        room = Room(room_code=code, host=host, mode=mode, difficulty=difficulty)

        # Générer le puzzle immédiatement
        puzzle, solution = SudokuEngine.generate_puzzle(difficulty)
        room.initial_puzzle = puzzle
        room.solution = solution
        room.shared_grid = copy.deepcopy(puzzle)

        # Attribuer la grille au host
        host.grid = copy.deepcopy(puzzle)

        # Si mode Solo AI, inscrire automatiquement le bot comme adversaire
        if mode == GameMode.SOLO_AI:
            bot_player = Player(player_id="bot_ki_fraid", name="KI FRAID 🤖", is_host=False)
            bot_player.grid = copy.deepcopy(puzzle)
            room.players[bot_player.player_id] = bot_player

        self.rooms[code] = room
        return room

    def join_room(self, room_code: str, player_id: str, player_name: str) -> Tuple[Room, str]:
        """
        Rejoint un salon. Renvoie (Room, rôle) avec rôle in ['player', 'spectator'].
        """
        code = room_code.upper().strip()
        room = self.rooms.get(code)
        if not room:
            raise ValueError(f"Salon '{code}' introuvable.")

        # Reconnexion d'un joueur existant
        if player_id in room.players:
            room.players[player_id].is_connected = True
            return room, "player"

        # Rejoindre en tant que Joueur 2 si disponible et non démarré
        if not room.is_full and room.state == RoomState.WAITING:
            new_player = Player(player_id=player_id, name=player_name, is_host=False)
            new_player.grid = copy.deepcopy(room.initial_puzzle)
            room.players[player_id] = new_player
            return room, "player"

        # Sinon, rejoindre en tant que spectateur
        if player_id not in room.spectators:
            room.spectators.append(player_id)
        return room, "spectator"

    def start_game(self, room_code: str) -> Room:
        room = self.rooms.get(room_code)
        if not room:
            raise ValueError("Salon introuvable.")

        room.state = RoomState.IN_GAME
        room.start_time = time.time()
        return room

    def play_move(self, room_code: str, player_id: str, row: int, col: int, value: int) -> Dict:
        """
        Valide et applique un coup soumis par un joueur.
        """
        room = self.rooms.get(room_code)
        if not room:
            raise ValueError("Salon introuvable.")
        if room.state != RoomState.IN_GAME:
            raise ValueError("La partie n'est pas en cours.")

        player = room.players.get(player_id)
        if not player:
            raise ValueError("Joueur non autorisé dans ce salon.")

        target_grid = room.shared_grid if room.mode == GameMode.CLASH else player.grid

        # Vérifier que la case n'est pas déjà fixée
        if target_grid[row][col] != 0:
            return {"valid": False, "reason": "Cell already filled"}

        # Validation autoritaire contre la solution secrète
        is_valid = SudokuEngine.validate_move(room.solution, row, col, value)

        if is_valid:
            target_grid[row][col] = value
            player.score += 10
            player.progress = room.calculate_progress(target_grid)

            # Vérifier si ce joueur a fini
            if player.progress >= 100.0:
                player.finished = True
                player.finish_time = time.time() - (room.start_time or time.time())
                room.winner_id = player.player_id
                room.state = RoomState.FINISHED
                room.end_time = time.time()

            return {
                "valid": True,
                "row": row,
                "col": col,
                "value": value,
                "player_id": player_id,
                "score": player.score,
                "progress": player.progress,
                "game_over": room.state == RoomState.FINISHED,
                "winner_id": room.winner_id
            }
        else:
            player.mistakes += 1
            player.score = max(0, player.score - 5)  # Pénalité
            return {
                "valid": False,
                "row": row,
                "col": col,
                "value": value,
                "player_id": player_id,
                "score": player.score,
                "mistakes": player.mistakes,
                "game_over": False
            }

    def leave_room(self, room_code: str, player_id: str):
        room = self.rooms.get(room_code)
        if not room:
            return

        if player_id in room.players:
            room.players[player_id].is_connected = False
            # Si le salon est encore en attente et que l'hôte quitte, supprimer le salon
            if room.state == RoomState.WAITING and room.players[player_id].is_host:
                del self.rooms[room_code]
        elif player_id in room.spectators:
            room.spectators.remove(player_id)

    def cleanup_old_rooms(self, max_idle_seconds: int = 600):
        """Supprime les salons inactifs depuis plus de max_idle_seconds."""
        now = time.time()
        to_delete = [
            code for code, room in self.rooms.items()
            if now - room.created_at > max_idle_seconds and room.state == RoomState.FINISHED
        ]
        for code in to_delete:
            del self.rooms[code]
