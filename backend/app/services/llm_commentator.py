"""
Module de Commentaire Intelligent — KI FRAID Caster 🎙️
Intègre le LLM (Google Gemini) avec :
1. Mémoire anti-répétition en cours de match.
2. Sac de tirage sans remise (ShuffleBag) pour rotation garantie sans répétition immédiate.
3. Filtre de similarité post-génération (Jaccard + préfixes).
4. Synthèse vocale Edge-TTS studio à la demande mise en cache.
Supporte nativement le Français 🇫🇷, l'Anglais 🇬🇧 et l'Allemand 🇩🇪.
"""

import os
import re
import random
import asyncio
import logging
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.services.tts_service import tts_service

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
    comment_id: Optional[str] = Field(default=None)

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
    comment_id: Optional[str] = Field(default=None)

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
    recent_history: List[str] = Field(default_factory=list, description="Derniers commentaires prononcés dans ce match")
    comment_id: Optional[str] = Field(default=None)

class CommentatorResponse(BaseModel):
    text: str = Field(description="Phrase générée pour KI FRAID")
    lang: str = Field(description="Langue de la phrase")
    source: str = Field(description="'gemini' si généré par IA, 'fallback' si règle procédurale")
    mood: str = Field(default="hype", description="Ambiance : hype, tense, celebratory, analytical, shocked, impressed, sarcastic")
    rate: float = Field(default=1.06, description="Débit de parole recommandé (1.00 à 1.25)")
    pitch: float = Field(default=1.00, description="Hauteur de voix recommandée (0.95 à 1.10)")
    audio_fallback_key: str = Field(description="Clé du fichier audio statique de secours (ex: WELCOME, VICTORY, COMBO_X2)")
    audio_url: Optional[str] = Field(default=None, description="URL du fichier audio Edge-TTS pré-généré ou mis en cache")
    comment_id: Optional[str] = Field(default=None)

# ============================================================================
# ShuffleBag : Tirage sans remise avec garde anti-oscillation
# ============================================================================

class ShuffleBag:
    """
    Sac de tirage aléatoire sans remise (Shuffle-Bag / Deck épuisable).
    Garantit qu'aucune phrase ne se répète avant d'avoir joué l'ensemble du deck,
    et empêche toute répétition consécutive ou oscillation A-B-A-B lors du remaniement.
    """
    def __init__(self, items: List[str]):
        self.original_items = list(items)
        self.current_deck: List[str] = []
        self.last_drawn: Optional[str] = None

    def draw(self) -> str:
        if not self.original_items:
            return ""
        if len(self.original_items) == 1:
            return self.original_items[0]

        if not self.current_deck:
            self.current_deck = list(self.original_items)
            random.shuffle(self.current_deck)
            # Empêche la première phrase du nouveau deck d'être identique à la dernière tirée
            if self.current_deck[-1] == self.last_drawn and len(self.current_deck) > 1:
                self.current_deck[0], self.current_deck[-1] = self.current_deck[-1], self.current_deck[0]

        chosen = self.current_deck.pop()
        self.last_drawn = chosen
        return chosen

# ============================================================================
# Catalogue Multi-Variantes Étendu (FR, EN, DE)
# ============================================================================

