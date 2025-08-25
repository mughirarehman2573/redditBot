from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import RedditAccount, RedditPost, RedditComment, User
from core.jwt import get_current_user

router = APIRouter()

@router.get("/stats/{account_id}")
def account_stats(
    account_id: int,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    acc = db.query(RedditAccount).filter_by(
        id=account_id, owner_id=current_user.id
    ).first()
    if not acc:
        return {"error": "Account not found"}

    limit = 10
    offset = (page - 1) * limit

    posts = (
        db.query(RedditPost, RedditComment)
        .join(RedditComment, RedditComment.reddit_id == RedditPost.reddit_id)
        .filter(RedditPost.account_id == acc.id)
        .order_by(RedditPost.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    posts_data = [
        {
            "reddit_id": p.reddit_id,
            "url": f"https://www.reddit.com/comments/{p.reddit_id}",
            "title": p.title,
            "body": p.body,
            "created_utc": p.created_utc,
            "comment": c.body,
            "comment_id": c.comment_id,
            "comment_url": f"https://www.reddit.com/comments/{p.reddit_id}/comment/{c.comment_id}"
        }
        for p, c in posts
    ]

    total_posts = (
        db.query(RedditPost)
        .join(RedditComment, RedditComment.reddit_id == RedditPost.reddit_id)
        .filter(RedditPost.account_id == acc.id)
        .count()
    )

    return {
        "account_id": acc.id,
        "username": acc.username,
        "page": page,
        "per_page": limit,
        "total_posts": total_posts,
        "total_pages": (total_posts + limit - 1) // limit,
        "posts": posts_data
    }
