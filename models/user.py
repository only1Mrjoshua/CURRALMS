# models/user.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
import enum

class RoleEnum(str, enum.Enum):
    admin = "admin"
    instructor = "instructor"
    student = "student"

class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class User(BaseModel):
    id: Optional[str] = None
    full_name: str
    username: str
    email: EmailStr
    password_hash: str
    role: RoleEnum = RoleEnum.student
    invited_by: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[GenderEnum] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
        use_enum_values = True