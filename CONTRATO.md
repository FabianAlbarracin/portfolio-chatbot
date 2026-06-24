# CONTRATO DE DESARROLLO — Chatbot_Asistente_Portafolio_RAG v2.0

**Estado:** Aprobado para implementacion
**Fecha:** 24 de junio de 2026
**Repositorio:** `chatbot_portfolio`

---

## 0. Trazabilidad y Documentos Vinculados

Este contrato es la fuente de verdad para la arquitectura v2.0. Los siguientes documentos
estan subordinados a el:

| Documento | Rol | Vinculo |
|---|---|---|
| `TICKETS.md` | Seguimiento de tareas | Los tickets T-001 al T-026 se resuelven segun este contrato |
| `AGENTS.md` | Instrucciones para IA desarrolladora | Describe el sistema legacy; se actualizara al finalizar |
| `README.md` | Arranque rapido | Se actualizara al finalizar |

### Tickets cerrados automaticamente por esta arquitectura

Al eliminar `SemanticRouter`, maquina de estados, `SessionManager` custom, y `VectorStore`
custom, los siguientes tickets **no requieren trabajo** porque sus componentes dejan de existir:

T-001, T-002, T-003, T-005, T-008, T-010, T-019, T-020, T-021, T-023, T-024

### Tickets que deben resolverse en la implementacion

T-004, T-006, T-007, T-009, T-011, T-012, T-013, T-014, T-016, T-017, T-018, T-022, T-025, T-026

---

## 1. Objeto

Microservicio backend de IA para portafolio profesional usando RAG deterministico
basado en LangChain. El chatbot responde de forma fluida, no-rigida, fundamentado
**exclusivamente** en documentos Markdown con frontmatter YAML. Opera en entornos
de recursos limitados (Homelab, 8 GB RAM) y cumple con estandares de seguridad y
evaluacion continua.

---

## 2. El Problema (Estado Legacy)

El sistema actual (`v1.x`) presenta tres fallas criticas:

1. **Rigidez en la interaccion:** El `SemanticRouter` fuerza clasificacion de 6
   intents via LLM antes de cada consulta. Si el router falla en extraer la entidad
   correcta del catalogo, bloquea la busqueda (Fail-safe anti-envenenamiento) y el
   chatbot no responde, generando una experiencia de "arbol de decisiones".

2. **Fragilidad en la recuperacion:** La validacion de entidades por string exacto
   (`if e in entity_catalog`) descarta matches validos cuando el LLM devuelve
   un nombre con formato ligeramente distinto al del catalogo. El intent `NONE`
   (fallo del router) produce generacion sin contexto → alucinaciones.

3. **Complejidad operativa:** El pipeline de ingesta requiere ejecucion manual de
   `update_knowledge.sh` tras cada cambio en los `.md`. La arquitectura contiene
   ~600 lineas de codigo custom (orquestador, router, maquina de estados, sesiones)
   que replican patrones ya resueltos por LangChain.

---

## 3. Decisiones de Arquitectura (Inamovibles)

> **Nota para el agente implementador:** Cada seccion incluye la URL canonica de
> LangChain que documenta el patron. Usar `webfetch` para consultar el contenido
> actualizado antes de escribir codigo. La documentacion de LangChain evoluciona;
> las URLs son la fuente de verdad, no la memoria del agente.

### 3.1 Patron RAG: LangChain `create_retrieval_chain`

**Fuente canonica:** https://python.langchain.com/docs/tutorials/rag/

- Recuperacion **INCONDICIONAL**: toda pregunta dispara `similarity_search(k=6)`
  contra ChromaDB. No existe clasificador de intents, no existe router previo,
  no existe maquina de estados de contexto.
- El contexto recuperado se inyecta en el prompt. El LLM recibe system prompt +
  contexto + pregunta y decide si responde o declina.
- **1 sola llamada LLM por request.**
- Se usa exclusivamente la API publica y documentada de LangChain:
  `create_retrieval_chain` + `create_stuff_documents_chain` + `ChatPromptTemplate`.

