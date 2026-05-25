from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, timedelta
import json

from app.models.workout import Workout, WorkoutExercise, WorkoutStatus
from app.models.exercise import Exercise
from app.models.user import User
from app.schemas.dashboard import DashboardStats, MuscleGroupStat, WeeklyProgressBar, PersonalRecord
from app.core.cache import cache_get, cache_set, CACHE_TTL


DASHBOARD_CACHE_KEY = "dashboard:{user_id}:stats"


def get_dashboard_stats(db: Session, user: User) -> DashboardStats:
    """Get dashboard stats, using Redis cache when available."""
    cache_key = DASHBOARD_CACHE_KEY.format(user_id=user.id)
    cached = cache_get(cache_key)
    if cached:
        cached["cached"] = True
        return DashboardStats(**cached)

    stats = _compute_dashboard(db, user)
    cache_set(cache_key, stats.model_dump(mode="json"), CACHE_TTL["dashboard"])
    return stats


def _compute_dashboard(db: Session, user: User) -> DashboardStats:
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Basic counts
    all_completed = db.query(Workout).filter(
        Workout.user_id == user.id,
        Workout.status == WorkoutStatus.COMPLETED,
    )

    total_all_time = all_completed.count()
    workouts_this_week = all_completed.filter(Workout.completed_at >= week_start).count()
    workouts_this_month = all_completed.filter(Workout.completed_at >= month_start).count()

    # Streak: consecutive days with at least one completed workout going back from today
    streak_days = _calculate_streak(db, user.id, now)

    # Total volume this week (sets * reps * weight_kg)
    volume_query = (
        db.query(func.coalesce(func.sum(
            WorkoutExercise.sets * WorkoutExercise.reps * WorkoutExercise.weight_kg
        ), 0))
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == user.id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at >= week_start,
        )
        .scalar()
    )
    total_volume_this_week = float(volume_query or 0)

    # Muscle group breakdown (all time)
    muscle_rows = (
        db.query(Exercise.muscle_group, func.count(WorkoutExercise.id), func.sum(WorkoutExercise.sets))
        .join(WorkoutExercise, Exercise.id == WorkoutExercise.exercise_id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(Workout.user_id == user.id, Workout.status == WorkoutStatus.COMPLETED)
        .group_by(Exercise.muscle_group)
        .all()
    )
    muscle_breakdown = [
        MuscleGroupStat(
            muscle_group=row[0],
            total_exercises=row[1],
            total_sets=int(row[2] or 0),
        )
        for row in muscle_rows
    ]

    # Personal records (max weight per exercise, last 30 days)
    pr_rows = (
        db.query(
            Exercise.name,
            func.max(WorkoutExercise.weight_kg),
            func.max(Workout.completed_at),
        )
        .join(WorkoutExercise, Exercise.id == WorkoutExercise.exercise_id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == user.id,
            Workout.status == WorkoutStatus.COMPLETED,
            WorkoutExercise.weight_kg.isnot(None),
            Workout.completed_at >= now - timedelta(days=30),
        )
        .group_by(Exercise.name)
        .order_by(func.max(Workout.completed_at).desc())
        .limit(5)
        .all()
    )
    personal_records = [
        PersonalRecord(
            exercise_name=row[0],
            weight_kg=float(row[1]),
            achieved_at=row[2],
        )
        for row in pr_rows
        if row[1] is not None
    ]

    # Weekly progress bars (last 8 weeks)
    weekly_bars = _build_weekly_bars(db, user.id, now)

    return DashboardStats(
        workouts_this_week=workouts_this_week,
        workouts_this_month=workouts_this_month,
        total_workouts_all_time=total_all_time,
        total_volume_this_week_kg=total_volume_this_week,
        streak_days=streak_days,
        muscle_group_breakdown=muscle_breakdown,
        recent_personal_records=personal_records,
        weekly_progress=weekly_bars,
        weekly_ai_summary=user.weekly_summary,
        summary_generated_at=user.weekly_summary_generated_at,
        cached=False,
        cache_generated_at=datetime.utcnow(),
    )


def _calculate_streak(db: Session, user_id: int, now: datetime) -> int:
    streak = 0
    check_date = now.date()
    for _ in range(365):
        day_start = datetime.combine(check_date, datetime.min.time())
        day_end = datetime.combine(check_date, datetime.max.time())
        worked = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at.between(day_start, day_end),
        ).count()
        if worked:
            streak += 1
            check_date -= timedelta(days=1)
        elif streak == 0:
            # Allow today to not yet have a workout
            check_date -= timedelta(days=1)
            continue
        else:
            break
    return streak


def _build_weekly_bars(db: Session, user_id: int, now: datetime) -> list:
    bars = []
    for week_offset in range(7, -1, -1):
        week_start = now - timedelta(days=now.weekday() + week_offset * 7)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        count = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at.between(week_start, week_end),
        ).count()

        vol = (
            db.query(func.coalesce(func.sum(
                WorkoutExercise.sets * WorkoutExercise.reps * WorkoutExercise.weight_kg
            ), 0))
            .join(Workout, WorkoutExercise.workout_id == Workout.id)
            .filter(
                Workout.user_id == user_id,
                Workout.status == WorkoutStatus.COMPLETED,
                Workout.completed_at.between(week_start, week_end),
            )
            .scalar()
        )

        bars.append(WeeklyProgressBar(
            week_label=f"{week_start.strftime('%b %d')} – {(week_end - timedelta(days=1)).strftime('%b %d')}",
            workouts_completed=count,
            total_volume_kg=float(vol or 0),
        ))
    return bars
