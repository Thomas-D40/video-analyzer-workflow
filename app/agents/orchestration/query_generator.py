"""
Enhanced query generation agent with better optimization and validation.

Improvements over original:
- API-specific query optimization
- Fallback query generation
- Query validation
- Confidence scoring
- Better prompt engineering
"""
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

from ...config import get_settings
from ...utils.api_helpers import retry_with_backoff, TransientAPIError

logger = logging.getLogger(__name__)


class QueryGenerator:
    """
    Enhanced query generator using LLM with caching and validation.
    """

    # Expected agents and their requirements
    AGENT_REQUIREMENTS = {
        "pubmed": {
            "language": "English",
            "style": "Medical terminology, MeSH terms",
            "length": "3-5 keywords",
            "example": "coffee consumption cancer risk epidemiology"
        },
        "arxiv": {
            "language": "English",
            "style": "Academic, technical terms",
            "length": "4-6 keywords",
            "example": "machine learning neural networks optimization"
        },
        "semantic_scholar": {
            "language": "English",
            "style": "Broad academic query with synonyms",
            "length": "5-8 keywords",
            "example": "artificial intelligence applications healthcare"
        },
        "crossref": {
            "language": "English",
            "style": "Formal academic terms",
            "length": "3-5 keywords",
            "example": "climate change economic impact"
        },
        "oecd": {
            "language": "English",
            "style": "Standard indicator names (GDP, unemployment, etc.)",
            "length": "2-4 keywords",
            "example": "GDP growth rate"
        },
        "world_bank": {
            "language": "English",
            "style": "Economic/development indicators",
            "length": "2-4 keywords",
            "example": "poverty rate income inequality"
        }
    }

    def __init__(self):
        """Initialize query generator."""
        self.settings = get_settings()
        if self.settings.openai_api_key:
            self.client = OpenAI(api_key=self.settings.openai_api_key)
            self.available = True
            logger.info("Query generator initialized")
        else:
            self.client = None
            self.available = False
            logger.warning("Query generator not available (no OpenAI key)")

    def _build_enhanced_prompt(self, argument: str, agents: List[str], language: str = "fr") -> str:
        """
        Build enhanced prompt for query generation.

        Args:
            argument: Argument to generate queries for
            agents: List of target agents
            language: Detected language of argument

        Returns:
            Prompt string
        """
        # Build agent-specific instructions
        agent_instructions = []
        for agent in agents:
            if agent in self.AGENT_REQUIREMENTS:
                req = self.AGENT_REQUIREMENTS[agent]
                agent_instructions.append(
                    f'\n{agent}:\n'
                    f'  - Language: {req["language"]}\n'
                    f'  - Style: {req["style"]}\n'
                    f'  - Length: {req["length"]}\n'
                    f'  - Example: "{req["example"]}"'
                )

        prompt = f"""You are an expert in academic and statistical information retrieval.
Your task is to generate HIGHLY OPTIMIZED search queries for different databases and APIs.

Argument to research: "{argument}"
Detected language: {language}

Generate search queries for these sources:
{''.join(agent_instructions)}

CRITICAL REQUIREMENTS:

1. OECD queries:
   - Use standard indicator names: "GDP", "unemployment rate", "inflation", "education spending"
   - Keep it simple and direct (2-4 words max)
   - Match official OECD terminology
   - Examples: "GDP growth", "unemployment rate", "health expenditure"

2. World Bank queries:
   - Use development/economic indicator terms
   - Keep concise (2-4 keywords)
   - Examples: "poverty rate", "life expectancy", "GDP per capita"

3. PubMed queries:
   - Medical/health topics ONLY
   - Use proper medical terminology
   - If not medical, return empty string ""

4. ArXiv queries:
   - Scientific/technical topics ONLY (physics, CS, math)
   - Use academic terminology
   - If not scientific, return empty string ""

5. Semantic Scholar / CrossRef:
   - Can handle any academic topic
   - Be comprehensive but focused
   - Include key concepts and related terms

Also provide fallback queries (alternatives if primary query fails) for each agent.

Example output format:
{{
    "pubmed": {{
        "query": "coffee cancer risk epidemiology",
        "fallback": ["coffee health effects", "caffeine cancer"],
        "confidence": 0.85
    }},
    "oecd": {{
        "query": "GDP growth",
        "fallback": ["economic growth", "national accounts"],
        "confidence": 0.90
    }},
    "world_bank": {{
        "query": "GDP growth rate",
        "fallback": ["economic growth"],
        "confidence": 0.90
    }}
}}

Respond ONLY with valid JSON. Set confidence between 0.0 and 1.0 based on query quality.
If a source is not relevant, use empty string "" for query and empty array for fallback.
"""
        return prompt

    @retry_with_backoff(max_attempts=2, base_delay=1.0)
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM to generate queries.

        Args:
            prompt: Prompt string

        Returns:
            Dictionary of queries

        Raises:
            TransientAPIError: If LLM call fails
        """
        if not self.available:
            raise TransientAPIError("OpenAI client not available")

        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a precise research query optimizer that responds in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            content = response.choices[0].message.content
            queries = json.loads(content)

            return queries

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise TransientAPIError(f"JSON parse error: {e}")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise TransientAPIError(f"LLM error: {e}")

    def _get_fallback_queries(self, argument: str, agents: List[str]) -> Dict[str, Any]:
        """
        Generate simple fallback queries without LLM.

        Args:
            argument: Argument text
            agents: Target agents

        Returns:
            Dictionary of basic queries
        """
        # Extract main keywords (simple approach)
        words = argument.lower().split()
        keywords = [w for w in words if len(w) > 3][:5]
        simple_query = " ".join(keywords)

        queries = {}
        for agent in agents:
            if agent in ["oecd", "world_bank"]:
                # For statistical sources, try to extract economic terms
                economic_terms = ["gdp", "unemployment", "inflation", "poverty", "growth", "trade"]
                found_terms = [t for t in economic_terms if t in argument.lower()]
                query = " ".join(found_terms) if found_terms else "economic indicators"
            else:
                query = simple_query

            queries[agent] = {
                "query": query,
                "fallback": [simple_query],
                "confidence": 0.3
            }

        logger.info("Using fallback query generation")
        return queries

    def generate_queries(self,
                        argument: str,
                        agents: Optional[List[str]] = None,
                        language: str = "fr",
                        use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Generate optimized search queries for multiple agents.

        Args:
            argument: Argument to research
            agents: List of agent names (None = all agents)
            language: Detected language of argument
            use_cache: Whether to use cached queries

        Returns:
            Dictionary mapping agent names to query metadata:
            {
                "agent_name": {
                    "query": "optimized query string",
                    "fallback": ["fallback", "queries"],
                    "confidence": 0.85
                }
            }

        Example:
            >>> gen = QueryGenerator()
            >>> queries = gen.generate_queries("Le café cause le cancer", ["pubmed", "oecd"])
            >>> print(queries["pubmed"]["query"])
            "coffee cancer risk"
        """
        if not argument or len(argument.strip()) < 3:
            logger.warning("Argument too short for query generation")
            return {}

        # Default agents
        if agents is None:
            agents = ["pubmed", "arxiv", "semantic_scholar", "crossref",
                     "oecd", "world_bank"]

        # Generate queries
        try:
            prompt = self._build_enhanced_prompt(argument, agents, language)
            queries = self._call_llm(prompt)

            # Validate and clean up
            for agent in agents:
                if agent not in queries:
                    queries[agent] = {"query": "", "fallback": [], "confidence": 0.0}

                # Ensure required fields
                if "fallback" not in queries[agent]:
                    queries[agent]["fallback"] = []
                if "confidence" not in queries[agent]:
                    queries[agent]["confidence"] = 0.5

            # Log generated queries
            logger.info(f"Generated queries for {len(queries)} agents")
            for agent, data in queries.items():
                if data.get("query"):
                    logger.debug(f"  {agent}: '{data['query'][:60]}...' (conf: {data.get('confidence', 0):.2f})")

            return queries

        except TransientAPIError as e:
            logger.warning(f"Query generation failed: {e}, using fallback")
            return self._get_fallback_queries(argument, agents)

        except Exception as e:
            logger.error(f"Unexpected error in query generation: {e}")
            return self._get_fallback_queries(argument, agents)


