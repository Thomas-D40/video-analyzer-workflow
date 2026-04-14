"""
Parallel research execution for arguments.

This module provides async functions to execute research in parallel,
significantly reducing total processing time.

All research services are native async — no ThreadPoolExecutor needed.
OpenAI-based agents (orchestration, analysis) remain synchronous and are
wrapped with asyncio.to_thread().
"""
import asyncio
from typing import Dict, List, Any

from app.services.research import (
    search_arxiv,
    search_world_bank_data,
    search_pubmed,
    search_semantic_scholar,
    search_crossref,
    search_oecd_data,
    search_core,
    search_doaj,
    search_europepmc,
)
from app.agents.orchestration import (
    generate_search_queries,
    get_research_strategy,
)
from app.agents.enrichment import (
    screen_sources_by_relevance,
    fetch_fulltext_for_sources,
    get_screening_stats,
)
from app.agents.analysis import extract_pros_cons
from app.logger import get_logger

logger = get_logger(__name__)


async def research_single_agent(
    agent_name: str,
    query: str,
    max_results: int = 5
) -> tuple[str, List[Dict], Exception | None]:
    """
    Execute research for a single agent asynchronously.

    Args:
        agent_name: Name of the research agent
        query: Search query
        max_results: Maximum results to return

    Returns:
        Tuple of (agent_name, results, error)
    """
    if not query:
        return (agent_name, [], None)

    try:
        logger.debug("agent_search_start", agent=agent_name, query_preview=query[:50])

        # All research services are async — await directly
        agent_funcs = {
            "pubmed": lambda: search_pubmed(query, max_results),
            "europepmc": lambda: search_europepmc(query, max_results),
            "arxiv": lambda: search_arxiv(query, max_results),
            "semantic_scholar": lambda: search_semantic_scholar(query, max_results),
            "crossref": lambda: search_crossref(query, max_results=3),
            "core": lambda: search_core(query, max_results),
            "doaj": lambda: search_doaj(query, max_results),
            "oecd": lambda: search_oecd_data(query, max_results=3),
            "world_bank": lambda: search_world_bank_data(query),
        }

        if agent_name not in agent_funcs:
            return (agent_name, [], None)

        results = await agent_funcs[agent_name]()

        logger.debug("agent_search_end", agent=agent_name, results_count=len(results))
        return (agent_name, results, None)

    except Exception as e:
        logger.warning("agent_search_failed", agent=agent_name, detail=str(e))
        return (agent_name, [], e)


