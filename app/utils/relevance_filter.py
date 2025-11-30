"""
Utilitaire pour filtrer les résultats de recherche web par pertinence.
"""
from typing import List, Dict
import re


def extract_keywords(text: str, min_length: int = 3) -> set:
    """
    Extrait les mots-clés significatifs d'un texte.
    
    Args:
        text: Texte source
        min_length: Longueur minimale des mots à conserver
        
    Returns:
        Ensemble de mots-clés en minuscules
    """
    # Mots vides français courants
    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais',
        'est', 'sont', 'a', 'ont', 'pour', 'dans', 'sur', 'avec', 'par',
        'ce', 'cette', 'ces', 'que', 'qui', 'quoi', 'dont', 'où',
        'il', 'elle', 'ils', 'elles', 'nous', 'vous', 'leur', 'leurs',
        'son', 'sa', 'ses', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
        'plus', 'moins', 'très', 'aussi', 'bien', 'pas', 'ne', 'si'
    }
    
    # Extraction des mots (lettres uniquement)
    words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿæœç]+\b', text.lower())
    
    # Filtrage
    keywords = {
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    }
    
    return keywords


def calculate_relevance_score(argument: str, result_snippet: str) -> float:
    """
    Calcule un score de pertinence entre un argument et un résumé de résultat.
    
    Args:
        argument: Texte de l'argument
        result_snippet: Résumé/snippet du résultat de recherche
        
    Returns:
        Score entre 0.0 et 1.0 (1.0 = très pertinent)
    """
    if not argument or not result_snippet:
        return 0.0
    
    # Extraction des mots-clés
    arg_keywords = extract_keywords(argument)
    snippet_keywords = extract_keywords(result_snippet)
    
    if not arg_keywords:
        return 0.0
    
    # Calcul du ratio de mots-clés communs
    common_keywords = arg_keywords.intersection(snippet_keywords)
    score = len(common_keywords) / len(arg_keywords)
    
    return min(score, 1.0)


def filter_relevant_results(
    argument: str, 
    results: List[Dict[str, str]], 
    min_score: float = 0.2,
    max_results: int = 2
) -> List[Dict[str, str]]:
    """
    Filtre les résultats de recherche par pertinence.
    
    Args:
        argument: Texte de l'argument
        results: Liste des résultats de recherche
        min_score: Score minimal de pertinence (0.0-1.0)
        max_results: Nombre maximum de résultats à retourner
        
    Returns:
        Liste filtrée et triée par pertinence
    """
    if not results:
        return []
    
    # Calcul des scores
    scored_results = []
    for result in results:
        snippet = result.get("snippet", "")
        score = calculate_relevance_score(argument, snippet)
        
        if score >= min_score:
            result_with_score = result.copy()
            result_with_score["relevance_score"] = score
            scored_results.append(result_with_score)
    
    # Tri par score décroissant
    scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    # Limitation du nombre de résultats
    return scored_results[:max_results]
