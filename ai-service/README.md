# Whistleblower & Ethics Hotline — AI Microservice

A production-ready Flask AI microservice that powers the Whistleblower & Ethics Hotline tool with AI-driven report classification, compliance recommendations, formal report generation, and RAG-based knowledge queries.

The service integrates with Groq's LLaMA-3.3-70b model for natural language processing, ChromaDB for semantic search over a compliance knowledge base, and Redis for response caching.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  React UI   │────▶│  Spring Boot     │────▶│  Flask AI Service  │
│  (Frontend) │     │  (Port 8080)     │     │  (Port 5000)       │
└─────────────┘     └──────────────────┘     └────────┬───────────┘
                                                      │
                                         ┌────────────┼────────────┐
                                         ▼            ▼            ▼
                                   ┌──────────┐ ┌──────────┐ ┌─────────┐
                                   │ Groq API │ │ ChromaDB │ │  Redis  │
                                   │ (LLM)   │ │ (Vectors)│ │ (Cache) │
                                   └──────────┘ └──────────┘ └─────────┘
```

## Prerequisites

| Tool       | Version  | Purpose                  |
|------------|----------|--------------------------|
| Python     | 3.11+    | Runtime                  |
| pip        | 23+      | Package manager          |
| Docker     | 24+      | Containerisation         |
| Redis      | 7+       | Caching (optional)       |
| Groq API   | —        | LLM inference            |

## Local Setup

```bash
# 1. Clone and navigate
cd ai-service

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set your GROQ_API_KEY

# 5. Test Groq connectivity
python test_groq.py

# 6. Start the service
python app.py
```

## Environment Variables

| Variable               | Required | Default                                          | Description                           |
|------------------------|----------|--------------------------------------------------|---------------------------------------|
| `GROQ_API_KEY`         | Yes      | —                                                | Groq API authentication key           |
| `GROQ_TIMEOUT_SECONDS` | No       | `25`                                             | Groq API request timeout (seconds)    |
| `AI_PORT`              | No       | `5000`                                           | Flask server port                     |
| `FLASK_DEBUG`          | No       | `false`                                          | Enable Flask debug mode               |
| `REDIS_URL`            | No       | —                                                | Redis connection URL for caching      |
| `CHROMA_PERSIST_DIR`   | No       | `./chroma_data`                                  | ChromaDB persistence directory        |
| `ALLOWED_ORIGINS`      | No       | `http://localhost:8080,http://127.0.0.1:8080`    | CORS allowed origins (comma-separated)|

## API Reference

### `GET /health`

Health check with system metrics.

**Response** `200`:
```json
{
  "status": "ok",
  "model": "llama-3.3-70b-versatile",
  "embedding_model": "all-MiniLM-L6-v2",
  "vector_store_documents": 10,
  "uptime_seconds": 120.5,
  "avg_response_ms": 450.2,
  "endpoint_avg_ms": {},
  "slow_endpoints": [],
  "performance_target_ms": 2000,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### `GET /ping`

Simple liveness probe.

**Response** `200`:
```json
{"pong": true}
```

### `POST /describe`

Classify and summarise a whistleblower report.

**Request**:
```json
{"text": "I discovered my manager submitting false expense reports..."}
```

**Response** `200`:
```json
{
  "category": "Fraud",
  "severity": "High",
  "summary": "Employee reported financial irregularities...",
  "key_entities": ["Finance Department", "Q3 Reports"],
  "recommended_action": "Initiate formal investigation.",
  "generated_at": "2024-01-01T00:00:00Z",
  "is_fallback": false
}
```

### `POST /recommend`

Generate compliance recommendations.

**Request**:
```json
{"text": "A colleague reported workplace harassment..."}
```

**Response** `200`:
```json
{
  "recommendations": [
    {"action_type": "Investigation", "description": "Start formal inquiry.", "priority": "High"},
    {"action_type": "HR Review", "description": "Engage HR department.", "priority": "Medium"},
    {"action_type": "Documentation", "description": "Preserve evidence.", "priority": "Low"}
  ],
  "is_fallback": false,
  "generated_at": "2024-01-01T00:00:00Z"
}
```

### `POST /generate-report`

Generate a formal compliance report.

**Request**:
```json
{"text": "Safety violations observed in warehouse operations..."}
```

**Response** `200`:
```json
{
  "title": "Safety Compliance Investigation Report",
  "summary": "Executive summary of the safety incident...",
  "overview": "Detailed overview of the warehouse safety violations...",
  "key_items": ["Forklift certification gap", "Missing safety equipment"],
  "recommendations": ["Mandatory retraining", "Equipment audit"],
  "generated_at": "2024-01-01T00:00:00Z",
  "is_fallback": false
}
```

### `POST /query`

Query the compliance knowledge base using RAG.

**Request**:
```json
{"query": "What is the procedure for reporting financial fraud?"}
```

**Response** `200`:
```json
{
  "answer": "Financial fraud should be reported immediately to the ethics hotline...",
  "sources": [{"source": "Financial Fraud & SOX/Dodd-Frank Policy", "relevance": 0.85}],
  "confidence": "High",
  "generated_at": "2024-01-01T00:00:00Z",
  "is_fallback": false
}
```

## Running Tests

```bash
# Set environment for tests
SKIP_GROQ_VALIDATION=true GROQ_API_KEY=test-key pytest tests/ -v

# Windows PowerShell
$env:SKIP_GROQ_VALIDATION="true"; $env:GROQ_API_KEY="test-key"; pytest tests/ -v
```

## Docker

```bash
# Build
docker build -t ai-service .

# Run
docker run -p 5000:5000 --env-file .env ai-service

# Health check
curl http://localhost:5000/health
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `RuntimeError: GROQ_API_KEY is missing` | `.env` not configured | Copy `.env.example` to `.env` and set your Groq API key |
| `Connection refused on port 5000` | Service not running | Run `python app.py` or check Docker container status |
| `Rate limit exceeded (429)` | Too many requests | Wait 60 seconds; rate limit is 30 req/min/IP |
