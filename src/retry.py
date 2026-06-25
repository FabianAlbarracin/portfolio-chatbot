import time
import logging
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

def with_retry(
    fn: Callable[..., T],
    max_retries: int = 2,
    backoff_base: float = 1.0,
) -> Callable[..., T]:
    def wrapper(*args, **kwargs):
        last_exception: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait = backoff_base * (2 ** attempt)
                    logger.warning(
                        "Intento %d/%d fallido: %s. Reintentando en %.1fs...",
                        attempt + 1, max_retries + 1, e, wait,
                    )
                    time.sleep(wait)
        logger.error("Agotados %d reintentos. Ultimo error: %s", max_retries + 1, last_exception)
        raise last_exception

    return wrapper
