# Documentación Técnica: Portfolio RAG Assistant

## 1. Visión General e Identidad
El **Portfolio RAG Assistant** es el asistente virtual técnico diseñado específicamente para responder preguntas sobre el perfil profesional, proyectos y experiencia de Fabián Albarracín.

**Infraestructura de Despliegue:**
La arquitectura está dividida. El motor lógico, el orquestador y la base de datos vectorial se ejecutan localmente en el **Home Lab** de Fabián (un servidor Mac Mini con Ubuntu), dentro de un contenedor Docker aislado. Por otro lado, la inferencia del modelo de lenguaje se delega a la nube mediante API.

## 2. Flujo de Funcionamiento (Pipeline RAG)
El sistema sigue una arquitectura de Generación Aumentada por Recuperación (RAG) estructurada en 4 pasos secuenciales:

1.  **Recepción (Input):** El motor principal (`main.py` / `llm_engine.py`) recibe la consulta textual del usuario y la clasifica semánticamente.
2.  **Recuperación Vectorial (Retrieval):**
    * El sistema utiliza **ChromaDB** para buscar en la base de conocimiento local estructurada.
    * Se comparan los embeddings de la pregunta con los vectores almacenados para recuperar los 3 fragmentos de texto con mayor similitud semántica.
3.  **Construcción del Prompt (Augmentation):**
    * El orquestador ensambla una instrucción estricta (System Role) junto con el historial de la conversación (Memoria).
    * Se inyecta el contexto técnico recuperado de ChromaDB, obligando al sistema a responder exclusivamente basándose en esos datos.
4.  **Generación (Inference):**
    * El paquete de datos final se envía a **Groq Cloud**, donde el modelo **Llama 3** procesa la información.
    * El modelo genera la respuesta técnica final que se devuelve a la interfaz del usuario.

## 3. Stack Tecnológico (Componentes Core)
El stack tecnológico del Portfolio RAG Assistant está compuesto por:

* **Lenguaje Base:** Python 3.10.
* **Modelo de Lenguaje (LLM):** Llama 3.1 8B Instant (ejecutado vía Groq).
* **Base de Datos Vectorial:** ChromaDB (Almacenamiento local persistente).
* **Modelo de Embeddings:** HuggingFace (`all-MiniLM-L6-v2`).
* **Orquestador:** LangChain.
* **Infraestructura y Redes:** Docker, Ubuntu Server Headless y Cloudflare Tunnels para exposición segura.

## 4. Filosofía de Ingeniería
Este proyecto evidencia competencias sólidas en **Full Cycle Development**, abarcando:
* **Ingeniería de Datos:** Creación de pipelines ETL para transformar Markdowns en vectores numéricos.
* **Backend Moderno:** Desarrollo de motores lógicos robustos en Python con manejo de memoria y enrutamiento semántico.
* **DevOps:** Containerización de entornos de Inteligencia Artificial en Linux.
* **Integración de IA:** Implementación avanzada de RAG, embeddings locales y Prompt Engineering defensivo.