# backend/app/api/endpoints/reddit_oauth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.models import User
from backend.app.integrations.reddit.auth import reddit_oauth
from backend.app.services.reddit_account_service import create_reddit_account
from backend.app.schemas.reddit_account import RedditAccount

router = APIRouter()


@router.get("/reddit/connect")
def connect_reddit_account(
    current_user: User = Depends(get_current_user)
):
    """Return Reddit OAuth2 URL for frontend to handle redirect."""
    state = f"user_{current_user.id}"
    auth_url = reddit_oauth.get_authorization_url(state=state)
    return {"auth_url": auth_url}


@router.get("/reddit/callback", response_model=RedditAccount)
def reddit_oauth_callback(
        request: Request,
        code: str,
        state: Optional[str] = None,
        error: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Handle the callback from Reddit OAuth2."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )

    try:
        # Exchange code for tokens
        token_data = reddit_oauth.exchange_code_for_tokens(code)
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # Get user info from Reddit
        user_info = reddit_oauth.get_user_info(access_token)
        reddit_username = user_info["name"]

        # Create or update Reddit account
        account = create_reddit_account(
            db,
            current_user.id,
            reddit_username,
            access_token,
            refresh_token
        )

        return account

    except Exception as e:
        import traceback
        print("OAuth Exception:", traceback.format_exc())  # Debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth flow: {str(e)}"
        )
