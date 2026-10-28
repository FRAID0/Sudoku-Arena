/**
 * Sudoku Arena — Frontend Game Engine & WebSocket Client
 * Gère le décompte synchrone, le mode Clash (Tour par Tour), le mode Course,
 * le bot KI FRAID, l'audio synthétique, le ruban LED IoT, l'accessibilité clavier,
 * la robustesse WebSocket et la validation duale (Simple vs Casse-Tête).
 */

// Audio Web synthétique (sans fichier externe)
let audioCtx = null;
function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtx;
}

function playBeep(frequency = 440, duration = 0.15) {
    // Remplacement par les SFX harmoniques feutrés
    if (window.caster && typeof window.caster.playSfxByFrequency === "function") {
        window.caster.playSfxByFrequency(frequency);
        return;
    }
    try {
        const ctx = getAudioContext();
        if (ctx.state === "suspended") ctx.resume();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = frequency;
        osc.connect(gain);
        gain.connect(ctx.destination);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
        osc.start();
        osc.stop(ctx.currentTime + duration);
    } catch (e) {
        // Fallback silencieux si l'audio est restreint par le navigateur
    }
}

// Détection dynamique et flexible de l'URL du Backend :
// - Surcharge via query param : ?backend=...
// - En local (localhost / 127.0.0.1) : utilise le proxy local / Nginx
// - En production (Vercel, etc.) : utilise le cluster Northflank en HTTPS/WSS
const urlParams = new URLSearchParams(window.location.search);
const customBackend = urlParams.get("backend");
const IS_LOCAL = !customBackend && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
const BACKEND_HOST = customBackend || (IS_LOCAL ? window.location.host : "p01--sudoku-backend--hvzj8dcpgjs4.code.run");
const API_BASE_URL = customBackend ? `https://${customBackend}` : (IS_LOCAL ? "" : `https://${BACKEND_HOST}`);

// État de l'application
const state = {
    playerId: "player_" + Math.random().toString(36).substring(2, 9),
    playerName: (window.i18n ? i18n.t("default_player_name") : "Joueur 1"),
    roomCode: null,
    isHost: false,
    mode: "clash", // "clash" | "race" | "solo_ai"
    difficulty: "medium",
    validationMode: "simple", // "simple" | "strict"
    selectedCell: null,
    grid: null,
    socket: null,
    isAiMatch: false,
    currentTurn: null,
    turnTimeout: 20.0,
    timerInterval: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,
    reconnectTimeout: null,
    // Statistiques E-Sport du match en direct
    matchStartTime: null,
    matchDurationSeconds: 0,
    validMovesCount: 0,
    errorMovesCount: 0,
    currentComboStreak: 0,
    maxComboStreak: 0,
    lastDebriefText: "",
    // Mode Spectateur & Hype
    isSpectator: false,
    spectatorCount: 0,
    hypeScore: 50
};

// Éléments du DOM
const dom = {
    arenaContainer: document.querySelector(".arena-container"),
    lobbySection: document.getElementById("lobbySection"),
    gameSection: document.getElementById("gameSection"),
    playerNameInput: document.getElementById("playerName"),
    gameModeSelect: document.getElementById("gameMode"),
    validationMode: document.getElementById("validationMode"),
    validationHelp: document.getElementById("validationHelp"),
    difficultySelect: document.getElementById("gameDifficulty"),
    clashRuleSelect: document.getElementById("clashRule"),
    clashRuleGroup: document.getElementById("clashRuleGroup"),
    btnToggleVoice: document.getElementById("btnToggleVoice"),
    voiceIcon: document.getElementById("voiceIcon"),
    btnCreateRoom: document.getElementById("btnCreateRoom"),
    btnJoinRoom: document.getElementById("btnJoinRoom"),
    btnPlayAi: document.getElementById("btnPlayAi"),
    joinCodeInput: document.getElementById("joinCodeInput"),
    displayRoomCode: document.getElementById("displayRoomCode"),
    displayModeBadge: document.getElementById("displayModeBadge"),
    matchStatusText: document.getElementById("matchStatusText"),
    btnStartGame: document.getElementById("btnStartGame"),
    btnLeaveRoom: document.getElementById("btnLeaveRoom"),
    btnErase: document.getElementById("btnErase"),
    sudokuGrid: document.getElementById("sudokuGrid"),
    controlsContainer: document.querySelector(".controls-container"),
    ledStrip: document.getElementById("ledStrip"),
    networkBadge: document.getElementById("networkBadge"),
    networkStatusText: document.getElementById("networkStatusText"),
    networkDot: document.getElementById("networkDot"),
    toastNotification: document.getElementById("toastNotification"),
    p1Card: document.getElementById("p1Card"),
    p2Card: document.getElementById("p2Card"),
    p1Name: document.getElementById("p1Name"),
    p2Name: document.getElementById("p2Name"),
    p1Score: document.getElementById("p1Score"),
    p2Score: document.getElementById("p2Score"),
    p1ProgressFill: document.getElementById("p1ProgressFill"),
    p2ProgressFill: document.getElementById("p2ProgressFill"),
    turnTimerWrapper: document.getElementById("turnTimerWrapper"),
    turnLabel: document.getElementById("turnLabel"),
    turnCountdown: document.getElementById("turnCountdown"),
    turnTimerFill: document.getElementById("turnTimerFill"),
    countdownOverlay: document.getElementById("countdownOverlay"),
    countdownNumber: document.getElementById("countdownNumber"),
    gameOverModal: document.getElementById("gameOverModal"),
    modalWinnerTitle: document.getElementById("modalWinnerTitle"),
    modalWinnerDesc: document.getElementById("modalWinnerDesc"),
    btnRematch: document.getElementById("btnRematch"),
    btnBackLobby: document.getElementById("btnBackLobby"),

    // Command Center & Guide Modal
    cardModeClash: document.getElementById("cardModeClash"),
    cardModeRace: document.getElementById("cardModeRace"),
    cardModeAi: document.getElementById("cardModeAi"),
    disciplineCards: document.querySelectorAll(".discipline-card"),
    paramClashRuleWrap: document.getElementById("paramClashRuleWrap"),
    paramsRow: document.querySelector(".params-row"),
    segValidation: document.getElementById("segValidation"),
    segClashRule: document.getElementById("segClashRule"),
    segDiff: document.getElementById("segDiff"),
    labelDifficulty: document.getElementById("labelDifficulty"),
    btnMainLaunch: document.getElementById("btnMainLaunch"),
    launchBtnIcon: document.getElementById("launchBtnIcon"),
    launchBtnText: document.getElementById("launchBtnText"),
    btnOpenGuide: document.getElementById("btnOpenGuide"),
    guideModal: document.getElementById("guideModal"),
    btnCloseGuide: document.getElementById("btnCloseGuide"),
    btnGuideGotIt: document.getElementById("btnGuideGotIt"),
    btnGuideVoice: document.getElementById("btnGuideVoice"),
    guideTabs: document.querySelectorAll(".guide-tab-btn"),
    guideTabText: document.getElementById("guideTabText"),

    // Post-Game Debrief Card
    postGameBadge: document.getElementById("postGameBadge"),
    statMatchTime: document.getElementById("statMatchTime"),
    statAccuracy: document.getElementById("statAccuracy"),
    statMaxCombo: document.getElementById("statMaxCombo"),
    statErrors: document.getElementById("statErrors"),
    modalDebriefText: document.getElementById("modalDebriefText"),
    btnReplayDebrief: document.getElementById("btnReplayDebrief"),
    btnShareCard: document.getElementById("btnShareCard"),

    // Matchmaking 1-Clic & Radar
    lobbyLaunchRow: document.getElementById("lobbyLaunchRow"),
    btnQuickMatch: document.getElementById("btnQuickMatch"),
    quickMatchBtnText: document.getElementById("quickMatchBtnText"),
    matchmakingOverlay: document.getElementById("matchmakingOverlay"),
    radarTimer: document.getElementById("radarTimer"),
    radarSubtitle: document.getElementById("radarSubtitle"),
    radarStatsText: document.getElementById("radarStatsText"),
    radarFallbackBox: document.getElementById("radarFallbackBox"),
    btnFallbackAi: document.getElementById("btnFallbackAi"),
    btnContinueWait: document.getElementById("btnContinueWait"),
    btnCancelMatchmaking: document.getElementById("btnCancelMatchmaking"),

    // Spectateur & Émotes Hype Wheel (Option C)
    btnSpectateRoom: document.getElementById("btnSpectateRoom"),
    displaySpectatorBadge: document.getElementById("displaySpectatorBadge"),
    spectatorCount: document.getElementById("spectatorCount"),
    spectatorRoleTag: document.getElementById("spectatorRoleTag"),
    emoteHypeContainer: document.getElementById("emoteHypeContainer"),
    hypeProgressFill: document.getElementById("hypeProgressFill"),
    hypeScoreText: document.getElementById("hypeScoreText"),
    emoteParticleLayer: document.getElementById("emoteParticleLayer")
};

