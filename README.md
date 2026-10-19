# 🎯 Sudoku Arena (Cloud-Native IoT Edition)

> **Real-Time Multiplayer & AI Sudoku Arena** with event-driven architecture, virtual IoT reactive lighting, dual validation logic, and Kubernetes-orchestrated microservices.

[![CI Pipeline](https://github.com/FRAID0/Sudoku-Arena/actions/workflows/ci.yml/badge.svg)](https://github.com/FRAID0/Sudoku-Arena/actions)
[![Live Demo](https://img.shields.io/badge/Demo-Live%20on%20Vercel-success)](https://sudoku-arena-frontend.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-Northflank%20Cloud-blue)](https://p01--sudoku-backend--hvzj8dcpgjs4.code.run/health)

---

## 🌐 Démo Publique en Direct (100% Gratuite)

- **Frontend (Vercel Edge) :** [https://sudoku-arena-frontend.vercel.app](https://sudoku-arena-frontend.vercel.app)
- **Backend (Northflank Developer Sandbox) :** [https://p01--sudoku-backend--hvzj8dcpgjs4.code.run](https://p01--sudoku-backend--hvzj8dcpgjs4.code.run)
- **Health Check :** [https://p01--sudoku-backend--hvzj8dcpgjs4.code.run/health](https://p01--sudoku-backend--hvzj8dcpgjs4.code.run/health)

---

## 🚀 Highlights & Gameplay V2

- ⚔️ **Mode Clash (Tour par Tour)** : Duel 1v1 en temps réel sur une grille commune avec chrono individuel, points de rapidité et pénalités.
- 🏎️ **Mode Course (Speedrun Miroir)** : Chaque joueur résout la même grille en parallèle avec jauges de progression synchronisées en direct.
- 🤖 **KI FRAID (Bot IA)** : 3 niveaux de jeu autonomes (Novice, Tactique, Grand Maître) avec délais de réflexion réalistes et taux d'erreurs calibré.
- ✨ **Validation Duale** :
  - **Mode Simple (Règles locales)** : Tout chiffre conforme aux règles de ligne, colonne et bloc 3x3 immédiat est accepté (zéro frustration).
  - **Mode Casse-Tête (Solution unique)** : Seule la solution secrète mathématique unique est validée (mode puriste compétition).
- 💡 **Ruban LED Virtuel IoT (WS2812B NeoPixel)** : Signalétique lumineuse par camp (cyan pour Joueur 1, violet pour Joueur 2 / Bot), impulsions vertes sur coup juste et onde rouge sur faute ou buzzer.
- 📱 **Ergonomie Zéro-Scroll (100dvh)** : Interface verrouillée sur un seul écran sans défilement vertical, navigation clavier intégrale (flèches + 1-9) et accessibilité tactile mobile.

---

## 🏛️ Stratégie d'Architecture DevOps (2 Niveaux)

```
[ Niveau 1 : Démo Publique (Portfolio & Recruteurs) ]
   Navigateur Web ──────► Vercel (Frontend CDN Edge)
         │
         └──────────────► Northflank (FastAPI + WebSockets toujours actif, 0.1 vCPU / 256MB)

[ Niveau 2 : Laboratoire Kubernetes Local (Démonstration DevOps) ]
   Cluster local Kind / Minikube (6 Pods) :
   ├── 3x Réplicas Backend (FastAPI, Liveness & Readiness Probes, Auto-restart)
   ├── 2x Réplicas Frontend (Nginx, Service LoadBalancer)
   ├── 1x Broker Mosquitto (MQTT / WebSockets)
   └── CI/CD GitHub Actions (.github/workflows/ci.yml : Pytest, Docker Build, Kubectl Dry-run)
```

---

## 📁 Repository Structure

```
Sudoku-Arena/
├── backend/            # Moteur Python FastAPI (SudokuEngine, RoomManager, KI FRAID Bot)
│   ├── app/            # Code source applicatif et WebSockets
│   └── tests/          # Suite de tests unitaires automatisés (18 tests pytest)
├── frontend/           # Interface Web Neo-Arcade (HTML5, Vanilla CSS 100dvh, WebSocket client)
│   ├── css/            # Thème Cyberpunk, animations LED et toasts d'alerte
│   └── js/             # Logique temps réel, navigation clavier et reconnexion
├── k8s/                # Manifests Kubernetes (Deployments, Services, ConfigMap)
├── mosquitto/          # Configuration broker MQTT (listeners 1883 & 9001 WSS)
├── docs/               # Cahier des charges et Product Backlog Scrum
└── docker-compose.yml  # Environnement multi-conteneurs pour développement local
```

---

## 🛠️ Lancer en Local

### Avec Docker Compose
```bash
docker compose up --build
```
Ouvrez `http://localhost:8080` dans votre navigateur.

### Avec la suite de tests automatisés
```bash
pytest backend/tests/ -v
```

---

## 📜 License
MIT License - Créé avec ❤️ par [FRAID0](https://github.com/FRAID0)

