from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime

# Base schemas
class LearningObjectiveBase(BaseModel):
    order_index: int = 0
    is_course_objective: bool = False

class CourseBase(BaseModel):
    title: str
    description: str
    short_description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    level: str = "beginner"
    language: str = "en"
    target_audience: Optional[str] = None
    duration_hours: Optional[float] = None
    effort_weeks: Optional[int] = None
    is_self_paced: bool = True
    max_enrollments: Optional[int] = None
    price: float = 0.0
    currency: str = "USD"
    access_days: Optional[int] = None
    course_image: Optional[str] = None
    promo_video: Optional[str] = None

# Response schemas
class LearningObjectiveResponse(LearningObjectiveBase):
    model_config = ConfigDict(from_attributes=True)

class CourseResponse(CourseBase):
    id: str = Field(alias="_id")
    instructor_id: str
    is_active: bool
    is_public: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True
    )

# Create schemas
class CourseCreate(CourseBase):
    instructor_id: str

class CourseModuleCreate(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    order_index: int = 0

class LessonCreate(BaseModel):
    module_id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    content_type: str = "html"
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    document_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    order_index: int = 0
    is_free_preview: bool = False

class QuizCreate(BaseModel):
    lesson_id: Optional[str] = None
    course_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    quiz_type: str = "knowledge_check"
    pass_threshold: float = 80.0
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 1
    order_index: int = 0

# Update schemas - ✅ FIXED: Added all missing fields
class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None  # ✅ ADDED
    level: Optional[str] = None
    language: Optional[str] = None  # ✅ ADDED
    target_audience: Optional[str] = None
    duration_hours: Optional[float] = None
    effort_weeks: Optional[int] = None  # ✅ ADDED
    is_self_paced: Optional[bool] = None  # ✅ ADDED
    max_enrollments: Optional[int] = None  # ✅ ADDED
    price: Optional[float] = None
    currency: Optional[str] = None  # ✅ ADDED
    access_days: Optional[int] = None  # ✅ ADDED
    course_image: Optional[str] = None
    promo_video: Optional[str] = None  # ✅ ADDED
    instructor_id: Optional[str] = None  # ✅ ADDED
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None

# Enrollment schemas
class EnrollmentBase(BaseModel):
    user_id: str
    course_id: str

class EnrollmentResponse(EnrollmentBase):
    id: str = Field(alias="_id")
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float
    current_lesson_id: Optional[str] = None
    status: str
    completed_lessons: List[str] = []
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True  # Add this line
    )

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentUpdate(BaseModel):
    progress_percentage: Optional[float] = None
    current_lesson_id: Optional[str] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_lessons: Optional[List[str]] = None