// Système de Toast de Notification (Non intrusif)
let toastTimeout = null;
function showToast(message, type = "error", duration = 3200) {
    if (!dom.toastNotification) return;
    clearTimeout(toastTimeout);
    dom.toastNotification.textContent = message;
    dom.toastNotification.className = `toast-notification ${type}`;
    dom.toastNotification.classList.remove("hidden");
    toastTimeout = setTimeout(() => {
        dom.toastNotification.classList.add("hidden");
    }, duration);
}

// Mise à jour de l'indicateur de statut réseau
function updateNetworkStatus(status, text) {
    if (!dom.networkBadge || !dom.networkStatusText) return;
    dom.networkBadge.className = `network-badge ${status}`;
    dom.networkStatusText.textContent = text;
    if (dom.networkDot) {
        dom.networkDot.className = `pulse-dot ${status === "online" ? "" : status}`;
    }
}

// Initialisation du bandeau LED virtuel (30 pixels WS2812B)
function initVirtualLedStrip() {
    if (!dom.ledStrip) return;
    dom.ledStrip.innerHTML = "";
    for (let i = 0; i < 30; i++) {
        const pixel = document.createElement("div");
        pixel.className = "led-pixel";
        dom.ledStrip.appendChild(pixel);
    }
}

// Éclairage doux du bandeau LED par camp (Joueur 1 Gauche / Joueur 2 Droite)
function updateLedTurnLighting(isP1Turn) {
    const pixels = document.querySelectorAll(".led-pixel");
    pixels.forEach((p, idx) => {
        p.className = "led-pixel";
        if (state.mode === "race") {
            p.classList.add("blue");
        } else if (isP1Turn) {
            if (idx < 15) {
                p.classList.add("active-p1");
            } else {
                p.classList.add("dim");
            }
        } else {
            if (idx >= 15) {
                p.classList.add("active-p2");
            } else {
                p.classList.add("dim");
            }
        }
    });
}

// Animations du bandeau LED lors des événements
function triggerLedEffect(effect) {
    const pixels = document.querySelectorAll(".led-pixel");
    pixels.forEach((p, idx) => {
        if (effect === "success") {
            setTimeout(() => { 
                p.classList.remove("red", "active-p1", "active-p2", "dim");
                p.classList.add("green"); 
            }, idx * 8);
            setTimeout(() => {
                if (state.currentTurn) updateLedTurnLighting(state.currentTurn === state.playerId);
            }, 600);
        } else if (effect === "error") {
            p.classList.remove("green", "active-p1", "active-p2", "dim");
            p.classList.add("red");
            setTimeout(() => {
                if (state.currentTurn) updateLedTurnLighting(state.currentTurn === state.playerId);
            }, 450);
        } else if (effect === "victory") {
            setTimeout(() => { p.className = "led-pixel rainbow"; }, idx * 15);
        }
    });
}

// Construction de la grille 9x9 avec accessibilité
function buildBoardUI(initialPuzzle) {
    document.body.classList.add("in-game");
    if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");
    dom.sudokuGrid.innerHTML = "";
    state.grid = JSON.parse(JSON.stringify(initialPuzzle));

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.createElement("div");
            cell.className = "cell";
            cell.dataset.row = r;
            cell.dataset.col = c;
            cell.tabIndex = 0; // Accessible au focus clavier
            cell.setAttribute("role", "gridcell");
            cell.setAttribute("aria-label", `Ligne ${r + 1}, Colonne ${c + 1}`);

            const val = initialPuzzle[r][c];
            if (val !== 0) {
                cell.textContent = val;
                cell.classList.add("fixed");
                cell.setAttribute("aria-readonly", "true");
            }

            cell.addEventListener("click", () => selectCell(r, c));
            cell.addEventListener("focus", () => selectCell(r, c));
            dom.sudokuGrid.appendChild(cell);
        }
    }
}

function selectCell(row, col) {
    if (state.isSpectator) return;
    const cellEl = document.querySelector(`.cell[data-row='${row}'][data-col='${col}']`);
    const isFilled = cellEl && (cellEl.classList.contains("fixed") || cellEl.classList.contains("user-filled") || cellEl.classList.contains("opponent-filled"));

    // Nettoyer tous les surlignages
    document.querySelectorAll(".cell").forEach(c => {
        c.classList.remove("selected", "related", "same-number");
    });

    if (cellEl) cellEl.classList.add("selected");

    // L'aide visuelle (surlignage ligne, colonne, bloc 3x3 et chiffres identiques)
    // est réservée au mode Facile (Novice). En Moyen et Difficile, le joueur reste concentré.
    if (state.difficulty === "easy") {
        const boxRowStart = Math.floor(row / 3) * 3;
        const boxColStart = Math.floor(col / 3) * 3;
        const selectedVal = cellEl ? cellEl.textContent.trim() : "";

        document.querySelectorAll(".cell").forEach(c => {
            const r = parseInt(c.dataset.row, 10);
            const colIdx = parseInt(c.dataset.col, 10);
            const inSameRow = (r === row);
            const inSameCol = (colIdx === col);
            const inSameBox = (r >= boxRowStart && r < boxRowStart + 3 && colIdx >= boxColStart && colIdx < boxColStart + 3);

            if ((inSameRow || inSameCol || inSameBox) && !(r === row && colIdx === col)) {
                c.classList.add("related");
            }

            if (selectedVal && selectedVal !== "" && c.textContent.trim() === selectedVal && !(r === row && colIdx === col)) {
                c.classList.add("same-number");
            }
        });
    }

    // Si la case est déjà fixée/remplie ou si ce n'est pas notre tour
    if (isFilled || ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId)) {
        state.selectedCell = null;
        return;
    }

    state.selectedCell = { row, col };
    if (window.caster) caster.playSfx("click");
}

function handleInput(number) {
    if (state.isSpectator) return;
    if (window.caster) caster.playSfx("click");
    // Vérification du tour en mode Clash
    if ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId) {
        playBeep(180, 0.15);
        showToast(window.i18n ? i18n.t("not_your_turn") : "⏳ Ce n'est pas votre tour !", "error");
        return;
    }

    if (!state.selectedCell) {
        showToast(window.i18n ? i18n.t("select_empty_cell") : "Sélectionnez d'abord une case vide !", "info");
        return;
    }

    const { row, col } = state.selectedCell;

    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({
            action: "PLAY_MOVE",
            row: row,
            col: col,
            value: number
        }));
    } else {
        showToast(window.i18n ? i18n.t("server_disconnected") : "Connexion au serveur interrompue...", "error");
    }
}

// Gestion du Chronomètre de tour (Mode Clash)
function startTurnTimer(timeoutSeconds) {
    stopTurnTimer();
    const startTime = Date.now();
    const duration = timeoutSeconds * 1000;

    state.timerInterval = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, (duration - elapsed) / 1000);

        if (dom.turnCountdown) {
            dom.turnCountdown.textContent = Math.ceil(remaining) + "s";
        }

        const pct = Math.max(0, Math.min(100, (remaining / timeoutSeconds) * 100));
        if (dom.turnTimerFill) {
            dom.turnTimerFill.style.width = pct + "%";
            if (remaining <= 3.0) {
                dom.turnTimerFill.className = "turn-timer-fill danger";
            } else if (remaining <= timeoutSeconds * 0.4) {
                dom.turnTimerFill.className = "turn-timer-fill warning";
            } else {
                dom.turnTimerFill.className = "turn-timer-fill";
            }
        }

        if (remaining <= 0) {
            stopTurnTimer();
            if (dom.turnCountdown) dom.turnCountdown.textContent = "0s";
            if (dom.turnTimerFill) dom.turnTimerFill.style.width = "0%";
            if (state.currentTurn === state.playerId && state.socket && state.socket.readyState === WebSocket.OPEN) {
                state.socket.send(JSON.stringify({ action: "TIMEOUT_TURN" }));
            }
        }
    }, 80);
}

function stopTurnTimer() {
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
}

