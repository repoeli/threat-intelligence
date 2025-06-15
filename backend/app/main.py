# ─────────────────────────────────────────────────────────────────────────────
# backend/app/main.py  – FastAPI gateway (cleaned)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import IndicatorRequest, VizResponse
from .services.virustotal_service import vt_call, APIError
from .utils.indicator import determine_indicator_type

load_dotenv()
app = FastAPI(title="VT‑Proxy v2", version="0.2.1")

# ───────────────────────────── CORS ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ───────────────────── global error envelope ──────────────────────
@app.exception_handler(HTTPException)
async def http_exc_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "ts": datetime.utcnow().isoformat()[:19]},
    )

# Placeholder – will be replaced by auth dependency

def get_identity() -> Dict[str, str]:
    return {"user_id": "anon", "subscription": "free"}

# ─────────────────── VirusTotal proxy ──────────────────────────────
@app.post("/api/virustotal", tags=["virustotal"])
async def vt_generic(body: Dict[str, Any], ident: Dict[str, str] = Depends(get_identity)):
    return await vt_call(
        ident["user_id"], ident["subscription"], body["name"],
        path_params=body.get("path_params"), params=body.get("params"), json=body.get("json")
    )

# (domain, url helpers, analyze, visualize *unchanged – snipped for brevity*)
# …

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

# ───────────────────── helper coroutines ────────────────────────────
async def _call_abuseipdb(ip: str, key: str):
    url = "https://api.abuseipdb.com/api/v2/check"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers={"Key": key, "Accept": "application/json"}, params={"ipAddress": ip, "maxAgeInDays": 90})
        r.raise_for_status()
        return r.json()

async def _call_openai(indicator_type: str, indicator: str, vt: Dict[str, Any], abuse: Dict[str, Any]):
    """Single GPT analysis call with retry + clear prompt."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "OPENAI key missing"

    prompt = (
        f"Analyze the following {indicator_type} indicator and give a verdict (malicious/benign), "
        "risk level, and recommended next steps in no more than 5 sentences.\n\n"
        f"Indicator: {indicator}\n\n"
        f"VirusTotal snippet: {json.dumps(vt, ensure_ascii=False)[:1500]}\n\n"
        f"AbuseIPDB snippet: {json.dumps(abuse, ensure_ascii=False)[:800]}"
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a seasoned SOC analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code == 429 and attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

async def _openai_visualize(indicator_type: str, indicator: str, attrs: Dict[str, Any]):
    """Ask GPT to build markdown & Chart.js configs – strict JSON return."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "OpenAI key missing")

    prompt = (
        "You are a SOC data‑viz assistant. Respond ONLY with valid JSON with keys:\n"
        "summary_markdown, charts, verdict.\n"
        "charts must contain two Chart.js configs: analysis_stats (bar) and engine_donut (doughnut).\n\n"
        f"Indicator: {indicator} ({indicator_type})\n"
        f"VirusTotal attributes (trimmed):\n{json.dumps(attrs, ensure_ascii=False)[:12000]}"
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
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        gpt_json = resp.json()["choices"][0]["message"]["content"]
        return json.loads(gpt_json)

# ── local run helper ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8686)), reload=True)