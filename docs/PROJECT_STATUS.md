# État du Projet - Video Analyzer Workflow

## Date de dernière mise à jour
Session initiale - Extraction d'arguments uniquement

## État actuel du développement

### ✅ Implémenté et fonctionnel

1. **Infrastructure de base**
   - FastAPI avec endpoint `/analyze`

   - MongoDB pour le stockage
   - Docker Compose configuré avec healthchecks

2. **Workflow actuel (première étape uniquement)**
   - Extraction de la transcription YouTube (yt-dlp)
   - Extraction des arguments avec OpenAI GPT-4o-mini
   - Détection du stance (affirmatif/conditionnel)
   - Persistance en base de données
   - Système de cache (ne relance pas si déjà analysé)

3. **Agents créés (non utilisés actuellement)**
   - `app/agents/arguments.py` - ✅ Utilisé
   - `app/agents/research.py` - ⏸️ Prêt (DuckDuckGo)
   - `app/agents/pros_cons.py` - ⏸️ Prêt (OpenAI)
   - `app/agents/aggregate.py` - ⏸️ Prêt (OpenAI)

### 📋 Structure du projet

```
video-analyzer-workflow/
├── app/
│   ├── agents/
│   │   ├── arguments.py      # ✅ Utilisé - Extraction arguments
│   │   ├── research.py       # ⏸️ Prêt - Recherche bibliographique
│   │   ├── pros_cons.py      # ⏸️ Prêt - Extraction pros/cons
│   │   └── aggregate.py      # ⏸️ Prêt - Agrégation finale
│   ├── utils/
│   │   ├── youtube.py        # Extraction video_id
│   │   └── transcript.py    # Extraction transcription
│   ├── main.py              # API FastAPI
│   ├── models.py             # Modèles Pydantic
│   ├── db/
│       └── mongo.py          # Configuration MongoDB
│   ├── config.py             # Configuration (pydantic-settings)
│   └── schemas.py            # Schémas Pydantic
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### 🔧 Configuration requise

**Fichier `.env` nécessaire :**
```env
DATABASE_URL=mongodb://mongo:27017
OPENAI_API_KEY=votre_clé_openai_ici  # REQUIS
ENV=development
```

### 🚀 Pour démarrer

```bash
# 1. Créer le fichier .env avec les clés API
# 2. Lancer les services
docker compose up -d --build

# 3. Tester
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### 📝 Points importants à retenir

1. **Cache en DB** : Le système vérifie si une vidéo a déjà été analysée avant de relancer
2. **Première étape uniquement** : Seule l'extraction d'arguments est active dans `tasks.py`
3. **Agents prêts** : Les autres agents (recherche, pros/cons, agrégation) sont implémentés mais non utilisés

### 🔄 Prochaines étapes prévues

1. Activer l'agent de recherche bibliographique (étape 2)
2. Activer l'extraction pros/cons (étape 3)
3. Activer l'agrégation finale (étape 4)

### 📚 Endpoints disponibles

- `POST /analyze` - Analyser une vidéo YouTube
- `GET /docs` - Documentation Swagger de l'API

### 🐛 Dépannage
- Vérifier que la DB est prête : `docker compose ps`

