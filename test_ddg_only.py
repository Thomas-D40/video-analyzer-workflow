from duckduckgo_search import DDGS
import arxiv

def test_real_case():
    argument = "L'eau du robinet est de plus en plus polluée, avec un taux de conformité de l'eau potable passant de 95 % en 2021 à 85 % en 2025."
    
    print("\n--- Test DDG (Cas Réel) ---")
    # Logique de research.py
    query_ddg = f"{argument} étude scientifique recherche académique"
    print(f"Requête DDG: '{query_ddg}'")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query_ddg, max_results=5))
            print(f"Résultats DDG: {len(results)}")
            for r in results:
                print(f"- {r.get('title')}")
    except Exception as e:
        print(f"ERREUR DDG: {e}")

    print("\n--- Test ArXiv (Cas Réel) ---")
    # Logique de scientific_research.py
    words = [w for w in argument.split() if len(w) > 4]
    if not words:
        words = argument.split()[:5]
    query_arxiv = " AND ".join(words[:4])
    print(f"Mots extraits: {words}")
    print(f"Requête ArXiv générée: '{query_arxiv}'")
    
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query_arxiv,
            max_results=5,
            sort_by=arxiv.SortCriterion.Relevance
        )
        results = list(client.results(search))
        print(f"Résultats ArXiv: {len(results)}")
        for r in results:
            print(f"- {r.title}")
    except Exception as e:
        print(f"ERREUR ArXiv: {e}")

if __name__ == "__main__":
    test_real_case()
