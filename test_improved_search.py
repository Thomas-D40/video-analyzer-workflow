import os
from dotenv import load_dotenv

# Charger les variables d'environnement AVANT d'importer les modules de l'app
load_dotenv()

# Mock des variables manquantes si nécessaire pour le test
os.environ.setdefault("DATABASE_URL", "postgresql://dummy:dummy@localhost:5432/dummy")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.agents.research import search_literature
from app.agents.scientific_research import search_arxiv
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

def test_improved_search():
    argument = "L'eau du robinet est de plus en plus polluée, avec un taux de conformité de l'eau potable passant de 95 % en 2021 à 85 % en 2025."
    
    print("\n=== TEST RECHERCHE WEB (LLM) ===")
    try:
        results = search_literature(argument, max_results=3)
        print(f"Nombre de résultats Web: {len(results)}")
        for r in results:
            print(f"- {r.get('title')} ({r.get('url')})")
    except Exception as e:
        print(f"ERREUR Web: {e}")

    print("\n=== TEST RECHERCHE ARXIV (LLM) ===")
    try:
        results = search_arxiv(argument, max_results=3)
        print(f"Nombre de résultats ArXiv: {len(results)}")
        for r in results:
            print(f"- {r.get('title')} ({r.get('url')})")
    except Exception as e:
        print(f"ERREUR ArXiv: {e}")

if __name__ == "__main__":
    test_improved_search()
