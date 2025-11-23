from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Vérifie la validité de la clé API fournie dans le header X-API-Key.
    Si aucune clé n'est configurée côté serveur, l'accès est libre (mode dev/local).
    """
    settings = get_settings()
    valid_keys = settings.api_keys_set
    
    # Si aucune clé n'est configurée, on autorise tout (mode local par défaut)
    if not valid_keys:
        return True
        
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante"
        )
        
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API invalide"
        )
        
    return True
