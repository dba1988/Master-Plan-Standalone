from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.config import settings
from app.lib.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.models.user import RefreshToken, User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        return user

    async def create_tokens(self, user: User) -> Tuple[str, str]:
        """Create access and refresh tokens for a user."""
        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )

        # Create refresh token
        refresh_token = create_refresh_token()
        token_hash = hash_token(refresh_token)

        # Store refresh token hash in DB
        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        )
        self.db.add(db_token)
        await self.db.commit()

        return access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """Refresh access token using a valid refresh token. Implements token rotation."""
        token_hash = hash_token(refresh_token)

        # Find valid token
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at == None,
                RefreshToken.expires_at > datetime.utcnow()
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            return None

        # Get user
        result = await self.db.execute(
            select(User).where(User.id == db_token.user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Revoke old token (rotation)
        db_token.revoked_at = datetime.utcnow()

        # Create new tokens
        return await self.create_tokens(user)

    async def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token (logout)."""
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        db_token = result.scalar_one_or_none()

        if db_token:
            db_token.revoked_at = datetime.utcnow()
            await self.db.commit()
            return True

        return False

    async def revoke_all_user_tokens(self, user_id) -> int:
        """Revoke all refresh tokens for a user."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at == None
            )
        )
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.revoked_at = datetime.utcnow()
            count += 1

        await self.db.commit()
        return count