**Lo que se elimina del codigo:**
- `src/core/orchestrator.py` (completo)
- `src/services/semantic_router.py` (completo)
- `src/core/session.py` (completo)
- `src/services/vector_db.py` (reemplazado por `as_retriever()` de LangChain)
- `src/api/dependencies.py` (reemplazado por inicializacion directa)

### 3.2 Memoria de Sesion

**Problema:** LangChain `create_retrieval_chain` no tiene memoria. El doc de
requerimientos exige "memoria de la conversacion por un tiempo corto".

**Solucion:** Usar `RunnableWithMessageHistory` de LangChain (API documentada).
Esto proporciona historial de chat con sesion por `session_id`, TTL configurable,
y almacenamiento en memoria (sin dependencia externa). No se construye un
SessionManager custom.

- TTL: 600 segundos (10 minutos)
- Maximo de mensajes en historial: 6 (3 interacciones)
- Sin particiones por dominio, sin LRU eviction manual. LangChain lo maneja.

**Referencia:** https://python.langchain.com/docs/how_to/message_history/

### 3.3 Base de Datos Vectorial: ChromaDB (SQLite local)

**Decision:** Se mantiene ChromaDB con persistencia SQLite local.

**Justificacion del rechazo de Qdrant/Milvus:**
- Qdrant requiere +200 MB RAM adicionales + otro contenedor Docker
- Milvus requiere +500 MB RAM
- El volumen actual (<100 consultas/dia, 7 documentos) no justifica la migracion
- ChromaDB con `workers=1` es suficiente y respeta la restriccion de recursos
  limitados del Homelab

