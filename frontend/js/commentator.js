/**
 * Module Commentateur Officiel — KI FRAID Caster 🎙️
 * Différencie explicitement l'arbitre/commentateur officiel (Caster) du bot rival en jeu (Bot KI FRAID).
 * Supporte le français, l'anglais et l'allemand avec un sac de tirage sans répétition (Shuffle Bag)
 * et la synthèse vocale Web Speech API native.
 */

class KIFraidCaster {
    constructor() {
        this.isVoiceEnabled = localStorage.getItem("sudoku_arena_voice") !== "false";
        this.lastPhrases = {}; // Mémorise la dernière phrase par événement pour éviter la répétition

        // Catalogue d'événements et de phrases en 3 langues (min 2 variantes par événement)
        this.catalogue = {
            fr: {
                WELCOME: [
                    "Bienvenue dans l'arène ! Prépare tes neurones, chaque coup compte !",
                    "Le public est en ébullition ! Choisis ton mode et que le meilleur gagne !"
                ],
                GAME_START: [
                    "3.. 2.. 1.. C'est parti ! Que le spectacle commence !",
                    "Début du duel ! Vitesse et rigueur seront les clés de la victoire !"
                ],
                MOVE_VALID: [
                    "Bien joué ! Chiffre validé avec précision !",
                    "Placement chirurgical ! Les points rentrent au compteur !"
                ],
                COMBO_X2: [
                    "⚡ OHHH ! COMBO x2 ! Deux coups d'affilée de toute beauté !",
                    "⚡ Le coup bonus est rentré ! Quelle vista, la pression monte !"
                ],
                MOVE_INVALID: [
                    "Aïe aïe aïe ! Erreur fatale, la main passe immédiatement !",
                    "Chiffre refusé ! Cette faute coûte cher, l'adversaire reprend la main !"
                ],
                TIMEOUT: [
                    "Trop tard ! Le chrono est tombé à zéro, tour perdu !",
                    "Temps écoulé ! Hésitation fatale, la main change de camp !"
                ],
                VICTORY: [
                    "🏆 VICTOIRE ÉCLATANTE ! Quel duel d'anthologie !",
                    "🏆 C'EST GAGNÉ ! L'arène a trouvé son véritable champion !"
                ],
                DEFEAT: [
                    "Fin du match ! La victoire s'échappe, mais une revanche s'impose !",
                    "Défaite serrée ! Belle résistance dans l'arène, relance un duel !"
                ],
                REMATCH: [
                    "C'est l'heure de la revanche ! Les compteurs sont remis à zéro !",
                    "Deuxième round immédiat ! L'honneur est en jeu !"
                ],
                VS_BOT: [
                    "🎙️ Ici KI FRAID Caster au micro ! Vous affrontez le Bot Rival KI FRAID sur la grille ! Montrez-lui votre niveau !",
                    "🎙️ Duel officiel lancé ! KI FRAID Caster aux commentaires, face au Bot Rival KI FRAID en jeu ! Donnez tout !"
                ]
            },

            en: {
                WELCOME: [
                    "Welcome to the Arena! Sharpen your mind, every move matters!",
                    "The crowd is buzzing! Pick your mode and let the battle begin!"
                ],
                GAME_START: [
                    "3.. 2.. 1.. GO! Let the battle begin!",
                    "Duel started! Speed and precision will decide the winner!"
                ],
                MOVE_VALID: [
                    "Nicely done! Number locked in with great accuracy!",
                    "Surgical placement! Points added to the scoreboard!"
                ],
                COMBO_X2: [
                    "⚡ OHHH! COMBO x2! Two consecutive hits, pure brilliance!",
                    "⚡ Bonus move nailed! What incredible momentum!"
                ],
                MOVE_INVALID: [
                    "Ouch! Bad move, the turn switches immediately!",
                    "Conflict detected! Costly mistake, opponent takes over!"
                ],
                TIMEOUT: [
                    "Time's up! Clock hit zero, turn forfeit!",
                    "Too late! Hesitation was fatal, opponent is on the move!"
                ],
                VICTORY: [
                    "🏆 GLORIOUS VICTORY! What an epic performance!",
                    "🏆 IT'S OVER! We have a true Sudoku Champion!"
                ],
                DEFEAT: [
                    "Match concluded! A tough defeat, but a rematch awaits!",
                    "Defeated on the wire! Great fight in the arena, run it back!"
                ],
                REMATCH: [
                    "Rematch accepted! Slate is wiped clean, game on!",
                    "Round two is live! Pride is on the line!"
                ],
                VS_BOT: [
                    "🎙️ KI FRAID Caster on the mic! You're facing Rival Bot KI FRAID on the grid! Show him what you've got!",
                    "🎙️ Official duel is live! KI FRAID Caster calling the shots against Rival Bot KI FRAID! Give it your all!"
                ]
            },

            de: {
                WELCOME: [
                    "Willkommen in der Arena! Schärfe deinen Verstand, jeder Zug zählt!",
                    "Das Publikum ist bereit! Wähle deinen Modus und möge der Beste gewinnen!"
                ],
                GAME_START: [
                    "3.. 2.. 1.. LOS! Möge das Duell beginnen!",
                    "Spiel gestartet! Schnelligkeit und Präzision führen zum Sieg!"
                ],
                MOVE_VALID: [
                    "Starker Zug! Zahl mit höchster Präzision platziert!",
                    "Chirurgischer Treffer! Punkte wandern auf das Konto!"
                ],
                COMBO_X2: [
                    "⚡ OHHH! COMBO x2! Zwei Treffer in Folge, fantastisch!",
                    "⚡ Der Bonuszug sitzt! Was für ein enormer Druck!"
                ],
                MOVE_INVALID: [
                    "Autsch! Ungültiger Zug, die Runde wechselt sofort!",
                    "Konflikt erkannt! Teurer Fehler, der Gegner übernimmt das Ruder!"
                ],
                TIMEOUT: [
                    "Zu spät! Die Uhr ist abgelaufen, Zug verloren!",
                    "Zeit ist um! Zögern bestraft, der Gegner ist am Zug!"
                ],
                VICTORY: [
                    "🏆 GLANZVOLLER SIEG! Was für ein Meisterstück in der Arena!",
                    "🏆 GEWONNEN! Die Arena feiert ihren Champion!"
                ],
                DEFEAT: [
                    "Spiel vorbei! Eine knappe Niederlage, Zeit für eine Revanche!",
                    "Starker Kampf, aber das Duell geht verloren. Auf zur Revanche!"
                ],
                REMATCH: [
                    "Revanche angenommen! Alles auf null, Runde zwei startet!",
                    "Sofortiges Rückspiel! Jetzt geht es um die Ehre!"
                ],
                VS_BOT: [
                    "🎙️ Hier ist KI FRAID Caster am Mikrofon! Du trittst gegen den Bot-Gegner KI FRAID an! Zeig ihm, was du kannst!",
                    "🎙️ Das offizielle Duell läuft! KI FRAID Caster moderiert gegen den Bot-Gegner KI FRAID! Gib alles!"
                ]
            }
        };
    }

