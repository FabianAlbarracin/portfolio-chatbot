import os
import re
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class ChatbotRAG:
    def __init__(self):
        print("⚙️  Inicializando motor RAG con Router y Memoria...")

        self.llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY"),
        )

        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.db = Chroma(
            persist_directory="/app/data/chroma_db",
            embedding_function=self.embedding_model,
        )

        # 🧠 MEMORIA A CORTO PLAZO (Guarda las últimas interacciones)
        self.chat_history = []
        print("✅ Base de datos, Router y Memoria listos.")

    def contextualize_query(self, query):
        """
        Si hay historial, reescribe la pregunta para que tenga contexto.
        """
        if not self.chat_history:
            return query  # Si es la primera pregunta, pasa directo

        history_str = "\n".join(
            [f"Usuario: {q}\nBot: {a}" for q, a in self.chat_history[-1:]]
        )

        prompt_final = f"""
{system_role}

### REGLAS DE ORO PARA ESTA RESPUESTA:
1. Si el usuario mezcla tecnologías de proyectos distintos, CORRÍGELO antes de responder.
2. NUNCA menciones nombres de archivos .md.
3. USA LISTAS (*) para enumerar proyectos o estudios.
4. HABLA SIEMPRE EN TERCERA PERSONA.

### CONTEXTO RECUPERADO:
{contexto}

Pregunta del usuario: {pregunta_reescrita}
"""
        # Prompt para reescribir la pregunta basándose en el historial
        prompt_template = f"""
        Dada la siguiente conversación y una pregunta de seguimiento, reescribe la pregunta de seguimiento para que sea una pregunta independiente que capture todo el contexto necesario.
        
        Historial de chat:
        {history_str}
        
        Pregunta de seguimiento: {query}
        
        Pregunta independiente:
        """

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            response = self.llm.invoke([HumanMessage(content=prompt_template)])
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Error contextualizando: {e}")
            return query  # En caso de error, usamos la original

    def detect_intent(self, query):
        print(f"🚦 [ROUTER] Analizando intención: '{query}'...")

        router_prompt = f"""
        Eres un clasificador de intenciones. Analiza la siguiente entrada del usuario y clasifícala en una de las siguientes categorías:
        
        - GREETING: Si el usuario saluda (hola, buenos días, estás ahí).
        - SHIELD: Si el usuario es grosero, tóxico o pregunta cosas sin sentido fuera de contexto profesional.
        - SEARCH_RAG: Si el usuario hace una pregunta técnica, sobre proyectos, experiencia o habilidades.
        
        Entrada: "{query}"
        
        Responde SOLO con la categoría (GREETING, SHIELD, SEARCH_RAG).
        """

        try:
            response = self.llm.invoke([HumanMessage(content=router_prompt)])
            decision = response.content.strip().upper()

            if "SEARCH_RAG" in decision:
                print("   ↳ Decisión: Pregunta Técnica -> 🚀 ACTIVANDO RAG")
                return None

            if "GREETING" in decision:
                print("   ↳ Decisión: Saludo -> 👋 SALUDO ESTÁNDAR")
                return "¡Hola! Estoy aquí para ayudarte con cualquier pregunta sobre los proyectos, habilidades o experiencia de Fabián Albarracín. ¿En qué te puedo ayudar hoy?"

            if "SHIELD" in decision:
                print("   ↳ Decisión: Tóxico/Sin sentido -> 🛡️ BLOQUEO DEFENSIVO")
                return "Soy un asistente técnico enfocado en el portafolio profesional de Fabián. Si tienes alguna pregunta sobre sus proyectos, stack tecnológico o experiencia, estaré encantado de responder."

            # Si el modelo alucina o dice otra cosa, por seguridad enviamos a RAG
            print(
                f"   ↳ Decisión ambigua ('{decision}') -> 🛡️ Forzando RAG por seguridad"
            )
            return None

        except Exception as e:
            print(f"⚠️ Error en Router: {e}")
            return None

    def get_response(self, query):
        # --- PASO 0: FILTRO SEMÁNTICO (Router y Escudo) ---
        quick_answer = self.detect_intent(query)
        if quick_answer:
            return quick_answer

        # --- PASO 1: REESCRITURA CON MEMORIA ---
        standalone_query = self.contextualize_query(query)
        if standalone_query != query:
            print(f"🧠 [MEMORIA] Pregunta reescrita a: '{standalone_query}'")

        # --- PASO 2: RECUPERACIÓN (Usando la pregunta reescrita) ---
        print(f"\n🔎 Buscando información en ChromaDB...")
        try:
            docs = self.db.similarity_search(standalone_query, k=8)
        except Exception as e:
            return f"Error conectando con la base de datos: {e}"

        if not docs:
            return "No tengo esa información en la documentación técnica actual."

        context_text = "\n\n---\n\n".join([d.page_content for d in docs])

        # --- PASO 3: CONSTRUCCIÓN DEL PROMPT ESTRATÉGICO ---
        # Cargar System Role con ruta absoluta para robustez
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        role_path = os.path.join(base_dir, "config", "system_role.md")
        try:
            with open(role_path, "r", encoding="utf-8") as f:
                system_role = f.read()
        except Exception:
            system_role = "Eres un asistente técnico útil y preciso."

        # Inicializar la lista de mensajes con el Rol del Sistema
        messages = [SystemMessage(content=system_role)]

        # Inyectamos las últimas interacciones para mantener el hilo
        for old_q, old_a in self.chat_history[-2:]:
            messages.append(HumanMessage(content=old_q))
            messages.append(AIMessage(content=old_a))

     
        final_prompt = f"""
        <contexto>
        {context_text}
        </contexto>

        <pregunta_usuario>
        {query}
        </pregunta_usuario>

        INSTRUCCIONES DE COMPORTAMIENTO:

        - Al responder sobre habilidades técnicas, DEBES incluir tanto la formación académica/certificaciones (mencionando instituciones y horas) como los proyectos prácticos de forma equilibrada."
        - Si el usuario pregunta "¿Quién eres?" o sobre el chatbot, explica que eres el Asistente del Portafolio de Fabián y utiliza los datos técnicos del archivo 'Portfolio_RAG_Assistant.md' para explicar cómo funcionas (RAG, Groq, ChromaDB).
        - Antes de decir "No tengo esa información", verifica si la respuesta está implícita en los cursos o hitos del <contexto>.
        - Eres el asistente del portafolio de Fabián. NO eres un generador de código. Si el usuario te pide programar, hacer scripts o tareas, declina amablemente explicando tu única función.
        - Si preguntan por experiencia en tecnologías que no están en el <contexto> (como Node.js, AWS, etc.), responde directamente que esa tecnología no forma parte del perfil o proyectos actuales de Fabián.
        - Si asocian TradeHUB con Python, SQL o Docker, aclara que es un proyecto Low-Code (AppSheet).
        - Si la información no está en el <contexto>, di: "No tengo esa información en la documentación técnica actual."

        ⛔ REGLA DE FORMATO CRÍTICA: Tienes estrictamente prohibido usar subtítulos, títulos en mayúsculas o dividir la respuesta en secciones. Escribe un solo párrafo fluido y natural. Responde directamente.

        Respuesta:
        """
        messages.append(HumanMessage(content=final_prompt))

        # --- PASO 4: GENERACIÓN ---
        print("\n🤖 Enviando a Groq (Llama 3)...")
        response = self.llm.invoke(messages)

        # --- PASO 5: FILTRO ANTI-MULETILLAS (REGEX MODO DIOS) ---
        final_text = response.content.strip()

        # Usamos Regex para eliminar CUALQUIER frase que empiece con "Según...", "Basado...", etc.
        patron_muletillas = r"^(?:\*\*?)?(?:Según|Basado en|En base a|De acuerdo con|Con base en)[^,:\n]+[,:\n]?\s*"
        final_text = re.sub(
            patron_muletillas, "", final_text, flags=re.IGNORECASE
        ).strip()

        # Eliminamos el subtítulo "Respuesta:" si Llama 3 se pone terco
        final_text = re.sub(
            r"^(?:\*\*?)?(?:Respuesta|Resposta|Rta):?(?:\*\*?)?\s*",
            "",
            final_text,
            flags=re.IGNORECASE,
        ).strip()

        # Aseguramos mayúscula inicial
        if final_text:
            final_text = final_text[0].upper() + final_text[1:]

        # --- PASO 6: GUARDAR EN MEMORIA ---
        self.chat_history.append((query, final_text))
        if len(self.chat_history) > 4:
            self.chat_history.pop(0)

        return final_text
