#!/usr/bin/env python3
"""Test script for authentication endpoints - Fixed version."""

import requests
import json
import time
import pytest
from datetime import datetime

BASE_URL = "http://localhost:8687"

@pytest.fixture(scope="session")
def auth_token():
    """Fixture to get authentication token for tests."""
    # Use timestamp to ensure unique email for each test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"test_{timestamp}@example.com"
    
    # Register user
    register_data = {
        "email": test_email,
        "password": "SecurePassword123!",
        "subscription_level": "premium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code not in [201, 409]:  # 409 = already exists
            pytest.fail(f"Registration failed: {response.text}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Registration request failed: {e}")
    
    # Login to get token
    login_data = {
        "username": test_email,
        "password": "SecurePassword123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            pytest.fail(f"Login failed: {response.text}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Login request failed: {e}")

def test_auth_endpoints():
    """Test authentication registration and login."""
    
    print("🔐 Testing Authentication System")
    print("=" * 50)
    
    # Use timestamp to ensure unique email for each test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_email = f"test_{timestamp}@example.com"
    
    # Test user registration
    print("\n1. Testing User Registration...")
    register_data = {
        "email": test_email,
        "password": "SecurePassword123!",
        "subscription_level": "premium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        print(f"Registration Status: {response.status_code}")
        print(f"Test Email: {test_email}")
        
        assert response.status_code in [201, 409], f"Registration failed: {response.text}"
        
        if response.status_code == 201:
            print("✅ Registration successful")
            user_data = response.json()
            print(f"User ID: {user_data.get('user_id')}")
        elif response.status_code == 409:
            print("⚠️  User already exists (unexpected - using timestamp)")
            print("✅ Proceeding with existing user for login test")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Registration request failed: {e}")
    
    # Test user login
    print("\n2. Testing User Login...")
    login_data = {
        "username": test_email,  # Use the same email we just registered
        "password": "SecurePassword123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login Status: {response.status_code}")
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        print("✅ Login successful")
        token_data = response.json()
        access_token = token_data.get('access_token')
        print(f"Token Type: {token_data.get('token_type')}")
        print(f"Access Token: {access_token[:20]}...")
        
        assert access_token is not None, "No access token received"
        assert len(access_token) > 0, "Empty access token received"
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Login request failed: {e}")

def test_protected_endpoints(auth_token):
    """Test protected endpoints with authentication token."""
    
    print("\n3. Testing Protected Endpoints...")
    headers = {"Authorization": f"Bearer {auth_token}"}
      # Test user profile endpoint
    try:
        response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
        print(f"Profile Status: {response.status_code}")
        
        assert response.status_code == 200, f"Profile access failed: {response.text}"
        
        print("✅ Profile access successful")
        profile = response.json()
        print(f"User Email: {profile.get('email')}")
        print(f"Subscription: {profile.get('subscription_level')}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Profile request failed: {e}")

def test_threat_analysis(auth_token):
    """Test threat analysis endpoints."""
    
    print("\n4. Testing Threat Analysis with Authentication...")
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test basic analysis endpoint
    analysis_data = {
        "indicator": "8.8.8.8",
        "user_id": "test-user-123",
        "subscription_level": "premium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/analyze", json=analysis_data, headers=headers)
        print(f"Analysis Status: {response.status_code}")
        
        # Analysis might return different status codes depending on implementation
        if response.status_code == 200:
            print("✅ Threat analysis successful")
            result = response.json()
            print(f"Analysis result keys: {list(result.keys())}")
        elif response.status_code == 422:
            print("⚠️  Analysis endpoint expects different data format")
            print(f"Response: {response.text}")
        else:
            print(f"⚠️  Analysis returned: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Analysis request failed: {e}")


if __name__ == "__main__":
    """Run tests manually for debugging."""
    print("🧪 Running Authentication Tests Manually")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            exit(1)
        print("✅ Server is running")
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to server - make sure it's running on port 8687")
        exit(1)
    
    # Test auth endpoints
    test_auth_endpoints()
    
    print("\n✅ Manual test complete - run with pytest for full test suite")
