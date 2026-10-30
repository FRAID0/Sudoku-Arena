"""
FastAPI Server & WebSocket Gateway for Sudoku Arena
Expose les endpoints REST et les connexions WebSockets pour les salons de jeu.
Gère le décompte synchronisé, le bot autonome KI FRAID et la télémétrie MQTT Mosquitto.
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import paho.mqtt.client as mqtt

from app.core.room_manager import RoomManager, GameMode, RoomState, ClashRule
from app.core.redis_manager import RedisManager
from app.core.metrics import (
    setup_metrics,
    ACTIVE_ROOMS,
    GAMES_STARTED_TOTAL,
    MOVES_TOTAL,
    WINS_TOTAL
)
from app.ai.bot import KIFraidBot
from app.services.llm_commentator import (
    IntroRequest,
    DebriefRequest,
    LiveCommentRequest,
    CommentatorResponse,
    commentator_service
)
from app.services.narrative_engine import narrative_engine


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

# Initialisation de l'instrumentation Prometheus (/metrics)
setup_metrics(app)

room_manager = RoomManager()
redis_manager = RedisManager()

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


class ConnectionManager:
    """Gère les connexions WebSockets actives par salon avec relais Redis Pub/Sub multi-Pods."""
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

    async def send_local(self, room_code: str, message: dict):
        """Envoie le message aux WebSockets locales connectées sur ce Pod."""
        code = room_code.upper()
        if code in self.active_connections:
            data = json.dumps(message)
            for connection in list(self.active_connections[code]):
                try:
                    await connection.send_text(data)
                except Exception:
                    pass

    async def broadcast(self, room_code: str, message: dict):
        """Diffuse le message : via Redis Pub/Sub si disponible (multi-Pods), ou en local directement."""
        code = room_code.upper()
        if redis_manager and redis_manager.is_connected:
            await redis_manager.publish_event(code, message)
        else:
            await self.send_local(code, message)


ws_manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    init_mqtt()
    connected = await redis_manager.connect()
    if connected:
        asyncio.create_task(redis_manager.subscribe_rooms(ws_manager.send_local))


@app.on_event("shutdown")
async def shutdown_event():
    await redis_manager.close()


async def check_and_broadcast_commentary(room_code: str, player_id: str, move_res: dict, lang: Optional[str] = None):
    """Analyse asynchrone non-bloquante du match pour interventions e-sport du Caster."""
    room = room_manager.rooms.get(room_code)
    if not room or move_res.get("game_over"):
        return
    room_lang = lang or getattr(room, "lang", "fr")
    req = narrative_engine.evaluate_move(room, player_id, move_res, lang=room_lang)
    if req:
        comment = await commentator_service.generate_live_comment(req)
        narrative_engine.record_comment(room_code, comment.text, req.event_type)
        await ws_manager.broadcast(room_code, {
            "event": "CASTER_COMMENT",
            "comment": comment.dict()
        })
        publish_mqtt("game/caster", {
            "text": comment.text,
            "mood": comment.mood,
            "event_type": req.event_type
        })


async def check_and_broadcast_timeout_commentary(room_code: str, timed_out_player_id: str, lang: Optional[str] = None):
    room = room_manager.rooms.get(room_code)
    if not room:
        return
    room_lang = lang or getattr(room, "lang", "fr")
    req = narrative_engine.evaluate_timeout(room, timed_out_player_id, lang=room_lang)
    if req:
        comment = await commentator_service.generate_live_comment(req)
        narrative_engine.record_comment(room_code, comment.text, req.event_type)
        await ws_manager.broadcast(room_code, {
            "event": "CASTER_COMMENT",
            "comment": comment.dict()
        })
        publish_mqtt("game/caster", {
            "text": comment.text,
            "mood": comment.mood,
            "event_type": req.event_type
        })


async def run_ai_opponent(room_code: str, difficulty: str):
    """Boucle d'actions asynchrone du bot KI FRAID dans un salon."""
    bot = KIFraidBot(difficulty)
    ai_id = "bot_ki_fraid"

    while True:
        room = room_manager.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME:
            break

        # Attendre que ce soit le tour du bot
        if room.current_turn_player_id != ai_id:
            await asyncio.sleep(0.5)
            continue

        bot_player = room.players.get(ai_id)
        if not bot_player or bot_player.finished:
            break

        target_grid = room.shared_grid if room.mode in (GameMode.CLASH, GameMode.SOLO_AI) else bot_player.grid
        move = bot.choose_move(target_grid, room.solution)
        if not move:
            break

        # Simuler le délai de réflexion dans la limite du tour
        simulated_delay = min(move["delay"], max(1.0, room.turn_timeout - 1.5))
        await asyncio.sleep(simulated_delay)

        # Vérifier si c'est toujours le tour du bot
        room = room_manager.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME or room.current_turn_player_id != ai_id:
            continue

        res = room_manager.play_move(room_code, ai_id, move["row"], move["col"], move["value"])
        await ws_manager.broadcast(room_code, {
            "event": "MOVE_RESULT",
            "result": res
        })

        asyncio.create_task(check_and_broadcast_commentary(room_code, ai_id, res))

        if res.get("valid"):
            publish_mqtt("game/led", {"state": "green", "source": "bot"})
        else:
            publish_mqtt("game/led", {"state": "red", "source": "bot"})

        if res.get("game_over"):
            publish_mqtt("game/led", {"state": "rainbow", "winner": res.get("winner_id")})
            break


