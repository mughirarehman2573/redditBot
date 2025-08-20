# backend/app/api/endpoints/activity.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.models import User
from backend.app.schemas.activity import ActivityLog, AnalyticsResponse
from backend.app.services.activity_service import get_activity_logs_for_user, get_analytics_for_user

router = APIRouter()

@router.get("/", response_model=List[ActivityLog])
def list_activity_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None,
    days: int = 7
):
    """Get activity logs for the current user."""
    logs = get_activity_logs_for_user(db, current_user.id, skip, limit, account_id, days)
    return logs

@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 30
):
    """Get analytics and statistics for the current user."""
    return get_analytics_for_user(db, current_user.id, days)