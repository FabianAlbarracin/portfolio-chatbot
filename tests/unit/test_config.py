import os

from src import config


def test_default_log_level():
    assert config.LOG_LEVEL == "INFO"


def test_default_daily_request_limit():
    assert config.DAILY_REQUEST_LIMIT == 100


def test_default_rate_limit_per_minute():
    assert config.RATE_LIMIT_PER_MINUTE == 20


def test_default_session_ttl():
    assert config.SESSION_TTL_SECONDS == 600


def test_default_allowed_origins():
    assert "localhost:5173" in config.ALLOWED_ORIGINS


def test_uvicorn_reload_default_false():
    assert config.UVICORN_RELOAD is False


def test_system_prompt_path_exists():
    assert os.path.exists(config.SYSTEM_PROMPT_PATH)


def test_chroma_persist_dir_valid():
    assert config.CHROMA_PERSIST_DIR.endswith("chroma_db")


def test_config_path_valid():
    assert os.path.isdir(config.CONFIG_PATH)
