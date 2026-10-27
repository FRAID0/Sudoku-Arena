"""
Module de Commentaire Intelligent — KI FRAID Caster 🎙️
Intègre le LLM (Google Gemini) avec Fallback procédural instantané (0 ms).
Supporte nativement le Français 🇫🇷, l'Anglais 🇬🇧 et l'Allemand 🇩🇪.
"""

import os
import asyncio
import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("sudoku_arena.llm_commentator")

# ============================================================================
# Modèles Pydantic pour les requêtes & réponses
# ============================================================================

class IntroRequest(BaseModel):
    player1_name: str = Field(default="Joueur 1", description="Pseudo du Joueur 1 (Hôte)")
    player2_name: Optional[str] = Field(default=None, description="Pseudo du Joueur 2 ou nom du Bot")
    mode: str = Field(default="clash", description="Mode de jeu : clash, race ou solo_ai")
    clash_rule: str = Field(default="combo_capped", description="Variante : strict, combo_capped, unlimited")
    lang: str = Field(default="fr", description="Langue : fr, en ou de")

class DebriefRequest(BaseModel):
    winner_name: str = Field(description="Nom du vainqueur")
    loser_name: Optional[str] = Field(default=None, description="Nom du perdant")
    winner_score: float = Field(default=0.0, description="Score du vainqueur")
    loser_score: float = Field(default=0.0, description="Score du perdant")
    is_draw: bool = Field(default=False, description="Match nul ?")
    total_combos: int = Field(default=0, description="Nombre total de combos réussis")
    duration_seconds: int = Field(default=0, description="Durée de la partie")
    mode: str = Field(default="clash", description="Mode de jeu")
    lang: str = Field(default="fr", description="Langue : fr, en ou de")

class LiveCommentRequest(BaseModel):
    event_type: str = Field(description="MOMENTUM_SHIFT, CLUTCH_MONEY_TIME, CHOKE_PRESSURE, HOT_STREAK, BOT_RIVAL_PROVOCATION")
    actor_name: str = Field(default="Joueur")
    opponent_name: Optional[str] = Field(default="Adversaire")
    leader_name: str = Field(default="Leader")
    score_diff: float = Field(default=0.0)
    empty_cells: int = Field(default=20)
    combo_streak: int = Field(default=1)
    mode: str = Field(default="clash")
    lang: str = Field(default="fr")

class CommentatorResponse(BaseModel):
    text: str = Field(description="Phrase générée pour KI FRAID")
    lang: str = Field(description="Langue de la phrase")
    source: str = Field(description="'gemini' si généré par IA, 'fallback' si règle procédurale")
    mood: str = Field(default="hype", description="Ambiance : hype, tense, celebratory, analytical, shocked, impressed, sarcastic")
    rate: float = Field(default=1.06, description="Débit de parole recommandé (1.00 à 1.25)")
    pitch: float = Field(default=1.00, description="Hauteur de voix recommandée (0.95 à 1.10)")
    audio_fallback_key: str = Field(description="Clé du fichier audio statique de secours (ex: WELCOME, VICTORY, COMBO_X2)")

# ============================================================================
# Moteur de Fallback Procédural (0ms, 100% Hors-ligne garanti)
# ============================================================================

import random

