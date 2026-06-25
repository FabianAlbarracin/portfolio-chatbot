import re
import logging

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(ignore|ignora|ignorar)\b.{0,50}\b(instructions?|instrucciones|prompts?)", re.IGNORECASE), "injection: ignore instructions"),
    (re.compile(r"system\s+prompt", re.IGNORECASE), "injection: system prompt"),
    (re.compile(r"instrucciones\s+del\s+sistema", re.IGNORECASE), "injection: instrucciones del sistema"),
    (re.compile(r"(api[_\s]?key|apikey)", re.IGNORECASE), "injection: api key"),
    (re.compile(r"(contraseña|contrasena|password|passwd)", re.IGNORECASE), "injection: password request"),
    (re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})", re.IGNORECASE), "injection: base64 pattern"),
]

def check_injection(query: str) -> tuple[bool, str]:
    for pattern, reason in _INJECTION_PATTERNS:
        if pattern.search(query):
            logger.warning("Guardrail bloqueo: %s", reason)
            return True, reason
    return False, ""
