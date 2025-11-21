from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from database import get_database
from models.assignment import Assignment, UserAssignmentSubmission, LateSubmissionApproval, ExtensionRequest


# Helper function to convert MongoDB document to model
def convert_doc_to_model(doc, model_class):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return model_class(**doc) if doc else None


# Assignment CRUD Operations
async def create_assignment_crud(assignment_data: dict):
    db = await get_database()
    
    # Add timestamps
    now = datetime.utcnow()
    assignment_data['created_at'] = now
    assignment_data['updated_at'] = now
    assignment_data['_id'] = ObjectId()
    
    result = await db.assignments.insert_one(assignment_data)
    
    # Fetch the created assignment
    assignment = await db.assignments.find_one({"_id": result.inserted_id})
    return convert_doc_to_model(assignment, Assignment)


async def get_assignments_by_course(course_id: str):
    db = await get_database()
    assignments = await db.assignments.find({"course_id": course_id}).to_list(length=100)
    return [convert_doc_to_model(assignment, Assignment) for assignment in assignments]


async def get_assignment_by_id(assignment_id: str):
    db = await get_database()
    assignment = await db.assignments.find_one({"_id": ObjectId(assignment_id)})
    return convert_doc_to_model(assignment, Assignment)


async def update_assignment_crud(assignment_id: str, update_data: dict):
    db = await get_database()
    update_data["updated_at"] = datetime.utcnow()
    await db.assignments.update_one(
        {"_id": ObjectId(assignment_id)},
        {"$set": update_data}
    )
    return await get_assignment_by_id(assignment_id)


async def delete_assignment_crud(assignment_id: str):
    db = await get_database()
    result = await db.assignments.delete_one({"_id": ObjectId(assignment_id)})
    return result.deleted_count > 0


async def get_all_assignments():
    db = await get_database()
    assignments = await db.assignments.find().to_list(length=100)
    return [convert_doc_to_model(assignment, Assignment) for assignment in assignments]


# Submission CRUD Operations
async def create_submission_crud(submission_data: dict):
    db = await get_database()
    
    # Add timestamps
    now = datetime.utcnow()
    submission_data['submitted_at'] = now
    submission_data['created_at'] = now
    submission_data['updated_at'] = now
    submission_data['_id'] = ObjectId()
    
    result = await db.submissions.insert_one(submission_data)
    
    # Fetch the created submission
    submission = await db.submissions.find_one({"_id": result.inserted_id})
    return convert_doc_to_model(submission, UserAssignmentSubmission)


async def get_submission_by_user_and_assignment(user_id: str, assignment_id: str):
    db = await get_database()
    submission = await db.submissions.find_one({
        "user_id": user_id,
        "assignment_id": assignment_id
    })
    return convert_doc_to_model(submission, UserAssignmentSubmission)


async def get_submissions_by_assignment(assignment_id: str):
    db = await get_database()
    submissions = await db.submissions.find({"assignment_id": assignment_id}).to_list(length=100)
    return [convert_doc_to_model(submission, UserAssignmentSubmission) for submission in submissions]


async def get_submission_by_id(submission_id: str):
    db = await get_database()
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    return convert_doc_to_model(submission, UserAssignmentSubmission)


async def grade_submission_crud(submission_id: str, grade: float, feedback: str = None):
    db = await get_database()
    update_data = {
        "grade": grade,
        "feedback": feedback,
        "updated_at": datetime.utcnow()
    }
    await db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": update_data}
    )
    return await get_submission_by_id(submission_id)


# Late Submission Approval Operations
async def create_late_approval_crud(approval_data: dict):
    db = await get_database()
    # Remove existing approval for same user and assignment
    await db.late_approvals.delete_many({
        "user_id": approval_data["user_id"],
        "assignment_id": approval_data["assignment_id"]
    })
    
    # Add timestamps
    now = datetime.utcnow()
    approval_data['created_at'] = now
    approval_data['updated_at'] = now
    approval_data['_id'] = ObjectId()
    
    result = await db.late_approvals.insert_one(approval_data)
    
    # Fetch the created approval
    approval = await db.late_approvals.find_one({"_id": result.inserted_id})
    return convert_doc_to_model(approval, LateSubmissionApproval)


async def get_late_approval_by_id(approval_id: str):
    db = await get_database()
    approval = await db.late_approvals.find_one({"_id": ObjectId(approval_id)})
    return convert_doc_to_model(approval, LateSubmissionApproval)


async def get_active_late_approval(user_id: str, assignment_id: str):
    db = await get_database()
    approval = await db.late_approvals.find_one({
        "user_id": user_id,
        "assignment_id": assignment_id,
        "approved_until": {"$gt": datetime.utcnow()}
    })
    return convert_doc_to_model(approval, LateSubmissionApproval)


# Extension Request Operations
async def create_extension_request_crud(request_data: dict):
    db = await get_database()
    
    # Add timestamps
    now = datetime.utcnow()
    request_data['created_at'] = now
    request_data['updated_at'] = now
    request_data['_id'] = ObjectId()
    
    result = await db.extension_requests.insert_one(request_data)
    
    # Fetch the created request
    request = await db.extension_requests.find_one({"_id": result.inserted_id})
    return convert_doc_to_model(request, ExtensionRequest)


async def get_extension_request_by_id(request_id: str):
    db = await get_database()
    request = await db.extension_requests.find_one({"_id": ObjectId(request_id)})
    return convert_doc_to_model(request, ExtensionRequest)


async def get_extension_requests_by_assignment(assignment_id: str):
    db = await get_database()
    requests = await db.extension_requests.find({"assignment_id": assignment_id}).to_list(length=100)
    return [convert_doc_to_model(request, ExtensionRequest) for request in requests]


async def update_extension_request_crud(request_id: str, status: str):
    db = await get_database()
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    await db.extension_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": update_data}
    )
    return await get_extension_request_by_id(request_id)