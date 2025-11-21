from datetime import date, time, datetime
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator
from enum import Enum

class LocationType(str, Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    PHYSICAL_CLASSROOM = "physical_classroom"

class LessonStatus(str, Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing" 
    COMPLETED = "completed"

class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(...)
    course_id: str = Field(...)
    start_date: date = Field(...)
    start_time: time = Field(...)
    duration: int = Field(..., ge=1)  # in minutes
    location_type: LocationType = Field(...)
    zoom_link: Optional[str] = Field(None, max_length=500)
    google_meet_link: Optional[str] = Field(None, max_length=500)
    classroom_location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: LessonStatus = LessonStatus.UPCOMING
    is_active: bool = True

    @model_validator(mode='after')
    def validate_location_fields(self):
        if self.location_type == LocationType.ZOOM and not self.zoom_link:
            raise ValueError("Zoom link is required for Zoom meetings")
        if self.location_type == LocationType.GOOGLE_MEET and not self.google_meet_link:
            raise ValueError("Google Meet link is required for Google Meet sessions")
        if self.location_type == LocationType.PHYSICAL_CLASSROOM and not self.classroom_location:
            raise ValueError("Classroom location is required for physical classrooms")
        return self

class LessonCreate(LessonBase):
    pass

class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    course_id: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    duration: Optional[int] = Field(None, ge=1)
    location_type: Optional[LocationType] = None
    zoom_link: Optional[str] = Field(None, max_length=500)
    google_meet_link: Optional[str] = Field(None, max_length=500)
    classroom_location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[LessonStatus] = None
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def validate_location_fields(self):
        if self.location_type:
            if self.location_type == LocationType.ZOOM and not self.zoom_link:
                raise ValueError("Zoom link is required for Zoom meetings")
            if self.location_type == LocationType.GOOGLE_MEET and not self.google_meet_link:
                raise ValueError("Google Meet link is required for Google Meet sessions")
            if self.location_type == LocationType.PHYSICAL_CLASSROOM and not self.classroom_location:
                raise ValueError("Classroom location is required for physical classrooms")
        return self

class LessonOut(LessonBase):
    id: str = Field(..., alias="_id")
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )

# Add to your models/lesson.py
class LessonWithCourseOut(LessonOut):
    course_title: Optional[str] = None
    course_name: Optional[str] = None

class LessonWithCompletion(LessonOut):
    completed: bool = False
    completed_at: Optional[datetime] = None