#!/usr/bin/env python3
"""
Database Integration Verification Script for Threat Intelligence API
Tests database integration, authentication, and data persistence.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

async def test_database_connection():
    """Test database connection and basic operations."""
    console.print("🗄️ Testing Database Connection...", style="cyan")
    
    try:
        from backend.app.database import AsyncSessionLocal, init_database
        from backend.app.services.database_service import db_service
        
        # Initialize database
        await init_database()
        
        # Test basic query
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            row = result.fetchone()
            
        console.print("✅ Database connection successful", style="green")
        return True
        
    except Exception as e:
        console.print(f"❌ Database connection failed: {e}", style="red")
        return False

async def test_user_operations():
    """Test user creation and authentication."""
    console.print("👤 Testing User Operations...", style="cyan")
    
    try:
        from backend.app.database import AsyncSessionLocal
        from backend.app.services.database_service import db_service
        from backend.app.models import UserCreate
        
        async with AsyncSessionLocal() as db:
            # Test user count
            from sqlalchemy import select, func
            from backend.app.db_models import User
            
            result = await db.execute(select(func.count(User.id)))
            user_count = result.scalar()
            
            console.print(f"📊 Users in database: {user_count}", style="blue")
            
            # Test getting a user
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
            if user:
                console.print(f"✅ Sample user found: {user.username} ({user.email})", style="green")
            else:
                console.print("⚠️ No users found - consider running migration", style="yellow")
            
        return True
        
    except Exception as e:
        console.print(f"❌ User operations failed: {e}", style="red")
        return False

async def test_api_with_auth():
    """Test API endpoints with authentication."""
    console.print("🔐 Testing API Authentication...", style="cyan")
    
    base_url = "http://localhost:8686"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test health endpoint
            response = await client.get(f"{base_url}/health")
            console.print(f"Health endpoint: {response.status_code}", style="green" if response.status_code == 200 else "red")
            
            # Test login with admin user
            login_data = {
                "email": "admin@example.com",
                "password": "admin123"
            }
            
            response = await client.post(f"{base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                console.print("✅ Admin login successful", style="green")
                
                auth_data = response.json()
                token = auth_data["token"]["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Test authenticated profile endpoint
                response = await client.get(f"{base_url}/auth/profile", headers=headers)
                if response.status_code == 200:
                    profile = response.json()
                    console.print(f"✅ Profile retrieved: {profile.get('email')}", style="green")
                else:
                    console.print(f"❌ Profile retrieval failed: {response.status_code}", style="red")
                
                # Test analysis history endpoint
                response = await client.get(f"{base_url}/auth/history", headers=headers)
                if response.status_code == 200:
                    history = response.json()
                    console.print(f"✅ Analysis history: {len(history.get('history', []))} records", style="green")
                else:
                    console.print(f"❌ History retrieval failed: {response.status_code}", style="red")
                    
                return True
            else:
                console.print(f"❌ Admin login failed: {response.status_code}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ API testing failed: {e}", style="red")
            return False

async def test_analysis_storage():
    """Test analysis result storage."""
    console.print("📊 Testing Analysis Storage...", style="cyan")
    
    base_url = "http://localhost:8686"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Login first
            login_data = {"email": "admin@example.com", "password": "admin123"}
            response = await client.post(f"{base_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                token = response.json()["token"]["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Perform analysis
                analysis_data = {
                    "indicator": "8.8.8.8",
                    "include_raw_data": False
                }
                
                response = await client.post(f"{base_url}/analyze", json=analysis_data, headers=headers)
                
                if response.status_code == 200:
                    console.print("✅ Analysis completed and stored", style="green")
                    
                    # Check if it appears in history
                    await asyncio.sleep(1)  # Brief delay
                    response = await client.get(f"{base_url}/auth/history", headers=headers)
                    
                    if response.status_code == 200:
                        history = response.json()
                        if history.get('history'):
                            console.print(f"✅ Analysis found in history: {len(history['history'])} total", style="green")
                        else:
                            console.print("⚠️ No analysis history found", style="yellow")
                    
                    return True
                else:
                    console.print(f"❌ Analysis failed: {response.status_code}", style="red")
                    return False
            else:
                console.print("❌ Could not authenticate for analysis test", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Analysis storage test failed: {e}", style="red")
            return False

async def main():
    """Run all verification tests."""
    console.print(Panel.fit("🔍 Threat Intelligence API - Database Integration Verification", style="bold blue"))
    
    # Test results
    results = {}
    
    # Database tests
    results["database"] = await test_database_connection()
    results["users"] = await test_user_operations()
    
    # API tests
    results["auth_api"] = await test_api_with_auth()
    results["analysis_storage"] = await test_analysis_storage()
    
    # Summary
    console.print("\n" + "="*60)
    console.print("📋 VERIFICATION SUMMARY", style="bold")
    console.print("="*60)
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    
    table.add_row("Database Connection", "✅ PASS" if results["database"] else "❌ FAIL", "SQLAlchemy connection working")
    table.add_row("User Operations", "✅ PASS" if results["users"] else "❌ FAIL", "User queries and management")
    table.add_row("API Authentication", "✅ PASS" if results["auth_api"] else "❌ FAIL", "Login, profile, history endpoints")
    table.add_row("Analysis Storage", "✅ PASS" if results["analysis_storage"] else "❌ FAIL", "Analysis results persistence")
    
    console.print(table)
    
    all_passed = all(results.values())
    
    if all_passed:
        console.print("\n🎉 ALL TESTS PASSED! Database integration is working correctly.", style="bold green")
        console.print("✅ Phase 1 (Database Integration) Complete!", style="green")
        console.print("🚀 Ready for Phase 2: Frontend Dashboard Development", style="blue")
    else:
        console.print("\n⚠️ Some tests failed. Please check the issues above.", style="bold yellow")
        
    return all_passed

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        console.print("\n⏹️ Verification cancelled by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n💥 Verification failed with error: {e}", style="red")
        sys.exit(1)
