from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from jose import jwt

from app.core.database import get_db
from app.core.security import get_current_user, create_access_token
from app.core.config import get_settings
from app.core.cache import blacklist_token as redis_blacklist
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse
from app.services.auth_service import create_user, authenticate_user, get_token_for_user
from app.core.mongodb import logs_collection

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict, status_code=201, summary="Register a new user")
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Register a new user account."""
    user = create_user(db, user_data)
    token = get_token_for_user(user)

    # Log to MongoDB
    col = logs_collection()
    if col is not None:
        await col.insert_one({
            "event": "user_registered",
            "user_id": user.id,
            "username": user.username,
            "ip": request.client.host if request.client else None,
            "timestamp": datetime.utcnow(),
        })

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "access_token": token,
        "token_type": "Bearer",
    }


@router.post("/login", response_model=Token, summary="Login and get JWT token")
async def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Authenticate with email/password and receive a Bearer token."""
    user = authenticate_user(db, credentials.email, credentials.password)
    token = get_token_for_user(user)

    # Log to MongoDB
    col = logs_collection()
    if col is not None:
        await col.insert_one({
            "event": "user_login",
            "user_id": user.id,
            "username": user.username,
            "ip": request.client.host if request.client else None,
            "timestamp": datetime.utcnow(),
        })

    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/logout", summary="Logout and invalidate JWT token")
async def logout(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Blacklist the current JWT token in Redis.
    The token will be rejected on all future requests until it naturally expires.
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

    # Calculate remaining TTL from the token's exp claim
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp = payload.get("exp", 0)
        remaining = int(exp - datetime.utcnow().timestamp())
        ttl = max(remaining, 1)
    except Exception:
        pass

    redis_blacklist(token, ttl)

    # Log to MongoDB
    col = logs_collection()
    if col is not None:
        await col.insert_one({
            "event": "user_logout",
            "user_id": current_user.id,
            "username": current_user.username,
            "timestamp": datetime.utcnow(),
        })

    return {"message": "Logged out successfully. Token has been revoked."}


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def me(current_user=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
