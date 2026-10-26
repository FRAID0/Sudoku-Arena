"""
Redis Manager for Sudoku Arena
Gère l'état distribué des salons de jeu (State) et la diffusion des événements (Pub/Sub)
pour permettre le scaling horizontal sans état (Stateless) sur Kubernetes.
Fournit un mécanisme de fallback transparent en mémoire si Redis n'est pas disponible.
"""

import json
import logging
import os
from typing import Optional, Callable
import redis.asyncio as aioredis
from app.core.room_manager import Room

logger = logging.getLogger("sudoku.redis")


class RedisManager:
    ROOM_KEY_PREFIX = "sudoku:room:"
    CHANNEL_PREFIX = "sudoku:channel:"
    DEFAULT_TTL = 7200  # 2 heures de rétention pour les parties en mémoire

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", "6379"))
        self.client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.is_connected = False
        self._listener_task = None

    async def connect(self) -> bool:
        """Tente d'établir la connexion avec le serveur Redis."""
        try:
            self.client = aioredis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            await self.client.ping()
            self.is_connected = True
            logger.info(f"✅ Redis connecté avec succès sur {self.host}:{self.port}")
            return True
        except Exception as e:
            self.is_connected = False
            self.client = None
            logger.warning(f"⚠️ Redis non disponible ({self.host}:{self.port}) - Mode Fallback mémoire actif : {e}")
            return False

    async def close(self):
        """Ferme proprement la connexion Redis et le Pub/Sub."""
        if self._listener_task:
            self._listener_task.cancel()
        if self.pubsub:
            if hasattr(self.pubsub, "aclose"):
                await self.pubsub.aclose()
            else:
                await self.pubsub.close()
        if self.client:
            if hasattr(self.client, "aclose"):
                await self.client.aclose()
            else:
                await self.client.close()
        self.is_connected = False

    def _room_key(self, room_code: str) -> str:
        return f"{self.ROOM_KEY_PREFIX}{room_code.upper()}"

    def _channel_name(self, room_code: str) -> str:
        return f"{self.CHANNEL_PREFIX}{room_code.upper()}"

    async def save_room(self, room: Room, ttl: Optional[int] = None) -> bool:
        """Sauvegarde l'état d'un salon dans Redis sous format JSON avec TTL."""
        if not self.is_connected or not self.client:
            return False

        try:
            key = self._room_key(room.room_code)
            data = json.dumps(room.to_dict())
            await self.client.set(key, data, ex=ttl or self.DEFAULT_TTL)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du salon {room.room_code} dans Redis : {e}")
            return False

    async def get_room(self, room_code: str) -> Optional[Room]:
        """Récupère et désérialise un salon depuis Redis."""
        if not self.is_connected or not self.client:
            return None

        try:
            key = self._room_key(room_code)
            raw_data = await self.client.get(key)
            if not raw_data:
                return None
            data = json.loads(raw_data)
            return Room.from_dict(data)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du salon {room_code} depuis Redis : {e}")
            return None

    async def delete_room(self, room_code: str) -> bool:
        """Supprime un salon de Redis."""
        if not self.is_connected or not self.client:
            return False

        try:
            key = self._room_key(room_code)
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du salon {room_code} de Redis : {e}")
            return False

    async def publish_event(self, room_code: str, event_data: dict) -> bool:
        """Publie un événement de jeu sur le canal Pub/Sub du salon."""
        if not self.is_connected or not self.client:
            return False

        try:
            channel = self._channel_name(room_code)
            message = json.dumps(event_data)
            await self.client.publish(channel, message)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la publication Pub/Sub pour {room_code} : {e}")
            return False

    async def subscribe_rooms(self, callback: Callable[[str, dict], None]):
        """Écoute tous les canaux de salons (sudoku:channel:*) et relaie les événements au callback."""
        if not self.is_connected or not self.client:
            return

        try:
            self.pubsub = self.client.pubsub()
            await self.pubsub.psubscribe(f"{self.CHANNEL_PREFIX}*")
            logger.info("📡 Abonnement Pub/Sub Redis activé pour les salons Sudoku Arena")

            async for message in self.pubsub.listen():
                if message and message.get("type") == "pmessage":
                    channel = message.get("channel", "")
                    data_str = message.get("data", "")
                    room_code = channel.replace(self.CHANNEL_PREFIX, "")
                    try:
                        payload = json.loads(data_str)
                        await callback(room_code, payload)
                    except Exception as err:
                        logger.error(f"Erreur de décodage du message Pub/Sub : {err}")
        except Exception as e:
            logger.warning(f"Arrêt de l'écoute Pub/Sub Redis : {e}")
