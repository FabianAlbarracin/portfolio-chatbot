import os
import shutil
import frontmatter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# -----------------------------
# Paths (Ajustados para src/pipelines/)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "../../data")
DB_PATH = os.path.join(DATA_PATH, "chroma_db")

def create_vector_db():
    print("🔄 Iniciando pipeline ETL offline para ChromaDB...")

    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: El directorio {DATA_PATH} no existe.")
        return

    loader = DirectoryLoader(
        DATA_PATH,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True},
        recursive=True,
    )

    raw_documents = loader.load()
    if not raw_documents:
        print("⚠️ No se encontraron archivos .md en data/.")
        return

    print(f"📄 Documentos crudos leídos: {len(raw_documents)}")

    documents = []
    for doc in raw_documents:
        try:
            parsed_file = frontmatter.loads(doc.page_content)

            if not parsed_file.metadata or 'entity_name' not in parsed_file.metadata:
                print(f"⚠️ Saltando {doc.metadata.get('source')}: Sin Frontmatter válido.")
                continue

            doc.page_content = parsed_file.content
            doc.metadata.update(parsed_file.metadata)
            documents.append(doc)
            print(f"✅ Procesado: {parsed_file.metadata.get('entity_name')} ({parsed_file.metadata.get('entity_type')})")

        except Exception as e:
            print(f"❌ Error procesando {doc.metadata.get('source')}: {e}")

    # 🔹 Chunking ajustado al límite real de all-MiniLM-L6-v2 (máx 256 tokens ~ 800 caracteres)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n# ", "\n\n", "\n", ". "],
    )

    raw_chunks = text_splitter.split_documents(documents)

    # 🔹 CORRECCIÓN CRÍTICA: Inyección de Contexto (Metadata Prepending)
    chunks = []
    for chunk in raw_chunks:
        entidad = chunk.metadata.get('entity_name', 'Portafolio')
        # Obligamos al modelo matemático a "leer" a qué proyecto pertenece este texto
        chunk.page_content = f"Contexto de {entidad}:\n{chunk.page_content}"
        chunks.append(chunk)

    print(f"✂️ Total chunks listos para vectorizar: {len(chunks)}")

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if os.path.exists(DB_PATH):
        print("🗑️ Eliminando base vectorial anterior para evitar colisiones...")
        shutil.rmtree(DB_PATH)

    print("💾 Vectorizando e indexando en ChromaDB...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_PATH,
    )
    print("🚀 Pipeline ETL completado. Base de datos lista para producción.")

if __name__ == "__main__":
    create_vector_db()