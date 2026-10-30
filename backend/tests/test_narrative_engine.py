import unittest
import asyncio
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.room_manager import RoomManager, GameMode, Player, Room
from app.services.narrative_engine import NarrativeEngine
from app.services.llm_commentator import (
    LiveCommentRequest,
    LLMCommentatorService,
    ShuffleBag,
    is_text_too_similar
)
from app.services.tts_service import CACHE_DIR


class TestNarrativeEngine(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.engine = NarrativeEngine(cooldown_seconds=10.0)
        self.offline_service = LLMCommentatorService(api_key="")
        self.offline_service.client = None

        # Création d'une salle de test avec 2 joueurs
        p1 = Player("p1", "Fraid", is_host=True)
        p1.score = 50.0
        p2 = Player("p2", "Shadow", is_host=False)
        p2.score = 45.0

        self.room = Room(room_code="TEST", host=p1, mode=GameMode.CLASH)
        self.room.players["p2"] = p2
        # Grille 9x9 avec 20 cases vides (0)
        self.room.shared_grid = [[1 if (r + c) % 2 == 0 else 0 for c in range(9)] for r in range(9)]

    def test_hot_streak_trigger(self):
        # Combo réussi
        move_res = {"valid": True, "is_combo": True, "score": 60.0}
        req = self.engine.evaluate_move(self.room, "p1", move_res, lang="fr")
        self.assertIsNotNone(req)
        self.assertEqual(req.event_type, "HOT_STREAK")
        self.assertEqual(req.actor_name, "Fraid")
        self.assertIsNotNone(req.comment_id)

    def test_cooldown_anti_spam(self):
        # Premier événement passe
        move_res = {"valid": True, "is_combo": True, "score": 60.0}
        req1 = self.engine.evaluate_move(self.room, "p1", move_res, lang="fr")
        self.assertIsNotNone(req1)

        # Deuxième événement immédiat : doit être bloqué par le cooldown
        req2 = self.engine.evaluate_move(self.room, "p1", move_res, lang="fr")
        self.assertIsNone(req2, "Le cooldown anti-spam doit bloquer les interventions trop rapprochées")

    def test_choke_pressure_trigger(self):
        engine = NarrativeEngine(cooldown_seconds=0.0) # Désactiver le cooldown pour le test
        err_res = {"valid": False, "is_combo": False}

        # Première erreur : pas encore de choke
        req1 = engine.evaluate_move(self.room, "p1", err_res, lang="fr")
        self.assertIsNone(req1)

        # Deuxième erreur consécutive : déclencheur CHOKE_PRESSURE
        req2 = engine.evaluate_move(self.room, "p1", err_res, lang="fr")
        self.assertIsNotNone(req2)
        self.assertEqual(req2.event_type, "CHOKE_PRESSURE")

    def test_clutch_money_time_trigger(self):
        engine = NarrativeEngine(cooldown_seconds=0.0)
        # Remplir la grille pour ne laisser que 5 cases vides
        grid_clutch = [[1]*9 for _ in range(9)]
        for i in range(5):
            grid_clutch[0][i] = 0
        self.room.shared_grid = grid_clutch

        move_res = {"valid": True, "is_combo": False, "score": 52.0}
        req = engine.evaluate_move(self.room, "p1", move_res, lang="fr")
        self.assertIsNotNone(req)
        self.assertEqual(req.event_type, "CLUTCH_MONEY_TIME")
        self.assertLessEqual(req.empty_cells, 8)

    def test_in_match_memory_and_reset(self):
        code = self.room.room_code
        self.engine.record_comment(code, "Incroyable bascule au score !", "MOMENTUM_SHIFT")
        self.engine.record_comment(code, "Quel rythme d'enfer !", "HOT_STREAK")

        self.assertEqual(len(self.engine.recent_phrases[code]), 2)
        self.assertIn("Incroyable bascule au score !", self.engine.recent_phrases[code])

        # Vérifier que evaluate_move injecte l'historique récent
        engine = NarrativeEngine(cooldown_seconds=0.0)
        engine.record_comment(code, "Première phrase prononcée", "WELCOME")
        move_res = {"valid": True, "is_combo": True, "score": 60.0}
        req = engine.evaluate_move(self.room, "p1", move_res, lang="fr")
        self.assertIsNotNone(req)
        self.assertIn("Première phrase prononcée", req.recent_history)

        # Reset
        self.engine.reset_room(code)
        self.assertNotIn(code, self.engine.recent_phrases)
        self.assertNotIn(code, self.engine.recent_events)

    def test_shuffle_bag_variety(self):
        items = ["A", "B", "C", "D"]
        bag = ShuffleBag(items)
        drawn = [bag.draw() for _ in range(4)]
        self.assertEqual(set(drawn), set(items), "Le ShuffleBag doit épuiser tout le deck sans répétition")

        # 8 tirages consécutifs : aucune répétition consécutive
        drawn_series = [bag.draw() for _ in range(8)]
        for i in range(len(drawn_series) - 1):
            self.assertNotEqual(drawn_series[i], drawn_series[i+1], "Pas de répétition consécutive immédiate")

    def test_similarity_filter(self):
        history = [
            "Incroyable bascule ! Fraid passe devant au score.",
            "Quel duel d'anthologie aujourd'hui !"
        ]
        # Même début de phrase (3 mots) -> Rejeté
        self.assertTrue(is_text_too_similar("Incroyable bascule ! Fraid prend le lead.", history))
        # Phrases avec fort chevauchement de mots -> Rejeté
        self.assertTrue(is_text_too_similar("Duel d'anthologie aujourd'hui entre les joueurs !", history))
        # Phrase totalement différente -> Acceptée
        self.assertFalse(is_text_too_similar("La grille se débloque avec une grande précision.", history))

    def test_offline_live_comment_generation(self):
        req = LiveCommentRequest(
            event_type="CLUTCH_MONEY_TIME",
            actor_name="Fraid",
            opponent_name="Shadow",
            leader_name="Fraid",
            score_diff=5.0,
            empty_cells=6,
            lang="fr"
        )
        res = asyncio.run(self.offline_service.generate_live_comment(req))
        self.assertEqual(res.source, "fallback")
        self.assertEqual(res.mood, "tense")
        self.assertGreaterEqual(res.rate, 1.10)
        self.assertIn("6", res.text)

    def test_api_commentator_live_endpoint(self):
        payload = {
            "event_type": "MOMENTUM_SHIFT",
            "actor_name": "Fraid",
            "opponent_name": "Shadow",
            "leader_name": "Fraid",
            "score_diff": 12.0,
            "empty_cells": 15,
            "combo_streak": 2,
            "lang": "en"
        }
        res = self.client.post("/api/commentator/live", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("text", data)
        self.assertEqual(data["mood"], "hype")
        self.assertEqual(data["lang"], "en")

    def test_api_commentator_audio_endpoint(self):
        # 1. Fichier non existant -> 404
        res_404 = self.client.get("/api/commentator/audio/non_existent.mp3")
        self.assertEqual(res_404.status_code, 404)

        # 2. Fichier temporaire existant dans le cache -> 200 audio/mpeg
        os.makedirs(CACHE_DIR, exist_ok=True)
        dummy_path = os.path.join(CACHE_DIR, "dummy_test.mp3")
        with open(dummy_path, "wb") as f:
            f.write(b"ID3dummy_audio_bytes")

        try:
            res_200 = self.client.get("/api/commentator/audio/dummy_test.mp3")
            self.assertEqual(res_200.status_code, 200)
            self.assertEqual(res_200.headers["content-type"], "audio/mpeg")
        finally:
            if os.path.exists(dummy_path):
                os.remove(dummy_path)

    def test_api_commentator_tts_endpoint(self):
        # Test endpoint de synthèse ou cache Edge-TTS à la demande
        payload = {
            "text": "Mode Simple sélectionné ! Concentration maximale !",
            "lang": "fr"
        }
        res = self.client.post("/api/commentator/tts", json=payload)
        # Peut renvoyer 200 avec audio_url si edge-tts réussit ou si mis en cache
        if res.status_code == 200:
            data = res.json()
            self.assertIn("audio_url", data)
            self.assertIn("text", data)
            self.assertTrue(data["audio_url"].startswith("/api/commentator/audio/"))


if __name__ == "__main__":
    unittest.main()
