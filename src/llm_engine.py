from google import genai
from google.genai import types

class GeminiEngine:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        
        # CAMBIO FINAL: Usamos el alias genérico que apareció en tu lista.
        # Este alias apunta a la versión 1.5 Flash estable y gratuita.
        self.model_name = "gemini-flash-latest"

    def generate_response(self, system_instruction, context, user_query):
        try:
            prompt_completo = f"""
            {system_instruction}

            === CONTEXTO OBLIGATORIO ===
            {context}
            """

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=prompt_completo,
                    temperature=0.0,
                )
            )
            
            return response.text

        except Exception as e:
            return f"Error del sistema: {str(e)}"