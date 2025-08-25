from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    run_at: datetime
    start_date: date | None = None
    end_date: date | None = None
    action: str = "comment"
    prompt: str | None = None


class ScheduleUpdate(BaseModel):
    run_at: Optional[datetime] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    action: Optional[str] = None
    prompt: Optional[str] = None