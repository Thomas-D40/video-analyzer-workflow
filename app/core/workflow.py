"""
Main module for YouTube video analysis business logic.

This module contains the `process_video` function that orchestrates the entire workflow:
- Transcript extraction
- Argument extraction
- Evidence Engine analysis (delegated via HTTP)
- Report generation
"""
import time
from typing import Dict, Any

from app.utils.youtube import extract_video_id
from app.utils.transcript import extract_transcript
from app.agents.extraction import extract_arguments, structure_to_dict
from app.services.evidence_engine import analyze_argument as evidence_engine_analyze
from app.utils.report_formatter import generate_markdown_report
from app.services.storage import save_analysis, get_available_analyses
from app.utils.analysis_metadata import build_available_analyses_metadata
from app.constants import (
    AnalysisMode,
    TRANSCRIPT_MIN_LENGTH
)
from app.logger import get_logger

logger = get_logger(__name__)


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
                logger.info("cache_hit", video_id=video_id, mode=analysis_mode.value)

                # Extract content from cached analysis
                cached_content = requested_analysis.get("content", {})

                # Return in same format as fresh results
                result = {
                    "video_id": video_id,
                    "youtube_url": all_analyses.get("youtube_url", ""),
                    "cached": True,
                    **cached_content  # Spread cached content (includes argument_structure, enriched_thesis_arguments, etc.)
                }

                logger.debug("returning_cached_analysis", video_id=video_id, mode=analysis_mode.value)
                return result
            else:
                # Requested mode not available, need to generate it
                logger.info("cache_miss_mode", video_id=video_id, mode=analysis_mode.value)
        else:
            # Video not in database at all
            logger.info("cache_miss_new", video_id=video_id)

    # Step 2: Extract transcript
    transcript_text = extract_transcript(youtube_url, youtube_cookies=youtube_cookies)
    if not transcript_text or len(transcript_text.strip()) < TRANSCRIPT_MIN_LENGTH:
        raise ValueError("Transcript not found or too short")

    # Step 3: Extract arguments with language detection (returns ArgumentStructure)
    t_args = time.time()
    language, argument_structure = extract_arguments(transcript_text, video_id=video_id)
    logger.info(
        "step_end",
        video_id=video_id,
        step="argument_extraction",
        duration_ms=int((time.time() - t_args) * 1000),
        language=language,
        chains_count=argument_structure.total_chains,
        args_count=argument_structure.total_arguments,
    )

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

    # Step 4: Build thesis argument list from reasoning forest
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

    # Step 5: Delegate per-argument analysis to evidence-engine
    logger.info("step_start", video_id=video_id, step="evidence_engine", thesis_count=len(thesis_arguments))
    t_evidence = time.time()
    enriched_thesis_arguments = []
    for arg in thesis_arguments:
        result = await evidence_engine_analyze(
            argument=arg["argument"],
            argument_en=arg.get("argument_en", arg["argument"]),
            mode=analysis_mode.value,
            language=language,
        )
        # Wrap pros/cons into analysis dict for report_formatter compatibility
        analysis = {
            "pros": result.get("pros", []),
            "cons": result.get("cons", []),
        }
        other = {k: v for k, v in result.items() if k not in ("pros", "cons")}
        enriched_thesis_arguments.append({**arg, "analysis": analysis, **other})

    logger.info(
        "step_end",
        video_id=video_id,
        step="evidence_engine",
        duration_ms=int((time.time() - t_evidence) * 1000),
        enriched_count=len(enriched_thesis_arguments),
    )

    # Step 6: Report generation
    structure_dict = structure_to_dict(argument_structure)

    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": enriched_thesis_arguments,
        "arguments_count": len(enriched_thesis_arguments)
    }

    report_markdown = generate_markdown_report(output_data)

    result = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": enriched_thesis_arguments,
        "report_markdown": report_markdown,
        "analysis_mode": analysis_mode
    }

    # Save to database
    try:
        await save_analysis(video_id, youtube_url, result, analysis_mode=analysis_mode)
        logger.info("analysis_saved", video_id=video_id, mode=analysis_mode.value)

        # After save, fetch available analyses to include in response
        from datetime import datetime
        available_data = await get_available_analyses(video_id)
        if available_data:
            logger.debug("available_analyses_keys", video_id=video_id, keys=list(available_data.get('analyses', {}).keys()))
            available_analyses = build_available_analyses_metadata(available_data)
            logger.debug("available_analyses_built", video_id=video_id, count=len(available_analyses))

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
        logger.error("database_save_failed", video_id=video_id, step="save", detail=str(e))

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
            requested_analysis = all_analyses["analyses"].get(analysis_mode.value)

            if requested_analysis and requested_analysis.get("status") == "completed":
                await progress_callback("cache", 100, "Using cached analysis")

                cached_content = requested_analysis.get("content", {})
                result = {
                    "video_id": video_id,
                    "youtube_url": all_analyses.get("youtube_url", ""),
                    "cached": True,
                    **cached_content
                }

                logger.debug("returning_cached_analysis", video_id=video_id, mode=analysis_mode.value)
                return result
            else:
                await progress_callback("cache", 15, f"Mode '{analysis_mode.value}' not cached, generating...")
        else:
            await progress_callback("cache", 15, "No cache found, starting new analysis...")

    # Step 2: Extract transcript
    await progress_callback("transcript", 15, "Extracting video transcript...")
    transcript_text = extract_transcript(youtube_url, youtube_cookies=youtube_cookies)
    if not transcript_text or len(transcript_text.strip()) < TRANSCRIPT_MIN_LENGTH:
        raise ValueError("Transcript not found or too short")

    # Step 3: Extract arguments (returns ArgumentStructure)
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

    # Step 4: Build thesis argument list from reasoning forest
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

    # Step 5: Delegate per-argument analysis to evidence-engine
    arg_count = len(thesis_arguments)
    await progress_callback("evidence_engine", 35, f"Analyzing {arg_count} thesis arguments via evidence-engine...")
    enriched_thesis_arguments = []
    for idx, arg in enumerate(thesis_arguments):
        percent = 35 + int((idx / arg_count) * 55)
        await progress_callback("evidence_engine", percent, f"Analyzing argument {idx + 1}/{arg_count}...")
        result = await evidence_engine_analyze(
            argument=arg["argument"],
            argument_en=arg.get("argument_en", arg["argument"]),
            mode=analysis_mode.value,
            language=language,
        )
        # Wrap pros/cons into analysis dict for report_formatter compatibility
        analysis = {
            "pros": result.get("pros", []),
            "cons": result.get("cons", []),
        }
        other = {k: v for k, v in result.items() if k not in ("pros", "cons")}
        enriched_thesis_arguments.append({**arg, "analysis": analysis, **other})

    # Step 6: Report generation
    await progress_callback("report", 95, "Generating final report...")
    structure_dict = structure_to_dict(argument_structure)

    output_data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": enriched_thesis_arguments,
        "arguments_count": len(enriched_thesis_arguments)
    }

    report_markdown = generate_markdown_report(output_data)

    result = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "language": language,
        "argument_structure": structure_dict,
        "enriched_thesis_arguments": enriched_thesis_arguments,
        "report_markdown": report_markdown,
        "analysis_mode": analysis_mode
    }

    # Step 7: Save to database
    await progress_callback("save", 98, "Saving to database...")
    try:
        await save_analysis(video_id, youtube_url, result, analysis_mode=analysis_mode)

        from datetime import datetime
        available_data = await get_available_analyses(video_id)
        if available_data:
            logger.debug("available_analyses_keys", video_id=video_id, keys=list(available_data.get('analyses', {}).keys()))
            available_analyses = build_available_analyses_metadata(available_data)
            logger.debug("available_analyses_built", video_id=video_id, count=len(available_analyses))

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
        logger.error("database_save_failed", video_id=video_id, step="save", detail=str(e))

    await progress_callback("complete", 100, "Analysis complete!")
    return result
