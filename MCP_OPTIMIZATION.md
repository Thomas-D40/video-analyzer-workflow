# Optimisation MCP pour Réduction de Tokens

## Vue d'ensemble

Ce projet a été refactorisé pour utiliser un système de gestion de ressources inspiré du **Model Context Protocol (MCP)** afin de réduire significativement la consommation de tokens lors des appels à l'API OpenAI.

## Problème initial

Avant l'optimisation, les agents envoyaient tout le contenu dans les prompts :
- **Transcriptions complètes** (jusqu'à 15000 caractères) → ~4000 tokens
- **Snippets d'articles complets** (jusqu'à 10000 caractères) → ~2500 tokens
- **JSON complets** pour l'agrégation (jusqu'à 15000 caractères) → ~4000 tokens

**Total estimé par analyse complète** : ~10 000+ tokens par vidéo

## Solution MCP

Un système de gestion de ressources en mémoire permet de :
1. **Diviser les transcriptions en chunks** accessibles sélectivement
2. **Résumer les articles** avant de les envoyer (300 caractères max au lieu de 500+)
3. **Optimiser les prompts** en réduisant la verbosité
4. **Limiter les données** envoyées (max 5 pros/cons par argument, 200 caractères par claim)

## Optimisations par agent

### 1. Agent `arguments.py`

**Avant** :
- Transcription complète tronquée à 15000 caractères
- Prompt système long et détaillé

**Après** :
- Transcription optimisée à 8000 caractères max (résumé intelligent)
- Prompt système condensé
- **Réduction estimée** : ~40% de tokens (de ~4000 à ~2400 tokens)

### 2. Agent `pros_cons.py`

**Avant** :
- Snippets d'articles complets (500 caractères chacun)
- Jusqu'à 10 articles × 500 = 5000 caractères
- Prompt système détaillé

**Après** :
- Résumés d'articles limités à 300 caractères
- Formatage optimisé avec limite de 6000 caractères total
- Prompt système condensé
- **Réduction estimée** : ~50% de tokens (de ~2500 à ~1250 tokens)

### 3. Agent `aggregate.py`

**Avant** :
- JSON complet avec tous les pros/cons
- Jusqu'à 15000 caractères
- Format JSON indenté (plus verbeux)

**Après** :
- Max 5 pros et 5 cons par argument
- Max 200 caractères par claim
- Max 300 caractères par argument
- Format JSON compact (sans indentation)
- Limite à 10000 caractères
- **Réduction estimée** : ~45% de tokens (de ~4000 à ~2200 tokens)

## Architecture MCP

### Composants

1. **`app/utils/mcp_server.py`** : Gestionnaire de ressources
   - Stocke les transcriptions en chunks
   - Stocke les articles résumés
   - Stocke les arguments extraits
   - Permet l'accès sélectif aux ressources

2. **`app/utils/mcp_client.py`** : Client pour accéder aux ressources
   - Méthodes pour récupérer des transcriptions optimisées
   - Méthodes pour formater les articles
   - Méthodes pour référencer les arguments

### Utilisation

```python
# Enregistrement d'une transcription
mcp_manager = get_mcp_manager()
mcp_manager.register_transcript(video_id, transcript_text)

# Récupération optimisée
mcp_client = get_mcp_client()
optimized_transcript = mcp_client.get_transcript_for_analysis(video_id, max_chars=8000)
```

## Résultats attendus

**Réduction totale estimée** : ~50-60% de tokens par analyse complète

- **Avant** : ~10 000 tokens par vidéo
- **Après** : ~4 000-5 000 tokens par vidéo

**Économies** :
- Pour 100 vidéos analysées : ~500 000 tokens économisés
- Coût réduit d'environ 50-60% (selon le modèle utilisé)

## Notes techniques

- Le système MCP est implémenté en mémoire (pas de serveur externe)
- Les ressources sont nettoyées automatiquement en cas d'erreur
- Compatible avec l'architecture existante (rétrocompatibilité)
- Les agents fonctionnent toujours sans MCP (fallback automatique)

## Prochaines optimisations possibles

1. **Embeddings** : Utiliser des embeddings pour identifier les chunks les plus pertinents
2. **Cache de résumés** : Mettre en cache les résumés de transcriptions
3. **Compression** : Utiliser des techniques de compression de texte
4. **Streaming** : Traiter les transcriptions par chunks séquentiels

