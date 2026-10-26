/**
 * Module Internationalisation (i18n) — Sudoku Arena
 * Supporte le Français (FR), l'Anglais (EN) et l'Allemand (DE).
 */

const translations = {
    fr: {
        // En-tête & Statut
        "iot_led_title": "IOT VIRTUAL LED MATRIX — WS2812B",
        "online_status": "🟢 EN LIGNE",
        "offline_status": "🔴 HORS LIGNE",
        "connecting_status": "🟡 CONNEXION...",
        "reconnecting_status": "🟠 CONNEXION...",
        "subtitle": "PROPULSÉ PAR FRAID — BATAILLE IOT & CLOUD TEMPS RÉEL",
        "lang_switch": "Langue :",

        // Caster / Commentateur Officiel (🎙️ Caster Studio)
        "caster_title": "🎙️ KI FRAID CASTER",
        "caster_badge": "COMMENTATEUR OFFICIEL DU TOURNOI",
        "voice_on": "🔊 Voix Activée",
        "voice_off": "🔇 Voix Coupée",

        // Lobby
        "lobby_title": "🕹️ REJOINDRE L'ARÈNE",
        "your_name": "Votre Pseudo :",
        "pseudo_placeholder": "ex: NeoSolver",
        "create_room_title": "Créer un Salon Privé",
        "game_mode_label": "Mode de Jeu :",
        "mode_clash": "⚡ Clash (Tour par Tour)",
        "mode_race": "🏎️ Course (Speedrun Miroir)",
        "validation_rule_label": "Règle de Validation :",
        "val_simple": "✨ Mode Simple (Règles locales)",
        "val_strict": "🧩 Mode Casse-Tête (Solution unique)",
        "val_help_simple": "✨ Chiffres valides selon les règles Sudoku sans bloquer sur la solution finale",
        "val_help_strict": "🧩 Doit correspondre exactement à la solution finale unique",
        "clash_rule_label": "Variante de Tour (Clash) :",
        "clash_combo_capped": "⚡ Combo x2 Limité (1 coup bonus max - Recommandé)",
        "clash_strict": "🛡️ Alternance Stricte (1 coup par tour)",
        "clash_unlimited": "🔥 Série Illimitée (Tant qu'on réussit, on joue)",
        "difficulty_label": "Difficulté :",
        "diff_easy": "Facile (Chrono 30s)",
        "diff_medium": "Moyen (Chrono 20s)",
        "diff_hard": "Difficile (Chrono 10s)",
        "btn_create": "Créer le Salon 🚀",
        "join_title": "Rejoindre par Code",
        "join_desc": "Entrez le code à 4 lettres d'un ami pour rejoindre son arène multijoueur en direct.",
        "join_placeholder": "CODE (EX: K9AF)",
        "btn_join": "Rejoindre ⚔️",

        // Bot Rival en jeu (🤖 Joueur Cybernétique)
        "ai_status": "⚡ JOUEUR CYBERNÉTIQUE SUR LA GRILLE",
        "ai_title": "Duel vs KI FRAID (Bot Rival 🤖)",
        "ai_desc": "Affrontez le joueur robotique autonome sur la grille. Il calcule ses coups en temps réel selon la difficulté choisie.",
        "btn_play_ai": "Défier le Bot Rival 🤖",
        "bot_rival_name": "KI FRAID (Bot Rival 🤖)",

        // Match UI
        "room_label": "SALON :",
        "waiting_player": "En attente d'un adversaire...",
        "game_starting": "La partie va commencer...",
        "match_in_progress": "🔥 MATCH EN COURS",
        "your_turn": "⏳ À VOTRE TOUR !",
        "opponent_turn": "⏳ TOUR DE L'ADVERSAIRE",
        "opponent_turn_of": "⏳ TOUR DE",
        "turn_ai_thinking": "🧠 LE BOT RIVAL KI FRAID RÉFLÉCHIT...",
        "btn_erase": "Effacer ⌫",
        "btn_start": "Démarrer le Duel 🔥",
        "btn_leave": "Quitter 🚪",
        "p1_default": "Moi",
        "p2_default": "Adversaire",
        "not_your_turn": "⏳ Ce n'est pas votre tour !",
        "select_empty_cell": "Sélectionnez d'abord une case vide !",
        "server_disconnected": "Connexion au serveur interrompue...",

        // Modal Fin de Partie
        "victory_title": "VICTOIRE ! 🏆",
        "defeat_title": "DÉFAITE ! 💥",
        "draw_title": "ÉGALITÉ ! 🤝",
        "modal_winner_desc": "Vous avez complété la grille en premier avec brio !",
        "modal_loser_desc": "L'adversaire a remporté la manche. Préparez votre revanche !",
        "btn_rematch": "Revanche Immédiate 🔄",
        "btn_lobby": "Retour au Lobby"
    },

    en: {
        // Header & Status
        "iot_led_title": "IOT VIRTUAL LED MATRIX — WS2812B",
        "online_status": "🟢 ONLINE",
        "offline_status": "🔴 OFFLINE",
        "connecting_status": "🟡 CONNECTING...",
        "reconnecting_status": "🟠 CONNECTING...",
        "subtitle": "POWERED BY FRAID — REAL-TIME CLOUD & IOT BATTLE",
        "lang_switch": "Language:",

        // Caster / Commentator (🎙️ Broadcast Studio)
        "caster_title": "🎙️ KI FRAID CASTER",
        "caster_badge": "OFFICIAL TOURNAMENT BROADCASTER",
        "voice_on": "🔊 Voice Enabled",
        "voice_off": "🔇 Voice Muted",

        // Lobby
        "lobby_title": "🕹️ JOIN THE ARENA",
        "your_name": "Your Nickname:",
        "pseudo_placeholder": "e.g. NeoSolver",
        "create_room_title": "Create a Private Room",
        "game_mode_label": "Game Mode:",
        "mode_clash": "⚡ Clash (Turn-Based)",
        "mode_race": "🏎️ Race (Mirror Speedrun)",
        "validation_rule_label": "Validation Rule:",
        "val_simple": "✨ Simple Rules (Local row/col/box)",
        "val_strict": "🧩 Strict Puzzle (Exact unique solution)",
        "val_help_simple": "✨ Valid Sudoku placement without forcing the single puzzle end-solution",
        "val_help_strict": "🧩 Must strictly match the unique mathematical solution",
        "clash_rule_label": "Clash Turn Variant:",
        "clash_combo_capped": "⚡ Capped Combo x2 (1 bonus move max - Recommended)",
        "clash_strict": "🛡️ Strict Alternation (1 move per turn)",
        "clash_unlimited": "🔥 Unlimited Streak (Keep playing while correct)",
        "difficulty_label": "Difficulty:",
        "diff_easy": "Easy (Timer 30s)",
        "diff_medium": "Medium (Timer 20s)",
        "diff_hard": "Hard (Timer 10s)",
        "btn_create": "Create Room 🚀",
        "join_title": "Join with Code",
        "join_desc": "Enter a 4-letter room code from your rival to jump into live battle.",
        "join_placeholder": "CODE (E.G. K9AF)",
        "btn_join": "Join ⚔️",

        // Bot Rival in Game (🤖 Grid Opponent)
        "ai_status": "⚡ CYBERNETIC GRID OPPONENT",
        "ai_title": "Duel vs KI FRAID (Rival Bot 🤖)",
        "ai_desc": "Battle the autonomous grid robot. It computes its moves in real-time according to selected difficulty.",
        "btn_play_ai": "Challenge Rival Bot 🤖",
        "bot_rival_name": "KI FRAID (Rival Bot 🤖)",

        // Match UI
        "room_label": "ROOM:",
        "waiting_player": "Waiting for an opponent...",
        "game_starting": "Game is starting...",
        "match_in_progress": "🔥 MATCH IN PROGRESS",
        "your_turn": "⏳ YOUR TURN!",
        "opponent_turn": "⏳ OPPONENT'S TURN",
        "opponent_turn_of": "⏳ TURN OF",
        "turn_ai_thinking": "🧠 RIVAL BOT KI FRAID IS COMPUTING...",
        "btn_erase": "Erase ⌫",
        "btn_start": "Start Duel 🔥",
        "btn_leave": "Leave 🚪",
        "p1_default": "Me",
        "p2_default": "Rival",
        "not_your_turn": "⏳ It is not your turn!",
        "select_empty_cell": "Select an empty cell first!",
        "server_disconnected": "Server connection interrupted...",

        // Game Over Modal
        "victory_title": "VICTORY! 🏆",
        "defeat_title": "DEFEAT! 💥",
        "draw_title": "DRAW! 🤝",
        "modal_winner_desc": "You completed the grid first with stellar skill!",
        "modal_loser_desc": "Opponent took the round. Ready for a rematch?",
        "btn_rematch": "Instant Rematch 🔄",
        "btn_lobby": "Back to Lobby"
    },

    de: {
        // Header & Status
        "iot_led_title": "IOT VIRTUELLE LED-MATRIX — WS2812B",
        "online_status": "🟢 ONLINE",
        "offline_status": "🔴 OFFLINE",
        "connecting_status": "🟡 VERBINDUNG...",
        "reconnecting_status": "🟠 VERBINDUNG...",
        "subtitle": "POWERED BY FRAID — ECHTZEIT-BATTLE IM CLOUD- UND IOT-NETZ",
        "lang_switch": "Sprache:",

        // Caster / Moderator (🎙️ Broadcast Studio)
        "caster_title": "🎙️ KI FRAID CASTER",
        "caster_badge": "OFFIZIELLER TURNIER-MODERATOR",
        "voice_on": "🔊 Stimme An",
        "voice_off": "🔇 Stimme Aus",

        // Lobby
        "lobby_title": "🕹️ ARENA BETRETEN",
        "your_name": "Dein Spielername:",
        "pseudo_placeholder": "z.B. NeoSolver",
        "create_room_title": "Privaten Raum erstellen",
        "game_mode_label": "Spielmodus:",
        "mode_clash": "⚡ Clash (Rundenbasiert)",
        "mode_race": "🏎️ Rennen (Spiegel-Speedrun)",
        "validation_rule_label": "Validierungsregel:",
        "val_simple": "✨ Einfache Regeln (Lokale Validierung)",
        "val_strict": "🧩 Exakte Lösung (Einzigartige Lösung)",
        "val_help_simple": "✨ Gültige Sudoku-Regeln, ohne auf die finale Endlösung zu sperren",
        "val_help_strict": "🧩 Muss exakt der einzigartigen mathematischen Lösung entsprechen",
        "clash_rule_label": "Clash-Rundenvariante:",
        "clash_combo_capped": "⚡ Limitierter Combo x2 (Max 1 Bonuszug - Empfohlen)",
        "clash_strict": "🛡️ Strikter Wechsel (1 Zug pro Runde)",
        "clash_unlimited": "🔥 Unbegrenzte Serie (Solange du triffst, bist du am Zug)",
        "difficulty_label": "Schwierigkeit:",
        "diff_easy": "Einfach (Timer 30s)",
        "diff_medium": "Mittel (Timer 20s)",
        "diff_hard": "Schwer (Timer 10s)",
        "btn_create": "Raum erstellen 🚀",
        "join_title": "Mit Code beitreten",
        "join_desc": "Gib den 4-stelligen Raumcode eines Freundes ein, um dem Duell beizutreten.",
        "join_placeholder": "CODE (Z.B. K9AF)",
        "btn_join": "Beitreten ⚔️",

        // Bot-Gegner im Spiel (🤖 Cybernetischer Spieler auf dem Raster)
        "ai_status": "⚡ CYBERNETISCHER GEGNER AUF DEM FELD",
        "ai_title": "Duell gegen KI FRAID (Bot-Gegner 🤖)",
        "ai_desc": "Tritt gegen den autonomen Raster-Roboter an. Er berechnet Züge in Echtzeit nach gewählter Schwierigkeit.",
        "btn_play_ai": "Bot-Gegner herausfordern 🤖",
        "bot_rival_name": "KI FRAID (Bot-Gegner 🤖)",

        // Match UI
        "room_label": "RAUM:",
        "waiting_player": "Warte auf einen Gegner...",
        "game_starting": "Spiel startet gleich...",
        "match_in_progress": "🔥 MATCH LÄUFT",
        "your_turn": "⏳ DU BIST AM ZUG!",
        "opponent_turn": "⏳ GEGNER IST AM ZUG",
        "opponent_turn_of": "⏳ ZUG VON",
        "turn_ai_thinking": "🧠 DER BOT-GEGNER KI FRAID RECHNET...",
        "btn_erase": "Löschen ⌫",
        "btn_start": "Duell starten 🔥",
        "btn_leave": "Verlassen 🚪",
        "p1_default": "Ich",
        "p2_default": "Gegner",
        "not_your_turn": "⏳ Du bist nicht am Zug!",
        "select_empty_cell": "Wähle zuerst ein leeres Feld aus!",
        "server_disconnected": "Verbindung zum Server unterbrochen...",

        // Game Over Modal
        "victory_title": "SIEG! 🏆",
        "defeat_title": "NIEDERLAGE! 💥",
        "draw_title": "UNENTSCHIEDEN! 🤝",
        "modal_winner_desc": "Du hast das Raster zuerst und meisterhaft gelöst!",
        "modal_loser_desc": "Der Gegner holt sich diese Runde. Bereit für eine Revanche?",
        "btn_rematch": "Sofortige Revanche 🔄",
        "btn_lobby": "Zurück zur Lobby"
    }
};

class I18nManager {
    constructor() {
        this.currentLang = localStorage.getItem("sudoku_arena_lang") || "fr";
        if (!translations[this.currentLang]) {
            this.currentLang = "fr";
        }
    }

    t(key) {
        const langDict = translations[this.currentLang] || translations.fr;
        return langDict[key] || translations.fr[key] || key;
    }

    setLanguage(lang) {
        if (!translations[lang]) return;
        this.currentLang = lang;
        localStorage.setItem("sudoku_arena_lang", lang);
        this.updateDOM();
        window.dispatchEvent(new CustomEvent("languageChanged", { detail: { lang } }));
    }

    updateDOM() {
        document.documentElement.lang = this.currentLang;

        // Éléments avec data-i18n
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            el.textContent = this.t(key);
        });

        // Placeholders avec data-i18n-placeholder
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            const key = el.getAttribute("data-i18n-placeholder");
            el.placeholder = this.t(key);
        });
    }
}

window.i18n = new I18nManager();
