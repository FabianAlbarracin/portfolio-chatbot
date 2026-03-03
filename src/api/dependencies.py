import os
from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-KEY"
# En producción, asegúrate de que CHATBOT_API_KEY esté en tu docker-compose.yml
API_KEY_VALUE = os.getenv("CHATBOT_API_KEY", "dev_key_fallback")

api_key_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_scheme)):
    if not api_key or api_key != API_KEY_VALUE:
        raise HTTPException(status_code=403, detail="Acceso denegado: API Key inválida o ausente")
    return api_key