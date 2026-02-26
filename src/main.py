from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

# Importaciones locales (Arquitectura Limpia)
from src.llm_engine import ChatbotRAG
from src.models.schemas import ChatRequest

# Cargar variables de entorno
load_dotenv()

app = FastAPI()
bot = ChatbotRAG()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, cambia "*" por "https://tu-dominio.com"
    allow_credentials=True,
    allow_methods=["*"],  # Permite POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "running"}

@app.post("/chat")
def chat(req: ChatRequest):
    if not os.getenv("GROQ_API_KEY"):
        return {"error": "GROQ_API_KEY not configured"}

    response = bot.get_response(req.session_id, req.question)
    return {"answer": response}