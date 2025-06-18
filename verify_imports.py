import sys
import traceback

def test_imports():
    """Test all critical imports"""
    tests = [
        ("backend.app.models", "Testing models import"),
        ("backend.app.auth", "Testing auth import"),
        ("backend.app.services.auth_service", "Testing auth service import"),
        ("backend.app.services.threat_analysis", "Testing threat analysis import"),
        ("backend.app.main", "Testing main app import")
    ]
    
    results = []
    for module, description in tests:
        try:
            __import__(module)
            results.append(f"✓ {description}")
        except Exception as e:
            results.append(f"✗ {description}: {e}")
            traceback.print_exc()
    
    return results

if __name__ == "__main__":
    print("Testing critical imports...")
    results = test_imports()
    for result in results:
        print(result)
    
    # Test basic functionality
    try:
        from backend.app.services.threat_analysis import threat_analysis_service
        print(f"✓ Service type: {type(threat_analysis_service).__name__}")
    except Exception as e:
        print(f"✗ Service instantiation failed: {e}")
