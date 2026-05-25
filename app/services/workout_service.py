from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, desc
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime, timedelta

from app.models.workout import Workout, WorkoutExercise, WorkoutStatus
from app.models.exercise import Exercise
from app.schemas.workout import WorkoutCreate, WorkoutUpdate, WorkoutExerciseCreate
from app.core.cache import cache_delete_pattern


def get_workout_or_404(db: Session, workout_id: int, user_id: int) -> Workout:
    workout = (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.exercise))
        .filter(Workout.id == workout_id, Workout.user_id == user_id)
        .first()
    )
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


def create_workout(db: Session, user_id: int, data: WorkoutCreate) -> Workout:
    workout = Workout(
        user_id=user_id,
        title=data.title,
        notes=data.notes,
        scheduled_at=data.scheduled_at,
        status=WorkoutStatus.SCHEDULED,
    )
    db.add(workout)
    db.flush()  # get workout.id

    for ex_data in data.exercises:
        _validate_exercise(db, ex_data.exercise_id)
        we = WorkoutExercise(workout_id=workout.id, **ex_data.model_dump())
        db.add(we)

    db.commit()
    db.refresh(workout)
    _invalidate_user_cache(user_id)
    return get_workout_or_404(db, workout.id, user_id)


def update_workout(db: Session, workout_id: int, user_id: int, data: WorkoutUpdate) -> Workout:
    workout = get_workout_or_404(db, workout_id, user_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)
    db.commit()
    db.refresh(workout)
    _invalidate_user_cache(user_id)
    return get_workout_or_404(db, workout_id, user_id)


def delete_workout(db: Session, workout_id: int, user_id: int) -> None:
    workout = db.query(Workout).filter(
        Workout.id == workout_id, Workout.user_id == user_id
    ).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    db.delete(workout)
    db.commit()
    _invalidate_user_cache(user_id)


def list_workouts(
    db: Session,
    user_id: int,
    status_filter: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Workout]:
    q = (
        db.query(Workout)
        .options(joinedload(Workout.exercises).joinedload(WorkoutExercise.exercise))
        .filter(Workout.user_id == user_id)
    )
    if status_filter:
        q = q.filter(Workout.status == status_filter)
    if from_date:
        q = q.filter(Workout.scheduled_at >= from_date)
    if to_date:
        q = q.filter(Workout.scheduled_at <= to_date)

    return q.order_by(Workout.scheduled_at.asc().nullslast(), Workout.created_at.desc()).offset(skip).limit(limit).all()


def add_exercise_to_workout(
    db: Session, workout_id: int, user_id: int, data: WorkoutExerciseCreate
) -> Workout:
    workout = db.query(Workout).filter(
        Workout.id == workout_id, Workout.user_id == user_id
    ).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    _validate_exercise(db, data.exercise_id)
    we = WorkoutExercise(workout_id=workout_id, **data.model_dump())
    db.add(we)
    db.commit()
    _invalidate_user_cache(user_id)
    return get_workout_or_404(db, workout_id, user_id)


def remove_exercise_from_workout(
    db: Session, workout_id: int, workout_exercise_id: int, user_id: int
) -> Workout:
    workout = db.query(Workout).filter(
        Workout.id == workout_id, Workout.user_id == user_id
    ).first()
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")

    we = db.query(WorkoutExercise).filter(
        WorkoutExercise.id == workout_exercise_id,
        WorkoutExercise.workout_id == workout_id,
    ).first()
    if not we:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise entry not found")

    db.delete(we)
    db.commit()
    _invalidate_user_cache(user_id)
    return get_workout_or_404(db, workout_id, user_id)


def get_progress_report(
    db: Session,
    user_id: int,
    exercise_id: Optional[int] = None,
    muscle_group: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> dict:
    """Returns historical performance data for the progress report endpoint."""
    from_date = from_date or (datetime.utcnow() - timedelta(days=90))
    to_date = to_date or datetime.utcnow()

    q = (
        db.query(WorkoutExercise, Workout, Exercise)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
        .filter(
            Workout.user_id == user_id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at.between(from_date, to_date),
        )
    )
    if exercise_id:
        q = q.filter(WorkoutExercise.exercise_id == exercise_id)
    if muscle_group:
        q = q.filter(Exercise.muscle_group == muscle_group)

    rows = q.order_by(Workout.completed_at.asc()).all()

    # Group into time-series per exercise
    from collections import defaultdict
    series: dict = defaultdict(list)
    for we, workout, exercise in rows:
        series[exercise.name].append({
            "date": workout.completed_at.isoformat() if workout.completed_at else None,
            "workout_id": workout.id,
            "workout_title": workout.title,
            "sets": we.sets,
            "reps": we.reps,
            "weight_kg": we.weight_kg,
            "duration_seconds": we.duration_seconds,
            "distance_meters": we.distance_meters,
            "volume_kg": (we.sets or 0) * (we.reps or 0) * (we.weight_kg or 0),
        })

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "exercise_series": dict(series),
        "total_workouts_in_period": len(set(we.workout_id for we, _, _ in rows)),
    }


def _validate_exercise(db: Session, exercise_id: int):
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id={exercise_id} not found",
        )


def _invalidate_user_cache(user_id: int):
    cache_delete_pattern(f"dashboard:{user_id}:*")
    cache_delete_pattern(f"workouts:{user_id}:*")
