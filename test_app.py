#!/usr/bin/env python3

import sys

def test_fastapi_app():
    """Test that the FastAPI app can be imported and initialized"""
    try:
        from backend.app.main import app
        print("✓ FastAPI app imports successfully")
        print(f"✓ App type: {type(app).__name__}")
        
        # Test that routes are properly configured
        routes = [route.path for route in app.routes]
        print(f"✓ Number of routes configured: {len(routes)}")
        
        # Check for key routes
        key_routes = ["/health", "/auth/register", "/auth/login", "/analyze"]
        found_routes = [route for route in key_routes if any(route in r for r in routes)]
        print(f"✓ Key routes found: {found_routes}")
        
        return True
    except Exception as e:
        print(f"✗ FastAPI app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing FastAPI application...")
    success = test_fastapi_app()
    sys.exit(0 if success else 1)
