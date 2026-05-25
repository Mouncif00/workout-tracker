from pydantic import BaseModel, Field
from typing import Optional
from app.models.exercise import ExerciseCategory, MuscleGroup


class ExerciseCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category: ExerciseCategory
    muscle_group: MuscleGroup
    equipment: Optional[str] = None
    instructions: Optional[str] = None


class ExerciseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    muscle_group: str
    equipment: Optional[str]
    instructions: Optional[str]

    class Config:
        from_attributes = True


class ExerciseFilter(BaseModel):
    category: Optional[ExerciseCategory] = None
    muscle_group: Optional[MuscleGroup] = None
    search: Optional[str] = None
