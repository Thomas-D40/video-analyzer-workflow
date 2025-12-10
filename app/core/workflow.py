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
from app.agents.analysis import extract_pros_cons, aggregate_results
from app.utils.report_formatter import generate_markdown_report
from app.core.parallel_research import research_all_arguments_parallel


from app.services.storage import save_analysis, get_available_analyses
from app.utils.analysis_metadata import build_available_analyses_metadata
from app.constants import (
    AnalysisMode,
    TRANSCRIPT_MIN_LENGTH
)

async def process_video(
    youtube_url: str,
    force_refresh: bool = False,
    youtube_cookies: str = None,
    analysis_mode: AnalysisMode = AnalysisMode.SIMPLE
) -> Dict[str, Any]:
    """
    Processes a YouTube video and returns the complete analysis.

    Args:
        youtube_url: YouTube video URL
        force_refresh: Force re-analysis even if cached
        youtube_cookies: Cookies for age-restricted videos
        analysis_mode: Analysis mode (see AnalysisMode enum)

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
        all_analyses = await get_available_analyses(video_id)

        if all_analyses and all_analyses.get("analyses"):
            # Video exists in database
            requested_analysis = all_analyses["analyses"].get(analysis_mode.value)

            if requested_analysis and requested_analysis.get("status") == "completed":
                # Requested mode is available - return all analyses
                print(f"[INFO] Cache hit for mode '{analysis_mode.value}'")
                result = all_analyses.copy()
                result["cached"] = True
                print(f"[DEBUG] Returning all analyses: {list(result['analyses'].keys())}")
                return result
            else:
                # Requested mode not available, need to generate it
                print(f"[INFO] Mode '{analysis_mode.value}' not found in cache, generating new analysis")
        else:
            # Video not in database at all
            print(f"[INFO] No cache found for video {video_id}, starting new analysis")

    # Step 2: Extract transcript
    transcript_text = extract_transcript(youtube_url, youtube_cookies=youtube_cookies)
    if not transcript_text or len(transcript_text.strip()) < TRANSCRIPT_MIN_LENGTH:
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
    
    # Step 4 & 5: Research and Analysis (PARALLEL EXECUTION)
    # Process all arguments in parallel for better performance
    enriched_arguments = await research_all_arguments_parallel(arguments, analysis_mode=analysis_mode)
    
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
        "report_markdown": report_markdown,
        "analysis_mode": analysis_mode
    }

    # Save to database
    try:
        await save_analysis(video_id, youtube_url, result, analysis_mode=analysis_mode)
        print(f"[INFO] Analysis saved for {video_id} (mode: {analysis_mode})")

        # After save, fetch available analyses to include in response
        from datetime import datetime
        available_data = await get_available_analyses(video_id)
        if available_data:
            print(f"[DEBUG] available_data.analyses keys: {available_data.get('analyses', {}).keys()}")
            # Build available_analyses array with metadata
            available_analyses = build_available_analyses_metadata(available_data)

            # Add cache_info to result
            print(f"[DEBUG] Final available_analyses count: {len(available_analyses)}")
            print(f"[DEBUG] Final available_analyses: {available_analyses}")
            result["cache_info"] = {
                "reason": "new_analysis",
                "message": f"New analysis created in mode '{analysis_mode.value}'",
                "selected_mode": analysis_mode.value,
                "requested_mode": analysis_mode.value,
                "age_days": 0,
                "average_rating": 0.0,
                "rating_count": 0,
                "updated_at": available_data.get("updated_at"),
                "created_at": available_data.get("created_at"),
                "available_analyses": available_analyses
            }
    except Exception as e:
        print(f"[ERROR] Database save error: {e}")

    return result


async def process_video_with_progress(
    youtube_url: str,
    progress_callback,
    force_refresh: bool = False,
    youtube_cookies: str = None,
    analysis_mode: AnalysisMode = AnalysisMode.SIMPLE
) -> Dict[str, Any]:
    """
    Process video with progress tracking via callback.
    
    Progress callback is called with: (step_name: str, percent: int, message: str)
    """
    # Step 1: Extract video ID
    await progress_callback("init", 5, "Extracting video ID...")
    video_id = extract_video_id(youtube_url)
    if not video_id:
        raise ValueError("Unable to extract video ID from URL")

    # Step 1.5: Check cache
    if not force_refresh:
        await progress_callback("cache", 10, "Checking for cached analysis...")
        all_analyses = await get_available_analyses(video_id)

        if all_analyses and all_analyses.get("analyses"):
            # Video exists in database
            requested_analysis = all_analyses["analyses"].get(analysis_mode.value)

            if requested_analysis and requested_analysis.get("status") == "completed":
                # Requested mode is available - return all analyses
                await progress_callback("cache", 100, "Using cached analysis")
                result = all_analyses.copy()
                result["cached"] = True
                print(f"[DEBUG] Returning all analyses: {list(result['analyses'].keys())}")
                return result
            else:
                # Requested mode not available, need to generate it
                await progress_callback("cache", 15, f"Mode '{analysis_mode.value}' not cached, generating...")
        else:
            # Video not in database at all
            await progress_callback("cache", 15, "No cache found, starting new analysis...")

    # Step 2: Extract transcript
    await progress_callback("transcript", 15, "Extracting video transcript...")
    transcript_text = extract_transcript(youtube_url, youtube_cookies=youtube_cookies)
    if not transcript_text or len(transcript_text.strip()) < TRANSCRIPT_MIN_LENGTH:
        raise ValueError("Transcript not found or too short")

    # Step 3: Extract arguments
    await progress_callback("arguments", 25, "Extracting arguments from transcript...")
    language, arguments = extract_arguments(transcript_text, video_id=video_id)

    if not arguments:
        await progress_callback("complete", 100, "No arguments found - analysis complete")
        result = {
            "video_id": video_id,
            "youtube_url": youtube_url,
            "language": language,
            "arguments": [],
            "report_markdown": "No substantial arguments found in this video.",
            "analysis_mode": analysis_mode
        }
        await save_analysis(video_id, youtube_url, result, analysis_mode=analysis_mode)
        return result

    # Step 4: Generate search queries
    await progress_callback("queries", 35, f"Generating search queries for {len(arguments)} arguments...")
    arg_count = len(arguments)
    
    # Step 5: Research (parallel)
    await progress_callback("research", 45, f"Researching sources for {arg_count} arguments...")
    enriched_arguments = await research_all_arguments_parallel(
        arguments, analysis_mode
    )
    
    # Step 6: Pros/cons analysis
    await progress_callback("analysis", 70, "Analyzing pros and cons from sources...")
    for idx, arg in enumerate(enriched_arguments):
        percent = 70 + int((idx / len(enriched_arguments)) * 20)
        await progress_callback("analysis", percent, f"Analyzing argument {idx+1}/{len(enriched_arguments)}...")
    
    # Step 7: Aggregation
    await progress_callback("aggregation", 90, "Calculating reliability scores...")
    try:
        aggregated_args_map = aggregate_results(enriched_arguments)
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

    # Step 8: Report generation
    await progress_callback("report", 95, "Generating final report...")
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
        "report_markdown": report_markdown,
        "analysis_mode": analysis_mode
    }

    # Step 9: Save to database
    await progress_callback("save", 98, "Saving to database...")
    try:
        await save_analysis(video_id, youtube_url, result, analysis_mode=analysis_mode)

        # After save, fetch available analyses to include in response
        from datetime import datetime
        available_data = await get_available_analyses(video_id)
        if available_data:
            print(f"[DEBUG] available_data.analyses keys: {available_data.get('analyses', {}).keys()}")
            # Build available_analyses array with metadata
            available_analyses = build_available_analyses_metadata(available_data)

            # Add cache_info to result
            print(f"[DEBUG] Final available_analyses count: {len(available_analyses)}")
            print(f"[DEBUG] Final available_analyses: {available_analyses}")
            result["cache_info"] = {
                "reason": "new_analysis",
                "message": f"New analysis created in mode '{analysis_mode.value}'",
                "selected_mode": analysis_mode.value,
                "requested_mode": analysis_mode.value,
                "age_days": 0,
                "average_rating": 0.0,
                "rating_count": 0,
                "updated_at": available_data.get("updated_at"),
                "created_at": available_data.get("created_at"),
                "available_analyses": available_analyses
            }
    except Exception as e:
        print(f"[ERROR] Database save error: {e}")

    await progress_callback("complete", 100, "Analysis complete!")
    return result
