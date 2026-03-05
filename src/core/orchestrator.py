from src.core.session import SessionManager
from src.services.vector_db import VectorStore
from src.services.semantic_router import SemanticRouter
from src.services.llm_groq import LLMGenerator

class ChatbotOrchestrator:
    def __init__(self):
        print("⚙️ Inicializando Orquestador RAG...")
        self.session_manager = SessionManager()
        self.vector_store = VectorStore()
        self.router = SemanticRouter()
        self.generator = LLMGenerator()

    # Cambiamos la firma para que devuelva un diccionario en lugar de un string
    def get_response(self, session_id: str, query: str) -> dict:
        # 1. Recuperar memoria
        session = self.session_manager.get_session(session_id)

        # 2. Enrutamiento y extracción de entidades
        routing_data = self.router.route_query(
            query,
            session["history"],
            self.vector_store.entity_catalog
        )
        session["last_detected_lang"] = routing_data.get("detected_language", "es")

        intent = routing_data.get("intent", "NONE")
        entities = routing_data.get("entities", [])
        print(f"🧠 [ROUTER] Intención: {intent} | Entidades: {entities}")

        # Mantenemos las entidades activas en memoria si es una consulta de seguimiento
        if intent == "CATALOGO" and entities:
            session["active_entities"] = entities
        active_entities = session.get("active_entities", [])

        # 3. Recuperación Vectorial (AQUÍ ESTÁ EL CAMBIO MAGISTRAL)
        query_for_retrieval = routing_data.get("translated_query", query)
        if intent == "CATALOGO": query_for_retrieval += " tecnologías arquitectura características"

        # Le diremos a la base vectorial que nos devuelva una tupla (texto, lista_de_fuentes)
        retrieval_result = self.vector_store.retrieve_context(query_for_retrieval, entities=active_entities)

        # Validamos si vector_db ya fue actualizado para devolver la tupla
        if isinstance(retrieval_result, tuple):
            context_text, sources = retrieval_result
        else:
            context_text = retrieval_result
            sources = ["Actualizar vector_db.py para ver las fuentes"]

        # 4. Generación LLM
        answer = self.generator.generate(session, context_text, query)

        # 5. Actualizar memoria y responder (AQUÍ EMPAQUETAMOS LA RESPUESTA)
        self.session_manager.update_history(session, query, answer)

        # Devolvemos el diccionario que nuestro chat_router.py (y el script de pruebas) están esperando
        return {
            "answer": answer,
            "sources": sources
        }