function updateTurnUI(currentTurnPlayerId, timeoutSeconds) {
    if (state.mode === "race") {
        if (dom.turnTimerWrapper) dom.turnTimerWrapper.classList.add("hidden");
        if (dom.p1Card) dom.p1Card.classList.remove("active-turn");
        if (dom.p2Card) dom.p2Card.classList.remove("active-turn", "is-p2");
        dom.sudokuGrid.classList.remove("disabled-turn");
        if (dom.controlsContainer) dom.controlsContainer.classList.remove("disabled-turn");
        updateLedTurnLighting(true);
        return;
    }

    if (dom.turnTimerWrapper) dom.turnTimerWrapper.classList.remove("hidden");
    const isMyTurn = (currentTurnPlayerId === state.playerId);

    if (isMyTurn) {
        if (dom.turnLabel) {
            dom.turnLabel.textContent = window.i18n ? i18n.t("your_turn") : "⏳ À VOTRE TOUR !";
            dom.turnLabel.style.color = "var(--neon-blue)";
        }
        if (dom.turnCountdown) dom.turnCountdown.style.color = "var(--neon-blue)";
        if (dom.p1Card) dom.p1Card.classList.add("active-turn");
        if (dom.p2Card) dom.p2Card.classList.remove("active-turn", "is-p2");
        dom.sudokuGrid.classList.remove("disabled-turn");
        if (dom.controlsContainer) dom.controlsContainer.classList.remove("disabled-turn");
        playBeep(587.33, 0.12); // Ton de notification (Ré)
    } else {
        const botLabel = window.i18n ? i18n.t("bot_rival_name") : "KI FRAID (Bot Rival 🤖)";
        const oppName = (state.isAiMatch ? botLabel : (dom.p2Name.textContent || "Adversaire")).replace(" (Moi)", "");
        if (dom.turnLabel) {
            dom.turnLabel.textContent = state.isAiMatch 
                ? (window.i18n ? i18n.t("turn_ai_thinking") : "🧠 LE BOT RIVAL KI FRAID RÉFLÉCHIT...") 
                : `${window.i18n ? i18n.t("opponent_turn_of") : "⏳ TOUR DE"} ${oppName.toUpperCase()}...`;
            dom.turnLabel.style.color = "var(--neon-purple)";
        }
        if (dom.turnCountdown) dom.turnCountdown.style.color = "var(--neon-purple)";
        if (dom.p2Card) dom.p2Card.classList.add("active-turn", "is-p2");
        if (dom.p1Card) dom.p1Card.classList.remove("active-turn");
        dom.sudokuGrid.classList.add("disabled-turn");
        if (dom.controlsContainer) dom.controlsContainer.classList.add("disabled-turn");
        // Désélectionner toute case
        document.querySelectorAll(".cell").forEach(c => c.classList.remove("selected"));
        state.selectedCell = null;
    }

    updateLedTurnLighting(isMyTurn);
    startTurnTimer(timeoutSeconds || state.turnTimeout);
}

// Connexion WebSocket avec reconnexion automatique
function connectWebSocket(roomCode, onOpenCallback = null) {
    const protocol = (window.location.protocol === "https:" || !IS_LOCAL) ? "wss:" : "ws:";
    const currentLang = (window.i18n && window.i18n.currentLang) || "fr";
    const wsUrl = `${protocol}//${BACKEND_HOST}/ws/${roomCode}/${state.playerId}/${encodeURIComponent(state.playerName)}?lang=${encodeURIComponent(currentLang)}`;

    updateNetworkStatus("reconnecting", "🟠 CONNEXION...");
    state.socket = new WebSocket(wsUrl);

    state.socket.onopen = () => {
        console.log("WebSocket connecté au salon :", roomCode);
        state.reconnectAttempts = 0;
        updateNetworkStatus("online", "🟢 EN LIGNE");
        if (onOpenCallback) onOpenCallback();
    };

    state.socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        console.log("Message reçu :", msg);

        if (msg.event === "PLAYER_JOINED") {
            updatePlayersLobby(msg.players);
            if (msg.spectators_count !== undefined && dom.spectatorCount) {
                dom.spectatorCount.textContent = msg.spectators_count;
            }
            if (msg.role === "spectator" && msg.player_id === state.playerId) {
                state.isSpectator = true;
                if (dom.gameSection) dom.gameSection.classList.add("spectator-view");
                if (dom.spectatorRoleTag) dom.spectatorRoleTag.classList.remove("hidden");
                showToast(window.i18n ? i18n.t("toast_spectator_mode_active") : "Mode Spectateur activé : vous observez le match en direct.", "info");
            }
            if (msg.players && msg.players.length >= 2) {
                closeMatchmakingOverlay();
                dom.lobbySection.classList.add("hidden");
                dom.gameSection.classList.remove("hidden");
                document.body.classList.add("in-game");
                if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");
            }
        } else if (msg.event === "AI_FALLBACK_TRIGGERED") {
            state.mode = "solo_ai";
            state.isAiMatch = true;
            closeMatchmakingOverlay();
            dom.lobbySection.classList.add("hidden");
            dom.gameSection.classList.remove("hidden");
            document.body.classList.add("in-game");
            if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");
            updatePlayersLobby(msg.players);
        } else if (msg.event === "COUNTDOWN") {
            closeMatchmakingOverlay();
            dom.lobbySection.classList.add("hidden");
            dom.gameSection.classList.remove("hidden");
            document.body.classList.add("in-game");
            if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");
            dom.countdownOverlay.classList.remove("hidden");
            dom.countdownNumber.textContent = msg.count;
            playBeep(msg.count === 1 ? 660 : 440, 0.18);
        } else if (msg.event === "GAME_STARTED") {
            dom.countdownOverlay.classList.add("hidden");
            dom.matchStatusText.textContent = "🔥 MATCH EN COURS";
            dom.btnStartGame.classList.add("hidden");
            state.turnTimeout = msg.turn_timeout || 20.0;
            state.currentTurn = msg.current_turn;

            // Réinitialiser les statistiques E-Sport du match
            state.matchStartTime = Date.now();
            state.matchDurationSeconds = 0;
            state.validMovesCount = 0;
            state.errorMovesCount = 0;
            state.currentComboStreak = 0;
            state.maxComboStreak = 0;
            state.lastDebriefText = "";

            if (window.caster) {
                const opponentName = (state.players && state.players.length > 1) 
                    ? state.players.find(p => p.id !== state.playerId)?.name 
                    : (state.mode === "solo_ai" ? "Bot Rival KI FRAID" : null);

                caster.commentIntro({
                    player1: state.playerName,
                    player2: opponentName,
                    mode: state.mode,
                    clashRule: state.clashRule || "combo_capped",
                    lang: (window.i18n && window.i18n.currentLang) || "fr"
                });
            }

            // Verrouiller la vue en 100dvh zéro-scroll
            if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");

            if (msg.shared_grid && (state.mode === "clash" || state.mode === "solo_ai")) {
                buildBoardUI(msg.shared_grid);
            } else {
                buildBoardUI(msg.initial_puzzle);
            }

            triggerLedEffect("success");
            if (window.caster) caster.playSfx("combo");
            updateTurnUI(msg.current_turn, state.turnTimeout);
        } else if (msg.event === "MOVE_RESULT") {
            const res = msg.result;

            // Cas de coup rejeté (ex: pas ton tour, case déjà remplie, hors bornes)
            if (res.rejected) {
                if (window.caster) caster.playSfx("error");
                const defaultMsg = window.i18n ? i18n.t("toast_move_rejected") : "Coup rejeté par le serveur.";
                const reason = (window.i18n && res.reason_code && i18n.t(res.reason_code)) || res.reason || defaultMsg;
                showToast(`⚠️ ${reason}`, "error");
                return;
            }

            const cellEl = document.querySelector(`.cell[data-row='${res.row}'][data-col='${res.col}']`);

            if (res.valid) {
                if (cellEl) {
                    cellEl.textContent = res.value;
                    cellEl.classList.remove("error-shake", "error-red");
                    if (res.player_id === state.playerId) {
                        cellEl.classList.add("user-filled");
                    } else {
                        cellEl.classList.add("opponent-filled");
                    }
                    if (window.ArenaAnimations) ArenaAnimations.pulseCell(cellEl, true);
                }
                triggerLedEffect("success");
                if (res.player_id === state.playerId) {
                    state.validMovesCount++;
                    state.currentComboStreak++;
                    if (state.currentComboStreak > state.maxComboStreak) {
                        state.maxComboStreak = state.currentComboStreak;
                    }

                    if (res.is_combo) {
                        if (window.caster) caster.playSfx("combo");
                        showToast(window.i18n ? i18n.t("toast_combo_bonus") : "⚡ COMBO x2 ! Coup Bonus !", "info");
                        if (window.ArenaAnimations) ArenaAnimations.triggerComboBurst(2);
                    } else {
                        if (window.caster) caster.playSfx("valid");
                    }
                } else if (res.is_combo) {
                    if (window.ArenaAnimations) ArenaAnimations.triggerComboBurst(2);
                    if (window.caster) caster.playSfx("combo");
                } else {
                    if (window.caster) caster.playSfx("valid");
                }
            } else {
                if (res.player_id === state.playerId) {
                    state.errorMovesCount++;
                    state.currentComboStreak = 0;
                }
                if (cellEl) {
                    cellEl.classList.add("error-red", "error-shake");
                    setTimeout(() => cellEl.classList.remove("error-red", "error-shake"), 400);
                    if (window.ArenaAnimations) ArenaAnimations.pulseCell(cellEl, false);
                }
                if (window.ArenaAnimations) ArenaAnimations.shakeBoard();
                triggerLedEffect("error");
                if (window.caster) caster.playSfx("error");
                if (res.player_id === state.playerId) {
                    const defaultReason = window.i18n ? i18n.t("toast_wrong_move") : "Ce chiffre n'est pas correct ici.";
                    const reason = (window.i18n && res.reason_code && i18n.t(res.reason_code)) || res.reason || defaultReason;
                    showToast(`❌ ${reason}`, "error");
                }
            }

            // Sécurisation stricte : mise à jour des scores et progression uniquement si disponible
            if (res.player_id === state.playerId) {
                if (res.score !== undefined) {
                    dom.p1Score.textContent = `${res.score} pts`;
                }
                if (res.valid && res.progress !== undefined) {
                    dom.p1ProgressFill.style.width = `${res.progress}%`;
                }
            } else {
                if (res.score !== undefined) {
                    dom.p2Score.textContent = `${res.score} pts`;
                }
                if (res.valid && res.progress !== undefined) {
                    dom.p2ProgressFill.style.width = `${res.progress}%`;
                }
            }

            // Alternance du tour en Clash
            if (state.mode === "clash" || state.mode === "solo_ai") {
                state.currentTurn = res.current_turn;
                updateTurnUI(res.current_turn, state.turnTimeout);
            }

            if (res.game_over) {
                stopTurnTimer();
                const isWinner = (res.winner_id === state.playerId);
                showGameOver(isWinner, res.winner_id === "DRAW");
                if (window.caster) {
                    caster.playSfx(isWinner ? "victory" : "error");
                }
            }
        } else if (msg.event === "TURN_TIMEOUT") {
            const res = msg.result;
            triggerLedEffect("error");
            if (window.caster) {
                caster.playSfx("error");
            }

            if (res.timed_out_player_id === state.playerId) {
                dom.p1Score.textContent = `${res.score} pts`;
                showToast(window.i18n ? i18n.t("toast_timeout_self") : "⏰ Temps écoulé ! La main passe.", "info");
            } else {
                dom.p2Score.textContent = `${res.score} pts`;
                showToast(window.i18n ? i18n.t("toast_timeout_opponent") : "⏰ Temps écoulé pour l'adversaire !", "info");
            }

            state.currentTurn = res.current_turn;
            updateTurnUI(res.current_turn, state.turnTimeout);
        } else if (msg.event === "CASTER_COMMENT") {
            const comment = msg.comment;
            if (comment && window.caster) {
                caster.handleLiveComment(comment);
            }
        } else if (msg.event === "GAME_OVER_FORFEIT") {
            stopTurnTimer();
            triggerLedEffect("victory");
            const isMe = (msg.winner_id === state.playerId);
            dom.modalWinnerTitle.textContent = isMe 
                ? (window.i18n ? i18n.t("forfeit_victory_title") : "VICTOIRE PAR FORFAIT ! 🏆") 
                : (window.i18n ? i18n.t("forfeit_game_over_title") : "PARTIE TERMINÉE 💥");
            const opponentName = msg.left_player_name || (window.i18n ? i18n.t("p2_default") : "L'adversaire");
            const forfeitMsg = window.i18n ? i18n.t("toast_player_left_forfeit") : "a quitté le duel. Victoire par forfait !";
            dom.modalWinnerDesc.textContent = isMe
                ? `${opponentName} ${forfeitMsg}`
                : "Vous avez quitté la partie.";
            dom.gameOverModal.classList.remove("hidden");
            playBeep(isMe ? 880 : 180, 0.6);
            showToast(`⚠️ ${opponentName} ${forfeitMsg}`, "info", 5000);
        } else if (msg.event === "PLAYER_LEFT") {
            if (msg.players) {
                updatePlayersLobby(msg.players);
            } else {
                dom.p2Name.textContent = window.i18n ? i18n.t("waiting_player") : "En attente...";
                dom.matchStatusText.textContent = window.i18n ? i18n.t("share_room_code") : "Partagez le code du salon !";
                if (dom.btnStartGame) dom.btnStartGame.classList.add("hidden");
            }
            showToast(window.i18n ? i18n.t("toast_player_left_lobby") : "Un joueur a quitté le salon.", "info");
        } else if (msg.event === "EMOTE_BURST") {
            spawnEmoteParticle(msg.emote_key, msg.player_name, msg.role);
            boostHype(4);
        } else if (msg.event === "HYPE_UPDATE") {
            boostHype(6);
        }
    };

    state.socket.onclose = () => {
        console.log("WebSocket déconnecté.");
        stopTurnTimer();

        // Tentative de reconnexion automatique si nous sommes en partie
        if (state.roomCode && state.reconnectAttempts < state.maxReconnectAttempts) {
            state.reconnectAttempts++;
            updateNetworkStatus("reconnecting", `🟠 RECONNEXION (${state.reconnectAttempts}/${state.maxReconnectAttempts})...`);
            clearTimeout(state.reconnectTimeout);
            state.reconnectTimeout = setTimeout(() => {
                connectWebSocket(state.roomCode);
            }, Math.min(1000 * Math.pow(1.5, state.reconnectAttempts), 8000));
        } else if (state.reconnectAttempts >= state.maxReconnectAttempts) {
            updateNetworkStatus("offline", "🔴 DÉCONNECTÉ");
            showToast(window.i18n ? i18n.t("toast_connection_lost") : "Connexion au serveur perdue. Rafraîchissez la page.", "error", 6000);
        }
    };

    state.socket.onerror = (err) => {
        console.error("Erreur WebSocket :", err);
    };
}

