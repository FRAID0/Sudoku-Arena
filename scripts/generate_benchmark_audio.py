#!/usr/bin/env python3
"""
Génération des échantillons audio pour le Banc d'Essai Audio (audio-benchmark.html)
de Sudoku Arena.
Génère :
1. Voix Edge-TTS multilingues (FR, EN, DE) pour 6 catégories clés.
2. SFX doux en format WAV (synthèse harmonique Web-ready feutrée sans bips agressifs).
"""

import os
import math
import struct
import wave
import asyncio
import edge_tts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "frontend", "assets", "audio")
BENCH_DIR = os.path.join(AUDIO_DIR, "benchmark")
SFX_DIR = os.path.join(AUDIO_DIR, "sfx")

PHRASES = {
    "fr": {
        "WELCOME": "Bienvenue dans Sudoku Arena ! Préparez vos neurones, aujourd'hui chaque coup compte !",
        "MODE_CLASH": "Mode Clash sélectionné ! Ici, c'est du tour par tour stratégique : vous partagez la même grille, et chaque chiffre validé rapporte des points avec bonus de combo !",
        "MODE_RACE": "Mode Course sélectionné ! Deux joueurs, une grille identique en miroir. Pas de tour, c'est un pur speedrun : le premier qui boucle sa grille gagne le duel !",
        "COMBO_X2": "Combo x2 ! Deux coups d'affilée, quelle vista ! Le public est en ébullition !",
        "ERROR": "Aïe, chiffre refusé ! Cette erreur coûte cher, la main passe immédiatement à l'adversaire !",
        "VICTORY": "Victoire éclatante ! Quel duel d'anthologie, l'arène a trouvé son véritable champion !"
    },
    "en": {
        "WELCOME": "Welcome to Sudoku Arena! Sharpen your mind, every move matters today!",
        "MODE_CLASH": "Clash Mode selected! Turn-based strategy: you share the same grid, and every valid number earns points with combo multipliers!",
        "MODE_RACE": "Race Mode selected! Two players, identical mirror grid. No turns, pure speedrun: the first to finish wins the duel!",
        "COMBO_X2": "Combo x2! Two consecutive hits, pure brilliance! The crowd is going wild!",
        "ERROR": "Ouch, invalid number! That mistake hurts, the turn switches immediately to your opponent!",
        "VICTORY": "Spectacular victory! What an incredible match, the Arena has found its true champion!"
    },
    "de": {
        "WELCOME": "Willkommen in der Sudoku Arena! Schärfe deinen Verstand, heute zählt jeder Zug!",
        "MODE_CLASH": "Clash-Modus ausgewählt! Rundenbasierte Strategie: Ihr teilt euch dasselbe Gitter, und jede richtige Zahl bringt Punkte mit Combo-Bonus!",
        "MODE_RACE": "Renn-Modus ausgewählt! Zwei Spieler, identisches Spiegel-Gitter. Reine Geschwindigkeit: Wer das Gitter zuerst löst, gewinnt!",
        "COMBO_X2": "Combo x2! Zwei Treffer in Folge, meisterhaft! Das Publikum tobt!",
        "ERROR": "Autsch, ungültiger Zug! Ein teurer Fehler, die Runde wechselt sofort zum Gegner!",
        "VICTORY": "Glanzvoller Sieg! Was für ein legendäres Duell, die Arena hat ihren wahren Champion gefunden!"
    }
}

VOICES = {
    "fr": [
        ("fr-FR-HenriNeural", "Henri (Masculin - Sportif/Énergique)"),
        ("fr-FR-RemyMultilingualNeural", "Remy (Masculin - Chaleureux/Multilingue)"),
        ("fr-FR-DeniseNeural", "Denise (Féminin - Radio/Posée)")
    ],
    "en": [
        ("en-US-GuyNeural", "Guy (US - Masculin/Dynamique)"),
        ("en-US-AriaNeural", "Aria (US - Féminin/Clair)"),
        ("en-GB-RyanNeural", "Ryan (UK - Masculin/Britannique)")
    ],
    "de": [
        ("de-DE-ConradNeural", "Conrad (Masculin - Posé/Précis)"),
        ("de-DE-KatjaNeural", "Katja (Féminin - Énergique)"),
        ("de-DE-FlorianMultilingualNeural", "Florian (Masculin - Moderne)")
    ]
}

async def generate_voice_files():
    print("=== 1. Génération des voix Edge-TTS ===")
    for lang, voice_list in VOICES.items():
        for voice_id, label in voice_list:
            voice_dir = os.path.join(BENCH_DIR, lang, voice_id)
            os.makedirs(voice_dir, exist_ok=True)
            for category, text in PHRASES[lang].items():
                out_path = os.path.join(voice_dir, f"{category}.mp3")
                if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                    continue
                print(f"[{lang}] {voice_id} -> {category} ...")
                try:
                    communicate = edge_tts.Communicate(text, voice_id, rate="+4%")
                    await communicate.save(out_path)
                except Exception as e:
                    print(f"Erreur sur {voice_id} ({category}): {e}")

