# AGENTS.md — Portfolio Chatbot API v2.0

Instrucciones para agentes de IA que trabajen en este repositorio.
Cada linea responde: "¿Un agente se equivocaria sin esta informacion?"

---

## Documentos rectores

| Documento | Rol | Precedencia |
|---|---|---|
| `CONTRATO.md` | Arquitectura v2.0 aprobada. Decisiones inamovibles. | **Maxima** |
| `TICKETS.md` | Seguimiento de tareas de implementacion. | Subordinado al contrato |
| `AGENTS.md` | Este archivo. Instrucciones operativas para el agente. | Subordinado al contrato |

---

## Estructura del proyecto (post-migracion v2.0)

```
chatbot_portfolio/
├── .env.example                # Plantilla de variables (commiteado, sin secretos)
├── .gitignore                  # Excluye .env, chroma_db/, __pycache__, .venv, data/**/*.md, data/usage_logs.json
├── .dockerignore               # Excluye venv/__pycache__/.git/.env
├── pyproject.toml              # Dependencias pineadas (reemplaza requirements.txt)
├── Dockerfile                  # python:3.12-slim, sin build-essential
├── docker-compose.yml          # Servicio unico, workers=1, UVICORN_RELOAD desde ENV
├── README.md                   # Arranque rapido
├── CONTRATO.md                 # Arquitectura v2.0 (fuente de verdad)
├── TICKETS.md                  # Seguimiento de tareas
├── AGENTS.md                   # Este archivo
├── update_knowledge.sh         # Script: ingest.py + curl POST /admin/refresh
│
├── config/
│   └── system_role.md          # System prompt del LLM (commiteado)
│
├── data/                       # Conocimiento real (gitignored salvo .gitkeep)
│   ├── chroma_db/              # Cache vectorial (gitignored)
│   ├── educacion/
│   ├── experiencia/
│   ├── perfil/
│   └── proyectos/
│
├── data_example/               # Mock data para open-source (commiteado)
│   ├── educacion/
│   │   └── educacion_ejemplo.md
│   ├── experiencia/
│   │   └── experiencia_ejemplo.md
│   ├── perfil/
│   │   └── perfil_ejemplo.md
│   └── proyectos/
│       └── proyecto_ejemplo.md
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, logging, CORS, healthcheck, registro de rutas
│   ├── config.py               # Carga tipada de variables de entorno con defaults
│   ├── chat.py                 # POST /chat + create_retrieval_chain + RunnableWithMessageHistory
│   ├── admin.py                # POST /admin/refresh (protegido con X-API-KEY)
│   ├── guardrails.py           # Regex anti-injection + filtro pre-LLM
│   ├── rate_limiter.py         # Contador diario en memoria con threading.Lock
│   ├── ingest.py               # Pipeline ETL offline: Markdown con frontmatter -> ChromaDB
│   ├── retry.py                # Wrapper de retry con backoff exponencial para llamadas LLM
│   └── models/
│       └── schemas.py          # Pydantic ChatRequest + ChatResponse (con campo blocked)
│
└── tests/
    ├── evaluator.py            # Triada RAG (RAGAS) + 30+ casos de prueba
    ├── datasets/               # Preguntas de control en JSON
    │   ├── extraccion.json
    │   ├── razonamiento.json
    │   ├── seguridad.json
    │   ├── idiomas.json
    │   ├── memoria.json
    │   └── falsos_positivos.json
    ├── unit/                   # Tests unitarios con pytest
    │   ├── test_guardrails.py
    │   ├── test_ingest.py
    │   ├── test_rate_limiter.py
    │   └── test_config.py
    └── reports/                # Resultados de evaluacion (gitignored)
```

**Archivos legacy que desaparecen en v2.0:**
`src/core/orchestrator.py`, `src/core/session.py`, `src/services/semantic_router.py`,
`src/services/vector_db.py`, `src/services/llm_groq.py`, `src/api/dependencies.py`,
`src/api/chat_router.py`, `requirements.txt`.

---

## Variables de entorno

