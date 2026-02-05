import os
from pathlib import Path

class ResourceLoader:
    def __init__(self):
        # Define las rutas relativas
        self.base_path = Path(__file__).resolve().parent.parent
        self.config_path = self.base_path / "config"
        self.data_path = self.base_path / "data"

    def _read_file(self, filepath: Path) -> str:
        if filepath.exists():
            return filepath.read_text(encoding='utf-8').strip()
        return ""

    def get_system_instructions(self) -> str:
        role = self._read_file(self.config_path / "system_role.md")
        security = self._read_file(self.config_path / "security_rules.md")
        return f"{role}\n\n{security}"

    def get_context(self) -> str:
        context_text = ""
        # Busca todos los archivos .md en la carpeta data
        for file in self.data_path.glob("*.md"):
            content = self._read_file(file)
            context_text += f"\n--- INFORMACIÓN DE {file.name} ---\n{content}\n"
        return context_text