FALLBACK_TEMPLATES = {
    "fr": {
        "intro_pvp": [
            "Bienvenue dans l'arène ! Duel au sommet entre {p1} et {p2} en mode {mode} ! Que le meilleur gagne !",
            "L'ambiance monte d'un cran ! {p1} face à {p2} en mode {mode}, place au spectacle et à la précision !",
            "Arène sous tension ! Deux styles s'affrontent aujourd'hui : {p1} contre {p2}. Que la logique triomphe !",
            "Coup d'envoi du face-à-face ! {p1} défie {p2} sur ce {mode}. Préparez vos méninges !"
        ],
        "intro_bot": [
            "Bienvenue dans l'arène ! {p1} défie mon alter-ego le Bot IA FRAID ! Prépare tes méninges, l'algorithme ne fera aucun cadeau !",
            "Face-à-face palpitant ! {p1} se mesure au Bot IA FRAID ! Concentration maximale exigée !",
            "L'esprit humain face au silicium ! {p1} affronte le Bot IA FRAID. Prouve ta supériorité tactique !",
            "Défi cybernétique lancé ! {p1} entre dans l'arène contre le Bot IA FRAID. Pas le droit à l'erreur !"
        ],
        "intro_solo": [
            "Bienvenue dans l'arène Sudoku {p1} ! Prépare tes neurones, chaque coup compte !",
            "C'est parti pour le défi solo {p1} ! Fais parler ta vitesse et ta rigueur logique !",
            "Grille chargée pour {p1} ! Sang-froid et précision millimétrée au programme !",
            "L'arène t'attend {p1} ! Lance-toi et vise le sans-faute !"
        ],
        "debrief_win": [
            "Quel duel d'anthologie ! {winner} s'impose avec brio face à {loser} avec un score magistral de {ws} points et {combos} combos !",
            "Prestation magistrale ! {winner} prend le dessus sur {loser} en accumulant {ws} points et {combos} combos !",
            "Victoire sans appel ! {winner} a dicté son tempo du début à la fin pour vaincre {loser} avec {ws} points !",
            "L'arène salue son champion ! {winner} triomphe avec {ws} points après une bataille haletante contre {loser} !"
        ],
        "debrief_draw": [
            "Égalité parfaite ! {p1} et {p2} terminent dos à dos avec {ws} points. Une revanche s'impose immédiatement !",
            "Score vierge de tout écart ! {p1} et {p2} finissent ex-aequo à {ws} points. Match splendide !",
            "Partage des points d'une rare intensité ! {p1} et {p2} neutralisés à {ws} points !"
        ],
        "debrief_solo": [
            "Fin de partie ! {winner} triomphe avec {ws} points au compteur. Une prestation d'une grande rigueur !",
            "Défi relevé avec brio ! {winner} conclut sa grille avec un total de {ws} points !",
            "Grille maîtrisée de bout en bout ! {winner} affiche un score solide de {ws} points !"
        ],
        "live_momentum_shift": [
            "Incroyable bascule ! {actor} passe devant au score avec {score_diff} points d'avance !",
            "Changement de leader ! {actor} prend les commandes du match (+{score_diff} pts) !",
            "La dynamique s'inverse ! {actor} comble son retard et s'empare de la tête (+{score_diff} pts) !",
            "Coup de théâtre sur la grille ! {actor} s'installe en pole position avec {score_diff} points d'écart !",
            "Renversement tactique ! {actor} impose son rythme et repasse devant (+{score_diff} pts) !"
        ],
        "live_clutch_money_time": [
            "Money time absolu ! Plus que {empty_cells} cases, la moindre erreur est éliminatoire !",
            "Tension maximale dans l'arène ! {empty_cells} cases restantes, chaque chiffre vaut de l'or !",
            "Sprint final engagé ! Seulement {empty_cells} cases à pourvoir, l'étau se resserre !",
            "Dernière ligne droite ! Plus que {empty_cells} cases ouvertes, gardez le sang-froid !",
            "L'arène retient son souffle ! {empty_cells} chiffres restants, interdiction formelle de trembler !"
        ],
        "live_choke_pressure": [
            "Aïe sous la pression ! {actor} commet une faute au pire moment possible !",
            "Coup dur ! {actor} trébuche face à l'urgence du chrono, la main passe !",
            "Faux pas regrettable pour {actor} ! La précipitation coûte très cher dans ce duel !",
            "Hésitation fatale ! {actor} cède son tour sur une case piégée !",
            "La pression monte d'un cran : {actor} manque sa cible, occasion en or pour l'adversaire !"
        ],
        "live_hot_streak": [
            "Quel rythme d'enfer ! {actor} enchaîne les coups avec une vista insolente !",
            "En pleine confiance ! {actor} aligne les validations avec une précision chirurgicale !",
            "Démonstration de vitesse ! {actor} accélère la cadence et verrouille les chiffres !",
            "Impressionnante fluidité ! {actor} trouve les failles de la grille sans la moindre hésitation !",
            "Coup de chaud dans l'arène ! {actor} enclenche le mode turbo !"
        ],
        "live_bot_provocation": [
            "Le Bot IA FRAID montre les muscles ! Ne le laisse pas s'échapper !",
            "Accélération du Bot IA FRAID ! La riposte adverse doit être immédiate !",
            "Le Bot IA FRAID accélère le calcul matriciel ! Il va falloir hausser le niveau de jeu !",
            "Réaction chirurgicale du Bot IA FRAID ! La pression retombe entièrement sur le joueur !",
            "Le Bot IA FRAID valide sans sourciller ! Montre-lui la créativité humaine !"
        ]
    },
    "en": {
        "intro_pvp": [
            "Welcome to the Arena! Epic clash between {p1} and {p2} in {mode} mode! Sharpen your minds, let the battle begin!",
            "High stakes today! {p1} versus {p2} in {mode} mode! May the sharpest logic prevail!",
            "Arena atmosphere is electric! Two tactical masterminds: {p1} against {p2}. Ready, set, solve!",
            "Showtime in the arena! {p1} challenges {p2} on this {mode} duel. Precision will decide the champion!"
        ],
        "intro_bot": [
            "Welcome to the Arena! {p1} takes on my alter-ego, the Rival Bot AI FRAID! The algorithm is ready, give it your all!",
            "Human versus machine! {p1} takes the stage against the AI FRAID Bot! Let's see what you've got!",
            "Silicon versus synaptic instinct! {p1} faces the AI FRAID Bot. No room for hesitation!",
            "Cybernetic showdown! {p1} steps in against the relentless AI FRAID Bot. Bring your A-game!"
        ],
        "intro_solo": [
            "Welcome to the Sudoku Arena {p1}! Sharpen your mind, every single move matters today!",
            "Solo challenge underway for {p1}! Speed and tactical precision will decide the score!",
            "Grid loaded for {p1}! Keep your focus sharp and your deduction clean!",
            "The arena awaits you, {p1}! Take your time or race the clock—your move!"
        ],
        "debrief_win": [
            "What a legendary match! {winner} takes the crown over {loser} with an incredible score of {ws} points and {combos} combos!",
            "Supreme performance! {winner} outplays {loser} finishing with {ws} points and {combos} combos!",
            "Decisive victory! {winner} controlled the board tempo and defeats {loser} with {ws} points!",
            "The arena bows to the victor! {winner} claims the match with {ws} points after an intense battle!"
        ],
        "debrief_draw": [
            "Dead heat! {p1} and {p2} finish dead even at {ws} points. An immediate rematch is in order!",
            "Perfect stalemate! {p1} and {p2} tie at {ws} points. What a thrilling showdown!",
            "Split decision at the wire! Both {p1} and {p2} locked at {ws} points!"
        ],
        "debrief_solo": [
            "Match concluded! {winner} triumphs with a solid score of {ws} points. Outstanding precision!",
            "Puzzle complete! {winner} wraps up the arena with {ws} points on the scoreboard!",
            "Masterful solo run! {winner} locks in the final digit with {ws} points!"
        ],
        "live_momentum_shift": [
            "Incredible turnaround! {actor} takes the lead with a {score_diff}-point swing!",
            "Lead change! {actor} surges ahead by {score_diff} points!",
            "Momentum shift in the arena! {actor} captures the high ground (+{score_diff} pts)!",
            "Tables turned! {actor} breaks through and grabs the advantage by {score_diff} points!",
            "Dramatic swing! {actor} claims pole position with a {score_diff}-point cushion!"
        ],
        "live_clutch_money_time": [
            "Clutch time! Only {empty_cells} cells remaining, every single digit is critical!",
            "Crunch time in the arena! Just {empty_cells} slots open, zero room for error!",
            "The endgame is here! {empty_cells} squares left, steel nerves required!",
            "Final stretch! {empty_cells} empty cells on the board, keep your composure!",
            "Down to the wire! Just {empty_cells} numbers remain to decide the fate of this match!"
        ],
        "live_choke_pressure": [
            "Cracking under pressure! {actor} makes a costly mistake at the worst possible time!",
            "Painful misstep! {actor} falters under time pressure, turn surrendered!",
            "Costly slip by {actor}! Rushing the clock can be deadly in this arena!",
            "Stumbled on the board! {actor} misses the placement, handing the initiative away!",
            "Pressure is mounting! {actor} hits a road block—golden opportunity for the opponent!"
        ],
        "live_hot_streak": [
            "Unreal momentum! {actor} is on fire with surgical precision!",
            "Pure flow state! {actor} locks in numbers with lightning speed!",
            "Sizzling cadence! {actor} reads the grid like an open book!",
            "Blistering tempo! {actor} strings together answers without blinking!",
            "High gear engaged! {actor} is dominating the grid right now!"
        ],
        "live_bot_provocation": [
            "Rival Bot AI FRAID is flexing! Don't let the algorithm run away with this!",
            "The AI FRAID Bot strikes again! Time to answer back with conviction!",
            "AI FRAID Bot shifts into overdrive! Human creativity needs to answer now!",
            "Algorithmic precision on display! The AI FRAID Bot sets the challenge high!",
            "Swift strike from the AI FRAID Bot! The arena demands a counter-attack!"
        ]
    },
    "de": {
        "intro_pvp": [
            "Willkommen in der Arena! Großes Duell zwischen {p1} und {p2} im {mode}-Modus! Schärft euren Verstand, möge der Beste gewinnen!",
            "Hochspannung in der Arena! {p1} gegen {p2} im {mode}-Modus, volle Konzentration jetzt!",
            "Elektrisierende Atmosphäre! Zwei Denker im Wettstreit: {p1} fordert {p2} heraus. Auf die Plätze, fertig, logisch!",
            "Spitzenspiel in der Arena! {p1} gegen {p2}. Taktische Brillanz entscheidet das Duell!"
        ],
        "intro_bot": [
            "Willkommen in der Arena! {p1} fordert meinen Bot-Rivalen KI FRAID heraus! Keine Geschenke vom Algorithmus, zeig dein Können!",
            "Mensch gegen Maschine! {p1} tritt gegen den KI FRAID Bot an! Zeig, was du drauf hast!",
            "Verstand gegen Algorithmus! {p1} stellt sich dem KI FRAID Bot. Höchste Wachsamkeit gefordert!",
            "Kybernetisches Duell! {p1} fordert die Rechenpower des KI FRAID Bots heraus. Viel Erfolg!"
        ],
        "intro_solo": [
            "Willkommen in der Sudoku Arena {p1}! Jeder einzelne Zug zählt heute!",
            "Solo-Herausforderung für {p1}! Präzision und schnelle Auffassungsgabe sind gefragt!",
            "Das Gitter ist bereit {p1}! Konzentration auf Maximum, jeder Zug zählt!",
            "Deine Bühne {p1}! Beweise deine logische Stärke im Alleingang!"
        ],
        "debrief_win": [
            "Was für ein fantastisches Match! {winner} triumphiert gegen {loser} mit stolzen {ws} Punkten und {combos} Combos!",
            "Glanzvolle Vorstellung! {winner} bezwingt {loser} mit {ws} Punkten und {combos} Combos!",
            "Klarer Sieg! {winner} bestimmte das Tempo und gewinnt gegen {loser} mit {ws} Punkten!",
            "Die Arena feiert ihren Sieger! {winner} holt den Triumph mit {ws} Punkten nach packendem Kampf!"
        ],
        "debrief_draw": [
            "Perfektes Unentschieden! {p1} und {p2} trennen sich gleichauf mit {ws} Punkten. Zeit für die Revanche!",
            "Gleichstand! {p1} und {p2} teilen sich die Punkte bei {ws}. Was für ein Kampf!",
            "Punkteteilung nach einem hochdramatischen Match zwischen {p1} und {p2}!"
        ],
        "debrief_solo": [
            "Spiel beendet! {winner} gewinnt mit {ws} Punkten auf dem Konto. Höchste Präzision!",
            "Herausforderung gemeistert! {winner} beendet das Spiel mit {ws} Punkten!",
            "Souveräner Solo-Durchlauf! {winner} schließt die Runde mit {ws} Punkten ab!"
        ],
        "live_momentum_shift": [
            "Unglaubliche Wende! {actor} übernimmt die Führung mit {score_diff} Punkten Vorsprung!",
            "Führungswechsel! {actor} dreht das Spiel und liegt mit {score_diff} Punkten vorne!",
            "Das Blatt hat sich gewendet! {actor} greift nach der Führung (+{score_diff} Pkt)!",
            "Taktischer Coup! {actor} zieht an der Konkurrenz vorbei (+{score_diff} Punkte)!",
            "Neuer Spitzenreiter! {actor} verschafft sich ein Polster von {score_diff} Punkten!"
        ],
        "live_clutch_money_time": [
            "Absolute Schlussphase! Nur noch {empty_cells} Felder, jeder Fehler ist tödlich!",
            "Hochspannung! Noch {empty_cells} offene Felder, jetzt zählt absolute Nervenstärke!",
            "Das Finale naht! Nur noch {empty_cells} freie Felder auf dem Brett!",
            "Endspurt in der Arena! Noch {empty_cells} Zahlen, kein Raum für Zögern!",
            "Herzschlagfinale! {empty_cells} offene Positionen entscheiden dieses Duell!"
        ],
        "live_choke_pressure": [
            "Nervenschwäche! {actor} patzt im denkbar ungünstigsten Moment!",
            "Teurer Ausrutscher! {actor} verliert die Nerven unter Zeitdruck!",
            "Schmerzhafter Fehlgriff von {actor}! Zeitdruck fordert seinen Tribut!",
            "Fehler unter Druck! {actor} verliert den Zug an den Gegner!",
            "Die Nerven flattern bei {actor}! Große Chance für die Gegenseite!"
        ],
        "live_hot_streak": [
            "Was für ein Lauf! {actor} versenkt die Züge mit chirurgischer Präzision!",
            "Im Flow! {actor} setzt die Zahlen in rasender Geschwindigkeit!",
            "Mächtige Serie! {actor} liest das Spielfeld mit bestechender Klarheit!",
            "Tempovorstoß! {actor} dominiert das Gitter mit blitzschnellen Zügen!",
            "Volle Fahrt voraus! {actor} zündet die nächste Stufe!"
        ],
        "live_bot_provocation": [
            "Bot-Rivale KI FRAID dreht auf! Lass den Algorithmus nicht davonziehen!",
            "Der KI FRAID Bot legt vor! Jetzt muss die prompte Antwort kommen!",
            "Rechenpower pur! Der KI FRAID Bot setzt ein starkes Ausrufezeichen!",
            "Kühler Zug vom KI FRAID Bot! Jetzt ist menschliche Finesse gefragt!",
            "Der KI FRAID Bot schlägt zu! Die Arena verlangt einen Gegenschlag!"
        ]
    }
}

