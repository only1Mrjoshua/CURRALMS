from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class LessonBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    course_id: str
    order: int = 0
    duration: Optional[int] = None  # minutes
    video_url: Optional[str] = None
    resources: Optional[List[str]] = None  # List of resource URLs
    is_active: bool = True

class LessonCreate(LessonBase):
    pass

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    duration: Optional[int] = None
    video_url: Optional[str] = None
    resources: Optional[List[str]] = None
    is_active: Optional[bool] = None

class LessonOut(LessonBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class LessonCompletion(BaseModel):
    lesson_id: str
    user_id: str
    course_id: str
    completed_at: datetime

class LessonWithCompletion(LessonOut):
    completed: bool = False