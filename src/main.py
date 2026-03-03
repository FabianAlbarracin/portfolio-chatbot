from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Importamos las rutas que acabamos de aislar
from src.api.chat_router import router as chat_router

# Inicialización pura de red
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Portfolio Chatbot API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fabslabs.uk", "https://www.fabslabs.uk", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["X-API-KEY", "Content-Type"],
)

# Inyección de los endpoints
app.include_router(chat_router)