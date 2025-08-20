
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from backend.app.models.models import RedditAccount
from backend.app.models.models import User
from backend.app.models.models import Niche



def get_reddit_accounts_for_user(db: Session, user_id: int):
    """Get all Reddit accounts for a specific user."""
    return db.query(RedditAccount).filter(RedditAccount.user_id == user_id).all()


def get_reddit_account_by_id(db: Session, account_id: int, user_id: int):
    """Get a specific Reddit account if it belongs to the user."""
    account = db.query(RedditAccount).filter(
        RedditAccount.id == account_id,
        RedditAccount.user_id == user_id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reddit account not found"
        )
    return account


def create_reddit_account(db: Session, user_id: int, reddit_username: str,
                          access_token: str, refresh_token: str) -> RedditAccount:
    """Create a new Reddit account for a user."""
    # Check if account already exists for this user
    existing_account = db.query(RedditAccount).filter(
        RedditAccount.reddit_username == reddit_username,
        RedditAccount.user_id == user_id
    ).first()

    if existing_account:
        # Update existing account tokens
        existing_account.access_token = access_token
        existing_account.refresh_token = refresh_token
        existing_account.token_expires = datetime.now() + timedelta(hours=1)
        db.commit()
        db.refresh(existing_account)
        return existing_account

    # Create new account
    db_account = RedditAccount(
        reddit_username=reddit_username,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires=datetime.now() + timedelta(hours=1),
        user_id=user_id,
        status="active"
    )

    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def update_reddit_account_status(db: Session, account_id: int, user_id: int, status: str):
    """Update a Reddit account's status."""
    account = get_reddit_account_by_id(db, account_id, user_id)
    account.status = status
    db.commit()
    db.refresh(account)
    return account


def delete_reddit_account(db: Session, account_id: int, user_id: int):
    """Delete a Reddit account."""
    account = get_reddit_account_by_id(db, account_id, user_id)
    db.delete(account)
    db.commit()
    return {"message": "Reddit account deleted successfully"}


def assign_niche_to_account(db: Session, account_id: int, user_id: int, niche_id: int):
    """Assign a niche to a Reddit account."""
    account = get_reddit_account_by_id(db, account_id, user_id)
    niche = db.query(Niche).filter(Niche.id == niche_id).first()

    if not niche:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Niche not found"
        )

    if niche not in account.niches:
        account.niches.append(niche)
        db.commit()

    return account