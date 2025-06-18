#!/usr/bin/env python3
"""Script to start the FastAPI server for testing."""

import uvicorn
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    print("🚀 Starting Threat Intelligence API server...")
    print("📊 Server will be available at: http://localhost:8686")
    print("📚 API Documentation: http://localhost:8686/docs")
    print("🔍 Alternative docs: http://localhost:8686/redoc")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8686,
        reload=True,
        log_level="info"
    )
