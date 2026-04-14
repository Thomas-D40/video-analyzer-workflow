from motor.motor_asyncio import AsyncIOMotorClient
from ..config import get_settings
from ..logger import get_logger

logger = get_logger(__name__)

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
        logger.info("mongo_connected", db_name=settings.mongo_db_name)

        # Ensure indexes exist for performance
        await _ensure_indexes()

    return db.db

async def _ensure_indexes():
    """
    Crée les index nécessaires pour les collections.
    """
    if db.db is None:
        return

    # Index sur _id pour les analyses vidéo (créé automatiquement par MongoDB)
    # Chaque document représente une vidéo avec plusieurs modes d'analyse imbriqués
    video_analyses_collection = db.db.video_analyses

    # Index sur youtube_url pour recherche rapide
    await video_analyses_collection.create_index(
        [("youtube_url", 1)],
        name="youtube_url_index"
    )

    # Index sur updated_at pour tri chronologique
    await video_analyses_collection.create_index(
        [("updated_at", -1)],
        name="updated_at_index"
    )

    logger.info("mongo_indexes_created", collection="video_analyses", fields="youtube_url, updated_at")

async def close_mongo_connection():
    """Ferme la connexion MongoDB."""
    if db.client:
        db.client.close()
        db.client = None
        logger.info("mongo_connection_closed")
