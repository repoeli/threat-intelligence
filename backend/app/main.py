# backend/app/main.py  – FastAPI gateway (v1.0.0-working)
# ----------------------------------------------------------------------------
from __future__ import annotations

import asyncio, base64, json, os, logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    IndicatorRequest, 
    SimpleIndicatorRequest,
    VizResponse, 
    ThreatIntelligenceResult,
    BulkAnalysisRequest,
    BulkAnalysisResponse,
    IndicatorType,
    # Authentication models
    UserRegistration,
    UserLogin,
    TokenResponse,
    UserResponse
)
from .services.virustotal_service import vt_call
from .services.threat_analysis import threat_analysis_service
from .services.auth_service import auth_service
from .utils.indicator import determine_indicator_type
from .auth import get_current_user, get_current_user_optional, require_medium, require_plus, check_rate_limit
from .database import init_database, close_database, get_db_session

# Load environment variables from the project root `.env` file, if present
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables
ABUSE_KEY = os.getenv("ABUSEIPDB_API_KEY")
URLSCAN_KEY = os.getenv("URLSCAN_API_KEY") 
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Database lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database lifecycle."""
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()

# Initialize FastAPI app with enhanced metadata
app = FastAPI(
    title="Threat Intelligence API",
    version="1.0.0",
    description="Advanced threat intelligence analysis platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ───────────────────────── CORS ────────────────────────────────
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
        content={"error": exc.detail, "ts": datetime.now(UTC).isoformat(timespec="seconds")},
        status_code=exc.status_code,
    )

# ───────────────────────── Authentication Endpoints ─────────────────────────
@app.post("/auth/register", response_model=dict, tags=["authentication"])
async def register(user_data: UserRegistration, db: AsyncSession = Depends(get_db_session)):
    """Register a new user"""
    try:
        user_response, token_response = await auth_service.register_user(user_data, db)
        
        # Get user's analysis count for the response (will be 0 for new users)
        from .services.database_service import db_service
        stats = await db_service.get_user_stats(db, int(user_response.user_id))
        
        return {
            "access_token": token_response.access_token,
            "token_type": token_response.token_type,
            "expires_in": token_response.expires_in,
            "user": {
                "user_id": user_response.user_id,
                "email": user_response.email,
                "subscription": user_response.subscription_level.value,
                "created_at": user_response.created_at.isoformat() if user_response.created_at else None,
                "analysis_count": stats.get("total_analyses", 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/auth/login", response_model=dict, tags=["authentication"])
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db_session)):
    """Authenticate user and return access token"""
    try:
        user_response, token_response = await auth_service.login_user(login_data, db)
        
        # Get user's analysis count for the response
        from .services.database_service import db_service
        stats = await db_service.get_user_stats(db, int(user_response.user_id))
        
        return {
            "access_token": token_response.access_token,
            "token_type": token_response.token_type,
            "expires_in": token_response.expires_in,
            "user": {
                "user_id": user_response.user_id,
                "email": user_response.email,
                "subscription": user_response.subscription_level.value,
                "created_at": user_response.created_at.isoformat() if user_response.created_at else None,
                "analysis_count": stats.get("total_analyses", 0)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@app.get("/auth/profile", response_model=dict, tags=["authentication"])
async def get_profile(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get current user profile (requires authentication)"""
    try:
        user_response = await auth_service.get_user_profile(int(current_user["user_id"]), db)
        
        # Get user's analysis count
        from .services.database_service import db_service
        stats = await db_service.get_user_stats(db, int(current_user["user_id"]))
        
        # Return format that matches frontend User interface
        return {
            "user_id": user_response.user_id,
            "email": user_response.email,
            "subscription": user_response.subscription_level.value,  # Convert enum to string
            "created_at": user_response.created_at.isoformat() if user_response.created_at else None,
            "analysis_count": stats.get("total_analyses", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch profile: {str(e)}"
        )


@app.get("/auth/stats", tags=["authentication"])
async def get_auth_stats(
    current_user: Dict = Depends(require_plus),
    db: AsyncSession = Depends(get_db_session)
):
    """Get authentication service statistics (plus users only)"""
    return await auth_service.get_user_stats(db)


@app.get("/auth/history", tags=["authentication"])
async def get_analysis_history(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0
):
    """Get user's analysis history (requires authentication)"""
    from .services.database_service import db_service
    
    history = await db_service.get_user_analysis_history(
        db=db,
        user_id=int(current_user["user_id"]),
        limit=limit,
        offset=offset
    )
    
    return {
        "history": [
            {
                "id": record.id,
                "indicator": record.indicator,
                "indicator_type": record.indicator_type,
                "threat_score": record.threat_score,
                "risk_level": record.risk_level,
                "created_at": record.created_at,
                "analysis_data": record.analysis_data,
                "sources": record.sources
            }
            for record in history
        ],
        "total": len(history),
        "limit": limit,
        "offset": offset
    }


# Updated identity function using optional authentication
async def get_identity(user: Dict[str, str] = Depends(get_current_user_optional)) -> Dict[str, str]:
    """Get current user identity with optional authentication"""
    return user

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
        "risk level, and next steps in ≤5 sentences.\\n\\n"
        f"Indicator: {ioc}\\n\\n"
        f"VirusTotal snippet: {json.dumps(vt)[:1500]}\\n\\n"
        f"AbuseIPDB snippet: {json.dumps(abuse)[:800]}\\n\\n"
    )
    if urlscan:
        prompt += f"URLScan snippet: {json.dumps(urlscan)[:800]}\\n\\n"

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
        "summary_markdown, charts, verdict.\\n"
        "charts must include analysis_stats (bar) and engine_donut (doughnut).\\n\\n"
        f"Indicator: {ioc} ({ind_t})\\n"
        f"VirusTotal attributes: {json.dumps(vt_attrs)[:12000]}\\n"
        f"AbuseIPDB snippet: {json.dumps(abuse)[:800]}\\n"
    )

    if urlscan:
        prompt += f"URLScan snippet: {json.dumps(urlscan)[:800]}\\n"

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
    """Generic VirusTotal API proxy"""
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
    """VirusTotal file analysis"""
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
    """VirusTotal IP analysis"""
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
    """VirusTotal domain analysis"""
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
    """VirusTotal URL analysis"""
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


