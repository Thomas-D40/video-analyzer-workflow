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
from app.agents.extraction import extract_arguments, structure_to_dict
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
                # Requested mode is available - return in consistent format
                print(f"[INFO] Cache hit for mode '{analysis_mode.value}'")

                # Extract content from cached analysis
                cached_content = requested_analysis.get("content", {})

                # Return in same format as fresh results
                result = {
                    "video_id": video_id,
                    "youtube_url": all_analyses.get("youtube_url", ""),
                    "cached": True,
                    **cached_content  # Spread cached content (includes argument_structure, enriched_thesis_arguments, etc.)
                }

                print(f"[DEBUG] Returning cached analysis for mode '{analysis_mode.value}'")
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

    # Step 3: Extract arguments with language detection (now returns ArgumentStructure)
    language, argument_structure = extract_arguments(transcript_text, video_id=video_id)
    print(f"[INFO workflow] Video language: {language}")
    print(f"[INFO workflow] Found {argument_structure.total_chains} reasoning chains with {argument_structure.total_arguments} total arguments")

    if not argument_structure.reasoning_chains:
        no_args_message = "No arguments found in this video." if language == "en" else "Aucun argument trouvé dans cette vidéo."
        structure_dict = structure_to_dict(argument_structure)
        return {
            "video_id": video_id,
            "youtube_url": youtube_url,
            "language": language,
            "argument_structure": structure_dict,
            "enriched_thesis_arguments": [],
            "report_markdown": no_args_message
        }
    
    # Step 4 & 5: Research and Analysis (PARALLEL EXECUTION)
    # Extract thesis arguments from reasoning forest for research
    # Note: We only research thesis-level arguments (main claims), not sub-arguments/evidence
    thesis_arguments = []
    for chain in argument_structure.reasoning_chains:
        thesis_arg = {
            "argument": chain.thesis.argument,
            "argument_en": chain.thesis.argument_en,
            "stance": chain.thesis.stance,
            "confidence": chain.thesis.confidence,
            "chain_id": chain.chain_id,
            "sub_arguments_count": len(chain.thesis.sub_arguments),
            "counter_arguments_count": len(chain.thesis.counter_arguments)
        }
        thesis_arguments.append(thesis_arg)

    print(f"[INFO workflow] Researching {len(thesis_arguments)} thesis-level arguments")

    # Process thesis arguments in parallel for better performance
    enriched_thesis_arguments = await research_all_arguments_parallel(thesis_arguments, analysis_mode=analysis_mode)
    
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
            for arg in enriched_thesis_arguments
        ]

        aggregation_result = aggregate_results(items_for_aggregation, video_id=video_id)
        aggregated_args_map = {a["argument"]: a for a in aggregation_result.get("arguments", [])}

        final_thesis_arguments = []
        for original_arg in enriched_thesis_arguments:
            arg_text = original_arg["argument"]
            agg_data = aggregated_args_map.get(arg_text, {})
            reliability = agg_data.get("reliability", 0.5)
            original_arg["reliability_score"] = reliability
            final_thesis_arguments.append(original_arg)

    except Exception as e:
        print(f"[ERROR] Aggregation error: {e}")
        final_thesis_arguments = enriched_thesis_arguments

    # Report generation
    # Convert argument structure to dict for JSON serialization
    structure_dict = structure_to_dict(argument_structure)

    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": final_thesis_arguments,
        "arguments_count": len(final_thesis_arguments)
    }

    report_markdown = generate_markdown_report(output_data)

    result = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": final_thesis_arguments,
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

            # Ensure timestamps are serializable
            updated_at = available_data.get("updated_at")
            created_at = available_data.get("created_at")
            updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at
            created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else created_at

            result["cache_info"] = {
                "reason": "new_analysis",
                "message": f"New analysis created in mode '{analysis_mode.value}'",
                "selected_mode": analysis_mode.value,
                "requested_mode": analysis_mode.value,
                "age_days": 0,
                "average_rating": 0.0,
                "rating_count": 0,
                "updated_at": updated_at_str,
                "created_at": created_at_str,
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
                # Requested mode is available - return in consistent format
                await progress_callback("cache", 100, "Using cached analysis")

                # Extract content from cached analysis
                cached_content = requested_analysis.get("content", {})

                # Return in same format as fresh results
                result = {
                    "video_id": video_id,
                    "youtube_url": all_analyses.get("youtube_url", ""),
                    "cached": True,
                    **cached_content  # Spread cached content (includes argument_structure, enriched_thesis_arguments, etc.)
                }

                print(f"[DEBUG] Returning cached analysis for mode '{analysis_mode.value}'")
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

    # Step 3: Extract arguments (now returns ArgumentStructure)
    await progress_callback("arguments", 25, "Extracting arguments from transcript...")
    language, argument_structure = extract_arguments(transcript_text, video_id=video_id)

    if not argument_structure.reasoning_chains:
        await progress_callback("complete", 100, "No arguments found - analysis complete")
        structure_dict = structure_to_dict(argument_structure)
        result = {
            "video_id": video_id,
            "youtube_url": youtube_url,
            "language": language,
            "argument_structure": structure_dict,
            "enriched_thesis_arguments": [],
            "report_markdown": "No substantial arguments found in this video.",
            "analysis_mode": analysis_mode
        }
        await save_analysis(video_id, youtube_url, result, analysis_mode=analysis_mode)
        return result

    # Step 4: Extract thesis arguments from reasoning forest
    thesis_arguments = []
    for chain in argument_structure.reasoning_chains:
        thesis_arg = {
            "argument": chain.thesis.argument,
            "argument_en": chain.thesis.argument_en,
            "stance": chain.thesis.stance,
            "confidence": chain.thesis.confidence,
            "chain_id": chain.chain_id,
            "sub_arguments_count": len(chain.thesis.sub_arguments),
            "counter_arguments_count": len(chain.thesis.counter_arguments)
        }
        thesis_arguments.append(thesis_arg)

    await progress_callback("queries", 35, f"Generating search queries for {len(thesis_arguments)} thesis arguments...")
    arg_count = len(thesis_arguments)

    # Step 5: Research (parallel)
    await progress_callback("research", 45, f"Researching sources for {arg_count} thesis arguments...")
    enriched_thesis_arguments = await research_all_arguments_parallel(
        thesis_arguments, analysis_mode
    )

    # Step 6: Pros/cons analysis
    await progress_callback("analysis", 70, "Analyzing pros and cons from sources...")
    for idx, arg in enumerate(enriched_thesis_arguments):
        percent = 70 + int((idx / len(enriched_thesis_arguments)) * 20)
        await progress_callback("analysis", percent, f"Analyzing argument {idx+1}/{len(enriched_thesis_arguments)}...")

    # Step 7: Aggregation
    await progress_callback("aggregation", 90, "Calculating reliability scores...")
    try:
        items_for_aggregation = [
            {
                "argument": arg["argument"],
                "pros": arg["analysis"].get("pros", []),
                "cons": arg["analysis"].get("cons", []),
                "stance": arg.get("stance", "affirmatif"),
                "sources": arg.get("sources", {})
            }
            for arg in enriched_thesis_arguments
        ]

        aggregation_result = aggregate_results(items_for_aggregation, video_id=video_id)
        aggregated_args_map = {a["argument"]: a for a in aggregation_result.get("arguments", [])}

        final_thesis_arguments = []
        for original_arg in enriched_thesis_arguments:
            arg_text = original_arg["argument"]
            agg_data = aggregated_args_map.get(arg_text, {})
            reliability = agg_data.get("reliability", 0.5)
            original_arg["reliability_score"] = reliability
            final_thesis_arguments.append(original_arg)

    except Exception as e:
        print(f"[ERROR] Aggregation error: {e}")
        final_thesis_arguments = enriched_thesis_arguments

    # Step 8: Report generation
    await progress_callback("report", 95, "Generating final report...")
    # Convert argument structure to dict for JSON serialization
    structure_dict = structure_to_dict(argument_structure)

    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": final_thesis_arguments,
        "arguments_count": len(final_thesis_arguments)
    }

    report_markdown = generate_markdown_report(output_data)

    result = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": final_thesis_arguments,
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

            # Ensure timestamps are serializable
            updated_at = available_data.get("updated_at")
            created_at = available_data.get("created_at")
            updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at
            created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else created_at

            result["cache_info"] = {
                "reason": "new_analysis",
                "message": f"New analysis created in mode '{analysis_mode.value}'",
                "selected_mode": analysis_mode.value,
                "requested_mode": analysis_mode.value,
                "age_days": 0,
                "average_rating": 0.0,
                "rating_count": 0,
                "updated_at": updated_at_str,
                "created_at": created_at_str,
                "available_analyses": available_analyses
            }
    except Exception as e:
        print(f"[ERROR] Database save error: {e}")

    await progress_callback("complete", 100, "Analysis complete!")
    return result