async def monitor_turn_timer(room_code: str):
    """Surveille le compte à rebours autoritaire de chaque tour en mode Clash."""
    while True:
        await asyncio.sleep(0.4)
        room = room_manager.rooms.get(room_code)
        if not room or room.state != RoomState.IN_GAME:
            break
        if room.mode not in (GameMode.CLASH, GameMode.SOLO_AI):
            break

        if room.turn_start_time:
            elapsed = time.time() - room.turn_start_time
            if elapsed >= room.turn_timeout:
                timeout_res = room_manager.timeout_turn(room_code)
                if timeout_res:
                    asyncio.create_task(check_and_broadcast_timeout_commentary(room_code, timeout_res.get("timed_out_player_id")))
                    await ws_manager.broadcast(room_code, {
                        "event": "TURN_TIMEOUT",
                        "result": timeout_res
                    })
                    publish_mqtt("game/led", {
                        "state": "red",
                        "reason": "timeout",
                        "player": timeout_res.get("timed_out_player_id")
                    })


async def start_game_flow(room_code: str):
    """Décompte synchronisé 3.. 2.. 1.. GO ! puis lancement."""
    for count in [3, 2, 1]:
        await ws_manager.broadcast(room_code, {
            "event": "COUNTDOWN",
            "count": count
        })
        await asyncio.sleep(1)

    room = room_manager.start_game(room_code)
    narrative_engine.reset_room(room_code)
    GAMES_STARTED_TOTAL.labels(mode=room.mode.value, difficulty=room.difficulty).inc()

    if redis_manager and redis_manager.is_connected:
        await redis_manager.save_room(room)

    await ws_manager.broadcast(room_code, {
        "event": "GAME_STARTED",
        "start_time": room.start_time,
        "turn_timeout": room.turn_timeout,
        "current_turn": room.current_turn_player_id,
        "initial_puzzle": room.initial_puzzle,
        "shared_grid": room.shared_grid
    })
    publish_mqtt("game/led", {"state": "blue"})

    if room.mode in (GameMode.CLASH, GameMode.SOLO_AI):
        asyncio.create_task(monitor_turn_timer(room_code))

    if room.mode == GameMode.SOLO_AI:
        asyncio.create_task(run_ai_opponent(room_code, room.difficulty))


class CreateRoomRequest(BaseModel):
    host_id: str
    host_name: str
    mode: str = "clash"
    difficulty: str = "medium"
    validation_mode: str = "simple"  # "simple" (règles locales) ou "strict" (solution finale unique)
    clash_rule: str = "combo_capped"  # "strict", "combo_capped" (défaut), ou "unlimited"
    lang: str = "fr"  # "fr", "en", ou "de"
    is_public: bool = True
    auto_start: bool = False


class MatchmakingRequest(BaseModel):
    player_id: str
    player_name: str
    mode: str = "clash"
    difficulty: str = "medium"
    validation_mode: str = "simple"
    clash_rule: str = "combo_capped"
    lang: str = "fr"


class FallbackAiRequest(BaseModel):
    room_code: str


