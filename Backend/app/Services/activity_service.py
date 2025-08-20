# backend/app/services/activity_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from backend.app.models.models import ActivityLog
from backend.app.schemas.activity import ActivityLogCreate
from typing import Optional



def create_activity_log(db: Session, user_id: int, log_data: ActivityLogCreate):
    """Create a new activity log entry."""
    db_log = ActivityLog(
        **log_data.dict(),
        user_id=user_id,
        execution_time=datetime.now()
    )

    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_activity_logs_for_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        account_id: Optional[int] = None,
        days: int = 7
):
    """Get activity logs for a user with optional filtering."""
    query = db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.execution_time >= datetime.now() - timedelta(days=days)
    )

    if account_id:
        query = query.filter(ActivityLog.account_id == account_id)

    return query.order_by(desc(ActivityLog.execution_time)).offset(skip).limit(limit).all()


def get_analytics_for_user(db: Session, user_id: int, days: int = 30):
    """Get analytics and statistics for a user."""
    # Base query
    query = db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.execution_time >= datetime.now() - timedelta(days=days)
    )

    # Total actions
    total_actions = query.count()

    # Successful vs failed actions
    successful_actions = query.filter(ActivityLog.status == "success").count()
    failed_actions = total_actions - successful_actions
    success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0

    # Actions by type
    actions_by_type = db.query(
        ActivityLog.action_type,
        func.count(ActivityLog.id)
    ).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.execution_time >= datetime.now() - timedelta(days=days)
    ).group_by(ActivityLog.action_type).all()

    # Actions by status
    actions_by_status = db.query(
        ActivityLog.status,
        func.count(ActivityLog.id)
    ).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.execution_time >= datetime.now() - timedelta(days=days)
    ).group_by(ActivityLog.status).all()

    # Actions by day (last 7 days)
    actions_by_day = db.query(
        func.date(ActivityLog.execution_time).label('date'),
        func.count(ActivityLog.id)
    ).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.execution_time >= datetime.now() - timedelta(days=7)
    ).group_by('date').order_by('date').all()

    return {
        "total_actions": total_actions,
        "successful_actions": successful_actions,
        "failed_actions": failed_actions,
        "success_rate": round(success_rate, 2),
        "actions_by_type": dict(actions_by_type),
        "actions_by_status": dict(actions_by_status),
        "actions_by_day": dict(actions_by_day)
    }