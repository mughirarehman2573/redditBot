from pydantic import BaseModel
from datetime import datetime

class RedditAccountOut(BaseModel):
    id: int
    username: str
    token_expires_at: datetime

    class Config:
        from_attributes = True

class NicheUpdate(BaseModel):
    niche: str