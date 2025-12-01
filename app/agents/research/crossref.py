"""
Agent de recherche pour CrossRef.

CrossRef fournit des métadonnées pour les publications académiques via DOI,
incluant les citations, financements, licences et données bibliographiques.

API Documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
Rate Limits: Variable selon l'utilisation "polie" (avec contact email)
"""
from typing import List, Dict, Optional
import requests

def search_crossref(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Recherche des publications académiques via CrossRef.

    CrossRef est utile pour obtenir des métadonnées complètes et des informations
    sur les citations pour valider la crédibilité des sources.

    Args:
        query: Requête de recherche (idéalement en anglais)
        max_results: Nombre maximum de résultats (défaut: 5)

    Returns:
        Liste de dictionnaires contenant:
        - title: Titre de la publication
        - url: URL vers la publication (via DOI)
        - snippet: Résumé/abstract
        - source: "CrossRef"
        - doi: DOI de la publication
        - type: Type de publication (journal-article, book-chapter, etc.)
        - year: Année de publication
        - citations: Nombre de citations
        - publisher: Éditeur
        - authors: Liste des auteurs

    Raises:
        Exception: Si la requête échoue
    """
    base_url = "https://api.crossref.org/works"

    # Headers "polite" pour de meilleures rate limits
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
            print(f"[CrossRef] Aucun résultat pour: {query}")
            return []

        for item in data["message"]["items"]:
            # Extract title
            title_list = item.get("title", [])
            title = title_list[0] if title_list else "Sans titre"

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
                "authors": ", ".join(authors) if authors else "N/A"
            }

            articles.append(article)

        print(f"[CrossRef] {len(articles)} publications trouvées pour: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[CrossRef] Timeout lors de la recherche: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[CrossRef] Erreur lors de la recherche: {e}")
        return []
    except Exception as e:
        print(f"[CrossRef] Erreur inattendue: {e}")
        return []


def get_citation_count(doi: str) -> Optional[int]:
    """
    Récupère le nombre de citations pour un DOI donné.

    Args:
        doi: DOI de la publication

    Returns:
        Nombre de citations ou None si erreur
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
        print(f"[CrossRef] Erreur lors de la récupération des citations pour {doi}: {e}")
        return None
