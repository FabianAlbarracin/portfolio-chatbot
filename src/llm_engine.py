import os
import re
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage, SystemMessage


class ChatbotRAG:
    def __init__(self):
        print("⚙️ Inicializando motor RAG híbrido profesional...")

        self.llm = ChatGroq(
            model="llama-3.1-8b-Instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY"),
        )

        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.db = Chroma(
            persist_directory="/app/data/chroma_db",
            embedding_function=self.embedding_model,
        )

        print("✅ Sistema listo.\n")

    def normalize(self, text: str):
        return text.lower().strip()

    def get_all_sources(self):
        # Obtener lista única de sources
        collection = self.db.get()
        metadatas = collection["metadatas"]
        return list(set([m.get("source") for m in metadatas if m.get("source")]))

    def get_response(self, query: str) -> str:

        query_lower = self.normalize(query)

        # 🔵 1. LISTA DE PROYECTOS (estructural enriquecido)
        if "proyectos" in query_lower:
            collection = self.db.get()
            metadatas = collection["metadatas"]

            projects = {}

            for m in metadatas:
                if m.get("category") == "project":
                    source = m.get("source")
                    title = m.get("title", source)
                    descriptor = m.get("project_type") or m.get("summary", "")

                    if source not in projects:
                        projects[source] = {
                            "title": title,
                            "descriptor": descriptor
                        }

            if not projects:
                return "No hay proyectos documentados."

            response = "Proyectos documentados:\n\n"

            for p in sorted(projects.values(), key=lambda x: x["title"]):
                if p["descriptor"]:
                    response += f"- {p['title']}\n  {p['descriptor']}\n\n"
                else:
                    response += f"- {p['title']}\n"

            return response.strip()

        # 🔵 2. MATCH EXACTO POR NOMBRE DE SOURCE
        sources = self.get_all_sources()

        for source in sources:
            if source.lower() in query_lower:
                print(f"🎯 Coincidencia directa detectada: {source}")

                docs = self.db.get(where={"source": source})
                context_text = "\n\n".join(docs["documents"])

                return self.generate_answer(context_text, query)

        # 🔵 3. FALLBACK SEMÁNTICO
        print("🔎 Búsqueda semántica...")

        results = self.db.similarity_search(query, k=6)

        if not results:
            return "Esa información no está documentada en el portafolio."

        context_text = "\n\n---\n\n".join(
            [doc.page_content for doc in results]
        )

        return self.generate_answer(context_text, query)

    def generate_answer(self, context_text: str, query: str):

        system_prompt = """
        Eres un asistente técnico especializado EXCLUSIVAMENTE en el portafolio profesional de Fabián Albarracín.

        REGLAS:
        1. Responde SOLO usando información del contexto.
        2. No inventes información.
        3. No uses conocimiento externo.
        4. Responde en tercera persona.
        5. Sé estructurado y técnico (máximo 5 puntos).
        """

        final_prompt = f"""
        <contexto>
        {context_text}
        </contexto>

        <pregunta>
        {query}
        </pregunta>

        Respuesta:
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=final_prompt),
        ]

        response = self.llm.invoke(messages)
        return response.content.strip()