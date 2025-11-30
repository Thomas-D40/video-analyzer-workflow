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
        
    return db.db

async def close_mongo_connection():
    """Ferme la connexion MongoDB."""
    if db.client:
        db.client.close()
        db.client = None
        print("[INFO] Connexion MongoDB fermée")
