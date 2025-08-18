from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models import PlannedComment, RunLog, Account
from ai import generate_comment
from reddit_client import get_reddit
from niches import load_niche

def plan_for_account(db: Session, account_id: int, niche_name: str = "golf", max_new: int = 3):
    account = db.query(Account).get(account_id)
    if not account:
        raise ValueError("Account not found")

    niche = load_niche(niche_name)
    reddit = get_reddit(account)

    created = 0
    now = datetime.now(timezone.utc)
    max_age = int(niche.filters.get("max_post_age_minutes", 60))
    min_score = int(niche.filters.get("min_score", 0))
    seen_ids = {pid for (pid,) in db.query(PlannedComment.post_id).all()}

    for sub in niche.subreddits:
        if created >= max_new:
            break
        for post in reddit.subreddit(sub).new(limit=50):
            if created >= max_new:
                break

            # Filters
            post_age = now - datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if post_age > timedelta(minutes=max_age):
                continue
            if getattr(post, "score", 0) < min_score:
                continue
            if post.id in seen_ids:
                continue

            text = generate_comment(post.title, getattr(post, "selftext", "") or "", niche_name)
            if not text:
                continue

            pc = PlannedComment(
                account_id=account.id,
                niche=niche_name,
                subreddit=sub,
                post_id=post.id,
                post_title=post.title,
                post_url=f"https://reddit.com{post.permalink}",
                text=text,
            )
            db.add(pc)
            created += 1

    db.add(RunLog(account_id=account.id, niche=niche_name, status="planned", message=f"planned={created}"))
    db.commit()
    return created
