from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.models import User
from backend.app.schemas.content import ContentPool, ContentPoolCreate, ContentPoolUpdate, ContentRequest, ContentResponse
from backend.app.services.content_service import (
    get_content_pools_for_user,
    get_content_pool_by_id,
    create_content_pool,
    update_content_pool,
    delete_content_pool,
    generate_content_from_pool
)

router = APIRouter()

@router.get("/", response_model=List[ContentPool])
def list_content_pools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    niche_id: Optional[int] = None
):
    """Get all content pools for the current user."""
    pools = get_content_pools_for_user(db, current_user.id, niche_id)
    return pools

@router.get("/{pool_id}", response_model=ContentPool)
def get_content_pool(
    pool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific content pool by ID."""
    return get_content_pool_by_id(db, pool_id, current_user.id)

@router.post("/", response_model=ContentPool)
def create_content_pool_endpoint(
    pool_data: ContentPoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new content pool."""
    return create_content_pool(db, current_user.id, pool_data)

@router.post("/generate", response_model=ContentResponse)
def generate_content(
    content_request: ContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate content from a content pool."""
    content = generate_content_from_pool(
        db,
        content_request.content_pool_id,
        current_user.id,
        content_request.variables
    )
    return ContentResponse(content=content, source="content_pool")

@router.put("/{pool_id}", response_model=ContentPool)
def update_content_pool_endpoint(
    pool_id: int,
    update_data: ContentPoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a content pool."""
    return update_content_pool(db, pool_id, current_user.id, update_data)

@router.delete("/{pool_id}")
def delete_content_pool_endpoint(
    pool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a content pool."""
    return delete_content_pool(db, pool_id, current_user.id)