# ───────────────────────── Premium Analysis Endpoints (JWT Protected) ─────────────────────────────

@app.post("/analyze/premium", response_model=ThreatIntelligenceResult, tags=["premium-analysis"])
async def analyze_premium(
    req: SimpleIndicatorRequest, 
    current_user: Dict[str, str] = Depends(require_medium),
    db: AsyncSession = Depends(get_db_session)
) -> ThreatIntelligenceResult:
    """Premium threat intelligence analysis (requires Medium+ subscription)"""
    
    # Perform the analysis
    result = await threat_analysis_service.analyze_indicator(
        indicator=req.indicator,
        user_id=current_user["user_id"],
        subscription=current_user["subscription"],
        include_raw=req.include_raw_data or True,  # Premium users get raw data by default
        enhanced_analysis=True  # Premium analysis features
    )
    
    # Store result in database
    from .utils.indicator import determine_indicator_type
    from .services.database_service import db_service
    
    indicator_type = determine_indicator_type(req.indicator)
    await db_service.store_analysis_result(
        db=db,
        user_id=int(current_user["user_id"]),
        indicator=req.indicator,
        indicator_type=indicator_type.value,
        result=result
    )
    
    return result


@app.post("/analyze/enterprise", response_model=ThreatIntelligenceResult, tags=["enterprise-analysis"])
async def analyze_enterprise(
    req: SimpleIndicatorRequest, 
    current_user: Dict[str, str] = Depends(require_plus),
    db: AsyncSession = Depends(get_db_session)
) -> ThreatIntelligenceResult:
    """Enterprise threat intelligence analysis (requires Plus+ subscription)"""
    
    # Perform the analysis
    result = await threat_analysis_service.analyze_indicator(
        indicator=req.indicator,
        user_id=current_user["user_id"],
        subscription=current_user["subscription"],
        include_raw=True,
        enhanced_analysis=True,
        deep_analysis=True  # Enterprise-only deep analysis
    )
    
    # Store result in database
    from .utils.indicator import determine_indicator_type
    from .services.database_service import db_service
    
    indicator_type = determine_indicator_type(req.indicator)
    await db_service.store_analysis_result(
        db=db,
        user_id=int(current_user["user_id"]),
        indicator=req.indicator,
        indicator_type=indicator_type.value,
        result=result
    )
    
    return result


