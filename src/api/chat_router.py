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
usage_tracker = UsageTracker(daily_limit=40)

# Instanciamos el orquestador una sola vez al arrancar la ruta
orchestrator = ChatbotOrchestrator()

@router.post("/chat")
@limiter.limit("7/minute")
async def chat_endpoint(request: Request, chat_req: ChatRequest, _: str = Depends(verify_api_key)):
    if not chat_req.question:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    client_ip = request.client.host
    if not usage_tracker.check_and_update(client_ip):
        return {"session_id": chat_req.session_id, "answer": "⚠️ Has alcanzado el límite de consultas diarias."}

    session_id = chat_req.session_id or str(uuid.uuid4())

    if len(chat_req.question) > 500:
            return {"session_id": session_id, "answer": "Tu pregunta es muy extensa. Máximo 500 caracteres."}

    try:
        # Delegamos toda la carga de IA al Orquestador
        answer = orchestrator.get_response(session_id, chat_req.question)
        return {"session_id": session_id, "answer": answer}
    except Exception as e:
        print(f"❌ Error en el motor RAG: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor procesando la consulta.")