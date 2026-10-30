import os
import asyncio
import edge_tts

BASE_DIR = r"d:\Sudoku-Arena\frontend\assets\audio\options"

PHRASES = {
    "fr": {
        "explain_val_simple": "Mode Simple : Tout chiffre valide selon les règles Sudoku est accepté, sans forcer la solution finale unique.",
        "explain_val_strict": "Mode Casse-Tête : Seule l'unique solution mathématique exacte du puzzle est validée. Pour les puristes !",
        "explain_clash_combo_capped": "Variante Combo x2 : Chaque coup correct réussi rapidement vous donne un coup bonus immédiat. Deux coups consécutifs au maximum par tour !",
        "explain_clash_strict": "Variante Alternance : Un seul coup par tour, bon ou faux. Aucun combo, la main passe immédiatement !",
        "explain_clash_unlimited": "Variante Série : Vous rejouez tant que vous ne commettez aucune erreur dans le temps imparti ! Idéal pour les gros combos !",
        "explain_diff_clash_easy": "Chrono 30 secondes : Rythme détendu pour bien analyser chaque case sans stress.",
        "explain_diff_clash_medium": "Chrono 20 secondes : Le tempo e-sport standard. Équilibre parfait entre réflexion et rapidité !",
        "explain_diff_clash_hard": "Chrono 10 secondes : Pression extrême ! Réflexes instantanés requis, chaque hésitation coûte cher !",
        "explain_diff_race_easy": "Grille Facile : Nombreux indices de départ, un sprint fluide et rapide.",
        "explain_diff_race_medium": "Grille Moyenne : Complexité équilibrée demandant des déductions croisées.",
        "explain_diff_race_hard": "Grille Difficile : Très peu d'indices, un vrai défi de speedrun pour experts.",
        "explain_diff_ai_easy": "Niveau Novice : L'IA prend son temps et commet parfois des erreurs de débutant.",
        "explain_diff_ai_medium": "Niveau Tactique : L'IA joue avec précision et un bon rythme de décision.",
        "explain_diff_ai_hard": "Niveau Grand Maître : L'IA calcule ses coups à la vitesse de l'éclair sans aucune faille !"
    },
    "en": {
        "explain_val_simple": "Simple Mode: Any placement respecting standard Sudoku rules is accepted, without forcing the single end solution.",
        "explain_val_strict": "Brain-Teaser Mode: Only the unique exact mathematical solution is validated. For purists!",
        "explain_clash_combo_capped": "Combo x2 Variant: Fast correct moves grant an immediate bonus turn. Maximum two consecutive moves per turn!",
        "explain_clash_strict": "Alternating Variant: Exactly one move per turn. No combos, turn switches immediately!",
        "explain_clash_unlimited": "Streak Variant: Keep playing as long as you make fast valid moves! Ideal for massive combos!",
        "explain_diff_clash_easy": "30-second Timer: Relaxed pace to analyze each cell without pressure.",
        "explain_diff_clash_medium": "20-second Timer: Standard e-sports tempo. Perfect balance between speed and precision!",
        "explain_diff_clash_hard": "10-second Timer: Extreme pressure! Lightning reflexes required, hesitation is fatal!",
        "explain_diff_race_easy": "Easy Grid: Many starting clues, smooth and fast sprint.",
        "explain_diff_race_medium": "Medium Grid: Balanced complexity requiring cross deductions.",
        "explain_diff_race_hard": "Hard Grid: Few clues, a genuine speedrun challenge for masters.",
        "explain_diff_ai_easy": "Novice Level: The AI takes its time and occasionally makes mistakes.",
        "explain_diff_ai_medium": "Tactical Level: The AI plays accurately with good decision tempo.",
        "explain_diff_ai_hard": "Grandmaster Level: The AI calculates lightning-fast with zero mistakes!"
    },
    "de": {
        "explain_val_simple": "Einfache Regeln: Jede gültige Sudoku-Zahl wird akzeptiert, ohne die finale Endlösung zu erzwingen.",
        "explain_val_strict": "Knobel-Modus: Nur die exakte finale mathematische Lösung wird gewertet. Für Puristen!",
        "explain_clash_combo_capped": "Combo x2 Variante: Schnelle richtige Züge gewähren einen sofortigen Bonuszug. Maximal zwei Züge pro Runde!",
        "explain_clash_strict": "Abwechselnd: Genau ein Zug pro Runde. Keine Combos, die Runde wechselt sofort!",
        "explain_clash_unlimited": "Serie: Du bleibst am Zug, solange du schnelle richtige Züge setzt! Perfekt für Highscore-Combos!",
        "explain_diff_clash_easy": "30 Sekunden Timer: Entspanntes Tempo für gründliche Analyse ohne Stress.",
        "explain_diff_clash_medium": "20 Sekunden Timer: Das reguläre E-Sport-Tempo. Perfekte Balance aus Schnelligkeit und Taktik!",
        "explain_diff_clash_hard": "10 Sekunden Timer: Extremer Druck! Blitzschnelle Reflexe nötig, jedes Zögern kostet den Sieg!",
        "explain_diff_race_easy": "Leichtes Gitter: Viele vorgegebene Zahlen, flüssiger Speedrun.",
        "explain_diff_race_medium": "Mittleres Gitter: Ausgewogene Komplexität mit Kreuz-Deduktionen.",
        "explain_diff_race_hard": "Schweres Gitter: Sehr wenige Zahlen, echte Herausforderung für Profis.",
        "explain_diff_ai_easy": "Novize: Die KI lässt sich Zeit und macht gelegentlich Fehler.",
        "explain_diff_ai_medium": "Taktiker: Die KI spielt präzise mit gutem Tempo.",
        "explain_diff_ai_hard": "Großmeister: Die KI kalkuliert blitzschnell und fehlerfrei!"
    }
}

VOICES = {
    "fr": "fr-FR-HenriNeural",
    "en": "en-US-GuyNeural",
    "de": "de-DE-FlorianMultilingualNeural"
}

async def generate_options():
    for lang, items in PHRASES.items():
        voice = VOICES[lang]
        out_dir = os.path.join(BASE_DIR, lang)
        os.makedirs(out_dir, exist_ok=True)
        for key, text in items.items():
            out_file = os.path.join(out_dir, f"{key}.mp3")
            if os.path.exists(out_file):
                if os.path.getsize(out_file) > 1000:
                    print(f"Skipping [{lang}] {key}")
                    continue
                else:
                    try:
                        os.remove(out_file)
                    except Exception:
                        pass
            print(f"Synthesizing [{lang}] {key} with {voice}...")
            for attempt in range(3):
                try:
                    comm = edge_tts.Communicate(text, voice, rate="+4%")
                    await comm.save(out_file)
                    if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
                        print(f"Saved {out_file} ({os.path.getsize(out_file)} bytes)")
                        await asyncio.sleep(0.3)
                        break
                    else:
                        raise RuntimeError("File too small")
                except Exception as e:
                    print(f"Attempt {attempt+1} failed for {key}: {e}")
                    if os.path.exists(out_file):
                        try: os.remove(out_file)
                        except Exception: pass
                    await asyncio.sleep(1.2)

if __name__ == "__main__":
    asyncio.run(generate_options())
