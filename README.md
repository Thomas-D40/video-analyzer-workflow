# Video Analyzer Workflow

API HTTP pour analyser des vidéos YouTube via un workflow d'agents.

## Stack
- FastAPI (API)

- MongoDB (stockage)
- Motor (driver async)
- yt-dlp / ffmpeg (ingest vidéo au besoin)

## Démarrage rapide

### 1. Créer le fichier `.env`

Créez un fichier `.env` à la racine du projet avec le contenu suivant:

```env
DATABASE_URL=mongodb://mongo:27017

OPENAI_API_KEY=votre_clé_openai_ici
ENV=development
```

**Note importante**: 
- `OPENAI_API_KEY` est **requis** pour l'extraction d'arguments

### 2. Lancer les services Docker

```bash
docker compose up -d --build
```

Cela va démarrer:
- L'API FastAPI sur le port 8000
- MongoDB (base de données)

### 3. Vérifier que tout fonctionne

Vérifier les logs:
```bash
docker compose logs -f api
```

Ou vérifier que l'API répond:
```bash
curl http://localhost:8000/docs
```

### 4. Tester l'endpoint d'analyse

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

Réponse attendue:
- Si première analyse: `{"video_id": "...", "status": "queued", "result": null}`
- Si déjà analysé: `{"video_id": "...", "status": "completed", "result": {"arguments": [...]}}`



## Configuration
- Variables dans `.env` (voir `.env.example`):
  - `DATABASE_URL`
  - `OPENAI_API_KEY` (ou autre LLM provider)

## Development Workflow

### Working Across Machines

This project uses Git for synchronization:

```bash
# Commit your changes
git add .
git commit -m "Description of changes"

# Push to remote
git push origin main

# On another machine, pull changes
git pull origin main
```

**Important**: Never commit the `.env` file (it contains API keys). Create it locally on each machine.

### Documentation Files

- `README.md` - Main documentation (this file)
- `GETTING_STARTED.md` - Minimal setup without Docker
- `HTTPS.md` - HTTPS configuration and testing
- `CLAUDE.md` - Instructions for Claude Code
- `docs/` - Technical documentation (MCP optimization, AI benchmarks, project status)

## Déploiement Automatique (CI/CD)

Le projet utilise GitHub Actions pour le déploiement automatique sur le VPS.

### Configuration des Secrets GitHub

Pour que le déploiement fonctionne, vous devez ajouter les "Repository secrets" suivants dans votre dépôt GitHub (Settings > Secrets and variables > Actions) :

| Nom du Secret | Description |
|---------------|-------------|
| `VPS_HOST` | Adresse IP de votre VPS |
| `VPS_USER` | Nom d'utilisateur SSH (ex: `root`) |
| `VPS_SSH_KEY` | Votre clé privée SSH (le contenu du fichier `.pem` ou `id_rsa`) |
| `OPENAI_API_KEY` | Votre clé API OpenAI pour la production |
| `ALLOWED_API_KEYS` | Clés API autorisées pour les utilisateurs (séparées par des virgules) |

### Premier Déploiement

Pour la première installation sur le VPS, connectez-vous manuellement et clonez le dépôt :

```bash
# Sur le VPS
mkdir -p /opt/video-analyzer
git clone https://github.com/Thomas-D40/video-analyzer-workflow.git /opt/video-analyzer
cd /opt/video-analyzer
# Le premier déploiement se fera ensuite automatiquement au prochain push
```

## Objectif fonctionnel
- Requête HTTP avec `youtube_url`
- Vérification en DB par `video_id`
- Si cache manquant: envoi à une crew d'agents:
  1. Extraction des arguments de la vidéo (ton affirmatif vs conditionnel)
  2. Recherche bibliographique/scientifique par argument (liste d'articles)
  3. Extraction pour/contre avec sources
  4. Agrégation: tableau arguments + pours/contres + note de fiabilité
