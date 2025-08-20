
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import random
import json
from datetime import datetime
from backend.app.models.models import ContentPool
from typing import Optional


from backend.app.models.models import User
from backend.app.models.models import Niche

from backend.app.schemas.content import ContentPoolCreate, ContentPoolUpdate


def get_content_pools_for_user(db: Session, user_id: int, niche_id: Optional[int] = None):
    """Get all content pools for a user, optionally filtered by niche."""
    query = db.query(ContentPool).filter(ContentPool.user_id == user_id)

    if niche_id:
        query = query.filter(ContentPool.niche_id == niche_id)

    return query.all()


def get_content_pool_by_id(db: Session, pool_id: int, user_id: int):
    """Get a specific content pool if it belongs to the user."""
    pool = db.query(ContentPool).filter(
        ContentPool.id == pool_id,
        ContentPool.user_id == user_id
    ).first()

    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content pool not found"
        )
    return pool


def create_content_pool(db: Session, user_id: int, pool_data: ContentPoolCreate):
    """Create a new content pool for a user."""
    # Verify niche belongs to user if provided
    if pool_data.niche_id:
        niche = db.query(Niche).filter(Niche.id == pool_data.niche_id).first()
        if not niche:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid niche ID"
            )

    # Validate content data based on format
    if not _validate_content_data(pool_data.content_format, pool_data.content_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content data for the specified format"
        )

    # Create the content pool
    db_pool = ContentPool(
        **pool_data.dict(),
        user_id=user_id
    )

    db.add(db_pool)
    db.commit()
    db.refresh(db_pool)
    return db_pool


def update_content_pool(db: Session, pool_id: int, user_id: int, update_data: ContentPoolUpdate):
    """Update a content pool."""
    pool = get_content_pool_by_id(db, pool_id, user_id)

    # Update fields
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(pool, field, value)

    # Validate content data if being updated
    if update_data.content_data and not _validate_content_data(pool.content_format, update_data.content_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content data for the specified format"
        )

    pool.updated_at = datetime.now()
    db.commit()
    db.refresh(pool)
    return pool


def delete_content_pool(db: Session, pool_id: int, user_id: int):
    """Delete a content pool."""
    pool = get_content_pool_by_id(db, pool_id, user_id)
    db.delete(pool)
    db.commit()
    return {"message": "Content pool deleted successfully"}


def generate_content_from_pool(db: Session, pool_id: int, user_id: int, variables: dict = None):
    """Generate content from a content pool."""
    pool = get_content_pool_by_id(db, pool_id, user_id)

    if pool.content_format == "text":
        return _generate_text_content(pool.content_data)
    elif pool.content_format == "template":
        return _generate_template_content(pool.content_data, variables or {})
    elif pool.content_format == "csv":
        return _generate_csv_content(pool.content_data)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content format"
        )


def _validate_content_data(content_format: str, content_data: dict) -> bool:
    """Validate content data based on format."""
    if content_format == "text":
        return isinstance(content_data, list) and len(content_data) > 0
    elif content_format == "template":
        return isinstance(content_data, dict) and "template" in content_data
    elif content_format == "csv":
        return isinstance(content_data, list) and len(content_data) > 0
    return False


def _generate_text_content(content_data: list) -> str:
    """Generate content from text pool."""
    if not content_data:
        return "No content available"
    return random.choice(content_data)


def _generate_template_content(content_data: dict, variables: dict) -> str:
    """Generate content from template with variable substitution."""
    template = content_data.get("template", "")
    available_variables = content_data.get("variables", {})

    # Replace variables in template
    result = template
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            if key in available_variables and isinstance(available_variables[key], list):
                # Randomly select from available options
                result = result.replace(placeholder, random.choice(available_variables[key]))
            else:
                result = result.replace(placeholder, str(value))

    return result


def _generate_csv_content(content_data: list) -> str:
    """Generate content from CSV-like data."""
    if not content_data:
        return "No content available"
    return random.choice(content_data)