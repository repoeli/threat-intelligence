# backend/app/main.py  – FastAPI gateway (v0.2.3)
# ----------------------------------------------------------------------------
from __future__ import annotations

import asyncio, base64, json, os
from datetime import datetime
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import IndicatorRequest, VizResponse
from .services.virustotal_service import vt_call
from .utils.indicator import determine_indicator_type

load_dotenv()
app = FastAPI(title="VT-Proxy v2", version="0.2.3")

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
        content={"error": exc.detail, "ts": datetime.utcnow().isoformat(timespec="seconds")},
        status_code=exc.status_code,
    )

# Placeholder identity (swap with auth later)
def get_identity() -> Dict[str, str]:
    return {"user_id": "anon", "subscription": "free"}

# ─────────────────────────── Config keys ──────────────────────────
ABUSE_KEY = os.getenv("ABUSEIPDB_API_KEY")
URLSCAN_KEY = os.getenv("URLSCAN_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ───────────────────────── Base helpers ───────────────────────────
async def _call_abuseipdb(ip: str):
    if not ABUSE_KEY:
        return {"note": "no AbuseIPDB key"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": ABUSE_KEY, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90},
        )
        r.raise_for_status()
        return r.json()


async def _call_openai(
    ind_t: str,
    ioc: str,
    vt: Dict[str, Any],
    abuse: Dict[str, Any],
    urlscan: Dict[str, Any],
):
    if not OPENAI_KEY:
        return "OpenAI key missing"

    prompt = (
        f"Analyze {ind_t} indicator and provide verdict (malicious/benign), "
        "risk level, and next steps in ≤5 sentences.\n\n"
        f"Indicator: {ioc}\n\n"
        f"VirusTotal snippet: {json.dumps(vt)[:1500]}\n\n"
        f"AbuseIPDB snippet: {json.dumps(abuse)[:800]}\n\n"
    )
    if urlscan:
        prompt += f"URLScan snippet: {json.dumps(urlscan)[:800]}\n\n"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a seasoned SOC analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
    }
    async with httpx.AsyncClient(timeout=60) as c:
        for a in range(3):
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if r.status_code == 429 and a < 2:
                await asyncio.sleep(2 ** a)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


async def _openai_visualize(ind_t: str, ioc: str,
                            vt_attrs: Dict[str, Any],
                            abuse: Dict[str, Any],
                            urlscan: Dict[str, Any]):

    if not OPENAI_KEY:
        raise HTTPException(503, "OpenAI key missing")
    prompt = (
        "You are a SOC data-viz assistant. Return STRICT JSON with keys "
        "summary_markdown, charts, verdict.\n"
        "charts must include analysis_stats (bar) and engine_donut (doughnut).\n\n"
        f"Indicator: {ioc} ({ind_t})\n"
        f"VirusTotal attributes: {json.dumps(vt_attrs)[:12000]}\n"
        f"AbuseIPDB snippet: {json.dumps(abuse)[:800]}\n"
    )

    if urlscan:
        prompt += f"URLScan snippet: {json.dumps(urlscan)[:800]}\n"

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

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])


# ───────────────────────── VT proxy endpoints ──────────────────────
@app.post("/api/virustotal", tags=["virustotal"])
async def vt_generic(body: Dict[str, Any], ident: Dict[str, str] = Depends(get_identity)):
    return await vt_call(
        ident["user_id"],
        ident["subscription"],
        body["name"],
        path_params=body.get("path_params"),
        params=body.get("params"),
        json=body.get("json"),
    )


# ───────────────────────── VT helper routes ────────────────────────
@app.post("/api/virustotal/file", tags=["virustotal"])
async def vt_file(req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)):
    if determine_indicator_type(req.indicator) != "hash":
        raise HTTPException(400, "indicator must be a file hash")
    try:
        return await vt_call(
            ident["user_id"],
            ident["subscription"],
            "get_file_report",
            path_params={"file_id": req.indicator},
        )
    except Exception as exc:
        raise HTTPException(502, f"Upstream service error: {exc}")


@app.post("/api/virustotal/ip", tags=["virustotal"])
async def vt_ip(req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)):
    if determine_indicator_type(req.indicator) != "ip":
        raise HTTPException(400, "indicator must be an IP")
    return await vt_call(
        ident["user_id"],
        ident["subscription"],
        "get_ip_report",
        path_params={"ip": req.indicator},
    )


@app.post("/api/virustotal/domain", tags=["virustotal"])
async def vt_domain(
    req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)
):
    if determine_indicator_type(req.indicator) != "domain":
        raise HTTPException(400, "invalid domain")
    return await vt_call(
        ident["user_id"],
        ident["subscription"],
        "get_domain_report",
        path_params={"domain": req.indicator},
    )


