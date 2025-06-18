#!/usr/bin/env python3

try:
    from backend.app.services.threat_analysis import threat_analysis_service
    print("✓ Service imports successfully")
    print(f"✓ Service class: {type(threat_analysis_service).__name__}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
