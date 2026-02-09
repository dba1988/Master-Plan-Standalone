# TASK-003: Auth Endpoints

**Phase**: 1 - Foundation
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-002

## Objective

Implement JWT authentication with secure refresh token rotation.

## Description

Create authentication endpoints:
- Login with email/password
- Refresh token rotation
- Logout (revoke tokens)
- Get current user

## Files to Create/Modify

```
admin-service/api/app/
├── core/
│   └── security.py
├── schemas/
│   └── auth.py
├── api/
│   └── auth.py
└── services/
    └── auth_service.py
```

## Implementation Steps

### Step 1: Security Utilities
```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import hashlib
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
```

### Step 2: Auth Schemas
```python
# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
```

### Step 3: Auth Service
```python
# app/services/auth_service.py
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, RefreshToken
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, hash_token
)
from app.core.config import settings

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    async def create_tokens(self, user: User) -> tuple[str, str]:
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

    async def refresh_tokens(self, refresh_token: str) -> Optional[tuple[str, str]]:
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
```

### Step 4: Auth Endpoints
```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token, refresh_token = await service.create_tokens(user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role
        )
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    tokens = await service.refresh_tokens(request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    access_token, refresh_token = tokens
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/logout")
async def logout(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AuthService(db)
    await service.revoke_token(request.refresh_token)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role
    )
```

### Step 5: Auth Dependency
```python
# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user

def require_role(allowed_roles: list[str]):
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return role_checker
```

## Acceptance Criteria

- [ ] Can login with valid credentials
- [ ] Returns JWT access token (15 min expiry)
- [ ] Returns refresh token (7 day expiry)
- [ ] Can refresh access token
- [ ] Refresh token rotates on use
- [ ] Can logout (revokes refresh token)
- [ ] Protected routes reject invalid tokens
- [ ] Password hashed with bcrypt

## Security Notes

- Refresh tokens stored as SHA-256 hash
- Access tokens are stateless JWT
- Token rotation prevents replay attacks
- Add rate limiting in production