# Initialisation des ShuffleBags pour chaque langue et catégorie de template
SHUFFLE_BAGS: Dict[str, Dict[str, ShuffleBag]] = {}
for lang_key, categories in FALLBACK_TEMPLATES.items():
    SHUFFLE_BAGS[lang_key] = {}
    for cat_key, template_list in categories.items():
        SHUFFLE_BAGS[lang_key][cat_key] = ShuffleBag(template_list)


# ============================================================================
# Fonctions d'Arbitrage Anti-Répétition & Contrôle de Similarité
# ============================================================================

def is_text_too_similar(candidate: str, recent_history: List[str], threshold: float = 0.55) -> bool:
    """
    Vérifie si une réplique candidate est sémantiquement trop proche
    des commentaires récents du match (Jaccard similarity + préfixes identiques).
    """
    if not candidate or not recent_history:
        return False

    c_words = set(re.findall(r"\w+", candidate.lower()))
    if not c_words:
        return False

    c_words_list = candidate.lower().split()
    c_prefix = " ".join(c_words_list[:3]) if len(c_words_list) >= 3 else candidate.lower()

    for prev in recent_history:
        if not prev:
            continue
        p_words = set(re.findall(r"\w+", prev.lower()))
        if not p_words:
            continue

        p_words_list = prev.lower().split()
        p_prefix = " ".join(p_words_list[:3]) if len(p_words_list) >= 3 else prev.lower()

        # 1. Vérification des 3 premiers mots (ex: "Bienvenue dans...", "Quel duel d'anthologie...")
        if c_prefix and p_prefix and c_prefix == p_prefix:
            logger.info(f"Filtre anti-répétition : Même amorce détectée ('{c_prefix}')")
            return True

        # 2. Score de similarité de Jaccard sur les tokens
        overlap = len(c_words & p_words) / len(c_words | p_words)
        if overlap >= threshold:
            logger.info(f"Filtre anti-répétition : Similarité de Jaccard trop élevée ({overlap:.2f} >= {threshold})")
            return True

    return False


