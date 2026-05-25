"""
Workout Comments — stored in MongoDB (workout_comments collection).
Schema per document:
{
  workout_id: int,
  user_id: int,
  username: str,
  content: str,
  created_at: datetime,
}
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from bson import ObjectId

from app.core.security import get_current_user
from app.core.mongodb import comments_collection, logs_collection
from app.models.user import User

router = APIRouter(prefix="/workouts", tags=["Comments"])


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    id: str
    workout_id: int
    user_id: int
    username: str
    content: str
    created_at: datetime


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.post(
    "/{workout_id}/comments",
    response_model=CommentResponse,
    status_code=201,
    summary="Add a comment to a workout",
)
async def add_comment(
    data: CommentCreate,
    workout_id: int = Path(...),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to a workout. Stored in MongoDB."""
    col = comments_collection()
    if col is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Comment service unavailable (MongoDB not connected)",
        )

    doc = {
        "workout_id": workout_id,
        "user_id": current_user.id,
        "username": current_user.username,
        "content": data.content,
        "created_at": datetime.utcnow(),
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


@router.get(
    "/{workout_id}/comments",
    response_model=List[CommentResponse],
    summary="Get all comments for a workout",
)
async def get_comments(
    workout_id: int = Path(...),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all comments for a workout. Stored in MongoDB."""
    col = comments_collection()
    if col is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Comment service unavailable (MongoDB not connected)",
        )

    cursor = col.find({"workout_id": workout_id}).sort("created_at", 1)
    docs = await cursor.to_list(length=100)
    return [_serialize(doc) for doc in docs]


@router.delete(
    "/{workout_id}/comments/{comment_id}",
    status_code=204,
    summary="Delete a comment",
)
async def delete_comment(
    workout_id: int = Path(...),
    comment_id: str = Path(...),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment. Only the comment author can delete it."""
    col = comments_collection()
    if col is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")

    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid comment ID")

    doc = await col.find_one({"_id": oid, "workout_id": workout_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if doc["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's comment")

    await col.delete_one({"_id": oid})
