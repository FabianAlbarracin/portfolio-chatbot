# Portfolio Chatbot API v2.0

Chatbot RAG deterministico usando LangChain + FastAPI + ChromaDB + LiteLLM proxy.
Responde preguntas sobre un portafolio profesional basandose exclusivamente en
documentos Markdown con frontmatter YAML.

## Arquitectura

```
POST /chat
  |
  v
[guardrails.py] --- pre-filtro regex anti-injection
  |
  v
[ChromaDB as_retriever(k=6)] --- busqueda vectorial incondicional
  |
  v
[LLM via LiteLLM] --- generacion con contexto + historial de sesion
  |
  v
ChatResponse { session_id, answer, sources, blocked, block_reason, confidence }
```

- **1 sola llamada LLM por request** (sin router, sin clasificacion de intents)
- **Memoria de sesion**: `RunnableWithMessageHistory` (TTL 600s)
- **Rate limiting**: slowapi (20 req/min) + contador diario con `threading.Lock`
- **Seguridad**: regex pre-LLM + system prompt anti-injection + `secrets.compare_digest()`

## Arranque rapido

### 1. Clonar y configurar

```bash
git clone <repo-url>
cd chatbot_portfolio

# Copiar datos de ejemplo (portafolio ficticio para pruebas)
cp -r data_example data

# Configurar variables de entorno
cp .env.example .env
```

Edita `.env` con tu virtual key de LiteLLM:

```ini
LITELLM_CHATBOT_KEY=sk-tu-virtual-key
CHATBOT_API_KEY=tu-api-key-secreta-para-admin
```

### 2. Construir y arrancar

```bash
docker compose up -d --build
```

### 3. Indexar los documentos de ejemplo

```bash
bash update_knowledge.sh
```

### 4. Probar

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Hablame sobre el Sistema de Inventario", "session_id": "test123"}'
```

Respuesta esperada:

```json
{
  "session_id": "test123",
  "answer": "Maria Ejemplo desarrollo el Sistema de Inventario Inteligente...",
  "sources": ["proyecto_ejemplo.md"],
  "blocked": false,
  "block_reason": "",
  "confidence": "high"
}
```

## Usar tus propios datos

1. Crea archivos `.md` en `data/` usando el formato con frontmatter YAML (ver ejemplos en `data_example/`)
2. Cada archivo requiere: `entity_type`, `entity_name`, `title`, `description`, `tags`
3. Ejecuta `bash update_knowledge.sh` para re-indexar
4. El chatbot incorpora el nuevo conocimiento sin reiniciar ni modificar codigo

## Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/health` | Healthcheck (ChromaDB + LiteLLM) |
| `POST` | `/chat` | Chat RAG principal |
| `POST` | `/admin/refresh` | Hot-reload de conocimiento (requiere `X-API-KEY`) |
| `GET` | `/docs` | Documentacion OpenAPI/Swagger |

## Tests

```bash
# Tests unitarios (29 tests, no requieren API corriendo)
docker exec portfolio_chatbot_api python -m pytest tests/unit/ -v

# Evaluador de calidad RAGAS (requiere API corriendo + GROQ_API_KEY en .env)
python tests/evaluator.py
```

## Variables de entorno

Ver `.env.example` para la lista completa. Variables requeridas:

| Variable | Proposito |
|----------|-----------|
| `LITELLM_CHATBOT_KEY` | Virtual key del proxy LiteLLM |
| `CHATBOT_API_KEY` | Protege `POST /admin/refresh` |

## Estructura del proyecto

```
chatbot_portfolio/
├── src/
│   ├── main.py          # FastAPI app, CORS, logging, healthcheck
│   ├── chat.py           # RAG chain LCEL + POST /chat
│   ├── admin.py          # POST /admin/refresh
│   ├── config.py         # Env vars + paths
│   ├── guardrails.py     # Regex anti-injection
│   ├── rate_limiter.py   # Contador diario con Lock
│   ├── ingest.py         # Pipeline ETL .md -> ChromaDB
│   ├── retry.py          # Backoff exponencial
│   └── models/schemas.py # Pydantic ChatRequest/Response
├── config/
│   └── system_role.md    # System prompt del LLM
├── data/                 # Tus documentos (gitignored)
├── data_example/         # Datos de ejemplo (commiteados)
├── tests/
│   ├── unit/             # Tests unitarios pytest
│   ├── evaluator.py      # Evaluador RAGAS
│   └── datasets/         # 35 casos de prueba en JSON
├── pyproject.toml        # Dependencias
├── Dockerfile
└── docker-compose.yml
```
