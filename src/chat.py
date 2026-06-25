import re
import time
import logging
from operator import itemgetter

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser

from src.config import (
    GROQ_API_KEY, SESSION_TTL_SECONDS,
    CHROMA_PERSIST_DIR, SYSTEM_PROMPT_PATH, DAILY_REQUEST_LIMIT,
)
from src.models.schemas import ChatRequest, ChatResponse
from src.guardrails import check_injection
from src.rate_limiter import check_and_update
from src.retry import with_retry

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_store: dict[str, tuple[InMemoryChatMessageHistory, float]] = {}
_rag_chain = None
_vector_store = None


def _clean_expired_sessions() -> None:
    now = time.time()
    expired = [
        sid for sid, (_, last_access) in _store.items()
        if now - last_access > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _store[sid]


def _get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    _clean_expired_sessions()
    now = time.time()
    if session_id not in _store:
        _store[session_id] = (InMemoryChatMessageHistory(), now)
    else:
        history, _ = _store[session_id]
        _store[session_id] = (history, now)
    return _store[session_id][0]


def _read_system_prompt() -> str:
    try:
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Archivo de rol no encontrado en: %s", SYSTEM_PROMPT_PATH)
        return "Eres un asistente tecnico. Responde basandote solo en el contexto proporcionado."


def _format_docs(docs: list) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def _extract_sources(docs: list) -> list[str]:
    sources: set[str] = set()
    for doc in docs:
        source = doc.metadata.get("source", "")
        filename = source.split("/")[-1] if source else "desconocido"
        sources.add(filename)
    return sorted(sources)


def _extract_named_items(text: str) -> set[str]:
    pattern = r"(?:^|\n)\s*[-*]\s*\*\*([^*]+)\*\*"
    matches = re.findall(pattern, text, re.MULTILINE)
    items: set[str] = set()
    for match in matches:
        if isinstance(match, tuple):
            for item in match:
                stripped = item.strip()
                if stripped:
                    items.add(stripped.lower())
        elif isinstance(match, str):
            stripped = match.strip()
            if stripped:
                items.add(stripped.lower())
    return items


def _check_confidence(answer: str, sources: list[str], context: str = "") -> str:
    if not sources:
        return "low"

    if context:
        context_items = _extract_named_items(context)
        answer_items = _extract_named_items(answer)
        if answer_items and context_items:
            invented_items = answer_items - context_items
            if invented_items:
                logger.warning(
                    "Items inventados detectados en respuesta: %s",
                    invented_items,
                )
                return "low"
            return "high"

    answer_lower = answer.lower()
    for source in sources:
        name = source.replace(".md", "").lower()
        if name in answer_lower:
            return "high"
    return "low"


def _load_vector_store() -> Chroma:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embeddings,
    )


def _build_chain() -> RunnableWithMessageHistory:
    global _vector_store

    if _vector_store is None:
        _vector_store = _load_vector_store()

    llm = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
    )

    retriever = _vector_store.as_retriever(search_kwargs={"k": 8})

    system_prompt = _read_system_prompt()
    system_template = system_prompt + "\n\n<contexto_documentos>\n{context}\n</contexto_documentos>"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    rag_chain = (
        RunnablePassthrough.assign(
            docs=itemgetter("input") | retriever
        )
        | RunnablePassthrough.assign(
            context=lambda x: _format_docs(x["docs"]),
            sources=lambda x: _extract_sources(x["docs"]),
        )
        | RunnablePassthrough.assign(
            answer=(
                {
                    "context": itemgetter("context"),
                    "input": itemgetter("input"),
                    "chat_history": itemgetter("chat_history"),
                }
                | prompt
                | llm
                | StrOutputParser()
            ),
        )
    )

    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        _get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    return chain_with_history


def get_rag_chain() -> RunnableWithMessageHistory:
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = _build_chain()
    return _rag_chain


def refresh_knowledge() -> dict:
    global _rag_chain, _vector_store, _store

    _store.clear()
    _vector_store = _load_vector_store()
    _rag_chain = _build_chain()

    col = _vector_store.get()
    chunk_count = len(col.get("ids", [])) if col else 0

    logger.info("Conocimiento recargado. Chunks en ChromaDB: %d", chunk_count)
    return {"status": "success", "chunks_en_chromadb": chunk_count}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, chat_req: ChatRequest) -> ChatResponse:
    if not chat_req.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacia")

    import uuid
    session_id = chat_req.session_id or str(uuid.uuid4())
    client_ip = request.client.host

    if len(chat_req.question) > 500:
        return ChatResponse(
            session_id=session_id,
            answer="Tu pregunta es muy extensa. Maximo 500 caracteres.",
            blocked=True,
            block_reason="input_too_long",
            confidence="low",
        )

    blocked, reason = check_injection(chat_req.question)
    if blocked:
        return ChatResponse(
            session_id=session_id,
            answer="Solo estoy autorizado para hablar sobre el portafolio tecnico y profesional de Fabian Albarracin.",
            blocked=True,
            block_reason=reason,
            confidence="low",
        )

    if not check_and_update(client_ip, daily_limit=DAILY_REQUEST_LIMIT):
        return ChatResponse(
            session_id=session_id,
            answer="Has alcanzado el limite de consultas diarias. Intenta de nuevo manana.",
            blocked=True,
            block_reason="daily_limit",
            confidence="low",
        )

    try:
        chain = get_rag_chain()
        result = with_retry(chain.invoke)(
            {"input": chat_req.question},
            config={"configurable": {"session_id": session_id}},
        )

        answer_text = result.get("answer", "")
        sources_list = result.get("sources", [])
        context_text = result.get("context", "")
        confidence = _check_confidence(answer_text, sources_list, context_text)

        return ChatResponse(
            session_id=session_id,
            answer=answer_text,
            sources=sources_list,
            blocked=False,
            confidence=confidence,
        )

    except Exception as e:
        logger.error("Error en generacion LLM: %s", e)
        return ChatResponse(
            session_id=session_id,
            answer="El servicio de IA no esta disponible en este momento. Intenta de nuevo en unos segundos.",
            sources=[],
            blocked=True,
            block_reason="llm_unavailable",
            confidence="low",
        )
