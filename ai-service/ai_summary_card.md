# AI Service Summary Card

## Service Overview

| Property           | Value                        |
|--------------------|------------------------------|
| **Port**           | 5000                         |
| **LLM Model**      | LLaMA-3.3-70b-versatile     |
| **LLM Provider**   | Groq                         |
| **Embedding Model** | all-MiniLM-L6-v2            |
| **Vector Store**   | ChromaDB (cosine similarity) |
| **Cache**          | Redis (optional)             |
| **Rate Limit**     | 30 req/min/IP                |

## Tech Stack

| Component            | Technology              | Version   |
|----------------------|-------------------------|-----------|
| Runtime              | Python                  | 3.11      |
| Web Framework        | Flask                   | 3.0.3     |
| WSGI Server          | Gunicorn                | 22.0.0    |
| LLM Client           | requests → Groq API    | 2.32.3    |
| Vector Database      | ChromaDB                | 0.5.23    |
| Embeddings           | sentence-transformers   | 3.3.1     |
| Tensor Compute       | PyTorch (CPU)           | 2.5.1     |
| Cache                | Redis                   | 5.0.8     |
| Rate Limiting        | flask-limiter           | 3.8.0     |
| CORS                 | Flask-Cors              | 4.0.1     |

## AI Endpoints

| Endpoint            | Method | Description                                  |
|---------------------|--------|----------------------------------------------|
| `/describe`         | POST   | Classify and summarise a whistleblower report |
| `/recommend`        | POST   | Generate 3 compliance recommendations         |
| `/generate-report`  | POST   | Generate a formal compliance report            |

## Bonus Endpoint

| Endpoint | Method | Description                                                    |
|----------|--------|----------------------------------------------------------------|
| `/query` | POST   | RAG-powered compliance knowledge base queries (10 seed docs)   |

## Security Features

- **Input Sanitisation:** 18 regex injection patterns + HTML stripping
- **Rate Limiting:** 30 requests/minute/IP (Redis or in-memory backend)
- **Security Headers:** 8 hardened headers on every response
- **Content Validation:** JSON-only POST, 16KB max payload, field length limits
- **PII Protection:** Raw text never logged; only `len()` at INFO level
- **Graceful Degradation:** Fallback responses (never HTTP 500) for all AI endpoints
- **Request Tracing:** X-Request-ID on every request/response

## Key Design Decisions

1. **Fallbacks over failures** — All AI endpoints return structured fallback responses (HTTP 200 with `is_fallback: true`) instead of HTTP 500 errors, ensuring the frontend always receives usable data.

2. **Cache-after-validate** — Responses are only cached after successful AI processing and validation. Fallback responses are never cached to ensure fresh AI results on recovery.

3. **RAG with seed data** — The `/query` endpoint uses a pre-seeded ChromaDB collection with 10 compliance documents covering key policy areas. The knowledge base can be expanded via the `add_documents()` API.

4. **Thread-safe metrics** — Response timing data is collected using `threading.Lock()` and bounded `deque` structures to prevent memory leaks under load.

5. **Prompt injection defence** — Multi-layered: HTML entity unescaping → tag stripping → 18 regex pattern matching → input truncation. Applied before any AI processing.
