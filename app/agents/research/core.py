"""
Research agent for CORE (COnnecting REpositories).

CORE aggregates open access research papers from repositories
and journals worldwide. It provides access to 350M+ open access papers.

API Documentation: https://core.ac.uk/services/api
Rate Limits: Free tier allows reasonable usage without API key
"""
from typing import List, Dict
import requests
import time


def search_core(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for open access research papers on CORE.

    CORE aggregates millions of open access papers from repositories
    worldwide, making it an excellent source for freely accessible research.

    Args:
        query: Search query (ideally in English)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing:
        - title: Article title
        - url: URL to the article
        - snippet: Article abstract/summary
        - source: "CORE"
        - year: Publication year
        - authors: List of authors
        - repository: Source repository
        - access_type: Always "open_access"
        - has_full_text: Always True
        - access_note: Full text availability note

    Raises:
        Exception: If the query fails
    """
    # CORE API v3 endpoint
    base_url = "https://api.core.ac.uk/v3/search/works"

    # Headers (API key optional for basic usage)
    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (Research Tool)"
    }

    # Search parameters
    params = {
        "q": query,
        "limit": max_results,
        "offset": 0
    }

    try:
        # Request with timeout
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        articles = []

        if "results" not in data or not data["results"]:
            print(f"[CORE] No results for: {query}")
            return []

        for paper in data["results"]:
            # Extract basic information
            title = paper.get("title", "Untitled")
            abstract = paper.get("abstract", "")

            # Extract year from publication date
            year = "N/A"
            pub_date = paper.get("publishedDate", "") or paper.get("yearPublished", "")
            if pub_date:
                # Try to extract year (format can vary)
                import re
                year_match = re.search(r'(\d{4})', str(pub_date))
                if year_match:
                    year = year_match.group(1)

            # Extract authors
            authors_list = paper.get("authors", [])
            authors = []
            if authors_list:
                for author in authors_list[:3]:  # First 3 authors
                    if isinstance(author, dict):
                        name = author.get("name", "")
                    else:
                        name = str(author)
                    if name:
                        authors.append(name)

            # Extract URL (prefer DOI, then landing page, then download URL)
            url = ""
            doi = paper.get("doi", "")
            if doi:
                url = f"https://doi.org/{doi}"
            else:
                url = paper.get("links", [{}])[0].get("url", "") if paper.get("links") else ""
                if not url:
                    url = paper.get("downloadUrl", "")

            # Extract repository information
            repository = "CORE"
            if paper.get("publisher"):
                repository = paper.get("publisher")
            elif paper.get("journals"):
                journals = paper.get("journals", [])
                if journals and isinstance(journals, list) and journals[0]:
                    repository = journals[0].get("title", "CORE") if isinstance(journals[0], dict) else str(journals[0])

            # CORE only provides open access content
            access_type = "open_access"
            has_full_text = True

            # Check if full text is available
            has_pdf = bool(paper.get("downloadUrl"))
            if has_pdf:
                access_note = "Full text PDF available (open access)"
            else:
                access_note = "Open access article (full text may be available)"

            # Build snippet
            if not abstract or len(abstract.strip()) < 20:
                abstract = f"Open access article from {repository} ({year})"

            article = {
                "title": title,
                "url": url if url else f"https://core.ac.uk/search?q={query}",
                "snippet": abstract[:500],  # Limit snippet length
                "source": "CORE",
                "year": year,
                "authors": ", ".join(authors) if authors else "N/A",
                "repository": repository,
                "access_type": access_type,
                "has_full_text": has_full_text,
                "access_note": access_note
            }

            articles.append(article)

        print(f"[CORE] {len(articles)} open access articles found for: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[CORE] Timeout during search: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[CORE] Error during search: {e}")
        return []
    except Exception as e:
        print(f"[CORE] Unexpected error: {e}")
        return []
