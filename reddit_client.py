import praw
from settings import settings

def get_reddit(account) -> praw.Reddit:
    client_id = (account.client_id or settings.REDDIT_CLIENT_ID) or ""
    client_secret = (account.client_secret or settings.REDDIT_CLIENT_SECRET) or ""
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=account.refresh_token,
        user_agent=settings.USER_AGENT,
    )
