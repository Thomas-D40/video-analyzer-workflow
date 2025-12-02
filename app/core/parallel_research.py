"""
Parallel research execution for arguments.

This module provides async functions to execute research in parallel,
significantly reducing total processing time.
"""
import asyncio
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

from app.agents.research import (
    search_arxiv,
    search_world_bank_data,
    search_pubmed,
    search_semantic_scholar,
    search_crossref,
    search_oecd_data,
)
from app.agents.orchestration import (
    generate_search_queries,
    get_research_strategy,
)
from app.agents.analysis import extract_pros_cons


# Thread pool for blocking I/O operations
executor = ThreadPoolExecutor(max_workers=10)


async def _run_in_executor(func, *args):
    """
    Run a synchronous function in a thread pool executor.

    Args:
        func: Synchronous function to run
        *args: Arguments to pass to the function

    Returns:
        Result from the function
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


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
        print(f"[INFO parallel] Starting {agent_name} search: '{query[:50]}...'")

        # Map agent names to functions
        agent_funcs = {
            "pubmed": lambda: search_pubmed(query, max_results),
            "arxiv": lambda: search_arxiv(query, max_results),
            "semantic_scholar": lambda: search_semantic_scholar(query, max_results),
            "crossref": lambda: search_crossref(query, max_results=3),
            "oecd": lambda: search_oecd_data(query, max_results=3),
            "world_bank": lambda: search_world_bank_data(query),
        }

        if agent_name not in agent_funcs:
            return (agent_name, [], None)

        # Run in thread pool (these are synchronous functions)
        results = await _run_in_executor(agent_funcs[agent_name])

        print(f"[INFO parallel] {agent_name}: {len(results)} results")
        return (agent_name, results, None)

    except Exception as e:
        print(f"[ERROR parallel] {agent_name} error: {e}")
        return (agent_name, [], e)


async def research_argument_parallel(
    argument_text: str,
    argument_en: str,
    arg_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute research for a single argument with parallel API calls.

    Args:
        argument_text: Original argument text
        argument_en: English version for research
        arg_data: Original argument data

    Returns:
        Enriched argument with research results
    """
    # Step 1: Determine research strategy
    try:
        strategy = await _run_in_executor(get_research_strategy, argument_en)
        selected_agents = strategy["agents"]
        categories = strategy["categories"]
        print(f"[INFO parallel] Argument classified: {categories}")
        print(f"[INFO parallel] Agents selected: {selected_agents}")
    except Exception as e:
        print(f"[ERROR parallel] Research strategy error: {e}")
        selected_agents = ["semantic_scholar", "crossref"]
        categories = ["general"]

    # Step 2: Generate optimized queries
    try:
        queries = await _run_in_executor(
            generate_search_queries,
            argument_en,
            selected_agents
        )
    except Exception as e:
        print(f"[ERROR parallel] Query generation error: {e}")
        queries = {}

    # Step 3: Execute all agent searches in parallel
    tasks = []
    for agent_name in selected_agents:
        query = queries.get(agent_name, "")
        if query:
            task = research_single_agent(agent_name, query)
            tasks.append(task)

    # Wait for all searches to complete
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Step 4: Organize results by type
    all_sources = []
    sources_by_type = {
        "scientific": [],
        "medical": [],
        "statistical": []
    }

    for agent_name, agent_results, error in results:
        if error:
            continue

        all_sources.extend(agent_results)

        # Categorize by source type
        if agent_name in ["pubmed"]:
            sources_by_type["medical"].extend(agent_results)
        elif agent_name in ["arxiv", "semantic_scholar", "crossref"]:
            sources_by_type["scientific"].extend(agent_results)
        elif agent_name in ["oecd", "world_bank"]:
            sources_by_type["statistical"].extend(agent_results)

    print(f"[INFO parallel] Argument: {argument_text[:50]}...")
    print(f"[INFO parallel] Total sources: {len(all_sources)}")

    # Step 5: Pros/Cons Analysis
    try:
        analysis = await _run_in_executor(
            extract_pros_cons,
            argument_en,
            all_sources
        )
        print(f"[INFO parallel] Analysis: {len(analysis.get('pros', []))} pros, {len(analysis.get('cons', []))} cons")
    except Exception as e:
        print(f"[ERROR parallel] Pros/cons analysis error: {e}")
        analysis = {"pros": [], "cons": []}

    # Build enriched object
    enriched_arg = arg_data.copy()
    enriched_arg["categories"] = categories
    enriched_arg["sources"] = sources_by_type
    enriched_arg["analysis"] = analysis

    return enriched_arg


async def research_all_arguments_parallel(
    arguments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Execute research for all arguments in parallel.

    This is the main entry point for parallel research execution.
    Each argument is processed independently and in parallel.

    Args:
        arguments: List of arguments to research

    Returns:
        List of enriched arguments with research results

    Example:
        >>> arguments = [
        ...     {"argument": "Coffee causes cancer", "argument_en": "Coffee causes cancer"},
        ...     {"argument": "GDP is rising", "argument_en": "GDP is rising"}
        ... ]
        >>> enriched = await research_all_arguments_parallel(arguments)
        >>> print(f"Processed {len(enriched)} arguments")
    """
    if not arguments:
        return []

    print(f"[INFO parallel] Starting parallel research for {len(arguments)} arguments")

    # Create tasks for each argument
    tasks = [
        research_argument_parallel(
            arg_data["argument"],
            arg_data["argument_en"],
            arg_data
        )
        for arg_data in arguments
    ]

    # Execute all argument research in parallel
    enriched_arguments = await asyncio.gather(*tasks, return_exceptions=False)

    print(f"[INFO parallel] Completed parallel research for {len(enriched_arguments)} arguments")

    return enriched_arguments
