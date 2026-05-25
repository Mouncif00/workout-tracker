import redis
import json
from typing import Optional, Any
from app.core.config import get_settings

settings = get_settings()

_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    client = get_redis()
    if client is None:
        return None
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception:
        return False


def cache_delete(key: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception:
        return False


def cache_delete_pattern(pattern: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
        return True
    except Exception:
        return False


def blacklist_token(token: str, ttl_seconds: int) -> bool:
    """Add a JWT to the blacklist with TTL matching remaining token lifetime."""
    client = get_redis()
    if client is None:
        return False
    try:
        client.setex(f"blacklist:{token}", ttl_seconds, "1")
        return True
    except Exception:
        return False


# Cache TTLs (seconds)
CACHE_TTL = {
    "dashboard": 300,        # 5 minutes
    "exercise_list": 3600,   # 1 hour
    "workout_list": 60,      # 1 minute
    "weekly_summary": 3600,  # 1 hour
    "reports": 600,          # 10 minutes
}
