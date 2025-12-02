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
from app.agents.analysis import extract_pros_cons, aggregate_results
from app.utils.report_formatter import generate_markdown_report
from app.core.parallel_research import research_all_arguments_parallel


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
    
    # Step 4 & 5: Research and Analysis (PARALLEL EXECUTION)
    # Process all arguments in parallel for better performance
    enriched_arguments = await research_all_arguments_parallel(arguments)
    
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
