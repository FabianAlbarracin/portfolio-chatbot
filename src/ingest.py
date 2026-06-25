import os
import logging
import frontmatter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_PATH, "chroma_db")


def create_vector_db() -> None:
    logger.info("Iniciando pipeline ETL offline estructurado para ChromaDB...")

    if not os.path.exists(DATA_PATH):
        logger.error("El directorio %s no existe.", DATA_PATH)
        return

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " "],
    )

    loader = DirectoryLoader(
        DATA_PATH,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True},
        recursive=True,
    )

    raw_documents = loader.load()
    if not raw_documents:
        logger.warning("No se encontraron archivos .md en data/.")
        return

    logger.info("Documentos crudos leidos: %d", len(raw_documents))

    final_chunks = []

    for doc in raw_documents:
        try:
            parsed_file = frontmatter.loads(doc.page_content)

            if not parsed_file.metadata or 'entity_name' not in parsed_file.metadata:
                logger.warning("Saltando %s: Sin Frontmatter valido.", doc.metadata.get('source'))
                continue

            md_header_splits = markdown_splitter.split_text(parsed_file.content)

            for split in md_header_splits:
                split.metadata.update(parsed_file.metadata)
                split.metadata.update(doc.metadata)

                sub_splits = text_splitter.split_documents([split])

                for sub_split in sub_splits:
                    entidad = sub_split.metadata.get('entity_name', 'Portafolio')
                    seccion = sub_split.metadata.get('Header 3',
                                sub_split.metadata.get('Header 2',
                                    sub_split.metadata.get('Header 1', 'General')))

                    sub_split.page_content = f"[Entidad: {entidad} | Seccion: {seccion}]\n{sub_split.page_content}"
                    final_chunks.append(sub_split)

            logger.info("Procesado y fragmentado semanticamente: %s", parsed_file.metadata.get('entity_name'))

        except Exception as e:
            logger.error("Error procesando %s: %s", doc.metadata.get('source'), e)

    logger.info("Total chunks listos para vectorizar: %d", len(final_chunks))

    logger.info("Conectando a la coleccion persistente en ChromaDB...")
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = Chroma(
        embedding_function=embedding_model,
        persist_directory=DB_PATH
    )

    logger.info("Purgando vectores antiguos preservando el UUID de la coleccion...")
    coleccion_actual = vector_store.get()
    if coleccion_actual and coleccion_actual["ids"]:
        vector_store.delete(ids=coleccion_actual["ids"])

    logger.info("Insertando %d vectores actualizados...", len(final_chunks))
    vector_store.add_documents(documents=final_chunks)

    logger.info("Pipeline ETL completado.")


if __name__ == "__main__":
    create_vector_db()