@app.get("/health")
async def health_check():
    """Sonde de santé pour Kubernetes (Liveness & Readiness probes)."""
    return {
        "status": "healthy",
        "service": "Sudoku Arena Backend",
        "redis_connected": redis_manager.is_connected if redis_manager else False,
        "active_rooms": len(room_manager.rooms)
    }


@app.get("/api/commentator/health")
async def commentator_health():
    """Vérifie l'état du commentateur IA KI FRAID (Gemini + Fallback)."""
    return {
        "status": "ready",
        "gemini_available": commentator_service.is_gemini_available(),
        "fallback_ready": True,
        "supported_languages": ["fr", "en", "de"]
    }


@app.post("/api/commentator/intro", response_model=CommentatorResponse)
async def commentator_intro(req: IntroRequest):
    """Génère l'annonce d'avant-match avec pseudos réels, mode et règles."""
    return await commentator_service.generate_intro(req)


@app.post("/api/commentator/debrief", response_model=CommentatorResponse)
async def commentator_debrief(req: DebriefRequest):
    """Génère le débriefing d'après-match e-sport basé sur les statistiques du serveur."""
    return await commentator_service.generate_debrief(req)


@app.post("/api/commentator/live", response_model=CommentatorResponse)
async def commentator_live(req: LiveCommentRequest):
    """Génère une intervention de commentateur e-sport à chaud selon un événement dramatique."""
    return await commentator_service.generate_live_comment(req)


class TTSRequest(BaseModel):
    text: str
    lang: str = "fr"
    rate: float = 1.06
    voice_id: Optional[str] = None


@app.post("/api/commentator/tts")
async def commentator_tts(req: TTSRequest):
    """Synthétise ou extrait du cache Edge-TTS un flux audio MP3 studio à la demande."""
    from app.services.tts_service import tts_service
    audio_url = await tts_service.get_or_synthesize(
        text=req.text,
        lang=req.lang,
        rate=req.rate,
        voice_id=req.voice_id
    )
    if not audio_url:
        raise HTTPException(status_code=500, detail="TTS synthesis unavailable")
    return {"audio_url": audio_url, "text": req.text}


