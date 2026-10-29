/**
 * Module Commentateur Officiel & Moteur Audio — KI FRAID Caster 🎙️
 * 
 * Architecture E-Sport Haute Fidélité :
 * 1. Voix HD Studio Edge-TTS unifiée (0 ms de latence, FR / EN / DE).
 * 2. Contrôleur audio unique & Arbitre de parole exclusif (zéro chevauchement de voix).
 * 3. Sac de tirage sans remise (ShuffleBag) pour variété garantie sans répétition immédiate.
 * 4. Déduplication stricte des événements WebSocket avec jeton de génération.
 * 5. Canal SFX harmonique doux indépendant du flux vocal.
 * 6. Intelligence Artificielle LLM (Google Gemini) contextualisée avec Fallback Edge-TTS / Web Speech.
 */

class ClientShuffleBag {
    /**
     * Sac de tirage sans remise (ShuffleBag / Deck épuisable côté client).
     * Garantit qu'aucune réplique ne se répète avant d'avoir vidé l'ensemble du deck,
     * et empêche les répétitions consécutives ou oscillations A-B-A-B lors du remaniement.
     */
    constructor(items = []) {
        this.items = [...items];
        this.deck = [];
        this.lastItem = null;
    }

    draw() {
        if (!this.items.length) return "";
        if (this.items.length === 1) return this.items[0];

        if (this.deck.length === 0) {
            this.deck = [...this.items];
            // Mélange de Fisher-Yates
            for (let i = this.deck.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [this.deck[i], this.deck[j]] = [this.deck[j], this.deck[i]];
            }
            // Empêche la première phrase du nouveau cycle d'être identique à la dernière tirée
            if (this.deck[this.deck.length - 1] === this.lastItem && this.deck.length > 1) {
                [this.deck[0], this.deck[this.deck.length - 1]] = [this.deck[this.deck.length - 1], this.deck[0]];
            }
        }

        const chosen = this.deck.pop();
        this.lastItem = chosen;
        return chosen;
    }
}

