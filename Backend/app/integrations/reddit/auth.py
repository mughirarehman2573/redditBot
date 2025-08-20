# backend/app/integrations/reddit/auth.py
import requests
from fastapi import HTTPException, status
from backend.app.core.config import settings
from typing import Dict, Optional


class RedditOAuth:
    def __init__(self):
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.redirect_uri = settings.REDDIT_REDIRECT_URI
        self.user_agent = "RedditAutomationSuite/1.0 by YourUsername"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate Reddit OAuth2 authorization URL."""
        base_url = "https://www.reddit.com/api/v1/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "state": state or "default_state",
            "redirect_uri": self.redirect_uri,
            "duration": "permanent",
            "scope": "identity read submit history save"
        }
        return f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

    def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens."""
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for tokens: {str(e)}"
            )

    def get_user_info(self, access_token: str) -> Dict:
        """Get user information using the access token."""
        headers = {
            "Authorization": f"bearer {access_token}",
            "User-Agent": self.user_agent
        }

        try:
            response = requests.get(
                "https://oauth.reddit.com/api/v1/me",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info: {str(e)}"
            )


# Create a singleton instance
reddit_oauth = RedditOAuth()