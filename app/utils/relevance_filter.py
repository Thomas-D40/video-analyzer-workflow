"""
Utility for filtering web search results by relevance.
"""
from typing import List, Dict
import re


def extract_keywords(text: str, min_length: int = 3) -> set:
    """
    Extract significant keywords from text.

    Args:
        text: Source text
        min_length: Minimum word length to keep

    Returns:
        Set of lowercase keywords
    """
    # Common French stop words
    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'mais',
        'est', 'sont', 'a', 'ont', 'pour', 'dans', 'sur', 'avec', 'par',
        'ce', 'cette', 'ces', 'que', 'qui', 'quoi', 'dont', 'où',
        'il', 'elle', 'ils', 'elles', 'nous', 'vous', 'leur', 'leurs',
        'son', 'sa', 'ses', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
        'plus', 'moins', 'très', 'aussi', 'bien', 'pas', 'ne', 'si'
    }

    # Extract words (letters only)
    words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿæœç]+\b', text.lower())

    # Filtering
    keywords = {
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    }
    
    return keywords


def calculate_relevance_score(argument: str, result_snippet: str) -> float:
    """
    Calculate a relevance score between an argument and a result summary.

    Args:
        argument: Argument text
        result_snippet: Search result summary/snippet

    Returns:
        Score between 0.0 and 1.0 (1.0 = very relevant)
    """
    if not argument or not result_snippet:
        return 0.0

    # Extract keywords
    arg_keywords = extract_keywords(argument)
    snippet_keywords = extract_keywords(result_snippet)

    if not arg_keywords:
        return 0.0

    # Calculate ratio of common keywords
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
    Filter search results by relevance.

    Args:
        argument: Argument text
        results: List of search results
        min_score: Minimum relevance score (0.0-1.0)
        max_results: Maximum number of results to return

    Returns:
        Filtered and sorted list by relevance
    """
    if not results:
        return []

    # Calculate scores
    scored_results = []
    for result in results:
        snippet = result.get("snippet", "")
        score = calculate_relevance_score(argument, snippet)

        if score >= min_score:
            result_with_score = result.copy()
            result_with_score["relevance_score"] = score
            scored_results.append(result_with_score)

    # Sort by descending score
    scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Limit number of results
    return scored_results[:max_results]
