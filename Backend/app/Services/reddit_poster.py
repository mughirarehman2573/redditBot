# backend/app/services/reddit_poster.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from backend.app.integrations.reddit.client import RedditAPIClient
from backend.app.utils.rate_limiter import RateLimiter
from backend.app.services.activity_service import create_activity_log
from backend.app.models.models import RedditAccount
from typing import Optional



class RedditPosterService:
    def __init__(self, db: Session):
        self.db = db
        self.rate_limiter = RateLimiter()

    async def create_post(self, account_id: int, subreddit: str, title: str,
                          content: Optional[str] = None, url: Optional[str] = None) -> dict:
        """Create a post using the specified Reddit account."""
        account = self.db.query(RedditAccount).filter(RedditAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Check rate limit
        if not self.rate_limiter.check_rate_limit(str(account_id), "post"):
            wait_time = self.rate_limiter.get_wait_time(str(account_id), "post")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please wait {wait_time} seconds."
            )

        try:
            # Initialize Reddit client
            client = RedditAPIClient(
                access_token=account.access_token,
                refresh_token=account.refresh_token,
                user_agent="RedditAutomationSuite/1.0"
            )

            # Create post
            result = client.create_post(subreddit, title, content, url)

            # Log successful activity
            await create_activity_log(self.db, account.user_id, {
                "action_type": "post_created",
                "status": "success",
                "target_subreddit": subreddit,
                "content_preview": title[:100],
                "reddit_id": result["id"],
                "account_id": account_id
            })

            # Update account statistics
            account.total_posts += 1
            account.last_activity = datetime.now()
            self.db.commit()

            return result

        except Exception as e:
            # Log failed activity
            await create_activity_log(self.db, account.user_id, {
                "action_type": "post_created",
                "status": "failure",
                "target_subreddit": subreddit,
                "content_preview": title[:100],
                "error_message": str(e),
                "account_id": account_id
            })
            raise

    async def create_comment(self, account_id: int, submission_id: str, comment_text: str) -> dict:
        """Create a comment using the specified Reddit account."""
        account = self.db.query(RedditAccount).filter(RedditAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Check rate limit
        if not self.rate_limiter.check_rate_limit(str(account_id), "comment"):
            wait_time = self.rate_limiter.get_wait_time(str(account_id), "comment")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please wait {wait_time} seconds."
            )

        try:
            # Initialize Reddit client
            client = RedditAPIClient(
                access_token=account.access_token,
                refresh_token=account.refresh_token,
                user_agent="RedditAutomationSuite/1.0"
            )

            # Create comment
            result = client.create_comment(submission_id, comment_text)

            # Log successful activity
            await create_activity_log(self.db, account.user_id, {
                "action_type": "comment_posted",
                "status": "success",
                "content_preview": comment_text[:100],
                "reddit_id": result["id"],
                "account_id": account_id
            })

            # Update account statistics
            account.total_comments += 1
            account.last_activity = datetime.now()
            self.db.commit()

            return result

        except Exception as e:
            # Log failed activity
            await create_activity_log(self.db, account.user_id, {
                "action_type": "comment_posted",
                "status": "failure",
                "content_preview": comment_text[:100],
                "error_message": str(e),
                "account_id": account_id
            })
            raise

    async def get_subreddit_info(self, account_id: int, subreddit_name: str) -> dict:
        """Get information about a subreddit."""
        account = self.db.query(RedditAccount).filter(RedditAccount.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        try:
            client = RedditAPIClient(
                access_token=account.access_token,
                refresh_token=account.refresh_token,
                user_agent="RedditAutomationSuite/1.0"
            )

            rules = client.get_subreddit_rules(subreddit_name)

            return {
                "name": subreddit_name,
                "rules": rules,
                "rules_count": len(rules)
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get subreddit info: {str(e)}"
            )