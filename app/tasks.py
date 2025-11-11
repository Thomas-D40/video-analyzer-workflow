"""
Tâche Celery principale pour le traitement des vidéos YouTube.

Cette tâche orchestre la première étape du workflow:
1. Extraction de la transcription
2. Extraction des arguments avec leur stance (affirmatif/conditionnel)
3. Persistance en base de données
"""
import json
from celery import Celery
from sqlmodel import select
from .config import get_settings
from .db import get_session
from .models import VideoAnalysisResult
from .utils.youtube import extract_video_id
from .utils.transcript import extract_transcript
from .agents.arguments import extract_arguments


settings = get_settings()

celery_app = Celery(
    "video_workflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(name="workflow.process_youtube")
def process_youtube(youtube_url: str) -> dict:
    """
    Extrait les arguments d'une vidéo YouTube.
    
    Cette fonction effectue uniquement la première étape du workflow:
    - Extraction de la transcription
    - Extraction des arguments avec leur stance (affirmatif/conditionnel)
    
    Args:
        youtube_url: URL complète de la vidéo YouTube
        
    Returns:
        Dictionnaire avec video_id et arguments extraits
    """
    video_id = extract_video_id(youtube_url) or ""
    
    # Initialisation du statut en base de données
    session = next(get_session())
    try:
        existing = session.exec(
            select(VideoAnalysisResult).where(VideoAnalysisResult.video_id == video_id)
        ).first()
        
        if existing is None:
            existing = VideoAnalysisResult(
                video_id=video_id,
                youtube_url=youtube_url,
                status="processing"
            )
            session.add(existing)
            session.commit()
        else:
            existing.status = "processing"
            session.add(existing)
            session.commit()
    except Exception as e:
        print(f"[{video_id}] Erreur lors de l'initialisation en DB: {e}")
        session.rollback()
    
    try:
        # Étape 1: Extraction de la transcription
        print(f"[{video_id}] Étape 1: Extraction de la transcription...")
        transcript_text = extract_transcript(youtube_url)
        
        if not transcript_text or len(transcript_text.strip()) < 50:
            raise ValueError("Transcription introuvable ou trop courte pour l'analyse")
        
        print(f"[{video_id}] Transcription extraite ({len(transcript_text)} caractères)")
        
        # Étape 2: Extraction des arguments (avec MCP pour réduire les tokens)
        print(f"[{video_id}] Étape 2: Extraction des arguments (avec MCP)...")
        arguments = extract_arguments(transcript_text, video_id=video_id)
        
        if not arguments:
            raise ValueError("Aucun argument extrait de la transcription")
        
        print(f"[{video_id}] {len(arguments)} argument(s) extrait(s)")
        
        # Affichage des arguments extraits pour debug
        for idx, arg in enumerate(arguments, 1):
            arg_text = arg.get("argument", "")
            stance = arg.get("stance", "affirmatif")
            print(f"[{video_id}]   Argument {idx}: {arg_text[:80]}... (stance: {stance})")
        
        # Enregistrement des arguments dans MCP pour utilisation ultérieure
        from .utils.mcp_server import get_mcp_manager
        mcp_manager = get_mcp_manager()
        mcp_manager.register_arguments(video_id, arguments)
        
        # Étape 3: Persistance en base de données
        print(f"[{video_id}] Étape 3: Persistance en base de données...")
        session = next(get_session())
        
        existing = session.exec(
            select(VideoAnalysisResult).where(VideoAnalysisResult.video_id == video_id)
        ).first()
        
        if existing:
            existing.status = "completed"
            existing.arguments_json = json.dumps(arguments, ensure_ascii=False)
            # Les autres champs restent None pour l'instant
            session.add(existing)
            session.commit()
        else:
            # Cas improbable mais on le gère quand même
            record = VideoAnalysisResult(
                video_id=video_id,
                youtube_url=youtube_url,
                status="completed",
                arguments_json=json.dumps(arguments, ensure_ascii=False),
            )
            session.add(record)
            session.commit()
        
        print(f"[{video_id}] Traitement terminé avec succès (MCP activé pour optimisation tokens)")
        
        return {
            "video_id": video_id,
            "arguments": arguments,
        }
        
    except Exception as e:
        # Gestion des erreurs: mise à jour du statut en DB
        print(f"[{video_id}] Erreur lors du traitement: {e}")
        session = next(get_session())
        
        try:
            existing = session.exec(
                select(VideoAnalysisResult).where(VideoAnalysisResult.video_id == video_id)
            ).first()
            
            if existing:
                existing.status = "failed"
                session.add(existing)
                session.commit()
        except Exception as db_error:
            print(f"[{video_id}] Erreur lors de la mise à jour du statut d'erreur: {db_error}")
        
        # Nettoyage des ressources MCP en cas d'erreur
        try:
            from .utils.mcp_server import get_mcp_manager
            mcp_manager = get_mcp_manager()
            mcp_manager.clear_resources(video_id=video_id)
        except Exception:
            pass  # Ignore les erreurs de nettoyage MCP
        
        # Re-lancer l'exception pour que Celery la gère
        raise
