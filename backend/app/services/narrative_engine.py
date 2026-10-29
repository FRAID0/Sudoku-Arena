"""
Moteur Narratif Temps Réel — KI FRAID Narrative Engine 🎙️⚡
Analyse l'état complet du match en direct (scores, combos, cases restantes, erreurs consécutives)
et déclenche des interventions de commentateur e-sport percutantes aux moments clés,
avec régulation anti-spam (cooldown) pour ne jamais lasser le joueur.
"""

import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from app.core.room_manager import Room, GameMode
from app.services.llm_commentator import LiveCommentRequest

logger = logging.getLogger("sudoku_arena.narrative_engine")


class NarrativeEngine:
    def __init__(self, cooldown_seconds: float = 16.0):
        self.cooldown_seconds = cooldown_seconds
        
        # Mémorisation par salon (room_code)
        self.last_comment_time: Dict[str, float] = {}
        self.consecutive_errors: Dict[str, Dict[str, int]] = {}
        self.clutch_triggered: Dict[str, bool] = {}
        self.previous_leader: Dict[str, Optional[str]] = {}
        
        # Mémoire anti-répétition de la manche en cours
        self.recent_phrases: Dict[str, List[str]] = {}
        self.recent_events: Dict[str, List[str]] = {}

    def reset_room(self, room_code: str):
        """Réinitialise les mémoires d'un salon au lancement d'une nouvelle manche."""
        code = room_code.upper()
        self.last_comment_time.pop(code, None)
        self.consecutive_errors.pop(code, None)
        self.clutch_triggered.pop(code, None)
        self.previous_leader.pop(code, None)
        self.recent_phrases.pop(code, None)
        self.recent_events.pop(code, None)

    def record_comment(self, room_code: str, text: str, event_type: str):
        """Enregistre une intervention prononcée pour la mémoire contextuelle anti-répétition."""
        if not text:
            return
        code = room_code.upper()
        if code not in self.recent_phrases:
            self.recent_phrases[code] = []
        if code not in self.recent_events:
            self.recent_events[code] = []

        self.recent_phrases[code].append(text.strip())
        self.recent_events[code].append(event_type)

        if len(self.recent_phrases[code]) > 5:
            self.recent_phrases[code] = self.recent_phrases[code][-5:]
        if len(self.recent_events[code]) > 5:
            self.recent_events[code] = self.recent_events[code][-5:]

    def is_cooling_down(self, room_code: str) -> bool:
        """Vérifie si le commentateur doit garder le silence pour laisser respirer le jeu."""
        code = room_code.upper()
        now = time.time()
        last = self.last_comment_time.get(code, 0.0)
        return (now - last) < self.cooldown_seconds

    def _count_empty_cells(self, room: Room) -> int:
        """Calcule le nombre de cases restantes à remplir."""
        if room.shared_grid:
            grid = room.shared_grid
        elif room.players:
            # En mode course, prend la grille du joueur en tête
            first_p = list(room.players.values())[0]
            grid = first_p.grid or room.initial_puzzle
        else:
            return 40

        if not grid:
            return 40
        return sum(row.count(0) for row in grid)

    def _get_leader_and_trailer(self, room: Room) -> Tuple[Optional[str], Optional[str], float]:
        """Retourne (leader_name, trailer_name, score_diff)."""
        players = list(room.players.values())
        if len(players) < 2:
            actor = players[0].name if players else "Joueur"
            return actor, None, 0.0

        p1, p2 = players[0], players[1]
        if p1.score >= p2.score:
            return p1.name, p2.name, round(p1.score - p2.score, 1)
        else:
            return p2.name, p1.name, round(p2.score - p1.score, 1)

    def evaluate_move(
        self,
        room: Room,
        player_id: str,
        move_result: dict,
        lang: str = "fr"
    ) -> Optional[LiveCommentRequest]:
        """
        Évalue un coup joué et détermine si un moment dramatique e-sport est atteint.
        Ne déclenche un commentaire que si le cooldown est respecté.
        """
        code = room.room_code.upper()
        player = room.players.get(player_id)
        if not player or move_result.get("rejected") or move_result.get("game_over"):
            return None

        # Suivi des erreurs consécutives
        if code not in self.consecutive_errors:
            self.consecutive_errors[code] = {}
        
        is_valid = move_result.get("valid", False)
        if is_valid:
            self.consecutive_errors[code][player_id] = 0
        else:
            self.consecutive_errors[code][player_id] = self.consecutive_errors[code].get(player_id, 0) + 1

        # Vérification du Cooldown Anti-Spam
        if self.is_cooling_down(code):
            return None

        empty_cells = self._count_empty_cells(room)
        leader_name, trailer_name, score_diff = self._get_leader_and_trailer(room)
        opponent = trailer_name if player.name == leader_name else leader_name
        recent_history = list(self.recent_phrases.get(code, []))
        comment_id = f"caster_{int(time.time()*1000)}_{random.randint(100, 999)}"

        # ====================================================================
        # DÉCLENCHEUR 1 : Le Money Time Absolu (Clutch Final)
        # Moins de 8 cases restantes et match serré
        # ====================================================================
        if empty_cells <= 8 and not self.clutch_triggered.get(code, False):
            self.clutch_triggered[code] = True
            self.last_comment_time[code] = time.time()
            logger.info(f"[{code}] Déclencheur CLUTCH_MONEY_TIME ({empty_cells} cases)")
            return LiveCommentRequest(
                event_type="CLUTCH_MONEY_TIME",
                actor_name=player.name,
                opponent_name=opponent,
                leader_name=leader_name,
                score_diff=score_diff,
                empty_cells=empty_cells,
                mode=room.mode.value if hasattr(room.mode, "value") else str(room.mode),
                lang=lang,
                recent_history=recent_history,
                comment_id=comment_id
            )

        # ====================================================================
        # DÉCLENCHEUR 2 : Remontada & Changement de Leader
        # Le joueur dépasse l'adversaire avec une avance
        # ====================================================================
        prev_lead = self.previous_leader.get(code)
        if leader_name and prev_lead and leader_name != prev_lead and player.name == leader_name:
            self.previous_leader[code] = leader_name
            self.last_comment_time[code] = time.time()
            logger.info(f"[{code}] Déclencheur MOMENTUM_SHIFT : {leader_name} prend la tête (+{score_diff} pts)")
            return LiveCommentRequest(
                event_type="MOMENTUM_SHIFT",
                actor_name=player.name,
                opponent_name=opponent,
                leader_name=leader_name,
                score_diff=score_diff,
                empty_cells=empty_cells,
                mode=room.mode.value if hasattr(room.mode, "value") else str(room.mode),
                lang=lang,
                recent_history=recent_history,
                comment_id=comment_id
            )
        self.previous_leader[code] = leader_name

        # ====================================================================
        # DÉCLENCHEUR 3 : Provocation du Bot Rival KI FRAID
        # En mode solo_ai, le bot valide un combo x2
        # ====================================================================
        if room.mode == GameMode.SOLO_AI and player_id == "bot_ki_fraid" and move_result.get("is_combo"):
            self.last_comment_time[code] = time.time()
            logger.info(f"[{code}] Déclencheur BOT_RIVAL_PROVOCATION")
            return LiveCommentRequest(
                event_type="BOT_RIVAL_PROVOCATION",
                actor_name=player.name,
                opponent_name=opponent,
                leader_name=leader_name,
                score_diff=score_diff,
                empty_cells=empty_cells,
                combo_streak=2,
                mode="solo_ai",
                lang=lang,
                recent_history=recent_history,
                comment_id=comment_id
            )

        # ====================================================================
        # DÉCLENCHEUR 4 : Hot Streak (Combo réussi du joueur)
        # ====================================================================
        if is_valid and move_result.get("is_combo"):
            self.last_comment_time[code] = time.time()
            logger.info(f"[{code}] Déclencheur HOT_STREAK pour {player.name}")
            return LiveCommentRequest(
                event_type="HOT_STREAK",
                actor_name=player.name,
                opponent_name=opponent,
                leader_name=leader_name,
                score_diff=score_diff,
                empty_cells=empty_cells,
                combo_streak=room.current_combo_streak or 2,
                mode=room.mode.value if hasattr(room.mode, "value") else str(room.mode),
                lang=lang,
                recent_history=recent_history,
                comment_id=comment_id
            )

        # ====================================================================
        # DÉCLENCHEUR 5 : Choke sous pression (2 fautes consécutives)
        # ====================================================================
        if not is_valid and self.consecutive_errors[code].get(player_id, 0) >= 2:
            self.consecutive_errors[code][player_id] = 0
            self.last_comment_time[code] = time.time()
            logger.info(f"[{code}] Déclencheur CHOKE_PRESSURE pour {player.name}")
            return LiveCommentRequest(
                event_type="CHOKE_PRESSURE",
                actor_name=player.name,
                opponent_name=opponent,
                leader_name=leader_name,
                score_diff=score_diff,
                empty_cells=empty_cells,
                mode=room.mode.value if hasattr(room.mode, "value") else str(room.mode),
                lang=lang,
                recent_history=recent_history,
                comment_id=comment_id
            )

        return None

    def evaluate_timeout(
        self,
        room: Room,
        timed_out_player_id: str,
        lang: str = "fr"
    ) -> Optional[LiveCommentRequest]:
        """Évalue un dépassement de chrono fatale (tour perdu)."""
        code = room.room_code.upper()
        player = room.players.get(timed_out_player_id)
        if not player or self.is_cooling_down(code):
            return None

        leader_name, trailer_name, score_diff = self._get_leader_and_trailer(room)
        empty_cells = self._count_empty_cells(room)
        opponent = trailer_name if player.name == leader_name else leader_name
        recent_history = list(self.recent_phrases.get(code, []))
        comment_id = f"caster_{int(time.time()*1000)}_{random.randint(100, 999)}"

        self.last_comment_time[code] = time.time()
        logger.info(f"[{code}] Déclencheur TIMEOUT_PRESSURE pour {player.name}")
        return LiveCommentRequest(
            event_type="CHOKE_PRESSURE",
            actor_name=player.name,
            opponent_name=opponent,
            leader_name=leader_name,
            score_diff=score_diff,
            empty_cells=empty_cells,
            mode=room.mode.value if hasattr(room.mode, "value") else str(room.mode),
            lang=lang,
            recent_history=recent_history,
            comment_id=comment_id
        )


# Singleton
narrative_engine = NarrativeEngine(cooldown_seconds=16.0)
