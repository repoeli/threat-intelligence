#!/usr/bin/env python3
"""
Simple test verification script
"""
import subprocess
import sys
import os

def run_tests():
    """Run pytest and capture results"""
    try:
        # Change to the project directory
        os.chdir(r'c:\threat-intelligence')
        
        # Activate virtual environment and run tests
        cmd = [
            sys.executable, 
            '-m', 'pytest', 
            'tests/', 
            '--tb=short',
            '-v'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=r'c:\threat-intelligence')
        
        print("=== PYTEST OUTPUT ===")
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
        # Parse results
        output = result.stdout
        if "failed" in output.lower():
            print("\n❌ Some tests failed")
        elif "passed" in output.lower():
            print("\n✅ Tests appear to be passing")
        else:
            print("\n⚠️ Could not determine test status")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    run_tests()
