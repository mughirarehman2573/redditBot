# backend/app/schemas/content.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.app.schemas.niche import Niche

class ContentPoolBase(BaseModel):
    name: str
    content_type: str  # post_title, post_body, comment
    content_format: str  # text, template, csv
    is_active: bool = True

class ContentPoolCreate(ContentPoolBase):
    content_data: Dict[str, Any]
    variables: Optional[Dict[str, Any]] = None
    niche_id: Optional[int] = None

class ContentPoolUpdate(BaseModel):
    name: Optional[str] = None
    content_data: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    niche_id: Optional[int] = None

class ContentPool(ContentPoolBase):
    id: int
    content_data: Dict[str, Any]
    variables: Optional[Dict[str, Any]] = None
    user_id: int
    niche_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    niche: Optional[Niche] = None

    class Config:
        from_attributes = True

class ContentRequest(BaseModel):
    content_pool_id: int
    variables: Optional[Dict[str, Any]] = None

class ContentResponse(BaseModel):
    content: str
    source: str