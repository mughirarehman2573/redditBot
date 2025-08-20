# backend/app/api/endpoints/niches.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user, get_current_superuser
from backend.app.models.models import User
from backend.app.schemas.niche import Niche, NicheCreate
from backend.app.services.niche_service import get_all_niches, create_niche, delete_niche

router = APIRouter()

@router.get("/", response_model=List[Niche])
def list_niches(
    db: Session = Depends(get_db)
):
    """Get all niches."""
    return get_all_niches(db)

@router.post("/", response_model=Niche)
def create_niche_endpoint(
    niche_data: NicheCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Create a new niche (admin only)."""
    return create_niche(db, niche_data)

@router.delete("/{niche_id}")
def delete_niche_endpoint(
    niche_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Delete a niche (admin only)."""
    return delete_niche(db, niche_id)