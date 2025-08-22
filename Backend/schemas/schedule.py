from datetime import datetime, date

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    run_at: datetime
    start_date: date | None = None
    end_date: date | None = None
    action: str = "comment"
    prompt: str | None = None