function updatePlayersLobby(players) {
    const p1 = players.find(p => p.id === state.playerId);
    const p2 = players.find(p => p.id !== state.playerId);
    const meTag = window.i18n ? i18n.t("player_me_tag") : "(Moi)";
    const defP1 = window.i18n ? i18n.t("default_player_name") : "Joueur 1";
    const defP2 = window.i18n ? i18n.t("default_player_2") : "Joueur 2";

    if (p1) {
        dom.p1Name.textContent = `${p1.name} ${meTag}`;
    } else {
        dom.p1Name.textContent = defP1;
    }

    if (p2) {
        dom.p2Name.textContent = p2.name;
        dom.matchStatusText.textContent = window.i18n ? i18n.t("match_ready") : "Prêt à démarrer !";
        if (state.isHost) dom.btnStartGame.classList.remove("hidden");
    } else {
        dom.p2Name.textContent = window.i18n ? i18n.t("waiting_player") : "En attente...";
        dom.matchStatusText.textContent = window.i18n ? i18n.t("share_room_code") : "Partagez le code du salon !";
    }
}

function showGameOver(isWinner, isDraw = false) {
    stopTurnTimer();
    triggerLedEffect("victory");

    // Calcul des statistiques réelles du match
    const durationSec = Math.max(1, Math.round((Date.now() - (state.matchStartTime || Date.now())) / 1000));
    state.matchDurationSeconds = durationSec;
    const minutes = Math.floor(durationSec / 60);
    const seconds = durationSec % 60;
    const timeStr = `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
    const totalMoves = state.validMovesCount + state.errorMovesCount;
    const accuracy = totalMoves > 0 ? Math.round((state.validMovesCount / totalMoves) * 100) : 100;
    const maxCombo = state.maxComboStreak || (isWinner ? 1 : 0);
    const errors = state.errorMovesCount;

    // Titres & Descriptions
    if (isDraw) {
        dom.modalWinnerTitle.textContent = window.i18n ? i18n.t("draw_title") : "ÉGALITÉ ! 🤝";
        dom.modalWinnerDesc.textContent = "Score parfaitement identique à l'issue de la grille !";
    } else {
        dom.modalWinnerTitle.textContent = isWinner 
            ? (window.i18n ? i18n.t("victory_title") : "VICTOIRE ! 🏆") 
            : (window.i18n ? i18n.t("defeat_title") : "DÉFAITE ! 💥");
        dom.modalWinnerDesc.textContent = isWinner
            ? (window.i18n ? i18n.t("modal_winner_desc") : "Vous avez complété la grille en premier avec brio !")
            : (window.i18n ? i18n.t("modal_loser_desc") : "Votre adversaire s'impose sur cette manche.");
    }

    // Attribution du Badge E-Sport
    let badgeKey = "badge_resilience";
    if (maxCombo >= 3) {
        badgeKey = "badge_combo_master";
    } else if (isWinner && durationSec <= 90) {
        badgeKey = "badge_speedrunner";
    } else if (accuracy >= 90 && totalMoves >= 3) {
        badgeKey = "badge_precision";
    } else if (isWinner) {
        badgeKey = "badge_champion";
    }
    const badgeText = window.i18n ? i18n.t(badgeKey) : badgeKey;
    if (dom.postGameBadge) dom.postGameBadge.textContent = badgeText;

    // Injection des tuiles de statistiques
    if (dom.statMatchTime) dom.statMatchTime.textContent = timeStr;
    if (dom.statAccuracy) dom.statAccuracy.textContent = `${accuracy}%`;
    if (dom.statMaxCombo) dom.statMaxCombo.textContent = `x${maxCombo}`;
    if (dom.statErrors) dom.statErrors.textContent = errors.toString();

    // Texte de débriefing par défaut en attendant l'analyse LLM
    const opponentName = (state.players && state.players.length > 1) 
        ? state.players.find(p => p.id !== state.playerId)?.name 
        : (state.mode === "solo_ai" ? "Bot Rival KI FRAID" : (window.i18n ? i18n.t("p2_default") : "Adversaire"));

    const defaultDebrief = isWinner 
        ? `« Superbe victoire de ${state.playerName} ! Une intensité remarquable avec ${accuracy}% de précision et un combo max x${maxCombo} ! »`
        : `« Victoire de ${opponentName}. Belle résistance de ${state.playerName}, prépare ta revanche immédiate ! »`;

    state.lastDebriefText = defaultDebrief;
    if (dom.modalDebriefText) dom.modalDebriefText.textContent = defaultDebrief;

    dom.gameOverModal.classList.remove("hidden");
    if (isWinner && window.ArenaAnimations) ArenaAnimations.celebrateVictory();
    playBeep(isWinner ? 880 : 180, 0.6);

    // Débriefing vocal et textuel Caster IA
    if (window.caster) {
        caster.commentDebrief({
            winner: isWinner ? state.playerName : opponentName,
            loser: isWinner ? opponentName : state.playerName,
            winnerScore: isWinner ? (state.validMovesCount * 100) : 0,
            loserScore: isWinner ? 0 : (state.validMovesCount * 100),
            isDraw: isDraw,
            totalCombos: maxCombo,
            duration: durationSec,
            mode: state.mode,
            lang: (window.i18n && window.i18n.currentLang) || "fr",
            isWinner: isWinner,
            onDebriefReady: (text) => {
                state.lastDebriefText = text;
                if (dom.modalDebriefText) dom.modalDebriefText.textContent = text;
            }
        });
    }
}
window.showGameOver = showGameOver;

// Mise à jour des explications des règles de validation
const updateValidationHelp = (selectEl, helpEl) => {
    if (!selectEl || !helpEl) return;
    if (selectEl.value === "simple") {
        helpEl.textContent = "✨ Mode Simple : Tout chiffre valide selon les règles Sudoku est accepté";
    } else {
        helpEl.textContent = "🧩 Mode Casse-Tête : Seule la solution finale unique est acceptée (Puriste)";
    }
};

if (dom.validationMode && dom.validationHelp) {
    dom.validationMode.addEventListener("change", () => updateValidationHelp(dom.validationMode, dom.validationHelp));
}

// --- Logique Arena Command Center & Gestion des Modes ---

// Action de création de salon (Clash ou Course)
async function createRoomGame() {
    const defaultName = window.i18n ? i18n.t("default_player_name") : "Joueur 1";
    state.playerName = (dom.playerNameInput ? dom.playerNameInput.value.trim() : "") || defaultName;
    const difficulty = dom.difficultySelect ? dom.difficultySelect.value : "medium";
    const mode = dom.gameModeSelect ? dom.gameModeSelect.value : "clash";
    const validationMode = dom.validationMode ? dom.validationMode.value : "simple";
    const clashRule = (dom.clashRuleSelect && mode === "clash") ? dom.clashRuleSelect.value : "combo_capped";
    state.mode = mode;
    state.difficulty = difficulty;
    state.validationMode = validationMode;

    const currentLang = (window.i18n && window.i18n.currentLang) || "fr";

    try {
        const res = await fetch(`${API_BASE_URL}/api/rooms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: mode,
                difficulty: difficulty,
                validation_mode: validationMode,
                clash_rule: clashRule,
                lang: currentLang
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;
        state.isHost = true;

        dom.displayRoomCode.textContent = state.roomCode;
        if (dom.displayModeBadge) {
            const modeName = mode === "clash" ? "⚡ CLASH" : "🏎️ COURSE";
            const valName = validationMode === "simple" 
                ? (window.i18n ? i18n.t("val_mode_simple_label") : "SIMPLE") 
                : (window.i18n ? i18n.t("val_mode_strict_label") : "STRICT");
            dom.displayModeBadge.textContent = `${modeName} [${valName}]`;
        }

        const meTag = window.i18n ? i18n.t("player_me_tag") : "(Moi)";
        dom.p1Name.textContent = `${state.playerName} ${meTag}`;

        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        document.body.classList.add("in-game");
        if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");
        buildBoardUI(data.initial_puzzle);

        connectWebSocket(state.roomCode);
    } catch (err) {
        showToast((window.i18n ? i18n.t("toast_error_create_room") : "Erreur lors de la création du salon : ") + err, "error");
    }
}

