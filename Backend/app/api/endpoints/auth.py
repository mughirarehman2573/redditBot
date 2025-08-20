from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.app.db.session import get_db
from backend.app.schemas.user import User, UserCreate
from backend.app.schemas.token import Token
from backend.app.services.user_service import authenticate_user, create_user, update_last_login
from backend.app.utils.security import create_access_token
from backend.app.core.config import settings
from backend.app.api.dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=User)
def register_user(
        user_in: UserCreate,
        db: Session = Depends(get_db)
):
    """Register a new user."""
    user = create_user(db, user_in)
    return user


@router.post("/login", response_model=Token)
def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """Login user and return access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Update last login
    update_last_login(db, user)

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
def get_current_user_info(
        current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user