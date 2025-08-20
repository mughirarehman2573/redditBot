# backend/app/schemas/task_schedule.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from backend.app.schemas.reddit_account import RedditAccount
from backend.app.schemas.content import ContentPool

class TaskScheduleBase(BaseModel):
    name: str
    task_type: str  # post, comment, vote
    frequency_type: str  # hourly, daily, weekly
    frequency_value: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: bool = True
    is_warmup: bool = False
    warmup_level: int = 1
    randomize_timing: bool = True
    time_variance: int = 15
    max_daily_actions: int = 10
    target_type: str = "specific"  # specific, random_from_niche, random_from_list

class TaskScheduleCreate(TaskScheduleBase):
    account_id: int
    content_pool_id: Optional[int] = None
    subreddits: Optional[List[str]] = None

class TaskScheduleUpdate(BaseModel):
    name: Optional[str] = None
    task_type: Optional[str] = None
    frequency_type: Optional[str] = None
    frequency_value: Optional[int] = None
    is_active: Optional[bool] = None
    is_warmup: Optional[bool] = None
    warmup_level: Optional[int] = None
    max_daily_actions: Optional[int] = None
    randomize_timing: Optional[bool] = None
    time_variance: Optional[int] = None

class TaskSchedule(TaskScheduleBase):
    id: int
    user_id: int
    account_id: int
    content_pool_id: Optional[int] = None
    next_run_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    account: Optional[RedditAccount] = None
    content_pool: Optional[ContentPool] = None

    class Config:
        from_attributes = True