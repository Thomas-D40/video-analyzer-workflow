"""
Agent de recherche pour les données statistiques de l'OECD.

L'OECD (Organisation for Economic Co-operation and Development) fournit
des données statistiques sur les pays développés: GDP, inflation, emploi,
éducation, santé, innovation, climat.

API Documentation: https://data-explorer.oecd.org/
SDMX API: https://stats.oecd.org/SDMX-JSON/
"""
from typing import List, Dict
import requests
from ...config import get_settings

def search_oecd_data(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Recherche des indicateurs statistiques dans la base OECD.

    L'OECD est la source de référence pour les statistiques économiques
    et sociales des pays développés (membres de l'OECD).

    Args:
        query: Mots-clés de recherche (ex: "GDP growth", "unemployment rate")
        max_results: Nombre maximum de résultats (défaut: 3)

    Returns:
        Liste de dictionnaires contenant:
        - title: Nom de l'indicateur
        - url: URL vers les données
        - snippet: Description de l'indicateur
        - source: "OECD"
        - indicator_code: Code de l'indicateur
        - dataset: Nom du dataset

    Note:
        L'API OECD est complexe et nécessite des codes d'indicateurs spécifiques.
        Cette implémentation utilise une approche simplifiée avec des indicateurs
        prédéfinis courants.
    """
    # Mapping de mots-clés vers des indicateurs OECD courants
    # Pour une implémentation complète, utiliser l'API de recherche OECD
    keyword_mapping = {
        "gdp": {
            "code": "GDP",
            "name": "Gross Domestic Product",
            "description": "GDP measures the monetary value of final goods and services produced in a country",
            "url": "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_NAMAIN1%40DF_TABLE1&df[ag]=OECD.SDD.NAD&dq=.Q.._T.B1GQ.."
        },
        "unemployment": {
            "code": "LFS",
            "name": "Labour Force Statistics - Unemployment Rate",
            "description": "Unemployment rate as percentage of labour force",
            "url": "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_LFS%40DF_IALFS_UNE_M&df[ag]=OECD.ELS.SAE&dq=.M...."
        },
        "inflation": {
            "code": "CPI",
            "name": "Consumer Price Index - Inflation",
            "description": "Annual inflation rate measured by changes in consumer price indices",
            "url": "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_PRICES%40DF_PRICES_ALL&df[ag]=OECD.SDD.TPS&dq=..CPI...."
        },
        "education": {
            "code": "EDU",
            "name": "Education Statistics",
            "description": "Educational attainment and spending across OECD countries",
            "url": "https://data-explorer.oecd.org/vis?lc=en&pg=0&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_EDU%40EDU_FINANCE&df[ag]=OECD.EDU.IMEP"
        },
        "health": {
            "code": "HEALTH",
            "name": "Health Statistics",
            "description": "Health expenditure, life expectancy, and health indicators",
            "url": "https://data-explorer.oecd.org/vis?lc=en&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_HEALTH_STAT%40DF_SHA&df[ag]=OECD.ELS.HD"
        },
        "climate": {
            "code": "ENV",
            "name": "Environment - CO2 Emissions",
            "description": "CO2 emissions and environmental indicators",
            "url": "https://data-explorer.oecd.org/vis?lc=en&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_AEI%40DF_AIR_EMISSION&df[ag]=OECD.ENV.EPI"
        },
        "trade": {
            "code": "ITF",
            "name": "International Trade and Finance",
            "description": "Trade balance, exports, imports data",
            "url": "https://data-explorer.oecd.org/vis?lc=en&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_KEI%40DF_KEI&df[ag]=OECD.SDD.STES"
        },
        "productivity": {
            "code": "PDB",
            "name": "Productivity Statistics",
            "description": "Labour productivity and multifactor productivity",
            "url": "https://data-explorer.oecd.org/vis?lc=en&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_PDBI%40DF_PDBI_LEVEL&df[ag]=OECD.SDD.TPS"
        }
    }

    # Normaliser la requête
    query_lower = query.lower()

    # Trouver les indicateurs correspondants
    results = []
    for keyword, indicator in keyword_mapping.items():
        if keyword in query_lower:
            result = {
                "title": indicator["name"],
                "url": indicator["url"],
                "snippet": indicator["description"],
                "source": "OECD",
                "indicator_code": indicator["code"],
                "dataset": "OECD Statistics"
            }
            results.append(result)

            if len(results) >= max_results:
                break

    # Si aucun résultat spécifique, retourner des indicateurs généraux
    if not results:
        # Retourner les 3 indicateurs les plus courants
        general_indicators = ["gdp", "unemployment", "inflation"]
        for key in general_indicators[:max_results]:
            indicator = keyword_mapping[key]
            result = {
                "title": indicator["name"],
                "url": indicator["url"],
                "snippet": indicator["description"],
                "source": "OECD",
                "indicator_code": indicator["code"],
                "dataset": "OECD Statistics"
            }
            results.append(result)

    print(f"[OECD] {len(results)} indicateurs trouvés pour: {query}")
    return results


def get_oecd_indicator_data(indicator_code: str, countries: List[str] = None) -> Dict:
    """
    Récupère les données d'un indicateur OECD spécifique.

    Args:
        indicator_code: Code de l'indicateur OECD
        countries: Liste de codes pays (ex: ["USA", "FRA", "DEU"])

    Returns:
        Dictionnaire avec les données de l'indicateur

    Note:
        Cette fonction est un placeholder pour une implémentation complète.
        L'API SDMX de l'OECD nécessite une connaissance des structures de données.
    """
    # Pour une implémentation complète, utiliser l'API SDMX
    # https://stats.oecd.org/SDMX-JSON/
    print(f"[OECD] Récupération des données pour: {indicator_code}")
    return {
        "indicator": indicator_code,
        "message": "Full SDMX API implementation required for detailed data retrieval"
    }
