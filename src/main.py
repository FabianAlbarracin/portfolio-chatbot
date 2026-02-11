import os
import sys
from dotenv import load_dotenv
from llm_engine import ChatbotRAG

# Cargar variables de entorno
load_dotenv()

def main():
    print("--------------------------------------------------")
    print("🤖 Chatbot RAG de Portafolio (Router Activado) - Iniciando...")
    print("--------------------------------------------------")

    # Verificar API Key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: No se encontró GROQ_API_KEY en las variables de entorno.")
        print("   Asegúrate de tener el archivo .env configurado correctamente.")
        return

    try:
        # Instanciar el motor (Esto carga la DB en memoria, el LLM y el Router)
        bot = ChatbotRAG()
    except Exception as e:
        print(f"❌ Error crítico iniciando el bot: {e}")
        return

    print("\n💬 Sistema listo. Escribe 'salir' para terminar.")
    print("--------------------------------------------------")

    while True:
        try:
            user_input = input("\nTú: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("👋 ¡Hasta luego!")
                break
            
            if not user_input:
                continue

            # Obtener respuesta del motor (El método get_response ahora tiene el Router integrado)
            response = bot.get_response(user_input)
            
            print(f"\nBot: {response}")

        except KeyboardInterrupt:
            print("\n👋 Salida forzada.")
            break
        except Exception as e:
            print(f"❌ Error en la conversación: {e}")

if __name__ == "__main__":
    main()