| Variable | Obligatoria | Default | Uso |
|---|---|---|---|
| `LITELLM_CHATBOT_KEY` | Si | — | Virtual key del proxy LiteLLM (`http://litellm:4000/v1`) |
| `CHATBOT_API_KEY` | Si | — | Protege `POST /admin/refresh` |
| `ALLOWED_ORIGINS` | No | `localhost:5173` | Origenes CORS (separados por coma) |
| `UVICORN_RELOAD` | No | `false` | Hot-reload uvicorn para desarrollo |
| `LOG_LEVEL` | No | `INFO` | Nivel de logging Python |
| `DAILY_REQUEST_LIMIT` | No | `100` | Limite diario por IP |
| `RATE_LIMIT_PER_MINUTE` | No | `20` | Limite por minuto por IP |
| `SESSION_TTL_SECONDS` | No | `600` | TTL de sesion en segundos |
| `GROQ_API_KEY` | Solo tests | — | Juez LLM para evaluador (conexion directa a Groq, no via LiteLLM) |

**Punto critico**: Las API keys reales de Groq/OpenCode NO estan en este repo.
Viven en LiteLLM. Este proyecto solo conoce la virtual key de LiteLLM.
`data/**/*.md` estan en `.gitignore` (informacion personal).

---

## Comandos exactos

```bash
# Arrancar (requiere red externa homelab_proxy_net)
docker compose up -d

# Actualizar base de conocimiento completa (ingest + hot-reload)
bash update_knowledge.sh

# Solo re-indexar vectores (sin hot-reload)
docker exec -t portfolio_chatbot_api python src/ingest.py

# Solo hot-reload (recargar vectores en RAM sin reiniciar uvicorn)
curl -X POST http://localhost:8000/admin/refresh \
     -H "x-api-key: $CHATBOT_API_KEY" \
     -H "Content-Length: 0"

# Healthcheck (verifica ChromaDB + LiteLLM)
curl http://localhost:8000/health

# Probar el chat
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "Hablame sobre Tradehub", "session_id": "abc123"}'

# Ejecutar tests unitarios
pytest tests/unit/ -v

# Ejecutar evaluador de calidad (requiere API corriendo en localhost:8000 + GROQ_API_KEY en .env)
python tests/evaluator.py

# Documentacion OpenAPI/Swagger
curl http://localhost:8000/docs
```

**No hay comandos de lint, typecheck ni build.** No existe CI configurado.

---

## Arquitectura v2.0

### Patron RAG: LangChain LCEL (implementacion real)

**Nota importante:** `create_retrieval_chain` y `create_stuff_documents_chain` fueron
removidos en LangChain 1.2.x. La implementacion usa LCEL (LangChain Expression Language)
con `itemgetter` + `RunnablePassthrough` + `RunnableLambda`. El comportamiento es
identico al patron documentado en el CONTRATO.

El flujo es deterministico, incondicional, y usa 1 sola llamada LLM por request:

```
POST /chat
  |
  v
[guardrails.py] --- pre-filtro regex anti-injection
  |
  v
[rate_limiter.py] --- verificacion limite diario con Lock
  |
  v
[ChromaDB.as_retriever(search_kwargs={"k": 6})] --- busqueda SIEMPRE
  |
  v
[LCEL chain: itemgetter + RunnablePassthrough + StrOutputParser]
  |-- retriever -> format_docs -> inyecta contexto en prompt
  |-- RunnableWithMessageHistory -> anade historial de sesion
  |-- with_retry(chain.invoke) -> 2 reintentos con backoff
  |
  v
[_check_confidence()] --- verifica entity_names en answer vs sources
  |
  v
ChatResponse: { session_id, answer, sources, blocked, block_reason, confidence }
```

**No existe:** SemanticRouter, clasificacion de intents, maquina de estados,
busqueda federada, particiones de memoria, inyeccion programatica de idioma,
`create_retrieval_chain`, `create_stuff_documents_chain`.

### Componentes LangChain utilizados (reales)

