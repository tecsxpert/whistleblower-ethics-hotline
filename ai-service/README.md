# Tool-70 — Whistleblower & Ethics Hotline AI Microservice

> **AI Developer 1** — Capstone Project  
> Flask 3.x · Groq Llama-3.3-70b · Redis · ChromaDB · Docker

---

## Overview

This microservice powers the AI features of the Whistleblower & Ethics Hotline platform. It analyses whistleblower complaints, classifies them by category and severity, generates actionable investigation recommendations, and produces formal compliance reports — all powered by the Groq Llama-3.3-70b-versatile large language model.

## Architecture

```
┌──────────────┐    ┌───────────────┐    ┌────────────┐
│  Flask App   │───▶│  Groq API     │    │  Redis     │
│  (port 5000) │    │  (LLM)        │    │  (cache)   │
│              │───▶│               │    │            │
│  Blueprints: │    └───────────────┘    └────────────┘
│  /describe   │                              ▲
│  /recommend  │──────────────────────────────┘
│  /report     │
│  /health     │───▶┌───────────────┐
└──────────────┘    │  ChromaDB     │
                    │  (vector RAG) │
                    └───────────────┘
```

## API Endpoints

| Method | Endpoint           | Description                          |
|--------|--------------------|--------------------------------------|
| POST   | `/describe/`       | Classify and summarise a complaint   |
| POST   | `/recommend/`      | Generate investigation recommendations|
| POST   | `/generate-report/`| Produce a formal investigation report|
| GET    | `/health/`         | Service health check                 |

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Run with Docker

```bash
docker build -t tool70-ai .
docker run -p 5000:5000 --env-file .env tool70-ai
```

### 3. Run Locally

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python app.py
```

### 4. Run Tests

```bash
pytest tests/ -v
```

## Example Request

```bash
curl -X POST http://localhost:5000/describe/ \
  -H "Content-Type: application/json" \
  -d '{"text": "I witnessed my manager approving fake invoices worth $50,000 to a shell company owned by his brother-in-law."}'
```

## Security Features

- **Rate Limiting**: 30 requests/minute per IP via flask-limiter
- **Input Sanitisation**: HTML stripping + prompt-injection detection
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, CSP, etc.
- **Fail-Silent Caching**: Redis failures never crash the app
- **Graceful Degradation**: Fallback responses when Groq is unavailable

## Tech Stack

| Component              | Technology                      |
|------------------------|---------------------------------|
| Web Framework          | Flask 3.0.3                     |
| LLM Provider           | Groq (llama-3.3-70b-versatile) |
| Caching                | Redis 7 (TTL 900s)             |
| Vector Store           | ChromaDB + all-MiniLM-L6-v2    |
| Rate Limiting          | flask-limiter 3.8.0            |
| Containerisation       | Docker (python:3.11-slim)       |
| Testing                | pytest 8.3.3                    |

## Environment Variables

| Variable       | Description               | Default              |
|----------------|---------------------------|----------------------|
| `GROQ_API_KEY` | Groq API key (required)   | —                    |
| `REDIS_URL`    | Redis connection URI      | `redis://redis:6379` |
| `FLASK_ENV`    | Flask environment         | `production`         |
| `FLASK_DEBUG`  | Debug mode (0 or 1)       | `0`                  |

## License

Internal capstone project — not for public distribution.