@app.post("/analyze/batch/premium", tags=["premium-analysis"])
async def analyze_batch_premium(
    request: BulkAnalysisRequest,
    current_user: Dict[str, str] = Depends(require_medium)
) -> BulkAnalysisResponse:
    """Premium batch analysis (requires Medium+ subscription)"""
    # Check batch size limits based on subscription
    subscription_limits = {
        "medium": 10,
        "plus": 50,
        "admin": 100
    }
    
    max_batch_size = subscription_limits.get(current_user["subscription"], 5)
    if len(request.indicators) > max_batch_size:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Batch size limit exceeded. {current_user['subscription']} subscription allows max {max_batch_size} indicators"
        )
      # Track API usage
    await auth_service.update_api_usage(current_user["user_id"])
    
    results = []
    for indicator_data in request.indicators:
        try:
            req = SimpleIndicatorRequest(
                indicator=indicator_data.get("value"),
                include_raw_data=True
            )
            result = await threat_analysis_service.analyze_indicator(
                indicator=req.indicator,
                user_id=current_user["user_id"],
                subscription=current_user["subscription"],
                include_raw=True,
                enhanced_analysis=True
            )
            results.append({
                "indicator": req.indicator,
                "type": indicator_data.get("type"),
                "analysis": result.model_dump(),
                "status": "success"
            })
        except Exception as e:
            results.append({
                "indicator": indicator_data.get("value"),
                "type": indicator_data.get("type"),
                "error": str(e),
                "status": "failed"
            })
    
    return BulkAnalysisResponse(
        results=results,
        total_processed=len(results),
        successful=len([r for r in results if r.get("status") == "success"]),
        failed=len([r for r in results if r.get("status") == "failed"]),
        user_id=current_user["user_id"],
        subscription_level=current_user["subscription"]
    )



# ───────────────────────── Protected Analysis History ─────────────────────────────

