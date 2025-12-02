"""
Enhanced World Bank research agent with improved search and error handling.

This agent uses the wbgapi library to access World Bank data with:
- Multi-strategy search approaches
- Broader country coverage
- Time series data
- Better error handling and fallbacks
"""
from typing import List, Dict, Any, Optional
import logging
import re

try:
    import wbgapi as wb
    WBGAPI_AVAILABLE = True
except ImportError:
    WBGAPI_AVAILABLE = False
    logging.warning("wbgapi not installed. Install with: pip install wbgapi")

from ...utils.api_helpers import (
    retry_with_backoff,
    TransientAPIError,
    rate_limiters,
    circuit_breakers
)

logger = logging.getLogger(__name__)


class WorldBankAgent:
    """
    Enhanced World Bank research agent.

    Features:
    - Multi-strategy indicator search
    - Context-aware country selection
    - Time series data retrieval
    - Intelligent caching
    - Robust error handling
    """

    # Common economic terms mapping (French → English)
    TERM_MAPPING = {
        "impôt": "tax revenue",
        "taxe": "tax",
        "pib": "gdp",
        "richesse": "wealth",
        "inégalité": "inequality gini",
        "revenu": "income",
        "chômage": "unemployment",
        "dette": "debt",
        "croissance": "growth gdp",
        "pauvreté": "poverty",
        "éducation": "education",
        "santé": "health",
        "mortalité": "mortality",
        "espérance de vie": "life expectancy",
        "inflation": "inflation",
        "commerce": "trade",
        "exportation": "exports",
        "importation": "imports"
    }

    # Country groups for different contexts
    COUNTRY_GROUPS = {
        "developed": ["USA", "DEU", "FRA", "GBR", "JPN", "CAN", "ITA"],  # G7
        "europe": ["FRA", "DEU", "GBR", "ITA", "ESP", "NLD", "BEL", "SWE"],
        "emerging": ["CHN", "IND", "BRA", "RUS", "ZAF", "MEX", "IDN"],
        "default": ["FRA", "WLD"],  # France and World
        "major": ["USA", "CHN", "JPN", "DEU", "GBR", "FRA", "IND", "BRA", "WLD"]
    }

    # Fallback indicators for common topics
    FALLBACK_INDICATORS = {
        "gdp": ["NY.GDP.MKTP.CD", "NY.GDP.MKTP.KD.ZG"],
        "unemployment": ["SL.UEM.TOTL.ZS"],
        "poverty": ["SI.POV.DDAY", "SI.POV.NAHC"],
        "education": ["SE.XPD.TOTL.GD.ZS", "SE.ADT.LITR.ZS"],
        "health": ["SH.XPD.CHEX.GD.ZS", "SP.DYN.LE00.IN"],
        "inequality": ["SI.POV.GINI"],
        "trade": ["NE.TRD.GNFS.ZS"],
        "debt": ["GC.DOD.TOTL.GD.ZS"]
    }

    def __init__(self):
        """Initialize World Bank agent."""
        if not WBGAPI_AVAILABLE:
            logger.error("wbgapi not available. World Bank agent will not function.")
            self.available = False
        else:
            self.available = True
            logger.info("World Bank agent initialized successfully")

    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract search keywords from query.

        Handles both French and English, maps French terms to English.

        Args:
            query: Search query

        Returns:
            List of English keywords for search
        """
        query_lower = query.lower()
        keywords = []

        # Check French term mappings
        for french_term, english_term in self.TERM_MAPPING.items():
            if french_term in query_lower:
                keywords.append(english_term)

        # Extract English terms (simple word extraction)
        words = re.findall(r'\w+', query_lower)
        # Filter out common words
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
                      'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for'}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                if word not in ' '.join(keywords):  # Avoid duplicates
                    keywords.append(word)

        return keywords[:5]  # Limit to 5 keywords

    def _detect_countries_from_query(self, query: str) -> List[str]:
        """
        Detect relevant countries from query.

        Args:
            query: Search query

        Returns:
            List of ISO country codes
        """
        query_lower = query.lower()

        # Country name to ISO code mapping (common cases)
        country_map = {
            "france": "FRA", "français": "FRA", "french": "FRA",
            "germany": "DEU", "allemagne": "DEU", "german": "DEU",
            "usa": "USA", "united states": "USA", "america": "USA", "états-unis": "USA",
            "uk": "GBR", "britain": "GBR", "royaume-uni": "GBR",
            "china": "CHN", "chine": "CHN",
            "japan": "JPN", "japon": "JPN",
            "india": "IND", "inde": "IND",
            "world": "WLD", "monde": "WLD", "global": "WLD"
        }

        detected = []
        for name, code in country_map.items():
            if name in query_lower:
                detected.append(code)

        # Default: France and World
        if not detected:
            detected = ["FRA", "WLD"]

        # Always include World if not already present
        if "WLD" not in detected and len(detected) < 3:
            detected.append("WLD")

        return detected

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def _search_indicators(self, query: str, max_indicators: int = 3) -> List[str]:
        """
        Search for World Bank indicators matching query.

        Args:
            query: Search query
            max_indicators: Maximum number of indicators to return

        Returns:
            List of indicator codes

        Raises:
            TransientAPIError: If search fails
        """
        if not self.available:
            raise TransientAPIError("wbgapi not available")

        # Apply rate limiting
        rate_limiters["world_bank"].wait_if_needed()

        try:
            # Strategy 1: Direct query search
            indicators = wb.series.info(q=query)
            found_codes = []

            for row in indicators:
                found_codes.append(row['id'])
                if len(found_codes) >= max_indicators:
                    break

            if found_codes:
                logger.debug(f"Found {len(found_codes)} indicators for '{query}'")
                return found_codes

            # Strategy 2: Try with extracted keywords
            keywords = self._extract_keywords(query)
            for keyword in keywords:
                try:
                    indicators = wb.series.info(q=keyword)
                    for row in indicators:
                        code = row['id']
                        if code not in found_codes:
                            found_codes.append(code)
                        if len(found_codes) >= max_indicators:
                            break
                    if len(found_codes) >= max_indicators:
                        break
                except Exception as e:
                    logger.debug(f"Keyword '{keyword}' search failed: {e}")
                    continue

            if found_codes:
                logger.debug(f"Found {len(found_codes)} indicators using keywords")
                return found_codes

            # Strategy 3: Fallback to common indicators based on topic
            query_lower = query.lower()
            for topic, indicator_codes in self.FALLBACK_INDICATORS.items():
                if topic in query_lower:
                    logger.info(f"Using fallback indicators for topic '{topic}'")
                    return indicator_codes[:max_indicators]

            # Strategy 4: Last resort - return most common economic indicators
            logger.info("Using default economic indicators")
            return ["NY.GDP.MKTP.CD", "SP.POP.TOTL", "NY.GDP.PCAP.CD"][:max_indicators]

        except Exception as e:
            logger.error(f"World Bank indicator search failed: {e}")
            raise TransientAPIError(f"Indicator search failed: {e}")

    @retry_with_backoff(max_attempts=2, base_delay=1.0)
    def _fetch_indicator_data(self,
                             indicator_codes: List[str],
                             countries: List[str],
                             years: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch data for indicators.

        Args:
            indicator_codes: List of indicator codes
            countries: List of country codes
            years: Number of recent years to fetch

        Returns:
            List of data points

        Raises:
            TransientAPIError: If data fetch fails
        """
        if not self.available:
            raise TransientAPIError("wbgapi not available")

        # Apply rate limiting
        rate_limiters["world_bank"].wait_if_needed()

        try:
            # Fetch data using wbgapi
            # mrv = Most Recent Value; years = number of most recent values
            data = wb.data.DataFrame(indicator_codes, countries, mrv=years)

            if data.empty:
                logger.warning("No data returned from World Bank")
                return []

            # Convert to list of dictionaries
            data_points = []
            df = data.reset_index()

            # Get indicator names
            indicator_names = {}
            for code in indicator_codes:
                try:
                    info = wb.series.get(code)
                    indicator_names[code] = info.get('value', code)
                except Exception:
                    indicator_names[code] = code

            # Process data
            for _, row in df.iterrows():
                economy = row.get('economy', 'Unknown')

                # Map economy code to name
                economy_name = economy
                if economy == "FRA":
                    economy_name = "France"
                elif economy == "WLD":
                    economy_name = "World"
                elif economy == "USA":
                    economy_name = "United States"
                elif economy == "DEU":
                    economy_name = "Germany"
                # Add more mappings as needed

                # Each indicator is a column
                for code in indicator_codes:
                    if code in row and row[code] is not None:
                        # Get the time period (year) from the column name if available
                        # The DataFrame structure varies, so we handle it flexibly
                        year = None
                        if 'time' in row:
                            year = row['time']

                        data_points.append({
                            "indicator": indicator_names.get(code, code),
                            "indicator_code": code,
                            "region": economy_name,
                            "country_code": economy,
                            "value": float(row[code]),
                            "year": year,
                            "source": "World Bank"
                        })

            logger.debug(f"Retrieved {len(data_points)} data points")
            return data_points

        except Exception as e:
            logger.error(f"Failed to fetch World Bank data: {e}")
            raise TransientAPIError(f"Data fetch failed: {e}")

    def search_world_bank_data(self,
                               query: str,
                               countries: Optional[List[str]] = None,
                               years: int = 5,
                               max_indicators: int = 3) -> List[Dict[str, Any]]:
        """
        Search World Bank data with enhanced capabilities.

        Args:
            query: Search query (can be in French or English)
            countries: List of country codes (auto-detected if None)
            years: Number of recent years to retrieve (default: 5)
            max_indicators: Maximum number of indicators (default: 3)

        Returns:
            List of data points with indicator values

        Example:
            >>> agent = WorldBankAgent()
            >>> data = agent.search_world_bank_data("GDP France")
            >>> for point in data:
            ...     print(f"{point['indicator']}: {point['value']}")
        """
        if not self.available:
            logger.error("World Bank agent not available")
            return []

        if not query or len(query.strip()) < 3:
            logger.warning("Query too short for World Bank search")
            return []

        try:
            # Use circuit breaker
            return circuit_breakers["world_bank"].call(
                self._search_world_bank_data_impl,
                query,
                countries,
                years,
                max_indicators
            )
        except Exception as e:
            logger.error(f"World Bank search failed: {e}")
            return []

    def _search_world_bank_data_impl(self,
                                    query: str,
                                    countries: Optional[List[str]],
                                    years: int,
                                    max_indicators: int) -> List[Dict[str, Any]]:
        """
        Implementation of World Bank search.

        Args:
            query: Search query
            countries: Country codes or None
            years: Number of years
            max_indicators: Max indicators

        Returns:
            List of data points
        """
        # Auto-detect countries if not provided
        if countries is None:
            countries = self._detect_countries_from_query(query)
            logger.debug(f"Auto-detected countries: {countries}")

        # Limit countries to avoid overwhelming results
        if len(countries) > 5:
            countries = countries[:5]

        # Search for indicators
        try:
            indicator_codes = self._search_indicators(query, max_indicators)
            if not indicator_codes:
                logger.warning(f"No indicators found for query: {query}")
                return []

            logger.info(f"Searching World Bank for: '{query}' "
                       f"(indicators: {indicator_codes}, countries: {countries})")

            # Fetch data
            data_points = self._fetch_indicator_data(indicator_codes, countries, years)

            logger.info(f"[World Bank] Retrieved {len(data_points)} data points for: {query}")
            return data_points

        except TransientAPIError as e:
            logger.error(f"World Bank API error: {e}")
            return []


# Module-level convenience function for backward compatibility
_wb_agent = None


def search_world_bank_data(query: str,
                           countries: Optional[List[str]] = None,
                           years: int = 1,
                           max_indicators: int = 3) -> List[Dict[str, Any]]:
    """
    Search World Bank data (backward compatible function).

    Args:
        query: Search query (can be argument text or optimized query)
        countries: List of country codes (auto-detected if None)
        years: Number of recent years (default: 1 for compatibility)
        max_indicators: Maximum indicators (default: 3)

    Returns:
        List of data points

    Example:
        >>> data = search_world_bank_data("GDP growth")
        >>> for point in data:
        ...     print(f"{point['indicator']}: {point['value']}")
    """
    global _wb_agent

    if _wb_agent is None:
        _wb_agent = WorldBankAgent()

    return _wb_agent.search_world_bank_data(query, countries, years, max_indicators)
