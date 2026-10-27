#!/usr/bin/env python3
"""
Génération des clips audio Edge-TTS complémentaires pour les événements en jeu.
Génère pour toutes les voix répertoriées (FR, EN, DE) :
- MOVE_VALID
- TIMEOUT
- DEFEAT
- GAME_START
"""

import os
import asyncio
import edge_tts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR = os.path.join(BASE_DIR, "frontend", "assets", "audio", "benchmark")

EXTRA_PHRASES = {
    "fr": {
        "MOVE_VALID": "Bien joué ! Chiffre validé avec précision !",
        "TIMEOUT": "Temps écoulé ! Hésitation fatale, la main passe !",
        "DEFEAT": "Fin du match ! Belle résistance dans l'arène, relancez un duel !",
        "GAME_START": "3.. 2.. 1.. C'est parti ! Que le spectacle commence !"
    },
    "en": {
        "MOVE_VALID": "Well played! Number locked in with precision!",
        "TIMEOUT": "Time is up! Fatal hesitation, turn lost!",
        "DEFEAT": "Match over! Great effort in the arena, challenge for a rematch!",
        "GAME_START": "3.. 2.. 1.. Go! Let the battle begin!"
    },
    "de": {
        "MOVE_VALID": "Gut gespielt! Zahl mit Präzision gesetzt!",
        "TIMEOUT": "Zeit abgelaufen! Zu lange gezögert, der Zug ist verloren!",
        "DEFEAT": "Spiel vorbei! Stark gekämpft, fordere eine Revanche!",
        "GAME_START": "3.. 2.. 1.. Los geht's! Möge der Beste gewinnen!"
    }
}

VOICES = {
    "fr": [
        "fr-FR-HenriNeural",
        "fr-FR-RemyMultilingualNeural",
        "fr-FR-DeniseNeural"
    ],
    "en": [
        "en-US-GuyNeural",
        "en-US-AriaNeural",
        "en-GB-RyanNeural"
    ],
    "de": [
        "de-DE-ConradNeural",
        "de-DE-KatjaNeural",
        "de-DE-FlorianMultilingualNeural"
    ]
}

async def generate():
    for lang, voice_ids in VOICES.items():
        for voice_id in voice_ids:
            target_dir = os.path.join(BENCH_DIR, lang, voice_id)
            os.makedirs(target_dir, exist_ok=True)
            for key, text in EXTRA_PHRASES[lang].items():
                out_file = os.path.join(target_dir, f"{key}.mp3")
                if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
                    print(f"Skipping existing: {lang}/{voice_id}/{key}.mp3")
                    continue
                try:
                    communicate = edge_tts.Communicate(text, voice_id, rate="+8%")
                    await communicate.save(out_file)
                    print(f"Generated: {lang}/{voice_id}/{key}.mp3 ({os.path.getsize(out_file)} bytes)")
                except Exception as e:
                    print(f"Failed {lang}/{voice_id}/{key}: {e}")

if __name__ == "__main__":
    asyncio.run(generate())
