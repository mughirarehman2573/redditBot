# backend/app/schemas/reddit_account.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from backend.app.schemas.niche import Niche

class RedditAccountBase(BaseModel):
    reddit_username: str
    status: str = "active"

class RedditAccountCreate(BaseModel):
    reddit_username: str
    access_token: str
    refresh_token: str

class RedditAccountUpdate(BaseModel):
    status: Optional[str] = None
    niche_ids: Optional[List[int]] = None

class RedditAccount(RedditAccountBase):
    id: int
    total_posts: int
    total_comments: int
    karma: int
    account_age_days: int
    last_activity: Optional[datetime] = None
    user_id: int
    created_at: datetime
    niches: List[Niche] = []

    class Config:
        from_attributes = True

class RedditAccountInDB(RedditAccount):
    access_token: str
    refresh_token: str
    token_expires: datetime