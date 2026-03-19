# FinSentinel AI - API Dockerfile

FROM python:3.11-slim

WORKDIR /app

# ─── System Dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Python Dependencies ──────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Application Source ───────────────────────────────────────────────────────
COPY . .

# ─── Security: Non-root User ──────────────────────────────────────────────────
RUN useradd --create-home --shell /bin/bash finsentinel && \
    chown -R finsentinel:finsentinel /app
USER finsentinel

# ─── Health Check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

# ─── Start Command ────────────────────────────────────────────────────────────
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]