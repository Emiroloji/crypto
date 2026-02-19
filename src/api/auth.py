from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from src.config.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate API Key from header.
    If no API key is set in settings, authentication is disabled (development mode).
    """
    if not settings.api_key:
        return True

    if api_key_header == settings.api_key:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )
