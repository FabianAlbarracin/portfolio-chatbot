import os
from dotenv import load_dotenv
from config_loader import ResourceLoader
from llm_engine import GeminiEngine

# Cargar variables de entorno (.env)
load_dotenv()

def main():
    # 1. Configuración
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No se encontró la GEMINI_API_KEY en el archivo .env")
        return

    # 2. Inicializar clases
    print("Iniciando sistema...")
    loader = ResourceLoader()
    bot = GeminiEngine(api_key)

    # 3. Cargar memoria (Solo se hace una vez al inicio)
    instrucciones = loader.get_system_instructions()
    contexto = loader.get_context()
    print("Sistema cargado. Escribe 'salir' para terminar.\n")

    # 4. Bucle de chat
    while True:
        pregunta = input("\nTú: ")
        if pregunta.lower() in ['salir', 'exit']:
            break
        
        respuesta = bot.generate_response(instrucciones, contexto, pregunta)
        print(f"Bot: {respuesta}")

if __name__ == "__main__":
    main()