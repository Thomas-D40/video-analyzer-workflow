"""
Module principal pour la logique métier de l'analyse de vidéos YouTube.

Ce module contient la fonction `process_video` qui orchestre l'ensemble du workflow:
- Extraction de transcription
- Extraction d'arguments
- Recherche de sources
- Analyse pros/cons
- Calcul de fiabilité
- Génération de rapports
"""
import os
from typing import Dict, List, Any

from app.utils.youtube import extract_video_id
from app.utils.transcript import extract_transcript
from app.agents.extraction import extract_arguments
from app.agents.research import (
    search_literature,
    generate_search_queries,
    search_arxiv,
    search_world_bank_data,
)
from app.agents.analysis import extract_pros_cons, aggregate_results
from app.utils.report_formatter import generate_markdown_report


from app.services.storage import save_analysis, get_analysis

async def process_video(youtube_url: str, force_refresh: bool = False, youtube_cookies: str = None) -> Dict[str, Any]:
    """
    Traite une vidéo YouTube et retourne l'analyse complète.
    
    Args:
        youtube_url: URL de la vidéo YouTube
        
    Returns:
        Dictionnaire contenant:
        - video_id: ID de la vidéo
        - youtube_url: URL source
        - arguments: Liste des arguments analysés
        - report_markdown: Rapport formaté en Markdown
        
    Raises:
        ValueError: Si l'URL est invalide ou la transcription introuvable
        Exception: Pour toute autre erreur durant le traitement
    """
    # Étape 1: Extraction de l'ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise ValueError("Impossible d'extraire l'ID de la vidéo depuis l'URL")
    
    # Étape 1.5: Vérification du cache
    if not force_refresh:
        cached_analysis = await get_analysis(video_id)
        if cached_analysis and cached_analysis.status == "completed":
            print(f"[INFO] Analyse trouvée en cache pour {video_id}")
            result = cached_analysis.content
            # On ajoute les métadonnées de cache
            result["cached"] = True
            result["last_updated"] = cached_analysis.updated_at.isoformat()
            return result

    # Étape 2: Extraction de la transcription
    transcript_text = extract_transcript(youtube_url, youtube_cookies=youtube_cookies)
    if not transcript_text or len(transcript_text.strip()) < 50:
        raise ValueError("Transcription introuvable ou trop courte")
    
    # Étape 3: Extraction des arguments
    arguments = extract_arguments(transcript_text, video_id=video_id)
    if not arguments:
        return {
            "video_id": video_id,
            "youtube_url": youtube_url,
            "arguments": [],
            "report_markdown": "Aucun argument trouvé dans cette vidéo."
        }
    
    # Étape 4 & 5: Recherche et Analyse
    enriched_arguments = []
    
    for arg_data in arguments:
        argument_text = arg_data["argument"]
        
        # Génération de requêtes optimisées
        queries = {"arxiv": "", "world_bank": "", "web_query": ""}
        try:
            queries = generate_search_queries(argument_text)
        except Exception:
            pass  # Continue avec requêtes vides
        
        # Recherche Web (avec filtrage de pertinence)
        try:
            from app.utils.relevance_filter import filter_relevant_results
            
            web_query = queries.get("web_query") or argument_text
            print(f"[DEBUG workflow] Recherche Web avec requête: '{web_query}'")
            
            # On récupère plus de résultats pour avoir le choix
            raw_web_articles = search_literature(web_query, max_results=10)
            print(f"[DEBUG workflow] Articles Web trouvés (brut): {len(raw_web_articles)}")
            
            # Filtrage par pertinence : garde les 2 meilleurs résultats
            web_articles = filter_relevant_results(
                argument_text, 
                raw_web_articles, 
                min_score=0.1,  # Assoupli à 10% pour éviter de tout filtrer
                max_results=5
            )
            print(f"[DEBUG workflow] Articles Web après filtrage: {len(web_articles)}")
        except Exception as e:
            print(f"[ERROR workflow] Erreur recherche Web: {e}")
            web_articles = []
        
        # Recherche Scientifique
        try:
            arxiv_query = queries.get("arxiv", "")
            print(f"[DEBUG workflow] Recherche ArXiv avec requête: '{arxiv_query}'")
            science_articles = search_arxiv(arxiv_query, max_results=5) if arxiv_query else []
            print(f"[DEBUG workflow] Articles ArXiv trouvés: {len(science_articles)}")
        except Exception as e:
            print(f"[ERROR workflow] Erreur recherche ArXiv: {e}")
            science_articles = []
        
        # Recherche Statistique
        try:
            wb_query = queries.get("world_bank", "")
            stats_data = search_world_bank_data(wb_query) if wb_query else []
        except Exception:
            stats_data = []
        
        # Analyse Pros/Cons
        all_sources = web_articles + science_articles
        print(f"[INFO] Argument: {argument_text[:50]}...")
        print(f"[INFO] Sources trouvées: {len(web_articles)} Web, {len(science_articles)} ArXiv, {len(stats_data)} Stats")
        
        try:
            analysis = extract_pros_cons(argument_text, all_sources)
            print(f"[INFO] Analyse générée: {len(analysis.get('pros', []))} pros, {len(analysis.get('cons', []))} cons")
        except Exception as e:
            print(f"[ERROR] Erreur analyse pros/cons: {e}")
            analysis = {"pros": [], "cons": []}
        
        # Construction de l'objet enrichi
        enriched_arg = arg_data.copy()
        enriched_arg["sources"] = {
            "web": web_articles,
            "scientific": science_articles,
            "statistical": stats_data
        }
        enriched_arg["analysis"] = analysis
        enriched_arguments.append(enriched_arg)
    
    # Étape 6: Calcul de fiabilité
    try:
        items_for_aggregation = [
            {
                "argument": arg["argument"],
                "pros": arg["analysis"].get("pros", []),
                "cons": arg["analysis"].get("cons", []),
                "stance": arg.get("stance", "affirmatif"),
                "sources": arg.get("sources", {})  # Ajouter les sources réelles
            }
            for arg in enriched_arguments
        ]
        
        aggregation_result = aggregate_results(items_for_aggregation, video_id=video_id)
        aggregated_args_map = {a["argument"]: a for a in aggregation_result.get("arguments", [])}
        
        final_arguments = []
        for original_arg in enriched_arguments:
            arg_text = original_arg["argument"]
            agg_data = aggregated_args_map.get(arg_text, {})
            reliability = agg_data.get("reliability", 0.5)
            original_arg["reliability_score"] = reliability
            final_arguments.append(original_arg)
        
        arguments = final_arguments
    except Exception:
        arguments = enriched_arguments
    
    # Génération du rapport
    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "arguments_count": len(arguments),
        "arguments": arguments
    }
    
    report_markdown = generate_markdown_report(output_data)
    
    result = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "arguments": arguments,
        "report_markdown": report_markdown
    }

    # Sauvegarde en base de données
    try:
        await save_analysis(video_id, youtube_url, result)
        print(f"[INFO] Analyse sauvegardée pour {video_id}")
    except Exception as e:
        print(f"[ERROR] Erreur sauvegarde DB: {e}")

    return result
