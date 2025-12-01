"""
Agent de recherche pour PubMed (NCBI).

PubMed est la base de données de référence pour la littérature biomédicale
avec ~39 millions de citations d'articles de MEDLINE et autres sources.

API Documentation: https://www.ncbi.nlm.nih.gov/home/develop/api/
E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""
from typing import List, Dict
import requests
import xml.etree.ElementTree as ET
import time
from ...config import get_settings

def search_pubmed(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Recherche des articles biomédicaux sur PubMed.

    PubMed est la source la plus autoritaire pour les affirmations liées à la santé,
    médecine, biologie et sciences biomédicales.

    Args:
        query: Requête de recherche (idéalement en anglais)
        max_results: Nombre maximum de résultats (défaut: 5)

    Returns:
        Liste de dictionnaires contenant:
        - title: Titre de l'article
        - url: URL vers l'article sur PubMed
        - snippet: Résumé/abstract de l'article
        - source: "PubMed"
        - pmid: PubMed ID
        - journal: Nom du journal
        - year: Année de publication
        - authors: Liste des auteurs

    Raises:
        Exception: Si la requête échoue après plusieurs tentatives
    """
    settings = get_settings()
    base_url_search = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_url_fetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # API key (optionnel mais recommandé pour des limites plus élevées)
    # Sans clé: 3 requêtes/sec, avec clé: 10 requêtes/sec
    api_key = getattr(settings, 'ncbi_api_key', None)

    try:
        # Étape 1: Recherche pour obtenir les PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        if api_key:
            search_params["api_key"] = api_key

        response = requests.get(base_url_search, params=search_params, timeout=10)
        response.raise_for_status()
        search_data = response.json()

        # Extraire les PMIDs
        pmids = search_data.get("esearchresult", {}).get("idlist", [])

        if not pmids:
            print(f"[PubMed] Aucun résultat pour: {query}")
            return []

        # Respect rate limits
        time.sleep(0.34 if not api_key else 0.11)  # 3 req/s sans clé, 10 req/s avec clé

        # Étape 2: Récupérer les détails des articles
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract"
        }
        if api_key:
            fetch_params["api_key"] = api_key

        response = requests.get(base_url_fetch, params=fetch_params, timeout=15)
        response.raise_for_status()

        # Parser le XML
        root = ET.fromstring(response.content)
        articles = []

        for article_elem in root.findall(".//PubmedArticle"):
            try:
                # PMID
                pmid = article_elem.find(".//PMID")
                pmid_text = pmid.text if pmid is not None else "N/A"

                # Title
                title_elem = article_elem.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "Sans titre"

                # Abstract
                abstract_texts = article_elem.findall(".//AbstractText")
                abstract = " ".join([abs_text.text for abs_text in abstract_texts if abs_text.text])
                if not abstract:
                    abstract = "Pas de résumé disponible"

                # Journal
                journal_elem = article_elem.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else "N/A"

                # Year
                year_elem = article_elem.find(".//PubDate/Year")
                year = year_elem.text if year_elem is not None else "N/A"

                # Authors
                author_elems = article_elem.findall(".//Author")
                authors = []
                for author in author_elems[:3]:  # First 3 authors
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None:
                        name = lastname.text
                        if forename is not None:
                            name = f"{forename.text} {name}"
                        authors.append(name)

                article = {
                    "title": title,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/",
                    "snippet": abstract[:500],  # Limit snippet length
                    "source": "PubMed",
                    "pmid": pmid_text,
                    "journal": journal,
                    "year": year,
                    "authors": ", ".join(authors) if authors else "N/A"
                }

                articles.append(article)

            except Exception as e:
                print(f"[PubMed] Erreur lors du parsing d'un article: {e}")
                continue

        print(f"[PubMed] {len(articles)} articles trouvés pour: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[PubMed] Timeout lors de la recherche: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[PubMed] Erreur lors de la recherche: {e}")
        return []
    except ET.ParseError as e:
        print(f"[PubMed] Erreur de parsing XML: {e}")
        return []
    except Exception as e:
        print(f"[PubMed] Erreur inattendue: {e}")
        return []
