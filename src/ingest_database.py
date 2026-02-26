import os
import shutil
import frontmatter # <-- Nueva librería
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
# (Mantén tus otros imports para ChatbotRAG aquí...)

# -----------------------------
# Paths
# -----------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data")
DB_PATH = os.path.join(DATA_PATH, "chroma_db")

# -----------------------------
# Ingesta y creación de ChromaDB
# -----------------------------
def create_vector_db():
    print("🔄 Iniciando ingesta determinística con Frontmatter...")

    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: {DATA_PATH} no existe.")
        return

    loader = DirectoryLoader(
        DATA_PATH,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True},
        recursive=True,
    )

    raw_documents = loader.load()
    if not raw_documents:
        print("⚠️ No se encontraron archivos .md.")
        return

    print(f"📄 Documentos crudos cargados: {len(raw_documents)}")

    documents = []
    for doc in raw_documents:
        try:
            # 1. Parsear el archivo: Separa el YAML del Markdown
            parsed_file = frontmatter.loads(doc.page_content)

            # 2. Validar que el archivo tenga los metadatos mínimos
            if not parsed_file.metadata or 'entity_name' not in parsed_file.metadata:
                print(f"⚠️ Saltando {doc.metadata.get('source')}: No tiene Frontmatter válido.")
                continue

            # 3. Asignar solo el texto limpio (sin el YAML) al contenido
            doc.page_content = parsed_file.content

            # 4. Inyectar los metadatos del YAML a los metadatos de LangChain
            doc.metadata.update(parsed_file.metadata)

            documents.append(doc)
            print(f"✅ Procesado: {parsed_file.metadata.get('entity_name')} ({parsed_file.metadata.get('entity_type')})")

        except Exception as e:
            print(f"❌ Error procesando {doc.metadata.get('source')}: {e}")

    # 🔹 Chunking profesional (Mantenemos tu configuración, es buena)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1100,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n# ", "\n\n", "\n", ". "],
    )

    # Al hacer split, LangChain hereda los metadatos a cada chunk automáticamente
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ Total chunks generados: {len(chunks)}")

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if os.path.exists(DB_PATH):
        print("🗑️ Eliminando base anterior para evitar duplicados...")
        shutil.rmtree(DB_PATH)

    print("💾 Creando nueva base vectorial estructurada...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_PATH,
    )
    print("🚀 Ingesta completada correctamente.")
# -----------------------------
# Chatbot RAG
# -----------------------------
class ChatbotRAG:
    def __init__(self):
        print("⚙️ Inicializando motor RAG híbrido profesional...")

        self.sessions = {}
        self.llm = ChatGroq(
            model="llama-3.1-8b-Instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY"),
        )

        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.db = Chroma(
            persist_directory=DB_PATH,
            embedding_function=self.embedding_model,
        )

        # Extraer títulos de todos los proyectos para fuzzy matching
        self.project_titles = self._load_project_titles()
        print("✅ Sistema listo.\n")

    def _load_project_titles(self):
        titles = []
        projects_path = os.path.join(DATA_PATH, "proyectos")
        for root, _, files in os.walk(projects_path):
            for f in files:
                if f.endswith(".md"):
                    file_path = os.path.join(root, f)
                    with open(file_path, "r", encoding="utf-8") as fd:
                        title, _, _ = extract_project_metadata(fd.read())
                        if title:
                            titles.append(title)
        return titles

    def normalize(self, text: str):
        return text.lower().strip()

    def similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    def _get_session(self, session_id: str):
        current_time = time.time()
        SESSION_TTL = 900  # 15 minutos

        expired_sessions = [
            sid
            for sid, data in self.sessions.items()
            if current_time - data["last_interaction"] > SESSION_TTL
        ]
        for sid in expired_sessions:
            del self.sessions[sid]

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "last_project": None,
                "last_interaction": current_time,
                "force_language": None,
            }

        self.sessions[session_id]["last_interaction"] = current_time
        return self.sessions[session_id]

    def _retrieve_context(self, query):
        # Placeholder: usar Chroma search real
        return "Contexto relevante simulado. En la implementación real se consultaría ChromaDB."

    def get_response(self, session_id: str, query: str) -> str:
        session = self._get_session(session_id)
        query_lower = query.lower()

        ambiguous_keywords = [
            "tecnologías", "tecnologia",
            "stack", "arquitectura",
            "base de datos", "infraestructura",
            "cómo funciona", "implementación",
            "detalles técnicos"
        ]

        # 🔹 Detectar proyecto explícitamente
        project_detected = None
        for title in self.project_titles:
            if any(word in query_lower for word in title.lower().split()):
                project_detected = title
                break
        if project_detected:
            session["last_project"] = project_detected

        # 🔹 Si ya hay proyecto activo y pregunta es ambigua → usar contexto
        if session["last_project"] and any(k in query_lower for k in ambiguous_keywords):
            contextual_query = f"""
Pregunta sobre el proyecto: {session['last_project']}
Pregunta específica del usuario: {query}
"""
            context_text = self._retrieve_context(contextual_query)
            return self.generate_answer(session, context_text, contextual_query)

        # 🔹 Flujo normal
        context_text = self._retrieve_context(query)
        return self.generate_answer(session, context_text, query)

    def generate_answer(self, session, context_text: str, query: str):
        language_instruction = f"Respond in {session['force_language']}." if session["force_language"] else """
Detect the language of the user's question and respond in that same language.
If unclear, default to Spanish.
"""
        system_prompt = f"""
You are a technical assistant specialized EXCLUSIVELY in the professional portfolio of Fabián Albarracín.

RULES:
1. Answer ONLY using the provided context.
2. Do not invent information.
3. Do not use external knowledge.
4. Always speak in third person.
5. {language_instruction}
6. Be structured and technical (maximum 5 points).

If the message is only a greeting, respond briefly greeting back and invite the user to ask about the portfolio.
If the message is a system check (e.g., "are you alive?"), respond briefly confirming operational status.
"""
        final_prompt = f"""
<context>
{context_text}
</context>

<question>
{query}
</question>

Answer:
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=final_prompt),
        ]
        response = self.llm.invoke(messages)
        return response.content.strip()


if __name__ == "__main__":
    create_vector_db()