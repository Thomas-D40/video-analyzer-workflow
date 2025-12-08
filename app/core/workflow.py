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


from app.services.storage import save_analysis, select_best_cached_analysis, get_available_analyses
from app.constants import (
    AnalysisMode,
    CACHE_MAX_AGE_DAYS,
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

    # Step 1.5: Smart cache selection
    if not force_refresh:
        cache_result = await select_best_cached_analysis(
            video_id,
            requested_mode=analysis_mode,
            max_age_days=CACHE_MAX_AGE_DAYS
        )

        cached_content, selected_mode, cache_metadata = cache_result

        if cached_content and selected_mode:
            # Cache hit! Return cached analysis with metadata
            print(f"[INFO] {cache_metadata['message']}")
            result = cached_content.copy()  # Make a copy to avoid mutating cached data

            # Add comprehensive cache metadata (including ratings and dates)
            result["cached"] = True
            result["updated_at"] = cache_metadata.get("updated_at")
            result["created_at"] = cache_metadata.get("created_at")
            available_modes = cache_metadata.get("available_modes", [])
            print(f"[DEBUG] Cache hit - available_modes from metadata: {available_modes}")
            result["cache_info"] = {
                "reason": cache_metadata["reason"],
                "message": cache_metadata["message"],
                "selected_mode": selected_mode.value,
                "requested_mode": analysis_mode.value,
                "age_days": cache_metadata.get("age_days", 0),
                "average_rating": cache_metadata.get("rating", 0.0),
                "rating_count": cache_metadata.get("rating_count", 0),
                "updated_at": cache_metadata.get("updated_at"),
                "created_at": cache_metadata.get("created_at"),
                "available_analyses": available_modes
            }

            return result
        else:
            # No suitable cache, proceed with new analysis
            print(f"[INFO] {cache_metadata['message']}")
            if cache_metadata.get("available_modes"):
                print(f"[INFO] Available modes: {cache_metadata['available_modes']}")
            print(f"[INFO] Starting new analysis in mode '{analysis_mode.value}'")

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
        from app.constants import AnalysisStatus
        available_data = await get_available_analyses(video_id)
        if available_data:
            print(f"[DEBUG] available_data.analyses keys: {available_data.get('analyses', {}).keys()}")
            # Build available_analyses array with metadata
            available_analyses = []
            for mode_str, analysis_data in available_data.get("analyses", {}).items():
                if analysis_data:
                    status = analysis_data.get("status")
                    print(f"[DEBUG] Mode {mode_str}: status={status}, type={type(status)}")
                    # Compare with both string and enum (for compatibility)
                    if status == "completed" or status == AnalysisStatus.COMPLETED or status == AnalysisStatus.COMPLETED.value:
                        updated_at = analysis_data.get("updated_at")
                        if updated_at:
                            age_days = (datetime.utcnow() - datetime.fromisoformat(updated_at.replace('Z', '+00:00'))).days
                        else:
                            age_days = 0

                        available_analyses.append({
                            "mode": mode_str,
                            "age_days": age_days,
                            "updated_at": updated_at,
                            "average_rating": analysis_data.get("average_rating", 0.0),
                            "rating_count": analysis_data.get("rating_count", 0)
                        })
                        print(f"[DEBUG] Added mode {mode_str} to available_analyses")

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
        cache_result = await select_best_cached_analysis(
            video_id,
            requested_mode=analysis_mode,
            max_age_days=CACHE_MAX_AGE_DAYS
        )

        cached_content, selected_mode, cache_metadata = cache_result

        if cached_content and selected_mode:
            await progress_callback("cache", 100, "Using cached analysis")
            result = cached_content.copy()
            result["cached"] = True
            result["updated_at"] = cache_metadata.get("updated_at")
            result["created_at"] = cache_metadata.get("created_at")
            available_modes = cache_metadata.get("available_modes", [])
            print(f"[DEBUG] Cache hit - available_modes from metadata: {available_modes}")
            result["cache_info"] = {
                "reason": cache_metadata["reason"],
                "message": cache_metadata["message"],
                "selected_mode": selected_mode.value,
                "requested_mode": analysis_mode.value,
                "age_days": cache_metadata.get("age_days", 0),
                "average_rating": cache_metadata.get("rating", 0.0),
                "rating_count": cache_metadata.get("rating_count", 0),
                "updated_at": cache_metadata.get("updated_at"),
                "created_at": cache_metadata.get("created_at"),
                "available_analyses": available_modes
            }
            return result

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
        from app.constants import AnalysisStatus
        available_data = await get_available_analyses(video_id)
        if available_data:
            print(f"[DEBUG] available_data.analyses keys: {available_data.get('analyses', {}).keys()}")
            # Build available_analyses array with metadata
            available_analyses = []
            for mode_str, analysis_data in available_data.get("analyses", {}).items():
                if analysis_data:
                    status = analysis_data.get("status")
                    print(f"[DEBUG] Mode {mode_str}: status={status}, type={type(status)}")
                    # Compare with both string and enum (for compatibility)
                    if status == "completed" or status == AnalysisStatus.COMPLETED or status == AnalysisStatus.COMPLETED.value:
                        updated_at = analysis_data.get("updated_at")
                        if updated_at:
                            age_days = (datetime.utcnow() - datetime.fromisoformat(updated_at.replace('Z', '+00:00'))).days
                        else:
                            age_days = 0

                        available_analyses.append({
                            "mode": mode_str,
                            "age_days": age_days,
                            "updated_at": updated_at,
                            "average_rating": analysis_data.get("average_rating", 0.0),
                            "rating_count": analysis_data.get("rating_count", 0)
                        })
                        print(f"[DEBUG] Added mode {mode_str} to available_analyses")

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
