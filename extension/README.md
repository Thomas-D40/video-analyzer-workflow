# Guide d'Installation et d'Utilisation

## Extension Chrome/Firefox : YouTube Argument Analyzer

### 🔧 Configuration Automatique Dev/Prod

L'extension détecte automatiquement l'environnement et utilise le bon endpoint:

- **Développement** (extension non empaquetée): `http://46.202.128.11:8000`
- **Production** (extension publiée): `https://46.202.128.11:8000`

### Installation Chrome

1. **Démarrer l'API Backend** (pour dev local)
   ```bash
   # Option 1: Docker (recommandé)
   docker compose up -d --build

   # Option 2: Direct
   uvicorn app.api:app --reload --port 8000
   ```
   L'API sera accessible sur `http://localhost:8000` (local) ou `http://46.202.128.11:8000` (VPS)

2. **Charger l'Extension dans Chrome**
   - Ouvrir Chrome et aller à `chrome://extensions/`
   - Activer le "Mode développeur" (en haut à droite)
   - Cliquer sur "Charger l'extension non empaquetée"
   - Sélectionner le dossier `extension/` du projet
   - L'extension apparaîtra dans la barre d'outils
   - ✅ L'extension utilisera automatiquement HTTP en mode développement

### Installation Firefox

Voir [FIREFOX_INSTALL.md](FIREFOX_INSTALL.md) pour les instructions détaillées.

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
