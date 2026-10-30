import os
import asyncio
import edge_tts

BASE_DIR = r"d:\Sudoku-Arena\frontend\assets\audio\benchmark"

VOICES = {
    "fr": [
        ("fr-FR-HenriNeural", "Duel contre l'IA Fraid ! Montre à l'algorithme ce que l'esprit humain a dans le ventre !"),
        ("fr-FR-RemyMultilingualNeural", "Duel contre l'IA Fraid ! Montre à l'algorithme ce que l'esprit humain a dans le ventre !"),
        ("fr-FR-DeniseNeural", "Duel contre l'IA Fraid ! Montre à l'algorithme ce que l'esprit humain a dans le ventre !")
    ],
    "en": [
        ("en-US-GuyNeural", "Duel against AI Fraid! Show the algorithm what human intelligence can do!"),
        ("en-US-AriaNeural", "Duel against AI Fraid! Show the algorithm what human intelligence can do!"),
        ("en-GB-RyanNeural", "Duel against AI Fraid! Show the algorithm what human intelligence can do!")
    ],
    "de": [
        ("de-DE-ConradNeural", "Duell gegen KI Fraid! Zeige dem Algorithmus, was der menschliche Verstand leisten kann!"),
        ("de-DE-KatjaNeural", "Duell gegen KI Fraid! Zeige dem Algorithmus, was der menschliche Verstand leisten kann!"),
        ("de-DE-FlorianMultilingualNeural", "Duell gegen KI Fraid! Zeige dem Algorithmus, was der menschliche Verstand leisten kann!")
    ]
}

async def gen():
    for lang, items in VOICES.items():
        for voice_id, text in items:
            out_path = os.path.join(BASE_DIR, lang, voice_id, "VS_BOT.mp3")
            print(f"Generating {out_path} with {voice_id}...")
            comm = edge_tts.Communicate(text, voice_id, rate="+4%")
            await comm.save(out_path)
            print(f"Saved {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    asyncio.run(gen())