class KIFraidCaster {
    constructor() {
        this.isVoiceEnabled = localStorage.getItem("sudoku_arena_voice") !== "false";
        this.isSfxEnabled = localStorage.getItem("sudoku_arena_sfx") !== "false";
        this.voiceVolume = parseFloat(localStorage.getItem("sudoku_arena_voice_volume") || "0.85");
        this.sfxVolume = parseFloat(localStorage.getItem("sudoku_arena_sfx_volume") || "0.65");

        // Voix Edge-TTS officielles selon la langue
        this.defaultVoices = {
            fr: "fr-FR-HenriNeural",
            en: "en-US-GuyNeural",
            de: "de-DE-FlorianMultilingualNeural"
        };

        this.preferredVoice = localStorage.getItem("sudoku_arena_preferred_voice") || null;
        this.currentAudio = null;
        
        // Jeton d'arbitrage audio strict (monotone croissant) pour éliminer tout chevauchement
        this.currentUtteranceId = 0;
        
        // Historique de déduplication des événements reçus par WebSocket
        this.recentCommentIds = new Set();

        // Préchargement des SFX harmoniques doux (canal indépendant)
        this.sfxAudio = {
            valid: new Audio("/assets/audio/sfx/valid_chord.wav"),
            combo: new Audio("/assets/audio/sfx/combo_burst.wav"),
            error: new Audio("/assets/audio/sfx/error_soft.wav"),
            click: new Audio("/assets/audio/sfx/click_soft.wav"),
            victory: new Audio("/assets/audio/sfx/victory_chime.wav")
        };

        Object.values(this.sfxAudio).forEach(a => {
            a.volume = this.sfxVolume;
            a.preload = "auto";
        });

        // Catalogue textuel étendu multi-variantes (FR, EN, DE)
        this.catalogue = {
            fr: {
                WELCOME: [
                    "Bienvenue dans l'arène ! Prépare tes neurones, chaque coup compte !",
                    "Le public est en ébullition ! Choisis ton mode et que le meilleur gagne !",
                    "Arène sous tension ! Prépare tes chiffres et impose ton tempo !",
                    "L'arène Sudoku s'anime ! Fais parler ta logique et ton sang-froid !"
                ],
                GAME_START: [
                    "3.. 2.. 1.. C'est parti ! Que le spectacle commence !",
                    "Top départ ! Que la plus belle logique l'emporte !",
                    "La grille est ouverte ! Vitesse et rigueur exigées dès le premier coup !"
                ],
                MOVE_VALID: [
                    "Bien joué ! Chiffre validé avec précision !",
                    "Parfaitement vu ! Case verrouillée sans trembler !",
                    "Coup limpide ! La grille commence à céder !"
                ],
                COMBO_X2: [
                    "⚡ COMBO x2 ! Deux coups d'affilée, quelle vista !",
                    "⚡ Deuxième coup validé ! Le tempo s'accélère !",
                    "⚡ Enchaînement parfait ! Deux chiffres d'un trait !"
                ],
                MOVE_INVALID: [
                    "Aïe aïe aïe ! Erreur fatale, la main passe immédiatement !",
                    "Coup refusé ! La précipitation coûte cher !",
                    "Fausse piste ! L'adversaire récupère l'initiative !"
                ],
                TIMEOUT: [
                    "Temps écoulé ! Hésitation fatale, la main passe !",
                    "Chrono épuisé ! L'urgence du temps a fait la différence !"
                ],
                VICTORY: [
                    "🏆 VICTOIRE ÉCLATANTE ! L'arène a trouvé son champion !",
                    "🏆 Prestation magistrale ! Le titre est scellé !",
                    "🏆 Quel triomphe ! Grille achevée avec panache !"
                ],
                DEFEAT: [
                    "Fin du match ! Belle résistance dans l'arène, relance un duel !",
                    "Fin de manche ! L'adversaire a su saisir sa chance, place à la revanche !"
                ],
                MODE_CLASH: [
                    "Mode Clash sélectionné : tour par tour stratégique avec bonus de combo !",
                    "Arène Clash enclenchée : partage de grille, opportunisme et multiplicateur !"
                ],
                MODE_RACE: [
                    "Mode Course sélectionné : pur speedrun en miroir, que le plus rapide gagne !",
                    "Arène Course activée : aucun tour, vitesse maximale en grille miroir !"
                ],
                VS_BOT: [
                    "Duel contre l'IA Fraid ! Montre à l'algorithme ce que l'esprit humain a dans le ventre !",
                    "L'humain face au silicium : défie le Bot IA Fraid et prouve ta supériorité !"
                ]
            },
            en: {
                WELCOME: [
                    "Welcome to Sudoku Arena! Sharpen your mind, every move matters today!",
                    "The crowd is ready! Pick your mode and may the sharpest mind win!",
                    "High voltage arena! Lock in your focus and control the board tempo!",
                    "Welcome gladiators! Logical brilliance and iron nerves required!"
                ],
                GAME_START: [
                    "3.. 2.. 1.. GO! Let the battle begin!",
                    "Match is live! Pure logic and swift fingers!",
                    "The grid is open! First digit sets the tone!"
                ],
                MOVE_VALID: [
                    "Well played! Number locked in with precision!",
                    "Clean placement! Spot on deduction!",
                    "Crisp deduction! The board is opening up!"
                ],
                COMBO_X2: [
                    "⚡ COMBO x2! Two consecutive hits, pure brilliance!",
                    "⚡ Double hit! Blistering pace on the grid!",
                    "⚡ Back-to-back validations! Flow state engaged!"
                ],
                MOVE_INVALID: [
                    "Ouch, invalid move! Costly mistake, opponent takes over!",
                    "Rejected! Rushing the clock hurts in this duel!",
                    "Trap triggered! Initiative handed right back!"
                ],
                TIMEOUT: [
                    "Time is up! Fatal hesitation, turn lost!",
                    "Clock ran out! Seconds can make or break a championship!"
                ],
                VICTORY: [
                    "🏆 SPECTACULAR VICTORY! We have a true Sudoku Champion!",
                    "🏆 Masterclass performance! The crown belongs to the victor!",
                    "🏆 Triumph in the arena! Finished with style!"
                ],
                DEFEAT: [
                    "Match over! Great effort in the arena, challenge for a rematch!",
                    "Final whistle! Your opponent took the upper hand, go for the rematch!"
                ],
                MODE_CLASH: [
                    "Clash Mode selected: turn-based strategy with combo multipliers!",
                    "Clash arena ready: shared board tactical warfare with bonus streaks!"
                ],
                MODE_RACE: [
                    "Race Mode selected: pure mirror speedrun, first to finish wins!",
                    "Race arena active: zero turns, flat-out sprint to the final cell!"
                ],
                VS_BOT: [
                    "Duel against AI Fraid! Show the cybernetic bot what human intellect can do!",
                    "Human vs AI showdown: test your speed against the AI Fraid Bot!"
                ]
            },
            de: {
                WELCOME: [
                    "Willkommen in der Sudoku Arena! Schärfe deinen Verstand, heute zählt jeder Zug!",
                    "Die Arena kocht! Wähle deinen Modus und möge die Logik siegen!",
                    "Hochspannung im Gitter! Volle Konzentration für dieses Match!",
                    "Willkommen Denk-Gladiatoren! Präzision und Nervenstärke sind gefragt!"
                ],
                GAME_START: [
                    "3.. 2.. 1.. LOS! Möge das Duell beginnen!",
                    "Start frei! Möge der schärfste Verstand triumphieren!",
                    "Das Spiel läuft! Präzision ab der ersten Zahl!"
                ],
                MOVE_VALID: [
                    "Gut gespielt! Zahl mit Präzision gesetzt!",
                    "Hervorragend erkannt! Zahl sitzt felsenfest!",
                    "Scharfer Blick! Das Gitter öffnet sich!"
                ],
                COMBO_X2: [
                    "⚡ COMBO x2! Zwei Treffer in Folge, meisterhaft!",
                    "⚡ Doppelter Treffer! Das Tempo zieht an!",
                    "⚡ Perfekte Serie! Zwei Zahlen in rasanter Folge!"
                ],
                MOVE_INVALID: [
                    "Autsch! Ungültiger Zug, die Runde wechselt sofort!",
                    "Fehlgriff! Hektik rächt sich im Duell sofort!",
                    "Falsche Zahl! Der Gegner übernimmt die Initiative!"
                ],
                TIMEOUT: [
                    "Zeit abgelaufen! Zu lange gezögert, der Zug ist verloren!",
                    "Die Uhr tickt gnadenlos! Runde kampflos abgegeben!"
                ],
                VICTORY: [
                    "🏆 GLANZVOLLER SIEG! Die Arena feiert ihren Champion!",
                    "🏆 Meisterleistung! Ein absolut verdienter Triumph!",
                    "🏆 Jubel in der Arena! Großartiges Finish!"
                ],
                DEFEAT: [
                    "Spiel vorbei! Stark gekämpft, fordere eine Revanche!",
                    "Runde beendet! Der Gegner nutzte seine Chance, Zeit für die Revanche!"
                ],
                MODE_CLASH: [
                    "Clash-Modus gewählt: rundenbasierte Strategie mit Combo-Multiplikator!",
                    "Clash-Arena aktiv: Gemeinsames Gitter mit taktischen Combo-Boni!"
                ],
                MODE_RACE: [
                    "Renn-Modus gewählt: reines Spiegel-Speedrun, wer zuerst löst, gewinnt!",
                    "Renn-Arena aktiv: Reiner Geschwindigkeitsrausch im Spiegelgitter!"
                ],
                VS_BOT: [
                    "Duell gegen KI Fraid! Zeige dem Algorithmus, was der menschliche Verstand leisten kann!",
                    "Mensch gegen Maschine: Fordere den KI Fraid Bot heraus!"
                ]
            }
        };

        // Initialisation des sacs de tirage sans remise pour chaque événement et chaque langue
        this.shuffleBags = { fr: {}, en: {}, de: {} };
        Object.keys(this.catalogue).forEach(lang => {
            Object.keys(this.catalogue[lang]).forEach(evt => {
                this.shuffleBags[lang][evt] = new ClientShuffleBag(this.catalogue[lang][evt]);
            });
        });
    }

