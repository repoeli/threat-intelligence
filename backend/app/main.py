## `backend/app/main.py`
# ─────────────────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import base64, os, json, asyncio
from dotenv import load_dotenv

from .services.virustotal_service import vt_call, RateLimitError, APIError
from .utils.indicator import determine_indicator_type
from .models import IndicatorRequest, VizResponse

load_dotenv()

app = FastAPI(title="VT-Proxy", version="1.0.0")

# ─── Security: narrow CORS to your front‑end domain(s) ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------
#  Generic VirusTotal proxy (covers **all** free‑tier endpoints)
# --------------------------------------------------------------------
@app.post("/api/virustotal", tags=["virustotal"])
async def vt_generic(body: Dict[str, Any]):
    """Call *any* public VirusTotal endpoint.

    Body schema:
    {
      "name": "get_file_report",      # key from FREE_ENDPOINTS
      "path_params": { ... },         # optional
      "params": { ... },              # optional query string
      "json": { ... },                # optional JSON body (POST)
      "files": { ... }                # optional files (upload)
    }
    """
    try:
        data = await vt_call(
            body["name"],
            path_params=body.get("path_params"),
            params=body.get("params"),
            json=body.get("json"),
            files=body.get("files"),
        )
        return data
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except APIError as e:
        raise HTTPException(status_code=502, detail=str(e))

# --------------------------------------------------------------------
#  Legacy / convenience endpoints (domain, url) re‑implemented via service
# --------------------------------------------------------------------
@app.post("/api/virustotal/domain", tags=["virustotal"])
async def vt_domain_analysis(req: IndicatorRequest):
    if determine_indicator_type(req.indicator) != "domain":
        raise HTTPException(status_code=400, detail="Invalid domain")
    return await vt_call("get_domain_report", path_params={"domain": req.indicator})

@app.post("/api/virustotal/url", tags=["virustotal"])
async def vt_url_analysis(req: IndicatorRequest):
    if determine_indicator_type(req.indicator) not in {"url", "domain"}:
        raise HTTPException(status_code=400, detail="Invalid URL/domain")

    url = req.indicator if req.indicator.startswith(("http://", "https://")) else f"http://{req.indicator}"
    url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

    try:
        # 1️⃣ try existing report
        report = await vt_call("get_url_report", path_params={"url_id": url_id})
        return report
    except APIError as e:
        # 404 ⇒ submit + return analysis_id
        if "404" not in str(e):
            raise HTTPException(status_code=502, detail=str(e))
        submission = await vt_call("scan_url", json={"url": url})
        return {"message": "submitted", "analysis_id": submission["data"]["id"]}

# --------------------------------------------------------------------
#  High‑level ANALYZE endpoint – pulls VT, AbuseIPDB, and OpenAI
# --------------------------------------------------------------------
@app.post("/analyze", tags=["analysis"])
async def analyze(req: IndicatorRequest, request: Request):
    ind_type = determine_indicator_type(req.indicator)
    if ind_type == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported indicator type")

    # build VT call table
    vt_name, path_params = {
        "ip":     ("get_ip_report",     {"ip": req.indicator}),
        "domain": ("get_domain_report", {"domain": req.indicator}),
        "url":    ("get_url_report",    {"url_id": base64.urlsafe_b64encode(req.indicator.encode()).decode().rstrip("=")}),
        "hash":   ("get_file_report",   {"file_id": req.indicator}),
    }[ind_type]

    vt_task       = asyncio.create_task(vt_call(vt_name, path_params=path_params))
    abuse_task    = None
    if ind_type == "ip" and (abuse_key := os.getenv("ABUSEIPDB_API_KEY")):
        abuse_task = asyncio.create_task(_call_abuseipdb(req.indicator, abuse_key))

    vt_json = await vt_task
    abuse_json = await abuse_task if abuse_task else {"note": "no IP or key"}

    openai_json = await _call_openai(ind_type, req.indicator, vt_json, abuse_json)

    return {
        "virustotal": vt_json,
        "abuseipdb": abuse_json,
        "openai_analysis": openai_json,
    }

# --------------------------------------------------------------------
#  /api/visualize – use GPT to build chart configs
# --------------------------------------------------------------------
@app.post("/api/visualize", response_model=VizResponse, tags=["visualize"])
async def visualize(req: IndicatorRequest):
    ind_type = determine_indicator_type(req.indicator)
    if ind_type == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported indicator type")

    vt_name, path_params = {
        "ip":     ("get_ip_report",     {"ip": req.indicator}),
        "domain": ("get_domain_report", {"domain": req.indicator}),
        "url":    ("get_url_report",    {"url_id": base64.urlsafe_b64encode(req.indicator.encode()).decode().rstrip("=")}),
        "hash":   ("get_file_report",   {"file_id": req.indicator}),
    }[ind_type]

    vt_json = await vt_call(vt_name, path_params=path_params)
    vt_attrs = vt_json["data"]["attributes"]

    viz_json = await _openai_visualize(ind_type, req.indicator, vt_attrs)
    return JSONResponse(viz_json)

# --------------------------------------------------------------------
#  Health
# --------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "OK"}

# --------------------------------------------------------------------
#  Helpers – AbuseIPDB & OpenAI (async, basic retries)
# --------------------------------------------------------------------
import httpx, time

async def _call_abuseipdb(ip: str, key: str):
    url = "https://api.abuseipdb.com/api/v2/check"
    params = {"ipAddress": ip, "maxAgeInDays": 90}
    headers = {"Key": key, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

async def _call_openai(ind_type: str, indicator: str, vt: Dict[str, Any], abuse: Dict[str, Any]):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "key not set"

    prompt = (
        f"Analyze this {ind_type}: {indicator}\n\n"
        f"VirusTotal: {json.dumps(vt)[:2000]}\n\n"
        f"AbuseIPDB: {json.dumps(abuse)[:1000]}\n\n"
        "Respond in <500 tokens, 3‑5 sentences, verdict + next steps."
    )
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a cybersecurity expert."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 500,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code == 429 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

async def _openai_visualize(ind_type: str, indicator: str, attrs: Dict[str, Any]):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI key missing")
    prompt = (
        "You are a SOC data‑viz assistant. Return STRICT JSON with keys: "
        "summary_markdown, charts, verdict. The charts key must contain "
        "two Chart.js configs: analysis_stats (bar) and engine_donut (doughnut).\n\n"
        f"Indicator: {indicator} ({ind_type})\nVirusTotal attributes (trimmed):\n{json.dumps(attrs)[:12000]}"
    )
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    
# ─── Run with: uvicorn backend.app.main:app --reload ─────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8686,          # ← was 8282
        reload=True
    )

# ─────────────────────────────────────────────────────────────────────

