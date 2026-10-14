# 📋 Cahier des Charges & Document Stratégique — Sudoku Arena
**Projet :** Sudoku Arena (powered by FRAID)  
**Version :** 1.0.0 — Draft officiel  
**Auteur :** FRAID  
**Date :** Octobre 2026  

---

## 1. 🎯 Vision du Produit & Objectifs

### 1.1 Qu'est-ce que Sudoku Arena ?
**Sudoku Arena** est une plateforme Web moderne de **Sudoku compétitif multijoueur en temps réel**. Elle réinvente le puzzle classique en un jeu d'arcade dynamique alliant rapidité, stratégie, esprit de duel, simulation IoT (ruban LED NeoPixel virtuel) et une architecture microservices Cloud-Native hautement résiliente.

### 1.2 Les 3 Objectifs Majeurs
1. **Expérience Joueur (Fun & Compétition)** : Transformer une activité solitaire en une expérience sociale et palpitante (duels 1v1, mode survie/course, salons privés avec amis, duel contre l'IA *KI FRAID*).
2. **Vitrine Technique & Portfolio DevOps** : Servir de démonstrateur d'ingénierie complet (FastAPI, WebSockets, MQTT/Mosquitto, Docker, Kubernetes, Helm, CI/CD, Observabilité Prometheus/Grafana).
3. **Potentiel de Croissance & Viabilité** : Concevoir un produit prêt pour la monétisation éthique (Freemium, cosmétiques, tournois) dès la phase de conception, sans altérer l'équité sportive.

---

## 2. 💡 Brainstorming : Modèle Économique & Croissance

### 2.1 Règle d'or : Zéro "Pay-to-Win"
Dans un jeu d'esprit et de logique comme le Sudoku, **l'intégrité compétitive est sacrée**. Un joueur ne doit **jamais** pouvoir acheter un avantage mécanique (indices payants en duel, temps supplémentaire payant, etc.).

### 2.2 Les 3 Paliers d'Évolution Économique

```
   ┌──────────────────────────────────────────────────────────────┐
   │ PALIER 1 : Acquisition & Viralité (Gratuit, Zéro Friction)   │
   │  • Pas de compte obligatoire au départ (invitation en 1 clic) │
   │  • 100% gratuit, 0 publicité intrusive                       │
   └──────────────────────────────┬───────────────────────────────┘
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ PALIER 2 : Freemium Éthique & Personnalisation (Cosmétiques)  │
   │  • Arena Free : Jeu illimité, pubs douces entre les manches  │
   │  • Arena Premium (2,99 €/mois) : Sans pub, thèmes Cyberpunk, │
   │    skins LED personnalisés, stats avancées & heatmaps        │
   └──────────────────────────────┬───────────────────────────────┘
                                  ▼
### 2.4 Extension IA Générative (LLM Assistant & Immersion)
* **Trash-Talk & Ambiance en direct** : KI FRAID ou un bot IA utilise un LLM léger pour envoyer des punchlines et des réactions textuelles en direct dans le chat en fonction des actions du joueur (*« Tu hésites sur le bloc 4 ? Tu transpires déjà ! »*).
* **Coach IA de Fin de Partie (Post-Match Analysis)** : Analyse de la feuille de match par le LLM pour expliquer au joueur ses erreurs, son temps perdu et lui donner un conseil pédagogique d'amélioration.
* **Moteur logique découplé** : La résolution mathématique reste 100% assurée par l'algorithme Python pur (Backtracking instantané < 1ms, 0€ de coût API).

---

## 3. 🎮 Spécifications Fonctionnelles & Gameplay

### 3.1 Les Modes de Jeu

| Mode | Description | Mécanique clé |
| :--- | :--- | :--- |
| **⚡ Mode Clash (Tour par Tour d'origine)** | Les deux joueurs (ou Joueur vs KI) partagent **la même grille**. | Chrono par tour (10s en Difficile, 20s en Moyen, 30s en Facile). **Bon coup** : chiffre validé en vert + points de base + bonus de rapidité. **Erreur ou Fin de chrono** : chiffre rouge/secoué, pénalité de points et **passage immédiat du tour** à l'adversaire. Témoin lumineux (buzzer/LED) indiquant le joueur actif. |
| **🏎️ Mode Course (Speedrun Miroir)** | Chaque joueur résout **sa propre copie identique** du puzzle. | Course de vitesse pure. Jauge de progression adverse en direct (Ghost bar). Le premier à compléter sa grille gagne. |
| **🤖 Mode VS KI FRAID** | Duel contre l'IA sur le Mode Tour par Tour ou Mode Course. | 3 niveaux : *Novice* (délai 5-30s, erreurs), *Tactique* (5-20s), *Grand Maître* (3-10s). |
| **⏱️ Mode Solo / Time Attack** | Entraînement solitaire avec chronomètre global. | Analyse de la régularité et détection de records personnels. |

### 3.2 La Station Virtuelle IoT (Ruban LED NeoPixel)
Héritage direct du projet hardware d'origine (Raspberry Pi + WS2812b) :
* Bandeau LED virtuel immersif intégré en haut de l'écran de jeu.
* **Animations réactives via MQTT/WebSocket** :
  - `🟢 Vert pulsé` : Chiffre correct validé (+ points).
  - `🔴 Rouge clignotant` : Erreur commise (- pénalité temps/score).
  - `🔵 Bleu balayage` : Tour du joueur actif.
  - `🌈 Vague Arc-en-ciel (Rainbow Wipe)` : Victoire finale / Fin de grille.

### 3.3 Gestion des Salons & Joueurs
* **Rôles** : Joueur 1 (Hôte), Joueur 2 (Challenger), Spectateurs (illimités en écoute).
* **Paramètres de Salon** :
  - Difficulté : Facile, Moyen, Difficile, Diabolique.
  - Timer par coup : 15s, 30s, 60s ou Illimité.
  - Malus par erreur : Déduction de points ou gel de jeu pendant 5s.

---

## 4. ⚙️ Spécifications Techniques & Architecture

### 4.1 Architecture Globale

```mermaid
graph TD
    Client1["Navigateur Web (Joueur 1)"] <-->|WebSocket / WSS| Ingress["Ingress Nginx / Envoy"]
    Client2["Navigateur Web (Joueur 2)"] <-->|WebSocket / WSS| Ingress
    
    Ingress -->|HTTP| FrontendSvc["Frontend Web (Nginx Static)"]
    Ingress -->|WSS / API| BackendSvc["Backend FastAPI (Game Engine)"]
    
    BackendSvc <-->|Cache & Session| Redis["Redis (Rooms State / Sessions)"]
    BackendSvc <-->|MQTT Pub/Sub| Mosquitto["Mosquitto Broker (Télémétrie & LED)"]
    
    Prometheus["Prometheus"] -->|Scrape /metrics| BackendSvc
    Grafana["Grafana"] -->|Dashboard| Prometheus
```

### 4.2 Stack Technologique
* **Backend** : Python 3.11+, FastAPI, Uvicorn, WebSockets natifs, Paho-MQTT, Pydantic v2.
* **Frontend** : HTML5, Vanilla CSS / CSS Custom Properties (Thème Cyberpunk Dark), JavaScript ES6+ moderne (sans dépendances superflues pour une vélocité maximale).
* **Moteur & Algorithme** : Backtracking optimisé, générateur de grilles à solution unique, validateur mathématique instantané.
* **Messagerie & Cache** : Eclipse Mosquitto (ports 1883 TCP & 9001 WebSockets), Redis (état distribué).
* **Conteneurisation & Orchestration** :
  - Multi-stage `Dockerfile` allégé.
  - `docker-compose.yml` pour le cycle de développement local.
  - Manifestes Kubernetes : `Deployment`, `Service` (ClusterIP/NodePort), `ConfigMap`, `Secret`, `Ingress`.
  - Packaging `Helm` chart paramétrable.
* **Observabilité** : Endpoint `/metrics` Prometheus, métriques custom (nombre de parties, latence de validation, erreurs).

### 4.3 Règle d'Arbitrage Anti-Triche (Serveur Autoritaire)
* **Zéro confiance envers le client** : Le client envoie uniquement `(row, col, value)`.
* Le serveur détient la grille solution secrète en mémoire/cache et valide chaque coup.
* L'horloge officielle de la partie est cadencée par le serveur.

---

## 5. 🗺️ Roadmap de Réalisation & Jalons

| Jalon | Intitulé | Livrables clés |
| :--- | :--- | :--- |
| **M1** | **Cœur Algorithmique & Tests** | `sudoku_engine.py` pur, générateur, solver backtracking, bot IA `KI FRAID`, tests `pytest` 100% passants. |
| **M2** | **Backend API & WebSockets** | Serveur FastAPI, gestionnaire de salons en mémoire (`room_manager.py`), synchronisation temps réel. |
| **M3** | **Frontend Neo-Arcade & LED IoT** | Grille responsive tactile/clavier, simulateur LED NeoPixel, sounds FX synthétiques, écran de victoire. |
| **M4** | **Docker & Intégration MQTT** | `Dockerfile`, `docker-compose.yml` (Backend + Frontend + Mosquitto), tests d'intégration locaux. |
| **M5** | **Kubernetes, CI/CD & Production** | Manifestes K8s multi-replicas, test de résilience aux pannes de Pods, workflow GitHub Actions CI. |
| **M6** | **Monétisation & Métriques** | Tableau de bord de rétention, intégration optionnelle thèmes Premium. |
