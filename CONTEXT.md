# Contexte de développement - Video Analyzer Workflow

> **Ce fichier permet de maintenir le contexte entre différentes sessions et machines**

## Historique des décisions

### Architecture choisie
- **Stack** : FastAPI + Celery + Redis + PostgreSQL
- **Agents IA** : OpenAI GPT-4o-mini (pour réduire les coûts)
- **Recherche** : SerpAPI (Google Scholar) - optionnel
- **Workflow** : Pipeline en plusieurs étapes (actuellement étape 1 active)

### Décisions techniques

1. **Extraction transcription** : Utilisation de yt-dlp pour extraire les sous-titres automatiques/manuels
2. **Cache en DB** : Vérification systématique avant traitement pour économiser tokens/énergie
3. **Format JSON** : Tous les résultats stockés en JSON dans PostgreSQL (simplicité)
4. **Stance des arguments** : Détection affirmatif vs conditionnel lors de l'extraction

### État actuel du développement

**Phase actuelle** : Étape 1 - Extraction d'arguments uniquement

**Fichier clé** : `app/tasks.py` - Contient uniquement l'extraction de transcription + arguments

**Prochaines étapes prévues** :
1. ✅ Extraction arguments (fait)
2. ⏳ Recherche bibliographique par argument
3. ⏳ Extraction pros/cons depuis articles
4. ⏳ Agrégation finale avec note de fiabilité

### Points d'attention

- **Cache en DB** : Logique dans `app/main.py` - vérifie si `status == "completed"` avant d'enqueue
- **Gestion d'erreurs** : Les statuts sont "processing", "completed", "failed"
- **Variables d'environnement** : `.env` requis avec `OPENAI_API_KEY` (obligatoire) et `SEARCH_API_KEY` (optionnel)

### Commandes utiles

```bash
# Lancer le projet
docker compose up -d --build

# Voir les logs
docker compose logs -f api
docker compose logs -f worker

# Tester l'API
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### Notes importantes

- Le projet est conçu pour être hébergé sur un VPS
- Utilisation d'API keys (pas d'agents IA locaux)
- Économie de tokens via cache en base de données
- Workflow modulaire : chaque étape peut être activée indépendamment

### Structure des données

**Arguments extraits** :
```json
[
  {
    "argument": "texte de l'argument",
    "stance": "affirmatif" ou "conditionnel"
  }
]
```

**Modèle DB** : `VideoAnalysisResult` avec champs :
- `video_id` (indexé)
- `youtube_url`
- `status` (processing/completed/failed)
- `arguments_json` (JSON string)
- `articles_json` (pour plus tard)
- `pros_cons_json` (pour plus tard)
- `aggregation_json` (pour plus tard)

