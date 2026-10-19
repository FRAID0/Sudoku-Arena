# 🗂️ Product Backlog & Issues — Sudoku Arena
> **Framework :** Agile / Scrum & GitHub Issues Roadmap  
> **Priorités :** P0 (Bloquant/MVP), P1 (Essentiel/V1), P2 (Différenciant/V2), P3 (Confort/Polish)  
> **Méthode d'exécution :** Tâche par tâche avec critères d'acceptation stricts et tests unitaires automatisés.

---

## 🏆 Synthèse de l'Analyse Concurrentielle & Positionnement

| Concurrent | Points forts identifiés | Faiblesses / Frustrations joueurs | Notre Différenciation |
| :--- | :--- | :--- | :--- |
| **Dueloku** | Duel temps réel sur grille partagée, classement ELO. | Matchmaking parfois lent, design générique, pas de mode course miroir. | **Mode Course miroir** (zéro frustration de vol intempestif) + **Mode Clash** optionnel + Ambiance Neo-Arcade immersive. |
| **UsDoku** | Salons privés avec codes, jusqu'à 10 joueurs. | Règles parfois confuses sur le comptage de blocs, UI basique. | **Simplicité radicale** (code salon 4 lettres, lien 1-clic) + Feedback visuel immédiat (ruban LED). |
| **Sudoku.com** | Leader mondial en trafic (35M+ visites), puzzles infinis. | **Pluie de publicités intrusives**, contrôles tactiles parfois imprécis, solo uniquement. | **ZÉRO pub pendant une manche**, respect total de la concentration, jouabilité tactile fluide au pixel près. |

---

## 🧭 Structure des Épics & Milestones

```
[Milestone M1 : MVP Engine & Tests] ──────► Issue #1, #2, #3 (P0)
                  │
                  ▼
[Milestone M2 : Temps Réel & Salons] ─────► Issue #4, #5, #6, #7 (P0/P1)
                  │
                  ▼
[Milestone M3 : UI Neo-Arcade & LED IoT] ─► Issue #8, #9, #10 (P1)
                  │
                  ▼
[Milestone M4 : Docker & Mosquitto] ──────► Issue #11, #12, #13 (P1)
                  │
                  ▼
[Milestone M5 : Kubernetes & Résilience] ─► Issue #14, #15, #16 (P2)
```

---

## 📋 Backlog Détaillé des Issues

### 🔷 EPIC 1 : Cœur Algorithmique & Règle Métier (M1)

#### `[#1 - P0]` Moteur de génération et de validation Sudoku
- **En tant que :** Moteur de jeu  
- **Je veux :** Générer des grilles valides à solution unique pour chaque difficulté (Facile, Moyen, Difficile) et valider instantanément un coup sans fuiter la solution  
- **Critères d'acceptation (DoD) :**
  1. La grille générée possède **exactement une seule solution** mathématique.
  2. Le temps de génération est inférieur à **50ms**.
  3. `validate_move(row, col, value)` renvoie `True/False` en `< 1ms`.
  4. La solution secrète reste confinée côté serveur.
  5. Couverture de tests `pytest` >= 95%.

#### `[#2 - P0]` Solveur automatique par Backtracking
- **En tant que :** Système  
- **Je veux :** Résoudre n'importe quelle grille 9x9 en mémoire  
- **Critères d'acceptation (DoD) :**
  1. Résout une grille standard en `< 10ms`.
  2. Détecte immédiatement une grille insoluble ou incohérente.
  3. Tests unitaires validés sur des cas limites (grilles vides, grilles diaboliques).

#### `[#3 - P1]` Intelligence Artificielle "KI FRAID"
- **En tant que :** Joueur solo  
- **Je veux :** Défier un bot IA autonome avec 3 personnalités  
- **Critères d'acceptation (DoD) :**
  1. **Niveau Facile** : Délais aléatoires (3-6s), taux d'erreur de ~15%.
  2. **Niveau Moyen** : Délais tactiques (2-4s), taux d'erreur de ~5%.
  3. **Niveau Expert** : Délais vifs (1-2s), zéro erreur.
  4. Simule un délai de réflexion "humain" non bloquant pour le serveur.

---

### 🔷 EPIC 2 : Multijoueur & Synchronisation Temps Réel (M2)

#### `[#4 - P0]` Gestionnaire de Salons (Room Manager)
- **En tant que :** Joueur  
- **Je veux :** Créer un salon privé avec un code à 4 lettres et inviter un ami  
- **Critères d'acceptation (DoD) :**
  1. Génération de code unique (ex: `AF7K`).
  2. Gestion des états de salon : `WAITING`, `STARTING`, `IN_GAME`, `FINISHED`.
  3. Support de 2 joueurs actifs + spectateurs illimités.
  4. Suppression automatique du salon après 10 minutes d'inactivité.

