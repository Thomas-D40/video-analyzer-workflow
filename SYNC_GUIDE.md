# Guide de synchronisation entre machines

## Méthode recommandée : Git

### 1. Initialiser Git (si pas déjà fait)

```bash
git init
git add .
git commit -m "Initial commit - Video Analyzer Workflow"
```

### 2. Créer un dépôt distant (optionnel mais recommandé)

- GitHub, GitLab, ou autre
- Pousser le code : `git push origin main`

### 3. Sur chaque machine

```bash
# Cloner ou pull le projet
git clone <url-du-repo>
# OU
git pull origin main
```

### 4. Fichiers importants pour le contexte

Ces fichiers sont versionnés et synchronisés :
- ✅ `CONTEXT.md` - Contexte de développement
- ✅ `PROJECT_STATUS.md` - État actuel du projet
- ✅ `README.md` - Instructions générales
- ✅ Tous les fichiers de code

### 5. Fichiers NON versionnés (à créer localement)

- ❌ `.env` - Contient les clés API (jamais commité)
- ❌ Fichiers de cache locaux

## Méthode alternative : Dossier partagé

Si vous n'utilisez pas Git, vous pouvez :
- Utiliser un service cloud (Dropbox, OneDrive, etc.)
- Synchroniser le dossier du projet
- **Attention** : Ne synchronisez PAS le dossier `.env` ou les volumes Docker

## Reprendre le contexte avec l'IA

Quand vous reprenez sur une autre machine :

1. **Lire les fichiers de contexte** :
   - `CONTEXT.md`
   - `PROJECT_STATUS.md`

2. **Me dire simplement** :
   ```
   "Reprends le projet video-analyzer-workflow, j'ai lu CONTEXT.md"
   ```

3. **Ou me donner un résumé** :
   ```
   "On était à l'étape d'extraction d'arguments, on veut maintenant 
   activer la recherche bibliographique"
   ```

## Fichiers de contexte créés

- `CONTEXT.md` - Décisions techniques et historique
- `PROJECT_STATUS.md` - État actuel du développement
- `SYNC_GUIDE.md` - Ce fichier (guide de synchronisation)

Ces fichiers sont conçus pour être commités dans Git et partagés entre machines.

