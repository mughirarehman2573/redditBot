# backend/app/services/niche_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import Niche

from backend.app.schemas.niche import NicheCreate


def get_all_niches(db: Session):
    """Get all niches."""
    return db.query(Niche).all()


def get_niche_by_id(db: Session, niche_id: int):
    """Get a niche by ID."""
    niche = db.query(Niche).filter(Niche.id == niche_id).first()
    if not niche:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Niche not found"
        )
    return niche


def create_niche(db: Session, niche_data: NicheCreate):
    """Create a new niche."""
    # Check if niche already exists
    existing_niche = db.query(Niche).filter(Niche.name == niche_data.name).first()
    if existing_niche:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Niche with this name already exists"
        )

    niche = Niche(**niche_data.dict())
    db.add(niche)
    db.commit()
    db.refresh(niche)
    return niche


def delete_niche(db: Session, niche_id: int):
    """Delete a niche."""
    niche = get_niche_by_id(db, niche_id)
    db.delete(niche)
    db.commit()
    return {"message": "Niche deleted successfully"}