- Persistencia: `/app/data/chroma_db/` dentro del contenedor Docker
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` via `HuggingFaceEmbeddings`
- Catalogo de entidades: construido en RAM al iniciar, leyendo frontmatter de cada `.md`

### 3.4 Multi-idioma

**Decision:** Sin deteccion programatica de idioma. Sin listas hardcodeadas.
Sin inyeccion de instrucciones de idioma en el codigo.

**Mecanismo:** El system prompt contiene la regla:

```
REGLA DE IDIOMA: Analiza el idioma de la pregunta del usuario y responde
FLUIDAMENTE en ese mismo idioma, traduciendo cualquier termino tecnico
segun corresponda.
```

El LLM (`llama-8b`) maneja naturalmente 50+ idiomas. Si el usuario pregunta
en frances, el LLM responde en frances. Si pregunta en arabe, responde en arabe.
Cero logica de deteccion en el codigo Python.

**Cobertura:** cualquier idioma que el modelo soporte, sin cambios en el codigo.

### 3.5 Seguridad y Rate Limiting

**Rate Limiting (doble capa):**
1. `slowapi`: 20 req/min por IP. Key func: `get_remote_address`. Retorna HTTP 429.
2. Contador diario: 100 req/dia por IP. En memoria con flush periodico a disco
   usando `threading.Lock` para atomicidad. Sin JSON sin locking.

**Guardrails anti prompt-injection (doble capa):**
1. **Pre-LLM (regex):** En el endpoint `/chat`, antes de invocar la cadena RAG,
   se aplican patrones regex para bloquear:
   - "ignore previous instructions", "ignore all"
   - "system prompt", "instrucciones del sistema", "api key", "contraseña",
     "password"
   - Patrones base64 (deteccion de encoding sospechoso)
   Si el pre-filtro detecta ataque → respuesta inmediata `OUT_OF_SCOPE` sin
   llamada al LLM.
2. **System prompt:** Regla de proteccion de identidad que instruye al LLM a
   declinar consultas fuera del portafolio (salarios, temas legales, medicos,
   prompt injection).

**CORS:**
- Origenes permitidos desde variable de entorno `ALLOWED_ORIGINS` (string separado
  por comas). Sin hardcodeo de dominios.

**API Key:**
- `POST /admin/refresh`: protegido con header `X-API-KEY` validado contra
  `CHATBOT_API_KEY`.
- `POST /chat`: sin autenticacion (el frontend no expone secretos).
- Comparacion de API key usando `secrets.compare_digest()` para evitar timing attacks.

**Rate Limiting en Frontend (responsabilidad del cliente HTTP):**
- Deshabilitar boton de envio durante el procesamiento de la respuesta.

### 3.6 Ingesta de Conocimiento

**Pipeline offline:**
- `src/ingest.py`: lee todos los `.md` bajo `data/`, extrae frontmatter YAML,
  divide jerarquicamente (H1/H2/H3), sub-divide en chunks de 800 chars con 150
  de overlap, enriquece con prefijo `[Entidad: X | Seccion: Y]`, inserta en
  ChromaDB.
- `POST /admin/refresh`: recarga el catalogo de entidades en RAM y limpia el
  cache de historial de sesiones.
- `update_knowledge.sh`: script Bash que ejecuta `ingest.py` + `POST /admin/refresh`.

**Sin Watchdog:** La deteccion automatica de cambios de archivo no se implementa.
Para un volumen de 7 documentos, el script manual es suficiente. La complejidad
de `watchdog` en Docker con volumenes montados no se justifica.

### 3.7 Retry ante Fallos de LiteLLM

**Mecanismo:** Envolver la llamada `chain.invoke()` en retry logic:
- 2 reintentos con backoff exponencial (1s, 2s)
- Si tras 3 intentos falla → respuesta clara: "El servicio de IA no esta
  disponible en este momento. Intenta de nuevo en unos segundos."
- Sin fallback silencioso a generacion sin contexto.

**Nota tecnica:** Este retry se aplica a la unica llamada LLM del sistema
(la generacion final). Al eliminar el SemanticRouter, ya no hay una segunda
llamada LLM que tambien necesite retry.

### 3.8 Evaluacion de Calidad (Benchmark Continuo)

**Metodologia:** Triada RAG (RAGAS):
- **Context Relevance:** ¿El contexto recuperado es relevante para la pregunta?
- **Faithfulness:** ¿La respuesta se fundamenta exclusivamente en el contexto?
- **Answer Relevance:** ¿La respuesta aborda la pregunta del usuario?

**Implementacion:** `tests/evaluator.py` reescrito para usar metricas RAGAS en
vez de LLM-as-a-Judge. El banco de preguntas se expande a >=30 casos cubriendo:
- Extraccion directa
- Razonamiento cruzado entre documentos
- Seguridad (prompt injection, out-of-scope)
- Idiomas (español, ingles, frances)
- Memoria conversacional

**Ejecucion obligatoria** antes de cualquier despliegue a produccion.

**Reporte:** Score numerico global + desglose por categoria. Almacenado en
`tests/reports/run_YYYYMMDD_HHMMSS/`.

### 3.9 Observabilidad

**Logging:**
- Modulo `logging` de Python (no `print()`)
- Niveles: DEBUG (desarrollo), INFO (produccion)
- Formato: `[%(levelname)s] %(asctime)s %(name)s: %(message)s`
- Salida: stdout. Docker recoge via `json-file` driver con rotacion (3x10MB)

**Sin archivos de log en disco ni JSON rotativos.**

**Healthcheck:**
- Verifica conectividad con ChromaDB (`db.get(limit=1)`)
- Verifica conectividad con LiteLLM (HEAD a `http://litellm:4000/health`)
- Responde: `{"status": "healthy"|"degraded", "checks": {"chromadb": "...", "litellm": "..."}}`

---

## 4. Estructura del Proyecto (Post-Migracion)