FALLBACK_TEMPLATES = {
    "fr": {
        "intro_pvp": [
            "Bienvenue dans l'arène ! Duel au sommet entre {p1} et {p2} en mode {mode} ! Que le meilleur gagne !",
            "L'ambiance monte d'un cran ! {p1} face à {p2} en mode {mode}, place au spectacle et à la précision !"
        ],
        "intro_bot": [
            "Bienvenue dans l'arène ! {p1} défie mon alter-ego le Bot IA FRAID ! Prépare tes méninges, l'algorithme ne fera aucun cadeau !",
            "Face-à-face palpitant ! {p1} se mesure au Bot IA FRAID ! Concentration maximale exigée !"
        ],
        "intro_solo": [
            "Bienvenue dans l'arène Sudoku {p1} ! Prépare tes neurones, chaque coup compte !",
            "C'est parti pour le défi solo {p1} ! Fais parler ta vitesse et ta rigueur logique !"
        ],
        "debrief_win": [
            "Quel duel d'anthologie ! {winner} s'impose avec brio face à {loser} avec un score magistral de {ws} points et {combos} combos !",
            "Prestation magistrale ! {winner} prend le dessus sur {loser} en accumulant {ws} points et {combos} combos !"
        ],
        "debrief_draw": [
            "Égalité parfaite ! {p1} et {p2} terminent dos à dos avec {ws} points. Une revanche s'impose immédiatement !",
            "Score vierge de tout écart ! {p1} et {p2} finissent ex-aequo à {ws} points. Match splendide !"
        ],
        "debrief_solo": [
            "Fin de partie ! {winner} triomphe avec {ws} points au compteur. Une prestation d'une grande rigueur !",
            "Défi relevé avec brio ! {winner} conclut sa grille avec un total de {ws} points !"
        ],
        "live_momentum_shift": [
            "Incroyable bascule ! {actor} passe devant au score avec {score_diff} points d'avance !",
            "Changement de leader ! {actor} renverse la vapeur et s'empare de la tête (+{score_diff} pts) !"
        ],
        "live_clutch_money_time": [
            "Money time absolu ! Plus que {empty_cells} cases, la moindre erreur est éliminatoire !",
            "Tension maximale dans l'arène ! {empty_cells} cases restantes, chaque chiffre vaut de l'or !"
        ],
        "live_choke_pressure": [
            "Aïe sous la pression ! {actor} commet une faute au pire moment possible !",
            "Coup dur ! {actor} trébuche face à l'urgence du chrono, la main passe !"
        ],
        "live_hot_streak": [
            "Quel rythme d'enfer ! {actor} enchaîne les coups avec une vista insolente !",
            "En pleine confiance ! {actor} aligne les validations avec une précision chirurgicale !"
        ],
        "live_bot_provocation": [
            "Le Bot IA FRAID montre les muscles ! Ne le laisse pas s'échapper !",
            "Accélération du Bot IA FRAID ! La riposte adverse doit être immédiate !"
        ]
    },
    "en": {
        "intro_pvp": [
            "Welcome to the Arena! Epic clash between {p1} and {p2} in {mode} mode! Sharpen your minds, let the battle begin!",
            "High stakes today! {p1} versus {p2} in {mode} mode! May the sharpest logic prevail!"
        ],
        "intro_bot": [
            "Welcome to the Arena! {p1} takes on my alter-ego, the Rival Bot AI FRAID! The algorithm is ready, give it your all!",
            "Human versus machine! {p1} takes the stage against the AI FRAID Bot! Let's see what you've got!"
        ],
        "intro_solo": [
            "Welcome to the Sudoku Arena {p1}! Sharpen your mind, every single move matters today!",
            "Solo challenge underway for {p1}! Speed and tactical precision will decide the score!"
        ],
        "debrief_win": [
            "What a legendary match! {winner} takes the crown over {loser} with an incredible score of {ws} points and {combos} combos!",
            "Supreme performance! {winner} outplays {loser} finishing with {ws} points and {combos} combos!"
        ],
        "debrief_draw": [
            "Dead heat! {p1} and {p2} finish dead even at {ws} points. An immediate rematch is in order!",
            "Perfect stalemate! {p1} and {p2} tie at {ws} points. What a thrilling showdown!"
        ],
        "debrief_solo": [
            "Match concluded! {winner} triumphs with a solid score of {ws} points. Outstanding precision!",
            "Puzzle complete! {winner} wraps up the arena with {ws} points on the scoreboard!"
        ],
        "live_momentum_shift": [
            "Incredible turnaround! {actor} takes the lead with a {score_diff}-point swing!",
            "Lead change! {actor} surges ahead by {score_diff} points!"
        ],
        "live_clutch_money_time": [
            "Clutch time! Only {empty_cells} cells remaining, every single digit is critical!",
            "Crunch time in the arena! Just {empty_cells} slots open, zero room for error!"
        ],
        "live_choke_pressure": [
            "Cracking under pressure! {actor} makes a costly mistake at the worst possible time!",
            "Painful misstep! {actor} falters under time pressure, turn surrendered!"
        ],
        "live_hot_streak": [
            "Unreal momentum! {actor} is on fire with surgical precision!",
            "Pure flow state! {actor} locks in numbers with lightning speed!"
        ],
        "live_bot_provocation": [
            "Rival Bot AI FRAID is flexing! Don't let the algorithm run away with this!",
            "The AI FRAID Bot strikes again! Time to answer back with conviction!"
        ]
    },
    "de": {
        "intro_pvp": [
            "Willkommen in der Arena! Großes Duell zwischen {p1} und {p2} im {mode}-Modus! Schärft euren Verstand, möge der Beste gewinnen!",
            "Hochspannung in der Arena! {p1} gegen {p2} im {mode}-Modus, volle Konzentration jetzt!"
        ],
        "intro_bot": [
            "Willkommen in der Arena! {p1} fordert meinen Bot-Rivalen KI FRAID heraus! Keine Geschenke vom Algorithmus, zeig dein Können!",
            "Mensch gegen Maschine! {p1} tritt gegen den KI FRAID Bot an! Zeig, was du drauf hast!"
        ],
        "intro_solo": [
            "Willkommen in der Sudoku Arena {p1}! Jeder einzelne Zug zählt heute!",
            "Solo-Herausforderung für {p1}! Präzision und schnelle Auffassungsgabe sind gefragt!"
        ],
        "debrief_win": [
            "Was für ein fantastisches Match! {winner} triumphiert gegen {loser} mit stolzen {ws} Punkten und {combos} Combos!",
            "Glanzvolle Vorstellung! {winner} bezwingt {loser} mit {ws} Punkten und {combos} Combos!"
        ],
        "debrief_draw": [
            "Perfektes Unentschieden! {p1} und {p2} trennen sich gleichauf mit {ws} Punkten. Zeit für die Revanche!",
            "Gleichstand! {p1} und {p2} teilen sich die Punkte bei {ws}. Was für ein Kampf!"
        ],
        "debrief_solo": [
            "Spiel beendet! {winner} gewinnt mit {ws} Punkten auf dem Konto. Höchste Präzision!",
            "Herausforderung gemeistert! {winner} beendet das Spiel mit {ws} Punkten!"
        ],
        "live_momentum_shift": [
            "Unglaubliche Wende! {actor} übernimmt die Führung mit {score_diff} Punkten Vorsprung!",
            "Führungswechsel! {actor} dreht das Spiel und liegt mit {score_diff} Punkten vorne!"
        ],
        "live_clutch_money_time": [
            "Absolute Schlussphase! Nur noch {empty_cells} Felder, jeder Fehler ist tödlich!",
            "Hochspannung! Noch {empty_cells} offene Felder, jetzt zählt absolute Nervenstärke!"
        ],
        "live_choke_pressure": [
            "Nervenschwäche! {actor} patzt im denkbar ungünstigsten Moment!",
            "Teurer Ausrutscher! {actor} verliert die Nerven unter Zeitdruck!"
        ],
        "live_hot_streak": [
            "Was für ein Lauf! {actor} versenkt die Züge mit chirurgischer Präzision!",
            "Im Flow! {actor} setzt die Zahlen in rasender Geschwindigkeit!"
        ],
        "live_bot_provocation": [
            "Bot-Rivale KI FRAID dreht auf! Lass den Algorithmus nicht davonziehen!",
            "Der KI FRAID Bot legt vor! Jetzt muss die prompte Antwort kommen!"
        ]
    }
}

