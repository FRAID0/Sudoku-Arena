# 🎯 Sudoku Arena (Cloud-Native IoT Edition)

> **Real-Time Multiplayer & AI Sudoku Arena** with event-driven architecture, virtual IoT reactive lighting, and Kubernetes-ready microservices.

---

## 🚀 Overview

**Sudoku Arena** is a modern reimagining of a Raspberry Pi IoT Sudoku battle station. It transforms a hardware turn-based Sudoku puzzle game into a full-scale **Cloud-Native multiplayer platform**.

### ✨ Highlights
- ⚔️ **Multiplayer 1v1 Arena**: Duel friends in real-time on a shared board with turn timers and point stealing.
- 🤖 **KI FRAID (AI Opponent)**: Intelligent Sudoku bot with 3 difficulty modes and human-like delays.
- 💡 **Virtual IoT LED Matrix**: Visual feedback simulation (WS2812b NeoPixel style) showing turns, correct numbers, errors, and game-over animations.
- ⚡ **Event-Driven Architecture**: Ultra-low latency state synchronization powered by MQTT & WebSockets.
- ☸️ **Kubernetes Ready**: Packaged for scalable multi-pod deployment with Ingress and health probes.

---

## 🏗️ Architecture

```
                 [ Web Browser (Player 1) ]        [ Web Browser (Player 2) ]
                             │                                 │
                             └────────────► WSS ◄──────────────┘
                                            │
                                            ▼
                               [ Ingress Controller / Proxy ]
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
         [ Mosquitto Broker ]                             [ Frontend Nginx ]
             (MQTT / WSS)                                    (HTML5 / JS)
                     │
                     ▼
         [ Sudoku Game Engine ]
          (Python Microservice)
```

---

## 📁 Repository Structure

```
Sudoku-Arena/
├── backend/            # Python Game Engine (Sudoku logic, AI bot, multi-room state)
├── frontend/           # Modern Web UI (Cyberpunk theme, responsive board, virtual LED strip)
├── mosquitto/          # MQTT Broker configuration (WebSockets enabled)
├── k8s/                # Kubernetes deployment manifests
└── docker-compose.yml  # Local multi-container development environment
```

---

## 🛠️ Getting Started (Local Development)

### Prerequisites
- Docker & Docker Compose
- Git

### Run with Docker Compose
```bash
docker-compose up --build
```
Open `http://localhost:8080` in your browser.

---

## 📜 License
MIT License - Created with ❤️ by [FRAID0](https://github.com/FRAID0)