#### `[#5 - P0]` Serveur WebSocket & Protocole d'événements
- **En tant que :** Client de jeu  
- **Je veux :** M'abonner aux événements de ma partie avec une latence < 30ms  
- **Critères d'acceptation (DoD) :**
  1. Événements standardisés JSON : `JOIN_ROOM`, `START_GAME`, `MOVE_PLAYED`, `OPPONENT_PROGRESS`, `GAME_OVER`.
  2. Validation serveur stricte avant diffusion aux adversaires.
  3. Horodatage serveur sur chaque message pour départager les ex æquo.

#### `[#6 - P1]` Mode Course (Mirror Speedrun)
- **En tant que :** Joueur compétitif  
- **Je veux :** Jouer la même grille que mon adversaire et voir sa jauge d'avancement en temps réel  
- **Critères d'acceptation (DoD) :**
  1. Les deux joueurs reçoivent la même grille initiale.
  2. Diffusion du pourcentage de complétion de l'adversaire (effet "Ghost").
  3. Détection de victoire instantanée dès la 81ème case validée.

#### `[#7 - P1]` Gestion des déconnexions & Anti-Ragequit
- **En tant que :** Joueur honnête  
- **Je veux :** Que mon adversaire ne puisse pas tricher ou geler le match en quittant  
- **Critères d'acceptation (DoD) :**
  1. Compte à rebours de grâce de 30 secondes en cas de déconnexion inopinée.
  2. Possibilité de se reconnecter avec restauration complète de l'état de la grille.
  3. Forfait automatique déclaré si le joueur ne revient pas avant la fin du délai.

---

### 🔷 EPIC 3 : Interface Web Neo-Arcade & IoT Virtuel (M3)

#### `[#8 - P0]` Grille de Sudoku Web Responsive & Clavier Tactile
- **En tant que :** Joueur mobile ou desktop  
- **Je veux :** Remplir les cases avec fluidité sans aucun lag  
- **Critères d'acceptation (DoD) :**
  1. Support tactile (mobile) et clavier physique (1-9, flèches, effacer).
  2. Mise en surbrillance intelligente (ligne, colonne, bloc 3x3 et chiffres identiques).
  3. Mode brouillon / annotations de candidats (notes au crayon).
  4. Palette Dark Theme / Cyberpunk avec contraste accessible (WCAG AA).

#### `[#9 - P1]` Simulateur de Ruban LED IoT (NeoPixel WS2812b)
- **En tant que :** Joueur nostalgique du projet physique  
- **Je veux :** Visualiser un bandeau lumineux virtuel réactif en haut de l'écran  
- **Critères d'acceptation (DoD) :**
  1. Ruban virtuel de 30 à 60 pixels animés en CSS/Canvas.
  2. Impulsion verte sur coup valide, éclat rouge sur erreur, vague arc-en-ciel sur victoire.
  3. Possibilité de connecter le simulateur aux messages MQTT de télémétrie.

#### `[#10 - P2]` Écran de Fin de Match & Carte de Partage
- **En tant que :** Vainqueur d'un duel  
- **Je veux :** Visualiser mes statistiques et partager ma victoire en un clic  
- **Critères d'acceptation (DoD) :**
  1. Affichage du temps exact, du nombre d'erreurs et de la précision.
  2. Bouton "Revanche immédiate" (relance une nouvelle manche dans le même salon).
  3. Carte visuelle téléchargeable/copiable pour partage social (Discord, WhatsApp).

---

### 🔷 EPIC 4 : Conteneurisation & Mosquitto (M4)

#### `[#11 - P0]` Dockerfile Backend & Frontend allégés
- **Critères d'acceptation :** Image Python < 150 Mo basée sur `python:3.11-slim`, sans dépendances de compilation inutiles, utilisateur non-root.

#### `[#12 - P0]` Docker Compose de Développement
- **Critères d'acceptation :** Un seul fichier `docker-compose.yml` lançant `backend`, `frontend`, et `mosquitto` avec réseau interne isolé et volumes montés pour le hot-reload.

#### `[#13 - P1]` Broker Mosquitto & Bridge WebSockets
- **Critères d'acceptation :** Mosquitto configuré avec listener 1883 (TCP) et listener 9001 (WebSockets) opérationnels.

---

### 🔷 EPIC 5 : Kubernetes, Haute Disponibilité & CI/CD (M5)

#### `[#14 - P1]` Manifestes Kubernetes de Base
- **Critères d'acceptation :** `Deployment` avec `replicas: 3`, probes `livenessProbe` et `readinessProbe`, `Service` ClusterIP et `ConfigMap`.

#### `[#15 - P1]` Pipeline GitHub Actions (CI)
- **Critères d'acceptation :** Exécution automatique de `pytest` et build Docker à chaque `git push` sur `main` ou Pull Request.

