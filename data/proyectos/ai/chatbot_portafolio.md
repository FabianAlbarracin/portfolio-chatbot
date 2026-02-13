**Proyecto: Portfolio RAG Assistant**

### Tecnologías

- **Lenguaje:** Python 3.10.
    
- **Orquestación:** LangChain.
    
- **Modelos LLM:** Llama 3.1 8B Instant (vía Groq Cloud API, Temperature 0.0).
    
- **Estrategia RAG:** Fragmentación semántica controlada (chunk_size y overlap ajustados), Similarity Search (Top-k optimizado).
    
- **Embeddings:** HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`).
    
- **Base de Datos Vectorial:** ChromaDB (Persistencia local).
    
- **Infraestructura:** Docker, Ubuntu Server (Headless).
    
- **Redes/Seguridad:** Cloudflare Tunnel, Gestión de secretos (.env).
    

### Tipo

Sistema de Asistencia Técnica basado en IA Generativa (RAG - Retrieval-Augmented Generation).

### Problema que resuelve

Necesidad de automatizar la respuesta a consultas técnicas sobre el perfil profesional y portafolio, garantizando precisión, eliminando alucinaciones y centralizando información dispersa en una interfaz conversacional capaz de mantener el contexto.

### Arquitectura / Implementación técnica

**Rol del desarrollador**
Responsable de la ingeniería completa del sistema: diseño del pipeline ETL para documentos, implementación de la lógica RAG en Python, configuración de la base de datos vectorial, ingeniería de prompts (System Roles) y orquestación de la infraestructura en Docker.

**Backend**
Implementado en **Python** con **LangChain** bajo un diseño modular que desacopla la capa de recuperación vectorial del motor de generación. El núcleo es la clase `ChatbotRAG`, que gestiona la lógica conversacional. Integra un **Router de Intenciones** basado en LLM para clasificar consultas (Greeting, Shield, Search_RAG) y optimizar costos/latencia. Incluye gestión de memoria a corto plazo para contextualizar preguntas de seguimiento.

**Base de datos**
Utiliza **ChromaDB** como almacén vectorial. Los documentos Markdown se procesan y convierten en embeddings vectoriales mediante el modelo `all-MiniLM-L6-v2`. La base de datos persiste localmente dentro del contenedor, asegurando privacidad y control de datos.

**Infraestructura**
Desplegado en un servidor local (**Home Lab**) con **Ubuntu Server** y **Docker**. La inferencia del modelo de lenguaje se realiza en la nube (**Groq**) para aprovechar la aceleración de hardware, mientras que la gestión de datos y lógica permanece on-premise. La exposición segura se gestiona mediante **Cloudflare Tunnel**. La seguridad se refuerza mediante el aislamiento del contenedor y la inyección de API Keys exclusivamente a través de variables de entorno.

**Integraciones**
- **Groq Cloud API:** Proveedor de inferencia para el modelo Llama 3.1.
- **HuggingFace:** Proveedor de modelos de embeddings locales.

**Flujo de datos**
1.  **Recepción:** El usuario envía una consulta textual.
2.  **Enrutamiento:** El sistema clasifica la intención (Saludo, Bloqueo o Consulta Técnica).
3.  **Contextualización:** Si es técnica, se reescribe la pregunta usando el historial de chat.
4.  **Recuperación:** Búsqueda de fragmentos relevantes en ChromaDB.
5.  **Generación:** Construcción del prompt (System Role + Contexto + Pregunta) y envío a Groq.
6.  **Respuesta:** Limpieza de formato y entrega al usuario.

### Funcionalidades clave

- **Sistema RAG (Retrieval-Augmented Generation):** Respuestas basadas estrictamente en documentación local.
    
- **Router de Intenciones:** Clasificación inteligente de entradas para evitar consumo innecesario de recursos en saludos o preguntas fuera de contexto.
    
- **Memoria Conversacional:** Capacidad de mantener el hilo de la conversación y entender referencias implícitas.
    
- **Ingeniería de Prompts Defensiva:** Reglas estrictas (System Role) para evitar suplantación de identidad y forzar el uso de tercera persona.
    
- **Limpieza de Output:** Post-procesamiento con Regex para eliminar muletillas generadas por el LLM.
    

### Resultados / Impacto

- Centralización del conocimiento técnico del portafolio en un agente interactivo.
    
- Reducción de alucinaciones mediante control estricto de contexto.
    
- Validación práctica de competencias en ingeniería de IA, Python y DevOps.
    
- Optimización de la precisión mediante evaluación cualitativa y ajustes iterativos en ingeniería de prompts.
    

### Limitaciones o mejoras futuras

- Dependencia de conexión a internet para la API de inferencia (Groq).
    
- Ventana de contexto limitada por el modelo Llama 3.1 8B.
    
- No incluye actualmente re-ranking ni búsqueda híbrida (BM25 + vectorial).
    
- El proceso de actualización de conocimiento requiere re-ingesta de documentos (no es tiempo real).