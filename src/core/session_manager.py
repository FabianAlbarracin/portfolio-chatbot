import time

class SessionManager:
    """
    Gestor de memoria de corto plazo (Multi-Tenant).
    Mantiene el estado de las conversaciones y limpia automáticamente las sesiones expiradas.
    """
    def __init__(self, ttl_seconds: int = 900):
        self.sessions = {}
        self.ttl = ttl_seconds

    def get_session(self, session_id: str) -> dict:
        current_time = time.time()

        # Limpiar sesiones expiradas (Garbage Collector manual)
        expired_sessions = [
            sid for sid, data in self.sessions.items()
            if current_time - data["last_interaction"] > self.ttl
        ]
        for sid in expired_sessions:
            del self.sessions[sid]

        # Crear nueva sesión si no existe
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "active_entities": [],
                "history": [],
                "last_interaction": current_time,
            }

        # Actualizar timestamp de última interacción
        self.sessions[session_id]["last_interaction"] = current_time
        return self.sessions[session_id]

    def update_history(self, session: dict, query: str, answer: str):
        """Mantiene un máximo de 3 interacciones en memoria (6 mensajes) para no saturar el LLM."""
        session["history"].append({"role": "usuario", "content": query})
        session["history"].append({"role": "asistente", "content": answer})
        if len(session["history"]) > 6:
            session["history"] = session["history"][-6:]