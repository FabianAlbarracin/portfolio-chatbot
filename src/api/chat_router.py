import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from src.models.schemas import ChatRequest
from src.api.dependencies import verify_api_key
from src.core.usage_tracker import UsageTracker
from src.core.orchestrator import ChatbotOrchestrator
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
usage_tracker = UsageTracker(daily_limit=1000)

# Instanciamos el orquestador una sola vez al arrancar la ruta
orchestrator = ChatbotOrchestrator()

@router.post("/chat")
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, chat_req: ChatRequest, _: str = Depends(verify_api_key)):
    # 1. Validación de entrada básica
    if not chat_req.question:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    session_id = chat_req.session_id or str(uuid.uuid4())
    client_ip = request.client.host

    # 2. Restricciones de seguridad globales (7/min ya aplicado por decorador)
    # Límite de caracteres
    if len(chat_req.question) > 500:
        return {"session_id": session_id, "answer": "Tu pregunta es muy extensa. Máximo 500 caracteres."}

    # Límite de uso diario
    if not usage_tracker.check_and_update(client_ip):
        return {"session_id": session_id, "answer": "⚠️ Has alcanzado el límite de consultas diarias."}

    # 3. Procesamiento RAG
    try:
        ia_data = orchestrator.get_response(session_id, chat_req.question)

        # Normalización para asegurar que siempre enviamos 'answer' y 'sources'
        if isinstance(ia_data, dict):
            answer = ia_data.get("answer", "")
            sources = ia_data.get("sources", [])
        else:
            answer = ia_data
            sources = ["Fuentes no disponibles"]

        return {
            "session_id": session_id,
            "answer": answer,
            "sources": sources
        }
    except Exception as e:
        print(f"❌ Error en el motor RAG: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")