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

        menu_options = ""
        for ent, data in entity_catalog.items():
            menu_options += f"- [{ent}] (Tipo: {data['type']}): {data['desc']}\n"

        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-2:]]) if history else "Ninguno"

        router_prompt = f"""
        Eres un enrutador multilingüe y analista de intenciones técnico.
        Tu salida debe ser UNICAMENTE un objeto JSON estrictamente válido.

        INSTRUCCIONES DE IDIOMA:
        1. Analiza la consulta en cualquier idioma (Inglés, Francés, etc.).
        2. Si la consulta NO está en español, escribe una traducción técnica al español en "translated_query".
        3. Identifica el código de idioma (es, en, fr, pt) y ponlo en "detected_language".

        FORMATO DE SALIDA (JSON):
        {{
            "intent": "VALOR",
            "entities": ["id1"],
            "translated_query": "Traducción al español solo si aplica",
            "detected_language": "en/es/fr"
        }}

        HISTORIAL RECIENTE:
        {history_str}

        CATÁLOGO DE DOCUMENTOS (ENTIDADES):
        {menu_options}

        ETIQUETAS DE SISTEMA:
        - GREETING: Saludos o presentaciones.
        - GIBBERISH: Cadenas sin sentido o ruido.
        - BOT_IDENTITY: Preguntas sobre quién eres o tu arquitectura.
        - LIST_ALL_PROJECTS: El usuario pide ver TODOS los proyectos.
        - LIST_ALL_EDUCATION: El usuario pide ver estudios de Fabián.

        REGLAS LÓGICAS:
        1. Si la intención es sobre el CATÁLOGO, usa "intent": "CATALOGO".
        2. Si es una ETIQUETA DE SISTEMA, usa el nombre de la etiqueta y entities [].
        3. SOLICITUDES GLOBALES (CRÍTICO): Usa "LIST_ALL_PROJECTS" SOLAMENTE si piden TODOS los proyectos. Si preguntan por un proyecto ESPECÍFICO, el intent DEBE SER "CATALOGO".
        4. SEGUIMIENTO (MEMORIA): Mantén el intent "CATALOGO" y usa entidades del HISTORIAL RECIENTE si es seguimiento.

        PREGUNTA: "{query}"
        """

        response = self.llm.invoke([SystemMessage(content=router_prompt)])
        raw_json = response.content.strip()

        try:
            decision = json.loads(raw_json)
            valid_entities = [e for e in decision.get("entities", []) if e in entity_catalog]
            decision["entities"] = valid_entities
            return decision
        except json.JSONDecodeError:
            print(f"⚠️ [ROUTER ERROR] Fallo crítico de parseo: {raw_json}")
            return {"intent": "NONE", "entities": [], "detected_language": "es"}