"""
Research agent for Semantic Scholar.

Semantic Scholar is an AI-powered academic database
that covers ~200M scientific articles across all disciplines.

API Documentation: https://www.semanticscholar.org/product/api
Rate Limits: 100 requests per 5 minutes (no API key required)
"""
from typing import List, Dict
import requests
import time

def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for academic articles on Semantic Scholar.

    Semantic Scholar uses AI to identify the most relevant articles
    across all academic disciplines (sciences, medicine, social sciences, etc.)

    Args:
        query: Search query (ideally in English)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing:
        - title: Article title
        - url: URL to the article on Semantic Scholar
        - snippet: Article abstract/summary
        - source: "Semantic Scholar"
        - year: Publication year
        - citations: Number of citations
        - authors: List of authors

    Raises:
        Exception: If the query fails after several attempts
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # Search parameters
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,year,citationCount,authors,url,openAccessPdf"
    }

    # Recommended headers (optional but polite)
    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (Research Tool)"
    }

    try:
        # Request with timeout
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []

        if "data" not in data or not data["data"]:
            print(f"[Semantic Scholar] No results for: {query}")
            return []

        for paper in data["data"]:
            # Extract authors
            authors = []
            if paper.get("authors"):
                authors = [author.get("name", "") for author in paper["authors"][:3]]  # First 3 authors

            # Build article URL
            paper_id = paper.get("paperId", "")
            paper_url = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else paper.get("url", "")

            # Get abstract
            abstract = paper.get("abstract", "")
            if not abstract:
                abstract = f"Article from {paper.get('year', 'N/A')} with {paper.get('citationCount', 0)} citations"

            article = {
                "title": paper.get("title", "Untitled"),
                "url": paper_url,
                "snippet": abstract[:500],  # Limit snippet length
                "source": "Semantic Scholar",
                "year": paper.get("year", "N/A"),
                "citations": paper.get("citationCount", 0),
                "authors": ", ".join(authors) if authors else "N/A",
                "open_access": bool(paper.get("openAccessPdf"))
            }

            articles.append(article)

        print(f"[Semantic Scholar] {len(articles)} articles found for: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[Semantic Scholar] Timeout during search: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[Semantic Scholar] Error during search: {e}")
        return []
    except Exception as e:
        print(f"[Semantic Scholar] Unexpected error: {e}")
        return []


def get_paper_details(paper_id: str) -> Dict:
    """
    Retrieve full details of an article by its Semantic Scholar ID.

    Args:
        paper_id: Semantic Scholar ID of the article

    Returns:
        Dictionary with full article details
    """
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    params = {
        "fields": "title,abstract,year,citationCount,authors,url,openAccessPdf,references,citations"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Semantic Scholar] Error retrieving details: {e}")
        return {}
