from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Base properties
class UserBase(BaseModel):
    email: EmailStr
    username: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None

# Properties to return via API (never return the password!)
class User(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True  # Allows ORM mode

# Properties stored in database
class UserInDB(User):
    hashed_password: str