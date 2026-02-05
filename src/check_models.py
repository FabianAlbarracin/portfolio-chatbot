import os
from dotenv import load_dotenv
from google import genai

# Cargar API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: No tienes API Key en .env")
else:
    print(f"Probando conexión con Key: {api_key[:5]}...*****")
    try:
        client = genai.Client(api_key=api_key)
        print("\n--- LISTA BRUTA DE MODELOS ---")
        
        # Iteramos e imprimimos directamente el nombre
        for m in client.models.list():
            # Algunos modelos vienen como "models/gemini-..." y otros solo el nombre
            print(f" -> {m.name}")

        print("\n-----------------------------------")
        print("Busca uno que diga 'gemini-1.5-flash' o 'gemini-2.0-flash'")

    except Exception as e:
        print(f"Error crítico: {e}")