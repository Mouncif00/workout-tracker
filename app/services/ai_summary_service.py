"""
AI-powered weekly progress summary using Hugging Face Inference API.
Model: facebook/bart-large-cnn (free, no billing required)
Fallback: rule-based summary if token not set or API unavailable.


"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
import httpx
import json

from app.models.workout import Workout, WorkoutExercise, WorkoutStatus
from app.models.exercise import Exercise
from app.models.user import User
from app.core.config import get_settings
from app.core.cache import cache_get, cache_set, CACHE_TTL

settings = get_settings()

# Free HuggingFace model — summarisation
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"


async def generate_weekly_summary(db: Session, user: User) -> str:
    """
    Generate a natural-language weekly summary for the user.
    Cached for 1 hour. Uses HuggingFace free inference API.
    """
   # cache_key = f"weekly_summary:{user.id}"
    #cached = cache_get(cache_key)
    #if cached:
     #   return cached
    

    context = _build_weekly_context(db, user)
    summary = await _call_huggingface(user.username, context)

    # Persist to user row
    user.weekly_summary = summary
    user.weekly_summary_generated_at = datetime.utcnow()
    db.commit()

   # cache_set(cache_key, summary, CACHE_TTL["weekly_summary"])
    return summary


def _build_weekly_context(db: Session, user: User) -> dict:
    """Collect structured stats for the current week."""
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    completed_workouts = (
        db.query(Workout)
        .filter(
            Workout.user_id == user.id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at >= week_start,
        )
        .all()
    )

    exercise_stats = {}
    for workout in completed_workouts:
        for we in workout.exercises:
            ex_name = we.exercise.name if we.exercise else f"exercise #{we.exercise_id}"
            if ex_name not in exercise_stats:
                exercise_stats[ex_name] = {"max_weight": 0, "total_sets": 0}
            s = exercise_stats[ex_name]
            s["max_weight"] = max(s["max_weight"], we.weight_kg or 0)
            s["total_sets"] += we.sets or 0

    # Compare to previous week for PRs
    prev_week_start = week_start - timedelta(days=7)
    prev_prs = {}
    prev_exercises = (
        db.query(WorkoutExercise.exercise_id, func.max(WorkoutExercise.weight_kg))
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == user.id,
            Workout.status == WorkoutStatus.COMPLETED,
            Workout.completed_at.between(prev_week_start, week_start),
        )
        .group_by(WorkoutExercise.exercise_id)
        .all()
    )
    for ex_id, max_w in prev_exercises:
        ex = db.query(Exercise).filter(Exercise.id == ex_id).first()
        if ex:
            prev_prs[ex.name] = max_w or 0

    new_prs = [
        f"{name}: {stats['max_weight']}kg"
        for name, stats in exercise_stats.items()
        if stats["max_weight"] > prev_prs.get(name, 0) and stats["max_weight"] > 0
    ]

    return {
        "training_days": len(completed_workouts),
        "exercises": exercise_stats,
        "new_personal_records": new_prs,
        "week_of": week_start.strftime("%B %d, %Y"),
        "username": user.username,
    }


async def _call_huggingface(username: str, context: dict) -> str:
    """
    Call HuggingFace Inference API (free tier).
    Uses bart-large-cnn to summarise a structured text paragraph.
    """
    if not settings.HUGGINGFACE_API_TOKEN:
        return _fallback_summary(context)

    days = context["training_days"]
    exercises = context["exercises"]
    prs = context["new_personal_records"]

    # Build a readable paragraph for the model to summarise
    ex_lines = ", ".join(
        f"{name} ({s['total_sets']} sets, max {s['max_weight']}kg)"
        for name, s in list(exercises.items())[:6]
    )
    pr_text = f" New personal records: {', '.join(prs)}." if prs else ""
    input_text = (
        f"{username} trained {days} day{'s' if days != 1 else ''} during the week of "
        f"{context['week_of']}. Exercises completed: {ex_lines or 'none'}.{pr_text} "
        f"Total unique exercises: {len(exercises)}."
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                HF_API_URL,
                headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"},
                json={
                    "inputs": input_text,
                    "parameters": {
                        "max_length": 80,
                        "min_length": 30,
                        "do_sample": False,
                    },
                },
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    return data[0].get("summary_text", _fallback_summary(context))
            # Model loading (503) — fall back gracefully
            return _fallback_summary(context)
    except Exception:
        return _fallback_summary(context)


def _fallback_summary(context: dict) -> str:
    """Rule-based summary — used when HuggingFace is unavailable or token not set."""
    days = context["training_days"]
    prs = context["new_personal_records"]
    exercises = context["exercises"]

    if days == 0:
        return "No workouts recorded this week — time to get back on track next week!"

    pr_text = (
        f" You hit {len(prs)} new personal record(s): {', '.join(prs)}."
        if prs else ""
    )
    return (
        f"Great week, {context['username']}! You trained {days} day{'s' if days != 1 else ''} "
        f"and worked through {len(exercises)} different exercise(s).{pr_text} Keep up the momentum!"
    )
