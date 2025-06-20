import asyncio
from backend.app.database import AsyncSessionLocal
from backend.app.services.database_service import db_service

async def test_user():
    async with AsyncSessionLocal() as db:
        user = await db_service.get_user_by_email(db, 'test@example.com')
        if user:
            print(f'Found user: {user.username} ({user.email})')
            print(f'Is active: {user.is_active}')
            print(f'Created at: {user.created_at}')
        else:
            print('No user found')

if __name__ == "__main__":
    asyncio.run(test_user())
