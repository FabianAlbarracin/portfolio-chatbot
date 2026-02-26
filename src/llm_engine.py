from langchain_core.messages import HumanMessage
from src.core.session_manager import SessionManager
from src.services.vector_store import VectorStore
from src.services.semantic_router import SemanticRouter
from src.services.llm_generator import LLMGenerator

class ChatbotRAG:
    def __init__(self):
        print("⚙️ Inicializando Arquitectura RAG Orquestada...")
        self.session_manager = SessionManager()
        self.vector_store = VectorStore()
        self.router = SemanticRouter()
        self.generator = LLMGenerator()
        print("✅ Motor RAG ensamblado y listo.\n")

    def get_response(self, session_id: str, query: str) -> str:
        # 1. Recuperar memoria (Hipocampo)
        session = self.session_manager.get_session(session_id)

        # 2. Enrutamiento Semántico y de Idioma
        routing_data = self.router.route_query(
            query,
            session["history"],
            self.vector_store.entity_catalog
        )
        intent = routing_data.get("intent", "NONE")
        entities = routing_data.get("entities", [])

        print(f"🧠 [ROUTER JSON NATIVO] Decisión: {routing_data}")

        session["last_detected_lang"] = routing_data.get("detected_language", "es")

        # ==========================================================
        # 🛡️ EARLY EXITS (Respuestas Estáticas Controladas)
        # ==========================================================
        static_response = None
        if intent == "BOT_IDENTITY":
            static_response = "Soy el asistente técnico de IA de este portafolio. Mi conocimiento proviene estrictamente de la documentación técnica, repositorios y archivos proporcionados por el autor original."
        elif intent == "GREETING":
            static_response = "Hola, soy el asistente técnico del portafolio. Puedo explicarte a detalle la arquitectura de los proyectos o la experiencia profesional. ¿Por dónde te gustaría empezar?"
        elif intent == "GIBBERISH":
            static_response = "No he logrado comprender tu mensaje. Si tienes alguna duda técnica, estaré encantado de ayudarte."
        elif intent == "PROFANITY":
            static_response = "Por favor, mantengamos un estándar de comunicación profesional."
        elif intent == "SYSTEM_CHECK":
            static_response = "Sistema en línea. Base vectorial y motor RAG operando correctamente."
        elif intent == "OUT_OF_SCOPE":
            static_response = "Soy un asistente de alcance estricto. Mi conocimiento se limita a la infraestructura, experiencia y proyectos de este portafolio."
        elif intent == "LIST_ALL_PROJECTS":
            proyectos = [
                data["desc"] for ent, data in self.vector_store.entity_catalog.items()
                if data.get("type") in ["project", "infrastructure"]
            ]
            lista_str = "\n".join([f"- {p}" for p in proyectos])
            static_response = f"Actualmente, el portafolio documenta los siguientes sistemas e infraestructura:\n{lista_str}\n\n¿Sobre cuál de estos deseas que profundice?"
        elif intent == "LIST_ALL_EDUCATION":
            intent = "CATALOGO"
            entities = ["formacion_academica"]

        # Traducción dinámica de la salida temprana
        if static_response:
            detected_lang = session.get("last_detected_lang", "es")[:2]
            if detected_lang != "es":
                translation_prompt = f"Traduce fielmente este texto al idioma con código '{detected_lang}'. Responde SOLO con la traducción, sin comillas, introducciones ni notas:\n\n{static_response}"
                static_response = self.generator.llm.invoke([HumanMessage(content=translation_prompt)]).content.strip()

            self.session_manager.update_history(session, query, static_response)
            return static_response

        # ==========================================================
        # 🔄 FLUJO RAG PROFUNDO
        # ==========================================================
        if intent == "CATALOGO" and entities:
            session["active_entities"] = entities
        active_entities = session.get("active_entities", [])

        # 3. Traducción para búsqueda en base de datos
        query_for_retrieval = routing_data.get("translated_query", query)

        # 4. Recuperar contexto vectorial (Bodeguero)
        context_text = self.vector_store.retrieve_context(query_for_retrieval, entities=active_entities)

        # 5. Generar respuesta final (Chef Ejecutivo)
        answer = self.generator.generate(session, context_text, query)

        # 6. Actualizar memoria y responder
        self.session_manager.update_history(session, query, answer)
        return answer