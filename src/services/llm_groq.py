import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

class LLMGenerator:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-Instant",
            temperature=0.3, # Subimos a 0.3 para darle un poco más de naturalidad
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def generate(self, session: dict, context_text: str, query: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        system_role_path = os.path.join(base_dir, "../../config/system_role.md")

        try:
            with open(system_role_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "Eres el asistente técnico de Fabián. Responde usando el contexto provisto."

        # Formatear el historial limpiamente
        history_block = "No hay historial previo."
        if session.get("history"):
            history_block = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in session["history"][-4:]])

        target_lang = session.get("last_detected_lang", "es")

        # El prompt final ahora solo inyecta datos, no da órdenes de comportamiento
        final_prompt = f"""
[DATA INJECTION]
LANGUAGE_TARGET: {target_lang}

<historial_conversacion>
{history_block}
</historial_conversacion>

<contexto_documentos>
{context_text}
</contexto_documentos>

PREGUNTA DEL USUARIO: {query}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=final_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"❌ [LLM ERROR] Falla en la generación: {e}")
            return "Lo siento, estoy experimentando intermitencias en mi motor de inferencia."