#### `[#16 - P2]` Test de Résilience & Chaos Monkey manuel
- **Critères d'acceptation :** Supprimer un Pod (`kubectl delete pod ...`) pendant une partie et vérifier le rétablissement automatique par Kubernetes.

---

### 🔷 EPIC 6 : Gameplay V2, Ergonomie Zéro-Scroll & Robustesse Frontend (M6)

#### `[#17 - P0]` Validation Duale Backend : Mode Simple (Local) vs Mode Casse-Tête (Strict)
- **Critères d'acceptation :**
  1. Le backend accepte un paramètre `validation_mode`: `"simple"` ou `"strict"`.
  2. En mode `"simple"` (défaut) : tout chiffre respectant ligne, colonne et carré 3x3 actuel est validé (`is_valid_placement`).
  3. En mode `"strict"` : seule la solution finale unique secrète est acceptée.
  4. Messages explicites de rejet (`"reason"` dans le payload WebSocket).

#### `[#18 - P0]` Layout Zéro-Scroll (Single-Screen Viewport 100dvh)
- **Critères d'acceptation :**
  1. Hauteur totale verrouillée à `100dvh` sans aucun scroll vertical sur mobile comme sur desktop.
  2. Grille, bandeau LED, chrono et scoreboards visibles en permanence.
  3. Masquage dynamique du header de marque dès le démarrage de la manche (`.arena-container.in-game`).

#### `[#19 - P1]` Refonte du Bandeau LED & Signalétique Tour par Tour
- **Critères d'acceptation :**
  1. Animations douces avec transitions fondues de 400 à 600ms (fini le flash instantané).
  2. Indicateur visuel clair du joueur actif : pixels 0 à 14 allumés en bleu cyan pour P1, pixels 15 à 29 allumés en violet néon pour P2/KI FRAID.
  3. Effets de feedback doux : impulsion verte sur coup juste, onde rouge sur coup faux/timeout.

#### `[#20 - P1]` Système de Notifications Toasts & Feedbacks de Rejet
- **Critères d'acceptation :**
  1. Affichage clair d'un toast d'alerte lors d'un coup refusé (ex: "Ce n'est pas votre tour !", "Case déjà remplie", "Chiffre déjà présent sur la ligne/colonne/carré").
  2. Sécurisation stricte de l'UI : empêcher toute modification erronée de la jauge de progression lors d'un coup invalide.

#### `[#21 - P1]` Robustesse WebSocket, Statut Réseau & Config Multi-Environnement
- **Critères d'acceptation :**
  1. Badge d'état de connexion visible (🟢 En ligne, 🟠 Reconnexion, 🔴 Déconnecté).
  2. Reconnexion automatique intelligente (tentatives espacées) sans blocage silencieux.
  3. Détection dynamique de l'URL du backend (local `localhost` vs Cloud Northflank, avec surcharge possible via paramètre d'URL `?backend=...`).

#### `[#22 - P2]` Accessibilité Clavier & Ergonomie Tactile Mobile
- **Critères d'acceptation :**
  1. Navigation complète au clavier : flèches directionnelles (Haut, Bas, Gauche, Droite) pour déplacer la sélection de cellule.
  2. Touches 1-9 pour jouer, `Suppr` / `Retour arrière` pour effacer.
  3. Focus visuel net avec contour néon sur la cellule active.
  4. Pavé tactile adaptatif sans débordement sur petits écrans.

---

## 🏛️ Stratégie d'Architecture DevOps & Démonstration Portfolio

Pour valoriser le projet auprès des recruteurs et sur LinkedIn sans frais d'infrastructure :

1. **Environnement A — Démo Publique Live (100% Gratuit) :**
   - **Frontend :** Vercel (Hébergement Edge mondial, CDN HTTPS gratuit, déploiement automatique sur `git push origin main`).
   - **Backend :** Northflank Developer Sandbox (Conteneur FastAPI / WebSockets toujours actif sans mise en veille, certifié $0 avec vérification CB).
   - **Objectif :** Permettre à n'importe quel recruteur de tester instantanément un duel en direct depuis deux navigateurs.

2. **Environnement B — Laboratoire Kubernetes Local (Démonstration Avancée) :**
   - **Cluster :** Docker Desktop avec cluster local `kind` (6 pods : 3 réplicas backend, 2 réplicas frontend, 1 broker Mosquitto).
   - **Compétences validées :** Deployments, Services (ClusterIP, LoadBalancer), ConfigMaps, Liveness & Readiness Probes, Self-Healing vérifié (<2s lors du kill d'un pod).
   - **CI/CD :** Pipeline GitHub Actions automatisé (`.github/workflows/ci.yml`) avec validation `pytest`, build Docker et `kubectl dry-run`.
   - **Évolution future (V3) :** Intégration de Redis pour synchroniser les salons entre plusieurs réplicas backend en production.
