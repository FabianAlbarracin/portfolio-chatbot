import os
import uuid
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader  # Nombre correcto de la clase
from pydantic import BaseModel

# Componentes internos
from src.llm_engine import ChatbotRAG
from src.core.usage_tracker import UsageTracker

# Seguridad: Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- 1. CONFIGURACIÓN DE SEGURIDAD ---

# Portero 1: Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Portero 2: Cuota Diaria (Ajusta a 50 después de probar)
usage_tracker = UsageTracker(daily_limit=40)

# Portero 3: API Key (X-API-KEY)
API_KEY_NAME = "X-API-KEY"
API_KEY_VALUE = os.getenv("CHATBOT_API_KEY", "dev_key_fallback")

# Usamos APIKeyHeader para definir el esquema de seguridad
api_key_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Corregimos el acceso a la variable usando un parámetro por defecto
async def verify_api_key(api_key: str = Depends(api_key_scheme), expected_key: str = API_KEY_VALUE):
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Acceso denegado: API Key inválida")
    return api_key

# --- 2. INICIALIZACIÓN ---

app = FastAPI(title="Portfolio Chatbot API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

chatbot = ChatbotRAG()

class ChatRequest(BaseModel):
    session_id: str = None
    question: str

# --- 3. ENDPOINT ---

@app.post("/chat")
@limiter.limit("7/minute")
async def chat_endpoint(
    request: Request,
    chat_req: ChatRequest,
    _ : str = Depends(verify_api_key) # <--- EL FILTRO DE LLAVE
):
    # 1. Validación básica
    if not chat_req.question:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    # 2. Obtener IP del cliente
    client_ip = request.client.host

    # 3. Capa 2: Bloqueo de Cuota Diaria
    if not usage_tracker.check_and_update(client_ip):
        return {
            "session_id": chat_req.session_id,
            "answer": "⚠️ Has alcanzado el límite de consultas diarias permitidas. ¡Te espero mañana!"
        }

    # 4. Asignar o crear ID de sesión
    session_id = chat_req.session_id or str(uuid.uuid4())

    try:
        # 5. Capa 3: Límite de Longitud
        if len(chat_req.question) > 500:
            return {
                "session_id": session_id,
                "answer": "Tu pregunta es muy extensa. Por favor, intenta resumirla en menos de 500 caracteres."
            }

        # 6. Respuesta del Motor RAG
        answer = chatbot.get_response(session_id, chat_req.question)
        return {"session_id": session_id, "answer": answer}

    except Exception as e:
        print(f"❌ Error en el endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")