@app.get("/api/commentator/audio/{filename}")
async def get_commentator_audio(filename: str):
    """Sert les fichiers audio MP3 générés et mis en cache par Edge-TTS."""
    from fastapi.responses import FileResponse
    from app.services.tts_service import CACHE_DIR
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(CACHE_DIR, safe_filename)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return FileResponse(filepath, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Audio file not found")


@app.post("/api/rooms")
async def create_room(req: CreateRoomRequest):
    try:
        mode = GameMode(req.mode)
    except ValueError:
        mode = GameMode.RACE

    try:
        clash_rule = ClashRule(req.clash_rule.lower())
    except (ValueError, AttributeError):
        clash_rule = ClashRule.COMBO_CAPPED

    room = room_manager.create_room(
        host_id=req.host_id,
        host_name=req.host_name,
        mode=mode,
        difficulty=req.difficulty,
        validation_mode=req.validation_mode,
        clash_rule=clash_rule,
        lang=req.lang,
        is_public=req.is_public,
        auto_start=req.auto_start
    )
    ACTIVE_ROOMS.set(len(room_manager.rooms))

    if redis_manager and redis_manager.is_connected:
        await redis_manager.save_room(room)

    return {
        "room_code": room.room_code,
        "mode": room.mode.value,
        "difficulty": room.difficulty,
        "validation_mode": room.validation_mode,
        "clash_rule": room.clash_rule.value,
        "lang": room.lang,
        "is_public": room.is_public,
        "auto_start": room.auto_start,
        "initial_puzzle": room.initial_puzzle
    }


@app.post("/api/matchmaking/find")
async def find_or_create_match(req: MatchmakingRequest):
    """Trouve un rival dans un salon public ouvert, ou crée un salon en attente avec auto-lancement."""
    try:
        mode = GameMode(req.mode)
    except ValueError:
        mode = GameMode.CLASH

    try:
        clash_rule = ClashRule(req.clash_rule.lower())
    except (ValueError, AttributeError):
        clash_rule = ClashRule.COMBO_CAPPED

    # 1. Chercher un salon public en attente
    existing_room = room_manager.find_open_room(mode=mode, player_id=req.player_id, difficulty=req.difficulty)
    if existing_room:
        return {
            "status": "matched",
            "room_code": existing_room.room_code,
            "mode": existing_room.mode.value,
            "difficulty": existing_room.difficulty,
            "validation_mode": existing_room.validation_mode,
            "clash_rule": existing_room.clash_rule.value,
            "lang": existing_room.lang,
            "is_host": False,
            "auto_start": existing_room.auto_start
        }

    # 2. Aucun salon : créer un nouveau salon public avec auto-start
    new_room = room_manager.create_room(
        host_id=req.player_id,
        host_name=req.player_name,
        mode=mode,
        difficulty=req.difficulty,
        validation_mode=req.validation_mode,
        clash_rule=clash_rule,
        lang=req.lang,
        is_public=True,
        auto_start=True
    )
    ACTIVE_ROOMS.set(len(room_manager.rooms))
    if redis_manager and redis_manager.is_connected:
        await redis_manager.save_room(new_room)

    return {
        "status": "waiting",
        "room_code": new_room.room_code,
        "mode": new_room.mode.value,
        "difficulty": new_room.difficulty,
        "validation_mode": new_room.validation_mode,
        "clash_rule": new_room.clash_rule.value,
        "lang": new_room.lang,
        "is_host": True,
        "auto_start": True
    }


@app.post("/api/matchmaking/fallback-ai")
async def fallback_ai(req: FallbackAiRequest):
    """Convertit immédiatement un salon d'attente en Solo AI et lance le compte à rebours."""
    code = req.room_code.upper().strip()
    try:
        room = room_manager.convert_to_solo_ai(code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if redis_manager and redis_manager.is_connected:
        await redis_manager.save_room(room)

    await ws_manager.broadcast(code, {
        "event": "AI_FALLBACK_TRIGGERED",
        "room_code": code,
        "mode": room.mode.value,
        "players": [{"id": p.player_id, "name": p.name, "is_host": p.is_host} for p in room.player_list]
    })
    asyncio.create_task(start_game_flow(code))

    return {
        "status": "ai_started",
        "room_code": code,
        "mode": room.mode.value
    }


@app.get("/api/matchmaking/stats")
async def matchmaking_stats():
    """Fournit les statistiques de l'arène en temps réel."""
    return room_manager.get_matchmaking_stats()


@app.get("/api/leaderboard")
async def get_leaderboard():
    """Retourne le Top Classement E-Sport officiel de Sudoku Arena."""
    return [
        {"rank": 1, "name": "KI FRAID (Grand Maître) 🤖", "mmr": 2840, "league": "Grand Maître", "badge": "👑", "winrate": "98%"},
        {"rank": 2, "name": "NeoSolver_99", "mmr": 2350, "league": "Diamant I", "badge": "💠", "winrate": "84%"},
        {"rank": 3, "name": "SpeedDigit", "mmr": 2180, "league": "Diamant II", "badge": "💠", "winrate": "79%"},
        {"rank": 4, "name": "CyberNinja", "mmr": 1920, "league": "Platine I", "badge": "💎", "winrate": "72%"},
        {"rank": 5, "name": "MatrixClasher", "mmr": 1640, "league": "Platine III", "badge": "💎", "winrate": "65%"}
    ]



@app.get("/api/rooms/{room_code}")
async def get_room(room_code: str):
    code = room_code.upper()
    room = None
    if redis_manager and redis_manager.is_connected:
        room = await redis_manager.get_room(code)
    if not room:
        room = room_manager.rooms.get(code)
    if not room:
        raise HTTPException(status_code=404, detail="Salon introuvable")

    return {
        "room_code": room.room_code,
        "state": room.state.value,
        "mode": room.mode.value,
        "difficulty": room.difficulty,
        "validation_mode": room.validation_mode,
        "clash_rule": room.clash_rule.value,
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
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str, player_name: str, lang: Optional[str] = None):
    code = room_code.upper()
    try:
        room, role = room_manager.join_room(code, player_id, player_name)
        if lang and lang in ("fr", "en", "de"):
            room.lang = lang
    except ValueError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    if redis_manager and redis_manager.is_connected:
        await redis_manager.save_room(room)

    await ws_manager.connect(code, websocket)

    # Informer tous les membres du salon de l'arrivée du joueur
    await ws_manager.broadcast(code, {
        "event": "PLAYER_JOINED",
        "player_id": player_id,
        "player_name": player_name,
        "role": role,
        "players": [{"id": p.player_id, "name": p.name, "is_host": p.is_host} for p in room.player_list],
        "spectators_count": len(room.spectators)
    })

    # Lancement automatique immédiat si salon de matchmaking 1-clic et 2 joueurs réunis
    if getattr(room, "auto_start", False) and len(room.players) >= 2 and room.state == RoomState.WAITING:
        asyncio.create_task(start_game_flow(code))

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
                if not res.get("rejected"):
                    result_label = "valid" if res.get("valid") else "invalid"
                    MOVES_TOTAL.labels(result=result_label, mode=room.mode.value).inc()

                if redis_manager and redis_manager.is_connected and code in room_manager.rooms:
                    await redis_manager.save_room(room_manager.rooms[code])

                await ws_manager.broadcast(code, {
                    "event": "MOVE_RESULT",
                    "result": res
                })

                asyncio.create_task(check_and_broadcast_commentary(code, player_id, res))

                if res.get("valid"):
                    publish_mqtt("game/led", {"state": "green", "player": player_id})
                else:
                    publish_mqtt("game/led", {"state": "red", "player": player_id})

                if res.get("game_over"):
                    winner_type = "bot" if res.get("winner_id") == "bot_ki_fraid" else "player"
                    WINS_TOTAL.labels(winner_type=winner_type, mode=room.mode.value).inc()
                    publish_mqtt("game/led", {"state": "rainbow", "winner": res.get("winner_id")})

            elif action == "TIMEOUT_TURN":
                room = room_manager.rooms.get(code)
                if room and room.mode in (GameMode.CLASH, GameMode.SOLO_AI) and room.current_turn_player_id == player_id:
                    timeout_res = room_manager.timeout_turn(code)
                    if timeout_res:
                        MOVES_TOTAL.labels(result="timeout", mode=room.mode.value).inc()

                        if redis_manager and redis_manager.is_connected and code in room_manager.rooms:
                            await redis_manager.save_room(room_manager.rooms[code])

                        await ws_manager.broadcast(code, {
                            "event": "TURN_TIMEOUT",
                            "result": timeout_res
                        })
                        asyncio.create_task(check_and_broadcast_timeout_commentary(code, timeout_res.get("timed_out_player_id")))
                        publish_mqtt("game/led", {
                            "state": "red",
                            "reason": "timeout",
                            "player": timeout_res.get("timed_out_player_id")
                        })

            elif action == "SEND_EMOTE":
                emote_key = data.get("emote_key", "fire")
                await ws_manager.broadcast(code, {
                    "event": "EMOTE_BURST",
                    "player_id": player_id,
                    "player_name": player_name,
                    "role": role,
                    "emote_key": emote_key
                })
                publish_mqtt("game/emote", {
                    "room": code,
                    "player": player_name,
                    "emote": emote_key
                })

            elif action == "HYPE_BURST":
                await ws_manager.broadcast(code, {
                    "event": "HYPE_UPDATE",
                    "player_id": player_id,
                    "player_name": player_name
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(code, websocket)
        res = room_manager.leave_room(code, player_id)
        ACTIVE_ROOMS.set(len(room_manager.rooms))

        if redis_manager and redis_manager.is_connected:
            if res and res.get("room_deleted"):
                await redis_manager.delete_room(code)
            elif code in room_manager.rooms:
                await redis_manager.save_room(room_manager.rooms[code])

        if res and res.get("forfeit"):
            await ws_manager.broadcast(code, {
                "event": "GAME_OVER_FORFEIT",
                "winner_id": res.get("winner_id"),
                "left_player_id": res.get("left_player_id"),
                "left_player_name": res.get("left_player_name")
            })
            publish_mqtt("game/led", {"state": "rainbow", "winner": res.get("winner_id")})
        elif res and res.get("player_left"):
            await ws_manager.broadcast(code, {
                "event": "PLAYER_LEFT",
                "player_id": player_id,
                "players": [{"id": p.player_id, "name": p.name, "is_host": p.is_host} for p in res.get("remaining_players", [])]
            })
        else:
            await ws_manager.broadcast(code, {
                "event": "PLAYER_LEFT",
                "player_id": player_id
            })
