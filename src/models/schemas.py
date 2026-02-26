from pydantic import BaseModel

class ChatRequest(BaseModel):
    """
    Esquema de validación para las peticiones entrantes del chat.
    Garantiza que el frontend siempre envíe un session_id y una question.
    """
    session_id: str
    question: str