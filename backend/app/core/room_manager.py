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


class ClashRule(str, Enum):
    STRICT = "strict"              # Option A : Alternance stricte (1 coup par tour)
    COMBO_CAPPED = "combo_capped"  # Option C : Combo limité (max 2 coups consécutifs, défaut recommandé)
    UNLIMITED = "unlimited"        # Option B : Série illimitée (tant qu'on valide, on garde la main)


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

REASON_MESSAGES = {
    "ERR_INVALID_DATA": {
        "fr": "Coordonnées ou valeur non numériques.",
        "en": "Non-numeric coordinates or value.",
        "de": "Nicht-numerische Koordinaten oder Werte."
    },
    "ERR_OUT_OF_BOUNDS": {
        "fr": "Coordonnées (0-8) ou chiffre (1-9) hors limites.",
        "en": "Coordinates (0-8) or number (1-9) out of bounds.",
        "de": "Koordinaten (0-8) oder Zahl (1-9) außerhalb des gültigen Bereichs."
    },
    "ERR_NOT_YOUR_TURN": {
        "fr": "Ce n'est pas votre tour !",
        "en": "It is not your turn!",
        "de": "Du bist nicht am Zug!"
    },
    "ERR_CELL_FILLED": {
        "fr": "Cette case est déjà remplie.",
        "en": "This cell is already filled.",
        "de": "Dieses Feld ist bereits belegt."
    },
    "ERR_INCORRECT_SOLUTION": {
        "fr": "Chiffre incorrect (ne correspond pas à la solution finale du casse-tête).",
        "en": "Incorrect number (does not match the puzzle's final solution).",
        "de": "Falsche Zahl (stimmt nicht mit der finalen Lösung des Rätsels überein)."
    },
    "ERR_CONFLICT": {
        "fr": "Conflit : ce chiffre est déjà présent sur la même ligne, colonne ou bloc 3x3 !",
        "en": "Conflict: this number is already in the same row, column, or 3x3 box!",
        "de": "Konflikt: Diese Zahl existiert bereits in derselben Zeile, Spalte oder im 3x3-Block!"
    }
}

def get_localized_reason(code: str, lang: str = "fr") -> str:
    lang_pack = REASON_MESSAGES.get(code, {})
    return lang_pack.get(lang, lang_pack.get("fr", code))


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

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "is_host": self.is_host,
            "is_connected": self.is_connected,
            "grid": self.grid,
            "score": self.score,
            "mistakes": self.mistakes,
            "progress": self.progress,
            "finished": self.finished,
            "finish_time": self.finish_time
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        p = cls(player_id=data["player_id"], name=data["name"], is_host=data.get("is_host", False))
        p.is_connected = data.get("is_connected", True)
        p.grid = data.get("grid")
        p.score = float(data.get("score", 0.0))
        p.mistakes = int(data.get("mistakes", 0))
        p.progress = float(data.get("progress", 0.0))
        p.finished = data.get("finished", False)
        p.finish_time = data.get("finish_time")
        return p


