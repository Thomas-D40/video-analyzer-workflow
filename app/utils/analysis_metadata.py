"""
Utility functions for building analysis metadata.
"""
from datetime import datetime
from typing import Dict, List, Any


def build_available_analyses_metadata(available_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Construit la liste des métadonnées d'analyses disponibles.

    Args:
        available_data: Données brutes des analyses disponibles

    Returns:
        Liste des métadonnées formatées pour chaque analyse
    """
    from app.constants import AnalysisStatus

    available_analyses = []

    for mode_str, analysis_data in available_data.get("analyses", {}).items():
        if not analysis_data:
            continue

        status = analysis_data.get("status")
        status_value = status.value if hasattr(status, 'value') else status

        if status_value == "completed":
            updated_at = analysis_data.get("updated_at")
            created_at = analysis_data.get("created_at")
            age_days = 0

            # Handle both string and datetime objects for updated_at
            if updated_at:
                if isinstance(updated_at, str):
                    try:
                        dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        age_days = (datetime.utcnow() - dt).days
                    except Exception as e:
                        print(f"[WARN] Could not parse date {updated_at}: {e}")
                elif isinstance(updated_at, datetime):
                    age_days = (datetime.utcnow() - updated_at).days

            # Ensure timestamps are strings for JSON serialization
            updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at
            created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else created_at

            # Get arguments count
            content = analysis_data.get("content", {})
            arguments_count = len(content.get("arguments", [])) if content else 0

            available_analyses.append({
                "analysis_mode": mode_str,
                "age_days": age_days,
                "created_at": created_at_str or updated_at_str,
                "updated_at": updated_at_str,
                "average_rating": analysis_data.get("average_rating", 0.0),
                "rating_count": analysis_data.get("rating_count", 0),
                "arguments_count": arguments_count,
                "status": status_value
            })

    return available_analyses