// Action de duel solo contre KI FRAID
async function startSoloAiGame() {
    const defaultName = window.i18n ? i18n.t("default_player_name") : "Joueur 1";
    state.playerName = (dom.playerNameInput ? dom.playerNameInput.value.trim() : "") || defaultName;
    state.isAiMatch = true;
    state.isHost = true;
    state.mode = "solo_ai";

    const chosenDiff = dom.difficultySelect ? dom.difficultySelect.value : "medium";
    const validationMode = dom.validationMode ? dom.validationMode.value : "simple";
    state.difficulty = chosenDiff;
    state.validationMode = validationMode;
    const currentLang = (window.i18n && window.i18n.currentLang) || "fr";

    try {
        const res = await fetch(`${API_BASE_URL}/api/rooms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: "solo_ai",
                difficulty: chosenDiff,
                validation_mode: validationMode,
                lang: currentLang
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;

        const diffLabels = {
            easy: window.i18n ? i18n.t("diff_label_novice") : "NOVICE",
            medium: window.i18n ? i18n.t("diff_label_tactique") : "TACTIQUE",
            hard: window.i18n ? i18n.t("diff_label_grand_maitre") : "GRAND MAÎTRE"
        };
        const diffName = diffLabels[chosenDiff] || "TACTIQUE";

        dom.displayRoomCode.textContent = "VS-AI";
        if (dom.displayModeBadge) {
            const valName = validationMode === "simple" 
                ? (window.i18n ? i18n.t("val_mode_simple_label") : "SIMPLE") 
                : (window.i18n ? i18n.t("val_mode_strict_label") : "STRICT");
            const botPersona = currentLang === "fr" ? "L'IA FRAID" : (currentLang === "en" ? "AI FRAID" : "KI FRAID");
            dom.displayModeBadge.textContent = `🤖 ${botPersona} (${diffName}) [${valName}]`;
        }
        const meTag = window.i18n ? i18n.t("player_me_tag") : "(Moi)";
        dom.p1Name.textContent = `${state.playerName} ${meTag}`;
        const botLabel = window.i18n ? i18n.t("bot_rival_name") : "KI FRAID (Bot Rival 🤖)";
        dom.p2Name.textContent = `${botLabel} [${diffName}]`;
        dom.matchStatusText.textContent = window.i18n ? i18n.t("game_starting") : "Départ imminent...";

        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        dom.btnStartGame.classList.add("hidden");
        document.body.classList.add("in-game");
        if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");

        buildBoardUI(data.initial_puzzle);

        // Connexion WebSocket et lancement automatique du décompte
        connectWebSocket(state.roomCode, () => {
            setTimeout(() => {
                if (state.socket) {
                    state.socket.send(JSON.stringify({ action: "START_GAME" }));
                }
            }, 300);
        });
    } catch (err) {
        showToast((window.i18n ? i18n.t("toast_error_ai") : "Erreur démarrage solo IA : ") + err, "error");
    }
}

// Sélecteur de Discipline E-Sport avec adaptation contextuelle
function setDiscipline(mode) {
    state.mode = mode;
    if (dom.gameModeSelect) dom.gameModeSelect.value = mode;

    // Mise à jour de l'état actif des cartes
    document.querySelectorAll(".discipline-card").forEach(card => {
        card.classList.toggle("active", card.dataset.mode === mode);
    });

    const currentLang = (window.i18n && window.i18n.currentLang) || "fr";

    // Adaptation du deck de paramètres
    if (dom.paramClashRuleWrap && dom.paramsRow) {
        if (mode === "clash") {
            dom.paramClashRuleWrap.style.display = "";
            dom.paramsRow.classList.remove("two-cols");
        } else {
            dom.paramClashRuleWrap.style.display = "none";
            dom.paramsRow.classList.add("two-cols");
        }
    }

    // Mise à jour du bouton d'action principal
    if (dom.launchBtnIcon && dom.launchBtnText) {
        if (mode === "clash") {
            dom.launchBtnIcon.textContent = "🚀";
            dom.launchBtnText.setAttribute("data-i18n", "btn_create_clash");
            dom.launchBtnText.textContent = window.i18n ? i18n.t("btn_create_clash") : "Créer le Salon Clash 🚀";
        } else if (mode === "race") {
            dom.launchBtnIcon.textContent = "🏎️";
            dom.launchBtnText.setAttribute("data-i18n", "btn_create_race");
            dom.launchBtnText.textContent = window.i18n ? i18n.t("btn_create_race") : "Lancer la Course Miroir 🏎️";
        } else if (mode === "solo_ai") {
            dom.launchBtnIcon.textContent = "🤖";
            dom.launchBtnText.setAttribute("data-i18n", "btn_challenge_ai");
            dom.launchBtnText.textContent = window.i18n ? i18n.t("btn_challenge_ai") : "Défier KI FRAID 🤖";
        }
    }

    // Adaptation de la rangée de lancement (Matchmaking 1-Clic masqué en Solo IA)
    if (dom.lobbyLaunchRow) {
        if (mode === "solo_ai") {
            dom.lobbyLaunchRow.classList.add("solo-mode");
            if (dom.btnQuickMatch) dom.btnQuickMatch.style.display = "none";
        } else {
            dom.lobbyLaunchRow.classList.remove("solo-mode");
            if (dom.btnQuickMatch) dom.btnQuickMatch.style.display = "";
        }
    }

    // Mise à jour des libellés de difficulté
    const btnEasy = document.getElementById("segDiffEasy");
    const btnMedium = document.getElementById("segDiffMedium");
    const btnHard = document.getElementById("segDiffHard");

    if (mode === "clash") {
        if (dom.labelDifficulty) {
            dom.labelDifficulty.setAttribute("data-i18n", "difficulty_label");
            dom.labelDifficulty.textContent = window.i18n ? i18n.t("difficulty_label") : "Difficulté / Chrono :";
        }
        if (btnEasy) btnEasy.innerHTML = `<span>${window.i18n ? i18n.t("diff_easy") : "Facile (30s)"}</span>`;
        if (btnMedium) btnMedium.innerHTML = `<span>${window.i18n ? i18n.t("diff_medium") : "Moyen (20s)"}</span>`;
        if (btnHard) btnHard.innerHTML = `<span>${window.i18n ? i18n.t("diff_hard") : "Difficile (10s)"}</span>`;
    } else if (mode === "race") {
        if (dom.labelDifficulty) {
            dom.labelDifficulty.textContent = currentLang === "de" ? "Raster-Schwierigkeit :" : (currentLang === "en" ? "Grid Difficulty:" : "Difficulté Grille :");
        }
        if (btnEasy) btnEasy.innerHTML = `<span>${currentLang === "de" ? "Leicht" : (currentLang === "en" ? "Easy" : "Facile")}</span>`;
        if (btnMedium) btnMedium.innerHTML = `<span>${currentLang === "de" ? "Mittel" : (currentLang === "en" ? "Medium" : "Moyen")}</span>`;
        if (btnHard) btnHard.innerHTML = `<span>${currentLang === "de" ? "Schwer" : (currentLang === "en" ? "Hard" : "Difficile")}</span>`;
    } else if (mode === "solo_ai") {
        if (dom.labelDifficulty) {
            dom.labelDifficulty.textContent = currentLang === "de" ? "KI-Schwierigkeitsgrad :" : (currentLang === "en" ? "AI Bot Level:" : "Niveau du Bot :");
        }
        if (btnEasy) btnEasy.innerHTML = `<span>${window.i18n ? i18n.t("diff_label_novice") : "Novice"}</span>`;
        if (btnMedium) btnMedium.innerHTML = `<span>${window.i18n ? i18n.t("diff_label_tactique") : "Tactique"}</span>`;
        if (btnHard) btnHard.innerHTML = `<span>${window.i18n ? i18n.t("diff_label_grand_maitre") : "Grand Maître"}</span>`;
    }

    // Réaction du Commentateur
    if (window.caster) {
        if (mode === "clash") caster.comment("MODE_CLASH");
        else if (mode === "race") caster.comment("MODE_RACE");
        else if (mode === "solo_ai") {
            const aiLines = {
                fr: "« Prêt à me défier ? Choisis bien ton niveau, je ne ferai aucun cadeau ! »",
                en: "« Ready to challenge me? Choose your difficulty level wisely! »",
                de: "« Bereit gegen mich anzutreten? Wähle deine Schwierigkeit mit Bedacht! »"
            };
            caster.displayHud(aiLines[currentLang] || aiLines.fr);
            if (caster.isVoiceEnabled) {
                caster.comment("VS_BOT");
            }
        }
    }
}

// Initialiseur pour barres segmentées modernes
function initSegmentedBar(containerEl, targetInputId, onValChange) {
    if (!containerEl) return;
    const targetInput = document.getElementById(targetInputId);
    containerEl.querySelectorAll(".seg-item").forEach(item => {
        item.addEventListener("click", () => {
            containerEl.querySelectorAll(".seg-item").forEach(btn => btn.classList.remove("active"));
            item.classList.add("active");
            const val = item.dataset.val;
            if (targetInput) targetInput.value = val;
            if (onValChange) onValChange(val);
            if (window.caster) caster.playSfx("click");
        });
    });
}

// Initialisation du Guide Modal Interactif
function initTabbedGuideModal() {
    if (!dom.guideModal) return;

    const setTab = (tabName) => {
        if (dom.guideTabs) {
            dom.guideTabs.forEach(btn => {
                btn.classList.toggle("active", btn.dataset.tab === tabName);
            });
        }
        const textKey = "guide_" + tabName + "_text";
        if (dom.guideTabText) {
            dom.guideTabText.setAttribute("data-i18n", textKey);
            dom.guideTabText.textContent = window.i18n ? i18n.t(textKey) : "";
        }
    };

    if (dom.btnOpenGuide) {
        dom.btnOpenGuide.addEventListener("click", () => {
            dom.guideModal.classList.remove("hidden");
            setTab("clash");
            if (window.caster) caster.playSfx("click");
        });
    }

    if (dom.btnCloseGuide) {
        dom.btnCloseGuide.addEventListener("click", () => {
            dom.guideModal.classList.add("hidden");
            if (window.caster) {
                caster.stopAllVoice();
                caster.playSfx("click");
            }
        });
    }

    if (dom.btnGuideGotIt) {
        dom.btnGuideGotIt.addEventListener("click", () => {
            dom.guideModal.classList.add("hidden");
            if (window.caster) {
                caster.stopAllVoice();
                caster.playSfx("click");
            }
        });
    }

    dom.guideModal.addEventListener("click", (e) => {
        if (e.target === dom.guideModal) {
            dom.guideModal.classList.add("hidden");
            if (window.caster) caster.stopAllVoice();
        }
    });

    if (dom.guideTabs) {
        dom.guideTabs.forEach(btn => {
            btn.addEventListener("click", () => {
                setTab(btn.dataset.tab);
                if (window.caster) {
                    caster.stopAllVoice();
                    caster.playSfx("click");
                }
            });
        });
    }

    if (dom.btnGuideVoice) {
        dom.btnGuideVoice.addEventListener("click", () => {
            const currentLang = (window.i18n && window.i18n.currentLang) || "fr";
            const textToSpeak = dom.guideTabText ? dom.guideTabText.textContent : "";
            if (textToSpeak && window.caster) {
                caster.speakWebSpeech(textToSpeak, currentLang);
            }
        });
    }
}

// Vocalisation pédagogique des paramètres
function explainOption(category, val) {
    let key = "";
    if (category === "validation") {
        key = val === "simple" ? "explain_val_simple" : "explain_val_strict";
    } else if (category === "clashRule") {
        key = "explain_clash_" + val;
    } else if (category === "difficulty") {
        const mode = state.mode || "clash";
        if (mode === "clash") {
            key = "explain_diff_clash_" + val;
        } else if (mode === "race") {
            key = "explain_diff_race_" + val;
        } else if (mode === "solo_ai") {
            key = "explain_diff_ai_" + val;
        }
    }

    if (key && window.caster && typeof caster.explainSetting === "function") {
        const text = window.i18n ? i18n.t(key) : "";
        caster.explainSetting(text);
    }
}

// Initialisation globale des composants Command Center
function initCommandCenter() {
    // 1. Clic sur les cartes de discipline
    document.querySelectorAll(".discipline-card").forEach(card => {
        card.addEventListener("click", () => {
            const mode = card.dataset.mode;
            setDiscipline(mode);
            if (window.caster) caster.playSfx("click");
        });
    });

    // 2. Barres segmentées avec explications vocales automatiques
    initSegmentedBar(dom.segValidation, "validationMode", (val) => { 
        state.validationMode = val;
        explainOption("validation", val);
    });
    initSegmentedBar(dom.segClashRule, "clashRule", (val) => {
        explainOption("clashRule", val);
    });
    initSegmentedBar(dom.segDiff, "gameDifficulty", (val) => { 
        state.difficulty = val;
        explainOption("difficulty", val);
    });

    // 3. Bouton Principal de Lancement
    if (dom.btnMainLaunch) {
        dom.btnMainLaunch.addEventListener("click", () => {
            if (state.mode === "solo_ai") {
                startSoloAiGame();
            } else {
                createRoomGame();
            }
        });
    }

    // 4. Bouton Matchmaking Rapide 1-Clic
    if (dom.btnQuickMatch) {
        dom.btnQuickMatch.addEventListener("click", startQuickMatchmaking);
    }

    // 5. Boutons de repli et d'annulation du Radar
    if (dom.btnFallbackAi) {
        dom.btnFallbackAi.addEventListener("click", triggerFallbackAi);
    }
    if (dom.btnContinueWait) {
        dom.btnContinueWait.addEventListener("click", () => {
            if (dom.radarFallbackBox) dom.radarFallbackBox.classList.add("hidden");
        });
    }
    if (dom.btnCancelMatchmaking) {
        dom.btnCancelMatchmaking.addEventListener("click", () => {
            closeMatchmakingOverlay();
            if (state.socket) {
                state.socket.close();
                state.socket = null;
            }
            state.roomCode = null;
        });
    }

    // 6. Guide Modal
    initTabbedGuideModal();

    // 7. Spectateur & Émotes Hype Wheel (Option C)
    if (dom.btnSpectateRoom) {
        dom.btnSpectateRoom.addEventListener("click", joinAsSpectator);
    }
    document.querySelectorAll(".btn-emote").forEach(btn => {
        btn.addEventListener("click", () => {
            const emote = btn.dataset.emote;
            sendEmote(emote);
        });
    });
}

// ==========================================================================
// Logique Matchmaking Rapide « 1-Clic » & Radar
// ==========================================================================

let matchmakingTimerInterval = null;
let matchmakingSeconds = 0;
let matchmakingActive = false;

function openMatchmakingOverlay() {
    matchmakingActive = true;
    matchmakingSeconds = 0;
    if (dom.matchmakingOverlay) dom.matchmakingOverlay.classList.remove("hidden");
    if (dom.radarFallbackBox) dom.radarFallbackBox.classList.add("hidden");
    if (dom.radarTimer) dom.radarTimer.textContent = "00:00";
    if (dom.radarSubtitle) {
        dom.radarSubtitle.textContent = window.i18n ? i18n.t("radar_searching_desc") : "Connexion au réseau e-sport des joueurs Sudoku Arena...";
    }

    clearInterval(matchmakingTimerInterval);
    matchmakingTimerInterval = setInterval(() => {
        if (!matchmakingActive) return;
        matchmakingSeconds++;
        const mins = Math.floor(matchmakingSeconds / 60).toString().padStart(2, "0");
        const secs = (matchmakingSeconds % 60).toString().padStart(2, "0");
        if (dom.radarTimer) dom.radarTimer.textContent = `${mins}:${secs}`;

        // Après 8 secondes sans rival : proposer le repli IA KI FRAID
        if (matchmakingSeconds >= 8 && dom.radarFallbackBox && dom.radarFallbackBox.classList.contains("hidden")) {
            dom.radarFallbackBox.classList.remove("hidden");
            if (window.caster) {
                const noRivalText = window.i18n ? i18n.t("radar_no_human") : "Aucun rival humain disponible pour l'instant !";
                caster.displayHud(`« ${noRivalText} »`);
                if (caster.isVoiceEnabled) {
                    caster.speakWebSpeech(noRivalText, (window.i18n && window.i18n.currentLang) || "fr");
                }
            }
        }
    }, 1000);

    fetchMatchmakingStats();
}

function closeMatchmakingOverlay() {
    matchmakingActive = false;
    clearInterval(matchmakingTimerInterval);
    if (dom.matchmakingOverlay) dom.matchmakingOverlay.classList.add("hidden");
    if (dom.radarFallbackBox) dom.radarFallbackBox.classList.add("hidden");
}

async function fetchMatchmakingStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/matchmaking/stats`);
        if (res.ok) {
            const data = await res.json();
            const currentLang = (window.i18n && window.i18n.currentLang) || "fr";
            const statsStr = currentLang === "de"
                ? `Wartende Räume: ${data.waiting_rooms} • Aktive Spieler: ${data.total_players}`
                : (currentLang === "en"
                    ? `Waiting rooms: ${data.waiting_rooms} • Active players: ${data.total_players}`
                    : `Salons en attente: ${data.waiting_rooms} • Joueurs actifs: ${data.total_players}`);
            if (dom.radarStatsText) dom.radarStatsText.textContent = statsStr;
        }
    } catch (e) {
        // En cas d'erreur réseau, conserver le texte actuel
    }
}

