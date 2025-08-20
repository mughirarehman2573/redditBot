# backend/app/schemas/niche.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NicheBase(BaseModel):
    name: str
    description: Optional[str] = None

class NicheCreate(NicheBase):
    pass

class Niche(NicheBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True