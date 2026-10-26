"""
Unit & Integration Tests for RedisManager and Distributed Room State
Valide la sérialisation/désérialisation JSON et le comportement du gestionnaire Redis.
"""

import os
import pytest
import pytest_asyncio
from app.core.room_manager import RoomManager, Room, Player, GameMode, RoomState
from app.core.redis_manager import RedisManager


def test_player_serialization_roundtrip():
    """Vérifie la sérialisation et reconstruction exacte d'un joueur."""
    player = Player(player_id="p1", name="Alice", is_host=True)
    player.score = 42.5
    player.mistakes = 2
    player.progress = 75.0
    player.finished = True
    player.finish_time = 123.45

    data = player.to_dict()
    reconstructed = Player.from_dict(data)

    assert reconstructed.player_id == "p1"
    assert reconstructed.name == "Alice"
    assert reconstructed.is_host is True
    assert reconstructed.score == 42.5
    assert reconstructed.mistakes == 2
    assert reconstructed.progress == 75.0
    assert reconstructed.finished is True
    assert reconstructed.finish_time == 123.45


def test_room_serialization_roundtrip():
    """Vérifie la sérialisation et reconstruction exacte d'un salon complet."""
    manager = RoomManager()
    room = manager.create_room(
        host_id="host_1",
        host_name="Bob",
        mode=GameMode.CLASH,
        difficulty="hard",
        validation_mode="strict"
    )

    data = room.to_dict()
    assert data["room_code"] == room.room_code
    assert data["mode"] == "clash"
    assert data["difficulty"] == "hard"
    assert data["validation_mode"] == "strict"
    assert "host_1" in data["players"]

    reconstructed = Room.from_dict(data)
    assert reconstructed.room_code == room.room_code
    assert reconstructed.mode == GameMode.CLASH
    assert reconstructed.difficulty == "hard"
    assert reconstructed.validation_mode == "strict"
    assert len(reconstructed.players) == 1
    assert reconstructed.players["host_1"].name == "Bob"
    assert reconstructed.initial_puzzle == room.initial_puzzle
    assert reconstructed.solution == room.solution


@pytest.mark.asyncio
async def test_redis_manager_offline_fallback():
    """Vérifie que RedisManager gère gracieusement un hôte inaccessible (Fallback)."""
    # Port inaccessible
    manager = RedisManager(host="127.0.0.1", port=59999)
    connected = await manager.connect()

    assert connected is False
    assert manager.is_connected is False

    # Les méthodes doivent retourner False / None sans lever d'exception
    rm = RoomManager()
    room = rm.create_room(host_id="h1", host_name="Test")
    assert await manager.save_room(room) is False
    assert await manager.get_room("TEST") is None
    assert await manager.delete_room("TEST") is False
    assert await manager.publish_event("TEST", {"event": "PING"}) is False

    await manager.close()


@pytest.mark.asyncio
async def test_redis_manager_live_integration():
    """
    Test d'intégration réel avec le conteneur Redis local (port 6379).
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    manager = RedisManager(host=host, port=port)
    connected = await manager.connect()

    if not connected:
        pytest.skip("Serveur Redis local non accessible sur localhost:6379")

    rm = RoomManager()
    room = rm.create_room(host_id="redis_host", host_name="RedisPlayer", mode=GameMode.CLASH)

    # 1. Sauvegarde dans Redis
    saved = await manager.save_room(room, ttl=60)
    assert saved is True

    # 2. Récupération et vérification
    fetched = await manager.get_room(room.room_code)
    assert fetched is not None
    assert fetched.room_code == room.room_code
    assert fetched.players["redis_host"].name == "RedisPlayer"

    # 3. Publication d'un événement
    published = await manager.publish_event(room.room_code, {"event": "TEST_EVENT", "data": 123})
    assert published is True

    # 4. Suppression
    deleted = await manager.delete_room(room.room_code)
    assert deleted is True

    # 5. Doit être None après suppression
    assert await manager.get_room(room.room_code) is None

    await manager.close()
