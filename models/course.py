# models/course.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return {
            'type': 'str',
            'format': 'objectid'
        }

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError("Invalid ObjectId string")
        raise ValueError("Must be ObjectId or string")

class MongoDBModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        from_attributes=True
    )

# Embedded documents
class LearningObjective(BaseModel):
    order_index: int = 0
    is_course_objective: bool = False

class QuestionOption(BaseModel):
    option_text: str
    is_correct: bool = False
    order_index: int = 0

class QuizQuestion(BaseModel):
    question_text: str
    question_type: str = "multiple_choice"
    points: int = 1
    order_index: int = 0
    explanation: Optional[str] = None
    options: List[QuestionOption] = []

class LessonResource(BaseModel):
    title: str
    resource_type: str = "document"
    file_url: Optional[str] = None
    external_url: Optional[str] = None
    description: Optional[str] = None
    order_index: int = 0

class Course(MongoDBModel):
    title: str
    description: str
    short_description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    language: str = "en"
    target_audience: Optional[str] = None
    instructor_id: PyObjectId
    duration_hours: Optional[float] = None
    effort_weeks: Optional[int] = None
    is_self_paced: bool = True
    max_enrollments: Optional[int] = None
    price: float = 0.0
    currency: str = "USD"
    access_days: Optional[int] = None
    course_image: Optional[str] = None
    promo_video: Optional[str] = None
    is_active: bool = True
    is_public: bool = False
    next_course_id: Optional[PyObjectId] = None  # The course that unlocks after completion
    is_sequential: bool = True  # Whether this course requires prerequisites

class CourseModule(MongoDBModel):
    course_id: PyObjectId
    title: str
    description: Optional[str] = None
    order_index: int = 0
    is_active: bool = True

class Lesson(MongoDBModel):
    module_id: PyObjectId
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    content_type: str = "html"
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    document_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    order_index: int = 0
    is_active: bool = True
    is_free_preview: bool = False
    resources: List[LessonResource] = []

class Quiz(MongoDBModel):
    lesson_id: Optional[PyObjectId] = None
    course_id: Optional[PyObjectId] = None
    title: str
    description: Optional[str] = None
    quiz_type: str = "knowledge_check"
    pass_threshold: float = 80.0
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 1
    order_index: int = 0
    is_active: bool = True
    questions: List[QuizQuestion] = []

class Enrollment(MongoDBModel):
    user_id: PyObjectId
    course_id: PyObjectId
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    current_lesson_id: Optional[PyObjectId] = None
    status: str = Field(default="enrolled", pattern="^(enrolled|in_progress|completed)$")
    completed_lessons: List[PyObjectId] = []
    grade: Optional[float] = None  # Final grade if applicable
    certificate_issued: bool = False