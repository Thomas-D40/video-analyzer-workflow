import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select
from .schemas import AnalyzeRequest, AnalyzeResponse
from .db import init_db, get_session
from .models import VideoAnalysisResult
from .utils.youtube import extract_video_id
from .tasks import celery_app

app = FastAPI(title="Video Analyzer Workflow")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, session=Depends(get_session)) -> AnalyzeResponse:
    """
    Analyse une vidéo YouTube ou retourne les résultats existants.
    
    Vérifie d'abord si l'analyse a déjà été effectuée pour éviter
    de relancer inutilement le traitement (économie de tokens/énergie).
    """
    video_id = extract_video_id(str(req.youtube_url))
    if not video_id:
        raise HTTPException(status_code=400, detail="URL YouTube invalide")

    # Vérification si l'analyse existe déjà en base de données
    existing = session.exec(
        select(VideoAnalysisResult).where(VideoAnalysisResult.video_id == video_id)
    ).first()

    if existing:
        # Si l'analyse est terminée et contient des arguments, on retourne directement
        if existing.status == "completed" and existing.arguments_json:
            result = {}
            result["arguments"] = json.loads(existing.arguments_json)
            
            return AnalyzeResponse(
                video_id=video_id,
                status=existing.status,
                result=result,
            )
        
        # Si l'analyse est en cours, on retourne le statut sans relancer
        if existing.status == "processing":
            return AnalyzeResponse(
                video_id=video_id,
                status=existing.status,
                result=None,
            )
        
        # Si l'analyse a échoué ou est incomplète, on peut relancer
        # (ou retourner l'erreur selon le besoin)
        if existing.status == "failed":
            # Option: relancer automatiquement ou retourner l'erreur
            # Pour l'instant, on relance pour permettre une nouvelle tentative
            pass

    # Aucun résultat trouvé ou résultat incomplet/échec: on enqueue la tâche
    celery_app.send_task("workflow.process_youtube", args=[str(req.youtube_url)])

    return AnalyzeResponse(video_id=video_id, status="queued", result=None)
