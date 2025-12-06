"""
Research agent for Europe PMC (Europe PubMed Central).

Europe PMC is a comprehensive life sciences literature database
providing access to biomedical and life sciences research, with better
full-text access than PubMed for European content.

API Documentation: https://europepmc.org/RestfulWebService
Rate Limits: Generous limits for reasonable usage
"""
from typing import List, Dict
import requests
import time


def search_europepmc(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for biomedical and life sciences articles on Europe PMC.

    Europe PMC provides better full-text access than PubMed, especially
    for European research content, and includes preprints and other sources.

    Args:
        query: Search query (ideally in English)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing:
        - title: Article title
        - url: URL to the article
        - snippet: Article abstract/summary
        - source: "Europe PMC"
        - year: Publication year
        - authors: List of authors
        - journal: Journal name
        - pmid: PubMed ID if available
        - pmcid: PMC ID if available
        - doi: DOI if available
        - access_type: "open_access" or "abstract_only"
        - has_full_text: Boolean indicating full text availability
        - access_note: Full text availability note

    Raises:
        Exception: If the query fails
    """
    # Europe PMC REST API endpoint
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    # Search parameters
    params = {
        "query": query,
        "pageSize": max_results,
        "format": "json",
        "resultType": "core",  # Get core metadata
        "sort": "RELEVANCE"
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
        result_list = data.get("resultList", {})
        results = result_list.get("result", [])

        if not results:
            print(f"[Europe PMC] No results for: {query}")
            return []

        for item in results:
            # Extract title
            title = item.get("title", "Untitled")

            # Extract abstract
            abstract = item.get("abstractText", "")

            # Extract year
            year = item.get("pubYear", "N/A")

            # Extract authors
            author_string = item.get("authorString", "")
            authors_list = []
            if author_string:
                # authorString is comma-separated
                authors_list = [a.strip() for a in author_string.split(",")[:3]]  # First 3

            # Extract journal
            journal = item.get("journalTitle", "N/A")
            if not journal or journal == "N/A":
                journal = item.get("bookOrReportDetails", {}).get("publisher", "N/A")

            # Extract identifiers
            pmid = item.get("pmid", "")
            pmcid = item.get("pmcid", "")
            doi = item.get("doi", "")

            # Build URL (prefer PMC, then DOI, then PubMed)
            url = ""
            if pmcid:
                url = f"https://europepmc.org/article/PMC/{pmcid.replace('PMC', '')}"
            elif doi:
                url = f"https://doi.org/{doi}"
            elif pmid:
                url = f"https://europepmc.org/article/MED/{pmid}"
            else:
                # Use the ID from the result
                source = item.get("source", "")
                id_val = item.get("id", "")
                if source and id_val:
                    url = f"https://europepmc.org/article/{source}/{id_val}"

            # Determine access type based on isOpenAccess flag and PMC ID
            is_open_access = item.get("isOpenAccess", "") == "Y"
            has_pmc = bool(pmcid)
            in_epmc = item.get("inEPMC", "") == "Y"
            has_pdf = item.get("hasPDF", "") == "Y"

            # Determine full text availability
            if is_open_access or has_pmc or in_epmc:
                access_type = "open_access"
                has_full_text = True
                if has_pdf:
                    access_note = "Full text PDF available (open access)"
                elif has_pmc:
                    access_note = f"Full text available via PMC (ID: {pmcid})"
                else:
                    access_note = "Full text HTML available (open access)"
            else:
                access_type = "abstract_only"
                has_full_text = False
                access_note = "Abstract only - full text may require subscription"

            # Build snippet
            if not abstract or len(abstract.strip()) < 20:
                abstract = f"Article from {journal} ({year})"

            article = {
                "title": title,
                "url": url if url else f"https://europepmc.org/search?query={query}",
                "snippet": abstract[:500],  # Limit snippet length
                "source": "Europe PMC",
                "year": str(year),
                "authors": ", ".join(authors_list) if authors_list else "N/A",
                "journal": journal,
                "pmid": pmid if pmid else "N/A",
                "pmcid": pmcid if pmcid else "N/A",
                "doi": doi if doi else "N/A",
                "access_type": access_type,
                "has_full_text": has_full_text,
                "access_note": access_note
            }

            articles.append(article)

        print(f"[Europe PMC] {len(articles)} articles found for: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[Europe PMC] Timeout during search: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[Europe PMC] Error during search: {e}")
        return []
    except Exception as e:
        print(f"[Europe PMC] Unexpected error: {e}")
        return []


def get_fulltext_xml(pmcid: str) -> str:
    """
    Retrieve full-text XML for an article from Europe PMC.

    This is useful for extracting detailed information from articles
    that have full text available in PMC.

    Args:
        pmcid: PMC ID (with or without 'PMC' prefix)

    Returns:
        XML string of the full text, or empty string on error
    """
    # Remove 'PMC' prefix if present
    clean_id = pmcid.replace("PMC", "")

    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{clean_id}/fullTextXML"

    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (Research Tool)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[Europe PMC] Error retrieving full text XML for {pmcid}: {e}")
        return ""
