# schemas/user.py - Simplified version
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, EmailStr
import enum

class RoleEnum(str, enum.Enum):
    admin = "admin"
    instructor = "instructor"
    student = "student"

class UserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    role: RoleEnum = RoleEnum.student  # Remove Optional and validator

    class Config:
        use_enum_values = True  # This will serialize enums to their values

class UserOut(BaseModel):
    id: str
    full_name: str
    username: str
    email: EmailStr
    role: str
    date_of_birth: Optional[str]
    phone_number: Optional[str]
    gender: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    invited_by: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None

    class Config:
        from_attributes = True

# schemas/user.py - UPDATE AdminUserCreate
class AdminUserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.student
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    invited_by: Optional[str] = None

    class Config:
        use_enum_values = True