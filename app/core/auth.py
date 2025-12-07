from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from app.config import get_settings
import secrets

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_basic = HTTPBasic()

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


async def verify_admin_password(credentials: HTTPBasicCredentials = Depends(http_basic)):
    """
    Vérifie le mot de passe admin via HTTP Basic Auth.
    Si aucun mot de passe n'est configuré, l'accès est libre (mode dev/local).

    Username: admin
    Password: ADMIN_PASSWORD env var
    """
    settings = get_settings()

    # Si aucun mot de passe n'est configuré, on autorise tout (mode local par défaut)
    if not settings.admin_password:
        return True

    # Verify username
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants admin incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )

    return True
