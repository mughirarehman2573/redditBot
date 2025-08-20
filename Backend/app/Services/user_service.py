from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from backend.app.models.models import User
from backend.app.schemas.user import UserCreate
from backend.app.utils.security import get_password_hash, verify_password


def get_user_by_username(db: Session, username: str) -> User:
    """Get a user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """Create a new user."""
    # Check if user already exists
    if get_user_by_username(db, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password
    hashed_password = get_password_hash(user_in.password)

    # Create user object
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser
    )

    # Save to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Authenticate a user with username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_last_login(db: Session, user: User):
    """Update user's last login time."""
    user.last_login = datetime.now()
    db.commit()
    db.refresh(user)