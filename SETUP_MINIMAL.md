# 🚀 Installation minimale - Extraction d'arguments

## Objectif

Exécuter uniquement la **première étape du workflow** :
1. ✅ Extraction de la transcription YouTube
2. ✅ Extraction des arguments avec OpenAI

**Sans** FastAPI, Celery, Redis, PostgreSQL, Docker.

## Prérequis

### 1. Python 3.8 ou supérieur

```bash
python --version
```

### 2. Clé API OpenAI

Vous devez avoir une clé API OpenAI. Obtenez-en une sur [platform.openai.com](https://platform.openai.com/api-keys)

## Installation

### Option 1 : Environnement virtuel (recommandé)

```bash
# Créer l'environnement
python -m venv venv

# Activer (Windows)
venv\Scripts\activate

# Activer (Linux/Mac)
source venv/bin/activate

# Installer les dépendances
pip install -r requirements_minimal.txt
```

### Option 2 : Installation globale

```bash
pip install -r requirements_minimal.txt
```

## Configuration

### Définir la clé API OpenAI

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-votre-cle-api-ici"
```

**Windows (CMD):**
```cmd
set OPENAI_API_KEY=sk-votre-cle-api-ici
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-votre-cle-api-ici"
```

**Permanent (créer un fichier `.env`):**
Créez un fichier `.env` à la racine du projet :
```env
OPENAI_API_KEY=sk-votre-cle-api-ici
```

Puis installez `python-dotenv` et modifiez le script pour charger le `.env`.

## Utilisation

```bash
python extract_arguments_minimal.py "https://www.youtube.com/watch?v=VxDcpOL9wUo"
```

### Exemple

```bash
python extract_arguments_minimal.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Résultat attendu

Le script va :
1. ✅ Extraire l'ID de la vidéo
2. ✅ Télécharger la transcription (français ou anglais)
3. ✅ Analyser la transcription avec OpenAI GPT-4o-mini
4. ✅ Extraire les arguments avec leur stance (affirmatif/conditionnel)
5. ✅ Afficher les résultats dans le terminal
6. ✅ Sauvegarder les résultats dans `arguments_VIDEO_ID.json`

### Exemple de sortie

```
================================================================================
🎬 EXTRACTION D'ARGUMENTS D'UNE VIDÉO YOUTUBE
================================================================================

📺 URL: https://www.youtube.com/watch?v=...

🔍 Étape 1: Extraction de l'ID de la vidéo...
✅ ID de la vidéo: dQw4w9WgXcQ

📝 Étape 2: Extraction de la transcription...
✅ Transcription extraite (1234 caractères)

🤖 Étape 3: Extraction des arguments avec OpenAI...
✅ 3 argument(s) extrait(s)

================================================================================
📊 RÉSULTATS
================================================================================

1. ✅ [AFFIRMATIF]
   Les réseaux sociaux créent de l'addiction chez les jeunes

2. ❓ [CONDITIONNEL]
   Il pourrait y avoir un lien entre écrans et troubles du sommeil

3. ✅ [AFFIRMATIF]
   La régulation des réseaux sociaux est nécessaire

================================================================================
💾 Résultats sauvegardés dans: arguments_dQw4w9WgXcQ.json
================================================================================
```

## Structure des fichiers

```
video-analyzer-workflow/
├── extract_arguments_minimal.py  # Script principal
├── requirements_minimal.txt       # Dépendances minimales
├── SETUP_MINIMAL.md              # Ce fichier
├── arguments_VIDEO_ID.json       # Résultats (généré)
└── app/                          # Modules du projet (utilisés par le script)
    ├── utils/
    │   ├── youtube.py           # Extraction ID vidéo
    │   └── transcript.py        # Extraction transcription
    ├── agents/
    │   └── arguments.py         # Extraction arguments
    └── config.py                # Configuration
```

## Dépannage

### "ModuleNotFoundError: No module named 'app'"
→ Assurez-vous d'exécuter le script depuis la racine du projet :
```bash
cd video-analyzer-workflow
python extract_arguments_minimal.py "URL"
```

### "OPENAI_API_KEY n'est pas définie"
→ Définissez la variable d'environnement (voir section Configuration)

### "Transcription introuvable"
→ La vidéo doit avoir des sous-titres activés (automatiques ou manuels). Essayez une autre vidéo.

### "Erreur lors de l'extraction des arguments"
→ Vérifiez que votre clé API OpenAI est valide et que vous avez des crédits disponibles.

## Coûts estimés

- **Modèle utilisé** : GPT-4o-mini (le moins cher)
- **Coût par vidéo** : ~$0.01-0.05 selon la longueur de la transcription
- **Optimisation MCP** : Réduction de ~40% des tokens grâce à l'optimisation

## Prochaines étapes

Une fois que cette première étape fonctionne, vous pouvez :
1. Ajouter les autres étapes du workflow (recherche, pros/cons, agrégation)
2. Intégrer avec FastAPI pour une API HTTP
3. Ajouter Celery pour le traitement asynchrone
4. Ajouter PostgreSQL pour la persistance

