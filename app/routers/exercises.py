from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseResponse, ExerciseCreate

router = APIRouter(prefix="/exercises", tags=["Exercises"])


@router.get("/", response_model=List[ExerciseResponse], summary="List all exercises")
def list_exercises(
    category: Optional[str] = Query(None, description="Filter by category"),
    muscle_group: Optional[str] = Query(None, description="Filter by muscle group"),
    search: Optional[str] = Query(None, description="Search by name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Return the exercise library. Supports filtering by category, muscle group, and name search."""
    q = db.query(Exercise)
    if category:
        q = q.filter(Exercise.category == category)
    if muscle_group:
        q = q.filter(Exercise.muscle_group == muscle_group)
    if search:
        q = q.filter(Exercise.name.ilike(f"%{search}%"))
    return q.order_by(Exercise.name).offset(skip).limit(limit).all()


@router.get("/{exercise_id}", response_model=ExerciseResponse, summary="Get exercise by ID")
def get_exercise(exercise_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from fastapi import HTTPException, status
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return ex


@router.post("/", response_model=ExerciseResponse, status_code=201, summary="Create exercise (admin)")
def create_exercise(data: ExerciseCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Add a new exercise to the library."""
    from fastapi import HTTPException, status
    existing = db.query(Exercise).filter(Exercise.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Exercise with this name already exists")
    ex = Exercise(**data.model_dump())
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex
