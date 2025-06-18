#!/usr/bin/env python3
"""Standalone simplified server without complex imports."""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

def create_standalone_app():
    """Create a completely standalone FastAPI app for testing."""
    
    app = FastAPI(
        title="Threat Intelligence API - Standalone",
        version="1.0.0",
        description="Simplified standalone API for testing",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def mock_analyze_indicator(indicator: str, indicator_type: str):
        """Mock analysis function that returns consistent results."""
        return {
            "indicator": indicator,
            "indicator_type": indicator_type,
            "threat_level": "low",
            "confidence": 0.85,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "sources": {
                "virustotal": {"status": "clean", "engines_detected": 0},
                "abuseipdb": {"confidence": 0, "usage_type": "good"},
                "openai_analysis": "No immediate threats detected."
            },
            "verdict": "benign"
        }

    # Health check endpoint
    @app.get("/health", tags=["system"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "OK",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0-standalone"
        }

    # Debug endpoint
    @app.get("/debug/app-info", tags=["system"])
    async def app_info():
        """Get application information."""
        return {
            "name": "Threat Intelligence API",
            "version": "1.0.0-standalone",
            "mode": "standalone",
            "endpoints": ["analyze", "auth", "health", "docs"]
        }

    # Analysis endpoints
    @app.post("/analyze/ip/{ip}", tags=["analysis"])
    async def analyze_ip(ip: str):
        """Analyze IP address"""
        return mock_analyze_indicator(ip, "ip")

    @app.post("/analyze/domain/{domain}", tags=["analysis"])
    async def analyze_domain(domain: str):
        """Analyze domain"""
        return mock_analyze_indicator(domain, "domain")

    @app.post("/analyze/url/{url:path}", tags=["analysis"])
    async def analyze_url(url: str):
        """Analyze URL"""
        return mock_analyze_indicator(url, "url")

    @app.post("/analyze/hash/{hash}", tags=["analysis"])
    async def analyze_hash(hash: str):
        """Analyze file hash"""
        return mock_analyze_indicator(hash, "hash")

    @app.post("/analyze/batch", tags=["analysis"])
    async def analyze_batch(request: dict):
        """Analyze multiple indicators in batch"""
        indicators = request.get("indicators", [])
        results = []
        
        for indicator_data in indicators:
            indicator_value = indicator_data.get("value", "")
            indicator_type = indicator_data.get("type", "unknown")
            result = mock_analyze_indicator(indicator_value, indicator_type)
            results.append(result)
        
        return {"results": results}

    # Simple authentication endpoints (no dependencies)
    users_db = {}

    @app.post("/auth/register", status_code=201, tags=["authentication"])
    async def register_user(user_data: dict):
        """Register a new user (simplified)"""
        email = user_data.get("email")
        password = user_data.get("password")
        
        if not email or not password:
            raise HTTPException(400, "Email and password are required")
        
        if email in users_db:
            raise HTTPException(409, "User already exists")
        
        user_id = f"user_{len(users_db) + 1}"
        users_db[email] = {
            "user_id": user_id,
            "email": email,
            "password": password,  # In real app, hash this!
            "subscription_level": user_data.get("subscription_level", "free")
        }
        
        return {
            "user_id": user_id,
            "email": email,
            "message": "User registered successfully"
        }

    @app.post("/auth/login", tags=["authentication"])
    async def login_user(credentials: dict):
        """Login user (simplified)"""
        email = credentials.get("username") or credentials.get("email")
        password = credentials.get("password")
        
        if not email or not password:
            raise HTTPException(400, "Email and password are required")
        
        user = users_db.get(email)
        if not user or user["password"] != password:
            raise HTTPException(401, "Invalid credentials")
        
        return {
            "access_token": f"mock_token_{user['user_id']}",
            "token_type": "bearer",
            "user_id": user["user_id"]
        }

    @app.get("/auth/profile", tags=["authentication"])
    async def get_user_profile(request: Request):
        """Get user profile (simplified)"""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Simple token validation (in real app, use JWT verification)
        if not token.startswith("mock_token_"):
            raise HTTPException(401, "Invalid token")
        
        user_id = token.replace("mock_token_", "")
        
        # Find user by user_id
        for email, user_data in users_db.items():
            if user_data["user_id"] == user_id:
                return {
                    "user_id": user_data["user_id"],
                    "email": user_data["email"],
                    "subscription_level": user_data["subscription_level"]
                }
        
        raise HTTPException(404, "User not found")

    return app

if __name__ == "__main__":
    print("🚀 Starting Standalone Threat Intelligence API server...")
    print("📊 Server will be available at: http://localhost:8687")
    print("📚 API Documentation: http://localhost:8687/docs")
    print("⚠️  Note: This is a standalone version with mock data")
    print("\nPress Ctrl+C to stop the server")
    
    app = create_standalone_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8687,
        reload=False,
        log_level="info"
    )
