import os
from datetime import timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
ALGORITHM = "HS256"

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "kpSy6WiVzyZjjQq4NMg6OA")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "Dx0u0TIJowrE8rxiOPkoREM51oposg")
REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8000/index.html")
REDDIT_OAUTH_URL = "https://www.reddit.com/api/v1/authorize"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OPEN_API_KEY = "sk-proj-A5sN3-6IDONW2Df_Dy0AmGc0MdLildIi-FavfjCV1z_miRjNMvYF3tsV8af2YZttvuOBPfnOg2T3BlbkFJlGNnaSZotiC-rxAlXmZej769fmgNmCLaM0Des8o9g53CkisqCkr2KXn4pi5COSkrryrzJHfU8A2"

def access_token_expires() -> timedelta:
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
