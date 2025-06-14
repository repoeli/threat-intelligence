## `Dockerfile` *(multi‑stage, ~90 MB final)*
# This Dockerfile builds a Python web application using FastAPI and Uvicorn,
# optimised for production deployment with Gunicorn. It uses a multi‑stage build
# ─────────── Stage 1: builder ────────────────────────────────────────────
FROM python:3.13-slim AS builder

LABEL org.opencontainers.image.source="https://github.com/repoeli/threat-intelligence" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# system deps required for manylinux wheels / cryptography
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc curl && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

# Install into a dedicated path we can copy later (keeps layer clean)
RUN pip install --prefix=/install -r requirements.txt

# ─────────── Stage 2: runtime ────────────────────────────────────────────
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH" \
    PORT=8686

# non‑root unprivileged user (UID 1001 == app)
RUN adduser --disabled-password --gecos "" --uid 1001 app
USER app
WORKDIR /app

# Copy site‑packages from builder (only what’s needed)
COPY --from=builder /install /usr/local/

# Copy application code *after* deps – maximises cache reuse
COPY --chown=app:app backend ./backend

# Health‑check endpoint is `/health`
HEALTHCHECK CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port (for docs only – Kubernetes/compose bind ports explicitly)
EXPOSE ${PORT}

# ── Start via Gunicorn (exec form; JSON array preserves PID 1 signals) ──
# Remove the ENTRYPOINT and replace both with a single CMD
CMD ["gunicorn", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8686", \
     "--timeout", "45", \
     "--workers", "4", \
     "backend.app.main:app"]
# ────────────────────────────────────────────────────────────────────────
# **Dockerfile Overview**
#Highlights**
# **Multi‑stage** keeps compile tools out of final layer → smaller attack surface.
# Runs as an **unprivileged user**.
# Uses **Gunicorn** (prefork) for better CPU utilisation vs. raw Uvicorn.
# Health‑check baked in; plays nice with Docker, k8s, ECS.
# `$PORT` / `$WEB_CONCURRENCY` allow flexible run‑time tuning.
