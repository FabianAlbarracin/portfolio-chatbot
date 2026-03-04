#!/bin/bash

echo "========================================"
echo "🧠 1. Ejecutando pipeline ETL (Ingesta)..."
echo "========================================"
# Activar entorno virtual si lo usas, o ejecutar directo
python src/pipelines/ingest.py

echo "========================================"
echo "🔄 2. Reiniciando la API para sincronizar..."
echo "========================================"
docker compose restart

echo "========================================"
echo "✅ ¡Base de conocimientos actualizada en producción!"
echo "========================================"
