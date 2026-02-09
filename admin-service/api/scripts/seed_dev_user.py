#!/usr/bin/env python3
"""Seed script to create a development admin user."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.lib.database import AsyncSessionLocal
from app.lib.security import get_password_hash
from app.models.user import User


async def seed():
    """Create a development admin user."""
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User already exists: {existing_user.email}")
            return

        user = User(
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            name="Admin User",
            role="admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Created user: {user.email} (password: admin123)")


if __name__ == "__main__":
    asyncio.run(seed())
