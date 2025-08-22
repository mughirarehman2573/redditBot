from typing import Optional

from pydantic import BaseModel
from datetime import datetime

class RedditAccountOut(BaseModel):
    id: int
    username: str
    niche: Optional[str] = None
    token_expires_at: datetime

    class Config:
        from_attributes = True

class NicheUpdate(BaseModel):
    niche: str