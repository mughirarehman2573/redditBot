from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import RedditAccount, RedditComment, RedditPost, User
from core.jwt import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/account/{account_id}")
def account_stats(account_id: int, days: int = 7, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    acc = db.query(RedditAccount).filter_by(id=account_id, owner_id=current_user.id).first()
    if not acc:
        return {"error": "Account not found"}

    since = datetime.utcnow() - timedelta(days=days)

    comments = db.query(RedditComment).filter(
        RedditComment.account_id == acc.id,
        RedditComment.created_utc >= since.timestamp()
    ).all()

    posts = db.query(RedditPost).filter(
        RedditPost.account_id == acc.id,
        RedditPost.created_utc >= since.timestamp()
    ).all()

    return {
        "account_id": acc.id,
        "username": acc.username,
        "comments_count": len(comments),
        "posts_count": len(posts),
        "posts": [
            {
                "id": p.id,
                "reddit_id": p.reddit_id,
                "title": p.title,
                "body": p.body,
                "created_utc": p.created_utc,
            }
            for p in posts
        ],
        "comments": [
            {
                "id": c.id,
                "reddit_id": c.reddit_id,
                "body": c.body,
                "created_utc": c.created_utc,
            }
            for c in comments
        ]
    }
