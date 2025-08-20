# backend/app/api/endpoints/reddit_accounts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.models import User
from backend.app.schemas.reddit_account import RedditAccount, RedditAccountUpdate
from backend.app.services.reddit_account_service import (
    get_reddit_accounts_for_user,
    get_reddit_account_by_id,
    update_reddit_account_status,
    delete_reddit_account,
    assign_niche_to_account
)

router = APIRouter()


@router.get("/", response_model=List[RedditAccount])
def list_reddit_accounts(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all Reddit accounts for the current user."""
    accounts = get_reddit_accounts_for_user(db, current_user.id)
    return accounts


@router.get("/{account_id}", response_model=RedditAccount)
def get_reddit_account(
        account_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific Reddit account by ID."""
    return get_reddit_account_by_id(db, account_id, current_user.id)


@router.put("/{account_id}", response_model=RedditAccount)
def update_reddit_account(
        account_id: int,
        update_data: RedditAccountUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a Reddit account."""
    account = get_reddit_account_by_id(db, account_id, current_user.id)

    if update_data.status:
        account = update_reddit_account_status(db, account_id, current_user.id, update_data.status)

    return account


@router.delete("/{account_id}")
def delete_reddit_account_endpoint(
        account_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a Reddit account."""
    return delete_reddit_account(db, account_id, current_user.id)


@router.post("/{account_id}/niches/{niche_id}")
def assign_niche(
        account_id: int,
        niche_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Assign a niche to a Reddit account."""
    return assign_niche_to_account(db, account_id, current_user.id, niche_id)