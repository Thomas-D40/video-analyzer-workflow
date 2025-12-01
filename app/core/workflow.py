"""
Main module for YouTube video analysis business logic.

This module contains the `process_video` function that orchestrates the entire workflow:
- Transcript extraction
- Argument extraction
- Source research
- Pros/cons analysis
- Reliability calculation
- Report generation
"""
import os
from typing import Dict, List, Any

from app.utils.youtube import extract_video_id
from app.utils.transcript import extract_transcript
from app.agents.extraction import extract_arguments
from app.agents.research import (
    generate_search_queries,
    search_arxiv,
    search_world_bank_data,
    search_pubmed,
    search_semantic_scholar,
    search_crossref,
    search_oecd_data,
    get_research_strategy,
)
from app.agents.analysis import extract_pros_cons, aggregate_results
from app.utils.report_formatter import generate_markdown_report


from app.services.storage import save_analysis, get_analysis

async def process_video(youtube_url: str, force_refresh: bool = False, youtube_cookies: str = None) -> Dict[str, Any]:
    """
    Processes a YouTube video and returns the complete analysis.

    Args:
        youtube_url: YouTube video URL

    Returns:
        Dictionary containing:
        - video_id: Video ID
        - youtube_url: Source URL
        - arguments: List of analyzed arguments
        - report_markdown: Markdown-formatted report

    Raises:
        ValueError: If URL is invalid or transcript not found
        Exception: For any other error during processing
    """
    # Step 1: Extract video ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise ValueError("Unable to extract video ID from URL")

    # Step 1.5: Check cache
    if not force_refresh:
        cached_analysis = await get_analysis(video_id)
        if cached_analysis and cached_analysis.status == "completed":
            print(f"[INFO] Cached analysis found for {video_id}")
            result = cached_analysis.content
            # Add cache metadata
            result["cached"] = True
            result["last_updated"] = cached_analysis.updated_at.isoformat()
            return result

    # Step 2: Extract transcript
    transcript_text = extract_transcript(youtube_url, youtube_cookies=youtube_cookies)
    if not transcript_text or len(transcript_text.strip()) < 50:
        raise ValueError("Transcript not found or too short")

    # Step 3: Extract arguments with language detection
    language, arguments = extract_arguments(transcript_text, video_id=video_id)
    print(f"[INFO workflow] Video language: {language}")

    if not arguments:
        no_args_message = "No arguments found in this video." if language == "en" else "Aucun argument trouvé dans cette vidéo."
        return {
            "video_id": video_id,
            "youtube_url": youtube_url,
            "language": language,
            "arguments": [],
            "report_markdown": no_args_message
        }
    
    # Step 4 & 5: Research and Analysis (with specialized agents)
    enriched_arguments = []

    for arg_data in arguments:
        argument_text = arg_data["argument"]  # Original language
        argument_en = arg_data["argument_en"]  # English for research

        # Step 4.1: Determine research strategy based on domain
        # Use English version for classification (more accurate)
        try:
            strategy = get_research_strategy(argument_en)
            selected_agents = strategy["agents"]
            categories = strategy["categories"]
            print(f"[INFO workflow] Argument classified: {categories}")
            print(f"[INFO workflow] Agents selected: {selected_agents}")
        except Exception as e:
            print(f"[ERROR workflow] Research strategy error: {e}")
            selected_agents = ["semantic_scholar", "crossref"]
            categories = ["general"]

        # Step 4.2: Generate optimized queries for selected agents
        # Use English version for query generation (all APIs work in English)
        queries = {}
        try:
            queries = generate_search_queries(argument_en, agents=selected_agents)
        except Exception as e:
            print(f"[ERROR workflow] Query generation error: {e}")

        # Initialize source collections
        all_sources = []
        sources_by_type = {
            "scientific": [],
            "medical": [],
            "statistical": []
        }

        # Step 4.3: Execute searches with appropriate agents
        # Note: DuckDuckGo web search removed - using only academic and official sources for better quality

        # PubMed (medicine/health)
        if "pubmed" in selected_agents and queries.get("pubmed"):
            try:
                print(f"[INFO workflow] PubMed search: '{queries['pubmed'][:50]}...'")
                pubmed_articles = search_pubmed(queries["pubmed"], max_results=5)
                sources_by_type["medical"].extend(pubmed_articles)
                all_sources.extend(pubmed_articles)
                print(f"[INFO workflow] PubMed: {len(pubmed_articles)} articles")
            except Exception as e:
                print(f"[ERROR workflow] PubMed search error: {e}")

        # ArXiv (exact sciences)
        if "arxiv" in selected_agents and queries.get("arxiv"):
            try:
                print(f"[INFO workflow] ArXiv search: '{queries['arxiv'][:50]}...'")
                arxiv_articles = search_arxiv(queries["arxiv"], max_results=5)
                sources_by_type["scientific"].extend(arxiv_articles)
                all_sources.extend(arxiv_articles)
                print(f"[INFO workflow] ArXiv: {len(arxiv_articles)} articles")
            except Exception as e:
                print(f"[ERROR workflow] ArXiv search error: {e}")

        # Semantic Scholar (all disciplines)
        if "semantic_scholar" in selected_agents and queries.get("semantic_scholar"):
            try:
                print(f"[INFO workflow] Semantic Scholar search: '{queries['semantic_scholar'][:50]}...'")
                ss_articles = search_semantic_scholar(queries["semantic_scholar"], max_results=5)
                sources_by_type["scientific"].extend(ss_articles)
                all_sources.extend(ss_articles)
                print(f"[INFO workflow] Semantic Scholar: {len(ss_articles)} articles")
            except Exception as e:
                print(f"[ERROR workflow] Semantic Scholar search error: {e}")

        # CrossRef (academic metadata)
        if "crossref" in selected_agents and queries.get("crossref"):
            try:
                print(f"[INFO workflow] CrossRef search: '{queries['crossref'][:50]}...'")
                crossref_articles = search_crossref(queries["crossref"], max_results=3)
                sources_by_type["scientific"].extend(crossref_articles)
                all_sources.extend(crossref_articles)
                print(f"[INFO workflow] CrossRef: {len(crossref_articles)} articles")
            except Exception as e:
                print(f"[ERROR workflow] CrossRef search error: {e}")

        # OECD (economic/social statistics)
        if "oecd" in selected_agents and queries.get("oecd"):
            try:
                print(f"[INFO workflow] OECD search: '{queries['oecd'][:50]}...'")
                oecd_data = search_oecd_data(queries["oecd"], max_results=3)
                sources_by_type["statistical"].extend(oecd_data)
                all_sources.extend(oecd_data)
                print(f"[INFO workflow] OECD: {len(oecd_data)} indicators")
            except Exception as e:
                print(f"[ERROR workflow] OECD search error: {e}")

        # World Bank (development indicators)
        if "world_bank" in selected_agents and queries.get("world_bank"):
            try:
                print(f"[INFO workflow] World Bank search: '{queries['world_bank'][:50]}...'")
                wb_data = search_world_bank_data(queries["world_bank"])
                sources_by_type["statistical"].extend(wb_data)
                all_sources.extend(wb_data)
                print(f"[INFO workflow] World Bank: {len(wb_data)} indicators")
            except Exception as e:
                print(f"[ERROR workflow] World Bank search error: {e}")

        # Step 4.4: Pros/Cons Analysis
        # Use English version for analysis (sources are in English)
        print(f"[INFO workflow] Argument: {argument_text[:50]}...")
        print(f"[INFO workflow] Total sources: {len(all_sources)}")

        try:
            analysis = extract_pros_cons(argument_en, all_sources)
            print(f"[INFO workflow] Analysis: {len(analysis.get('pros', []))} pros, {len(analysis.get('cons', []))} cons")
        except Exception as e:
            print(f"[ERROR workflow] Pros/cons analysis error: {e}")
            analysis = {"pros": [], "cons": []}

        # Build enriched object
        enriched_arg = arg_data.copy()
        enriched_arg["categories"] = categories
        enriched_arg["sources"] = sources_by_type
        enriched_arg["analysis"] = analysis
        enriched_arguments.append(enriched_arg)
    
    # Step 6: Reliability calculation
    try:
        items_for_aggregation = [
            {
                "argument": arg["argument"],
                "pros": arg["analysis"].get("pros", []),
                "cons": arg["analysis"].get("cons", []),
                "stance": arg.get("stance", "affirmatif"),
                "sources": arg.get("sources", {})  # Add real sources
            }
            for arg in enriched_arguments
        ]
        
        aggregation_result = aggregate_results(items_for_aggregation, video_id=video_id)
        aggregated_args_map = {a["argument"]: a for a in aggregation_result.get("arguments", [])}
        
        final_arguments = []
        for original_arg in enriched_arguments:
            arg_text = original_arg["argument"]
            agg_data = aggregated_args_map.get(arg_text, {})
            reliability = agg_data.get("reliability", 0.5)
            original_arg["reliability_score"] = reliability
            final_arguments.append(original_arg)
        
        arguments = final_arguments
    except Exception:
        arguments = enriched_arguments

    # Report generation
    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "arguments_count": len(arguments),
        "arguments": arguments
    }

    report_markdown = generate_markdown_report(output_data)

    result = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "arguments": arguments,
        "report_markdown": report_markdown
    }

    # Save to database
    try:
        await save_analysis(video_id, youtube_url, result)
        print(f"[INFO] Analysis saved for {video_id}")
    except Exception as e:
        print(f"[ERROR] Database save error: {e}")

    return result
