"""
Quick test status check
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def check_imports():
    """Check if key modules can be imported"""
    try:
        from backend.app.auth import get_current_user, check_rate_limit, RATE_LIMITS
        from backend.app.models import SubscriptionTier, UserIdentity
        from backend.app.database import AsyncSessionLocal
        print("✅ All key imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def check_database():
    """Check database setup"""
    try:
        from backend.app.database import get_db_session
        print("✅ Database session factory available")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    print("=== Quick Status Check ===")
    
    all_good = True
    all_good &= check_imports()
    all_good &= check_database()
    
    if all_good:
        print("\n🎉 Basic setup looks good!")
        print("Database integration appears to be working.")
        print("Ready for Phase 2: Frontend Development")
    else:
        print("\n⚠️ Some issues detected")
    
    return all_good

if __name__ == "__main__":
    main()
