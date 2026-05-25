from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.workout import WorkoutStatus
from app.schemas.exercise import ExerciseResponse


class WorkoutExerciseCreate(BaseModel):
    exercise_id: int
    order_index: int = 0
    sets: Optional[int] = Field(None, ge=1, le=100)
    reps: Optional[int] = Field(None, ge=1, le=1000)
    weight_kg: Optional[float] = Field(None, ge=0)
    duration_seconds: Optional[int] = Field(None, ge=0)
    distance_meters: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class WorkoutExerciseUpdate(BaseModel):
    sets: Optional[int] = Field(None, ge=1, le=100)
    reps: Optional[int] = Field(None, ge=1, le=1000)
    weight_kg: Optional[float] = Field(None, ge=0)
    duration_seconds: Optional[int] = Field(None, ge=0)
    distance_meters: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    order_index: Optional[int] = None


class WorkoutExerciseResponse(BaseModel):
    id: int
    exercise_id: int
    exercise: ExerciseResponse
    order_index: int
    sets: Optional[int]
    reps: Optional[int]
    weight_kg: Optional[float]
    duration_seconds: Optional[int]
    distance_meters: Optional[float]
    notes: Optional[str]

    class Config:
        from_attributes = True


class WorkoutCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    exercises: List[WorkoutExerciseCreate] = []


class WorkoutUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    notes: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[WorkoutStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=0)


class WorkoutResponse(BaseModel):
    id: int
    title: str
    notes: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    exercises: List[WorkoutExerciseResponse] = []

    class Config:
        from_attributes = True


class WorkoutSummary(BaseModel):
    """Lightweight workout response for list views."""
    id: int
    title: str
    status: str
    scheduled_at: Optional[datetime]
    completed_at: Optional[datetime]
    exercise_count: int

    class Config:
        from_attributes = True
