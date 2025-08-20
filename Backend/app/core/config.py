from pydantic_settings import BaseSettings
import secrets
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"


    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Reddit
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/reddit/callback"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()