import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

class LLMGenerator:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-Instant",
            temperature=0.0, # Mantenemos esto en 0 para evitar alucinaciones
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def generate(self, session: dict, context_text: str, query: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        system_role_path = os.path.join(base_dir, "../../config/system_role.md")

        # 1. Única fuente de verdad. Si no existe, fallamos con gracia.
        try:
            with open(system_role_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            print(f"❌ [FATAL ERROR] Archivo de rol no encontrado en: {system_role_path}")
            return "Error interno del servidor: Falta el archivo de configuración del asistente."

        # 2. Formatear el historial limpiamente
        history_block = "No hay historial previo."
        if session.get("history"):
            history_block = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in session["history"][-4:]])

        target_lang = session.get("last_detected_lang", "es")

        # 3. Inyección de datos
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