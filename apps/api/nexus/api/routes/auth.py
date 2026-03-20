"""Authentication routes — JWT login, refresh, logout, password change."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from nexus.config import settings
from nexus.dependencies import get_pg_connection, get_token_blacklist
from nexus.models.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    TokenPayload,
    ChangePasswordRequest,
)
from nexus.services.password_policy import PasswordPolicy, PasswordPolicyError
from nexus.services.token_blacklist import TokenBlacklist

router = APIRouter()
security = HTTPBearer()


def _create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn=Depends(get_pg_connection),
    blacklist: TokenBlacklist = Depends(get_token_blacklist),
) -> UserResponse:
    """Validate JWT and return current user."""
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        token_data = TokenPayload(**payload)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Check if token has been revoked
    jti = payload.get("jti")
    if jti and await blacklist.is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1 AND is_active = TRUE", token_data.sub)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return UserResponse(
        id=str(row["id"]),
        username=row["username"],
        email=row["email"],
        role=row["role"],
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, conn=Depends(get_pg_connection)):
    """Register a new user and return JWT tokens."""
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    try:
        PasswordPolicy.validate(request.password)
    except PasswordPolicyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Check username uniqueness
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE username = $1", request.username
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )

    # Check email uniqueness
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1", request.email
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    password_hash = PasswordPolicy.hash(request.password)
    row = await conn.fetchrow(
        "INSERT INTO users (username, email, password_hash, role) "
        "VALUES ($1, $2, $3, 'viewer') RETURNING id, role",
        request.username,
        request.email,
        password_hash,
    )

    access_token = _create_token(
        {"sub": str(row["id"]), "role": row["role"]},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    refresh_token = _create_token(
        {"sub": str(row["id"]), "role": row["role"]},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, conn=Depends(get_pg_connection)):
    """Authenticate user and return JWT tokens."""
    row = await conn.fetchrow(
        "SELECT * FROM users WHERE username = $1 AND is_active = TRUE", request.username
    )
    if not row or not PasswordPolicy.verify(request.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = _create_token(
        {"sub": str(row["id"]), "role": row["role"]},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    refresh_token = _create_token(
        {"sub": str(row["id"]), "role": row["role"]},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    blacklist: TokenBlacklist = Depends(get_token_blacklist),
):
    """Revoke the current access token."""
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    jti = payload.get("jti")
    if jti:
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 0)
        await blacklist.blacklist(jti, ttl_seconds=ttl)

    return {"detail": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn=Depends(get_pg_connection),
    blacklist: TokenBlacklist = Depends(get_token_blacklist),
):
    """Refresh access token using a valid refresh token."""
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Check if refresh token has been revoked
    jti = payload.get("jti")
    if jti and await blacklist.is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1 AND is_active = TRUE", payload["sub"])
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Blacklist the old refresh token
    if jti:
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 0)
        await blacklist.blacklist(jti, ttl_seconds=ttl)

    access_token = _create_token(
        {"sub": str(row["id"]), "role": row["role"]},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    new_refresh = _create_token(
        {"sub": str(row["id"]), "role": row["role"]},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user),
    conn=Depends(get_pg_connection),
):
    """Change the current user's password."""
    row = await conn.fetchrow("SELECT password_hash FROM users WHERE id = $1", current_user.id)
    if not row or not PasswordPolicy.verify(request.current_password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    try:
        PasswordPolicy.validate(request.new_password)
    except PasswordPolicyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    new_hash = PasswordPolicy.hash(request.new_password)
    await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE id = $2",
        new_hash,
        current_user.id,
    )

    return {"detail": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get the current authenticated user."""
    return current_user
