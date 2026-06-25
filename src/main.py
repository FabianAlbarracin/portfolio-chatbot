import logging
import httpx

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config import ALLOWED_ORIGINS, LOG_LEVEL
from src.chat import router as chat_router
from src.admin import router as admin_router

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="[%(levelname)s] %(asctime)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Portfolio Chatbot API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["X-API-KEY", "Content-Type"],
)


@app.get("/health", status_code=200)
async def health_check() -> dict:
    import os
    import sqlite3
    from src.config import CHROMA_PERSIST_DIR

    chromadb_status = "error"
    litellm_status = "error"

    db_path = os.path.join(CHROMA_PERSIST_DIR, "chroma.sqlite3")
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1 FROM collections LIMIT 1")
            conn.close()
            chromadb_status = "ok"
    except Exception as e:
        logger.warning("Healthcheck ChromaDB fallido: %s", e)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://litellm:4000/health")
            litellm_status = "ok" if resp.status_code < 500 else "error"
    except Exception as e:
        logger.warning("Healthcheck LiteLLM fallido: %s", e)

    overall = "healthy" if chromadb_status == "ok" and litellm_status == "ok" else "degraded"

    return {
        "status": overall,
        "checks": {
            "chromadb": chromadb_status,
            "litellm": litellm_status,
        },
    }


app.include_router(chat_router)
app.include_router(admin_router)
