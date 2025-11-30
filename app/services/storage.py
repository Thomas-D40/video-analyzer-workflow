from datetime import datetime
from typing import Optional, List, Dict, Any
from ..db.mongo import get_database
from ..models.analysis import VideoAnalysis

async def save_analysis(video_id: str, youtube_url: str, content: Dict[str, Any]) -> VideoAnalysis:
    """
    Sauvegarde ou met à jour une analyse dans la base de données.
    """
    db = await get_database()
    collection = db.analyses
    
    now = datetime.utcnow()
    
    analysis_data = {
        "id": video_id,
        "youtube_url": youtube_url,
        "updated_at": now,
        "status": "completed",
        "content": content
    }
    
    # Upsert: Si l'ID existe, on met à jour, sinon on crée
    # On utilise $set pour mettre à jour les champs, et $setOnInsert pour created_at
    await collection.update_one(
        {"id": video_id},
        {
            "$set": analysis_data,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )
    
    # On récupère le document complet pour le retourner
    doc = await collection.find_one({"id": video_id})
    return VideoAnalysis(**doc)

async def get_analysis(video_id: str) -> Optional[VideoAnalysis]:
    """
    Récupère une analyse par son ID vidéo.
    """
    db = await get_database()
    collection = db.analyses
    
    doc = await collection.find_one({"id": video_id})
    if doc:
        return VideoAnalysis(**doc)
    return None

async def list_analyses(limit: int = 10, skip: int = 0) -> List[VideoAnalysis]:
    """
    Liste les analyses récentes.
    """
    db = await get_database()
    collection = db.analyses
    
    cursor = collection.find().sort("updated_at", -1).skip(skip).limit(limit)
    
    analyses = []
    async for doc in cursor:
        analyses.append(VideoAnalysis(**doc))
        
    return analyses
