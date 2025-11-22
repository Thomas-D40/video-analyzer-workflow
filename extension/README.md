# Guide d'Installation et d'Utilisation

## Extension Chrome : YouTube Argument Analyzer

### Installation

1. **Démarrer l'API Backend**
   ```bash
   # Depuis la racine du projet
   uvicorn app.api:app --reload --port 8000
   ```
   L'API sera accessible sur `http://localhost:8000`

2. **Charger l'Extension dans Chrome**
   - Ouvrir Chrome et aller à `chrome://extensions/`
   - Activer le "Mode développeur" (en haut à droite)
   - Cliquer sur "Charger l'extension non empaquetée"
   - Sélectionner le dossier `extension/` du projet
   - L'extension apparaîtra dans la barre d'outils

### Utilisation

1. Naviguer vers une vidéo YouTube
2. Cliquer sur l'icône de l'extension dans la barre d'outils
3. Cliquer sur "Analyser cette vidéo"
4. Attendre 30-60 secondes pendant l'analyse
5. Consulter les résultats dans la popup
6. Optionnel : Copier le rapport avec le bouton "📋 Copier"

### Endpoints API

- `GET /` - Page d'accueil de l'API
- `GET /health` - Vérification de santé
- `POST /api/analyze` - Analyse d'une vidéo YouTube
  - Body: `{"url": "https://youtube.com/watch?v=..."}`
  - Response: Rapport complet avec arguments et sources

### Prérequis

- Python 3.8+
- Variable d'environnement `OPENAI_API_KEY` configurée
- Dépendances installées : `pip install -r requirements.txt`
- Chrome ou navigateur basé sur Chromium
