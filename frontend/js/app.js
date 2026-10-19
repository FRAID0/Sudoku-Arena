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
    try {
        const ctx = getAudioContext();
        if (ctx.state === "suspended") ctx.resume();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = frequency;
        osc.connect(gain);
        gain.connect(ctx.destination);
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
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
    playerName: "Joueur 1",
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
    reconnectTimeout: null
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
    aiValidationMode: document.getElementById("aiValidationMode"),
    aiValidationHelp: document.getElementById("aiValidationHelp"),
    aiDifficultySelect: document.getElementById("aiDifficulty"),
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
    btnBackLobby: document.getElementById("btnBackLobby")
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
}

function handleInput(number) {
    // Vérification du tour en mode Clash
    if ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId) {
        playBeep(180, 0.15);
        showToast("⏳ Ce n'est pas votre tour !", "error");
        return;
    }

    if (!state.selectedCell) {
        showToast("Sélectionnez d'abord une case vide !", "info");
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
        showToast("Connexion au serveur interrompue...", "error");
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
            dom.turnLabel.textContent = "⏳ À VOTRE TOUR !";
            dom.turnLabel.style.color = "var(--neon-blue)";
        }
        if (dom.turnCountdown) dom.turnCountdown.style.color = "var(--neon-blue)";
        if (dom.p1Card) dom.p1Card.classList.add("active-turn");
        if (dom.p2Card) dom.p2Card.classList.remove("active-turn", "is-p2");
        dom.sudokuGrid.classList.remove("disabled-turn");
        if (dom.controlsContainer) dom.controlsContainer.classList.remove("disabled-turn");
        playBeep(587.33, 0.12); // Ton de notification (Ré)
    } else {
        const oppName = (state.isAiMatch ? "KI FRAID" : (dom.p2Name.textContent || "Adversaire")).replace(" (Moi)", "");
        if (dom.turnLabel) {
            dom.turnLabel.textContent = state.isAiMatch 
                ? "🧠 KI FRAID ANALYSE LA GRILLE..." 
                : `⏳ TOUR DE ${oppName.toUpperCase()}...`;
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
    const wsUrl = `${protocol}//${BACKEND_HOST}/ws/${roomCode}/${state.playerId}/${encodeURIComponent(state.playerName)}`;

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
        } else if (msg.event === "COUNTDOWN") {
            dom.countdownOverlay.classList.remove("hidden");
            dom.countdownNumber.textContent = msg.count;
            playBeep(msg.count === 1 ? 660 : 440, 0.18);
        } else if (msg.event === "GAME_STARTED") {
            dom.countdownOverlay.classList.add("hidden");
            dom.matchStatusText.textContent = "🔥 MATCH EN COURS";
            dom.btnStartGame.classList.add("hidden");
            state.turnTimeout = msg.turn_timeout || 20.0;
            state.currentTurn = msg.current_turn;

            // Verrouiller la vue en 100dvh zéro-scroll
            if (dom.arenaContainer) dom.arenaContainer.classList.add("in-game");

            if (msg.shared_grid && (state.mode === "clash" || state.mode === "solo_ai")) {
                buildBoardUI(msg.shared_grid);
            } else {
                buildBoardUI(msg.initial_puzzle);
            }

            triggerLedEffect("success");
            playBeep(980, 0.3); // Son de lancement
            updateTurnUI(msg.current_turn, state.turnTimeout);
        } else if (msg.event === "MOVE_RESULT") {
            const res = msg.result;

            // Cas de coup rejeté (ex: pas ton tour, case déjà remplie, hors bornes)
            if (res.rejected) {
                playBeep(180, 0.2);
                const reason = res.reason || "Coup rejeté par le serveur.";
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
                }
                triggerLedEffect("success");
                if (res.player_id === state.playerId) {
                    playBeep(523.25, 0.12);
                }
            } else {
                if (cellEl) {
                    cellEl.classList.add("error-red", "error-shake");
                    setTimeout(() => cellEl.classList.remove("error-red", "error-shake"), 400);
                }
                triggerLedEffect("error");
                playBeep(220, 0.25);
                if (res.player_id === state.playerId) {
                    const reason = res.reason || "Chiffre incorrect ou conflit !";
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
                showGameOver(res.winner_id === state.playerId, res.winner_id === "DRAW");
            }
        } else if (msg.event === "TURN_TIMEOUT") {
            const res = msg.result;
            triggerLedEffect("error");
            playBeep(196, 0.3);

            if (res.timed_out_player_id === state.playerId) {
                dom.p1Score.textContent = `${res.score} pts`;
                showToast("⏰ Temps écoulé ! Pénalité de 1 point.", "error");
            } else {
                dom.p2Score.textContent = `${res.score} pts`;
                showToast("⏰ Temps écoulé pour l'adversaire !", "info");
            }

            state.currentTurn = res.current_turn;
            updateTurnUI(res.current_turn, state.turnTimeout);
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
            showToast("Connexion au serveur perdue. Rafraîchissez la page.", "error", 6000);
        }
    };

    state.socket.onerror = (err) => {
        console.error("Erreur WebSocket :", err);
    };
}

