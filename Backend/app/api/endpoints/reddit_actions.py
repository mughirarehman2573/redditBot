# backend/app/api/endpoints/reddit_actions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.models import User
from backend.app.services.reddit_poster import RedditPosterService

router = APIRouter()


@router.post("/posts")
async def create_post(
        subreddit: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None,
        account_id: int = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a post on Reddit."""
    if not account_id:
        raise HTTPException(status_code=400, detail="Account ID required")

    poster_service = RedditPosterService(db)
    return await poster_service.create_post(account_id, subreddit, title, content, url)


@router.post("/comments")
async def create_comment(
        submission_id: str,
        comment_text: str,
        account_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a comment on a Reddit post."""
    poster_service = RedditPosterService(db)
    return await poster_service.create_comment(account_id, submission_id, comment_text)


@router.get("/subreddits/{subreddit_name}")
async def get_subreddit_info(
        subreddit_name: str,
        account_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get information about a subreddit."""
    poster_service = RedditPosterService(db)
    return await poster_service.get_subreddit_info(account_id, subreddit_name)