# ============================================================================
# Service Principal du Commentateur E-Sport KI FRAID
# ============================================================================

class LLMCommentatorService:
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 3.2):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.client = None
        self._init_gemini_client()

    def _init_gemini_client(self):
        if not self.api_key:
            logger.info("Aucune clé GEMINI_API_KEY détectée. Mode Fallback procédural actif.")
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

    async def generate_intro(self, req: IntroRequest) -> CommentatorResponse:
        """
        Génère une annonce d'avant-match personnalisée avec les pseudos réels et les règles.
        """
        lang = req.lang if req.lang in FALLBACK_TEMPLATES else "fr"
        text = None
        source = "fallback"

        # 1. Tentative d'appel Gemini avec timeout strict
        if self.client:
            try:
                candidate = await asyncio.wait_for(self._call_gemini_intro(req), timeout=self.timeout_seconds)
                if candidate:
                    text = candidate.strip()
                    source = "gemini"
            except Exception as e:
                logger.warning(f"Délai dépassé ou erreur Gemini intro ({repr(e)}). Utilisation du ShuffleBag.")

        # 2. Fallback procédural via ShuffleBag (rotation garantie sans répétition immédiate)
        if not text:
            bags = SHUFFLE_BAGS[lang]
            p1 = req.player1_name
            p2 = req.player2_name

            mode_label = {
                "clash": "Clash Tour par Tour" if lang == "fr" else ("Clash Turn-Based" if lang == "en" else "Rundenbasierter Clash"),
                "race": "Course Speedrun" if lang == "fr" else ("Race Speedrun" if lang == "en" else "Speedrun-Rennen"),
                "solo_ai": "Duel vs Bot Rival" if lang == "fr" else ("Duel vs Rival Bot" if lang == "en" else "Duell gegen Bot-Rivale")
            }.get(req.mode, req.mode)

            if p2 and ("bot" in p2.lower() or "fraid" in p2.lower()):
                tmpl = bags["intro_bot"].draw()
                text = tmpl.format(p1=p1, mode=mode_label)
            elif p2:
                tmpl = bags["intro_pvp"].draw()
                text = tmpl.format(p1=p1, p2=p2, mode=mode_label)
            else:
                tmpl = bags["intro_solo"].draw()
                text = tmpl.format(p1=p1)

        # 3. Synthèse Edge-TTS studio mise en cache
        audio_url = await tts_service.get_or_synthesize(text, lang=lang, rate=1.06)

        return CommentatorResponse(
            text=text,
            lang=lang,
            source=source,
            mood="hype",
            rate=1.06,
            pitch=1.00,
            audio_fallback_key="WELCOME",
            audio_url=audio_url,
            comment_id=req.comment_id
        )

    async def generate_debrief(self, req: DebriefRequest) -> CommentatorResponse:
        """
        Génère une analyse post-match e-sport fondée sur les faits calculés par le serveur.
        """
        lang = req.lang if req.lang in FALLBACK_TEMPLATES else "fr"
        text = None
        source = "fallback"

        # 1. Tentative d'appel Gemini
        if self.client:
            try:
                candidate = await asyncio.wait_for(self._call_gemini_debrief(req), timeout=self.timeout_seconds)
                if candidate:
                    text = candidate.strip()
                    source = "gemini"
            except Exception as e:
                logger.warning(f"Délai dépassé ou erreur Gemini debrief ({repr(e)}). Utilisation du ShuffleBag.")

        # 2. Fallback procédural via ShuffleBag
        if not text:
            bags = SHUFFLE_BAGS[lang]
            if req.is_draw:
                tmpl = bags["debrief_draw"].draw()
                text = tmpl.format(p1=req.winner_name, p2=req.loser_name or "Adversaire", ws=req.winner_score)
            elif req.loser_name:
                tmpl = bags["debrief_win"].draw()
                text = tmpl.format(winner=req.winner_name, loser=req.loser_name, ws=req.winner_score, combos=req.total_combos)
            else:
                tmpl = bags["debrief_solo"].draw()
                text = tmpl.format(winner=req.winner_name, ws=req.winner_score)

        # 3. Synthèse Edge-TTS studio mise en cache
        audio_url = await tts_service.get_or_synthesize(text, lang=lang, rate=1.06)

        return CommentatorResponse(
            text=text,
            lang=lang,
            source=source,
            mood="celebratory",
            rate=1.06,
            pitch=1.00,
            audio_fallback_key="VICTORY",
            audio_url=audio_url,
            comment_id=req.comment_id
        )

    async def generate_live_comment(self, req: LiveCommentRequest) -> CommentatorResponse:
        """
        Génère une intervention de commentateur e-sport en direct (Echtzeit)
        selon les événements dramatiques détectés (Money time, Remontada, Choke, Hot Streak).
        Garantit l'absence de répétition via mémoire d'historique + filtre de similarité.
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

        text = None
        source = "fallback"

        # 1. Tentative d'appel Gemini avec directive anti-répétition et timeout strict (2.2s)
        if self.client:
            try:
                candidate = await asyncio.wait_for(self._call_gemini_live(req, mood), timeout=2.2)
                if candidate:
                    clean_candidate = candidate.strip()
                    # Validation du contrôle de similarité post-génération
                    if is_text_too_similar(clean_candidate, req.recent_history):
                        logger.info(f"Commentaire Gemini rejeté car trop similaire à l'historique : '{clean_candidate}'. Utilisation de la rotation.")
                    else:
                        text = clean_candidate
                        source = "gemini"
            except Exception as e:
                logger.warning(f"Délai dépassé ou erreur Gemini live ({repr(e)}). Fallback ShuffleBag.")

        # 2. Fallback procédural via ShuffleBag (rotation garantie sans répétition immédiate)
        if not text:
            bags = SHUFFLE_BAGS[lang]
            template_keys = {
                "CLUTCH_MONEY_TIME": "live_clutch_money_time",
                "MOMENTUM_SHIFT": "live_momentum_shift",
                "HOT_STREAK": "live_hot_streak",
                "CHOKE_PRESSURE": "live_choke_pressure",
                "BOT_RIVAL_PROVOCATION": "live_bot_provocation"
            }
            template_key = template_keys.get(req.event_type, "live_momentum_shift")
            bag = bags.get(template_key, bags["live_momentum_shift"])
            
            # Tirer une phrase du deck
            tmpl = bag.draw()
            text = tmpl.format(
                actor=req.actor_name,
                score_diff=abs(round(req.score_diff, 1)),
                empty_cells=req.empty_cells,
                combo=req.combo_streak
            )

        # 3. Synthèse Edge-TTS studio mise en cache
        audio_url = await tts_service.get_or_synthesize(text, lang=lang, rate=rate)

        return CommentatorResponse(
            text=text,
            lang=lang,
            source=source,
            mood=mood,
            rate=rate,
            pitch=pitch,
            audio_fallback_key=fallback_key,
            audio_url=audio_url,
            comment_id=req.comment_id
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

    async def _call_gemini_live(self, req: LiveCommentRequest, mood: str) -> Optional[str]:
        lang_names = {"fr": "français", "en": "anglais", "de": "allemand"}
        persona = self._get_persona_instruction(req.lang)

        history_clause = ""
        if req.recent_history:
            history_clause = (
                f"\nRÉPLIQUES RÉCEMMENT PRONONCÉES DANS CE MATCH :\n" +
                "\n".join(f"- {h}" for h in req.recent_history[-4:]) +
                "\nDIRECTIVE ANTI-RÉPÉTITION ABSOLUE : Interdiction formelle de réutiliser la même structure de phrase, "
                "le même verbe d'ouverture ou les mêmes métaphores que ci-dessus. Propose une formulation totalement inédite.\n"
            )

        prompt = (
            f"{persona}\n\n"
            f"MISSION : Réagis en direct au match avec une phrase spontanée, vivante et percutante (max 16 mots).\n"
            f"Langue obligatoire : {lang_names.get(req.lang, 'français')}.\n"
            f"Événement clé : {req.event_type} | Intention/Émotion : {mood}.\n"
            f"Données de télémétrie en temps réel : Joueur actif = '{req.actor_name}', Adversaire = '{req.opponent_name or 'Rival'}', "
            f"Écart au score = {abs(round(req.score_diff, 1))} pts, Cases restantes = {req.empty_cells}, "
            f"Combos = {req.combo_streak}.\n"
            f"{history_clause}"
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
