import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

class SemanticRouter:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-Instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY"),
        ).bind(response_format={"type": "json_object"})

    def route_query(self, query: str, history: list, entity_catalog: dict) -> dict:
        if not entity_catalog:
            return {"intent": "NONE", "entities": [], "detected_language": "es"}

        menu_options = "\n".join([f"- [{ent}] ({data['type']}): {data['desc']}" for ent, data in entity_catalog.items()])
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-2:]]) if history else "Ninguno"

        router_prompt = f"""
        Eres un enrutador analítico. Tu única función es leer la pregunta del usuario y devolver un JSON.

        FORMATO DE SALIDA ESTRICTO:
        {{
            "intent": "CATALOGO" o "GREETING" o "BOT_IDENTITY" o "OUT_OF_SCOPE",
            "entities": ["id_del_proyecto"],
            "detected_language": "es" o "en"
        }}

        CATÁLOGO DISPONIBLE:
        {menu_options}

        HISTORIAL RECIENTE:
        {history_str}

        PREGUNTA DEL USUARIO: "{query}"

        REGLAS:
        1. Si pregunta por un proyecto del catálogo, intent es "CATALOGO" y en entities pon el ID exacto.
        2. Si saluda, intent es "GREETING".
        3. Si pregunta quién eres, intent es "BOT_IDENTITY".
        4. Detecta el idioma en ISO 639-1 (es, en, fr).
        """

        try:
            response = self.llm.invoke([SystemMessage(content=router_prompt)])
            decision = json.loads(response.content.strip())

            # Validación de seguridad para que ChromaDB no falle con IDs inventados
            valid_entities = [e for e in decision.get("entities", []) if e in entity_catalog]
            decision["entities"] = valid_entities

            # Mantenemos retrocompatibilidad con el orquestador
            decision["translated_query"] = query

            return decision
        except Exception as e:
            print(f"⚠️ [ROUTER ERROR] Fallo en clasificación: {e}")
            return {"intent": "NONE", "entities": [], "detected_language": "es"}