def create_sine_tone(frequency, duration, sample_rate=44100, volume=0.3, attack=0.01, decay=0.1):
    num_samples = int(sample_rate * duration)
    samples = []
    for i in range(num_samples):
        t = float(i) / sample_rate
        # Enveloppe ADSR simple
        if t < attack:
            env = t / attack
        else:
            env = max(0.0, 1.0 - (t - attack) / (duration - attack))
        
        sample = volume * env * math.sin(2.0 * math.pi * frequency * t)
        samples.append(sample)
    return samples

def save_wav(filepath, samples, sample_rate=44100):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        packed = b''.join(struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32767)) for s in samples)
        wf.writeframes(packed)

def generate_sfx_files():
    print("=== 2. Génération des Effets Sonores (SFX Doux) ===")
    sr = 44100

    # 1. Clic feutré (cellule sélectionnée) - court tap organique 1200Hz -> 400Hz
    click_samples = []
    dur = 0.04
    for i in range(int(sr * dur)):
        t = i / sr
        freq = 1200 - (800 * (t / dur))
        env = math.exp(-t * 80)
        click_samples.append(0.25 * env * math.sin(2 * math.pi * freq * t))
    save_wav(os.path.join(SFX_DIR, "click_soft.wav"), click_samples, sr)

    # 2. Validation harmonique (accord montant C5 -> E5 -> G5, doux style marimba/bell)
    valid_samples = [0.0] * int(sr * 0.35)
    notes = [(523.25, 0.0, 0.28), (659.25, 0.05, 0.28), (783.99, 0.10, 0.25)]
    for freq, delay, notelen in notes:
        start_idx = int(delay * sr)
        for i in range(int(notelen * sr)):
            t = i / sr
            env = math.exp(-t * 9)
            s = 0.18 * env * (math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t))
            idx = start_idx + i
            if idx < len(valid_samples):
                valid_samples[idx] += s
    save_wav(os.path.join(SFX_DIR, "valid_chord.wav"), valid_samples, sr)

    # 3. Combo x2 (Whoosh montant + accord puissant et brillant)
    combo_samples = [0.0] * int(sr * 0.5)
    for i in range(int(sr * 0.5)):
        t = i / sr
        # Sweep basse 180 -> 440
        sweep_freq = 180 + (400 * (t / 0.5))
        sweep = 0.2 * (1.0 - t / 0.5) * math.sin(2 * math.pi * sweep_freq * t)
        # Accord brillant à 0.1s
        if t > 0.08:
            tb = t - 0.08
            bell = 0.22 * math.exp(-tb * 7) * (
                math.sin(2 * math.pi * 587.33 * tb) + # D5
                math.sin(2 * math.pi * 880.00 * tb) + # A5
                math.sin(2 * math.pi * 1174.66 * tb)  # D6
            )
        else:
            bell = 0.0
        combo_samples[i] = sweep + bell
    save_wav(os.path.join(SFX_DIR, "combo_burst.wav"), combo_samples, sr)

    # 4. Erreur douce (Thud basse fréquence 110Hz rond sans buzzer agressif)
    error_samples = []
    for i in range(int(sr * 0.28)):
        t = i / sr
        freq = 130 - (40 * (t / 0.28))
        env = math.exp(-t * 12)
        error_samples.append(0.35 * env * math.sin(2 * math.pi * freq * t))
    save_wav(os.path.join(SFX_DIR, "error_soft.wav"), error_samples, sr)

    # 5. Victoire (Fanfare carillon néon ascendante)
    vic_samples = [0.0] * int(sr * 0.85)
    vic_chords = [
        (523.25, 0.00, 0.3),  # C5
        (659.25, 0.12, 0.3),  # E5
        (783.99, 0.24, 0.3),  # G5
        (1046.50, 0.36, 0.45) # C6
    ]
    for freq, delay, notelen in vic_chords:
        start_idx = int(delay * sr)
        for i in range(int(notelen * sr)):
            t = i / sr
            env = math.exp(-t * 6)
            s = 0.22 * env * math.sin(2 * math.pi * freq * t)
            idx = start_idx + i
            if idx < len(vic_samples):
                vic_samples[idx] += s
    save_wav(os.path.join(SFX_DIR, "victory_chime.wav"), vic_samples, sr)
    print("Tous les SFX ont été générés dans", SFX_DIR)

if __name__ == "__main__":
    generate_sfx_files()
    asyncio.run(generate_voice_files())
    print("\n✅ Terminé avec succès ! Tous les fichiers audio de test sont prêts.")
