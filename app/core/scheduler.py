"""
Background scheduler that generates weekly AI summaries for all active users.
Runs every Sunday at midnight UTC.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.services.ai_summary_service import generate_weekly_summary

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def generate_all_weekly_summaries():
    """Task: generate AI summaries for every active user."""
    logger.info("Starting weekly AI summary generation for all users...")
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            try:
                await generate_weekly_summary(db, user)
                logger.info(f"Generated summary for user {user.id} ({user.username})")
            except Exception as e:
                logger.error(f"Failed to generate summary for user {user.id}: {e}")
    finally:
        db.close()


def start_scheduler():
    """Register and start the background scheduler (no-ops gracefully in tests)."""
    try:
        scheduler.add_job(
            generate_all_weekly_summaries,
            trigger="cron",
            day_of_week="sun",
            hour=0,
            minute=0,
            id="weekly_ai_summaries",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Background scheduler started.")
    except Exception as e:
        logger.warning(f"Scheduler could not start (non-fatal): {e}")


def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
    except Exception as e:
        logger.warning(f"Scheduler could not stop (non-fatal): {e}")
