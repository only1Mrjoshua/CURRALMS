from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from bson import ObjectId


# Simple ObjectId handling for Pydantic v2
class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return {
            'type': 'str',
            'from_attributes': True,
        }

    @classmethod
    def validate(cls, value):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return str(value)


class SubmissionType(str, Enum):
    TEXT = "text"
    LINK = "link"
    FILE = "file"


class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime
    max_score: float = Field(gt=0)
    course_id: str


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: Optional[float] = Field(None, gt=0)
    course_id: Optional[str] = None


class AssignmentOut(AssignmentBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# Separate submission request schemas
class TextSubmissionRequest(BaseModel):
    content: str


class LinkSubmissionRequest(BaseModel):
    content: str  # This will be the URL/link


# File submission will be handled via FormData


# Unified submission response
class AssignmentSubmissionResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    assignment_id: str
    submission_type: SubmissionType
    content: Optional[str] = None
    file_url: Optional[str] = None
    grade: Optional[float] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class GradeSubmission(BaseModel):
    grade: float
    feedback: Optional[str] = None


class LateSubmissionApprovalBase(BaseModel):
    approved_until: datetime


class LateSubmissionApprovalCreate(LateSubmissionApprovalBase):
    user_id: str
    assignment_id: str


class LateSubmissionApprovalResponse(LateSubmissionApprovalBase):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    assignment_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class ExtensionRequestBase(BaseModel):
    reason: str
    requested_until: datetime


class ExtensionRequestCreate(ExtensionRequestBase):
    assignment_id: str


class ExtensionRequestResponse(ExtensionRequestBase):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    assignment_id: str
    status: str  # pending, approved, rejected
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class ExtensionRequestUpdate(BaseModel):
    status: str  # approved, rejected