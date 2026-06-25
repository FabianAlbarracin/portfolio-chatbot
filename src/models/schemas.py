from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""
