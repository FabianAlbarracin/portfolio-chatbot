# portfolio_chatbot_api

Chatbot con FastAPI + LangChain + Groq + ChromaDB para servir respuestas contextuales sobre el portafolio personal.

## Arranque

```bash
docker compose up -d
```

## Dependencias

- Groq API key (variable `GROQ_API_KEY` en `.env`)
- ChromaDB en `./data/` (persistencia local)
- Puerto 8000 (expuesto, proxy NPM)

## Endpoints

- `GET /health` — healthcheck
- `POST /chat` — endpoint principal de conversacion

## Variables de entorno

Ver `.env.example`.
