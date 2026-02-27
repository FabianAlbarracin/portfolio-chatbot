import json
import os
import time

class UsageTracker:
    def __init__(self, log_file="data/usage_logs.json", daily_limit=2):
        # Usamos la ruta absoluta para evitar problemas con Docker
        self.log_file = os.path.abspath(log_file)
        self.daily_limit = daily_limit
        self._ensure_log_exists()
        print(f"🚀 UsageTracker inicializado. Límite: {self.daily_limit} consultas/día.")

    def _ensure_log_exists(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                json.dump({}, f)

    def check_and_update(self, ip_address: str) -> bool:
        """Verifica y actualiza el contador diario por IP."""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "r") as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception as e:
            print(f"⚠️ Error leyendo log de uso: {e}")
            data = {}

        current_day = time.strftime("%Y-%m-%d")

        if ip_address not in data or data[ip_address].get("date") != current_day:
            data[ip_address] = {"date": current_day, "count": 1}
        else:
            if data[ip_address]["count"] >= self.daily_limit:
                print(f"🚫 IP BLOQUEADA (Límite diario): {ip_address} | Intentos hoy: {data[ip_address]['count']}")
                return False
            data[ip_address]["count"] += 1

        # Log de consola para que sepas qué está pasando
        print(f"📊 IP: {ip_address} | Consultas hoy: {data[ip_address]['count']}/{self.daily_limit}")

        try:
            with open(self.log_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"❌ Error guardando log de uso: {e}")

        return True