#!/usr/bin/env python3
"""
Quick frontend restart to apply proxy fixes
"""
import subprocess
import os
import sys
import time

def main():
    print("🔄 Restarting Frontend with Fixed Configuration...")
    print("=" * 50)
    print()
    
    # Navigate to frontend directory
    os.chdir("frontend")
    
    print("📋 Configuration Summary:")
    print("  ✅ Fixed vite.config.ts syntax errors")
    print("  ✅ Added missing vite.svg file")
    print("  ✅ Updated proxy to point to localhost:8686")
    print("  ✅ Fixed import paths")
    print()
    
    print("🚀 Starting development server...")
    print("   Frontend will be available at: http://localhost:3000")
    print("   Backend is running at: http://localhost:8686")
    print()
    
    try:
        # Start the dev server
        subprocess.run(["npm", "run", "dev"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Frontend server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting frontend: {e}")
        return 1
    except FileNotFoundError:
        print("❌ npm not found. Please ensure Node.js is installed.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