| Componente | API LangChain | Uso |
|---|---|---|
| LLM | `ChatOpenAI(model="llama-8b", base_url="http://litellm:4000/v1")` | Conexion via LiteLLM proxy |
| Embeddings | `HuggingFaceEmbeddings("all-MiniLM-L6-v2")` | Vectorizacion de chunks |
| Vector Store | `Chroma(persist_directory=..., embedding_function=...)` | Persistencia local SQLite |
| Retriever | `vector_store.as_retriever(search_kwargs={"k": 6})` | Recuperacion de chunks |
| Prompt | `ChatPromptTemplate.from_messages([("system", ...), MessagesPlaceholder, ("human", ...)])` | System + historial + user |
| Chain composition | `itemgetter("input")` + `RunnablePassthrough.assign(...)` + `prompt` + `llm` + `StrOutputParser()` | Composicion declarativa |
| History | `RunnableWithMessageHistory(chain, get_session_history, input_messages_key, output_messages_key)` | Memoria por session_id |
| History store | `InMemoryChatMessageHistory` con TTL manual en dict | Almacenamiento en RAM con limpieza por timestamp |

### Memoria de sesion

- `RunnableWithMessageHistory` de LangChain maneja el historial por `session_id`
- TTL: 600s (configurable via `SESSION_TTL_SECONDS`)
- Almacenamiento: `ChatMessageHistory` en memoria (dict por session_id)
- Sin particiones, sin LRU manual, sin garbage collector custom
- Referencia: `https://python.langchain.com/docs/how_to/message_history/`

### ChromaDB

- Persistencia: `/app/data/chroma_db/` (Docker) o `./data/chroma_db/` (local)
- Embeddings: `all-MiniLM-L6-v2` via `HuggingFaceEmbeddings`
- `as_retriever()` expone la interfaz estandar de LangChain
- Metadatos por chunk: `entity_name`, `entity_type`, `source`, headers, `description`, `tags`
- Referencia: `https://python.langchain.com/docs/integrations/vectorstores/chroma/`

### Multi-idioma

- **Cero codigo.** El system prompt instruye: "Responde en el mismo idioma de la pregunta"
- El LLM maneja 50+ idiomas naturalmente
- Sin deteccion programatica, sin listas hardcodeadas, sin inyeccion de idioma

### Rate limiting (doble capa)

1. **slowapi**: `@limiter.limit("20/minute")` sobre `POST /chat`. Retorna HTTP 429.
2. **Contador diario**: 100 req/dia por IP en `rate_limiter.py` con `threading.Lock`.
   En memoria, con flush periodico a `data/usage_logs.json`. Sin race condition.

### Seguridad (triple capa)

1. **Pre-filtro regex** (`guardrails.py`): bloquea "ignore previous instructions",
   "system prompt", "api key", "contraseña", patrones base64. Sin llamada LLM.
2. **System prompt**: Regla 4 anti prompt-injection en `config/system_role.md`.
3. **Campo `blocked`**: la respuesta incluye `"blocked": true/false` y
   `"block_reason": "out_of_scope"|"daily_limit"|"injection"` para el frontend.

### Ingesta de conocimiento

- `src/ingest.py`: `DirectoryLoader` -> `MarkdownHeaderTextSplitter` ->
  `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)` ->
  `HuggingFaceEmbeddings` -> `Chroma.add_documents()`
- `POST /admin/refresh`: recarga catalogo de entidades en RAM
- `update_knowledge.sh`: `ingest.py` + `curl POST /admin/refresh`

### Retry ante fallos de LiteLLM

- `src/retry.py`: wrapper generico con 2 reintentos, backoff 1s/2s
- Aplica a la unica llamada LLM del sistema (generacion final)
- Si falla tras 3 intentos: mensaje claro de indisponibilidad

---

## Pipeline de conocimiento

### Formato de documentos Markdown

Cada archivo `.md` requiere frontmatter YAML:

```yaml
---
entity_type: project | education | experience | profile
entity_name: identificador_unico_sin_extension
title: Titulo Formal del Documento
description: Maximo 15 palabras resumiendo el contenido
tags: [tag1, tag2, tag3]
---
```

