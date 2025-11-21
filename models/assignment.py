from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Assignment(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    course_id: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    max_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class UserAssignmentSubmission(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    assignment_id: str
    submission_type: str  # text, link, file
    content: Optional[str] = None
    file_url: Optional[str] = None
    grade: Optional[float] = None
    feedback: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class LateSubmissionApproval(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    assignment_id: str
    approved_until: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class ExtensionRequest(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    assignment_id: str
    reason: str
    requested_until: datetime
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )