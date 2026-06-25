import json
import os
import time
import threading
import logging

logger = logging.getLogger(__name__)

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "usage_logs.json")

_lock = threading.Lock()


def _ensure_log_file() -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump({}, f)


def check_and_update(ip_address: str, daily_limit: int = 100) -> bool:
    with _lock:
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception as e:
            logger.warning("Error leyendo usage_logs: %s", e)
            data = {}

        current_day = time.strftime("%Y-%m-%d")

        if ip_address not in data or data[ip_address].get("date") != current_day:
            data[ip_address] = {"date": current_day, "count": 1}
        else:
            if data[ip_address]["count"] >= daily_limit:
                logger.warning("IP bloqueada (limite diario): %s | %s consultas", ip_address, data[ip_address]["count"])
                return False
            data[ip_address]["count"] += 1

        logger.info("IP: %s | %s/%s consultas hoy", ip_address, data[ip_address]["count"], daily_limit)

        try:
            with open(LOG_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error("Error guardando usage_logs: %s", e)

        return True


_ensure_log_file()
