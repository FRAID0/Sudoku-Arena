"""
Service de Synthèse Vocale Edge-TTS à la Demande — KI FRAID Caster 🎙️
Génère et met en cache côté serveur les voix HD Studio Edge-TTS
pour les répliques dynamiques de Gemini et du fallback procédural.
Garantit la parfaite cohérence de timbre avec le catalogue audio existant.
"""

import os
import re
import hashlib
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("sudoku_arena.tts_service")


def _resolve_cache_dir() -> str:
    """Résout de manière robuste et sécurisée un dossier de cache accessible en écriture."""
    env_dir = os.environ.get("TTS_CACHE_DIR")
    if env_dir:
        try:
            os.makedirs(env_dir, exist_ok=True)
            return env_dir
        except Exception:
            pass

    # 1. Tester l'environnement de développement local (Sudoku-Arena/frontend/assets/audio/cache)
    curr = os.path.abspath(__file__)
    for _ in range(5):
        curr = os.path.dirname(curr)
        candidate = os.path.join(curr, "frontend", "assets", "audio", "cache")
        if os.path.exists(os.path.join(curr, "frontend", "assets")):
            try:
                os.makedirs(candidate, exist_ok=True)
                test_path = os.path.join(candidate, ".write_test")
                with open(test_path, "w") as f:
                    f.write("ok")
                os.remove(test_path)
                return candidate
            except Exception:
                pass

    # 2. Tester le dossier /app/audio_cache (environnement Docker standard)
    app_cache = os.path.join("/app", "audio_cache")
    try:
        os.makedirs(app_cache, exist_ok=True)
        return app_cache
    except Exception:
        pass

    # 3. Repli garanti sur le dossier temporaire du système d'exploitation
    import tempfile
    tmp_cache = os.path.join(tempfile.gettempdir(), "sudoku_arena_audio_cache")
    try:
        os.makedirs(tmp_cache, exist_ok=True)
        return tmp_cache
    except Exception:
        return tempfile.gettempdir()


CACHE_DIR = _resolve_cache_dir()

DEFAULT_VOICES = {
    "fr": "fr-FR-HenriNeural",
    "en": "en-US-GuyNeural",
    "de": "de-DE-FlorianMultilingualNeural"
}


class TTSService:
    def __init__(self, cache_dir: str = CACHE_DIR, timeout_seconds: float = 2.5):
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Impossible de créer le dossier cache {self.cache_dir}: {e}")

    def _normalize_speech_text(self, text: str, lang: str = "fr") -> str:
        """
        Normalise le texte pour la synthèse vocale.
        Évite que 'FRAID' soit épelé lettre par lettre (F-R-A-I-D) comme un acronyme.
        Prononce 'Fraid' naturellement et gère 'l'IA Fraid' / 'AI Fraid' / 'KI Fraid'.
        """
        clean = re.sub(r"[\*\_\#\`\"]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()

        if lang == "fr":
            clean = re.sub(r"\bKI\s+FRAID\b", "l'IA Fraid", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bBOT\s+IA\s+FRAID\b", "le Bot IA Fraid", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bIA\s+FRAID\b", "l'IA Fraid", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bFRAID\b", "Fraid", clean)
        elif lang == "en":
            clean = re.sub(r"\bKI\s+FRAID\b", "AI Fraid", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\bFRAID\b", "Fraid", clean)
        else:  # de
            clean = re.sub(r"\bFRAID\b", "Fraid", clean)

        def _uncap(match):
            return match.group(0).capitalize()

        clean = re.sub(r"\b[A-Z]{4,}\b", _uncap, clean)
        return clean

    def _compute_hash(self, text: str, voice: str, rate_pct: int) -> str:
        key = f"{voice}:{rate_pct}:{text.strip().lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    async def get_or_synthesize(
        self,
        text: str,
        lang: str = "fr",
        rate: float = 1.06,
        voice_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Synthétise ou extrait du cache un fichier audio MP3 Edge-TTS.
        Retourne l'URL relative /api/commentator/audio/{filename} ou None en cas d'indisponibilité.
        """
        speech_text = self._normalize_speech_text(text, lang=lang)
        if not speech_text:
            return None

        voice = voice_id or DEFAULT_VOICES.get(lang, DEFAULT_VOICES["fr"])
        
        # Formatage du débit pour edge-tts (ex: 1.06 -> "+6%")
        rate_diff = int(round((rate - 1.0) * 100))
        rate_str = f"+{rate_diff}%" if rate_diff >= 0 else f"{rate_diff}%"

        file_hash = self._compute_hash(speech_text, voice, rate_diff)
        filename = f"tts_{lang}_{file_hash}.mp3"
        filepath = os.path.join(self.cache_dir, filename)
        web_url = f"/api/commentator/audio/{filename}"

        # 1. Vérification du cache disque existant (0 ms)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
            return web_url

        # 2. Synthèse asynchrone avec Edge-TTS et timeout strict
        try:
            import edge_tts
            communicate = edge_tts.Communicate(speech_text, voice, rate=rate_str)
            await asyncio.wait_for(communicate.save(filepath), timeout=self.timeout_seconds)
            
            if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
                logger.info(f"Audio TTS généré et mis en cache : {filename} ({os.path.getsize(filepath)} octets)")
                return web_url
        except asyncio.TimeoutError:
            logger.warning(f"Timeout lors de la synthèse Edge-TTS pour: '{speech_text[:30]}...'")
        except Exception as e:
            logger.warning(f"Erreur synthèse Edge-TTS: {e}")

        return None


# Singleton
tts_service = TTSService()
