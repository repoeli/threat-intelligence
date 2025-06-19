# Threat Intelligence API - Testing Guide

## Quick Start Testing

### 1. Start the Server
```bash
# Start the standalone FastAPI server (recommended for testing)
python start_standalone.py
```
The server will be available at:
- API: http://localhost:8687
- Documentation: http://localhost:8687/docs
- Alternative docs: http://localhost:8687/redoc

### 2. Run API Tests
```bash
# Test basic API endpoints
python test_api.py

# Test authentication system
python test_auth_api.py

# Test specific port
python test_standalone_8687.py
```

### 3. Run Automated Tests
```bash
# Run all tests
python run_tests.py

# Or run specific test categories
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_ml_classifier.py -v
python -m pytest tests/test_intelligence_fusion.py -v
```

## Available Endpoints

### Analysis Endpoints
- POST `/analyze/ip/{ip}` - Analyze IP address
- POST `/analyze/domain/{domain}` - Analyze domain
- POST `/analyze/url/{url}` - Analyze URL  
- POST `/analyze/hash/{hash}` - Analyze file hash
- POST `/analyze/batch` - Batch analysis

### Authentication Endpoints
- POST `/auth/register` - Register new user
- POST `/auth/login` - Login and get JWT token
- GET `/auth/profile` - Get user profile (requires auth)

### System Endpoints
- GET `/health` - Health check
- GET `/debug/app-info` - App information
- GET `/docs` - API documentation

## Expected Test Results

When everything is working correctly:
1. **Analysis Endpoints**: Should return threat level and confidence scores
2. **Authentication**: JWT tokens should be generated and validated
3. **Documentation**: Interactive API docs should be accessible

## Troubleshooting

### Common Issues:
1. **Port Conflicts**: Server runs on port 8687
2. **ML Dependencies**: sklearn/numpy may not be available (graceful fallback)
3. **Authentication**: Uses in-memory storage for testing

### Recent Fixes Applied:
- **Authentication API Fix**: Fixed login endpoint to accept JSON data instead of form data
- **Profile Endpoint**: Added missing `/auth/profile` endpoint to standalone server
- **Token Validation**: Implemented basic token validation for protected endpoints
- **User Conflict Fix**: Updated test to use timestamp-based unique emails to avoid "User already exists" errors
- **Syntax Error Fix**: Fixed indentation and syntax errors in `start_standalone.py` causing server crashes

### Authentication Test Fixes:
1. **Content-Type Issue**: 
   - **Problem**: Login endpoint expected JSON data but test was sending form data
   - **Fix**: Updated test to send `json=login_data` instead of `data=login_data`

2. **User Already Exists Issue**:
   - **Problem**: Test failed with 409 "User already exists" on subsequent runs
   - **Solution**: Use timestamp-based unique emails: `test_{timestamp}@example.com`
   - **Fixed Script**: `test_auth_api_fixed.py` (use this instead of `test_auth_api.py`)

3. **Server Syntax Error**:
   - **Problem**: TypeError in `start_standalone.py` causing 500 Internal Server Error
   - **Root Cause**: Missing line break between return statement and decorator
   - **Fix**: Corrected indentation and syntax throughout `start_standalone.py`
   - **Backup**: Broken version saved as `start_standalone_broken.py`

### Authentication Test Fix:
The authentication test was failing because:
- **Issue**: Login endpoint expected JSON data but test was sending form data
- **Fix**: Updated `test_auth_api.py` to send `json=login_data` instead of `data=login_data`
- **Result**: Authentication flow now works correctly (register → login → profile access)

### Environment Setup:
```bash
# Activate virtual environment
.venv\Scripts\activate

# Install dependencies  
pip install -r backend/requirements.txt

# Run tests
python test_standalone_8687.py
```

## Current Testing Status

### ✅ Successfully Fixed and Working:
1. **Authentication Test Content-Type**: Fixed `test_auth_api.py` to send JSON instead of form data
2. **User Conflict Prevention**: Added timestamp-based unique emails to avoid "User already exists" errors  
3. **Missing Authentication Endpoints**: Added `/auth/profile` endpoint to standalone server
4. **Server Syntax Error**: Fixed missing line break in `start_standalone.py`
5. **Missing Authentication Models**: Added `LoginRequest`, `UserRegistration`, etc. to `backend/app/models.py`
6. **Missing Authentication Classes**: Added `AuthService`, `UserRole`, `Permission` to `backend/app/auth.py`
7. **AuthService Unit Tests**: Fixed `tests/test_auth.py` to properly test `AuthService` class methods
8. **Bcrypt Dependency**: Installed bcrypt package for password hashing functionality

