from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.core.jwt import get_current_user
from app.database.db import get_db
from app.database.models import RedditAccount, User
from app.schemas.reddit import RedditAccountOut, NicheUpdate
from app.core.config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_REDIRECT_URI,
    REDDIT_OAUTH_URL, REDDIT_TOKEN_URL
)
from app.core.security import decode_token

router = APIRouter(prefix="/reddit", tags=["reddit"])

@router.get("/authorize")
def authorize():
    scope = "identity submit read"
    url = (
        f"{REDDIT_OAUTH_URL}"
        f"?client_id={REDDIT_CLIENT_ID}"
        f"&response_type=code"
        f"&state=randomstring"
        f"&redirect_uri={REDDIT_REDIRECT_URI}"
        f"&duration=permanent"
        f"&scope={scope}"
    )
    return {"auth_url": url}

@router.get("/callback")
def reddit_callback(code: str, state: str):
    auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDDIT_REDIRECT_URI}
    headers = {"User-Agent": "mybot/0.0.1"}
    res = requests.post(REDDIT_TOKEN_URL, auth=auth, data=data, headers=headers)
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to get tokens")
    tokens = res.json()

    me = requests.get(
        "https://oauth.reddit.com/api/v1/me",
        headers={"Authorization": f"bearer {tokens['access_token']}", "User-Agent": "mybot/0.0.1"},
    ).json()

    return {
        "username": me["name"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "expires_in": tokens["expires_in"],
    }


@router.post("/link_account", response_model=RedditAccountOut)
def link_account(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = RedditAccount(
        username=payload["username"],
        owner_id=current_user.id,
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        token_expires_at=datetime.utcnow() + timedelta(seconds=payload["expires_in"]),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[RedditAccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(RedditAccount)
        .filter(RedditAccount.owner_id == current_user.id)
        .all()
    )


@router.post("/accounts/{account_id}/refresh", response_model=RedditAccountOut)
def refresh_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = (
        db.query(RedditAccount)
        .filter(RedditAccount.id == account_id, RedditAccount.owner_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token stored")

    return refresh_token(account, db)



@router.put("/accounts/{account_id}/niche", response_model=RedditAccountOut)
def update_niche(
    account_id: int,
    payload: NicheUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = (
        db.query(RedditAccount)
        .filter(RedditAccount.id == account_id, RedditAccount.owner_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.niche = payload.niche
    db.commit()
    db.refresh(account)
    return account


def refresh_token(account: RedditAccount, db: Session):
    auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    data = {"grant_type": "refresh_token", "refresh_token": account.refresh_token}
    headers = {"User-Agent": "mybot/0.0.1"}

    res = requests.post(REDDIT_TOKEN_URL, auth=auth, data=data, headers=headers)
    tokens = res.json()
    account.access_token = tokens["access_token"]
    account.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
    db.commit()
    db.refresh(account)
    return account
