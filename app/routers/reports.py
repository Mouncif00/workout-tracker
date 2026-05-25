"""
Reports & Progress endpoints.
GET /reports/progress   — overall workout stats
GET /reports/monthly    — monthly summary
GET /reports/exercises  — most-used exercises analysis
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.cache import cache_get, cache_set, CACHE_TTL
from app.core.mongodb import analytics_collection
from app.models.workout import Workout, WorkoutExercise, WorkoutStatus
from app.models.exercise import Exercise
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["Reports & Progress"])


@router.get("/progress", summary="Generate workout progress report")
async def progress_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns overall workout statistics for the authenticated user.
    Cached in Redis for 10 minutes. Snapshot also saved to MongoDB.
    """
    cache_key = f"reports:progress:{current_user.id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    base = db.query(Workout).filter(Workout.user_id == current_user.id)

    total = base.count()
    completed = base.filter(Workout.status == WorkoutStatus.COMPLETED).count()
    pending = base.filter(Workout.status == WorkoutStatus.SCHEDULED).count()
    in_progress = base.filter(Workout.status == WorkoutStatus.IN_PROGRESS).count()
    skipped = base.filter(Workout.status == WorkoutStatus.SKIPPED).count()

    result = {
        "total_workouts": total,
        "completed_workouts": completed,
        "pending_workouts": pending,
        "in_progress_workouts": in_progress,
        "cancelled_workouts": skipped,
    }

    cache_set(cache_key, result, CACHE_TTL["reports"])

    # Save snapshot to MongoDB analytics_snapshots
    col = analytics_collection()
    if col is not None:
        await col.insert_one({
            "type": "progress_report",
            "user_id": current_user.id,
            "data": result,
            "generated_at": datetime.utcnow(),
        })

    return result


@router.get("/monthly", summary="Get monthly workout summary")
async def monthly_report(
    year: Optional[int] = Query(None, description="Year (defaults to current)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month 1-12 (defaults to current)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a summary of workouts for a given month.
    Defaults to the current month. Cached in Redis for 10 minutes.
    """
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month

    cache_key = f"reports:monthly:{current_user.id}:{year}:{month}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Month boundaries
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    month_label = start.strftime("%B %Y")

    workouts = (
        db.query(Workout)
        .filter(
            Workout.user_id == current_user.id,
            Workout.created_at >= start,
            Workout.created_at < end,
        )
        .all()
    )

    completed = [w for w in workouts if w.status == WorkoutStatus.COMPLETED]

    # Average duration
    durations = [w.duration_minutes for w in completed if w.duration_minutes]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else None

    # Total volume
    volume = (
        db.query(func.coalesce(func.sum(
            WorkoutExercise.sets * WorkoutExercise.reps * WorkoutExercise.weight_kg
        ), 0))
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == current_user.id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at >= start,
            Workout.completed_at < end,
        )
        .scalar()
    )

    # Simple intensity label
    wc = len(completed)
    if wc == 0:
        intensity = "none"
    elif wc <= 2:
        intensity = "low"
    elif wc <= 4:
        intensity = "medium"
    else:
        intensity = "high"

    result = {
        "month": month_label,
        "year": year,
        "workouts_total": len(workouts),
        "workouts_completed": wc,
        "workouts_pending": len([w for w in workouts if w.status == WorkoutStatus.SCHEDULED]),
        "average_duration_minutes": avg_duration,
        "total_volume_kg": round(float(volume or 0), 2),
        "average_intensity": intensity,
    }

    cache_set(cache_key, result, CACHE_TTL["reports"])

    # Save to MongoDB
    col = analytics_collection()
    if col is not None:
        await col.insert_one({
            "type": "monthly_report",
            "user_id": current_user.id,
            "year": year,
            "month": month,
            "data": result,
            "generated_at": datetime.utcnow(),
        })

    return result


@router.get("/exercises", summary="Analyze most used exercises")
async def exercises_report(
    limit: int = Query(10, ge=1, le=50, description="Number of top exercises to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the most frequently used exercises for the authenticated user,
    ranked by usage count. Cached in Redis for 10 minutes.
    """
    cache_key = f"reports:exercises:{current_user.id}:{limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    rows = (
        db.query(
            Exercise.name,
            Exercise.muscle_group,
            Exercise.category,
            func.count(WorkoutExercise.id).label("usage_count"),
            func.max(WorkoutExercise.weight_kg).label("max_weight_kg"),
            func.sum(WorkoutExercise.sets).label("total_sets"),
        )
        .join(WorkoutExercise, Exercise.id == WorkoutExercise.exercise_id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(Workout.user_id == current_user.id)
        .group_by(Exercise.id, Exercise.name, Exercise.muscle_group, Exercise.category)
        .order_by(func.count(WorkoutExercise.id).desc())
        .limit(limit)
        .all()
    )

    result = [
        {
            "exercise_name": row.name,
            "muscle_group": row.muscle_group,
            "category": row.category,
            "usage_count": row.usage_count,
            "max_weight_kg": float(row.max_weight_kg) if row.max_weight_kg else None,
            "total_sets": int(row.total_sets) if row.total_sets else 0,
        }
        for row in rows
    ]

    cache_set(cache_key, result, CACHE_TTL["reports"])
    return result
