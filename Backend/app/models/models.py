from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.db.base import Base

# Many-to-many between RedditAccount <-> Niche
account_niche = Table(
    "account_niche",
    Base.metadata,
    Column("reddit_account_id", Integer, ForeignKey("reddit_accounts.id"), primary_key=True),
    Column("niche_id", Integer, ForeignKey("niches.id"), primary_key=True),
)

# Many-to-many between TaskSchedule <-> SubredditTarget
schedule_subreddit = Table(
    "schedule_subreddit",
    Base.metadata,
    Column("task_schedule_id", Integer, ForeignKey("task_schedules.id"), primary_key=True),
    Column("subreddit_target_id", Integer, ForeignKey("subreddit_targets.id"), primary_key=True),
)

# ----------------- MODELS -----------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))

    reddit_accounts = relationship("RedditAccount", back_populates="owner", cascade="all, delete-orphan")
    content_pools = relationship("ContentPool", back_populates="owner", cascade="all, delete-orphan")
    task_schedules = relationship("TaskSchedule", back_populates="owner", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")


class RedditAccount(Base):
    __tablename__ = "reddit_accounts"

    id = Column(Integer, primary_key=True, index=True)
    reddit_username = Column(String, index=True, nullable=False)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires = Column(DateTime(timezone=True))
    status = Column(String, default="active")  # active, paused, rate_limited, banned
    last_activity = Column(DateTime(timezone=True))
    total_posts = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    karma = Column(Integer, default=0)
    account_age_days = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="reddit_accounts")
    niches = relationship("Niche", secondary=account_niche, back_populates="accounts")
    activity_logs = relationship("ActivityLog", back_populates="account", cascade="all, delete-orphan")
    task_schedules = relationship("TaskSchedule", back_populates="account")


class Niche(Base):
    __tablename__ = "niches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    accounts = relationship("RedditAccount", secondary=account_niche, back_populates="niches")
    content_pools = relationship("ContentPool", back_populates="niche")


class ContentPool(Base):
    __tablename__ = "content_pools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    content_type = Column(String, nullable=False)
    content_format = Column(String, default="text")
    content_data = Column(JSON, nullable=False)
    variables = Column(JSON)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    niche_id = Column(Integer, ForeignKey("niches.id"))

    owner = relationship("User", back_populates="content_pools")
    niche = relationship("Niche", back_populates="content_pools")
    task_schedules = relationship("TaskSchedule", back_populates="content_pool")


class TaskSchedule(Base):
    __tablename__ = "task_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    task_type = Column(String, nullable=False)
    frequency_type = Column(String, nullable=False)
    frequency_value = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

    is_warmup = Column(Boolean, default=False)
    warmup_level = Column(Integer, default=1)
    randomize_timing = Column(Boolean, default=True)
    time_variance = Column(Integer, default=15)
    max_daily_actions = Column(Integer, default=10)
    target_type = Column(String, default="specific")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("reddit_accounts.id"), nullable=False)
    content_pool_id = Column(Integer, ForeignKey("content_pools.id"))

    owner = relationship("User", back_populates="task_schedules")
    account = relationship("RedditAccount", back_populates="task_schedules")
    content_pool = relationship("ContentPool", back_populates="task_schedules")
    subreddits = relationship("SubredditTarget", secondary=schedule_subreddit, back_populates="schedules")
    activity_logs = relationship("ActivityLog", back_populates="schedule")


class SubredditTarget(Base):
    __tablename__ = "subreddit_targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    niche_id = Column(Integer, ForeignKey("niches.id"))
    min_karma_required = Column(Integer, default=0)
    min_account_age_days = Column(Integer, default=0)
    post_cooldown_minutes = Column(Integer, default=60)
    comment_cooldown_minutes = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)

    niche = relationship("Niche")
    schedules = relationship("TaskSchedule", secondary=schedule_subreddit, back_populates="subreddits")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    target_subreddit = Column(String)
    content_preview = Column(Text)
    reddit_id = Column(String)
    error_message = Column(Text)
    response_data = Column(JSON)
    execution_time = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("reddit_accounts.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("task_schedules.id"))

    user = relationship("User", back_populates="activity_logs")
    account = relationship("RedditAccount", back_populates="activity_logs")
    schedule = relationship("TaskSchedule", back_populates="activity_logs")


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