```
chatbot_portfolio/
├── .env.example                # Plantilla de variables (commiteado, sin secretos)
├── .gitignore                  # Excluye .env, chroma_db/, __pycache__, .venv, data/**/*.md
├── .dockerignore               # Excluye venv/__pycache__/.git/.env
├── pyproject.toml              # Dependencias pineadas (reemplaza requirements.txt)
├── Dockerfile                  # python:3.12-slim, sin build-essential
├── docker-compose.yml          # Servicio unico, workers=1, --reload segun ENV
├── README.md                   # Arranque rapido
├── CONTRATO.md                 # Este archivo
├── TICKETS.md                  # Seguimiento de tareas
├── AGENTS.md                   # Instrucciones para IA (actualizado post-migracion)
├── update_knowledge.sh         # Script: ingest.py + curl POST /admin/refresh
│
├── config/
│   └── system_role.md          # System prompt del LLM
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
│   ├── main.py                 # FastAPI app, CORS, healthcheck, registro de rutas
│   ├── config.py               # Carga tipada de variables de entorno
│   ├── chat.py                 # Endpoint /chat + create_retrieval_chain + message history
│   ├── admin.py                # Endpoint /admin/refresh
│   ├── guardrails.py           # Regex anti-injection + filtro pre-LLM
│   ├── rate_limiter.py         # Contador diario en memoria con Lock
│   ├── ingest.py               # Pipeline ETL offline: .md → ChromaDB
│   └── retry.py                # Wrapper de retry con backoff para llamadas LLM
│
└── tests/
    ├── evaluator.py            # Triada RAG (RAGAS) + 30+ casos de prueba
    ├── datasets/               # Preguntas de control en JSON
    │   ├── extraccion.json
    │   ├── razonamiento.json
    │   ├── seguridad.json
    │   ├── idiomas.json
    │   └── memoria.json
    ├── unit/                   # Tests unitarios (pytest)
    │   ├── test_guardrails.py
    │   ├── test_ingest.py
    │   ├── test_rate_limiter.py
    │   └── test_config.py
    └── reports/                # Resultados de evaluacion (gitignored)
```

---

## 5. Diff de Archivos (Legacy → v2.0)

### Archivos eliminados

| Archivo | Razon |
|---|---|
| `src/core/orchestrator.py` | Reemplazado por `create_retrieval_chain` de LangChain |
| `src/core/session.py` | Reemplazado por `RunnableWithMessageHistory` de LangChain |
| `src/services/semantic_router.py` | Eliminado. Sin router, sin clasificacion de intents |
| `src/services/vector_db.py` | Reemplazado por `as_retriever()` de LangChain |
| `src/services/llm_groq.py` | LLM se instancia directamente en `chat.py` |
| `src/api/dependencies.py` | Inicializacion directa sin singleton |
| `src/api/chat_router.py` | Reorganizado en `chat.py` + `admin.py` |
| `requirements.txt` | Reemplazado por `pyproject.toml` |

### Archivos creados

| Archivo | Proposito |
|---|---|
| `src/chat.py` | Endpoint `/chat` + cadena RAG + historial de mensajes |
| `src/admin.py` | Endpoint `/admin/refresh` |
| `src/config.py` | Carga tipada de `.env` con defaults |
| `src/guardrails.py` | Regex anti-injection + filtro pre-LLM |
| `src/retry.py` | Wrapper de retry con backoff exponencial |
| `pyproject.toml` | Dependencias pineadas |
| `data_example/` | Mock data para open-source |
| `tests/unit/` | Tests unitarios con pytest |
| `CONTRATO.md` | Este archivo |

### Archivos modificados

| Archivo | Cambios |
|---|---|
| `src/main.py` | Simplificado: imports, registro de rutas, logging |
| `src/ingest.py` | Sin cambios funcionales; movido a `src/` raiz |
| `src/rate_limiter.py` | Refactorizado con `threading.Lock` (antes `usage_tracker.py`) |
| `src/models/schemas.py` | Anadir campo `blocked` y `block_reason` a la respuesta |
| `config/system_role.md` | Anadir regla de multi-idioma delegado al LLM |
| `Dockerfile` | Remover `build-essential`, optimizar capas |
| `docker-compose.yml` | `UVICORN_RELOAD` desde variable de entorno, documentar workers=1 |
| `tests/evaluator.py` | Reescrito con metricas RAGAS |
| `.env.example` | Actualizar variables documentadas |
| `AGENTS.md` | Actualizar a arquitectura v2.0 |
| `README.md` | Actualizar comandos y estructura |

