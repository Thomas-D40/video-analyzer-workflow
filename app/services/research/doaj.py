"""
Research agent for DOAJ (Directory of Open Access Journals).

DOAJ indexes ~2 million articles from quality, peer-reviewed
open access journals across all disciplines.

API Documentation: https://doaj.org/api/docs
Rate Limits: Reasonable usage without API key
"""
from typing import List, Dict
import requests


def search_doaj(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for articles in open access journals via DOAJ.

    DOAJ provides access to high-quality, peer-reviewed open access journals.
    All content is guaranteed to be open access with full text available.

    Args:
        query: Search query (ideally in English)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing:
        - title: Article title
        - url: URL to the article
        - snippet: Article abstract/summary
        - source: "DOAJ"
        - year: Publication year
        - authors: List of authors
        - journal: Journal name
        - doi: DOI if available
        - access_type: Always "open_access"
        - has_full_text: Always True
        - access_note: Full text availability note

    Raises:
        Exception: If the query fails
    """
    # DOAJ API endpoint for articles
    base_url = "https://doaj.org/api/search/articles"

    # Search parameters
    params = {
        "q": query,
        "pageSize": max_results,
        "page": 1
    }

    # Headers
    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (Research Tool)"
    }

    try:
        # Request with timeout
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        articles = []

        # Check if results exist
        results = data.get("results", [])
        if not results:
            print(f"[DOAJ] No results for: {query}")
            return []

        for item in results:
            # DOAJ returns nested structure with 'bibjson' containing metadata
            bibjson = item.get("bibjson", {})

            # Extract title
            title = bibjson.get("title", "Untitled")

            # Extract abstract
            abstract = bibjson.get("abstract", "")

            # Extract year
            year = "N/A"
            if bibjson.get("year"):
                year = str(bibjson["year"])
            elif bibjson.get("month") and bibjson.get("year"):
                year = str(bibjson["year"])

            # Extract authors
            authors_list = bibjson.get("author", [])
            authors = []
            for author in authors_list[:3]:  # First 3 authors
                name = author.get("name", "")
                if name:
                    authors.append(name)

            # Extract journal
            journal_info = bibjson.get("journal", {})
            journal = journal_info.get("title", "N/A")

            # Extract DOI
            doi_list = bibjson.get("identifier", [])
            doi = ""
            url = ""

            for identifier in doi_list:
                if identifier.get("type") == "doi":
                    doi = identifier.get("id", "")
                    if doi:
                        url = f"https://doi.org/{doi}"
                        break

            # If no DOI, try to get URL from links
            if not url:
                links = bibjson.get("link", [])
                for link in links:
                    if link.get("type") == "fulltext":
                        url = link.get("url", "")
                        break

            # If still no URL, check the item-level id
            if not url:
                url = item.get("id", "")

            # Build snippet
            if not abstract or len(abstract.strip()) < 20:
                abstract = f"Open access article from {journal} ({year})"

            # DOAJ only contains open access journals
            access_type = "open_access"
            has_full_text = True
            access_note = "Full text available (peer-reviewed open access journal)"

            article = {
                "title": title,
                "url": url if url else f"https://doaj.org/search/articles?q={query}",
                "snippet": abstract[:500],  # Limit snippet length
                "source": "DOAJ",
                "year": year,
                "authors": ", ".join(authors) if authors else "N/A",
                "journal": journal,
                "doi": doi if doi else "N/A",
                "access_type": access_type,
                "has_full_text": has_full_text,
                "access_note": access_note
            }

            articles.append(article)

        print(f"[DOAJ] {len(articles)} open access articles found for: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[DOAJ] Timeout during search: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[DOAJ] Error during search: {e}")
        return []
    except Exception as e:
        print(f"[DOAJ] Unexpected error: {e}")
        return []


def search_doaj_journals(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for open access journals (not articles) in DOAJ.

    This is useful for verifying journal quality and open access status.

    Args:
        query: Search query (journal name or subject)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing journal information
    """
    base_url = "https://doaj.org/api/search/journals"

    params = {
        "q": query,
        "pageSize": max_results,
        "page": 1
    }

    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (Research Tool)"
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        journals = []

        results = data.get("results", [])
        for item in results:
            bibjson = item.get("bibjson", {})

            journal = {
                "title": bibjson.get("title", "Untitled"),
                "publisher": bibjson.get("publisher", {}).get("name", "N/A"),
                "subjects": ", ".join([s.get("term", "") for s in bibjson.get("subject", [])[:3]]),
                "url": bibjson.get("ref", {}).get("journal", ""),
                "source": "DOAJ"
            }

            journals.append(journal)

        print(f"[DOAJ] {len(journals)} open access journals found for: {query}")
        return journals

    except Exception as e:
        print(f"[DOAJ] Error searching journals: {e}")
        return []
