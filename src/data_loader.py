import os

def load_portfolio_data(data_folder):
    """
    Carga los archivos MD.
    IMPORTANTE: 'general' ya no es la suma de todo. Es solo el Perfil para ser rápido.
    """
    topics = {}
    
    if not os.path.exists(data_folder):
        return {"general": "Error: Carpeta data no encontrada"}

    # 1. Cargamos cada archivo individualmente
    for filename in os.listdir(data_folder):
        if filename.endswith(".md"):
            try:
                path = os.path.join(data_folder, filename)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    name_key = filename.lower()
                    # Guardamos el archivo con su nombre clave
                    topics[name_key] = f"\n=== DOCUMENTO: {filename} ===\n{content}"
            except Exception as e:
                print(f"Error cargando {filename}: {e}")

    # 2. Definimos qué es el contexto "general" (LIGERO)
    # Buscamos si existe un archivo de perfil o resumen
    clave_perfil = next((k for k in topics if "perfil" in k or "profile" in k or "resume" in k), None)
    
    if clave_perfil:
        # Si existe Perfil.md, ese es nuestro contexto general
        topics["general"] = topics[clave_perfil]
    else:
        # Si no, creamos un contexto general sintético (muy ligero)
        topics["general"] = """
        === RESUMEN GENERAL ===
        Este es el portafolio de Fabian.
        Contiene proyectos de:
        - Desarrollo de Chatbots (RAG, LLMs)
        - Sistemas de Inventario (TradeHub)
        - Telemetría y IoT
        
        (Si el usuario pregunta detalles específicos, intenta derivarlo al tema correcto).
        """
        
    return topics

def load_system_instruction(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Eres un asistente útil."