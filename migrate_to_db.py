"""
Migration script to move data from JSON files to the database.
Run this once to migrate existing data.
"""
import asyncio
import json
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import AsyncSessionLocal, init_database
from backend.app.services.database_service import db_service
from backend.app.models import UserCreate


async def migrate_users_from_json():
    """Migrate users from users_db.json to the database."""
    json_file_path = Path("users_db.json")
    
    if not json_file_path.exists():
        print("No users_db.json found, skipping user migration")
        return
    
    async with AsyncSessionLocal() as db:
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Extract users from the nested structure
            users_data = data.get('users', {})
            print(f"Found {len(users_data)} users to migrate")
            
            for user_id, user_data in users_data.items():
                # Check if user already exists by email
                existing_user = await db_service.get_user_by_email(db, user_data['email'])
                if existing_user:
                    print(f"User {user_data['email']} already exists, skipping")
                    continue
                
                # Create user with existing hashed password
                from backend.app.db_models import User
                from datetime import datetime, timezone
                
                db_user = User(
                    username=user_data['email'].split('@')[0],  # Use email prefix as username
                    email=user_data['email'],
                    hashed_password=user_data['password_hash'],
                    is_active=user_data.get('is_active', True),
                    is_admin=user_data.get('is_admin', False),
                    created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00')) if user_data.get('created_at') else datetime.now(timezone.utc)
                )
                
                db.add(db_user)
                print(f"Migrated user: {user_data['email']}")
            
            await db.commit()
            print("User migration completed successfully")
            
        except Exception as e:
            print(f"Error during user migration: {e}")
            await db.rollback()
            raise


async def create_admin_user():
    """Create a default admin user if none exists."""
    async with AsyncSessionLocal() as db:
        # Check if any admin user exists
        from sqlalchemy import select
        from backend.app.db_models import User
        
        result = await db.execute(select(User).where(User.is_admin == True))
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            print(f"Admin user already exists: {admin_user.username}")
            return
          # Create default admin user
        admin_data = UserCreate(
            username="admin",
            email="admin@example.com",
            password="admin123"  # Change this in production!
        )
        
        from backend.app.db_models import User
        from datetime import datetime, timezone
        
        hashed_password = db_service._hash_password(admin_data.password)
        admin_user = User(
            username=admin_data.username,
            email=admin_data.email,
            hashed_password=hashed_password,
            is_active=True,
            is_admin=True,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(admin_user)
        await db.commit()
        print(f"Created admin user: {admin_data.username}")
        print("⚠️  Default password is 'admin123' - please change it immediately!")


async def main():
    """Run the migration."""
    print("Starting database migration...")
    
    # Initialize database (create tables)
    await init_database()
    print("Database tables created")
    
    # Migrate users
    await migrate_users_from_json()
    
    # Create admin user if needed
    await create_admin_user()
    
    print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(main())
