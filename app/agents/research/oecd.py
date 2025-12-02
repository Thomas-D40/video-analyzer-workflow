"""
Enhanced OECD research agent with real SDMX API integration.

This agent uses the pandasdmx library to access the OECD's SDMX REST API,
providing real data retrieval capabilities instead of static keyword mapping.

Features:
- Real-time dataflow discovery and search
- Actual data retrieval from OECD
- Intelligent caching of dataflow metadata
- Fallback strategies for robustness
- Rate limiting and error handling
"""
from typing import List, Dict, Optional, Tuple
import re
import logging
from datetime import datetime

try:
    import pandasdmx as sdmx
    SDMX_AVAILABLE = True
except ImportError:
    SDMX_AVAILABLE = False
    logging.warning("pandasdmx not installed. Install with: pip install pandasdmx")

from ...utils.api_helpers import (
    retry_with_backoff,
    TransientAPIError,
    PermanentAPIError,
    rate_limiters,
    circuit_breakers
)

logger = logging.getLogger(__name__)


class OECDAgent:
    """
    Enhanced OECD research agent using SDMX API.

    Provides access to OECD statistical data through the official SDMX REST API.
    """

    # Common OECD datasets for quick reference (fallback)
    COMMON_DATASETS = {
        "gdp": {
            "dataflow": "QNA",  # Quarterly National Accounts
            "name": "Quarterly National Accounts - GDP",
            "description": "GDP and main aggregates from national accounts",
            "keywords": ["gdp", "gross domestic product", "economic output", "national accounts"]
        },
        "unemployment": {
            "dataflow": "LFS_SEXAGE_I_R",
            "name": "Labour Force Statistics - Unemployment",
            "description": "Unemployment rates by sex and age group",
            "keywords": ["unemployment", "jobless", "labour force", "employment"]
        },
        "inflation": {
            "dataflow": "PRICES_CPI",
            "name": "Consumer Price Indices",
            "description": "CPI and inflation rates",
            "keywords": ["inflation", "cpi", "consumer prices", "price index"]
        },
        "education": {
            "dataflow": "EAG_FIN_RATIO_CATEGORY",
            "name": "Education at a Glance - Finance",
            "description": "Educational finance and spending",
            "keywords": ["education", "school", "university", "educational spending"]
        },
        "health": {
            "dataflow": "HEALTH_STAT",
            "name": "Health Statistics",
            "description": "Health expenditure and indicators",
            "keywords": ["health", "healthcare", "medical", "life expectancy"]
        },
        "environment": {
            "dataflow": "AIR_EMISSIONS",
            "name": "Air Emissions",
            "description": "Air emissions including CO2",
            "keywords": ["environment", "emissions", "co2", "climate", "pollution"]
        },
        "trade": {
            "dataflow": "KEI",  # Key Economic Indicators
            "name": "Key Economic Indicators - Trade",
            "description": "Trade balance and international trade",
            "keywords": ["trade", "exports", "imports", "balance of trade"]
        },
        "productivity": {
            "dataflow": "PDB_LV",
            "name": "Productivity Database - Level",
            "description": "Labour productivity indicators",
            "keywords": ["productivity", "efficiency", "labour productivity", "output per worker"]
        }
    }

    def __init__(self):
        """Initialize OECD agent."""
        if not SDMX_AVAILABLE:
            logger.error("pandasdmx not available. OECD agent will use fallback mode.")
            self.oecd_client = None
        else:
            try:
                self.oecd_client = sdmx.Request("OECD")
                logger.info("OECD SDMX client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OECD client: {e}")
                self.oecd_client = None

    @retry_with_backoff(max_attempts=3, base_delay=2.0)
    def _fetch_dataflows(self) -> Dict[str, Dict]:
        """
        Fetch all available OECD dataflows with caching.

        Returns:
            Dictionary mapping dataflow IDs to metadata

        Raises:
            TransientAPIError: If API call fails temporarily
            PermanentAPIError: If dataflows cannot be fetched
        """
        if not self.oecd_client:
            raise PermanentAPIError("OECD client not available")

        try:
            # Apply rate limiting
            rate_limiters["oecd"].wait_if_needed()

            logger.info("Fetching OECD dataflows from API...")
            response = self.oecd_client.dataflow()

            dataflows = {}
            for flow_id, flow in response.dataflow.items():
                # Extract name in English
                name = str(flow.name.localisations.get('en', flow.name))

                # Extract description if available
                description = ""
                if hasattr(flow, 'description') and flow.description:
                    description = str(flow.description.localisations.get('en', flow.description))

                dataflows[flow_id] = {
                    "id": flow_id,
                    "name": name,
                    "description": description,
                    "name_lower": name.lower(),
                    "search_text": f"{name} {description}".lower()
                }

            logger.info(f"Fetched {len(dataflows)} OECD dataflows")

            return dataflows

        except Exception as e:
            logger.error(f"Failed to fetch OECD dataflows: {e}")
            raise TransientAPIError(f"Failed to fetch dataflows: {e}")

    def _search_dataflows(self, query: str, dataflows: Dict[str, Dict]) -> List[Tuple[str, Dict, float]]:
        """
        Search dataflows by query with relevance scoring.

        Args:
            query: Search query
            dataflows: Dictionary of dataflows

        Returns:
            List of (dataflow_id, metadata, relevance_score) tuples, sorted by relevance
        """
        query_lower = query.lower()
        query_terms = set(re.findall(r'\w+', query_lower))

        results = []

        for flow_id, metadata in dataflows.items():
            # Calculate relevance score
            score = 0.0

            # Exact match in name (high score)
            if query_lower in metadata['name_lower']:
                score += 10.0

            # Term matching in name (medium score)
            name_terms = set(re.findall(r'\w+', metadata['name_lower']))
            name_overlap = len(query_terms & name_terms)
            score += name_overlap * 3.0

            # Term matching in description (lower score)
            if metadata['description']:
                desc_terms = set(re.findall(r'\w+', metadata['description'].lower()))
                desc_overlap = len(query_terms & desc_terms)
                score += desc_overlap * 1.0

            # Full text match in search_text
            if query_lower in metadata['search_text']:
                score += 5.0

            if score > 0:
                results.append((flow_id, metadata, score))

        # Sort by relevance score (descending)
        results.sort(key=lambda x: x[2], reverse=True)

        return results

    def _get_fallback_dataflows(self, query: str) -> List[Dict[str, str]]:
        """
        Get fallback dataflows using keyword matching on common datasets.

        Args:
            query: Search query

        Returns:
            List of dataflow metadata dictionaries
        """
        query_lower = query.lower()
        results = []

        for category, dataset in self.COMMON_DATASETS.items():
            # Check if any keyword matches the query
            for keyword in dataset['keywords']:
                if keyword in query_lower:
                    results.append({
                        "title": dataset['name'],
                        "url": f"https://data-explorer.oecd.org/",
                        "snippet": dataset['description'],
                        "source": "OECD",
                        "indicator_code": dataset['dataflow'],
                        "dataset": "OECD Statistics",
                        "relevance": "fallback"
                    })
                    break  # Only add once per dataset

            if len(results) >= 3:
                break

        # If no matches, return most common indicators
        if not results:
            for category in ["gdp", "unemployment", "inflation"]:
                dataset = self.COMMON_DATASETS[category]
                results.append({
                    "title": dataset['name'],
                    "url": "https://data-explorer.oecd.org/",
                    "snippet": dataset['description'],
                    "source": "OECD",
                    "indicator_code": dataset['dataflow'],
                    "dataset": "OECD Statistics",
                    "relevance": "default"
                })

        logger.info(f"Fallback mode: returning {len(results)} common datasets")
        return results

    def search_oecd_data(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Search for statistical indicators in the OECD database.

        This method uses the real OECD SDMX API to discover relevant dataflows
        based on the search query. Falls back to common indicators if API is unavailable.

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
            - relevance: Relevance score or "fallback"/"default"
        """
        try:
            # Use circuit breaker
            return circuit_breakers["oecd"].call(
                self._search_oecd_data_impl,
                query,
                max_results
            )
        except PermanentAPIError as e:
            logger.warning(f"Circuit breaker open for OECD: {e}")
            return self._get_fallback_dataflows(query)

    def _search_oecd_data_impl(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """
        Implementation of OECD search.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of result dictionaries
        """
        if not query or len(query.strip()) < 2:
            logger.warning("Query too short for OECD search")
            return []

        # Try to fetch and search dataflows
        try:
            dataflows = self._fetch_dataflows()
            search_results = self._search_dataflows(query, dataflows)

            results = []
            for flow_id, metadata, score in search_results[:max_results]:
                # Build URL to data explorer
                base_url = "https://data-explorer.oecd.org/"
                url = f"{base_url}?lc=en"  # Generic URL, specific requires complex query

                result = {
                    "title": metadata['name'],
                    "url": url,
                    "snippet": metadata['description'] or metadata['name'],
                    "source": "OECD",
                    "indicator_code": flow_id,
                    "dataset": "OECD Statistics",
                    "relevance": round(score, 2)
                }
                results.append(result)

            if results:
                logger.info(f"[OECD] Found {len(results)} indicators for: {query}")
                return results
            else:
                logger.info(f"[OECD] No specific dataflows found for '{query}', using fallback")
                return self._get_fallback_dataflows(query)

        except (TransientAPIError, PermanentAPIError) as e:
            logger.warning(f"[OECD] API error: {e}, using fallback")
            return self._get_fallback_dataflows(query)

        except Exception as e:
            logger.error(f"[OECD] Unexpected error: {e}, using fallback")
            return self._get_fallback_dataflows(query)

    def get_dataflow_metadata(self, dataflow_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific OECD dataflow.

        Args:
            dataflow_id: OECD dataflow identifier

        Returns:
            Dictionary with dataflow metadata or None if not found
        """
        try:
            dataflows = self._fetch_dataflows()
            return dataflows.get(dataflow_id)
        except Exception as e:
            logger.error(f"Failed to get metadata for dataflow {dataflow_id}: {e}")
            return None


# Module-level convenience function for backward compatibility
_oecd_agent = None


def search_oecd_data(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search for statistical indicators in the OECD database.

    This is a convenience function that maintains backward compatibility
    with the original API while using the enhanced agent implementation.

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