async def research_argument_parallel(
    argument_text: str,
    argument_en: str,
    arg_data: Dict[str, Any],
    analysis_mode: str = "abstract_only"
) -> Dict[str, Any]:
    """
    Execute research for a single argument with parallel API calls.

    Args:
        argument_text: Original argument text
        argument_en: English version for research
        arg_data: Original argument data
        analysis_mode: "simple" (fast, cheap) or "medium"/"hard" (deep, expensive)

    Returns:
        Enriched argument with research results
    """
    # Step 1: Determine research strategy (sync OpenAI call → thread)
    try:
        strategy = await asyncio.to_thread(get_research_strategy, argument_en)
        selected_agents = strategy["agents"]
        categories = strategy["categories"]
        logger.debug("research_strategy", categories=categories, agents=selected_agents)
    except Exception as e:
        logger.error("research_strategy_failed", detail=str(e))
        selected_agents = ["semantic_scholar", "crossref"]
        categories = ["general"]

    # Step 2: Generate optimized queries (sync OpenAI call → thread)
    try:
        queries = await asyncio.to_thread(
            generate_search_queries,
            argument_en,
            selected_agents
        )
    except Exception as e:
        logger.error("query_generation_failed", detail=str(e))
        queries = {}

    # Step 3: Execute all agent searches in parallel
    tasks = [
        research_single_agent(agent_name, queries.get(agent_name, ""))
        for agent_name in selected_agents
        if queries.get(agent_name, "")
    ]

    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Step 4: Collect all results
    all_sources = []
    for agent_name, agent_results, error in results:
        if error:
            continue
        all_sources.extend(agent_results)

    logger.debug("sources_collected", argument_preview=argument_text[:50], total_sources=len(all_sources))

    # Map analysis modes to enrichment configuration
    mode_config = {
        "simple": {"enabled": False, "top_n": 0, "min_score": 0.0},
        "medium": {"enabled": True, "top_n": 3, "min_score": 0.6},
        "hard": {"enabled": True, "top_n": 6, "min_score": 0.5},
    }

    config = mode_config.get(analysis_mode, mode_config["simple"])
    enrichment_enabled = config["enabled"]
    top_n = config["top_n"]
    min_score = config["min_score"]

    logger.info("enrichment_config", analysis_mode=analysis_mode, fulltext_top_n=top_n, min_score=min_score)

    # Step 4.5: Enrichment - Screen for relevance (sync OpenAI call → thread)
    if enrichment_enabled and all_sources:
        try:
            logger.info("screening_start", sources_count=len(all_sources), top_n=top_n, min_score=min_score)

            selected_sources, rejected_sources = await asyncio.to_thread(
                screen_sources_by_relevance,
                argument_en,
                all_sources,
                "en",
                top_n,
                min_score
            )

            stats = get_screening_stats(all_sources)
            logger.debug(
                "screening_stats",
                avg_score=round(stats['avg_score'], 2),
                high_relevance=stats['high_relevance'],
                medium_relevance=stats['medium_relevance'],
                low_relevance=stats['low_relevance'],
            )

        except Exception as e:
            logger.error("screening_failed", detail=str(e))
            selected_sources = all_sources[:top_n] if top_n > 0 else []
            rejected_sources = all_sources[top_n:] if top_n > 0 else all_sources
    else:
        logger.info("enrichment_disabled", analysis_mode=analysis_mode)
        selected_sources = []
        rejected_sources = all_sources

    # Step 4.6: Enrichment - Fetch full text for top sources (async, parallel)
    if enrichment_enabled and selected_sources:
        try:
            logger.info("fulltext_fetch_start", sources_count=len(selected_sources))

            enhanced_sources = await fetch_fulltext_for_sources(selected_sources)

            fulltext_count = sum(1 for s in enhanced_sources if "fulltext" in s)
            logger.info("fulltext_fetch_end", retrieved=fulltext_count, requested=len(selected_sources))

            final_sources = enhanced_sources + rejected_sources

        except Exception as e:
            logger.error("fulltext_fetch_failed", detail=str(e))
            final_sources = all_sources
    else:
        final_sources = all_sources

    # Reorganize final sources by type (for report)
    sources_by_type = {
        "scientific": [],
        "medical": [],
        "statistical": []
    }

    for source in final_sources:
        source_name = source.get("source", "").lower()
        if any(x in source_name for x in ["pubmed", "europe"]):
            sources_by_type["medical"].append(source)
        elif any(x in source_name for x in ["arxiv", "semantic", "crossref", "core", "doaj"]):
            sources_by_type["scientific"].append(source)
        elif any(x in source_name for x in ["oecd", "world bank"]):
            sources_by_type["statistical"].append(source)

    # Step 5: Pros/Cons Analysis (sync OpenAI call → thread)
    try:
        logger.info("pros_cons_start", sources_count=len(final_sources))
        analysis = await asyncio.to_thread(
            extract_pros_cons,
            argument_en,
            final_sources
        )
        logger.info("pros_cons_end", pros_count=len(analysis.get('pros', [])), cons_count=len(analysis.get('cons', [])))
    except Exception as e:
        logger.error("pros_cons_failed", detail=str(e))
        analysis = {"pros": [], "cons": []}

    enriched_arg = arg_data.copy()
    enriched_arg["categories"] = categories
    enriched_arg["sources"] = sources_by_type
    enriched_arg["analysis"] = analysis

    return enriched_arg


async def research_all_arguments_parallel(
    arguments: List[Dict[str, Any]],
    analysis_mode: str = "simple"
) -> List[Dict[str, Any]]:
    """
    Execute research for all arguments in parallel.

    This is the main entry point for parallel research execution.
    Each argument is processed independently and in parallel.

    Args:
        arguments: List of arguments to research
        analysis_mode: "simple" (fast, abstracts only), "medium" (3 full-texts), "hard" (6 full-texts)

    Returns:
        List of enriched arguments with research results
    """
    if not arguments:
        return []

    logger.info("parallel_research_start", args_count=len(arguments), analysis_mode=str(analysis_mode))

    tasks = [
        research_argument_parallel(
            arg_data["argument"],
            arg_data["argument_en"],
            arg_data,
            analysis_mode
        )
        for arg_data in arguments
    ]

    enriched_arguments = await asyncio.gather(*tasks, return_exceptions=False)

    logger.info("parallel_research_end", enriched_count=len(enriched_arguments))

    return enriched_arguments
