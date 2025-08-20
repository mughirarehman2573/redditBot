import praw
from prawcore import exceptions
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class RedditAPIClient:
    def __init__(self, access_token: str, refresh_token: str, user_agent: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_agent = user_agent
        self.reddit = None
        self._initialize_praw()

    def _initialize_praw(self):
        """Initialize PRAW instance."""
        try:
            self.reddit = praw.Reddit(
                client_id="dummy",  # Not needed for refresh token flow
                client_secret="dummy",
                refresh_token=self.refresh_token,
                user_agent=self.user_agent,
                timeout=30,
                retry_on_error=[500, 502, 503, 504]
            )
        except Exception as e:
            logger.error(f"Failed to initialize PRAW: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize Reddit client"
            )

    def create_post(self, subreddit_name: str, title: str, content: Optional[str] = None,
                    url: Optional[str] = None, flair: Optional[str] = None) -> Dict:
        """Create a post on Reddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            if url:
                submission = subreddit.submit(title=title, url=url, flair_id=flair)
            else:
                submission = subreddit.submit(title=title, selftext=content, flair_id=flair)

            return {
                "id": submission.id,
                "title": submission.title,
                "url": submission.url,
                "permalink": submission.permalink,
                "subreddit": subreddit_name
            }

        except exceptions.Forbidden as e:
            logger.warning(f"Permission denied for subreddit {subreddit_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for r/{subreddit_name}"
            )
        except exceptions.NotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subreddit r/{subreddit_name} not found"
            )
        except Exception as e:
            logger.error(f"Failed to create post: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create post: {str(e)}"
            )

    def create_comment(self, submission_id: str, comment_text: str) -> Dict:
        """Create a comment on a Reddit post."""
        try:
            submission = self.reddit.submission(id=submission_id)
            comment = submission.reply(comment_text)

            return {
                "id": comment.id,
                "text": comment.body,
                "post_title": submission.title,
                "post_url": submission.url
            }

        except exceptions.Forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to comment"
            )
        except Exception as e:
            logger.error(f"Failed to create comment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create comment: {str(e)}"
            )

    def get_subreddit_rules(self, subreddit_name: str) -> List[Dict]:
        """Get rules for a subreddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            rules = []

            for rule in subreddit.rules:
                rules.append({
                    "short_name": rule.short_name,
                    "description": rule.description,
                    "violation_reason": rule.violation_reason
                })

            return rules

        except Exception as e:
            logger.warning(f"Failed to get rules for r/{subreddit_name}: {str(e)}")
            return []

    def get_user_info(self) -> Dict:
        """Get current user information."""
        try:
            user = self.reddit.user.me()
            return {
                "username": user.name,
                "karma": user.comment_karma + user.link_karma,
                "account_created": datetime.fromtimestamp(user.created_utc),
                "comment_karma": user.comment_karma,
                "link_karma": user.link_karma
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user information"
            )