**Convencion de `entity_name`:**
- Sin extension `.md`
- Lowercase
- Snake_case sin espacios
- Ejemplos: `tradehub`, `formacion_academica`, `perfil_personal`, `experiencia_profesional`

### Ingest (`src/ingest.py`)

1. `DirectoryLoader` con `TextLoader` carga `**/*.md` bajo `data/`
2. `python-frontmatter` extrae metadatos YAML. Archivos sin `entity_name` se ignoran
3. `MarkdownHeaderTextSplitter` divide por H1/H2/H3
4. `RecursiveCharacterTextSplitter` sub-divide (chunk_size=800, chunk_overlap=150)
5. Prefijo `[Entidad: {name} | Seccion: {header}]\n` en cada chunk
6. Purga vectores existentes preservando UUID de coleccion
7. Inserta nuevos vectores con `HuggingFaceEmbeddings("all-MiniLM-L6-v2")`

### Hot-reload (`POST /admin/refresh`)

- Reconstruye catalogo de entidades desde frontmatter de `.md`
- Limpia cache de historial de sesiones
- Zero-downtime: no requiere reiniciar uvicorn

**Orden obligatorio:** `ingest.py` -> `POST /admin/refresh`. Si solo ejecutas
ingest sin hot-reload, el servidor usa vectores viejos en RAM.

---

## Testing

### Tests unitarios

```bash
# Ejecutar dentro del contenedor Docker (pytest no esta instalado en el host)
docker exec portfolio_chatbot_api python -m pytest tests/unit/ -v
```

- `test_guardrails.py` (10 tests): pre-filtro regex ingles/espanol + falsos positivos
- `test_ingest.py` (6 tests): parseo de frontmatter, splitting, enriquecimiento
- `test_rate_limiter.py` (4 tests): atomicidad del contador con Lock, concurrencia
- `test_config.py` (9 tests): defaults, paths, env vars

### Evaluador de calidad (RAGAS)

```bash
# Requiere API corriendo en localhost:8000 + GROQ_API_KEY en .env
python tests/evaluator.py
```

- Metricas RAGAS: Context Relevance, Faithfulness, Answer Relevance
- 35 casos de prueba en `tests/datasets/` (6 archivos JSON)
- Reportes en `tests/reports/run_YYYYMMDD_HHMMSS/`

---

## Problemas conocidos

### Alucinaciones en documentos con listas (cursos, certificaciones, fechas)

**Severidad:** Alta | **Estado:** Sin resolver | **Sesion:** 2026-06-25

El LLM (`llama-8b`) tiende a inventar cursos, certificaciones, plataformas y fechas
cuando se le pide listar elementos de documentos como `formacion_academica.md`.
Ejemplo: el chatbot invento "Certificacion en Desarrollo de Aplicaciones Web con
Python: Platzi, 2023", "React Native: Udemy, 2022", etc. — ninguna existe en el
documento real.

**Causa:** El system prompt tiene reglas anti-alucinacion (Regla 1, 3) pero el
modelo las ignora al listar items. Tiende a "rellenar" con datos plausibles.

**Entidades en riesgo:**
- `formacion_academica` (CRITICO) — cursos, certificaciones, fechas, plataformas
- `experiencia_profesional` (ALTO) — nombres de empresas, fechas, tecnologias
- `perfil_personal` (MEDIO) — habilidades, idiomas, anos de experiencia
- `proyectos` (BAJO) — el stack tecnologico suele ser preciso

**`_check_confidence()` NO detecta este problema** porque solo verifica entity_names
en sources, no el contenido factual de la respuesta.

**Posibles soluciones (no implementadas):**
1. Reforzar system prompt con regla anti-invencion de cursos
2. Aumentar `k` de 6 a 10 en el retriever
3. Verificacion post-generacion a nivel de tokens (extraer entidades del contexto
   y verificar que la respuesta no invente ninguna)
4. Cambiar el modelo via LiteLLM (ej. `llama-70b`, `mistral`, `command-r`)

**Documentacion detallada:** `docs/handoff/session_2026-06-25.md`

---

## Restricciones y convenciones

