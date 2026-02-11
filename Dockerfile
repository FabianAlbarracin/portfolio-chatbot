# 1. Usamos una imagen base ligera
FROM python:3.10-slim

# 2. Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Directorio de trabajo
WORKDIR /app

# --- NUEVO: Dependencias del Sistema ---
# ChromaDB y librerías de IA a veces requieren compilar componentes en C++.
# Instalamos 'build-essential' para evitar errores durante el 'pip install'.
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Instalamos dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el código
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# 6. SEGURIDAD: 
# HE REMOVIDO la creación de 'appuser' intencionalmente.
# Razón: Al usar volúmenes (- ./data:/app/data) para guardar la base de datos,
# los problemas de permisos de escritura son muy frecuentes si no eres root.
# Para desarrollo local, correr como root es la opción más estable.

# 7. Comando de arranque (será ignorado si usas el docker-compose que te di, 
# pero sirve de respaldo).
CMD ["python", "src/main.py"]