# Module-level convenience function for backward compatibility
_query_generator = None


def generate_search_queries(argument: str,
                           agents: Optional[List[str]] = None,
                           language: str = "fr") -> Dict[str, str]:
    """
    Generate optimized search queries (backward compatible function).

    Args:
        argument: Argument to research
        agents: List of agent names
        language: Detected language

    Returns:
        Dictionary mapping agent names to query strings (simplified format)

    Example:
        >>> queries = generate_search_queries("Coffee causes cancer")
        >>> print(queries["pubmed"])
        "coffee cancer risk epidemiology"
    """
    global _query_generator

    if _query_generator is None:
        _query_generator = QueryGenerator()

    # Get enhanced queries
    enhanced_queries = _query_generator.generate_queries(argument, agents, language)

    # Convert to simple format for backward compatibility
    simple_queries = {}
    for agent, data in enhanced_queries.items():
        simple_queries[agent] = data.get("query", "")

    return simple_queries


def generate_search_queries_enhanced(argument: str,
                                    agents: Optional[List[str]] = None,
                                    language: str = "fr") -> Dict[str, Dict[str, Any]]:
    """
    Generate optimized search queries with metadata (enhanced version).

    This version returns full metadata including fallback queries and confidence scores.

    Args:
        argument: Argument to research
        agents: List of agent names
        language: Detected language

    Returns:
        Dictionary mapping agent names to query metadata

    Example:
        >>> queries = generate_search_queries_enhanced("Coffee causes cancer")
        >>> pubmed_data = queries["pubmed"]
        >>> print(f"Query: {pubmed_data['query']}")
        >>> print(f"Confidence: {pubmed_data['confidence']}")
        >>> print(f"Fallbacks: {pubmed_data['fallback']}")
    """
    global _query_generator

    if _query_generator is None:
        _query_generator = QueryGenerator()

    return _query_generator.generate_queries(argument, agents, language)
