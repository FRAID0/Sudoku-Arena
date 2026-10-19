/**
 * Sudoku Arena — Frontend Game Engine & WebSocket Client
 * Gère le décompte synchrone, le mode Clash (Tour par Tour), le mode Course,
 * le bot KI FRAID, l'audio synthétique et le ruban LED IoT.
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

// État de l'application
const state = {
    playerId: "player_" + Math.random().toString(36).substring(2, 9),
    playerName: "Joueur 1",
    roomCode: null,
    isHost: false,
    mode: "clash", // "clash" | "race" | "solo_ai"
    difficulty: "medium",
    selectedCell: null,
    grid: null,
    socket: null,
    isAiMatch: false,
    currentTurn: null,
    turnTimeout: 20.0,
    timerInterval: null
};

// Éléments du DOM
const dom = {
    lobbySection: document.getElementById("lobbySection"),
    gameSection: document.getElementById("gameSection"),
    playerNameInput: document.getElementById("playerName"),
    gameModeSelect: document.getElementById("gameMode"),
    difficultySelect: document.getElementById("gameDifficulty"),
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

function triggerLedEffect(effect) {
    const pixels = document.querySelectorAll(".led-pixel");
    pixels.forEach((p, idx) => {
        p.className = "led-pixel";
        if (effect === "success") {
            setTimeout(() => { p.classList.add("green"); }, idx * 8);
            setTimeout(() => { p.className = "led-pixel"; }, 600);
        } else if (effect === "error") {
            p.classList.add("red");
            setTimeout(() => { p.className = "led-pixel"; }, 400);
        } else if (effect === "blue") {
            setTimeout(() => { p.classList.add("blue"); }, idx * 8);
            setTimeout(() => { p.className = "led-pixel"; }, 500);
        } else if (effect === "victory") {
            setTimeout(() => { p.classList.add("rainbow"); }, idx * 15);
        }
    });
}

// Construction de la grille 9x9
function buildBoardUI(initialPuzzle) {
    dom.sudokuGrid.innerHTML = "";
    state.grid = JSON.parse(JSON.stringify(initialPuzzle));

    for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
            const cell = document.createElement("div");
            cell.className = "cell";
            cell.dataset.row = r;
            cell.dataset.col = c;

            const val = initialPuzzle[r][c];
            if (val !== 0) {
                cell.textContent = val;
                cell.classList.add("fixed");
            }

            cell.addEventListener("click", () => selectCell(r, c));
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
    // est réservée au mode Facile (Novice). En Moyen et Difficile, le joueur doit rester 100% focus.
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

    // Si la case est déjà fixée/remplie ou si ce n'est pas notre tour, elle n'est pas modifiable
    if (isFilled || ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId)) {
        state.selectedCell = null;
        return;
    }

    state.selectedCell = { row, col };
}

function handleInput(number) {
    // Vérification du tour en mode Clash
    if ((state.mode === "clash" || state.mode === "solo_ai") && state.currentTurn && state.currentTurn !== state.playerId) {
        playBeep(180, 0.15); // Bloqué
        return;
    }

    if (!state.selectedCell) return;
    const { row, col } = state.selectedCell;

    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({
            action: "PLAY_MOVE",
            row: row,
            col: col,
            value: number
        }));
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
        playBeep(587.33, 0.12); // Ton de notification de prise de main (Ré)
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

    startTurnTimer(timeoutSeconds || state.turnTimeout);
}

// Connexion WebSocket
function connectWebSocket(roomCode, onOpenCallback = null) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${roomCode}/${state.playerId}/${encodeURIComponent(state.playerName)}`;

    state.socket = new WebSocket(wsUrl);

    state.socket.onopen = () => {
        console.log("WebSocket connecté au salon :", roomCode);
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
            if (res.rejected) {
                playBeep(180, 0.2);
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
            }

            // Mise à jour des scores
            if (res.player_id === state.playerId) {
                dom.p1Score.textContent = `${res.score} pts`;
                dom.p1ProgressFill.style.width = `${res.progress}%`;
            } else {
                dom.p2Score.textContent = `${res.score} pts`;
                dom.p2ProgressFill.style.width = `${res.progress}%`;
            }

            // Gestion de l'alternance de tour
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
            playBeep(196, 0.3); // Son d'expiration buzzer

            if (res.timed_out_player_id === state.playerId) {
                dom.p1Score.textContent = `${res.score} pts`;
            } else {
                dom.p2Score.textContent = `${res.score} pts`;
            }

            state.currentTurn = res.current_turn;
            updateTurnUI(res.current_turn, state.turnTimeout);
        }
    };

    state.socket.onclose = () => {
        console.log("WebSocket déconnecté.");
        stopTurnTimer();
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

// Navigation & Actions
dom.btnCreateRoom.addEventListener("click", async () => {
    state.playerName = dom.playerNameInput.value.trim() || "Joueur 1";
    const difficulty = dom.difficultySelect.value;
    const mode = dom.gameModeSelect ? dom.gameModeSelect.value : "clash";
    state.mode = mode;
    state.difficulty = difficulty;

    try {
        const res = await fetch("/api/rooms", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: mode,
                difficulty: difficulty
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;
        state.isHost = true;

        dom.displayRoomCode.textContent = state.roomCode;
        if (dom.displayModeBadge) {
            dom.displayModeBadge.textContent = mode === "clash" ? "⚡ CLASH" : "🏎️ COURSE";
        }

        dom.lobbySection.classList.add("hidden");
        dom.gameSection.classList.remove("hidden");
        buildBoardUI(data.initial_puzzle);

        connectWebSocket(state.roomCode);
    } catch (err) {
        alert("Erreur lors de la création du salon : " + err);
    }
});

dom.btnJoinRoom.addEventListener("click", () => {
    const code = dom.joinCodeInput.value.trim().toUpperCase();
    if (code.length !== 4) {
        alert("Code à 4 lettres invalide.");
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
    state.difficulty = chosenDiff;

    try {
        const res = await fetch("/api/rooms", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: "solo_ai",
                difficulty: chosenDiff
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;

        const diffLabels = { easy: "NOVICE", medium: "TACTIQUE", hard: "GRAND MAÎTRE" };
        const diffName = diffLabels[chosenDiff] || "TACTIQUE";

        dom.displayRoomCode.textContent = "VS-AI";
        if (dom.displayModeBadge) {
            dom.displayModeBadge.textContent = `🤖 VS KI FRAID (${diffName})`;
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
        alert("Erreur démarrage solo IA : " + err);
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

// Pavé Tactile & Clavier
document.querySelectorAll(".numpad-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        const val = parseInt(btn.dataset.val, 10);
        handleInput(val);
    });
});

window.addEventListener("keydown", (e) => {
    if (e.key >= "1" && e.key <= "9") {
        handleInput(parseInt(e.key, 10));
    } else if (e.key === "Backspace" || e.key === "Delete") {
        dom.btnErase.click();
    }
});

// Initialisation au chargement
document.addEventListener("DOMContentLoaded", () => {
    initVirtualLedStrip();
});
