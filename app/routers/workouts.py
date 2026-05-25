from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.workout import (
    WorkoutCreate, WorkoutUpdate, WorkoutResponse,
    WorkoutExerciseCreate,
)
from app.services import workout_service

router = APIRouter(prefix="/workouts", tags=["Workouts"])


@router.get("/scheduled", response_model=List[WorkoutResponse], summary="Get upcoming scheduled workouts")
def get_scheduled(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all scheduled (pending) workouts sorted by date ascending."""
    return workout_service.list_workouts(
        db, current_user.id, status_filter="scheduled"
    )




@router.get("/reports/progress", summary="Get detailed progress time-series")
def progress_report(
    exercise_id: Optional[int] = Query(None),
    muscle_group: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns historical exercise performance data for charting progress."""
    return workout_service.get_progress_report(
        db, current_user.id, exercise_id, muscle_group, from_date, to_date
    )




@router.get("/", response_model=List[WorkoutResponse], summary="List all user workouts")
def list_workouts(
    status: Optional[str] = Query(None, description="Filter: scheduled|in_progress|completed|skipped"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List workouts for the authenticated user, sorted by scheduled date."""
    return workout_service.list_workouts(
        db, current_user.id, status, from_date, to_date, skip, limit
    )


@router.post("/", response_model=dict, status_code=201, summary="Create a workout")
def create_workout(
    data: WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workout plan with optional exercises and a scheduled date."""
    workout = workout_service.create_workout(db, current_user.id, data)
    return {"message": "Workout created successfully", "workout_id": workout.id}


@router.get("/{workout_id}", response_model=WorkoutResponse, summary="Get workout by ID")
def get_workout(
    workout_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return workout_service.get_workout_or_404(db, workout_id, current_user.id)


@router.put("/{workout_id}", response_model=dict, summary="Update a workout")
def update_workout(
    data: WorkoutUpdate,
    workout_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update workout details, status, notes, or schedule."""
    workout_service.update_workout(db, workout_id, current_user.id, data)
    return {"message": "Workout updated successfully"}


@router.delete("/{workout_id}", response_model=dict, summary="Delete a workout")
def delete_workout(
    workout_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout_service.delete_workout(db, workout_id, current_user.id)
    return {"message": "Workout deleted successfully"}


@router.post(
    "/{workout_id}/exercises",
    response_model=WorkoutResponse,
    status_code=201,
    summary="Add an exercise to a workout",
)
def add_exercise(
    data: WorkoutExerciseCreate,
    workout_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return workout_service.add_exercise_to_workout(db, workout_id, current_user.id, data)


@router.delete(
    "/{workout_id}/exercises/{workout_exercise_id}",
    response_model=dict,
    summary="Remove an exercise from a workout",
)
def remove_exercise(
    workout_id: int = Path(...),
    workout_exercise_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout_service.remove_exercise_from_workout(
        db, workout_id, workout_exercise_id, current_user.id
    )
    return {"message": "Exercise removed from workout"}


