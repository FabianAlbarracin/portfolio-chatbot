import os
import shutil
import re
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DATA_PATH = "/app/data"
DB_PATH = "/app/data/chroma_db"


def extract_project_metadata(content: str):
    lines = content.split("\n")

    title = None
    summary = None
    project_type = None

    # 🔹 Extraer título
    for line in lines:
        clean_line = line.strip().replace("*", "")
        if "Proyecto:" in clean_line:
            title = clean_line.replace("Proyecto:", "").strip()
            break

    # 🔹 Extraer sección ### Tipo
    capture_type = False
    type_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("### Tipo"):
            capture_type = True
            continue

        if capture_type:
            if stripped.startswith("###"):
                break
            if stripped:
                type_lines.append(stripped)

    if type_lines:
        project_type = " ".join(type_lines)[:300]

    # 🔹 Fallback summary (primer párrafo después del título)
    if not project_type:
        paragraph_lines = []
        capture = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if capture:
                    break
                continue

            if title and title in line:
                capture = True
                continue

            if capture:
                paragraph_lines.append(stripped)

        if paragraph_lines:
            summary = " ".join(paragraph_lines[:3])[:300]

    return title, summary, project_type


def build_metadata_from_path(file_path, content):
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

    # 🔥 NUEVO: title + summary
    title, summary, project_type = extract_project_metadata(content)

    if title:
        metadata["title"] = title

    if project_type:
        metadata["project_type"] = project_type
    elif summary:
        metadata["summary"] = summary

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
        content = doc.page_content
        metadata = build_metadata_from_path(doc.metadata["source"], content)
        doc.metadata.update(metadata)
        documents.append(doc)

    # 🔹 Chunking profesional
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