@app.post("/api/virustotal/url", tags=["virustotal"])
async def vt_url(req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)):
    if determine_indicator_type(req.indicator) not in {"url", "domain"}:
        raise HTTPException(400, "invalid URL/domain")
    url = (
        req.indicator
        if req.indicator.startswith(("http://", "https://"))
        else f"http://{req.indicator}"
    )
    url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    try:
        return await vt_call(
            ident["user_id"],
            ident["subscription"],
            "get_url_report",
            path_params={"url_id": url_id},
        )
    except HTTPException as exc:
        if exc.status_code != 502 or "404" not in exc.detail:
            raise
        sub = await vt_call(
            ident["user_id"],
            ident["subscription"],
            "scan_url",
            json={"url": url},
        )
        return {"message": "submitted", "analysis_id": sub["data"]["id"]}


# ───────────────────────── URLScan routes ──────────────────────────
@app.post("/api/urlscan/scan", tags=["urlscan"])
async def urlscan_scan(body: Dict[str, str]):
    if not URLSCAN_KEY:
        raise HTTPException(503, "URLScan key missing")
    target = body.get("url")
    if determine_indicator_type(target) != "url":
        raise HTTPException(400, "invalid URL")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://urlscan.io/api/v1/scan/",
            headers={"API-Key": URLSCAN_KEY, "Content-Type": "application/json"},
            json={"url": target},
        )
        r.raise_for_status()
        return r.json()


@app.get("/api/urlscan/result/{scan_id}", tags=["urlscan"])
async def urlscan_result(scan_id: str):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"https://urlscan.io/api/v1/result/{scan_id}")
        r.raise_for_status()
        return r.json()


# ───────────────────────── Analyze route ───────────────────────────
@app.post("/analyze", tags=["analysis"])
async def analyze(
    req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)
):
    typ = determine_indicator_type(req.indicator)
    if typ == "unknown":
        raise HTTPException(400, "unsupported indicator")

    vt_name, pp = {
        "ip": ("get_ip_report", {"ip": req.indicator}),
        "domain": ("get_domain_report", {"domain": req.indicator}),
        "url": (
            "get_url_report",
            {
                "url_id": base64.urlsafe_b64encode(req.indicator.encode())
                .decode()
                .rstrip("=")
            },
        ),
        "hash": ("get_file_report", {"file_id": req.indicator}),
    }[typ]

    vt_task = asyncio.create_task(
        vt_call(
            ident["user_id"],
            ident["subscription"],
            vt_name,
            path_params=pp,
        )
    )
    abuse_task = (
        asyncio.create_task(_call_abuseipdb(req.indicator)) if typ == "ip" else None
    )

    urlscan_json = {}
    if typ == "url" and URLSCAN_KEY:
        url_id = (
            base64.urlsafe_b64encode(req.indicator.encode()).decode().rstrip("=")
        )
        urlscan_json = await urlscan_result(url_id)

    vt_json = await vt_task
    abuse_json = await abuse_task if abuse_task else {"note": "n/a"}
    gpt_json = await _call_openai(
        typ, req.indicator, vt_json, abuse_json, urlscan_json
    )

    return {
        "virustotal": vt_json,
        "abuseipdb": abuse_json,
        "urlscan": urlscan_json,
        "openai_analysis": gpt_json,
    }


# ───────────────────────── Visualize route ─────────────────────────
@app.post("/api/visualize", response_model=VizResponse, tags=["visualize"])
async def visualize(
    req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)
):
    typ = determine_indicator_type(req.indicator)
    if typ == "unknown":
        raise HTTPException(400, "unsupported indicator")

    vt_name, pp = {
        "ip": ("get_ip_report", {"ip": req.indicator}),
        "domain": ("get_domain_report", {"domain": req.indicator}),
        "url": (
            "get_url_report",
            {
                "url_id": base64.urlsafe_b64encode(req.indicator.encode())
                .decode()
                .rstrip("=")
            },
        ),
        "hash": ("get_file_report", {"file_id": req.indicator}),
    }[typ]

    vt_task = asyncio.create_task(
        vt_call(
            ident["user_id"],
            ident["subscription"],
            vt_name,
            path_params=pp,
        )
    )
    abuse_task = (
        asyncio.create_task(_call_abuseipdb(req.indicator)) if typ == "ip" else None
    )

    urlscan_json = {}
    if typ == "url" and URLSCAN_KEY:
        url_id = (
            base64.urlsafe_b64encode(req.indicator.encode()).decode().rstrip("=")
        )
        urlscan_json = await urlscan_result(url_id)

    vt_json = await vt_task
    abuse_json = await abuse_task if abuse_task else {"note": "n/a"}
    
    viz = await _openai_visualize(
            typ,
            req.indicator,
            vt_json["data"]["attributes"],
            abuse_json,
            urlscan_json,
        )
    return JSONResponse(viz)


# ───────────────────────── Meta/health ─────────────────────────────
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "OK"}

# ───────────────────────── Local run helper ─────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8686)), reload=True
    )