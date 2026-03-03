import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

class LLMGenerator:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.1-8b-Instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY"),
        )

    def generate(self, session: dict, context_text: str, query: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        system_role_path = os.path.join(base_dir, "../../config/system_role.md")

        try:
            with open(system_role_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "Eres un asistente técnico estricto. Responde solo con el contexto."

        history_block = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in session["history"][-4:]]) if session["history"] else "Ninguno"

        detected_lang = session.get("last_detected_lang", "es")[:2]
        lang_map = {"en": "INGLÉS", "es": "ESPAÑOL", "fr": "FRANCÉS", "pt": "PORTUGUÉS"}
        target_lang = lang_map.get(detected_lang, "el idioma de la pregunta")

        final_prompt = f"""
        You are a strict technical translator and assistant.
        CRITICAL INSTRUCTION: The user is speaking in {target_lang}. You MUST read the Spanish context below, but write your ENTIRE response in {target_lang}.

        === HISTORIAL RECIENTE ===
        {history_block}

        === CONTEXTO DE DOCUMENTOS (ESPAÑOL) ===
        {context_text}

        === PREGUNTA DEL USUARIO ===
        {query}

        INSTRUCCIONES DE GENERACIÓN:
        1. Responde a la PREGUNTA basándote ÚNICAMENTE en el CONTEXTO.
        2. Usa el HISTORIAL solo para entender referencias.
        3. Ve directo al grano, sin saludos iniciales.
        4. TRADUCE TODO AL {target_lang.upper()}.
        5. PROHIBICIÓN: NUNCA uses frases como "Based on the provided context" o "Aquí tienes la información".
        6. FRENO ESTRICTO: NO generes preguntas de seguimiento. NO simules una conversación contigo mismo. Detén tu generación inmediatamente después de responder los datos solicitados.

        RESPONSE IN {target_lang.upper()}:
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=final_prompt),
        ]

        response = self.llm.invoke(messages)
        return response.content.strip()