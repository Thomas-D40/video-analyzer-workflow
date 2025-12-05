"""
Research agent for PubMed (NCBI).

PubMed is the reference database for biomedical literature
with ~39 million citations from MEDLINE and other sources.

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
    Search for biomedical articles on PubMed.

    PubMed is the most authoritative source for health-related claims,
    medicine, biology and biomedical sciences.

    Args:
        query: Search query (ideally in English)
        max_results: Maximum number of results (default: 5)

    Returns:
        List of dictionaries containing:
        - title: Article title
        - url: URL to the article on PubMed
        - snippet: Article abstract/summary
        - source: "PubMed"
        - pmid: PubMed ID
        - journal: Journal name
        - year: Publication year
        - authors: List of authors

    Raises:
        Exception: If the query fails after several attempts
    """
    settings = get_settings()
    base_url_search = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    base_url_fetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # API key (optional but recommended for higher limits)
    # Without key: 3 requests/sec, with key: 10 requests/sec
    api_key = getattr(settings, 'ncbi_api_key', None)

    try:
        # Step 1: Search to get PMIDs
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

        # Extract PMIDs
        pmids = search_data.get("esearchresult", {}).get("idlist", [])

        if not pmids:
            print(f"[PubMed] No results for: {query}")
            return []

        # Respect rate limits
        time.sleep(0.34 if not api_key else 0.11)  # 3 req/s without key, 10 req/s with key

        # Step 2: Fetch article details
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

        # Parse XML
        root = ET.fromstring(response.content)
        articles = []

        for article_elem in root.findall(".//PubmedArticle"):
            try:
                # PMID
                pmid = article_elem.find(".//PMID")
                pmid_text = pmid.text if pmid is not None else "N/A"

                # Title
                title_elem = article_elem.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "Untitled"

                # Abstract
                abstract_texts = article_elem.findall(".//AbstractText")
                abstract = " ".join([abs_text.text for abs_text in abstract_texts if abs_text.text])
                if not abstract:
                    abstract = "No abstract available"

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

                # Check for PMC ID (indicates potential full text access)
                pmc_id = article_elem.find(".//ArticleId[@IdType='pmc']")
                has_pmc = pmc_id is not None

                # Determine access type
                if has_pmc:
                    access_type = "open_access"
                    has_full_text = True
                    access_note = f"Full text available via PMC{pmc_id.text}"
                else:
                    access_type = "abstract_only"
                    has_full_text = False
                    access_note = "Abstract only - full text may require subscription"

                article = {
                    "title": title,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/",
                    "snippet": abstract[:500],  # Limit snippet length
                    "source": "PubMed",
                    "pmid": pmid_text,
                    "journal": journal,
                    "year": year,
                    "authors": ", ".join(authors) if authors else "N/A",
                    "access_type": access_type,
                    "has_full_text": has_full_text,
                    "access_note": access_note
                }

                articles.append(article)

            except Exception as e:
                print(f"[PubMed] Error parsing article: {e}")
                continue

        print(f"[PubMed] {len(articles)} articles found for: {query}")
        return articles

    except requests.exceptions.Timeout:
        print(f"[PubMed] Timeout during search: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[PubMed] Error during search: {e}")
        return []
    except ET.ParseError as e:
        print(f"[PubMed] XML parsing error: {e}")
        return []
    except Exception as e:
        print(f"[PubMed] Unexpected error: {e}")
        return []
