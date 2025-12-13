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

# Optional: News & Fact-Check APIs
NEWSAPI_KEY=votre_clé_newsapi
GNEWS_API_KEY=votre_clé_gnews
GOOGLE_FACTCHECK_API_KEY=votre_clé_google
CLAIMBUSTER_API_KEY=votre_clé_claimbuster
```

**Note importante**:

- `OPENAI_API_KEY` est **requis** pour l'extraction d'arguments
- Les autres clés sont optionnelles (services sautés si non configurés)

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

### 5. Tester les services de recherche

```bash
# Test all research APIs
python tests/test_research_services.py

# Test specific category
python tests/test_research_services.py --category news
python tests/test_research_services.py --category factcheck

# Verbose output
python tests/test_research_services.py -v
```

See `tests/README.md` for details.

## Configuration

- Variables dans `.env` (voir `.env.example`):
  - `DATABASE_URL`
  - `OPENAI_API_KEY` (ou autre LLM provider)

## Workflow Diagram

```mermaid
graph TD
    Start([YouTube Video URL]) --> Extract[Extract Transcript]
    Extract --> Arguments[Extract Arguments<br/>GPT-4o]

    Arguments --> Loop{For Each<br/>Argument}

    Loop --> Classify[Topic Classifier<br/>GPT-4o-mini]

    Classify --> Strategy{Determine<br/>Research Strategy}

    Strategy -->|Medicine| MedAgents[PubMed + Europe PMC<br/>+ Fact-Check APIs]
    Strategy -->|Economics| EconAgents[OECD + World Bank<br/>+ Semantic Scholar]
    Strategy -->|Physics/CS/Math| SciAgents[ArXiv + Semantic Scholar<br/>+ CORE + DOAJ]
    Strategy -->|Current Events| NewsAgents[NewsAPI + GNews<br/>+ Fact-Check APIs]
    Strategy -->|Fact-Check| FactAgents[Google Fact Check<br/>+ ClaimBuster]
    Strategy -->|General| GenAgents[Semantic Scholar<br/>+ CrossRef]

    MedAgents --> QueryGen[Generate Queries<br/>GPT-4o-mini]
    EconAgents --> QueryGen
    SciAgents --> QueryGen
    NewsAgents --> QueryGen
    FactAgents --> QueryGen
    GenAgents --> QueryGen

    QueryGen --> Search[Execute Searches<br/>in Parallel]

    Search --> PubMed[(PubMed API)]
    Search --> SemanticScholar[(Semantic Scholar API)]
    Search --> CrossRef[(CrossRef API)]
    Search --> ArXiv[(ArXiv API)]
    Search --> OECD[(OECD Data)]
    Search --> WorldBank[(World Bank API)]

    PubMed --> Aggregate[Aggregate Sources]
    SemanticScholar --> Aggregate
    CrossRef --> Aggregate
    ArXiv --> Aggregate
    OECD --> Aggregate
    WorldBank --> Aggregate

    Aggregate --> ProsCons[Extract Pros/Cons<br/>GPT-4o]

    ProsCons --> Reliability[Calculate Reliability Score]

    Reliability --> MoreArgs{More<br/>Arguments?}

    MoreArgs -->|Yes| Loop
    MoreArgs -->|No| Report[Generate Markdown Report]

    Report --> Cache[(Save to MongoDB)]
    Cache --> End([Return Analysis])

    style Classify fill:#e1f5ff
    style QueryGen fill:#e1f5ff
    style Arguments fill:#ffe1e1
    style ProsCons fill:#ffe1e1
    style Strategy fill:#fff4e1

    classDef apiNode fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    class PubMed,SemanticScholar,CrossRef,ArXiv,OECD,WorldBank apiNode
```
