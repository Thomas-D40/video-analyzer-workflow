import logging
from duckduckgo_search import DDGS
import arxiv

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

def test_ddg():
    print("\n--- Test DuckDuckGo ---")
    query = "pollution eau france étude scientifique"
    print(f"Requête: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            print(f"Nombre de résultats: {len(results)}")
            for i, r in enumerate(results):
                print(f"Result {i+1}: {r.get('title')} - {r.get('href')}")
    except Exception as e:
        print(f"ERREUR DuckDuckGo: {e}")

def test_arxiv():
    print("\n--- Test ArXiv ---")
    query = "water pollution"
    print(f"Requête: {query}")
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=5,
            sort_by=arxiv.SortCriterion.Relevance
        )
        results = list(client.results(search))
        print(f"Nombre de résultats: {len(results)}")
        for i, r in enumerate(results):
            print(f"Result {i+1}: {r.title} - {r.entry_id}")
    except Exception as e:
        print(f"ERREUR ArXiv: {e}")

if __name__ == "__main__":
    test_ddg()
    test_arxiv()
