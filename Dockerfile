FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN mkdir -p src && touch src/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf src

COPY src/ ./src/
COPY config/ ./config/

RUN mkdir -p /app/data

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]