- **Workers = 1 es obligatorio.** ChromaDB usa SQLite como backend.
- **Nunca expongas el puerto 8000 directamente a internet.**
- **No commitees `data/**/*.md` ni `data/chroma_db/`.** Son personales; regenerables.
- **Siempre haz hot-reload despues del ingest.** El servidor cachea en RAM.
- **No uses emojis en las respuestas del chatbot** (system prompt lo prohibe).
- **`print()` esta prohibido.** Usar modulo `logging` con niveles.
- **Type hints en todas las funciones publicas.**
- **`secrets.compare_digest()` para comparar API keys** (anti timing attack).
- **CORS desde variable de entorno `ALLOWED_ORIGINS`**, no hardcodeado.

---

## Referencias API (Documentacion de LangChain)

Estas son las paginas de documentacion oficial que el agente debe consultar
durante la implementacion. Usar `webfetch` para acceder a ellas.

### Core — Patron RAG

| Pagina | URL | Contenido clave |
|---|---|---|
| RAG Tutorial | `https://python.langchain.com/docs/tutorials/rag/` | `create_retrieval_chain`, `create_stuff_documents_chain`, `ChatPromptTemplate` |
| Message History | `https://python.langchain.com/docs/how_to/message_history/` | `RunnableWithMessageHistory`, `ChatMessageHistory`, session_id, TTL |
| Chroma Integration | `https://python.langchain.com/docs/integrations/vectorstores/chroma/` | `Chroma()`, `as_retriever()`, `similarity_search`, metadata filter, `persist_directory` |

### Complementos

| Pagina | URL | Contenido clave |
|---|---|---|
| ChatOpenAI | `https://python.langchain.com/docs/integrations/chat/openai/` | `base_url` para LiteLLM, `temperature`, `model` |
| HuggingFace Embeddings | `https://python.langchain.com/docs/integrations/text_embedding/huggingfacehub/` | `HuggingFaceEmbeddings(model_name=...)` |
| Text Splitters | `https://python.langchain.com/docs/how_to/#text-splitters` | `RecursiveCharacterTextSplitter`, `MarkdownHeaderTextSplitter` |
| Retrieval | `https://python.langchain.com/docs/how_to/#retrieval` | `as_retriever()`, search_kwargs, filtros |
| ChatPromptTemplate | `https://python.langchain.com/docs/how_to/#prompt-templates` | `from_messages()`, system + human templates |
| API Reference (Chroma) | `https://reference.langchain.com/python/langchain-chroma/vectorstores/Chroma` | Metodos completos del wrapper Chroma |

### Seguridad y Frontend

| Pagina | URL | Contenido clave |
|---|---|---|
| FastAPI CORS | `https://fastapi.tiangolo.com/tutorial/cors/` | `CORSMiddleware`, `allow_origins`, `allow_methods` |
| FastAPI Security | `https://fastapi.tiangolo.com/tutorial/security/api-key-header/` | `APIKeyHeader`, `Depends` |
| SlowAPI | `https://slowapi.readthedocs.io/` | `Limiter`, `@limiter.limit`, `get_remote_address` |
| RAGAS Metrics | `https://docs.ragas.io/` | `ContextRelevancy`, `Faithfulness`, `AnswerRelevancy` |


### Notas de implementacion

1. **Siempre leer la documentacion antes de escribir codigo.** Las APIs de LangChain
   evolucionan. Lo que funcionaba en v0.x puede tener nombres distintos en v1.x.
   Las URLs arriba son la fuente canonica.

2. **`webfetch` es la herramienta para consultar documentacion.** Ejemplo:
   `webfetch(url="https://python.langchain.com/docs/how_to/message_history/", format="markdown")`

3. **Las APIs de LangChain son el contrato.** No reinventes patrones que ya
   estan documentados. Si existe `create_retrieval_chain`, no escribas un
   orquestador custom. Si existe `RunnableWithMessageHistory`, no escribas
   un SessionManager custom.

4. **Ante duda, consulta `CONTRATO.md`.** Es la maxima autoridad de diseno.