---

## 6. Convenciones y Estandares

### 6.1 Formato de Documentos Markdown

Cada archivo `.md` en `data/` debe incluir frontmatter YAML obligatorio:

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

### 6.2 Variables de Entorno

| Variable | Obligatoria | Default | Uso |
|---|---|---|---|
| `LITELLM_CHATBOT_KEY` | Si | — | Virtual key del proxy LiteLLM |
| `CHATBOT_API_KEY` | Si | — | Protege `/admin/refresh` |
| `ALLOWED_ORIGINS` | No | `localhost:5173` | Origenes CORS (separados por coma) |
| `UVICORN_RELOAD` | No | `false` | Hot-reload para desarrollo |
| `LOG_LEVEL` | No | `INFO` | Nivel de logging Python |
| `DAILY_REQUEST_LIMIT` | No | `100` | Limite diario por IP |
| `RATE_LIMIT_PER_MINUTE` | No | `20` | Limite por minuto por IP |
| `SESSION_TTL_SECONDS` | No | `600` | TTL de sesion |
| `GROQ_API_KEY` | Solo tests | — | Juez LLM para evaluador |

### 6.3 Codigo

- Type hints en todas las funciones publicas
- Docstrings en formato Google style
- Sin `print()` — usar `logging`
- Sin hardcodeo de valores que puedan ser variables de entorno

---

## 7. Fuera del Alcance (Explicito y Justificado)

| Exclusion | Justificacion |
|---|---|
| Procesamiento multimodal | Fuera del proposito del portafolio |
| Watchdog / auto-ingesta | Complejidad innecesaria para 7 documentos |
| Migracion a Qdrant/Milvus | Viola restriccion de recursos; ChromaDB es suficiente |
| Clasificador de intents / SemanticRouter | Causa raiz de la rigidez; eliminado por arquitectura |
| Maquina de estados de contexto | Reemplazada por historial simple de LangChain |
| Inyeccion programatica de idioma | Delegado al LLM via system prompt |
| Auditoria de interacciones | Fase futura opcional; no bloquea el MVP |
| Telemetria en archivos JSON | stdout + Docker es el estandar; si se requiere analitica avanzada, se disena en fase 2 |

---

## 8. Criterios de Aceptacion

### Funcionalidad Core

- [ ] `POST /chat` con pregunta sobre un proyecto → respuesta con fuentes correctas
      en >=90% de casos del banco de pruebas
- [ ] Pregunta out-of-scope → respuesta de declinacion sin alucinar
- [ ] Prompt injection → respuesta de declinacion (latencia <50ms indica pre-filtro regex)
- [ ] Pregunta en ingles → respuesta en ingles fluido
- [ ] Pregunta en frances → respuesta en frances fluido
- [ ] Pregunta de seguimiento (misma sesion) → el chatbot recuerda el contexto previo
- [ ] Sesion expirada (>10 min) → el chatbot responde sin contexto previo

### Operaciones

- [ ] `GET /health` reporta estado de ChromaDB y LiteLLM con campos individuales
- [ ] `GET /docs` muestra OpenAPI/Swagger funcional con todos los endpoints
- [ ] Anadir un nuevo `.md` a `data/proyectos/` y ejecutar `bash update_knowledge.sh`
      incorpora el conocimiento sin modificar codigo fuente
- [ ] `docker compose up` con solo `.env` configurado arranca el servicio

### Open-Source

- [ ] `data_example/` permite clonar el repo y ejecutar `docker compose up` con
      datos de ejemplo (sin exponer el portafolio real)
