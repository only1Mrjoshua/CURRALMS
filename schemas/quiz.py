from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class QuestionTypeEnum(str, Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    coding = "coding"

# Add this enum for categories
class QuizCategoryEnum(str, Enum):
    design = "Design"
    development = "Development"
    blockchain = "Blockchain"
    cybersecurity = "Cyber Security"

class QuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionTypeEnum
    options: Optional[List[str]] = None
    correct_answer: str
    code_template: Optional[str] = None
    test_cases: Optional[List[Dict[str, Any]]] = None

class QuizCreate(BaseModel):
    course_id: str
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: QuizCategoryEnum = QuizCategoryEnum.design  # Default to Design
    total_questions: int
    passing_score: float = Field(..., ge=0, le=100)
    questions: List[QuestionCreate]

class QuizResponse(BaseModel):
    id: str
    course_id: str
    title: str
    description: Optional[str]
    category: QuizCategoryEnum
    total_questions: int
    passing_score: float
    created_at: datetime
    updated_at: datetime

class QuizSubmission(BaseModel):
    answers: Dict[str, str]  # question_id -> answer

class QuizResult(BaseModel):
    quiz_id: str
    user_id: str
    score: float
    passed: bool
    completed_at: datetime
    detailed_results: List[Dict[str, Any]]
    progress: Dict[str, Any]

class QuizProgressResponse(BaseModel):
    id: str
    user_id: str
    quiz_id: str
    quiz_title: Optional[str] = None
    course_title: Optional[str] = None  # Make this optional
    score: Optional[float] = None
    attempt_number: int
    passed: bool
    completed_at: datetime

class UserQuizHistoryResponse(BaseModel):
    user_id: str
    summary: Dict[str, float]
    progress: List[QuizProgressResponse]