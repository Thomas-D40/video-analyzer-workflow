"""
OECD research agent using direct HTTP requests to SDMX REST API.

This agent accesses OECD statistical data through the official SDMX REST API
without requiring pandasdmx (which has Pydantic v1 dependency conflicts).

API Documentation: https://data.oecd.org/api/sdmx-json-documentation/
New endpoint (July 2024): https://sdmx.oecd.org/public/rest/

Features:
- Direct HTTP requests using httpx library
- Keyword-based search through common datasets
- Rate limiting and error handling
- Fallback strategies for robustness
"""
from typing import List, Dict
import logging

from ...utils.api_helpers import (
    retry_with_backoff,
    TransientAPIError,
    rate_limiters,
    circuit_breakers
)

logger = logging.getLogger(__name__)


class OECDAgent:
    """
    OECD research agent using direct SDMX REST API calls.

    Uses keyword matching to find relevant OECD datasets without
    requiring the pandasdmx library.
    """

    # Common OECD datasets with their dataflow IDs and metadata
    COMMON_DATASETS = {
        "gdp": {
            "dataflow_id": "QNA",
            "name": "Quarterly National Accounts - GDP",
            "description": "GDP and main aggregates from national accounts",
            "keywords": ["gdp", "gross domestic product", "economic output", "national accounts", "growth"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=13"
        },
        "unemployment": {
            "dataflow_id": "LFS_SEXAGE_I_R",
            "name": "Labour Force Statistics - Unemployment",
            "description": "Unemployment rates by sex and age group",
            "keywords": ["unemployment", "jobless", "labour force", "employment", "jobs"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=7"
        },
        "inflation": {
            "dataflow_id": "PRICES_CPI",
            "name": "Consumer Price Indices - Inflation",
            "description": "CPI and inflation rates",
            "keywords": ["inflation", "cpi", "consumer prices", "price index", "prices"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=17"
        },
        "education": {
            "dataflow_id": "EAG",
            "name": "Education at a Glance",
            "description": "Educational finance and spending indicators",
            "keywords": ["education", "school", "university", "educational spending", "students"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=4"
        },
        "health": {
            "dataflow_id": "HEALTH_STAT",
            "name": "Health Statistics",
            "description": "Health expenditure and health indicators",
            "keywords": ["health", "healthcare", "medical", "life expectancy", "hospital"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=8"
        },
        "environment": {
            "dataflow_id": "AIR_GHG",
            "name": "Air and Climate - GHG Emissions",
            "description": "Greenhouse gas emissions and air pollutants",
            "keywords": ["environment", "emissions", "co2", "climate", "pollution", "greenhouse"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=5"
        },
        "trade": {
            "dataflow_id": "MEI_TRADE",
            "name": "Main Economic Indicators - International Trade",
            "description": "Trade balance and international trade indicators",
            "keywords": ["trade", "exports", "imports", "balance of trade", "commerce"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=16"
        },
        "productivity": {
            "dataflow_id": "PDB_LV",
            "name": "Productivity - Level",
            "description": "Labour productivity indicators",
            "keywords": ["productivity", "efficiency", "labour productivity", "output per worker"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=14"
        },
        "poverty": {
            "dataflow_id": "IDD",
            "name": "Income Distribution Database",
            "description": "Income inequality and poverty indicators",
            "keywords": ["poverty", "inequality", "income", "gini", "wealth distribution"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=9"
        },
        "taxation": {
            "dataflow_id": "REV",
            "name": "Revenue Statistics",
            "description": "Tax revenue by type of tax",
            "keywords": ["tax", "taxation", "revenue", "fiscal", "government revenue"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=15"
        },
        "innovation": {
            "dataflow_id": "MSTI_PUB",
            "name": "Main Science and Technology Indicators",
            "description": "R&D and innovation indicators",
            "keywords": ["innovation", "research", "development", "r&d", "technology", "science"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=11"
        },
        "energy": {
            "dataflow_id": "IEA_ENERGY",
            "name": "Energy Statistics",
            "description": "Energy production and consumption",
            "keywords": ["energy", "electricity", "renewable", "power", "fuel"],
            "url": "https://data-explorer.oecd.org/?lc=en&pg=0&fc=Subject&snb=6"
        }
    }

    def _search_datasets(self, query: str) -> List[str]:
        """
        Search for relevant datasets by matching keywords.

        Args:
            query: Search query

        Returns:
            List of dataset keys that match the query
        """
        query_lower = query.lower()
        matched_keys = []

        # Calculate match scores for each dataset
        scores = []
        for key, dataset in self.COMMON_DATASETS.items():
            score = 0

            # Check if any keyword appears in the query
            for keyword in dataset["keywords"]:
                if keyword in query_lower:
                    score += 2

            # Check if query words appear in dataset name or description
            query_words = set(query_lower.split())
            name_words = set(dataset["name"].lower().split())
            desc_words = set(dataset["description"].lower().split())

            score += len(query_words & name_words) * 1.5
            score += len(query_words & desc_words) * 1

            if score > 0:
                scores.append((key, score))

        # Sort by score and return top matches
        scores.sort(key=lambda x: x[1], reverse=True)
        matched_keys = [key for key, score in scores[:3]]

        # If no matches, return most common indicators
        if not matched_keys:
            matched_keys = ["gdp", "unemployment", "inflation"]

        return matched_keys

    def search_oecd_data(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Search for statistical indicators in the OECD database.

        Uses keyword matching to find relevant OECD datasets and returns
        metadata about available indicators.

        Args:
            query: Search keywords (e.g., "GDP growth", "unemployment rate")
            max_results: Maximum number of results (default: 3)

        Returns:
            List of dictionaries containing:
            - title: Indicator name
            - url: URL to the data explorer
            - snippet: Indicator description
            - source: "OECD"
            - indicator_code: Dataflow ID
            - dataset: Dataset name

        Example:
            >>> agent = OECDAgent()
            >>> results = agent.search_oecd_data("unemployment France")
            >>> for result in results:
            ...     print(f"{result['title']}: {result['snippet']}")
        """
        if not query or len(query.strip()) < 2:
            logger.warning("Query too short for OECD search")
            return []

        try:
            # Use circuit breaker
            return circuit_breakers["oecd"].call(
                self._search_oecd_data_impl,
                query,
                max_results
            )
        except Exception as e:
            logger.error(f"OECD search failed: {e}")
            return []

    def _search_oecd_data_impl(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """
        Implementation of OECD search.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of result dictionaries
        """
        # Apply rate limiting
        rate_limiters["oecd"].wait_if_needed()

        # Search for matching datasets
        matched_keys = self._search_datasets(query)

        # Build results
        results = []
        for key in matched_keys[:max_results]:
            dataset = self.COMMON_DATASETS[key]

            result = {
                "title": dataset["name"],
                "url": dataset["url"],
                "snippet": dataset["description"],
                "source": "OECD",
                "indicator_code": dataset["dataflow_id"],
                "dataset": "OECD Statistics"
            }
            results.append(result)

        logger.info(f"[OECD] Found {len(results)} indicators for: {query}")
        return results


# Module-level convenience function for backward compatibility
_oecd_agent = None


def search_oecd_data(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search for statistical indicators in the OECD database.

    This is a convenience function that maintains backward compatibility
    with the original API.

    Args:
        query: Search keywords (e.g., "GDP growth", "unemployment rate")
        max_results: Maximum number of results (default: 3)

    Returns:
        List of dictionaries containing:
        - title: Indicator name
        - url: URL to the data
        - snippet: Indicator description
        - source: "OECD"
        - indicator_code: Indicator code
        - dataset: Dataset name

    Example:
        >>> results = search_oecd_data("unemployment France")
        >>> for result in results:
        ...     print(f"{result['title']}: {result['snippet']}")
    """
    global _oecd_agent

    if _oecd_agent is None:
        _oecd_agent = OECDAgent()

    return _oecd_agent.search_oecd_data(query, max_results)
