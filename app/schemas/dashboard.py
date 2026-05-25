from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MuscleGroupStat(BaseModel):
    muscle_group: str
    total_sets: int
    total_exercises: int


class WeeklyProgressBar(BaseModel):
    week_label: str      # e.g. "May 12 - May 18"
    workouts_completed: int
    total_volume_kg: float  # sum of sets * reps * weight


class PersonalRecord(BaseModel):
    exercise_name: str
    weight_kg: float
    achieved_at: datetime


class DashboardStats(BaseModel):
    # This week
    workouts_this_week: int
    workouts_this_month: int
    total_workouts_all_time: int

    # Volume
    total_volume_this_week_kg: float
    streak_days: int

    # Breakdown
    muscle_group_breakdown: List[MuscleGroupStat]
    recent_personal_records: List[PersonalRecord]
    weekly_progress: List[WeeklyProgressBar]  # last 8 weeks

    # AI Summary
    weekly_ai_summary: Optional[str] = None
    summary_generated_at: Optional[datetime] = None

    # Cache metadata
    cached: bool = False
    cache_generated_at: Optional[datetime] = None