async function startQuickMatchmaking() {
    const defaultName = window.i18n ? i18n.t("default_player_name") : "Joueur 1";
    state.playerName = (dom.playerNameInput ? dom.playerNameInput.value.trim() : "") || defaultName;
    const currentLang = (window.i18n && window.i18n.currentLang) || "fr";
    const selectedClashRule = document.getElementById("clashRule") ? document.getElementById("clashRule").value : "combo_capped";
    const modeToFind = (state.mode === "solo_ai") ? "clash" : state.mode;

    openMatchmakingOverlay();
    if (window.caster) caster.playSfx("click");

    try {
        const resp = await fetch(`${API_BASE_URL}/api/matchmaking/find`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                player_id: state.playerId,
                player_name: state.playerName,
                mode: modeToFind,
                difficulty: state.difficulty,
                validation_mode: state.validationMode,
                clash_rule: selectedClashRule,
                lang: currentLang
            })
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || "Erreur de matchmaking");
        }

        const data = await resp.json();
        state.roomCode = data.room_code;
        state.isHost = data.is_host;
        state.mode = data.mode;
        state.difficulty = data.difficulty;
        state.validationMode = data.validation_mode;
        state.isAiMatch = false;

        dom.displayRoomCode.textContent = state.roomCode;
        dom.displayModeBadge.textContent = state.mode === "clash" ? "⚡ CLASH" : "🏎️ COURSE";
        const meTag = window.i18n ? i18n.t("player_me_tag") : "(Moi)";
        dom.p1Name.textContent = `${state.playerName} ${meTag}`;

        if (data.status === "matched") {
            // Rival trouvé immédiatement !
            if (dom.radarSubtitle) {
                dom.radarSubtitle.textContent = window.i18n ? i18n.t("radar_rival_found") : "⚔️ Rival trouvé ! Lancement du duel...";
            }
            if (window.caster) caster.playSfx("combo");

            setTimeout(() => {
                closeMatchmakingOverlay();
                dom.lobbySection.classList.add("hidden");
                dom.gameSection.classList.remove("hidden");
                document.body.classList.add("in-game");
                if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");
                connectWebSocket(state.roomCode);
            }, 700);
        } else {
            // En attente : connecter le WebSocket dans le salon public créé
            connectWebSocket(state.roomCode);
        }

    } catch (err) {
        closeMatchmakingOverlay();
        showToast("Erreur de matchmaking : " + err.message, "error");
    }
}

