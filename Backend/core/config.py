import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
ALGORITHM = "HS256"

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "kpSy6WiVzyZjjQq4NMg6OA")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "Dx0u0TIJowrE8rxiOPkoREM51oposg")
REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8000/index.html")
REDDIT_OAUTH_URL = "https://www.reddit.com/api/v1/authorize"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"

def access_token_expires() -> timedelta:
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
