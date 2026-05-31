from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import get_current_user, create_access_token
from app.core.config import get_settings
from app.core.cache import blacklist_token as redis_blacklist
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse
from app.services.auth_service import create_user, authenticate_user, get_token_for_user
from app.core.mongodb import logs_collection

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@limiter.limit("3/minute")
@router.post("/register", response_model=dict, status_code=201, summary="Register a new user")
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account. Rate limited to 3 requests per minute per IP."""
    user = create_user(db, user_data)
    token = get_token_for_user(user)

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


@limiter.limit("5/minute")
@router.post("/login", response_model=Token, summary="Login and get JWT token")
async def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email/password. Rate limited to 5 requests per minute per IP."""
    user = authenticate_user(db, credentials.email, credentials.password)
    token = get_token_for_user(user)

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
    """Blacklist the current JWT token in Redis."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

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