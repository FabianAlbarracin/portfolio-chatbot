import os
import frontmatter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

class VectorStore:
    def __init__(self):
        print("🗄️ Inicializando Almacén Vectorial y Catálogo...")
        # Ajustamos la ruta porque ahora estamos dentro de src/services/
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_path = os.path.join(base_dir, "../../data")

        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.db = Chroma(
            persist_directory=os.path.join(self.data_path, "chroma_db"),
            embedding_function=self.embedding_model,
        )

        self.entity_catalog = self._build_entity_catalog()

    def _build_entity_catalog(self):
        catalog = {}
        for root, _, files in os.walk(self.data_path):
            if "chroma_db" in root:
                continue
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            parsed = frontmatter.load(f)
                            ent_name = parsed.metadata.get("entity_name")
                            desc = parsed.metadata.get("description")
                            ent_type = parsed.metadata.get("entity_type", "general")

                            if ent_name and desc:
                                catalog[ent_name] = {"desc": desc, "type": ent_type}
                    except Exception as e:
                        print(f"   [!] Error leyendo {file}: {e}")
        return catalog

    def retrieve_context(self, query: str, entities: list = []) -> str:
        """Busca en ChromaDB y formatea los bloques de contexto."""

        # Aumentamos agresivamente los valores de 'k' para evitar que se queden fragmentos por fuera
        if not entities:
            docs = self.db.similarity_search(query, k=10)
        elif len(entities) == 1:
            # k=10 asegura que traiga casi todo el documento de un solo proyecto
            docs = self.db.similarity_search(query, k=10, filter={"entity_name": entities[0]})
        else:
            # k=25 asegura que haya espacio suficiente para los chunks de TODOS los proyectos
            docs = self.db.similarity_search(query, k=25, filter={"entity_name": {"$in": entities}})

        if not docs:
            return "No hay información documentada sobre esta consulta específica."

        context_blocks = []
        for doc in docs:
            entidad = doc.metadata.get("entity_name", "DESCONOCIDO").upper()
            bloque_etiquetado = (
                f"=== INICIO CONTEXTO: {entidad} ===\n"
                f"{doc.page_content}\n"
                f"=== FIN CONTEXTO: {entidad} ==="
            )
            context_blocks.append(bloque_etiquetado)

        return "\n\n".join(context_blocks)