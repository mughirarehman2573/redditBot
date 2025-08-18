from sqlalchemy.orm import Session
from models import PlannedComment, RunLog, Account
from reddit_client import get_reddit

def approve_and_post(db: Session, planned_id: int) -> bool:
    pc = db.query(PlannedComment).get(planned_id)
    if not pc or pc.posted:
        return False

    account = db.query(Account).get(pc.account_id)
    try:
        reddit = get_reddit(account)
        submission = reddit.submission(id=pc.post_id)
        result = submission.reply(pc.text)

        pc.posted = True
        pc.posted_comment_id = result.id
        db.add(RunLog(
            account_id=account.id,
            niche=pc.niche,
            status="posted",
            message=f"comment_id={result.id} on r/{pc.subreddit}",
        ))
        db.commit()
        return True
    except Exception as e:
        db.add(RunLog(
            account_id=account.id,
            niche=pc.niche,
            status="error",
            message=str(e),
        ))
        db.commit()
        return False
