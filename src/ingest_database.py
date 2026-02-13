import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DATA_PATH = "/app/data"
DB_PATH = "/app/data/chroma_db"


def build_metadata_from_path(file_path):
    normalized = file_path.replace("\\", "/")
    parts = normalized.split("/")

    metadata = {}

    if "proyectos" in parts:
        metadata["category"] = "project"
        index = parts.index("proyectos")
        metadata["domain"] = parts[index + 1] if len(parts) > index + 1 else "general"

    elif "educacion" in parts:
        metadata["category"] = "education"
        metadata["domain"] = "general"

    elif "perfil" in parts:
        metadata["category"] = "profile"
        metadata["domain"] = "general"

    else:
        metadata["category"] = "general"
        metadata["domain"] = "general"

    metadata["source"] = os.path.basename(file_path).replace(".md", "")
    return metadata


def create_vector_db():
    print("🔄 Iniciando nueva ingesta optimizada...")

    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: {DATA_PATH} no existe.")
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
        print("⚠️ No se encontraron archivos .md.")
        return

    print(f"📄 Documentos cargados: {len(raw_documents)}")

    documents = []
    for doc in raw_documents:
        metadata = build_metadata_from_path(doc.metadata["source"])
        doc.metadata.update(metadata)
        documents.append(doc)

    # 🔥 NUEVO CHUNKING PROFESIONAL
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1100,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n# ", "\n\n", "\n", ". "],
    )

    chunks = text_splitter.split_documents(documents)
    print(f"✂️ Total chunks generados: {len(chunks)}")

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if os.path.exists(DB_PATH):
        print("🗑️ Eliminando base anterior...")
        shutil.rmtree(DB_PATH)

    print("💾 Creando nueva base vectorial...")

    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_PATH,
    )

    print("🚀 Ingesta completada correctamente.")


if __name__ == "__main__":
    create_vector_db()