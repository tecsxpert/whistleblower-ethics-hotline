# ai-service/Dockerfile
# =====================
# Tool-70 — Whistleblower & Ethics Hotline
# AI Microservice — Production Dockerfile
#
# Changes from dev version:
#   - Uses gunicorn (production WSGI server) instead of python app.py
#   - Non-root user for security hardening
#   - .dockerignore should exclude: __pycache__, .env, *.pyc, chroma_data/

FROM python:3.11-slim

# --------------------------------------------------------------------------
# System dependencies
# --------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# Non-root user (security best practice)
# --------------------------------------------------------------------------
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# --------------------------------------------------------------------------
# Working directory
# --------------------------------------------------------------------------
WORKDIR /app

# --------------------------------------------------------------------------
# Install Python dependencies
# Install before copying app code so layer is cached when only code changes
# --------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn==21.2.0

# --------------------------------------------------------------------------
# Pre-download the sentence-transformer model so container starts fast
# --------------------------------------------------------------------------
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# --------------------------------------------------------------------------
# Copy application code
# --------------------------------------------------------------------------
COPY --chown=appuser:appgroup . .

# --------------------------------------------------------------------------
# Switch to non-root user
# --------------------------------------------------------------------------
USER appuser

# --------------------------------------------------------------------------
# Expose port
# --------------------------------------------------------------------------
EXPOSE 5000

# --------------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# --------------------------------------------------------------------------
# Production entrypoint
# Replaces: python app.py
# 2 workers (-w 2) — increase to (2 * CPU_cores + 1) for production hardware
# Timeout 120s to handle slow Groq API responses gracefully
# --------------------------------------------------------------------------
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
