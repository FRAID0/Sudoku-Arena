"""
FastAPI Server & WebSocket Gateway for Sudoku Arena
Expose les endpoints REST et les connexions WebSockets pour les salons de jeu.
Gère le décompte synchronisé, le bot autonome KI FRAID et la télémétrie MQTT Mosquitto.
"""

import asyncio
import json
import os
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import paho.mqtt.client as mqtt

from app.core.room_manager import RoomManager, GameMode, RoomState
from app.ai.bot import KIFraidBot

app = FastAPI(
    title="Sudoku Arena API",
    version="1.0.0",
    description="Real-Time Multiplayer & AI Sudoku Game Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

room_manager = RoomManager()

# Configuration MQTT Télémétrie
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
mqtt_client = mqtt.Client()


def init_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"MQTT connecté à {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"MQTT non disponible (mode sans broker) : {e}")


def publish_mqtt(topic: str, payload: dict):
    try:
        mqtt_client.publish(topic, json.dumps(payload))
    except Exception:
        pass


@app.on_event("startup")
async def startup_event():
    init_mqtt()


class CreateRoomRequest(BaseModel):
    host_id: str
    host_name: str
    mode: str = "race"
    difficulty: str = "medium"


class ConnectionManager:
    """Gère les connexions WebSockets actives par salon."""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = []
        self.active_connections[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.active_connections:
            if websocket in self.active_connections[room_code]:
                self.active_connections[room_code].remove(websocket)
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]

    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.active_connections:
            data = json.dumps(message)
            for connection in self.active_connections[room_code]:
                try:
                    await connection.send_text(data)
                except Exception:
                    pass


ws_manager = ConnectionManager()


async def run_ai_opponent(room_code: str, difficulty: str):
    """Boucle d'actions asynchrone du bot KI FRAID dans un salon."""
    bot = KIFraidBot(difficulty)
    ai_id = "bot_ki_fraid"

    while True:
        room = room_manager.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME:
            break

        bot_player = room.players.get(ai_id)
        if not bot_player or bot_player.finished:
            break

        move = bot.choose_move(bot_player.grid, room.solution)
        if not move:
            break

        await asyncio.sleep(move["delay"])

        # Vérifier si la partie est toujours en cours après le délai de réflexion
        room = room_manager.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME:
            break

        res = room_manager.play_move(room_code, ai_id, move["row"], move["col"], move["value"])
        await ws_manager.broadcast(room_code, {
            "event": "MOVE_RESULT",
            "result": res
        })

        if res.get("valid"):
            publish_mqtt("game/led", {"state": "green", "source": "bot"})
        else:
            publish_mqtt("game/led", {"state": "red", "source": "bot"})

        if res.get("game_over"):
            publish_mqtt("game/led", {"state": "rainbow", "winner": ai_id})
            break


async def start_game_flow(room_code: str):
    """Décompte synchronisé 3.. 2.. 1.. GO ! puis lancement."""
    for count in [3, 2, 1]:
        await ws_manager.broadcast(room_code, {
            "event": "COUNTDOWN",
            "count": count
        })
        await asyncio.sleep(1)

    room = room_manager.start_game(room_code)
    await ws_manager.broadcast(room_code, {
        "event": "GAME_STARTED",
        "start_time": room.start_time,
        "initial_puzzle": room.initial_puzzle
    })
    publish_mqtt("game/led", {"state": "blue"})

    if room.mode == GameMode.SOLO_AI:
        asyncio.create_task(run_ai_opponent(room_code, room.difficulty))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Sudoku Arena Backend",
        "active_rooms": len(room_manager.rooms)
    }


@app.post("/api/rooms")
async def create_room(req: CreateRoomRequest):
    try:
        mode = GameMode(req.mode)
    except ValueError:
        mode = GameMode.RACE

    room = room_manager.create_room(
        host_id=req.host_id,
        host_name=req.host_name,
        mode=mode,
        difficulty=req.difficulty
    )
    return {
        "room_code": room.room_code,
        "mode": room.mode.value,
        "difficulty": room.difficulty,
        "initial_puzzle": room.initial_puzzle
    }


@app.get("/api/rooms/{room_code}")
async def get_room(room_code: str):
    room = room_manager.rooms.get(room_code.upper())
    if not room:
        raise HTTPException(status_code=404, detail="Salon introuvable")

    return {
        "room_code": room.room_code,
        "state": room.state.value,
        "mode": room.mode.value,
        "difficulty": room.difficulty,
        "players": [
            {
                "id": p.player_id,
                "name": p.name,
                "is_host": p.is_host,
                "score": p.score,
                "mistakes": p.mistakes,
                "progress": p.progress
            }
            for p in room.player_list
        ],
        "spectators_count": len(room.spectators)
    }


@app.websocket("/ws/{room_code}/{player_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str, player_name: str):
    code = room_code.upper()
    try:
        room, role = room_manager.join_room(code, player_id, player_name)
    except ValueError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    await ws_manager.connect(code, websocket)

    # Informer tous les membres du salon de l'arrivée du joueur
    await ws_manager.broadcast(code, {
        "event": "PLAYER_JOINED",
        "player_id": player_id,
        "player_name": player_name,
        "role": role,
        "players": [{"id": p.player_id, "name": p.name, "is_host": p.is_host} for p in room.player_list]
    })

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action = data.get("action")

            if action == "START_GAME":
                player = room.players.get(player_id)
                if player and (player.is_host or room.mode == GameMode.SOLO_AI):
                    asyncio.create_task(start_game_flow(code))

            elif action == "PLAY_MOVE":
                row = data.get("row")
                col = data.get("col")
                val = data.get("value")

                res = room_manager.play_move(code, player_id, row, col, val)
                await ws_manager.broadcast(code, {
                    "event": "MOVE_RESULT",
                    "result": res
                })

                if res.get("valid"):
                    publish_mqtt("game/led", {"state": "green", "player": player_id})
                else:
                    publish_mqtt("game/led", {"state": "red", "player": player_id})

                if res.get("game_over"):
                    publish_mqtt("game/led", {"state": "rainbow", "winner": res.get("winner_id")})

    except WebSocketDisconnect:
        ws_manager.disconnect(code, websocket)
        room_manager.leave_room(code, player_id)
        await ws_manager.broadcast(code, {
            "event": "PLAYER_LEFT",
            "player_id": player_id
        })
