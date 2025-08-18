from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, index=True)                # e.g., "Main Golf"
    username = Column(String, index=True)
    # Optional — if different apps per account; else keep env defaults
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)

    refresh_token = Column(Text, nullable=False)
    active_niche = Column(String, default="golf")
    created_at = Column(DateTime, default=utcnow)

class PlannedComment(Base):
    __tablename__ = "planned_comments"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True)
    created_at = Column(DateTime, default=utcnow)
    niche = Column(String, default="golf")

    subreddit = Column(String, index=True)
    post_id = Column(String, index=True, unique=True)
    post_title = Column(Text)
    post_url = Column(Text)
    text = Column(Text)

    posted = Column(Boolean, default=False)
    posted_comment_id = Column(String, nullable=True)
    email_sent = Column(Boolean, default=False)

class RunLog(Base):
    __tablename__ = "run_logs"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True)
    created_at = Column(DateTime, default=utcnow)
    niche = Column(String, default="golf")
    status = Column(String)  # "planned" | "posted" | "error"
    message = Column(Text)
