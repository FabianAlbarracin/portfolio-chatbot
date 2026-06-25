import secrets
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyHeader

from src.config import CHATBOT_API_KEY
from src.chat import refresh_knowledge

logger = logging.getLogger(__name__)

router = APIRouter()

API_KEY_NAME = "X-API-KEY"
api_key_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_scheme)) -> str:
    if not api_key or not secrets.compare_digest(api_key, CHATBOT_API_KEY):
        raise HTTPException(status_code=403, detail="Acceso denegado: API Key invalida o ausente")
    return api_key


@router.post("/admin/refresh")
async def refresh_endpoint(_: str = Depends(verify_api_key)) -> dict:
    try:
        result = refresh_knowledge()
        return {
            "message": "Base de conocimientos recargada exitosamente (Zero-Downtime).",
            "details": result,
        }
    except Exception as e:
        logger.error("Error critico en Hot-Reload: %s", e)
        raise HTTPException(status_code=500, detail="Fallo al recargar la memoria vectorial.")
