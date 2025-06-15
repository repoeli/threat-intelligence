## README (snippet)
```markdown
### 🚀 Build & run (Docker Desktop / WSL2)

```powershell
# 0. clone repo & cd into it

# 1. put your API keys in backend/.env   (VIRUSTOTAL_API_KEY, OPENAI_API_KEY, …)

# 2. build image (multi‑stage)
docker build -t vt-proxy:latest .

# 3. run
#    -p HOSTPORT:CONTAINERPORT, here we keep 8686
#    -e WEB_CONCURRENCY=2 overrides default workers when RAM is tight

docker run -d --name vt-proxy -p 8686:8686 --env-file backend/.env vt-proxy:latest

# 4. browse OpenAPI
start http://localhost:8686/docs
```

---

### 📝 Why this setup is “industry‑level”
1. **Multi‑stage build** – strips compilers, shrink image (~90 MB vs 300 MB).
2. **Unprivileged runtime** – stops container breakout into host root.
3. **Gunicorn with Uvicorn workers** – leverages multiple CPU cores; Env vars enable platform‑tuned scaling (k8s HPA).
4. **Config via env only** – 12‑factor ready (secrets stay outside image).
5. **Health‑check & labels** – ready for Docker Swarm / k8s / ECS rollout.
6. **.dockerignore** – small build context → faster CI pipeline.
7. **Extensible** – Traefik snippet shows how to front the API with TLS.

> With this you can build & push once, then run the same immutable image on any orchestrator without tweaks.

# 📁 Project Layout – v2 (future‑ready SaaS)
.
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI API‑gateway (async) – port via $PORT (default 8686)
│   │   ├── db.py                         # SQLModel engine / session
│   │   ├── auth/                         # (placeholder for OAuth2/JWT & Stripe sync)
│   │   │   ├── __init__.py               # to be implemented next stage
│   │   ├── services/
│   │   │   ├── virustotal_service.py     # Async, per‑user RL, Redis
│   │   │   └── __init__.py
│   │   ├── clients/virustotal_client.py  # Async httpx wrapper (free tier)
│   │   ├── utils/indicator.py            # IoC detection (extensible)
│   │   ├── models.py                     # Pydantic & SQLModel schemas
│   │   └── __init__.py
│   └── requirements.txt
├── migrations/                           # Alembic (empty for now)
├── Dockerfile                            # 🐳 multi‑stage, JSON‑exec, non‑root
├── docker-compose.yml                    # API + Postgres + Redis
├── .dockerignore
└── README.md