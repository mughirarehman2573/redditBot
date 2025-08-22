from datetime import datetime

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    run_at: datetime
    action: str = "comment"
    prompt: str | None = None