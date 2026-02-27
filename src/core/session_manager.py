import time


class SessionManager:
    """
    Gestor de memoria de corto plazo (Multi-Tenant).
    Mantiene el estado de las conversaciones y aplica doble limpieza:
    1. Por Tiempo (TTL): Borra sesiones inactivas.
    2. Por Capacidad (Max Sessions): Evita saturación de RAM.
    """

    def __init__(self, ttl_seconds: int = 600, max_sessions: int = 30):
        self.sessions = {}
        self.ttl = ttl_seconds
        self.max_sessions = max_sessions

    def get_session(self, session_id: str) -> dict:
        current_time = time.time()

        # 1. LIMPIEZA POR TIEMPO (Garbage Collector manual)
        expired_sessions = [
            sid
            for sid, data in self.sessions.items()
            if current_time - data["last_interaction"] > self.ttl
        ]
        for sid in expired_sessions:
            del self.sessions[sid]
            print(f"🧹 TTL: Sesión {sid} expirada.")

        # 2. CONTROL DE CAPACIDAD (Evitar saturación de RAM)
        if session_id not in self.sessions:
            if len(self.sessions) >= self.max_sessions:
                # Borramos la sesión que menos recientemente se usó
                oldest_session = min(
                    self.sessions, key=lambda k: self.sessions[k]["last_interaction"]
                )
                del self.sessions[oldest_session]
                print(f"⚖️ Límite: Sesión {oldest_session} eliminada por cupo máximo.")

            self.sessions[session_id] = {
                "active_entities": [],
                "history": [],
                "last_interaction": current_time,
                "last_detected_lang": "es",
            }

        # 3. Actualizar timestamp de interacción
        self.sessions[session_id]["last_interaction"] = current_time
        return self.sessions[session_id]

    def update_history(self, session: dict, query: str, answer: str):
        """Mantiene un máximo de 3 interacciones (6 mensajes) para optimizar tokens."""
        session["history"].append({"role": "user", "content": query})
        session["history"].append({"role": "assistant", "content": answer})

        # Recorte estricto de ventana de contexto
        if len(session["history"]) > 6:
            session["history"] = session["history"][-6:]