- [ ] `.env.example` contiene todas las variables necesarias con valores ficticios
- [ ] El repositorio no contiene API keys, secretos, ni informacion personal

### Calidad

- [ ] `python tests/evaluator.py` ejecuta >=30 casos de prueba y genera reporte
      con score numerico global
- [ ] `pytest tests/unit/` ejecuta >=10 tests unitarios en <5 segundos
- [ ] El banco de pruebas cubre: extraccion, razonamiento cruzado, seguridad,
      idiomas, memoria

### Rendimiento

- [ ] Latencia promedio de `POST /chat` < 3 segundos (incluyendo llamada LLM)
- [ ] `docker compose up` consume < 3 GB RAM en idle
- [ ] 2 sesiones concurrentes no degradan el tiempo de respuesta

---

## 9. Fases Futuras (No incluidas en este contrato)

1. **Auditoria de interacciones:** Registro persistente de conversaciones para
   analitica y deteccion de fallas. Requiere diseno de esquema de almacenamiento
   y politica de retencion.

2. **Dashboard de monitoreo:** Panel visual con metricas de uso, latencia,
   precision de recuperacion.

3. **Multimodalidad:** Procesamiento de imagenes, PDFs, o audio.

4. **Internacionalizacion avanzada:** Si el enfoque delegado al LLM resulta
   insuficiente para algun idioma, implementar deteccion programatica como
   fallback.

---

---

## 10. Referencias API — Documentacion Canonica de LangChain

Estas URLs son la fuente de verdad para la implementacion. El agente debe
consultarlas via `webfetch` antes de escribir cada modulo.

### Core — Patron RAG

| Componente | URL | Uso en este proyecto |
|---|---|---|
| RAG Tutorial | `https://python.langchain.com/docs/tutorials/rag/` | `create_retrieval_chain`, `create_stuff_documents_chain` |
| Message History | `https://python.langchain.com/docs/how_to/message_history/` | `RunnableWithMessageHistory` para sesiones |
| Chroma Integration | `https://python.langchain.com/docs/integrations/vectorstores/chroma/` | `Chroma()`, `as_retriever()`, metadata filter |

### Complementos

| Componente | URL | Uso en este proyecto |
|---|---|---|
| ChatOpenAI (LiteLLM) | `https://python.langchain.com/docs/integrations/chat/openai/` | `base_url="http://litellm:4000/v1"` |
| HuggingFace Embeddings | `https://python.langchain.com/docs/integrations/text_embedding/huggingfacehub/` | `all-MiniLM-L6-v2` |
| Text Splitters | `https://python.langchain.com/docs/how_to/#text-splitters` | `RecursiveCharacterTextSplitter`, `MarkdownHeaderTextSplitter` |
| Retrieval | `https://python.langchain.com/docs/how_to/#retrieval` | `as_retriever()`, `search_kwargs` |
| ChatPromptTemplate | `https://python.langchain.com/docs/how_to/#prompt-templates` | `from_messages()` system + human |
| Chroma API Reference | `https://reference.langchain.com/python/langchain-chroma/vectorstores/Chroma` | Metodos completos |

### Seguridad y Evaluacion

| Componente | URL | Uso en este proyecto |
|---|---|---|
| FastAPI CORS | `https://fastapi.tiangolo.com/tutorial/cors/` | `CORSMiddleware`, `allow_origins` |
| FastAPI API Key | `https://fastapi.tiangolo.com/tutorial/security/api-key-header/` | `APIKeyHeader` para `/admin/refresh` |
| SlowAPI | `https://slowapi.readthedocs.io/` | `Limiter`, `@limiter.limit` |
| RAGAS | `https://docs.ragas.io/` | Triada: Context Relevance, Faithfulness, Answer Relevance |

---

> **Este contrato anula y reemplaza cualquier discusion previa sobre la
> arquitectura del proyecto. Cualquier cambio a estas decisiones debe
> documentarse como una enmienda con fecha y justificacion.**
