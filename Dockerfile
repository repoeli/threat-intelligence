# ─── Stage 1: builder ──────────────────────────────────────────────
FROM python:3.13-slim AS builder
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /build

# Build deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
# Install Python deps into /install so we can copy a slim tree later
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt && \
    pip install --prefix=/install email-validator
    

# ─── Stage 2: runtime ──────────────────────────────────────────────
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 PATH="/home/app/.local/bin:$PATH" PORT=8686

RUN adduser --disabled-password --gecos "" --uid 1001 app
USER app
WORKDIR /app

COPY --from=builder /install /usr/local/
COPY --chown=app:app backend ./backend

HEALTHCHECK CMD curl -f http://localhost:${PORT}/health || exit 1
EXPOSE ${PORT}

CMD ["gunicorn", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8686", "--timeout", "45", "--workers", "4", "backend.app.main:app"]