async function triggerFallbackAi() {
    if (!state.roomCode) return;
    try {
        if (window.caster) caster.playSfx("click");
        const resp = await fetch(`${API_BASE_URL}/api/matchmaking/fallback-ai`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ room_code: state.roomCode })
        });

        if (!resp.ok) {
            throw new Error("Erreur de conversion en solo IA");
        }

        state.mode = "solo_ai";
        state.isAiMatch = true;
        closeMatchmakingOverlay();
        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        document.body.classList.add("in-game");
        if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");

    } catch (err) {
        showToast("Impossible de lancer le bot : " + err.message, "error");
    }
}

// ==========================================================================
// Logique Spectateur & Émotes Hype Wheel (Option C)
// ==========================================================================

const EMOTE_MAP = {
    fire: "🔥",
    brain: "🧠",
    speed: "⚡",
    panic: "😱",
    gg: "👏",
    fraid: "🤖"
};

function sendEmote(emoteKey) {
    if (!state.roomCode) return;
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({
            action: "SEND_EMOTE",
            emote_key: emoteKey
        }));
    }
}

function boostHype(delta = 4) {
    state.hypeScore = Math.min(100, Math.max(10, state.hypeScore + delta));
    updateHypeUI();
}

function updateHypeUI() {
    if (dom.hypeProgressFill) {
        dom.hypeProgressFill.style.width = `${state.hypeScore}%`;
    }
    if (dom.hypeScoreText) {
        dom.hypeScoreText.textContent = `${state.hypeScore}%`;
    }
}

function spawnEmoteParticle(emoteKey, authorName = "", role = "player") {
    if (!dom.emoteParticleLayer) return;
    const emoji = EMOTE_MAP[emoteKey] || "🔥";
    const bubble = document.createElement("div");
    bubble.className = "floating-emote-bubble";

    const randomLeft = Math.floor(Math.random() * 70) + 10;
    bubble.style.left = `${randomLeft}%`;
    bubble.style.bottom = "30px";

    const isSpectator = role === "spectator";
    const authorTag = authorName ? `<span class="floating-emote-author">${isSpectator ? "👁️ " : ""}${authorName}</span>` : "";
    bubble.innerHTML = `${authorTag}${emoji}`;

    dom.emoteParticleLayer.appendChild(bubble);

    if (window.caster) {
        if (emoteKey === "fire" || emoteKey === "speed") caster.playSfx("combo");
        else if (emoteKey === "panic") caster.playSfx("error");
        else caster.playSfx("valid");
    }

    setTimeout(() => {
        bubble.remove();
    }, 2300);
}

function joinAsSpectator() {
    const code = dom.joinCodeInput.value.trim().toUpperCase();
    if (code.length !== 4) {
        showToast(window.i18n ? i18n.t("toast_invalid_code") : "Code à 4 lettres invalide.", "error");
        return;
    }
    const defaultName = window.i18n ? i18n.t("default_player_2") : "Spectateur";
    const rawName = (dom.playerNameInput ? dom.playerNameInput.value.trim() : "") || defaultName;
    state.playerName = rawName;
    state.roomCode = code;
    state.isHost = false;
    state.isSpectator = true;

    dom.displayRoomCode.textContent = state.roomCode;
    dom.p1Name.textContent = state.playerName;

    dom.lobbySection.classList.add("hidden");
    dom.gameSection.classList.remove("hidden");
    dom.gameSection.classList.add("spectator-view");
    if (dom.spectatorRoleTag) dom.spectatorRoleTag.classList.remove("hidden");
    document.body.classList.add("in-game");
    if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");

    connectWebSocket(state.roomCode);
}

// Actions rétro-compatibles
if (dom.btnCreateRoom) {
    dom.btnCreateRoom.addEventListener("click", createRoomGame);
}