### 🎯 Current Status (Updated June 18, 2025)

### ✅ AUTHENTICATION TESTS - FULLY WORKING
- **All 9 authentication tests passing** ✅
- Fixed bcrypt dependency (installed successfully)
- Fixed test function returns vs assertions
- AuthService unit tests working correctly
- Password hashing and verification working
- User registration and authentication working

### 📊 Complete Test Suite Status

| Test Suite | Status | Tests | Issues |
|------------|--------|-------|--------|
| **Authentication Tests** | ✅ **PASS** | 9/9 | None - All working! |
| ML Classifier Tests | ❌ FAIL | 0/? | Missing `ThreatMLClassifier` class |
| Intelligence Fusion Tests | ❌ FAIL | 0/? | Missing `IntelligenceFusion` class |
| API Schema Tests | ❌ FAIL | 5/12 | Missing auth endpoints in main app |
| Performance Tests | ❌ FAIL | 3/10 | Missing `User` class, auth_service |
| Enhanced Analysis Tests | ❌ FAIL | ?/? | Missing `ThreatVerdict`, `RiskLevel` |

### 🔧 Remaining Issues to Address

1. **Missing Classes in Intelligence Modules**:
   - `ThreatMLClassifier` in `ml_classifier.py`
   - `IntelligenceFusion` in `fusion.py`

2. **Missing Models/Enums**:
   - `ThreatVerdict` and `RiskLevel` in `models.py`
   - `User` class in `auth.py`

3. **API Schema Issues**:
   - Main app missing auth endpoints (only in standalone)
   - Missing security schemes in OpenAPI

4. **Test Configuration Issues**:
   - Some tests expect different app structure
   - Mock fixtures need updating

### 🎉 Major Success
The core authentication system is now **fully functional** with:
- Proper password hashing with bcrypt
- User registration working
- User authentication working  
- Token creation working
- All unit tests passing

This resolves the main authentication issues that were blocking development!

## Troubleshooting

### Common Issues:
1. **Port Conflicts**: Server runs on port 8687
2. **ML Dependencies**: sklearn/numpy may not be available (graceful fallback)
3. **Authentication**: Uses in-memory storage for testing

### Recent Fixes Applied:
- **Authentication API Fix**: Fixed login endpoint to accept JSON data instead of form data
- **Profile Endpoint**: Added missing `/auth/profile` endpoint to standalone server
- **Token Validation**: Implemented basic token validation for protected endpoints
- **User Conflict Fix**: Updated test to use timestamp-based unique emails to avoid "User already exists" errors
- **Syntax Error Fix**: Fixed indentation and syntax errors in `start_standalone.py` causing server crashes

### Authentication Test Fixes:
1. **Content-Type Issue**: 
   - **Problem**: Login endpoint expected JSON data but test was sending form data
   - **Fix**: Updated test to send `json=login_data` instead of `data=login_data`

2. **User Already Exists Issue**:
   - **Problem**: Test failed with 409 "User already exists" on subsequent runs
   - **Solution**: Use timestamp-based unique emails: `test_{timestamp}@example.com`
   - **Fixed Script**: `test_auth_api_fixed.py` (use this instead of `test_auth_api.py`)

3. **Server Syntax Error**:
   - **Problem**: TypeError in `start_standalone.py` causing 500 Internal Server Error
   - **Root Cause**: Missing line break between return statement and decorator
   - **Fix**: Corrected indentation and syntax throughout `start_standalone.py`
   - **Backup**: Broken version saved as `start_standalone_broken.py`

### Authentication Test Fix:
The authentication test was failing because:
- **Issue**: Login endpoint expected JSON data but test was sending form data
- **Fix**: Updated `test_auth_api.py` to send `json=login_data` instead of `data=login_data`
- **Result**: Authentication flow now works correctly (register → login → profile access)

### Environment Setup:
```bash
# Activate virtual environment
.venv\Scripts\activate

# Install dependencies  
pip install -r backend/requirements.txt

# Run tests
python test_standalone_8687.py
```
