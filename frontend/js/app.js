/**
 * Sudoku Arena — Frontend Game Engine & WebSocket Client
 * Gère le décompte synchrone, le bot KI FRAID, l'audio synthétique et le ruban LED IoT.
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
        // Fallback silencieux si l'audio est bloqué par le navigateur
    }
}

// État de l'application
const state = {
    playerId: "player_" + Math.random().toString(36).substring(2, 9),
    playerName: "Joueur 1",
    roomCode: null,
    isHost: false,
    selectedCell: null,
    grid: null,
    socket: null,
    isAiMatch: false
};

// Éléments du DOM
const dom = {
    lobbySection: document.getElementById("lobbySection"),
    gameSection: document.getElementById("gameSection"),
    playerNameInput: document.getElementById("playerName"),
    difficultySelect: document.getElementById("gameDifficulty"),
    btnCreateRoom: document.getElementById("btnCreateRoom"),
    btnJoinRoom: document.getElementById("btnJoinRoom"),
    btnPlayAi: document.getElementById("btnPlayAi"),
    joinCodeInput: document.getElementById("joinCodeInput"),
    displayRoomCode: document.getElementById("displayRoomCode"),
    matchStatusText: document.getElementById("matchStatusText"),
    btnStartGame: document.getElementById("btnStartGame"),
    btnLeaveRoom: document.getElementById("btnLeaveRoom"),
    btnErase: document.getElementById("btnErase"),
    sudokuGrid: document.getElementById("sudokuGrid"),
    ledStrip: document.getElementById("ledStrip"),
    p1Name: document.getElementById("p1Name"),
    p2Name: document.getElementById("p2Name"),
    p1Score: document.getElementById("p1Score"),
    p2Score: document.getElementById("p2Score"),
    p1ProgressFill: document.getElementById("p1ProgressFill"),
    p2ProgressFill: document.getElementById("p2ProgressFill"),
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
    if (cellEl && cellEl.classList.contains("fixed")) return;

    document.querySelectorAll(".cell").forEach(c => c.classList.remove("selected"));
    state.selectedCell = { row, col };
    if (cellEl) cellEl.classList.add("selected");
}

function handleInput(number) {
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
            buildBoardUI(msg.initial_puzzle);
            triggerLedEffect("success");
            playBeep(980, 0.3); // Son de lancement aigu
        } else if (msg.event === "MOVE_RESULT") {
            const res = msg.result;
            if (res.player_id === state.playerId) {
                const cellEl = document.querySelector(`.cell[data-row='${res.row}'][data-col='${res.col}']`);
                if (res.valid) {
                    if (cellEl) {
                        cellEl.textContent = res.value;
                        cellEl.classList.add("user-filled");
                    }
                    dom.p1Score.textContent = `${res.score} pts`;
                    dom.p1ProgressFill.style.width = `${res.progress}%`;
                    triggerLedEffect("success");
                    playBeep(523.25, 0.12); // Do aigu (succès)
                } else {
                    if (cellEl) {
                        cellEl.classList.add("error-shake");
                        setTimeout(() => cellEl.classList.remove("error-shake"), 300);
                    }
                    triggerLedEffect("error");
                    playBeep(220, 0.25); // Faible (erreur)
                }
            } else {
                // Coup de l'adversaire ou du bot
                if (res.valid) {
                    dom.p2Score.textContent = `${res.score} pts`;
                    dom.p2ProgressFill.style.width = `${res.progress}%`;
                }
            }

            if (res.game_over) {
                showGameOver(res.winner_id === state.playerId);
            }
        }
    };

    state.socket.onclose = () => {
        console.log("WebSocket déconnecté.");
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

function showGameOver(isWinner) {
    triggerLedEffect("victory");
    dom.modalWinnerTitle.textContent = isWinner ? "VICTOIRE ! 🏆" : "DÉFAITE ! 💥";
    dom.modalWinnerDesc.textContent = isWinner 
        ? "Félicitations, vous avez triomphé dans l'arène !" 
        : "Votre adversaire a complété sa grille plus vite.";
    dom.gameOverModal.classList.remove("hidden");
    playBeep(isWinner ? 880 : 180, 0.6);
}

// Navigation & Actions
dom.btnCreateRoom.addEventListener("click", async () => {
    state.playerName = dom.playerNameInput.value.trim() || "Joueur 1";
    const difficulty = dom.difficultySelect.value;

    try {
        const res = await fetch("/api/rooms", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: "race",
                difficulty: difficulty
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;
        state.isHost = true;

        dom.displayRoomCode.textContent = state.roomCode;
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

    try {
        const res = await fetch("/api/rooms", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                host_id: state.playerId,
                host_name: state.playerName,
                mode: "solo_ai",
                difficulty: dom.difficultySelect.value
            })
        });
        const data = await res.json();
        state.roomCode = data.room_code;

        dom.displayRoomCode.textContent = "VS-AI";
        dom.p1Name.textContent = state.playerName + " (Moi)";
        dom.p2Name.textContent = "KI FRAID 🤖";
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
    if (state.selectedCell) {
        const { row, col } = state.selectedCell;
        const cellEl = document.querySelector(`.cell[data-row='${row}'][data-col='${col}']`);
        if (cellEl && !cellEl.classList.contains("fixed")) {
            cellEl.textContent = "";
            cellEl.classList.remove("user-filled");
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