class Room:
    def __init__(self, room_code: str, host: Player, mode: GameMode = GameMode.CLASH, difficulty: str = "medium", validation_mode: str = "simple", clash_rule: ClashRule = ClashRule.COMBO_CAPPED, lang: str = "fr"):
        self.room_code = room_code
        self.mode = mode
        self.difficulty = difficulty.lower() if difficulty.lower() in POINTS else "medium"
        self.validation_mode = validation_mode.lower() if validation_mode.lower() in ("simple", "strict") else "simple"
        self.lang = lang.lower() if lang.lower() in ("fr", "en", "de") else "fr"
        if isinstance(clash_rule, ClashRule):
            self.clash_rule = clash_rule
        else:
            try:
                self.clash_rule = ClashRule(str(clash_rule).lower())
            except ValueError:
                self.clash_rule = ClashRule.COMBO_CAPPED
        self.current_combo_streak: int = 0
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

    def to_dict(self) -> dict:
        return {
            "room_code": self.room_code,
            "mode": self.mode.value if isinstance(self.mode, GameMode) else str(self.mode),
            "difficulty": self.difficulty,
            "validation_mode": self.validation_mode,
            "clash_rule": self.clash_rule.value if isinstance(self.clash_rule, ClashRule) else str(self.clash_rule),
            "lang": self.lang,
            "current_combo_streak": self.current_combo_streak,
            "state": self.state.value if isinstance(self.state, RoomState) else str(self.state),
            "created_at": self.created_at,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "spectators": self.spectators,
            "winner_id": self.winner_id,
            "current_turn_player_id": self.current_turn_player_id,
            "turn_start_time": self.turn_start_time,
            "turn_timeout": self.turn_timeout,
            "initial_puzzle": self.initial_puzzle,
            "solution": self.solution,
            "shared_grid": self.shared_grid
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        players_data = data.get("players", {})
        host_p = None
        for p_dict in players_data.values():
            if p_dict.get("is_host"):
                host_p = Player.from_dict(p_dict)
                break
        if not host_p and players_data:
            host_p = Player.from_dict(next(iter(players_data.values())))
        if not host_p:
            host_p = Player(player_id="unknown_host", name="Host", is_host=True)

        mode_val = data.get("mode", "clash")
        try:
            mode = GameMode(mode_val)
        except ValueError:
            mode = GameMode.CLASH

        clash_rule_val = data.get("clash_rule", ClashRule.COMBO_CAPPED)
        try:
            clash_rule = ClashRule(clash_rule_val)
        except ValueError:
            clash_rule = ClashRule.COMBO_CAPPED

        room = cls(
            room_code=data["room_code"],
            host=host_p,
            mode=mode,
            difficulty=data.get("difficulty", "medium"),
            validation_mode=data.get("validation_mode", "simple"),
            clash_rule=clash_rule,
            lang=data.get("lang", "fr")
        )
        room.current_combo_streak = int(data.get("current_combo_streak", 0))
        state_val = data.get("state", "waiting")
        try:
            room.state = RoomState(state_val)
        except ValueError:
            room.state = RoomState.WAITING

        room.created_at = data.get("created_at", time.time())
        room.start_time = data.get("start_time")
        room.end_time = data.get("end_time")
        room.players = {pid: Player.from_dict(p_dict) for pid, p_dict in players_data.items()}
        room.spectators = data.get("spectators", [])
        room.winner_id = data.get("winner_id")
        room.current_turn_player_id = data.get("current_turn_player_id")
        room.turn_start_time = data.get("turn_start_time")
        room.turn_timeout = float(data.get("turn_timeout", 20.0))
        room.initial_puzzle = data.get("initial_puzzle")
        room.solution = data.get("solution")
        room.shared_grid = data.get("shared_grid")
        return room

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
        """Passe la main au joueur suivant et réinitialise le chrono et la série de combo."""
        players = self.player_list
        if len(players) >= 2:
            current_idx = next((i for i, p in enumerate(players) if p.player_id == self.current_turn_player_id), 0)
            next_idx = (current_idx + 1) % len(players)
            self.current_turn_player_id = players[next_idx].player_id
        self.current_combo_streak = 0
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

    def create_room(self, host_id: str, host_name: str, mode: GameMode = GameMode.CLASH, difficulty: str = "medium", validation_mode: str = "simple", clash_rule: ClashRule = ClashRule.COMBO_CAPPED, lang: str = "fr") -> Room:
        code = self._generate_unique_code()
        default_names = {"fr": "Joueur 1", "en": "Player 1", "de": "Spieler 1"}
        if not host_name or not host_name.strip() or host_name.strip() in ("Joueur 1", "Player 1", "Spieler 1"):
            host_name = default_names.get(lang, "Joueur 1")

        host = Player(player_id=host_id, name=host_name, is_host=True)
        room = Room(room_code=code, host=host, mode=mode, difficulty=difficulty, validation_mode=validation_mode, clash_rule=clash_rule, lang=lang)

        # Générer le puzzle
        puzzle, solution = SudokuEngine.generate_puzzle(difficulty)
        room.initial_puzzle = puzzle
        room.solution = solution
        room.shared_grid = copy.deepcopy(puzzle)
        host.grid = copy.deepcopy(puzzle)

        # Si mode Solo AI, inscrire automatiquement le bot comme Joueur 2
        if mode == GameMode.SOLO_AI:
            bot_names = {"fr": "IA FRAID 🤖", "en": "AI FRAID 🤖", "de": "KI FRAID 🤖"}
            bot_name = bot_names.get(room.lang, "IA FRAID 🤖")
            bot_player = Player(player_id="bot_ki_fraid", name=bot_name, is_host=False)
            bot_player.grid = copy.deepcopy(puzzle)
            room.players[bot_player.player_id] = bot_player

        self.rooms[code] = room
        return room

    def join_room(self, room_code: str, player_id: str, player_name: str) -> Tuple[Room, str]:
        code = room_code.upper().strip()
        room = self.rooms.get(code)
        if not room:
            raise ValueError(f"Salon '{code}' introuvable.")

        default_p2 = {"fr": "Joueur 2", "en": "Player 2", "de": "Spieler 2"}
        if not player_name or not player_name.strip() or player_name.strip() in ("Joueur 2", "Player 2", "Spieler 2", "Challenger"):
            player_name = default_p2.get(room.lang, "Joueur 2")

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
        room.current_combo_streak = 0
        # Le premier joueur actif est l'hôte
        room.current_turn_player_id = room.player_list[0].player_id
        return room

    def play_move(self, room_code: str, player_id: str, row: int, col: int, value: int) -> Dict:
        """
        Valide et applique un coup soumis par un joueur avec arbitrage du tour et du score.
        Supporte deux modes de validation ('simple' et 'strict') et 3 variantes de tour Clash :
        - STRICT : 1 coup par tour obligatoire (alternance stricte)
        - COMBO_CAPPED : max 2 coups consécutifs par joueur si valide (recommandé par défaut)
        - UNLIMITED : le joueur garde la main tant qu'il réussit ses coups
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
            return {
                "valid": False,
                "rejected": True,
                "reason_code": "ERR_INVALID_DATA",
                "reason": get_localized_reason("ERR_INVALID_DATA", room.lang)
            }

        if not (0 <= row < 9 and 0 <= col < 9 and 1 <= value <= 9):
            return {
                "valid": False,
                "rejected": True,
                "reason_code": "ERR_OUT_OF_BOUNDS",
                "reason": get_localized_reason("ERR_OUT_OF_BOUNDS", room.lang)
            }

        # En mode Clash ou Solo AI : vérifier impérativement si c'est son tour
        if room.mode in (GameMode.CLASH, GameMode.SOLO_AI):
            if player_id != room.current_turn_player_id:
                return {
                    "valid": False,
                    "rejected": True,
                    "reason_code": "ERR_NOT_YOUR_TURN",
                    "reason": get_localized_reason("ERR_NOT_YOUR_TURN", room.lang),
                    "current_turn": room.current_turn_player_id
                }

        target_grid = room.shared_grid if room.mode in (GameMode.CLASH, GameMode.SOLO_AI) else player.grid

        # Case déjà remplie
        if target_grid[row][col] != 0:
            return {
                "valid": False,
                "rejected": True,
                "reason_code": "ERR_CELL_FILLED",
                "reason": get_localized_reason("ERR_CELL_FILLED", room.lang)
            }

        time_taken = time.time() - (room.turn_start_time or time.time())

        # Validation selon le mode choisi :
        # - Mode 'strict' (Casse-Tête) : doit correspondre à la solution finale unique
        # - Mode 'simple' (Règles locales) : doit respecter la ligne, la colonne et le bloc 3x3 actuel
        if room.validation_mode == "strict":
            is_valid = SudokuEngine.validate_move(room.solution, row, col, value)
            error_code = "ERR_INCORRECT_SOLUTION"
            error_reason = get_localized_reason(error_code, room.lang)
        else:
            is_valid = SudokuEngine.is_valid_placement(target_grid, row, col, value)
            error_code = "ERR_CONFLICT"
            error_reason = get_localized_reason(error_code, room.lang)

        if is_valid:
            target_grid[row][col] = value
            base_pts, bonus_pts = room.calculate_points_and_bonus(time_taken)
            points_gained = base_pts + bonus_pts
            player.score += points_gained
            player.progress = room.calculate_progress(target_grid)

            # Gestion de l'alternance et des combos selon la variante Clash choisie :
            if room.mode in (GameMode.CLASH, GameMode.SOLO_AI):
                room.current_combo_streak += 1
                streak_recorded = room.current_combo_streak
                if room.clash_rule == ClashRule.STRICT:
                    # Option A : Alternance stricte systématique (1 coup par tour)
                    next_player = room.switch_turn()
                    turn_switched = True
                    is_combo = False
                elif room.clash_rule == ClashRule.UNLIMITED:
                    # Option B : Série illimitée (tant qu'on valide, on garde la main)
                    next_player = room.current_turn_player_id
                    room.turn_start_time = time.time()
                    turn_switched = False
                    is_combo = (streak_recorded > 1)
                else:
                    # Option C (Défaut : COMBO_CAPPED) : Max 2 coups consécutifs
                    if streak_recorded < 2:
                        next_player = room.current_turn_player_id
                        room.turn_start_time = time.time()
                        turn_switched = False
                        is_combo = True
                    else:
                        next_player = room.switch_turn()
                        turn_switched = True
                        is_combo = False
            else:
                streak_recorded = 0
                next_player = room.current_turn_player_id
                turn_switched = False
                is_combo = False

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
                "turn_switched": turn_switched,
                "combo_streak": streak_recorded,
                "is_combo": is_combo,
                "clash_rule": room.clash_rule.value,
                "shared_grid": target_grid,
                "game_over": room.state == RoomState.FINISHED,
                "winner_id": room.winner_id
            }
        else:
            # ERREUR : pénalité de 1 point, bris de combo et passage de tour immédiat
            player.mistakes += 1
            player.score = max(0.0, player.score - 1.0)
            room.current_combo_streak = 0
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
                "turn_switched": (room.mode in (GameMode.CLASH, GameMode.SOLO_AI)),
                "combo_streak": 0,
                "is_combo": False,
                "clash_rule": room.clash_rule.value,
                "game_over": False,
                "reason_code": error_code,
                "reason": error_reason
            }

    def timeout_turn(self, room_code: str) -> Optional[Dict]:
        """Déclenché quand le chrono du tour expire."""
        room = self.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME:
            return None

        current_player = room.players.get(room.current_turn_player_id)
        # Timeout ne déduit plus de pénalité : on conserve les points acquis.
        # La seule pénalité s'applique lors d'un mouvement invalide.
        room.current_combo_streak = 0
        next_player = room.switch_turn()
        return {
            "timeout": True,
            "timed_out_player_id": current_player.player_id if current_player else None,
            "score": current_player.score if current_player else 0.0,
            "current_turn": next_player,
            "combo_streak": 0,
            "turn_switched": True
        }

    def leave_room(self, room_code: str, player_id: str) -> Optional[Dict]:
        room = self.rooms.get(room_code)
        if not room:
            return None

        leaving_player = room.players.get(player_id)
        if leaving_player:
            leaving_player.is_connected = False

            if room.state == RoomState.WAITING:
                if leaving_player.is_host:
                    del self.rooms[room_code]
                    return {"room_deleted": True}
                else:
                    del room.players[player_id]
                    return {"player_left": True, "remaining_players": room.player_list}

            elif room.state == RoomState.IN_GAME:
                # Rupture de connexion en plein match -> Victoire par forfait pour l'autre joueur !
                active_players = [p for p in room.player_list if p.is_connected and p.player_id != player_id]
                if len(active_players) >= 1:
                    room.state = RoomState.FINISHED
                    room.winner_id = active_players[0].player_id
                    room.end_time = time.time()
                    return {
                        "forfeit": True,
                        "winner_id": room.winner_id,
                        "left_player_id": player_id,
                        "left_player_name": leaving_player.name
                    }
        elif player_id in room.spectators:
            room.spectators.remove(player_id)

        return None
