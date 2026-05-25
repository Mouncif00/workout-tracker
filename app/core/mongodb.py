"""
MongoDB connection using Motor (async driver).
Collections:
  - workout_comments   : comments added to workouts
  - activity_logs      : user activity history
  - analytics_snapshots: generated progress snapshots
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> Optional[AsyncIOMotorClient]:
    global _client
    if _client is None:
        try:
            _client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=3000,
            )
        except Exception:
            _client = None
    return _client


def get_db():
    client = get_client()
    if client is None:
        return None
    return client[settings.MONGODB_DB]


# Collection helpers (return None gracefully if Mongo unavailable)
def comments_collection():
    db = get_db()
    return db["workout_comments"] if db is not None else None


def logs_collection():
    db = get_db()
    return db["activity_logs"] if db is not None else None


def analytics_collection():
    db = get_db()
    return db["analytics_snapshots"] if db is not None else None


async def close_mongo():
    global _client
    if _client:
        _client.close()
        _client = None
