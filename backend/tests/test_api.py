import unittest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


class TestFastAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "Sudoku Arena Backend")

    def test_create_and_get_room(self):
        # Créer un salon
        payload = {
            "host_id": "host_123",
            "host_name": "Antigravity",
            "mode": "race",
            "difficulty": "easy"
        }
        res_create = self.client.post("/api/rooms", json=payload)
        self.assertEqual(res_create.status_code, 200)
        data_create = res_create.json()
        self.assertIn("room_code", data_create)
        room_code = data_create["room_code"]

        # Récupérer l'état du salon
        res_get = self.client.get(f"/api/rooms/{room_code}")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertEqual(data_get["room_code"], room_code)
        self.assertEqual(data_get["state"], "waiting")
        self.assertEqual(len(data_get["players"]), 1)
        self.assertEqual(data_get["players"][0]["name"], "Antigravity")


if __name__ == "__main__":
    unittest.main()