if (dom.btnJoinRoom) {
    dom.btnJoinRoom.addEventListener("click", () => {
        const code = dom.joinCodeInput.value.trim().toUpperCase();
        if (code.length !== 4) {
            showToast(window.i18n ? i18n.t("toast_invalid_code") : "Code à 4 lettres invalide.", "error");
            return;
        }
        const defaultName = window.i18n ? i18n.t("default_player_2") : "Joueur 2";
        state.playerName = (dom.playerNameInput ? dom.playerNameInput.value.trim() : "") || defaultName;
        state.roomCode = code;
        state.isHost = false;

        dom.displayRoomCode.textContent = state.roomCode;
        const meTag = window.i18n ? i18n.t("player_me_tag") : "(Moi)";
        dom.p1Name.textContent = `${state.playerName} ${meTag}`;

        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        document.body.classList.add("in-game");
        if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");

        connectWebSocket(state.roomCode);
    });
}

if (dom.btnPlayAi) {
    dom.btnPlayAi.addEventListener("click", startSoloAiGame);
}

dom.btnStartGame.addEventListener("click", () => {
    if (state.socket) {
        state.socket.send(JSON.stringify({ action: "START_GAME" }));
    }
});

dom.btnLeaveRoom.addEventListener("click", () => {
    window.location.reload();
});

dom.btnBackLobby.addEventListener("click", () => {
    window.location.reload();
});

dom.btnRematch.addEventListener("click", () => {
    window.location.reload();
});

if (dom.btnShareCard) {
    dom.btnShareCard.addEventListener("click", () => {
        const modeTitle = state.mode === "clash" ? "Mode Clash ⚡" : (state.mode === "race" ? "Mode Course 🏎️" : "Duel vs Bot 🤖");
        const outcome = dom.modalWinnerTitle ? dom.modalWinnerTitle.textContent : "MATCH TERMINÉ";
        const badge = dom.postGameBadge ? dom.postGameBadge.textContent : "";
        const time = dom.statMatchTime ? dom.statMatchTime.textContent : "00:00";
        const acc = dom.statAccuracy ? dom.statAccuracy.textContent : "100%";
        const combo = dom.statMaxCombo ? dom.statMaxCombo.textContent : "x1";
        const errs = dom.statErrors ? dom.statErrors.textContent : "0";

        const shareText = `🎮 SUDOKU ARENA — RAPPORT DE MATCH 🏆\n` +
            `Discipline : ${modeTitle}\n` +
            `Résultat : ${outcome}\n` +
            `Distinction : ${badge}\n` +
            `⏱️ Durée : ${time} | 🎯 Précision : ${acc}\n` +
            `⚡ Max Combo : ${combo} | ❌ Fautes : ${errs}\n` +
            `Rejoignez l'arène : https://sudoku-arena-frontend.vercel.app`;

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(shareText).then(() => {
                showToast(window.i18n ? i18n.t("card_copied_toast") : "📋 Bilan du match copié dans le presse-papier !", "success");
            }).catch(() => {
                showToast("Erreur lors de la copie", "error");
            });
        }
    });
}

if (dom.btnReplayDebrief) {
    dom.btnReplayDebrief.addEventListener("click", () => {
        const text = state.lastDebriefText || (dom.modalDebriefText ? dom.modalDebriefText.textContent : "");
        const lang = (window.i18n && window.i18n.currentLang) || "fr";
        if (text && window.caster) {
            caster.speakWebSpeech(text, lang, { rate: 1.05 });
        }
    });
}

dom.btnErase.addEventListener("click", () => {
    if ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId) {
        showToast(window.i18n ? i18n.t("not_your_turn") : "Ce n'est pas votre tour !", "error");
        return;
    }
    if (state.selectedCell) {
        const { row, col } = state.selectedCell;
        const cellEl = document.querySelector(`.cell[data-row='${row}'][data-col='${col}']`);
        if (cellEl && !cellEl.classList.contains("fixed") && !cellEl.classList.contains("user-filled") && !cellEl.classList.contains("opponent-filled")) {
            cellEl.textContent = "";
        }
    }
});

// Pavé Tactile
document.querySelectorAll(".numpad-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        const val = parseInt(btn.dataset.val, 10);
        handleInput(val);
    });
});

// Accessibilité & Navigation Clavier Complète
window.addEventListener("keydown", (e) => {
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
        e.preventDefault();
        let curRow = state.selectedCell ? state.selectedCell.row : 0;
        let curCol = state.selectedCell ? state.selectedCell.col : 0;
        if (e.key === "ArrowUp") curRow = Math.max(0, curRow - 1);
        if (e.key === "ArrowDown") curRow = Math.min(8, curRow + 1);
        if (e.key === "ArrowLeft") curCol = Math.max(0, curCol - 1);
        if (e.key === "ArrowRight") curCol = Math.min(8, curCol + 1);
        selectCell(curRow, curCol);
    } else if (e.key >= "1" && e.key <= "9") {
        handleInput(parseInt(e.key, 10));
    } else if (e.key === "Backspace" || e.key === "Delete") {
        dom.btnErase.click();
    } else if (document.activeElement && document.activeElement.tagName !== "INPUT") {
        const k = e.key.toLowerCase();
        if (k === "f") sendEmote("fire");
        else if (k === "b") sendEmote("brain");
        else if (k === "s") sendEmote("speed");
        else if (k === "p") sendEmote("panic");
        else if (k === "g") sendEmote("gg");
        else if (k === "k") sendEmote("fraid");
    }
});

// Initialisation au chargement
document.addEventListener("DOMContentLoaded", () => {
    initVirtualLedStrip();

    // 1. Initialiser le système trilingue
    if (window.i18n) {
        window.i18n.updateDOM();
        
        // Mettre à jour l'état actif des boutons de langue
        const currentLang = window.i18n.currentLang;
        document.querySelectorAll(".lang-btn").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.lang === currentLang);
            btn.addEventListener("click", () => {
                const lang = btn.dataset.lang;
                window.i18n.setLanguage(lang);
                document.querySelectorAll(".lang-btn").forEach(b => b.classList.toggle("active", b === btn));
                if (window.caster) caster.comment("WELCOME");
            });
        });
    }

        // Réagir aux changements de langue
        window.addEventListener("languageChanged", () => {
            updateValidationHelp(dom.validationMode, dom.validationHelp);
            const currentLang = (window.i18n && window.i18n.currentLang) || "fr";
            const defaultNames = ["Joueur 1", "Player 1", "Spieler 1", ""];
            if (defaultNames.includes(state.playerName)) {
                state.playerName = window.i18n ? i18n.t("default_player_name") : "Joueur 1";
            }
            if (dom.p1Name) {
                const meTag = window.i18n ? i18n.t("player_me_tag") : "(Moi)";
                dom.p1Name.textContent = `${state.playerName} ${meTag}`;
            }
            if (state.isAiMatch && dom.p2Name) {
                const diffLabels = {
                    easy: window.i18n ? i18n.t("diff_label_novice") : "NOVICE",
                    medium: window.i18n ? i18n.t("diff_label_tactique") : "TACTIQUE",
                    hard: window.i18n ? i18n.t("diff_label_grand_maitre") : "GRAND MAÎTRE"
                };
                const diffName = diffLabels[state.difficulty] || "TACTIQUE";
                const botLabel = window.i18n ? i18n.t("bot_rival_name") : "KI FRAID (Bot Rival 🤖)";
                dom.p2Name.textContent = `${botLabel} [${diffName}]`;
                if (dom.displayModeBadge) {
                    const valName = state.validationMode === "simple" 
                        ? (window.i18n ? i18n.t("val_mode_simple_label") : "SIMPLE") 
                        : (window.i18n ? i18n.t("val_mode_strict_label") : "STRICT");
                    const botPersona = currentLang === "fr" ? "L'IA FRAID" : (currentLang === "en" ? "AI FRAID" : "KI FRAID");
                    dom.displayModeBadge.textContent = `🤖 ${botPersona} (${diffName}) [${valName}]`;
                }
            }
            if (state.currentTurn) {
                updateTurnUI(state.currentTurn, state.turnTimeout);
            }
            if (dom.btnToggleVoice && window.caster) {
                dom.btnToggleVoice.title = caster.isVoiceEnabled 
                    ? (window.i18n ? i18n.t("voice_on") : "Voix activée") 
                    : (window.i18n ? i18n.t("voice_off") : "Voix coupée");
            }

            // Rafraîchir les libellés dynamiques du Command Center
            setDiscipline(state.mode || "clash");
        });

    // 2. Initialiser le pupitre de KI FRAID Caster
    if (dom.btnToggleVoice && window.caster) {
        dom.btnToggleVoice.addEventListener("click", () => {
            const active = caster.toggleVoice();
            if (dom.voiceIcon) dom.voiceIcon.textContent = active ? "🔊" : "🔇";
            dom.btnToggleVoice.title = active 
                ? (window.i18n ? i18n.t("voice_on") : "Voix activée") 
                : (window.i18n ? i18n.t("voice_off") : "Voix coupée");
        });
    }

    // 3. Initialiser le Command Center E-Sport & Guide Modal
    initCommandCenter();

    // 4. Salutation de bienvenue du Commentateur
    setTimeout(() => {
        if (window.caster) caster.comment("WELCOME");
    }, 600);
});


