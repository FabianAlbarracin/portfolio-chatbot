#!/bin/bash

echo "========================================"
echo "🧠 1. Ejecutando pipeline ETL (Upsert inmutable)..."
echo "========================================"
docker exec -t portfolio_chatbot_api python src/ingest.py

echo "========================================"
echo "🔄 2. Disparando Hot-Reload en FastAPI (Zero-Downtime)..."
echo "========================================"

# Extraer CHATBOT_API_KEY sanitizada: busca solo líneas que COMIENCEN con el nombre exacto
API_KEY=$(grep "^CHATBOT_API_KEY=" .env | cut -d '=' -f2 | tr -d '\r' | tr -d ' ' | tr -d '"' | tr -d "'")

# Llamada HTTP con volcado de código de estado para auditoría
curl -X POST http://localhost:8000/admin/refresh \
     -H "x-api-key: $API_KEY" \
     -H "Content-Length: 0" \
     -s -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "========================================"
echo "✅ ¡Actualización completada en caliente! El contenedor sigue en línea."
echo "========================================"