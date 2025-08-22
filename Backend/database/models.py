from datetime import datetime

from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reddit_accounts: Mapped[list["RedditAccount"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

class RedditAccount(Base):
    __tablename__ = "reddit_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    access_token: Mapped[str] = mapped_column(String(500), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(500), nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    niche: Mapped[str] = mapped_column(String(200), nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="reddit_accounts")
    posts: Mapped[list["RedditPost"]] = relationship("RedditPost", back_populates="account", cascade="all, delete-orphan")
    comments: Mapped[list["RedditComment"]] = relationship("RedditComment", back_populates="account", cascade="all, delete-orphan")
    schedules: Mapped[list["RedditSchedule"]] = relationship("RedditSchedule", back_populates="account", cascade="all, delete-orphan")


class RedditSchedule(Base):
    __tablename__ = "reddit_schedules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("reddit_accounts.id", ondelete="CASCADE"), index=True)

    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    action: Mapped[str] = mapped_column(String(20), default="comment")
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    account: Mapped["RedditAccount"] = relationship(back_populates="schedules")


class RedditPost(Base):
    __tablename__ = "reddit_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("reddit_accounts.id", ondelete="CASCADE"), index=True)
    reddit_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    created_utc: Mapped[int] = mapped_column(Integer, index=True)

    account: Mapped["RedditAccount"] = relationship(back_populates="posts")

class RedditComment(Base):
    __tablename__ = "reddit_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("reddit_accounts.id", ondelete="CASCADE"), index=True)
    reddit_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text)
    created_utc: Mapped[int] = mapped_column(Integer, index=True)

    account: Mapped["RedditAccount"] = relationship(back_populates="comments")