    /**
     * Choisit une phrase sans répéter la même immédiatement (Shuffle Bag)
     */
    pickPhrase(eventKey, lang = "fr") {
        const langPack = this.catalogue[lang] || this.catalogue.fr;
        const phrases = langPack[eventKey] || langPack.MOVE_VALID;
        if (!phrases || phrases.length === 0) return "";

        let available = phrases.filter(p => p !== this.lastPhrases[eventKey]);
        if (available.length === 0) available = phrases;

        const chosen = available[Math.floor(Math.random() * available.length)];
        this.lastPhrases[eventKey] = chosen;
        return chosen;
    }

    /**
     * Fait réagir le commentateur (texte HUD + voix Web Speech API)
     */
    comment(eventKey, context = {}) {
        const lang = (window.i18n && window.i18n.currentLang) || "fr";
        const phrase = this.pickPhrase(eventKey, lang);
        if (!phrase) return;

        // 1. Affichage dans la bulle HUD du Caster
        this.displayHud(phrase);

        // 2. Synthèse Vocale (si activée)
        if (this.isVoiceEnabled) {
            this.speak(phrase, lang);
        }
    }

    displayHud(text) {
        const casterBubble = document.getElementById("casterSpeechBubble");
        const casterText = document.getElementById("casterSpeechText");
        if (casterBubble && casterText) {
            casterText.textContent = text;
            casterBubble.classList.remove("pop-anim");
            void casterBubble.offsetWidth; // Trigger reflow
            casterBubble.classList.add("pop-anim");
            casterBubble.classList.remove("hidden");
        }
    }

    speak(text, lang) {
        if (!("speechSynthesis" in window)) return;

        try {
            window.speechSynthesis.cancel(); // Arrêter la phrase précédente
            const utterance = new SpeechSynthesisUtterance(text);
            
            // Langue de synthèse
            const langMap = {
                fr: "fr-FR",
                en: "en-US",
                de: "de-DE"
            };
            utterance.lang = langMap[lang] || "fr-FR";
            utterance.rate = 1.08; // Rythme dynamique d'animateur e-sport
            utterance.pitch = 1.02;

            // Sélectionner la meilleure voix disponible
            const voices = window.speechSynthesis.getVoices();
            const matchingVoice = voices.find(v => v.lang.startsWith(utterance.lang.slice(0, 2)));
            if (matchingVoice) {
                utterance.voice = matchingVoice;
            }

            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.warn("SpeechSynthesis non disponible :", e);
        }
    }

    toggleVoice() {
        this.isVoiceEnabled = !this.isVoiceEnabled;
        localStorage.setItem("sudoku_arena_voice", this.isVoiceEnabled.toString());
        if (!this.isVoiceEnabled && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
        return this.isVoiceEnabled;
    }
}

window.caster = new KIFraidCaster();