@app.get("/analyze/history", tags=["user-analytics"])
async def get_analysis_history(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    indicator_type: Optional[str] = None,
    threat_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's analysis history with filtering options (requires authentication)"""
    from .services.database_service import db_service
    
    user_id = int(current_user["user_id"])
    
    # Get filtered analysis history from database
    history_records = await db_service.get_user_analysis_history_filtered(
        db, user_id, limit, offset, search, indicator_type, threat_level, date_from, date_to
    )
    
    # Get total count for pagination (with same filters)
    total_count = await db_service.get_user_analysis_count_filtered(
        db, user_id, search, indicator_type, threat_level, date_from, date_to
    )
    
    analyses = []
    for record in history_records:
        analyses.append({
            "id": record.id,
            "indicator": record.indicator,
            "indicator_type": record.indicator_type,
            "threat_score": record.threat_score,
            "risk_level": record.risk_level,
            "analyzed_at": record.created_at.isoformat(),
            "analysis_data": record.analysis_data
        })
    
    return {
        "user_id": current_user["user_id"],
        "subscription": current_user["subscription"],
        "total_analyses": total_count,
        "analyses": analyses,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }


@app.get("/analyze/stats", tags=["user-analytics"])
async def get_user_analysis_stats(
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user's analysis statistics (requires authentication)"""
    from .services.database_service import db_service
    
    user_id = int(current_user["user_id"])
    stats = await db_service.get_user_stats(db, user_id)
    
    return {
        "user_id": current_user["user_id"],
        "subscription": current_user["subscription"],
        "usage_stats": {
            "total_analyses": stats["total_analyses"],
            "this_month": stats["month_analyses"],
            "this_week": stats["week_analyses"],
            "today": stats["today_analyses"]
        },
        "risk_breakdown": stats["risk_breakdown"],
        "type_breakdown": stats["type_breakdown"],
        "high_risk_findings": stats["high_risk_findings_this_month"],
        "subscription_limits": {
            "daily_limit": 100 if current_user["subscription"] in ["plus", "admin"] else 20,
            "monthly_limit": 3000 if current_user["subscription"] in ["plus", "admin"] else 500,
            "batch_size_limit": 50 if current_user["subscription"] in ["plus", "admin"] else 10
        },
        "feature_access": {
            "raw_data": current_user["subscription"] in ["medium", "plus", "admin"],
            "batch_analysis": current_user["subscription"] in ["medium", "plus", "admin"],
            "deep_analysis": current_user["subscription"] in ["plus", "admin"],
            "priority_processing": current_user["subscription"] in ["plus", "admin"]
        }
    }


# ───────────────────────── Enhanced Analyze route ───────────────────────────
@app.post("/analyze", response_model=ThreatIntelligenceResult, tags=["analysis"])
async def analyze_enhanced(
    req: SimpleIndicatorRequest, 
    ident: Dict[str, str] = Depends(get_identity),
    db: AsyncSession = Depends(get_db_session)
) -> ThreatIntelligenceResult:
    """Enhanced unified threat intelligence analysis"""
    # Perform the analysis
    result = await threat_analysis_service.analyze_indicator(
        indicator=req.indicator,
        user_id=ident["user_id"],
        subscription=ident["subscription"],
        include_raw=req.include_raw_data
    )
    
    # Store result in database if user is authenticated (not anonymous)
    if ident["user_id"] != "anonymous":
        try:
            from .utils.indicator import determine_indicator_type
            from .services.database_service import db_service
            
            indicator_type = determine_indicator_type(req.indicator)
            await db_service.store_analysis_result(
                db=db,
                user_id=int(ident["user_id"]),
                indicator=req.indicator,
                indicator_type=indicator_type.value,
                result=result
            )
        except Exception as db_error:
            # Log the error but don't fail the analysis
            logger.warning(f"Failed to store analysis result in database: {db_error}")
    
    return result


# ───────────────────────── Legacy Analyze route (for backward compatibility) ───────────────────────────
@app.post("/analyze/legacy", tags=["analysis"])
async def analyze_legacy(
    req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)
):
    """Legacy analysis endpoint with raw response format"""
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
            base64.urlsafe_b64encode(req.indicator.encode()).decode().rstrip("=")        )
    
    vt_json = await vt_task
    abuse_json = await abuse_task if abuse_task else {"note": "n/a"}
    gpt_json = await _call_openai(
        typ, req.indicator, vt_json, abuse_json, urlscan_json
    )

    # Enhanced response with metadata
    return {
        "indicator": req.indicator,
        "indicator_type": typ,
        "analysis_timestamp": datetime.now(UTC).isoformat(),
        "sources": {
            "virustotal": vt_json,
            "abuseipdb": abuse_json,
            "urlscan": urlscan_json,
            "openai_analysis": gpt_json,
        },
        "metadata": {
            "user_id": ident["user_id"],
            "subscription_level": ident["subscription"],
            "analysis_version": "1.0.0"
        }
    }


