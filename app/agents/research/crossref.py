"""
Research agent for CrossRef.

CrossRef provides metadata for academic publications via DOI,
including citations, funding, licenses and bibliographic data.

API Documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
Rate Limits: Variable based on "polite" usage (with contact email)
"""
from typing import List, Dict, Optional
import requests

def search_crossref(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search for academic publications via CrossRef.

    CrossRef is useful for obtaining complete metadata and citation
    information to validate source credibility.

    Args:
        query: Search query (ideally in English)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing:
        - title: Publication title
        - url: URL to the publication (via DOI)
        - snippet: Abstract/summary
        - source: "CrossRef"
        - doi: Publication DOI
        - type: Publication type (journal-article, book-chapter, etc.)
        - year: Publication year
        - citations: Number of citations
        - publisher: Publisher
        - authors: List of authors

    Raises:
        Exception: If the query fails
    """
    base_url = "https://api.crossref.org/works"

    # "Polite" headers for better rate limits
    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (mailto:research@example.com)"
    }

    params = {
        "query": query,
        "rows": max_results,
        "select": "DOI,title,author,published,abstract,type,publisher,is-referenced-by-count,URL"
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        articles = []

        if "message" not in data or "items" not in data["message"]:
            print(f"[CrossRef] No results for: {query}")
            return []

        for item in data["message"]["items"]:
            # Extract title
            title_list = item.get("title", [])
            title = title_list[0] if title_list else "Untitled"

            # Extract DOI and URL
            doi = item.get("DOI", "")
            url = item.get("URL", f"https://doi.org/{doi}" if doi else "")

            # Extract abstract
            abstract = item.get("abstract", "")
            if not abstract:
                # Fallback to subtitle or type info
                subtitle = item.get("subtitle", [])
                if subtitle:
                    abstract = subtitle[0]
                else:
                    abstract = f"{item.get('type', 'Publication')} from {item.get('publisher', 'N/A')}"

            # Clean HTML tags from abstract (CrossRef sometimes includes them)
            if abstract:
                import re
                abstract = re.sub(r'<[^>]+>', '', abstract)

            # Extract year
            published = item.get("published", {})
            if "date-parts" in published and published["date-parts"]:
                year = published["date-parts"][0][0] if published["date-parts"][0] else "N/A"
            else:
                year = "N/A"

            # Extract authors
            authors_list = item.get("author", [])
            authors = []
            for author in authors_list[:3]:  # First 3 authors
                given = author.get("given", "")
                family = author.get("family", "")
                if family:
                    name = f"{given} {family}".strip() if given else family
                    authors.append(name)

            # Extract citation count
            citations = item.get("is-referenced-by-count", 0)

            # Check for license information (indicator of potential open access)
            licenses = item.get("license", [])
            is_open_license = any("creativecommons" in lic.get("URL", "").lower() or
                                  "cc-by" in lic.get("URL", "").lower()
                                  for lic in licenses)

            # Determine access type
            if is_open_license:
                access_type = "open_access"
                has_full_text = True
                access_note = "Open access via Creative Commons license"
            else:
                access_type = "metadata_only"
                has_full_text = False
                access_note = "Metadata and abstract only - full text may require subscription"

            article = {
                "title": title,
                "url": url,
                "snippet": abstract[:500],  # Limit snippet length
                "source": "CrossRef",
                "doi": doi,
                "type": item.get("type", "N/A"),
                "year": str(year),
                "citations": citations,
                "publisher": item.get("publisher", "N/A"),
                "authors": ", ".join(authors) if authors else "N/A",
                "access_type": access_type,
                "has_full_text": has_full_text,
                "access_note": access_note
            }

            articles.append(article)

        print(f"[CrossRef] {len(articles)} publications found for: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[CrossRef] Timeout during search: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[CrossRef] Error during search: {e}")
        return []
    except Exception as e:
        print(f"[CrossRef] Unexpected error: {e}")
        return []


def get_citation_count(doi: str) -> Optional[int]:
    """
    Retrieve the citation count for a given DOI.

    Args:
        doi: Publication DOI

    Returns:
        Number of citations or None if error
    """
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "VideoAnalyzerWorkflow/1.0 (mailto:research@example.com)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("is-referenced-by-count", 0)
    except Exception as e:
        print(f"[CrossRef] Error retrieving citations for {doi}: {e}")
        return None
