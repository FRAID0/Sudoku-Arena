# ☸️ Helm Chart — Sudoku Arena

> **Application :** Sudoku Arena (Cloud-Native Multiplayer & AI Engine)  
> **Type :** Helm v3 / v4 Application Chart  
> **Composants :** Backend (FastAPI, 3 répliques), Frontend (Nginx, 2 répliques), Redis (State & Pub/Sub), Mosquitto (MQTT), Ingress Controller.

---

## 1. 🎯 Présentation

Ce Helm Chart package l'ensemble des microservices de **Sudoku Arena** pour un déploiement résilient et haute disponibilité sur n'importe quel cluster Kubernetes (Local avec Docker Desktop / Kind / Minikube, ou Cloud avec GKE / EKS / Hetzner).

### ✨ Fonctionnalités Clés :
* **Découplage d'état (Stateless)** : 3 Pods Backend partageant une instance Redis pour les salles de jeu et le relais Pub/Sub des WebSockets.
* **Haute Disponibilité** : 2 Pods Frontend sous Nginx avec équilibrage de charge.
* **Sondes Kubernetes intégrées** :
  - `readinessProbe` : Attend que le service soit prêt avant de router le trafic joueur.
  - `livenessProbe` : Redémarre automatiquement un Pod s'il ne répond plus.
* **Porte d'entrée unifiée (Ingress)** :
  - Route `/` vers le Frontend.
  - Route `/api`, `/ws` (WebSockets) et `/health` vers le Backend.

---

## 2. 🚀 Installation & Déploiement

### Étape 1 : Vérification de la syntaxe (Lint)
```bash
helm lint ./charts/sudoku-arena
```

### Étape 2 : Prévisualisation des manifestes générés (Dry-Run / Template)
```bash
helm template sudoku-arena ./charts/sudoku-arena
```

### Étape 3 : Déploiement sur le cluster
```bash
# Dans le namespace par défaut
helm install sudoku-arena ./charts/sudoku-arena

# Ou dans un namespace dédié 'sudoku-arena'
kubectl create namespace sudoku-arena
helm install sudoku-arena ./charts/sudoku-arena --namespace sudoku-arena
```

---

## 3. ⚙️ Personnalisation des Valeurs (`values.yaml`)

Vous pouvez surcharger n'importe quel paramètre au déploiement via `--set` ou avec un fichier dédié :

| Paramètre | Description | Valeur par défaut |
| :--- | :--- | :--- |
| `backend.replicaCount` | Nombre de répliques du backend FastAPI | `3` |
| `backend.image.repository` | Image Docker du backend | `ghcr.io/fraid0/sudoku-arena/backend` |
| `backend.image.tag` | Tag de l'image backend | `latest` |
| `frontend.replicaCount` | Nombre de répliques du frontend | `2` |
| `redis.enabled` | Déploie le cache Redis et bus Pub/Sub | `true` |
| `mosquitto.enabled` | Déploie le broker MQTT pour télémétrie LED | `true` |
| `ingress.enabled` | Active l'Ingress HTTP/WebSocket | `true` |
| `ingress.hosts[0].host` | Nom de domaine d'accès | `sudoku.local` |

### Exemple de surcharge pour un environnement de développement local léger :
```bash
helm install sudoku-arena ./charts/sudoku-arena \
  --set backend.replicaCount=1 \
  --set frontend.replicaCount=1 \
  --set backend.resources.requests.cpu=50m
```

---

## 4. 🧹 Désinstallation
```bash
helm uninstall sudoku-arena --namespace sudoku-arena
```