    /**
     * Récupère l'ID de voix Edge-TTS actif selon la langue
     */
    getActiveVoiceId(lang = "fr") {
        try {
            const saved = localStorage.getItem("sudoku_arena_preferred_voices");
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed && parsed[lang]) return parsed[lang];
            }
        } catch (e) {}

        if (this.preferredVoice) return this.preferredVoice;
        return this.defaultVoices[lang] || this.defaultVoices.fr;
    }

    /**
     * Joue un effet sonore doux (SFX) totalement indépendant du flux vocal
     */
    playSfx(type) {
        if (!this.isSfxEnabled) return;
        const sound = this.sfxAudio[type] || this.sfxAudio.valid;
        if (!sound) return;

        try {
            const clone = sound.cloneNode();
            clone.volume = this.sfxVolume;
            clone.play().catch(() => {});
        } catch (e) {}
    }

    playSfxByFrequency(frequency) {
        if (frequency <= 250) {
            this.playSfx("error");
        } else if (frequency >= 800) {
            this.playSfx("combo");
        } else {
            this.playSfx("valid");
        }
    }

    /**
     * Choisit une phrase via ShuffleBag (rotation garantie sans répétition immédiate)
     */
    pickPhrase(eventKey, lang = "fr") {
        const langPack = this.shuffleBags[lang] || this.shuffleBags.fr;
        const bag = langPack[eventKey] || langPack.WELCOME;
        if (bag && typeof bag.draw === "function") {
            return bag.draw();
        }
        return "";
    }

    /**
     * Réaction vocale et textuelle du Commentateur officiel
     */
    comment(eventKey, context = {}) {
        const lang = (window.i18n && window.i18n.currentLang) || "fr";
        const phrase = context.text || this.pickPhrase(eventKey, lang);

        this.displayHud(phrase);

        if (this.isVoiceEnabled) {
            this.playVoice(eventKey, lang, phrase);
        }
    }

    /**
     * Stoppe immédiatement et strictement toute voix en cours
     * Incrémente le jeton d'arbitrage pour invalider toute opération différée.
     */
    stopAllVoice() {
        this.currentUtteranceId++;

        if (this.currentAudio) {
            try {
                this.currentAudio.onended = null;
                this.currentAudio.onerror = null;
                this.currentAudio.pause();
                this.currentAudio.currentTime = 0;
            } catch (e) {}
            this.currentAudio = null;
        }

        if ("speechSynthesis" in window) {
            try {
                window.speechSynthesis.cancel();
            } catch (e) {}
        }

        document.dispatchEvent(new CustomEvent("caster:speak:end"));
    }

    /**
     * Réinitialise la session de match pour le commentateur
     */
    resetMatchSession() {
        this.stopAllVoice();
        this.recentCommentIds.clear();
        const casterBubble = document.getElementById("casterSpeechBubble");
        if (casterBubble) casterBubble.classList.add("hidden");
    }

    /**
     * Joue un fichier audio studio par URL avec contrôle strict d'arbitre unique
     */
    playAudioUrl(audioUrl, fallbackText = "", lang = "fr", fallbackEventKey = "MOVE_VALID") {
        this.stopAllVoice();
        const utteranceId = ++this.currentUtteranceId;

        const audio = new Audio(audioUrl);
        audio.volume = this.voiceVolume;
        this.currentAudio = audio;

        document.dispatchEvent(new CustomEvent("caster:speak:start"));

        audio.onended = () => {
            if (this.currentUtteranceId !== utteranceId) return;
            this.currentAudio = null;
            document.dispatchEvent(new CustomEvent("caster:speak:end"));
        };

        audio.onerror = () => {
            if (this.currentUtteranceId !== utteranceId) return;
            this.currentAudio = null;
            document.dispatchEvent(new CustomEvent("caster:speak:end"));
            // En cas d'erreur de chargement de l'URL, tenter le clip studio standard ou WebSpeech
            if (fallbackEventKey && this.catalogue[lang] && this.catalogue[lang][fallbackEventKey]) {
                this.playVoice(fallbackEventKey, lang, fallbackText, utteranceId);
            } else if (fallbackText) {
                this.speakWebSpeech(fallbackText, lang, {}, utteranceId);
            }
        };

        audio.play().catch(() => {
            if (this.currentUtteranceId !== utteranceId) return;
            if (fallbackText) {
                this.speakWebSpeech(fallbackText, lang, {}, utteranceId);
            }
        });
    }

    /**
     * Joue l'échantillon HD Edge-TTS pré-généré du catalogue studio
     */
    playVoice(eventKey, lang = "fr", fallbackText = "", existingUtteranceId = null) {
        if (!existingUtteranceId) {
            this.stopAllVoice();
        }
        const utteranceId = existingUtteranceId || ++this.currentUtteranceId;

        const voiceId = this.getActiveVoiceId(lang);
        const audioUrl = `/assets/audio/benchmark/${lang}/${voiceId}/${eventKey}.mp3`;

        const audio = new Audio(audioUrl);
        audio.volume = this.voiceVolume;
        this.currentAudio = audio;

        document.dispatchEvent(new CustomEvent("caster:speak:start"));

        audio.onended = () => {
            if (this.currentUtteranceId !== utteranceId) return;
            this.currentAudio = null;
            document.dispatchEvent(new CustomEvent("caster:speak:end"));
        };

        audio.onerror = () => {
            if (this.currentUtteranceId !== utteranceId) return;
            this.currentAudio = null;
            document.dispatchEvent(new CustomEvent("caster:speak:end"));
            if (fallbackText) {
                this.speakWebSpeech(fallbackText, lang, {}, utteranceId);
            }
        };

        audio.play().catch(() => {
            if (this.currentUtteranceId !== utteranceId) return;
            if (fallbackText) {
                this.speakWebSpeech(fallbackText, lang, {}, utteranceId);
            }
        });
    }

    /**
     * Appel à l'IA Gemini pour une annonce d'avant-match contextualisée
     */
    async commentIntro(ctx) {
        const lang = ctx.lang || (window.i18n && window.i18n.currentLang) || "fr";
        const payload = {
            player1_name: ctx.player1 || "Joueur 1",
            player2_name: ctx.player2 || null,
            mode: ctx.mode || "clash",
            clash_rule: ctx.clashRule || "combo_capped",
            lang: lang,
            comment_id: `intro_${Date.now()}`
        };

        try {
            const resp = await fetch("/api/commentator/intro", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                const data = await resp.json();
                this.displayHud(data.text);

                if (this.isVoiceEnabled) {
                    // Priorité 1 : Fichier Edge-TTS studio synthétisé côté serveur
                    if (data.audio_url) {
                        this.playAudioUrl(data.audio_url, data.text, lang, "WELCOME");
                    } else if (data.source === "gemini") {
                        this.speakWebSpeech(data.text, lang, { rate: data.rate || 1.06 });
                    } else {
                        this.playVoice("WELCOME", lang, data.text);
                    }
                }
                return;
            }
        } catch (e) {
            console.warn("Commentator LLM intro offline, using standard voice:", e);
        }

        this.comment("WELCOME");
    }

    /**
     * Appel à l'IA Gemini pour un débriefing e-sport d'après-match fondé sur les stats réelles
     */
    async commentDebrief(ctx) {
        const lang = ctx.lang || (window.i18n && window.i18n.currentLang) || "fr";
        const payload = {
            winner_name: ctx.winner || "Champion",
            loser_name: ctx.loser || null,
            winner_score: ctx.winnerScore || 0,
            loser_score: ctx.loserScore || 0,
            is_draw: Boolean(ctx.isDraw),
            total_combos: ctx.totalCombos || 0,
            duration_seconds: ctx.duration || 0,
            mode: ctx.mode || "clash",
            lang: lang,
            comment_id: `debrief_${Date.now()}`
        };

        try {
            const resp = await fetch("/api/commentator/debrief", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                const data = await resp.json();
                this.displayHud(data.text);
                if (typeof ctx.onDebriefReady === "function") {
                    ctx.onDebriefReady(data.text);
                }

                if (this.isVoiceEnabled) {
                    const fallbackClip = ctx.isWinner ? "VICTORY" : "DEFEAT";
                    if (data.audio_url) {
                        this.playAudioUrl(data.audio_url, data.text, lang, fallbackClip);
                    } else if (data.source === "gemini") {
                        this.speakWebSpeech(data.text, lang, { rate: data.rate || 1.06 });
                    } else {
                        this.playVoice(fallbackClip, lang, data.text);
                    }
                }
                return;
            }
        } catch (e) {
            console.warn("Commentator LLM debrief offline, using standard voice:", e);
        }

        this.comment(ctx.isWinner ? "VICTORY" : "DEFEAT");
    }

    /**
     * Traite une intervention de commentateur e-sport en direct (diffusée par WebSocket)
     * Déduplication absolue et voix studio Edge-TTS prioritaire.
     */
    handleLiveComment(comment) {
        if (!comment || !comment.text) return;

        // Déduplication de message WebSocket pour empêcher les doubles lectures
        if (comment.comment_id) {
            if (this.recentCommentIds.has(comment.comment_id)) {
                return;
            }
            this.recentCommentIds.add(comment.comment_id);
            if (this.recentCommentIds.size > 50) {
                const first = this.recentCommentIds.values().next().value;
                this.recentCommentIds.delete(first);
            }
        }

        const lang = comment.lang || (window.i18n && window.i18n.currentLang) || "fr";

        // 1. Afficher dans la bulle HUD avec effet de pop
        this.displayHud(comment.text);

        // 2. Vocalisation exclusive sans chevauchement
        if (this.isVoiceEnabled) {
            if (comment.audio_url) {
                // Synthèse Edge-TTS studio disponible depuis le backend
                this.playAudioUrl(comment.audio_url, comment.text, lang, comment.audio_fallback_key || "COMBO_X2");
            } else if (comment.source !== "gemini" && comment.audio_fallback_key) {
                // Clip audio studio pré-généré du catalogue
                this.playVoice(comment.audio_fallback_key, lang, comment.text);
            } else {
                // Repli WebSpeech avec contrôle de pitch et rate
                this.speakWebSpeech(comment.text, lang, {
                    rate: comment.rate || 1.12,
                    pitch: comment.pitch || 1.02
                });
            }
        }
    }

    /**
     * Vocalise et affiche une explication pédagogique d'un paramètre ou d'une option
     */
    explainSetting(text) {
        if (!text) return;
        const lang = (window.i18n && window.i18n.currentLang) || "fr";
        this.displayHud(text);
        if (this.isVoiceEnabled) {
            this.speakWebSpeech(text, lang, { rate: 1.08 });
        }
    }

    displayHud(text) {
        const casterBubble = document.getElementById("casterSpeechBubble");
        const casterText = document.getElementById("casterSpeechText");
        if (casterBubble && casterText) {
            casterText.textContent = text;
            casterBubble.classList.remove("pop-anim");
            void casterBubble.offsetWidth;
            casterBubble.classList.add("pop-anim");
            casterBubble.classList.remove("hidden");
        }
    }

    normalizeForSpeech(text, lang = "fr") {
        if (!text) return "";
        let clean = text.replace(/[\*\_\#\`\"]/g, "").replace(/\s+/g, " ").trim();
        if (lang === "fr") {
            clean = clean.replace(/\bKI\s+FRAID\b/gi, "l'IA Fraid");
            clean = clean.replace(/\bBOT\s+IA\s+FRAID\b/gi, "le Bot IA Fraid");
            clean = clean.replace(/\bIA\s+FRAID\b/gi, "l'IA Fraid");
            clean = clean.replace(/\bFRAID\b/g, "Fraid");
        } else if (lang === "en") {
            clean = clean.replace(/\bKI\s+FRAID\b/gi, "AI Fraid");
            clean = clean.replace(/\bFRAID\b/g, "Fraid");
        } else {
            clean = clean.replace(/\bFRAID\b/g, "Fraid");
        }
        clean = clean.replace(/\b[A-Z]{4,}\b/g, (w) => w.charAt(0) + w.slice(1).toLowerCase());
        return clean;
    }

    speakWebSpeech(text, lang = "fr", opts = {}, existingUtteranceId = null) {
        if (!("speechSynthesis" in window)) return;
        if (!existingUtteranceId) {
            this.stopAllVoice();
        }
        const utteranceId = existingUtteranceId || ++this.currentUtteranceId;
        const speechText = this.normalizeForSpeech(text, lang);

        try {
            const utterance = new SpeechSynthesisUtterance(speechText);
            const langMap = { fr: "fr-FR", en: "en-US", de: "de-DE" };
            utterance.lang = langMap[lang] || "fr-FR";
            utterance.rate = opts.rate || 1.06;
            utterance.pitch = opts.pitch || 1.0;

            utterance.onstart = () => {
                if (this.currentUtteranceId !== utteranceId) return;
                document.dispatchEvent(new CustomEvent("caster:speak:start"));
            };
            utterance.onend = () => {
                if (this.currentUtteranceId !== utteranceId) return;
                document.dispatchEvent(new CustomEvent("caster:speak:end"));
            };
            utterance.onerror = () => {
                if (this.currentUtteranceId !== utteranceId) return;
                document.dispatchEvent(new CustomEvent("caster:speak:end"));
            };

            const voices = window.speechSynthesis.getVoices();
            const langPrefix = utterance.lang.slice(0, 2).toLowerCase();
            const matching = voices.filter(v => v.lang && v.lang.toLowerCase().startsWith(langPrefix));
            // Privilégier les voix neurales / naturelles / online / google pour une diction ultra-réaliste
            const premium = matching.find(v => /natural|neural|online|google/i.test(v.name));
            utterance.voice = premium || matching[0] || null;

            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.warn("SpeechSynthesis error:", e);
        }
    }

    toggleVoice() {
        this.isVoiceEnabled = !this.isVoiceEnabled;
        localStorage.setItem("sudoku_arena_voice", this.isVoiceEnabled.toString());
        if (!this.isVoiceEnabled) {
            this.stopAllVoice();
        }
        return this.isVoiceEnabled;
    }

    toggleSfx() {
        this.isSfxEnabled = !this.isSfxEnabled;
        localStorage.setItem("sudoku_arena_sfx", this.isSfxEnabled.toString());
        return this.isSfxEnabled;
    }

    setPreferredVoice(voiceId) {
        this.preferredVoice = voiceId;
        localStorage.setItem("sudoku_arena_preferred_voice", voiceId);
    }
}

// Instance globale singleton
window.caster = new KIFraidCaster();
