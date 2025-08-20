
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ActivityLogBase(BaseModel):
    action_type: str
    status: str
    target_subreddit: Optional[str] = None
    content_preview: Optional[str] = None
    reddit_id: Optional[str] = None
    error_message: Optional[str] = None

class ActivityLogCreate(ActivityLogBase):
    account_id: int
    schedule_id: Optional[int] = None

class ActivityLog(ActivityLogBase):
    id: int
    user_id: int
    account_id: int
    schedule_id: Optional[int] = None
    response_data: Optional[dict] = None
    execution_time: datetime

    class Config:
        from_attributes = True

class AnalyticsResponse(BaseModel):
    total_actions: int
    successful_actions: int
    failed_actions: int
    success_rate: float
    actions_by_type: dict
    actions_by_status: dict
    actions_by_day: dict