function updatePlayersLobby(players) {
    const p1 = players.find(p => p.id === state.playerId);
    const p2 = players.find(p => p.id !== state.playerId);

    if (p1) dom.p1Name.textContent = p1.name + " (Moi)";
    if (p2) {
        dom.p2Name.textContent = p2.name;
        dom.matchStatusText.textContent = "Prêt à démarrer !";
        if (state.isHost) dom.btnStartGame.classList.remove("hidden");
    } else {
        dom.p2Name.textContent = "En attente...";
        dom.matchStatusText.textContent = "Partagez le code du salon !";
    }
}

function showGameOver(isWinner, isDraw = false) {
    stopTurnTimer();
    triggerLedEffect("victory");

    if (isDraw) {
        dom.modalWinnerTitle.textContent = "ÉGALITÉ ! 🤝";
        dom.modalWinnerDesc.textContent = "Score parfaitement identique à l'issue de la grille !";
    } else {
        dom.modalWinnerTitle.textContent = isWinner ? "VICTOIRE ! 🏆" : "DÉFAITE ! 💥";
        dom.modalWinnerDesc.textContent = isWinner
            ? "Félicitations, vous remportez le duel au sommet de l'arène !"
            : "Votre adversaire s'impose sur cette manche.";
    }
    dom.gameOverModal.classList.remove("hidden");
    playBeep(isWinner ? 880 : 180, 0.6);
}

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
if (dom.aiValidationMode && dom.aiValidationHelp) {
    dom.aiValidationMode.addEventListener("change", () => updateValidationHelp(dom.aiValidationMode, dom.aiValidationHelp));
}

// Actions du Lobby
dom.btnCreateRoom.addEventListener("click", async () => {
    state.playerName = dom.playerNameInput.value.trim() || "Joueur 1";
    const difficulty = dom.difficultySelect.value;
    const mode = dom.gameModeSelect ? dom.gameModeSelect.value : "clash";
    const validationMode = dom.validationMode ? dom.validationMode.value : "simple";
    state.mode = mode;
    state.difficulty = difficulty;
    state.validationMode = validationMode;

    try {
        const res = await fetch(`${API_BASE_URL}/api/rooms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: mode,
                difficulty: difficulty,
                validation_mode: validationMode
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;
        state.isHost = true;

        dom.displayRoomCode.textContent = state.roomCode;
        if (dom.displayModeBadge) {
            const modeName = mode === "clash" ? "⚡ CLASH" : "🏎️ COURSE";
            const valName = validationMode === "simple" ? "SIMPLE" : "STRICT";
            dom.displayModeBadge.textContent = `${modeName} [${valName}]`;
        }

        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        buildBoardUI(data.initial_puzzle);

        connectWebSocket(state.roomCode);
    } catch (err) {
        showToast("Erreur lors de la création du salon : " + err, "error");
    }
});

dom.btnJoinRoom.addEventListener("click", () => {
    const code = dom.joinCodeInput.value.trim().toUpperCase();
    if (code.length !== 4) {
        showToast("Code à 4 lettres invalide.", "error");
        return;
    }
    state.playerName = dom.playerNameInput.value.trim() || "Challenger";
    state.roomCode = code;
    state.isHost = false;

    dom.displayRoomCode.textContent = state.roomCode;
    dom.lobbySection.classList.add("hidden");
    dom.gameSection.classList.remove("hidden");

    connectWebSocket(state.roomCode);
});

// Duel solo contre KI FRAID
dom.btnPlayAi.addEventListener("click", async () => {
    state.playerName = dom.playerNameInput.value.trim() || "Joueur";
    state.isAiMatch = true;
    state.isHost = true;
    state.mode = "solo_ai";
    const chosenDiff = dom.aiDifficultySelect ? dom.aiDifficultySelect.value : "medium";
    const validationMode = dom.aiValidationMode ? dom.aiValidationMode.value : "simple";
    state.difficulty = chosenDiff;
    state.validationMode = validationMode;

    try {
        const res = await fetch(`${API_BASE_URL}/api/rooms`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: "solo_ai",
                difficulty: chosenDiff,
                validation_mode: validationMode
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;

        const diffLabels = { easy: "NOVICE", medium: "TACTIQUE", hard: "GRAND MAÎTRE" };
        const diffName = diffLabels[chosenDiff] || "TACTIQUE";

        dom.displayRoomCode.textContent = "VS-AI";
        if (dom.displayModeBadge) {
            const valName = validationMode === "simple" ? "SIMPLE" : "STRICT";
            dom.displayModeBadge.textContent = `🤖 KI FRAID (${diffName}) [${valName}]`;
        }
        dom.p1Name.textContent = state.playerName + " (Moi)";
        dom.p2Name.textContent = `KI FRAID (${diffName}) 🤖`;
        dom.matchStatusText.textContent = "Départ imminent...";

        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        dom.btnStartGame.classList.add("hidden");

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
        showToast("Erreur démarrage solo IA : " + err, "error");
    }
});

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

dom.btnErase.addEventListener("click", () => {
    if ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId) {
        showToast("Ce n'est pas votre tour !", "error");
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
    }
});

// Initialisation au chargement
document.addEventListener("DOMContentLoaded", () => {
    initVirtualLedStrip();
});
