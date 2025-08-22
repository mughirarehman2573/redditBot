from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool
    is_admin: bool

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_admin: bool = False

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True
