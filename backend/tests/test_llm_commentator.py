import unittest
import asyncio
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.llm_commentator import (
    LLMCommentatorService,
    IntroRequest,
    DebriefRequest,
    CommentatorResponse
)


class TestLLMCommentator(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Service isolé sans client pour tester le fallback déterministe
        self.offline_service = LLMCommentatorService(api_key="")
        self.offline_service.client = None

    def test_health_endpoint(self):
        res = self.client.get("/api/commentator/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["fallback_ready"])
        self.assertIn("fr", data["supported_languages"])
        self.assertIn("en", data["supported_languages"])
        self.assertIn("de", data["supported_languages"])

    def test_offline_intro_fallback_fr(self):
        req = IntroRequest(
            player1_name="Alice",
            player2_name="Bob",
            mode="clash",
            clash_rule="combo_capped",
            lang="fr"
        )
        res = asyncio.run(self.offline_service.generate_intro(req))
        self.assertIsInstance(res, CommentatorResponse)
        self.assertEqual(res.lang, "fr")
        self.assertEqual(res.source, "fallback")
        self.assertIn("Alice", res.text)
        self.assertIn("Bob", res.text)
        self.assertEqual(res.audio_fallback_key, "WELCOME")

    def test_offline_intro_fallback_en(self):
        req = IntroRequest(
            player1_name="Alice",
            player2_name="Bob",
            mode="race",
            lang="en"
        )
        res = asyncio.run(self.offline_service.generate_intro(req))
        self.assertEqual(res.lang, "en")
        self.assertEqual(res.source, "fallback")
        self.assertIn("Alice", res.text)
        self.assertIn("Bob", res.text)

    def test_offline_intro_fallback_de(self):
        req = IntroRequest(
            player1_name="Hans",
            player2_name="KI FRAID Bot",
            mode="solo_ai",
            lang="de"
        )
        res = asyncio.run(self.offline_service.generate_intro(req))
        self.assertEqual(res.lang, "de")
        self.assertEqual(res.source, "fallback")
        self.assertIn("Hans", res.text)

    def test_offline_debrief_win_fallback(self):
        req = DebriefRequest(
            winner_name="Max",
            loser_name="Leo",
            winner_score=150.0,
            loser_score=90.0,
            total_combos=3,
            lang="fr"
        )
        res = asyncio.run(self.offline_service.generate_debrief(req))
        self.assertEqual(res.source, "fallback")
        self.assertIn("Max", res.text)
        self.assertIn("Leo", res.text)
        self.assertIn("150", res.text)
        self.assertEqual(res.audio_fallback_key, "VICTORY")

    def test_offline_debrief_draw_fallback(self):
        req = DebriefRequest(
            winner_name="PlayerA",
            loser_name="PlayerB",
            winner_score=100.0,
            is_draw=True,
            lang="en"
        )
        res = asyncio.run(self.offline_service.generate_debrief(req))
        self.assertEqual(res.source, "fallback")
        self.assertIn("PlayerA", res.text)
        self.assertIn("PlayerB", res.text)

    def test_api_intro_endpoint(self):
        payload = {
            "player1_name": "Antigravity",
            "player2_name": "Challenger",
            "mode": "clash",
            "clash_rule": "combo_capped",
            "lang": "fr"
        }
        res = self.client.post("/api/commentator/intro", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("text", data)
        self.assertIn(data["source"], ["gemini", "fallback"])
        self.assertEqual(data["lang"], "fr")
        self.assertEqual(data["audio_fallback_key"], "WELCOME")

    def test_api_debrief_endpoint(self):
        payload = {
            "winner_name": "Antigravity",
            "loser_name": "Challenger",
            "winner_score": 120.0,
            "loser_score": 80.0,
            "is_draw": False,
            "total_combos": 2,
            "duration_seconds": 95,
            "mode": "clash",
            "lang": "en"
        }
        res = self.client.post("/api/commentator/debrief", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("text", data)
        self.assertIn(data["source"], ["gemini", "fallback"])
        self.assertEqual(data["lang"], "en")
        self.assertEqual(data["audio_fallback_key"], "VICTORY")


if __name__ == "__main__":
    unittest.main()
