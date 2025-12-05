from motor.motor_asyncio import AsyncIOMotorClient
from ..config import get_settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

db = MongoDB()

async def get_database():
    """
    Retourne l'instance de la base de données.
    Initialise la connexion si nécessaire.
    """
    if db.client is None:
        settings = get_settings()
        # Création du client Motor
        db.client = AsyncIOMotorClient(settings.database_url)
        db.db = db.client[settings.mongo_db_name]
        print(f"[INFO] Connecté à MongoDB: {settings.mongo_db_name}")

        # Ensure indexes exist for performance
        await _ensure_indexes()

    return db.db

async def _ensure_indexes():
    """
    Crée les index nécessaires pour les collections.
    """
    if db.db is None:
        return

    # Index composite sur (id, analysis_mode) pour les analyses
    # Permet de stocker plusieurs analyses du même vidéo avec différents modes
    analyses_collection = db.db.analyses
    await analyses_collection.create_index(
        [("id", 1), ("analysis_mode", 1)],
        unique=True,
        name="video_analysis_composite_key"
    )
    print("[INFO] Index MongoDB créés: analyses (id, analysis_mode)")

async def close_mongo_connection():
    """Ferme la connexion MongoDB."""
    if db.client:
        db.client.close()
        db.client = None
        print("[INFO] Connexion MongoDB fermée")