class LLMCommentatorService:
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 3.5):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.client = None
        self._init_gemini_client()

    def _init_gemini_client(self):
        if not self.api_key:
            logger.info("Aucune clé GEMINI_API_KEY détectée. Mode Fallback procédural activé.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Client Google GenAI initialisé avec succès.")
        except Exception as e:
            logger.warning(f"Impossible d'initialiser Google GenAI : {e}. Mode Fallback actif.")
            self.client = None

    def is_gemini_available(self) -> bool:
        return self.client is not None

    async def generate_intro(self, req: IntroRequest) -> CommentatorResponse:
        """
        Génère une annonce d'avant-match personnalisée avec les pseudos réels et les règles.
        """
        lang = req.lang if req.lang in FALLBACK_TEMPLATES else "fr"

        # 1. Tentative d'appel Gemini avec timeout strict
        if self.client:
            try:
                text = await asyncio.wait_for(self._call_gemini_intro(req), timeout=self.timeout_seconds)
                if text:
                    return CommentatorResponse(
                        text=text.strip(),
                        lang=lang,
                        source="gemini",
                        mood="hype",
                        audio_fallback_key="WELCOME"
                    )
            except Exception as e:
                logger.warning(f"Délai dépassé ou erreur Gemini intro ({repr(e)}). Utilisation du Fallback.")

        # 2. Fallback procédural instantané
        t = FALLBACK_TEMPLATES[lang]
        p1 = req.player1_name
        p2 = req.player2_name

        mode_label = {
            "clash": "Clash Tour par Tour" if lang == "fr" else ("Clash Turn-Based" if lang == "en" else "Rundenbasierter Clash"),
            "race": "Course Speedrun" if lang == "fr" else ("Race Speedrun" if lang == "en" else "Speedrun-Rennen"),
            "solo_ai": "Duel vs Bot Rival" if lang == "fr" else ("Duel vs Rival Bot" if lang == "en" else "Duell gegen Bot-Rivale")
        }.get(req.mode, req.mode)

        if p2 and ("bot" in p2.lower() or "fraid" in p2.lower()):
            tmpl = random.choice(t["intro_bot"]) if isinstance(t["intro_bot"], list) else t["intro_bot"]
            msg = tmpl.format(p1=p1, mode=mode_label)
        elif p2:
            tmpl = random.choice(t["intro_pvp"]) if isinstance(t["intro_pvp"], list) else t["intro_pvp"]
            msg = tmpl.format(p1=p1, p2=p2, mode=mode_label)
        else:
            tmpl = random.choice(t["intro_solo"]) if isinstance(t["intro_solo"], list) else t["intro_solo"]
            msg = tmpl.format(p1=p1)

        return CommentatorResponse(
            text=msg,
            lang=lang,
            source="fallback",
            mood="hype",
            audio_fallback_key="WELCOME"
        )

    async def generate_debrief(self, req: DebriefRequest) -> CommentatorResponse:
        """
        Génère une analyse post-match e-sport fondée sur les faits calculés par le serveur.
        """
        lang = req.lang if req.lang in FALLBACK_TEMPLATES else "fr"

        # 1. Tentative d'appel Gemini
        if self.client:
            try:
                text = await asyncio.wait_for(self._call_gemini_debrief(req), timeout=self.timeout_seconds)
                if text:
                    return CommentatorResponse(
                        text=text.strip(),
                        lang=lang,
                        source="gemini",
                        mood="celebratory",
                        audio_fallback_key="VICTORY"
                    )
            except Exception as e:
                logger.warning(f"Délai dépassé ou erreur Gemini debrief ({repr(e)}). Utilisation du Fallback.")

        # 2. Fallback procédural
        t = FALLBACK_TEMPLATES[lang]
        if req.is_draw:
            tmpl = random.choice(t["debrief_draw"]) if isinstance(t["debrief_draw"], list) else t["debrief_draw"]
            msg = tmpl.format(p1=req.winner_name, p2=req.loser_name or "Adversaire", ws=req.winner_score)
        elif req.loser_name:
            tmpl = random.choice(t["debrief_win"]) if isinstance(t["debrief_win"], list) else t["debrief_win"]
            msg = tmpl.format(winner=req.winner_name, loser=req.loser_name, ws=req.winner_score, combos=req.total_combos)
        else:
            tmpl = random.choice(t["debrief_solo"]) if isinstance(t["debrief_solo"], list) else t["debrief_solo"]
            msg = tmpl.format(winner=req.winner_name, ws=req.winner_score)

        return CommentatorResponse(
            text=msg,
            lang=lang,
            source="fallback",
            mood="celebratory",
            audio_fallback_key="VICTORY"
        )

    def _get_persona_instruction(self, lang: str) -> str:
        """Fournit les directives de personnalité et de prononciation exacte selon la langue."""
        if lang == "fr":
            return (
                "RÔLE & IDENTITÉ : Tu es l'IA FRAID, le commentateur officiel e-sport de Sudoku Arena. "
                "PRONONCIATION OBLIGATOIRE : En français, écris et nomme-toi TOUJOURS 'l'IA FRAID' "
                "(ne dis JAMAIS 'KI FRAID' ni 'K-I', pour que la synthèse vocale prononce naturellement 'l'IA FRAID'). "
                "Si l'adversaire est le bot, appelle-le 'le Bot IA FRAID'. "
                "DIRECTIVE DE VARIÉTÉ : Bannis formellement les clichés éculés (interdit : 'renverse la table', 'hold-up', 'les neurones chauffent', 'au coude à coude', 'en ébullition'). "
                "Varie ton lexique : tempo, rigueur, audace, sang-froid, pression du chrono, précision chirurgicale."
            )
        elif lang == "en":
            return (
                "ROLE & IDENTITY: You are AI FRAID, the official e-sports shoutcaster of Sudoku Arena. "
                "PRONUNCIATION: In English, your name is 'AI FRAID' (pronounced 'Ey-Eye Fraid'), "
                "and the training rival is 'the AI FRAID Bot'. "
                "VARIETY DIRECTIVE: Strictly avoid repetitive clichés (forbidden: 'turns the tables', 'nail-biter', 'brains on fire'). "
                "Vary your vocabulary: lightning tempo, cool nerves, clock pressure, tactical audacity, clinical precision."
            )
        else:  # de
            return (
                "ROLLE & IDENTITÄT: Du bist KI FRAID, der offizielle E-Sport-Kommentator von Sudoku Arena. "
                "AUSSPRACHE: Auf Deutsch heißt du 'KI FRAID' (gesprochen 'Ka-I Fraid'), "
                "und der Trainingsgegner ist 'der KI FRAID Bot'. "
                "VARIATIONS-RICHTLINIE: Vermeide abgedroschene Floskeln (verboten: 'dreht das Spiel komplett um', 'Gehirnzellen rauchen'). "
                "Variiere deinen Wortschatz: Nervenstärke, Tempowechsel, Zeitdruck, taktische Finesse, chirurgische Präzision."
            )

    async def _call_gemini_intro(self, req: IntroRequest) -> Optional[str]:
        lang_names = {"fr": "français", "en": "anglais", "de": "allemand"}
        persona = self._get_persona_instruction(req.lang)
        bot_default = "le Bot IA FRAID" if req.lang == "fr" else ("the AI FRAID Bot" if req.lang == "en" else "der KI FRAID Bot")
        p2_label = req.player2_name or bot_default

        prompt = (
            f"{persona}\n\n"
            f"MISSION : Rédige UNE SEULE phrase percutante d'introduction d'avant-match (max 22 mots).\n"
            f"Langue obligatoire : {lang_names.get(req.lang, 'français')}.\n"
            f"Contexte du match : Joueur 1 = '{req.player1_name}', Joueur 2 = '{p2_label}', "
            f"Mode de jeu = '{req.mode}', Règle = '{req.clash_rule}'.\n"
            f"Contrainte technique : Ne mets aucun guillemet, aucun tiret, aucune balise markdown. Uniquement la phrase parlée directe."
        )

        for model_candidate in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash"]:
            try:
                res = await self.client.aio.models.generate_content(
                    model=model_candidate,
                    contents=prompt
                )
                if res and res.text:
                    return res.text
            except Exception as e:
                logger.debug(f"Modèle {model_candidate} indisponible pour intro: {e}")
                continue
        return None

    async def _call_gemini_debrief(self, req: DebriefRequest) -> Optional[str]:
        lang_names = {"fr": "français", "en": "anglais", "de": "allemand"}
        persona = self._get_persona_instruction(req.lang)

        prompt = (
            f"{persona}\n\n"
            f"MISSION : Rédige le mot de clôture officiel du match en UNE SEULE phrase mémorable et percutante (max 22 mots).\n"
            f"Langue obligatoire : {lang_names.get(req.lang, 'français')}.\n"
            f"Faits réels du match : Vainqueur = '{req.winner_name}', Perdant = '{req.loser_name or 'N/A'}', "
            f"Score vainqueur = {req.winner_score} pts, Score perdant = {req.loser_score} pts, "
            f"Combos validés = {req.total_combos}, Match nul = {req.is_draw}.\n"
            f"Contrainte technique : Ne mets aucun guillemet, aucun tiret, aucune balise markdown. Uniquement la phrase parlée directe."
        )

        for model_candidate in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash"]:
            try:
                res = await self.client.aio.models.generate_content(
                    model=model_candidate,
                    contents=prompt
                )
                if res and res.text:
                    return res.text
            except Exception as e:
                logger.debug(f"Modèle {model_candidate} indisponible pour debrief: {e}")
                continue
        return None

    async def generate_live_comment(self, req: LiveCommentRequest) -> CommentatorResponse:
        """
        Génère une intervention de commentateur e-sport en direct (Echtzeit)
        selon les événements dramatiques détectés (Money time, Remontada, Choke, Hot Streak).
        """
        lang = req.lang if req.lang in FALLBACK_TEMPLATES else "fr"

        mood_profiles = {
            "CLUTCH_MONEY_TIME": ("tense", 1.15, 1.04, "MOVE_VALID"),
            "MOMENTUM_SHIFT": ("hype", 1.18, 1.05, "COMBO_X2"),
            "HOT_STREAK": ("impressed", 1.12, 1.02, "COMBO_X2"),
            "CHOKE_PRESSURE": ("shocked", 1.04, 0.98, "ERROR"),
            "BOT_RIVAL_PROVOCATION": ("sarcastic", 1.08, 1.02, "COMBO_X2")
        }
        mood, rate, pitch, fallback_key = mood_profiles.get(req.event_type, ("hype", 1.06, 1.00, "COMBO_X2"))

        # 1. Tentative d'appel Gemini
        if self.client:
            try:
                text = await asyncio.wait_for(self._call_gemini_live(req, mood), timeout=2.2)
                if text:
                    return CommentatorResponse(
                        text=text.strip(),
                        lang=lang,
                        source="gemini",
                        mood=mood,
                        rate=rate,
                        pitch=pitch,
                        audio_fallback_key=fallback_key
                    )
            except Exception as e:
                logger.warning(f"Délai dépassé ou erreur Gemini live ({repr(e)}). Fallback.")

        # 2. Fallback procédural instantané
        t = FALLBACK_TEMPLATES[lang]
        template_keys = {
            "CLUTCH_MONEY_TIME": "live_clutch_money_time",
            "MOMENTUM_SHIFT": "live_momentum_shift",
            "HOT_STREAK": "live_hot_streak",
            "CHOKE_PRESSURE": "live_choke_pressure",
            "BOT_RIVAL_PROVOCATION": "live_bot_provocation"
        }
        template_key = template_keys.get(req.event_type, "live_momentum_shift")
        tmpl_raw = t.get(template_key, t["live_momentum_shift"])
        tmpl = random.choice(tmpl_raw) if isinstance(tmpl_raw, list) else tmpl_raw

        text = tmpl.format(
            actor=req.actor_name,
            score_diff=abs(round(req.score_diff, 1)),
            empty_cells=req.empty_cells,
            combo=req.combo_streak
        )

        return CommentatorResponse(
            text=text,
            lang=lang,
            source="fallback",
            mood=mood,
            rate=rate,
            pitch=pitch,
            audio_fallback_key=fallback_key
        )

    async def _call_gemini_live(self, req: LiveCommentRequest, mood: str) -> Optional[str]:
        lang_names = {"fr": "français", "en": "anglais", "de": "allemand"}
        persona = self._get_persona_instruction(req.lang)

        prompt = (
            f"{persona}\n\n"
            f"MISSION : Réagis en direct au match avec une phrase spontanée, vivante et percutante (max 16 mots).\n"
            f"Langue obligatoire : {lang_names.get(req.lang, 'français')}.\n"
            f"Événement clé : {req.event_type} | Intention/Émotion : {mood}.\n"
            f"Données de télémétrie en temps réel : Joueur actif = '{req.actor_name}', Adversaire = '{req.opponent_name or 'Rival'}', "
            f"Écart au score = {abs(round(req.score_diff, 1))} pts, Cases restantes = {req.empty_cells}, "
            f"Combos = {req.combo_streak}.\n"
            f"Contrainte technique : Ne mets aucun guillemet, aucun tiret, aucune balise markdown. Uniquement la phrase parlée directe."
        )

        for model_candidate in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash"]:
            try:
                res = await self.client.aio.models.generate_content(
                    model=model_candidate,
                    contents=prompt
                )
                if res and res.text:
                    return res.text
            except Exception as e:
                logger.debug(f"Modèle {model_candidate} indisponible pour live comment: {e}")
                continue
        return None

# Instance singleton du service
commentator_service = LLMCommentatorService()

