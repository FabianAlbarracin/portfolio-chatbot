import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LITELLM_CHATBOT_KEY: str = os.getenv("LITELLM_CHATBOT_KEY", "")
CHATBOT_API_KEY: str = os.getenv("CHATBOT_API_KEY", "")
ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "localhost:5173")
UVICORN_RELOAD: bool = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DAILY_REQUEST_LIMIT: int = int(os.getenv("DAILY_REQUEST_LIMIT", "100"))
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "600"))

DATA_PATH: str = os.environ.get("DATA_PATH", os.path.join(PROJECT_ROOT, "data"))
CONFIG_PATH: str = os.path.join(PROJECT_ROOT, "config")
CHROMA_PERSIST_DIR: str = os.path.join(DATA_PATH, "chroma_db")
SYSTEM_PROMPT_PATH: str = os.path.join(CONFIG_PATH, "system_role.md")
