from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service
from app.services.ai_summary_service import generate_weekly_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardStats, summary="Get user dashboard stats")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns aggregated fitness stats for the authenticated user.
    Results are cached in Redis for 5 minutes.
    Includes weekly AI-generated progress summary.
    """
    return dashboard_service.get_dashboard_stats(db, current_user)


@router.post("/summary/generate", summary="Trigger AI weekly summary generation")
async def generate_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger the AI weekly progress summary for the current user.
    Normally this runs on a weekly schedule; this endpoint lets you force a refresh.
    """
    summary = await generate_weekly_summary(db, current_user)
    return {"summary": summary}