# ───────────────────────── Enhanced Visualize route ─────────────────────────
@app.post("/api/visualize", response_model=VizResponse, tags=["visualize"])
async def visualize(
    req: IndicatorRequest, ident: Dict[str, str] = Depends(get_identity)
):
    """Enhanced visualization with improved error handling"""
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
        asyncio.create_task(_call_abuseipdb(req.indicator)) if typ == "ip" else None    )

    urlscan_json = {}
    # URLScan integration removed due to missing implementation

    vt_json = await vt_task
    abuse_json = await abuse_task if abuse_task else {"note": "n/a"}
    
    viz = await _openai_visualize(
            typ,
            req.indicator,
            vt_json.get("data", {}).get("attributes", {}),
            abuse_json,
            urlscan_json,
        )
    return JSONResponse(viz)


# ───────────────────────── Analysis Endpoints ─────────────────────────────
@app.post("/analyze/ip/{ip}", response_model=ThreatIntelligenceResult, tags=["analysis"])
async def analyze_ip(ip: str, ident: Dict[str, str] = Depends(get_identity)):
    """Analyze IP address"""
    req = SimpleIndicatorRequest(indicator=ip)
    return await analyze_enhanced(req, ident)

@app.post("/analyze/domain/{domain}", response_model=ThreatIntelligenceResult, tags=["analysis"])
async def analyze_domain(domain: str, ident: Dict[str, str] = Depends(get_identity)):
    """Analyze domain"""
    req = SimpleIndicatorRequest(indicator=domain)
    return await analyze_enhanced(req, ident)

@app.post("/analyze/url/{url:path}", response_model=ThreatIntelligenceResult, tags=["analysis"])
async def analyze_url(url: str, ident: Dict[str, str] = Depends(get_identity)):
    """Analyze URL"""
    req = SimpleIndicatorRequest(indicator=url)
    return await analyze_enhanced(req, ident)

@app.post("/analyze/hash/{hash}", response_model=ThreatIntelligenceResult, tags=["analysis"])
async def analyze_hash(hash: str, ident: Dict[str, str] = Depends(get_identity)):
    """Analyze file hash"""
    req = SimpleIndicatorRequest(indicator=hash)
    return await analyze_enhanced(req, ident)

@app.post("/analyze/batch", tags=["analysis"])
async def analyze_batch(
    request: Dict[str, Any], 
    ident: Dict[str, str] = Depends(get_identity)
):
    """Analyze multiple indicators in batch"""
    indicators = request.get("indicators", [])
    if not indicators:
        raise HTTPException(400, "No indicators provided")
    
    results = []
    for indicator_data in indicators:
        try:
            indicator_value = indicator_data.get("value")
            if not indicator_value:
                continue
                
            req = SimpleIndicatorRequest(indicator=indicator_value)
            result = await analyze_enhanced(req, ident)
            results.append({
                "indicator": indicator_value,
                "type": indicator_data.get("type"),
                "analysis": result.model_dump()
            })
        except Exception as e:
            results.append({
                "indicator": indicator_data.get("value"),
                "type": indicator_data.get("type"),
                "error": str(e)
            })
    
    return {"results": results}


# ───────────────────────── Enhanced Meta/health/monitoring ─────────────────────────────
@app.get("/health", tags=["meta"])
async def health():
    """Enhanced health check endpoint"""
    return {
        "status": "OK",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "services": {
            "virustotal": bool(os.getenv("VIRUSTOTAL_API_KEY")),
            "abuseipdb": bool(ABUSE_KEY),
            "urlscan": bool(URLSCAN_KEY),
            "openai": bool(OPENAI_KEY)
        }
    }


@app.get("/status", tags=["monitoring"]) 
async def system_status():
    """System status endpoint"""
    return {
        "system": {
            "status": "operational",
            "version": "1.0.0"
        },
        "external_apis": {
            "virustotal": {"status": "connected" if os.getenv("VIRUSTOTAL_API_KEY") else "disconnected"},
            "abuseipdb": {"status": "connected" if ABUSE_KEY else "disconnected"},
            "urlscan": {"status": "connected" if URLSCAN_KEY else "disconnected"},
            "openai": {"status": "connected" if OPENAI_KEY else "disconnected"}        }
    }


# ───────────────────────── Local run helper ─────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8686)), reload=True
    )
