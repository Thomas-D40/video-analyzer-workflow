# ⚡ Démarrage rapide - Extraction d'arguments

## Installation en 3 commandes

```bash
# 1. Installer les dépendances
pip install -r requirements_minimal.txt

# 2. Définir votre clé API OpenAI
export OPENAI_API_KEY="sk-votre-cle-ici"  # Linux/Mac
# OU
set OPENAI_API_KEY=sk-votre-cle-ici        # Windows CMD
# OU
$env:OPENAI_API_KEY="sk-votre-cle-ici"     # Windows PowerShell

# 3. Lancer le script
python extract_arguments_minimal.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Exemple complet

```bash
# Installation
pip install -r requirements_minimal.txt

# Configuration (remplacez par votre vraie clé)
export OPENAI_API_KEY="sk-..."

# Test avec une vidéo
python extract_arguments_minimal.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Ce qui est installé

- ✅ **yt-dlp** : Pour extraire les transcriptions YouTube
- ✅ **openai** : Pour l'API OpenAI (extraction d'arguments)
- ✅ **pydantic-settings** : Pour la configuration

**Total** : 3 dépendances seulement !

## Résultat

Le script va :
1. ✅ Extraire la transcription
2. ✅ Analyser avec OpenAI GPT-4o-mini
3. ✅ Extraire les arguments (affirmatif/conditionnel)
4. ✅ Sauvegarder dans `arguments_VIDEO_ID.json`

## Besoin d'aide ?

Voir `SETUP_MINIMAL.md` pour plus de détails.

