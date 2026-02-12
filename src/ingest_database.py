import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# --- CONFIGURACIÓN ---
DATA_PATH = "/app/data"
DB_PATH = "/app/data/chroma_db"

def create_vector_db():
    print("🔄 [INGESTA] Iniciando proceso...")

    # 1. VERIFICAR ARCHIVOS
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: La carpeta {DATA_PATH} no existe.")
        return

    print(f"📂 Buscando archivos Markdown en: {DATA_PATH}")
    # MEJORA: Forzamos la autodección de UTF-8 para proteger acentos y 'ñ' al cruzar sistemas operativos
    loader = DirectoryLoader(
        DATA_PATH, 
        glob="*.md", 
        loader_cls=TextLoader, 
        loader_kwargs={'autodetect_encoding': True}
    )
    documents = loader.load()
    
    if not documents:
        print("⚠️  No se encontraron archivos .md. Asegúrate de haber copiado tus archivos a data/.")
        return

    print(f"✅ Se cargaron {len(documents)} documentos.")

  # 2. FRAGMENTAR (CHUNKING) - OPTIMIZADO
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,        # Un poco más pequeño para mayor precisión semántica
        chunk_overlap=200,     # Mayor solapamiento para no cortar cursos por la mitad
        separators=["\n## ", "\n### ", "\n# ", "\n", ". ", " "] # Añadido ### para tus listas
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"✂️  Documentos divididos en {len(chunks)} fragmentos útiles.")

    # 3. EMBEDDINGS (TEXTO -> NÚMEROS)
    print("🧠 Cargando modelo de embeddings local (HuggingFace)...")
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4. GUARDAR EN CHROMA
    if os.path.exists(DB_PATH):
        print("🗑️  Limpiando base de datos anterior...")
        shutil.rmtree(DB_PATH)

    print("💾 Creando y guardando vectores en disco...")
    
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_PATH
    )
    
    print(f"🚀 ¡ÉXITO! Base de datos guardada en: {DB_PATH}")

if __name__ == "__main__":
    create_vector_db()