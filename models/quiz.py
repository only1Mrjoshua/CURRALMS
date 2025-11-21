from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class QuestionTypeEnum(str, Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    coding = "coding"

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
    total_questions: int
    passing_score: float = Field(..., ge=0, le=100)
    questions: List[QuestionCreate]

class QuizResponse(BaseModel):
    id: str
    course_id: str
    title: str
    description: Optional[str]
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
    quiz_title: Optional[str]
    course_title: Optional[str]
    score: Optional[float]
    attempt_number: int
    passed: bool
    completed_at: datetime

class UserQuizHistoryResponse(BaseModel):
    user_id: str
    summary: Dict[str, float]
    progress: List[QuizProgressResponse]