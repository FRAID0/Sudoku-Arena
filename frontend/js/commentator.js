/**
 * Module Commentateur Officiel & Moteur Audio — KI FRAID Caster 🎙️
 * 
 * Intègre :
 * 1. Voix HD Edge-TTS pré-générées (0 ms de latence, FR / EN / DE).
 * 2. Effets Sonores Harmoniques doux (WAV feutrés sans bips stridents).
 * 3. Intelligence Artificielle LLM (Google Gemini) pour Intros & Débriefings e-sport contextualisés.
 * 4. Fallback transparent vers Web Speech API si réseau indisponible.
 */

class KIFraidCaster {
    constructor() {
        this.isVoiceEnabled = localStorage.getItem("sudoku_arena_voice") !== "false";
        this.isSfxEnabled = localStorage.getItem("sudoku_arena_sfx") !== "false";
        this.voiceVolume = parseFloat(localStorage.getItem("sudoku_arena_voice_volume") || "0.85");
        this.sfxVolume = parseFloat(localStorage.getItem("sudoku_arena_sfx_volume") || "0.65");

        // Voix Edge-TTS par défaut selon la langue
        this.defaultVoices = {
            fr: "fr-FR-HenriNeural",
            en: "en-US-GuyNeural",
            de: "de-DE-FlorianMultilingualNeural"
        };

        this.preferredVoice = localStorage.getItem("sudoku_arena_preferred_voice") || null;
        this.currentAudio = null;
        this.lastPhrases = {};

        // Préchargement des SFX doux
        this.sfxAudio = {
            valid: new Audio("/assets/audio/sfx/valid_chord.wav"),
            combo: new Audio("/assets/audio/sfx/combo_burst.wav"),
            error: new Audio("/assets/audio/sfx/error_soft.wav"),
            click: new Audio("/assets/audio/sfx/click_soft.wav"),
            victory: new Audio("/assets/audio/sfx/victory_chime.wav")
        };

        // Configuration volume initiale des SFX
        Object.values(this.sfxAudio).forEach(a => {
            a.volume = this.sfxVolume;
            a.preload = "auto";
        });

        // Catalogue textuel de repli et de sous-titres HUD (3 langues)
        this.catalogue = {
            fr: {
                WELCOME: [
                    "Bienvenue dans l'arène ! Prépare tes neurones, chaque coup compte !",
                    "Le public est en ébullition ! Choisis ton mode et que le meilleur gagne !"
                ],
                GAME_START: [
                    "3.. 2.. 1.. C'est parti ! Que le spectacle commence !"
                ],
                MOVE_VALID: [
                    "Bien joué ! Chiffre validé avec précision !"
                ],
                COMBO_X2: [
                    "⚡ COMBO x2 ! Deux coups d'affilée, quelle vista !"
                ],
                MOVE_INVALID: [
                    "Aïe aïe aïe ! Erreur fatale, la main passe immédiatement !"
                ],
                TIMEOUT: [
                    "Temps écoulé ! Hésitation fatale, la main passe !"
                ],
                VICTORY: [
                    "🏆 VICTOIRE ÉCLATANTE ! L'arène a trouvé son champion !"
                ],
                DEFEAT: [
                    "Fin du match ! Belle résistance dans l'arène, relance un duel !"
                ],
                MODE_CLASH: [
                    "Mode Clash sélectionné : tour par tour stratégique avec bonus de combo !"
                ],
                MODE_RACE: [
                    "Mode Course sélectionné : pur speedrun en miroir, que le plus rapide gagne !"
                ],
                VS_BOT: [
                    "Duel contre l'IA FRAID ! Montre à l'algorithme ce que l'esprit humain a dans le ventre !"
                ]
            },
            en: {
                WELCOME: [
                    "Welcome to Sudoku Arena! Sharpen your mind, every move matters today!"
                ],
                GAME_START: [
                    "3.. 2.. 1.. GO! Let the battle begin!"
                ],
                MOVE_VALID: [
                    "Well played! Number locked in with precision!"
                ],
                COMBO_X2: [
                    "⚡ COMBO x2! Two consecutive hits, pure brilliance!"
                ],
                MOVE_INVALID: [
                    "Ouch, invalid move! Costly mistake, opponent takes over!"
                ],
                TIMEOUT: [
                    "Time is up! Fatal hesitation, turn lost!"
                ],
                VICTORY: [
                    "🏆 SPECTACULAR VICTORY! We have a true Sudoku Champion!"
                ],
                DEFEAT: [
                    "Match over! Great effort in the arena, challenge for a rematch!"
                ],
                MODE_CLASH: [
                    "Clash Mode selected: turn-based strategy with combo multipliers!"
                ],
                MODE_RACE: [
                    "Race Mode selected: pure mirror speedrun, first to finish wins!"
                ],
                VS_BOT: [
                    "Duel against AI FRAID! Show the cybernetic bot what human intellect can do!"
                ]
            },
            de: {
                WELCOME: [
                    "Willkommen in der Sudoku Arena! Schärfe deinen Verstand, heute zählt jeder Zug!"
                ],
                GAME_START: [
                    "3.. 2.. 1.. LOS! Möge das Duell beginnen!"
                ],
                MOVE_VALID: [
                    "Gut gespielt! Zahl mit Präzision gesetzt!"
                ],
                COMBO_X2: [
                    "⚡ COMBO x2! Zwei Treffer in Folge, meisterhaft!"
                ],
                MOVE_INVALID: [
                    "Autsch! Ungültiger Zug, die Runde wechselt sofort!"
                ],
                TIMEOUT: [
                    "Zeit abgelaufen! Zu lange gezögert, der Zug ist verloren!"
                ],
                VICTORY: [
                    "🏆 GLANZVOLLER SIEG! Die Arena feiert ihren Champion!"
                ],
                DEFEAT: [
                    "Spiel vorbei! Stark gekämpft, fordere eine Revanche!"
                ],
                MODE_CLASH: [
                    "Clash-Modus gewählt: rundenbasierte Strategie mit Combo-Multiplikator!"
                ],
                MODE_RACE: [
                    "Renn-Modus gewählt: reines Spiegel-Speedrun, wer zuerst löst, gewinnt!"
                ],
                VS_BOT: [
                    "Duell gegen KI FRAID! Zeige dem Algorithmus, was der menschliche Verstand leisten kann!"
                ]
            }
        };
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
     * Joue un effet sonore doux (SFX) sans agressivité
     */
    playSfx(type) {
        if (!this.isSfxEnabled) return;
        const sound = this.sfxAudio[type] || this.sfxAudio.valid;
        if (!sound) return;

        try {
            // Cloner le nœud audio pour permettre les sons superposés rapides sans coupure
            const clone = sound.cloneNode();
            clone.volume = this.sfxVolume;
            clone.play().catch(() => {});
        } catch (e) {
            // Ignorer silencieusement si bloqué par autoplay
        }
    }

    /**
     * Remplace les anciens bips stridents par les SFX doux selon la fréquence
     */
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
     * Choisit une phrase sans répétition immédiate
     */
    pickPhrase(eventKey, lang = "fr") {
        const langPack = this.catalogue[lang] || this.catalogue.fr;
        const phrases = langPack[eventKey] || langPack.WELCOME || [];
        if (!phrases || phrases.length === 0) return "";

        let available = phrases.filter(p => p !== this.lastPhrases[eventKey]);
        if (available.length === 0) available = phrases;

        const chosen = available[Math.floor(Math.random() * available.length)];
        this.lastPhrases[eventKey] = chosen;
        return chosen;
    }

    /**
     * Réaction vocale et textuelle du Commentateur officiel
     */
    comment(eventKey, context = {}) {
        const lang = (window.i18n && window.i18n.currentLang) || "fr";
        const phrase = context.text || this.pickPhrase(eventKey, lang);

        // 1. Afficher dans la bulle HUD du Caster
        this.displayHud(phrase);

        // 2. Jouer la voix HD si activée
        if (this.isVoiceEnabled) {
            this.playVoice(eventKey, lang, phrase);
        }
    }

    /**
     * Stoppe immédiatement toute parole en cours (Audio HTML5 et WebSpeech API)
     * Empêche strictement tout chevauchement ou double commentateur simultané.
     */
    stopAllVoice() {
        if (this.currentAudio) {
            try {
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
     * Joue l'échantillon HD Edge-TTS pré-généré (avec repli Web Speech API si manquant)
     */
    playVoice(eventKey, lang = "fr", fallbackText = "") {
        // Arrêter strictement toute voix en cours
        this.stopAllVoice();

        const voiceId = this.getActiveVoiceId(lang);
        const audioUrl = `/assets/audio/benchmark/${lang}/${voiceId}/${eventKey}.mp3`;

        const audio = new Audio(audioUrl);
        audio.volume = this.voiceVolume;
        this.currentAudio = audio;

        document.dispatchEvent(new CustomEvent("caster:speak:start"));

        audio.onended = () => {
            this.currentAudio = null;
            document.dispatchEvent(new CustomEvent("caster:speak:end"));
        };

        audio.onerror = () => {
            // Si le fichier MP3 n'est pas trouvé (ex: phrase dynamique LLM), repli vers Web Speech
            this.currentAudio = null;
            document.dispatchEvent(new CustomEvent("caster:speak:end"));
            if (fallbackText) {
                this.speakWebSpeech(fallbackText, lang);
            }
        };

        audio.play().catch(() => {
            // Bloqué par les politiques de navigateur ou fichier indisponible
            if (fallbackText) {
                this.speakWebSpeech(fallbackText, lang);
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
            lang: lang
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
                    if (data.source === "gemini") {
                        // Phrase unique créée sur-mesure par l'IA : lue via synthèse vocale dynamique
                        this.speakWebSpeech(data.text, lang);
                    } else {
                        // Repli procédural : joue le MP3 HD studio WELCOME
                        this.playVoice("WELCOME", lang, data.text);
                    }
                }
                return;
            }
        } catch (e) {
            console.warn("Commentator LLM intro offline, using standard voice:", e);
        }

        // Repli par défaut
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
            lang: lang
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

                if (this.isVoiceEnabled) {
                    if (data.source === "gemini") {
                        this.speakWebSpeech(data.text, lang);
                    } else {
                        const clip = ctx.isWinner ? "VICTORY" : "DEFEAT";
                        this.playVoice(clip, lang, data.text);
                    }
                }
                return;
            }
        } catch (e) {
            console.warn("Commentator LLM debrief offline, using standard voice:", e);
        }

        // Repli par défaut
        this.comment(ctx.isWinner ? "VICTORY" : "DEFEAT");
    }

    /**
     * Traite une intervention de commentateur e-sport en direct (diffusée par WebSocket)
     */
    handleLiveComment(comment) {
        if (!comment || !comment.text) return;
        const lang = comment.lang || (window.i18n && window.i18n.currentLang) || "fr";

        // 1. Afficher dans la bulle HUD avec effet de pop
        this.displayHud(comment.text);

        // 2. Si la voix est activée, vocaliser avec le mood, débit (rate) et hauteur (pitch)
        if (this.isVoiceEnabled) {
            if (comment.source === "gemini") {
                this.speakWebSpeech(comment.text, lang, {
                    rate: comment.rate || 1.12,
                    pitch: comment.pitch || 1.02
                });
            } else if (comment.audio_fallback_key) {
                this.playVoice(comment.audio_fallback_key, lang, comment.text);
            }
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

    speakWebSpeech(text, lang = "fr", opts = {}) {
        if (!("speechSynthesis" in window)) return;
        this.stopAllVoice();

        try {
            const utterance = new SpeechSynthesisUtterance(text);
            const langMap = { fr: "fr-FR", en: "en-US", de: "de-DE" };
            utterance.lang = langMap[lang] || "fr-FR";
            utterance.rate = opts.rate || 1.06;
            utterance.pitch = opts.pitch || 1.0;

            utterance.onstart = () => {
                document.dispatchEvent(new CustomEvent("caster:speak:start"));
            };
            utterance.onend = () => {
                document.dispatchEvent(new CustomEvent("caster:speak:end"));
            };
            utterance.onerror = () => {
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
